#include "Weapons/MIWeaponRules.h"

namespace MIWeaponRulesPrivate
{
	// Constants of src/weapon/logic.js that belong to the rules, not to the tuning.
	constexpr double Credit = 0.001;  // CREDIT: an idle gun may bank this much of a shot interval, no more
	const FName Magout(TEXT("magout"));
	const FName Magin(TEXT("magin"));
	const FName Bolt(TEXT("bolt"));
	const FName Done(TEXT("done"));
	const FName Start(TEXT("start"));
	const FName Cancel(TEXT("cancel"));
}

void FMIWeaponRules::Init(const FMIWeaponsData& InData, uint32 Seed, FMIGameEvents* InEvents)
{
	using namespace MIWeaponRulesPrivate;
	Data = InData;
	Events = InEvents;
	Rng = FMIRng(Seed).Fork(TEXT("weapon"));
	Timelines.Reset();
	Ammo.SetNum(Data.Guns.Num());
	SemiMode.SetNum(Data.Guns.Num());
	// Pools (LOADOUT.md 4.3): every finite gun draws on its named pool (the bag); an infinite gun has its own.
	Pools.Reset();
	TMap<FName, int32> Named;
	for (int32 I = 0; I < Data.Guns.Num(); ++I)
	{
		const FMIWeaponDef& Gun = Data.Guns[I];
		if (FMath::IsFinite(Gun.Reserve))
		{
			const FName Name = Gun.Pool.IsNone() ? FName(TEXT("bag")) : Gun.Pool;
			if (const int32* Found = Named.Find(Name))
			{
				Ammo[I].Pool = *Found;
				continue;
			}
			Named.Add(Name, Pools.Num());
		}
		Ammo[I].Pool = Pools.Num();
		Pools.Add(0.0);
	}
	for (const FMIWeaponDef& Gun : Data.Guns)
	{
		for (int32 Empty = 0; Empty < 2; ++Empty)
		{
			TArray<FMark>& List = Timelines.AddDefaulted_GetRef();
			List.Add({Gun.Reload.MagOut, Magout});
			List.Add({Gun.Reload.MagIn, Magin});
			const double BoltAt = Empty ? Gun.Reload.BoltEmpty : Gun.Reload.BoltTactical;
			if (BoltAt >= 0.0)
			{
				List.Add({BoltAt, Bolt});
			}
			List.Add({Empty ? Gun.Reload.Empty : Gun.Reload.Tactical, Done});
		}
	}
	Reset();
}

void FMIWeaponRules::Settle()
{
	Cooldown = 0.0;
	SinceShot = 1e30;
	Burst = 0;
	Bloom = 0.0;
	Heat = 0.0;
	FireBuffer = 0.0;
	bDryLatch = false;
	bSustained = false;
	AutoReload = 0.0;
}

void FMIWeaponRules::Equip(int32 Gun)
{
	if (Gun != Current)
	{
		LastUsed = Current;
	}
	Current = Gun;
	Settle();
}

void FMIWeaponRules::Reset()
{
	// The bag starts with the largest reserve among its guns (150 for every gun of the roster: the web CHOPPER's).
	for (double& P : Pools)
	{
		P = -1.0;
	}
	for (int32 I = 0; I < Data.Guns.Num(); ++I)
	{
		Ammo[I].Mag = Data.Guns[I].MagSize;
		double& P = PoolOf(I);
		P = P < 0.0 ? Data.Guns[I].Reserve : FMath::Max(P, Data.Guns[I].Reserve);
		// Every run starts each gun in fireModes[0] (no fire mode is saved).
		SemiMode[I] = Data.Guns[I].FireModes.Num() > 0 ? Data.Guns[I].FireModes[0] == TEXT("semi") : !Data.Guns[I].bAuto;
	}
	Selector = FSelector();
	bReloadAfterSelector = false;
	Reload = FReload();
	Swap = FSwap();
	Strike = FStrike();
	QueuedSwap = INDEX_NONE;
	StrikeWait = 0.0;
	bDropped = false;
	AdsLinear = AdsValue = 0.0;
	SprintBlend.Reset();
	Wall = WallTarget = WallTimer = 0.0;
	AimTimer = 0.0;
	AimTargetValue = 1.0;
	AimSlow = 1.0;
	Current = 0;
	LastUsed = Data.Guns.Num() > 1 ? 1 : 0;
	Settle();
	Spread = Data.Guns.Num() > 0 ? Data.Guns[0].Spread.Hip : 0.0;
}

void FMIWeaponRules::AddReserve(double Rounds, double Cap)
{
	if (!(Rounds > 0.0))
	{
		return;
	}
	// Once per pool, not per gun: with one finite gun that is the web's arithmetic.
	for (double& P : Pools)
	{
		if (FMath::IsFinite(P) && P < Cap)
		{
			P = FMath::Min(Cap, P + Rounds);
		}
	}
}

void FMIWeaponRules::Drop()
{
	if (bDropped)
	{
		return;
	}
	CancelReload();
	CancelSelector();
	Swap = FSwap();
	Strike = FStrike();
	QueuedSwap = INDEX_NONE;
	AutoReload = 0.0;
	FireBuffer = 0.0;
	bDropped = true;
}

FName FMIWeaponRules::GetState() const
{
	if (bDropped) return TEXT("lowered");
	if (Swap.bActive) return TEXT("switching");
	if (Strike.bActive) return TEXT("melee");
	if (Reload.bActive) return TEXT("reloading");
	if (Selector.bActive) return TEXT("selector");
	if (SprintBlend.X > 0.5) return TEXT("lowered");
	return SinceShot < Data.Common.FiringHold ? TEXT("firing") : TEXT("idle");
}

FName FMIWeaponRules::GetCue() const
{
	if (bDropped || Swap.bActive) return NAME_None;
	if (Reload.bActive) return TEXT("reloading");
	const FAmmo& A = Ammo[Current];
	if (A.Mag == 0) return Pools[A.Pool] > 0.0 ? TEXT("reload") : TEXT("empty");
	return A.Mag <= FMath::CeilToInt(GetDef().MagSize * Data.Common.LowAmmoFraction) ? FName(TEXT("low")) : NAME_None;
}

EMIWeaponActivity FMIWeaponRules::GetActivity() const
{
	if (bDropped) return EMIWeaponActivity::Dropped;
	if (Swap.bActive) return Swap.bHolster ? EMIWeaponActivity::Holstering : EMIWeaponActivity::Drawing;
	if (Strike.bActive) return EMIWeaponActivity::Striking;
	if (Reload.bActive) return EMIWeaponActivity::Reloading;
	if (Selector.bActive) return EMIWeaponActivity::Selector;
	return EMIWeaponActivity::Ready;
}

double FMIWeaponRules::GetBag() const
{
	for (const double P : Pools)
	{
		if (FMath::IsFinite(P)) return P;
	}
	return -1.0;
}

double FMIWeaponRules::HolsterOf(int32 Gun) const
{
	const double H = Data.Guns.IsValidIndex(Gun) ? Data.Guns[Gun].Holster : 0.0;
	return H > 0.0 ? H : Data.Common.Holster;
}

double FMIWeaponRules::DrawOf(int32 Gun) const
{
	const double D = Data.Guns.IsValidIndex(Gun) ? Data.Guns[Gun].Draw : 0.0;
	return D > 0.0 ? D : Data.Common.Draw;
}

double FMIWeaponRules::GetActivityTime() const
{
	if (Swap.bActive) return Swap.T;
	if (Strike.bActive) return Strike.T;
	if (Reload.bActive) return Reload.T;
	if (Selector.bActive) return Selector.T;
	return 0.0;
}

// ------------------------------------------------------------------------------------------------- reload

void FMIWeaponRules::ReloadEvent(FName Phase, bool bEmpty)
{
	if (Events)
	{
		Events->WeaponReload.Broadcast({GetDef().Id, Phase, bEmpty});
	}
}

bool FMIWeaponRules::StartReload()
{
	const FAmmo& A = Ammo[Current];
	if (Busy() || bDropped || A.Mag >= GetDef().MagSize || Pools[A.Pool] <= 0.0)
	{
		return false;
	}
	const bool bEmpty = A.Mag == 0;
	AutoReload = 0.0;
	FireBuffer = 0.0;
	Reload.bActive = true;
	Reload.T = 0.0;
	Reload.bEmpty = bEmpty;
	Reload.Next = 0;
	ReloadEvent(MIWeaponRulesPrivate::Start, bEmpty);
	return true;
}

void FMIWeaponRules::CancelReload()
{
	if (!Reload.bActive)
	{
		return;
	}
	const bool bEmpty = Reload.bEmpty;
	Reload = FReload();
	ReloadEvent(MIWeaponRulesPrivate::Cancel, bEmpty);
}

void FMIWeaponRules::AdvanceReload(double Dt)
{
	using namespace MIWeaponRulesPrivate;
	Reload.T += Dt;
	const TArray<FMark>& List = Marks(Current, Reload.bEmpty);
	while (Reload.bActive && Reload.Next < List.Num() && Reload.T >= List[Reload.Next].T)
	{
		const FName Phase = List[Reload.Next++].Phase;
		const bool bEmpty = Reload.bEmpty;
		if (Phase == Magin)
		{
			// The rounds count from the moment the magazine is seated, not from the end of the reload.
			FAmmo& A = Ammo[Current];
			double& Reserve = Pools[A.Pool];
			const double N = FMath::Min(static_cast<double>(GetDef().MagSize - A.Mag), Reserve);
			A.Mag += static_cast<int32>(N);
			Reserve -= N;
		}
		else if (Phase == Done)
		{
			Reload = FReload();
		}
		ReloadEvent(Phase, bEmpty);
	}
}

// ------------------------------------------------------------------------------------------------- switching

void FMIWeaponRules::SwitchEvent(int32 From, int32 To, bool bHolster)
{
	if (Events)
	{
		Events->WeaponSwitch.Broadcast({Data.Guns[From].Id, Data.Guns[To].Id, bHolster ? FName(TEXT("holster")) : FName(TEXT("draw"))});
	}
}

void FMIWeaponRules::RequestSwitch(int32 Gun)
{
	if (!Data.Guns.IsValidIndex(Gun) || bDropped)
	{
		return;
	}
	if (Strike.bActive)
	{
		QueuedSwap = Gun;  // goes through when the strike is over
		return;
	}
	if (Selector.bActive && Gun != Current)
	{
		CancelSelector();  // a switch request cancels the selector without flipping
	}
	if (!Swap.bActive)
	{
		if (Gun == Current)
		{
			return;
		}
		CancelReload();
		AutoReload = 0.0;
		FireBuffer = 0.0;
		Swap.bActive = true;
		Swap.bHolster = true;
		Swap.T = 0.0;
		Swap.To = Gun;
		SwitchEvent(Current, Gun, true);
	}
	else if (Swap.bHolster)
	{
		if (Gun == Swap.To)
		{
			return;
		}
		if (Gun != Current)
		{
			// A third gun while holstering: the holster runs on toward the new choice (never with two guns).
			Swap.To = Gun;
			SwitchEvent(Current, Gun, true);
			return;
		}
		// Changed their mind: the gun on its way down comes straight back up from where it got to.
		const int32 From = Swap.To;
		Swap.bHolster = false;
		Swap.T = DrawOf(Current) * (1.0 - Swap.T / HolsterOf(Current));
		Swap.To = Current;
		SwitchEvent(From, Current, false);
	}
	else if (Gun != Current)
	{
		// Mid-draw and they want another gun: holster again, as far along as the draw was short.
		Swap.bHolster = true;
		Swap.T = HolsterOf(Current) * (1.0 - Swap.T / DrawOf(Current));
		Swap.To = Gun;
		SwitchEvent(Current, Gun, true);
	}
}

void FMIWeaponRules::AdvanceSwitch(double Dt)
{
	Swap.T += Dt;
	if (Swap.bHolster && Swap.T >= HolsterOf(Current))
	{
		const int32 From = Current;
		const double Holster = HolsterOf(Current);
		Equip(Swap.To);
		Swap.bHolster = false;
		Swap.T -= Holster;
		SwitchEvent(From, Current, false);
	}
	if (!Swap.bHolster && Swap.T >= DrawOf(Current))
	{
		Swap = FSwap();
	}
}

// ------------------------------------------------------------------------------------------------- selector

void FMIWeaponRules::CancelSelector()
{
	Selector = FSelector();
	bReloadAfterSelector = false;
}

void FMIWeaponRules::AdvanceSelector(double Dt)
{
	Selector.T += Dt;
	if (Selector.T >= GetDef().ModeSwitch)
	{
		Selector = FSelector();
		SemiMode[Current] = !SemiMode[Current];
		if (Events)
		{
			Events->WeaponMode.Broadcast(GetDef().Id, SemiMode[Current]);
		}
		if (bReloadAfterSelector)
		{
			// A dry fire's auto reload that fell due meanwhile runs now.
			bReloadAfterSelector = false;
			StartReload();
		}
	}
}

// ------------------------------------------------------------------------------------------------- melee

void FMIWeaponRules::StartStrike()
{
	if (Reload.bActive)
	{
		if (!Data.Melee.bCancelsReload)
		{
			return;
		}
		CancelReload();
	}
	CancelSelector();
	AutoReload = 0.0;
	FireBuffer = 0.0;
	Strike.bActive = true;
	Strike.T = 0.0;
	Strike.bLanded = false;
	StrikeWait = Data.Melee.Cooldown;
	if (Events)
	{
		Events->WeaponSwing.Broadcast(GetDef().Id);
	}
}

void FMIWeaponRules::AdvanceStrike(double Dt, IMIWeaponHost& Host)
{
	const FMIMeleeData& M = Data.Melee;
	Strike.T += Dt;
	if (!Strike.bLanded && Strike.T >= M.HitAt)
	{
		Strike.bLanded = true;
		const FMIWeaponPlayerState Player = Host.GetPlayerState();
		FMIStrikeRequest Request;
		Request.Origin = Player.Eye;
		Request.Direction = Player.Forward;
		Request.Reach = M.Reach;
		Request.ConeDegrees = M.Cone;
		Request.Damage = M.Damage;
		const EMIStrikeResult Result = Host.Melee(Request);
		const bool bHit = Result == EMIStrikeResult::Enemy;
		const bool bSolid = bHit || Result == EMIStrikeResult::World;
		if (bSolid)
		{
			Host.AddShake(bHit ? M.Shake : M.Shake * 0.5);
		}
		if (Events)
		{
			Events->WeaponMelee.Broadcast(bHit);
		}
		if (bHit)
		{
			Host.Rumble(0.6, 0.4, 90.0);
		}
	}
	if (Strike.T >= M.Duration)
	{
		Strike = FStrike();
		if (QueuedSwap != INDEX_NONE)
		{
			const int32 Gun = QueuedSwap;
			QueuedSwap = INDEX_NONE;
			RequestSwitch(Gun);
		}
	}
}

// ------------------------------------------------------------------------------------------------- firing

void FMIWeaponRules::Shoot(IMIWeaponHost& Host)
{
	const FMIWeaponDef& Def = GetDef();
	const FMIWeaponCommonData& C = Data.Common;
	FAmmo& A = Ammo[Current];
	A.Mag--;
	Burst++;
	SinceShot = 0.0;
	Heat = FMath::Min(C.HeatMax, Heat + C.HeatPerShot);

	// A uniformly random direction inside the spread cone around the aim.
	const FMIWeaponPlayerState Player = Host.GetPlayerState();
	FVector Right = FVector::CrossProduct(FVector::UpVector, Player.Forward);
	if (Right.SizeSquared() < 1e-10)
	{
		Right = FVector(0.0, 1.0, 0.0);
	}
	Right.Normalize();
	const FVector Up = FVector::CrossProduct(Player.Forward, Right);
	const double R = FMath::Tan(MI::DegToRad(Spread)) * FMath::Sqrt(Random());
	const double Angle = Random() * UE_DOUBLE_TWO_PI;
	const FVector Dir = (Player.Forward + Right * (R * FMath::Cos(Angle)) + Up * (R * FMath::Sin(Angle))).GetSafeNormal();

	// The round leaves the eye, not the barrel: what the crosshair covers is what gets hit.
	FMIShotRequest Shot;
	Shot.Origin = Player.Eye;
	Shot.Direction = Dir;
	Shot.Range = Def.Range;
	Shot.Damage = Def.Damage;
	Shot.HeadMultiplier = C.HeadMultiplier;
	Shot.Weapon = Def.Id;
	Shot.FalloffStart = Def.FalloffStart;
	Shot.FalloffEnd = Def.FalloffEnd;
	Shot.FalloffMin = Def.FalloffMin;
	Shot.NoiseRadius = Def.NoiseRadius;
	Shot.bSuppressed = Def.bSuppressed;
	const FMIShotResult Hit = Host.Hitscan(Shot);
	Host.OnRoundFired(Shot, Hit, Def.FlashScale * MI::Lerp(1.0, C.AdsFlashScale, AdsValue));

	// Recoil into the camera: the CHOPPER climbs, then weaves; the NINE snaps. Web yaw is to the left: negated.
	const double Scale = MI::Lerp(1.0, C.AdsRecoilScale, AdsValue) * (Player.bCrouching ? C.CrouchRecoilScale : 1.0);
	const FMIWeaponRecoilData& K = Def.Recoil;
	double KickPitch = K.Pitch * Scale * MI::Lerp(K.PitchRandomMin, K.PitchRandomMax, Random());
	double KickYawLeft;
	if (!K.bWeave)
	{
		KickYawLeft = Signed() * K.Yaw * Scale;
	}
	else
	{
		if (Burst >= K.LateFrom)
		{
			KickPitch *= K.LateScale;
		}
		KickYawLeft = Burst < K.WeaveFrom
			? Signed() * K.YawEarly * Scale
			: (FMath::Sin(Burst * K.WeaveFreq + WeavePhase) * K.WeaveAmp + Signed() * K.WeaveRandom) * Scale;
	}
	// The web game says weapon:fire before the kick reaches the camera.
	if (Events)
	{
		FMIShotFiredEvent Event;
		Event.Weapon = Def.Id;
		Event.Muzzle = Player.Eye;
		Event.Direction = Dir;
		Event.Ads = AdsValue;
		Event.KickPitch = KickPitch;
		Event.KickYaw = -KickYawLeft;
		Event.Spread = Spread;
		Event.Burst = Burst;
		Event.MagLeft = A.Mag;
		Event.NoiseRadius = Def.NoiseRadius;
		Event.bSuppressed = Def.bSuppressed;
		Events->WeaponFire.Broadcast(Event);
	}
	Host.AddRecoil(KickPitch, -KickYawLeft);
	Host.AddShake(K.Shake * Scale);

	Bloom = FMath::Min(1.0, Bloom + Def.Spread.Shot);
	Host.Rumble(Def.RumbleStrong, Def.RumbleWeak, Def.RumbleMs);
}

void FMIWeaponRules::DryFire(IMIWeaponHost& Host)
{
	const FMIWeaponDef& Def = GetDef();
	bDryLatch = true;
	if (Def.DryCooldown > 0.0)
	{
		Cooldown = Def.DryCooldown;
	}
	if (PoolOf(Current) > 0.0)
	{
		AutoReload = Def.DryReloadDelay;
	}
	if (Events)
	{
		Events->WeaponDry.Broadcast(Def.Id);
	}
	Host.OnDry();
}

void FMIWeaponRules::PullTrigger(const FMIWeaponInput& Input, IMIWeaponHost& Host)
{
	using namespace MIWeaponRulesPrivate;
	const FMIWeaponDef& Def = GetDef();
	FAmmo& A = Ammo[Current];
	const bool bHeld = Input.bFireDown;
	const bool bCanFire = !Busy() && SprintBlend.X < Data.Common.SprintFireGate;
	// An automatic gun on its semi setting fires as a semi-automatic (LOADOUT.md 4.4).
	const bool bAuto = Def.bAuto && !SemiMode[Current];
	if (!bHeld)
	{
		bDryLatch = false;
	}

	// Only a gun that was already firing carries time over from the last frame; a fresh pull banks nothing.
	const bool bFiring = bAuto && bHeld && bCanFire && A.Mag > 0;
	if (!(bFiring && bSustained) && Cooldown < -Credit)
	{
		Cooldown = -Credit;
	}
	bSustained = bFiring;

	if (bAuto)
	{
		if (bFiring)
		{
			// The remainder of the interval carries over and a slow frame fires catch-up rounds.
			for (int32 N = 0; N < Data.Common.MaxCatchUpShots && Cooldown <= 0.0 && A.Mag > 0; ++N)
			{
				Shoot(Host);
				Cooldown += Def.Interval();
			}
		}
		else if (bHeld && bCanFire && !bDryLatch && Cooldown <= 0.0)
		{
			DryFire(Host);
		}
	}
	else
	{
		// Semi-automatic: one round per press; a press a moment early still counts.
		if (Input.bFirePressed)
		{
			FireBuffer = Def.FireBuffer > 0.0 ? Def.FireBuffer : Def.SemiFireBuffer;
		}
		if (FireBuffer > 0.0 && bCanFire && Cooldown <= 0.0)
		{
			FireBuffer = 0.0;
			if (A.Mag > 0)
			{
				Shoot(Host);
				Cooldown = Def.Interval();
			}
			else
			{
				DryFire(Host);
			}
		}
	}
	if (Cooldown < -Credit)
	{
		Cooldown = -Credit;
	}
	bTriggerHeld = bHeld && bCanFire;
}

// ------------------------------------------------------------------------------------------------- per frame

void FMIWeaponRules::ProbeWall(double Dt, const FMIWeaponPlayerState& Player, IMIWeaponHost& Host)
{
	const FMIWeaponCommonData& C = Data.Common;
	WallTimer -= Dt;
	if (WallTimer <= 0.0)
	{
		WallTimer = C.WallEvery;
		const FMIWeaponDef& Def = GetDef();
		const double Distance = Host.ProbeWall(Player.Eye, Player.Forward, Def.WallStart);
		WallTarget = Distance >= 0.0 ? MI::Clamp01((Def.WallStart - Distance) / (Def.WallStart - Def.WallFull)) : 0.0;
	}
	Wall = MI::Damp(Wall, WallTarget * MI::Lerp(1.0, C.WallAdsScale, AdsValue), C.WallRate, Dt);
}

void FMIWeaponRules::AssistAim(double Dt, const FMIWeaponInput& Input, const FMIWeaponPlayerState& Player, IMIWeaponHost& Host)
{
	const FMIWeaponCommonData& C = Data.Common;
	if (!Input.bPadActive)
	{
		AimTargetValue = 1.0;
		AimSlow = 1.0;
		return;
	}
	AimTimer -= Dt;
	if (AimTimer <= 0.0)
	{
		AimTimer = C.AimEvery;
		AimTargetValue = Host.AimTarget(Player.Eye, Player.Forward, C.AimRange) ? C.AimSlow : 1.0;
	}
	AimSlow = MI::Damp(AimSlow, AimTargetValue, C.AimRate, Dt);
}

void FMIWeaponRules::SetAim(IMIWeaponHost& Host, bool bWant, double Dt)
{
	AdsLinear = MI::MoveToward(AdsLinear, bWant ? 1.0 : 0.0, Dt / GetDef().AdsTime);
	AdsValue = MI::SmootherStep(0.0, 1.0, AdsLinear);
	Host.SetPlayerAimView(GetDef().AdsFov, GetDef().AdsLook);
	Host.SetPlayerAds(AdsValue);
}

void FMIWeaponRules::Update(double Dt, const FMIWeaponInput& Input, IMIWeaponHost& Host)
{
	const FMIWeaponCommonData& C = Data.Common;
	const FMIWeaponPlayerState Player = Host.GetPlayerState();

	if (!Player.bAlive)
	{
		Drop();
		SetAim(Host, false, Dt);
		AimSlow = 1.0;
		return;
	}
	if (bDropped)
	{
		bDropped = false;  // back on his feet without a full reset: the gun is simply in hand again
	}

	Cooldown -= Dt;
	SinceShot += Dt;
	StrikeWait -= Dt;
	FireBuffer -= Dt;
	// Bloom holds for a moment after every round, so rapid fire stacks it and paced fire sheds it.
	if (SinceShot > C.BloomHold)
	{
		Bloom = FMath::Max(0.0, Bloom - GetDef().Spread.Decay * Dt);
	}
	Heat = FMath::Max(0.0, Heat - C.HeatCool * Dt);
	if (Burst > 0 && SinceShot > C.BurstReset)
	{
		Burst = 0;
		WeavePhase = Random() * UE_DOUBLE_TWO_PI;
	}

	// Precedence within a frame: swap, next, previous, slots 1 to 4, wheel (LOADOUT.md 4.2). With two guns every
	// one of them picks the gun the web's swap picked: (Aim +- 1) mod 2 is OtherOf(Aim), LastUsed is OtherOf(Current).
	const int32 N = Data.Guns.Num();
	if (Input.bSwapPressed)
	{
		RequestSwitch(Swap.bActive && Swap.bHolster ? Current : LastUsed);
	}
	else if (Input.bNextPressed && N > 0)
	{
		RequestSwitch((GetAimIndex() + 1) % N);
	}
	else if (Input.bPreviousPressed && N > 0)
	{
		RequestSwitch((GetAimIndex() - 1 + N) % N);
	}
	else if (Input.bWeapon1Pressed)
	{
		RequestSwitch(0);
	}
	else if (Input.bWeapon2Pressed)
	{
		RequestSwitch(1);
	}
	else if (Input.bWeapon3Pressed)
	{
		RequestSwitch(2);
	}
	else if (Input.bWeapon4Pressed)
	{
		RequestSwitch(3);
	}
	else if (Input.WheelPick != INDEX_NONE)
	{
		RequestSwitch(Input.WheelPick);
	}

	if (Input.bFireModePressed && HasTwoModes(Current) && !Busy() && !bDropped)
	{
		Selector.bActive = true;
		Selector.T = 0.0;
	}

	if (Input.bMeleePressed && !Strike.bActive && StrikeWait <= 0.0 && !(Swap.bActive && Data.Melee.bBlockedWhileSwitching))
	{
		StartStrike();
	}

	if (Input.bReloadPressed)
	{
		StartReload();
	}
	if (AutoReload > 0.0 && (AutoReload -= Dt) <= 0.0)
	{
		AutoReload = 0.0;
		if (Selector.bActive)
		{
			bReloadAfterSelector = true;  // stays pending until the selector ends
		}
		else
		{
			StartReload();
		}
	}

	if (Swap.bActive)
	{
		AdvanceSwitch(Dt);
	}
	if (Reload.bActive)
	{
		AdvanceReload(Dt);
	}
	if (Strike.bActive)
	{
		AdvanceStrike(Dt, Host);
	}
	if (Selector.bActive)
	{
		AdvanceSelector(Dt);
	}

	// Sprinting lowers the gun; wanting to use it brings it back up, a little faster.
	const bool bWantsGun = Busy() || Input.bFireDown || Input.bAdsDown;
	SprintBlend.Step(Player.bSprinting && !bWantsGun ? 1.0 : 0.0, C.SprintRate * (bWantsGun ? C.SprintHurry : 1.0), 1.0, Dt);
	SprintBlend.X = MI::Clamp01(SprintBlend.X);

	SetAim(Host, Input.bAdsDown && !Busy() && SprintBlend.X < C.SprintAdsGate, Dt);

	const FMIWeaponSpreadData& S = GetDef().Spread;
	const double Cone = MI::Lerp(S.Hip, S.Ads, AdsValue)
		+ MI::Clamp01(Player.Speed / C.SpreadSpeedRef) * MI::Lerp(S.MoveHip, S.MoveAds, AdsValue)
		+ Bloom * MI::Lerp(S.BloomHip, S.BloomAds, AdsValue)
		+ (!Player.bOnGround ? S.Air : 0.0)
		- (Player.bCrouching ? S.Crouch * (1.0 - AdsValue) : 0.0);
	Spread = MI::Damp(Spread, FMath::Max(0.0, Cone), C.SpreadRate, Dt);

	PullTrigger(Input, Host);
	const FMIWeaponPlayerState After = Host.GetPlayerState();
	ProbeWall(Dt, After, Host);
	AssistAim(Dt, Input, After, Host);
}

FMIWeaponView FMIWeaponRules::GetView() const
{
	const FMIWeaponDef& Def = GetDef();
	FMIWeaponView V;
	V.Weapon = Def.Id;
	V.Activity = GetActivity();
	V.ActivityTime = GetActivityTime();
	switch (V.Activity)
	{
	case EMIWeaponActivity::Reloading: V.ActivityLength = Reload.bEmpty ? Def.Reload.Empty : Def.Reload.Tactical; break;
	case EMIWeaponActivity::Holstering: V.ActivityLength = HolsterOf(Current); break;
	case EMIWeaponActivity::Drawing: V.ActivityLength = DrawOf(Current); break;
	case EMIWeaponActivity::Selector: V.ActivityLength = Def.ModeSwitch; break;
	case EMIWeaponActivity::Striking: V.ActivityLength = Data.Melee.Duration; break;
	default: break;
	}
	if (Reload.bActive)
	{
		const TArray<FMark>& List = Marks(Current, Reload.bEmpty);
		V.ReloadStage = Reload.Next > 0 && List.IsValidIndex(Reload.Next - 1) ? List[Reload.Next - 1].Phase : FName(TEXT("start"));
		V.bReloadEmpty = Reload.bEmpty;
	}
	V.bTrigger = bTriggerHeld;
	V.Mag = Ammo[Current].Mag;
	V.MagSize = Def.MagSize;
	V.Ads = AdsValue;
	V.SprintBlend = SprintBlend.X;
	V.Wall = Wall;
	V.Spread = Spread;
	V.SinceShot = SinceShot;
	V.Burst = Burst;
	return V;
}
