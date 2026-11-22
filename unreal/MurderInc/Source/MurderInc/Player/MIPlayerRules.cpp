#include "Player/MIPlayerRules.h"

#include "Core/MIMath.h"

namespace MIPlayerRulesPrivate
{
	// Constants of src/player.js that are part of the formulas, not tuning (they are not in config.json either).
	constexpr double SpringStep = 1.0 / 120.0;  // SPRING_STEP: longest sub-step of the two springs
	// The phases of the six shake sines (src/player.js createShake).
	constexpr double ShakePhasePitch = 1.3;
	constexpr double ShakePhaseYaw[2] = {2.1, 0.4};
	constexpr double ShakePhaseRoll[2] = {4.2, 3.3};
	constexpr double SustainFloor = 1e-4;
}

// ------------------------------------------------------------------------------------------------- pure parts

double MIPlayerRules::TargetSpeed(const FMIPlayerSpeedData& S, bool bCrouching, bool bSprinting, double Ads, double Forward)
{
	double V = bCrouching ? S.Crouch : (bSprinting ? S.Sprint : S.Walk);
	V = MI::Lerp(V, FMath::Min(V, S.Ads), MI::Clamp01(Ads));
	if (Forward < 0.0)
	{
		V *= MI::Lerp(1.0, S.Backpedal, FMath::Min(1.0, -Forward));
	}
	return V;
}

bool MIPlayerRules::SprintWanted(const FMIPlayerSprintData& R, bool bHeld, double Forward, double Strafe, bool bCrouching, double Ads, bool bFiring)
{
	return bHeld && Forward > R.MinForward && FMath::Abs(Strafe) < R.MaxStrafe && !bCrouching && Ads < R.MaxAds && !bFiring;
}

void MIPlayerRules::ApproachVelocity(double& VX, double& VY, double WishX, double WishY, double Rate, double Dt, bool bSnap)
{
	const double EX = WishX - VX;
	const double EY = WishY - VY;
	const double Error = FMath::Sqrt(EX * EX + EY * EY);
	const double Step = Rate * Dt;
	if (Error <= Step)
	{
		if (bSnap)
		{
			VX = WishX;
			VY = WishY;
		}
		return;
	}
	VX += (EX / Error) * Step;
	VY += (EY / Error) * Step;
}

void FMIRecoil::Kick(const FMIPlayerRecoilData& Tune, double PitchDeg, double YawDeg)
{
	const double Share = 1.0 - Tune.Keep;
	TargetPitch = FMath::Clamp(TargetPitch + PitchDeg * Share, -Tune.MaxPitch, Tune.MaxPitch);
	TargetYaw = FMath::Clamp(TargetYaw + YawDeg * Share, -Tune.MaxYaw, Tune.MaxYaw);
	SinceKick = 0.0;
}

void FMIRecoil::Update(const FMIPlayerRecoilData& Tune, double Dt)
{
	SinceKick += Dt;
	// Only the part of this step that lies past the hold recentres: the same curve at any frame rate.
	const double Past = FMath::Min(Dt, SinceKick - Tune.Hold);
	if (Past > 0.0)
	{
		TargetPitch = MI::ExpDecay(TargetPitch, Tune.Recover, Past);
		TargetYaw = MI::ExpDecay(TargetYaw, Tune.Recover, Past);
	}
	Pitch = MI::Damp(Pitch, TargetPitch, Tune.Chase, Dt);
	Yaw = MI::Damp(Yaw, TargetYaw, Tune.Chase, Dt);
}

void FMIShake::Add(const FMIPlayerShakeData& Tune, double X)
{
	if (!(X > 0.0))
	{
		return;
	}
	if (X < Tune.SustainBelow)
	{
		Trickle += X;
	}
	else
	{
		Impulse = FMath::Min(1.0, Impulse + X);
	}
	Trauma = FMath::Max(Impulse, Sustained);
}

void FMIShake::AtLeast(double X)
{
	if (X > Impulse)
	{
		Impulse = FMath::Min(1.0, X);
	}
	Trauma = FMath::Max(Impulse, Sustained);
}

void FMIShake::Update(const FMIPlayerShakeData& Tune, double Dt)
{
	using namespace MIPlayerRulesPrivate;
	Time += Dt;
	Impulse = FMath::Max(0.0, Impulse - Tune.Decay * Dt);
	const double Level = Dt > 0.0 ? FMath::Min(Tune.SustainMax, Trickle / Dt / Tune.Decay) : 0.0;
	Trickle = 0.0;
	Sustained = MI::Damp(Sustained, Level, Tune.SustainRate, Dt);
	if (Sustained < SustainFloor)
	{
		Sustained = 0.0;
	}
	Trauma = FMath::Max(Impulse, Sustained);
	const double Power = Trauma * Trauma;
	if (Power == 0.0)
	{
		Pitch = Yaw = Roll = 0.0;
		return;
	}
	const double S = Time;
	// Web yaw and roll grow to the left: Unreal's to the right.
	Pitch = Tune.Pitch * Power * (FMath::Sin(S * Tune.FreqPitch[0]) + FMath::Sin(S * Tune.FreqPitch[1] + ShakePhasePitch));
	Yaw = -Tune.Yaw * Power * (FMath::Sin(S * Tune.FreqYaw[0] + ShakePhaseYaw[0]) + FMath::Sin(S * Tune.FreqYaw[1] + ShakePhaseYaw[1]));
	Roll = -Tune.Roll * Power * (FMath::Sin(S * Tune.FreqRoll[0] + ShakePhaseRoll[0]) + FMath::Sin(S * Tune.FreqRoll[1] + ShakePhaseRoll[1]));
}

void FMIClampedSpring::Update(double Dt, double Stiffness, double Damping, double Min, double Max)
{
	double Left = Dt;
	while (Left > 1e-7)
	{
		const double H = FMath::Min(Left, MIPlayerRulesPrivate::SpringStep);
		Left -= H;
		Velocity += (-Stiffness * Offset - Damping * Velocity) * H;
		Offset += Velocity * H;
		if (Offset < Min)
		{
			Offset = Min;
			if (Velocity < 0.0)
			{
				Velocity = 0.0;
			}
		}
		else if (Offset > Max)
		{
			Offset = Max;
			if (Velocity > 0.0)
			{
				Velocity = 0.0;
			}
		}
	}
}

// ------------------------------------------------------------------------------------------------- the player

void FMIPlayerRules::Init(const FMIPlayerData& InTuning, FMIGameEvents* InEvents)
{
	T = InTuning;
	Events = InEvents;
	MaxHealth = T.Health.Max;
	RegenDelay = T.Health.RegenDelay;
	RegenRate = T.Health.RegenRate;
	BaseFov = T.Fov.Base;
	Reset(Feet, Yaw);
}

void FMIPlayerRules::Reset(const FVector& InFeet, double InYaw)
{
	Feet = InFeet;
	Velocity = FVector::ZeroVector;
	Yaw = InYaw;
	Pitch = 0.0;
	Health = MaxHealth;
	bAlive = true;
	bOnGround = true;
	bSprinting = false;
	bCrouching = false;
	Speed = 0.0;
	Ads = 0.0;
	bInvulnerable = false;
	EyeHeight = EyeAtDeath = T.Body.Eye;
	Coyote = JumpBuffer = AirTime = FallSpeed = 0.0;
	StridePhase = BobAmp = StrafeRoll = 0.0;
	BobX = BobY = ViewPitch = ViewRoll = 0.0;
	SinceHit = 1e30;
	Hurt = Blast = LowHealth = DeadTime = 0.0;
	DeathSide = 1.0;
	ViewFov = BaseFov;
	Recoil.Reset();
	Shake.Reset();
	Spring.Reset();
	StepLag.Reset();
	bWasGrounded = true;
	bJumpedThisFrame = bWantSprint = bDeadMove = false;
	PlaceView();
}

FVector FMIPlayerRules::RightOf(double YawDeg) const
{
	const double R = MI::DegToRad(YawDeg);
	return FVector(-FMath::Sin(R), FMath::Cos(R), 0.0);
}

void FMIPlayerRules::Damage(double Amount, const TOptional<FVector>& From, EMIDamageKind Kind)
{
	if (!bAlive || bInvulnerable || !(Amount > 0.0) || !FMath::IsFinite(Amount))
	{
		return;
	}
	Health = FMath::Max(0.0, Health - Amount);
	SinceHit = 0.0;
	Hurt = FMath::Min(1.0, Hurt + T.Health.HurtBase + Amount * T.Health.HurtPerDamage);
	Shake.Add(T.Shake, T.Shake.OnHitBase + Amount * T.Shake.OnHitPerDamage);
	if (Events)
	{
		FMIPlayerHitEvent Event;
		Event.Amount = Amount;
		Event.From = From;
		Event.Health = Health;
		Event.Kind = Kind;
		Events->PlayerHit.Broadcast(Event);
	}
	if (Health <= 0.0)
	{
		Die(From);
	}
}

void FMIPlayerRules::Die(const TOptional<FVector>& From)
{
	bAlive = false;
	bSprinting = false;
	DeadTime = 0.0;
	EyeAtDeath = EyeHeight;
	// Fall away from whatever hit: a shot from the left drops the camera onto its right shoulder.
	DeathSide = 1.0;
	if (From.IsSet())
	{
		const FVector ToFrom = From.GetValue() - Feet;
		const FVector Right = RightOf(Yaw);
		if (ToFrom.X * Right.X + ToFrom.Y * Right.Y < 0.0)
		{
			DeathSide = -1.0;
		}
	}
	if (Events)
	{
		Events->PlayerDead.Broadcast(From);
	}
}

void FMIPlayerRules::Heal(double Amount)
{
	if (bAlive && Amount > 0.0 && FMath::IsFinite(Amount))
	{
		Health = FMath::Min(MaxHealth, Health + Amount);
	}
}

void FMIPlayerRules::AddRecoil(double PitchDeg, double YawDeg)
{
	if (!FMath::IsFinite(PitchDeg) || !FMath::IsFinite(YawDeg))
	{
		return;
	}
	Pitch = FMath::Clamp(Pitch + PitchDeg * T.Recoil.Keep, -T.Look.PitchLimit, T.Look.PitchLimit);
	Yaw = MI::WrapDegrees(Yaw + YawDeg * T.Recoil.Keep);
	Recoil.Kick(T.Recoil, PitchDeg, YawDeg);
	// The weapon runs after the player: refresh the aim so that a second round of the same frame carries the kick.
	if (bAlive)
	{
		PlaceView();
	}
}

void FMIPlayerRules::AddShake(double Trauma)
{
	if (FMath::IsFinite(Trauma))
	{
		Shake.Add(T.Shake, Trauma);
	}
}

void FMIPlayerRules::SetFov(double VerticalDegrees)
{
	if (FMath::IsFinite(VerticalDegrees))
	{
		BaseFov = FMath::Clamp(VerticalDegrees, T.Fov.Min, T.Fov.Max);
	}
}

void FMIPlayerRules::OnExplosion(const FVector& Position, bool bBig)
{
	const double Near = 1.0 - FVector::Dist(Eye, Position) / T.Shake.BlastRange;
	if (Near > 0.0)
	{
		Blast = FMath::Max(Blast, (T.Shake.BlastBase + T.Shake.BlastScale * Near * Near) * (bBig ? 1.0 : T.Shake.BlastSmall));
	}
}

FMIBodyMove FMIPlayerRules::BeginFrame(double Dt, const FMIPlayerInputFrame& Input, TFunctionRef<bool()> CanStand)
{
	FMIBodyMove Move;
	bDeadMove = false;
	if (!(Dt > 0.0))
	{
		return Move;
	}
	Hurt = FMath::Max(0.0, Hurt - T.Health.HurtDecay * Dt);
	if (Blast > 0.0)
	{
		Shake.AtLeast(Blast);
		Blast = 0.0;
	}

	if (!bEnabled)
	{
		// Something else owns the camera: only the screen feedback keeps settling.
		Shake.Update(T.Shake, Dt);
		EaseLowHealth(Dt);
		return Move;
	}

	if (!bAlive)
	{
		// The body keeps falling and slides to rest.
		DeadTime += Dt;
		Velocity.X = MI::ExpDecay(Velocity.X, T.Death.Slide, Dt);
		Velocity.Y = MI::ExpDecay(Velocity.Y, T.Death.Slide, Dt);
		Velocity.Z = FMath::Max(Velocity.Z - T.Jump.Gravity * Dt, -T.Jump.Terminal);
		Move.bMove = true;
		Move.bDead = true;
		Move.Velocity = Velocity;
		Move.Height = T.Death.CapsuleHeight;
		Move.bAllowStep = bOnGround;
		bDeadMove = true;
		return Move;
	}

	double MX = Input.Move.X;
	double MY = Input.Move.Y;
	const double Push = MX * MX + MY * MY;
	if (!(Push <= 1.0))
	{
		const double K = Push > 1.0 ? 1.0 / FMath::Sqrt(Push) : 0.0;
		MX *= K;
		MY *= K;
	}

	// Look. Aiming slows every device alike.
	if (FMath::IsFinite(Input.LookDegrees.X) && FMath::IsFinite(Input.LookDegrees.Y))
	{
		const double K = MI::Lerp(1.0, T.Look.AdsScale, MI::Clamp01(Ads));
		Yaw = MI::WrapDegrees(Yaw + Input.LookDegrees.X * K);
		Pitch = FMath::Clamp(Pitch - Input.LookDegrees.Y * K, -T.Look.PitchLimit, T.Look.PitchLimit);
	}

	// Crouch is a hold; standing back up waits for headroom.
	if (Input.bCrouchHeld)
	{
		bCrouching = true;
	}
	else if (bCrouching && CanStand())
	{
		bCrouching = false;
	}

	// Jump: a press is remembered for a moment, and so is the ground after walking off a ledge.
	bWasGrounded = bOnGround;
	Coyote = bWasGrounded ? T.Jump.Coyote : Coyote - Dt;
	JumpBuffer = Input.bJumpPressed ? T.Jump.Buffer : JumpBuffer - Dt;
	bJumpedThisFrame = false;
	if (JumpBuffer > 0.0 && Coyote > 0.0 && (!bCrouching || CanStand()))
	{
		bCrouching = false;
		Velocity.Z = T.Jump.LaunchSpeed();
		JumpBuffer = Coyote = 0.0;
		bJumpedThisFrame = true;
		if (Events)
		{
			Events->PlayerJump.Broadcast();
		}
	}

	// Velocity moves straight toward the wish velocity at a constant rate.
	bWantSprint = MIPlayerRules::SprintWanted(T.Sprint, Input.bSprintHeld, MY, MX, bCrouching, Ads, Input.bFireHeld);
	const double Target = MIPlayerRules::TargetSpeed(T.Speed, bCrouching, bWantSprint, Ads, MY);
	const double YawRad = MI::DegToRad(Yaw);
	const double Cos = FMath::Cos(YawRad);
	const double Sin = FMath::Sin(YawRad);
	const bool bHasInput = MX != 0.0 || MY != 0.0;
	// Forward (cos, sin), right (-sin, cos).
	const double WishX = bHasInput ? (-Sin * MX + Cos * MY) * Target : 0.0;
	const double WishY = bHasInput ? (Cos * MX + Sin * MY) * Target : 0.0;
	const double Rate = bWasGrounded ? (bHasInput ? T.Accel.Ground : T.Accel.GroundStop) : (bHasInput ? T.Accel.Air : T.Accel.AirStop);
	double VX = Velocity.X;
	double VY = Velocity.Y;
	MIPlayerRules::ApproachVelocity(VX, VY, WishX, WishY, Rate, Dt, bWasGrounded || bHasInput);
	Velocity.X = VX;
	Velocity.Y = VY;

	// The fastest descent is read after the first half of this frame's gravity (the web game's sample point).
	const double HalfStep = FMath::Max(Velocity.Z - T.Jump.Gravity * Dt * 0.5, -T.Jump.Terminal);
	if (!bWasGrounded)
	{
		FallSpeed = FMath::Max(FallSpeed, -HalfStep);
	}
	FeetBefore = Feet.Z;

	Move.bMove = true;
	Move.Velocity = Velocity;
	Move.Height = bCrouching ? T.Body.CrouchHeight : T.Body.Height;
	Move.bAllowStep = bWasGrounded && !bJumpedThisFrame;
	Move.bJumped = bJumpedThisFrame;
	return Move;
}

void FMIPlayerRules::EndFrame(double Dt, const FMIBodyResult& Body)
{
	if (!(Dt > 0.0) || !bEnabled)
	{
		return;
	}
	if (bDeadMove)
	{
		Feet = Body.Feet;
		Velocity = Body.Velocity;
		bOnGround = Body.bOnGround;
		Speed = FMath::Sqrt(Velocity.X * Velocity.X + Velocity.Y * Velocity.Y);
		Recoil.Update(T.Recoil, Dt);
		Shake.Update(T.Shake, Dt);
		Spring.Update(Dt, T.Bob.SpringStiffness, T.Bob.SpringDamping, T.Bob.SpringMin, T.Bob.SpringMax);
		StepLag.Update(Dt, T.Bob.StepFrequency * T.Bob.StepFrequency, 2.0 * T.Bob.StepFrequency, -T.Bob.StepMax, T.Bob.StepMax);
		DeadView(Dt);
		return;
	}
	if (!bAlive)
	{
		return;
	}

	Feet = Body.Feet;
	Velocity = Body.Velocity;
	if (!Body.Surface.IsNone())
	{
		Surface = Body.Surface;
	}
	bOnGround = Body.bOnGround;
	Speed = FMath::Sqrt(Velocity.X * Velocity.X + Velocity.Y * Velocity.Y);
	const double SprintSpeed = T.Speed.Walk * T.Sprint.MinSpeedFrac;
	bSprinting = bWantSprint && (bOnGround ? Speed > SprintSpeed : bSprinting);

	if (bOnGround)
	{
		if (!bWasGrounded && AirTime > T.Fall.LandMinAir)
		{
			Land(FallSpeed);
		}
		AirTime = 0.0;
		FallSpeed = 0.0;
	}
	else
	{
		AirTime += Dt;
	}

	// Stairs and kerbs: the body pops by the step, the eye catches up.
	if (T.Bob.StepFrequency > 0.0)
	{
		const double Popped = Feet.Z - FeetBefore;
		if (bWasGrounded && bOnGround && !bJumpedThisFrame && Popped != 0.0)
		{
			StepLag.Offset = FMath::Clamp(StepLag.Offset - Popped, -T.Bob.StepMax, T.Bob.StepMax);
		}
		StepLag.Update(Dt, T.Bob.StepFrequency * T.Bob.StepFrequency, 2.0 * T.Bob.StepFrequency, -T.Bob.StepMax, T.Bob.StepMax);
	}

	if (bAlive)
	{
		UpdateStride(Dt);
	}
	UpdateHealth(Dt);

	EyeHeight = MI::Damp(EyeHeight, bCrouching ? T.Body.CrouchEye : T.Body.Eye, T.Body.EyeRate, Dt);
	const double A = MI::Clamp01(Ads);
	const double FovTarget = MI::Lerp(BaseFov + (bSprinting ? T.Fov.SprintAdd : 0.0), T.Fov.Ads, A);
	const bool bAiming = A > T.Fov.AdsBandLow && A < T.Fov.AdsBandHigh;
	ViewFov = MI::Damp(ViewFov, FovTarget, bAiming ? T.Fov.RateAds : T.Fov.Rate, Dt);

	Recoil.Update(T.Recoil, Dt);
	Shake.Update(T.Shake, Dt);
	Spring.Update(Dt, T.Bob.SpringStiffness, T.Bob.SpringDamping, T.Bob.SpringMin, T.Bob.SpringMax);

	// Lean into strafes (moving right tilts right); the sideways bob rolls the view a touch the other way.
	const FVector Right = RightOf(Yaw);
	const double Lateral = Velocity.X * Right.X + Velocity.Y * Right.Y;
	const double Lean = (Lateral / T.Speed.Sprint) * T.Bob.StrafeRoll * MI::Lerp(1.0, T.Bob.StrafeRollAds, A);
	StrafeRoll = MI::Damp(StrafeRoll, Lean, T.Bob.StrafeRollRate, Dt);
	ViewPitch = Spring.Offset * T.Bob.SpringPitch;
	ViewRoll = StrafeRoll - BobX * T.Bob.RollFromLateral;

	if (bAlive)
	{
		PlaceView();
	}
	else
	{
		DeadView(0.0);  // the fall that killed: the death view starts on the same frame
	}
}

void FMIPlayerRules::Land(double LandSpeed)
{
	if (Events)
	{
		FMIPlayerLandEvent Event;
		Event.Speed = LandSpeed;
		Event.Surface = Surface;
		Events->PlayerLand.Broadcast(Event);
	}
	Spring.Kick(-FMath::Min(LandSpeed * T.Fall.DipPerSpeed, T.Fall.DipMax));
	if (LandSpeed > T.Fall.ShakeFrom)
	{
		Shake.Add(T.Shake, FMath::Min(T.Fall.ShakeMax, (LandSpeed - T.Fall.ShakeFrom) * T.Fall.ShakePerSpeed));
	}
	// A footstep follows the landing shortly.
	StridePhase = FMath::FloorToDouble(StridePhase) + T.Stride.AfterLanding;
	if (LandSpeed > T.Fall.DamageFrom)
	{
		Damage((LandSpeed - T.Fall.DamageFrom) * T.Fall.DamagePerSpeed, TOptional<FVector>(), EMIDamageKind::Fall);
	}
}

void FMIPlayerRules::UpdateStride(double Dt)
{
	const bool bWalking = bOnGround && Speed > T.Speed.Moving;
	if (bWalking)
	{
		const double Length = bCrouching ? T.Stride.Crouch : (bSprinting ? T.Stride.Sprint : T.Stride.Walk);
		const double Before = FMath::FloorToDouble(StridePhase);
		StridePhase += (Speed * Dt) / Length;
		if (FMath::FloorToDouble(StridePhase) > Before && Events)
		{
			FMIPlayerStepEvent Event;
			Event.Position = Feet;
			Event.Surface = Surface;
			Event.bSprint = bSprinting;
			Events->PlayerStep.Broadcast(Event);
		}
	}
	else if (bOnGround)
	{
		// Standing still: both feet come to rest on a footfall (JavaScript Math.round: halves round up).
		const double Rest = FMath::FloorToDouble(StridePhase + 0.5);
		StridePhase = FMath::Abs(Rest - StridePhase) < 0.02 ? Rest : MI::Damp(StridePhase, Rest, T.Stride.SettleRate, Dt);
	}
	if (StridePhase >= 2.0)
	{
		StridePhase -= 2.0;
	}

	const double A = MI::Clamp01(Ads);
	const double Amp = bOnGround
		? MI::Clamp01(Speed / T.Speed.Walk) * (bSprinting ? T.Bob.SprintScale : 1.0) * MI::Lerp(1.0, T.Bob.AdsScale, A) * (bCrouching ? T.Bob.CrouchScale : 1.0)
		: 0.0;
	BobAmp = MI::Damp(BobAmp, Amp, T.Bob.Rate, Dt);
	BobY = -FMath::Cos(UE_DOUBLE_TWO_PI * StridePhase) * T.Bob.Vertical * BobAmp;
	BobX = FMath::Sin(UE_DOUBLE_PI * StridePhase) * T.Bob.Lateral * BobAmp;
}

void FMIPlayerRules::EaseLowHealth(double Dt)
{
	const double Target = bAlive ? 1.0 - MI::SmoothStep(T.Health.LowTo, T.Health.LowFrom, Health / MaxHealth) : 1.0;
	LowHealth = MI::Damp(LowHealth, Target, T.Health.LowRate, Dt);
}

void FMIPlayerRules::UpdateHealth(double Dt)
{
	SinceHit += Dt;
	if (bAlive && Health < MaxHealth && SinceHit >= RegenDelay)
	{
		Health = FMath::Min(MaxHealth, Health + RegenRate * Dt);
	}
	EaseLowHealth(Dt);
}

void FMIPlayerRules::DeadView(double Dt)
{
	const double S = MI::SmoothStep(0.0, T.Death.Collapse, DeadTime);
	EyeHeight = MI::Damp(EyeHeight, MI::Lerp(EyeAtDeath, T.Death.Eye, S * S), T.Death.EyeRate, Dt);
	BobAmp = MI::Damp(BobAmp, 0.0, T.Bob.Rate, Dt);
	BobY = -FMath::Cos(UE_DOUBLE_TWO_PI * StridePhase) * T.Bob.Vertical * BobAmp;
	BobX = FMath::Sin(UE_DOUBLE_PI * StridePhase) * T.Bob.Lateral * BobAmp;
	StrafeRoll = MI::Damp(StrafeRoll, 0.0, T.Bob.StrafeRollRate, Dt);
	ViewFov = MI::Damp(ViewFov, BaseFov, T.Fov.Rate, Dt);
	ViewPitch = T.Death.Pitch * S + T.Death.PitchBounce * FMath::Sin(UE_DOUBLE_PI * S) + Spring.Offset * T.Bob.SpringPitch;
	// DeathSide +1: onto the left shoulder (web positive roll), which is a negative Unreal roll.
	ViewRoll = -DeathSide * T.Death.Roll * S * S + StrafeRoll;
	LowHealth = 1.0;
	PlaceView();
}

void FMIPlayerRules::PlaceView()
{
	const double AimYaw = GetAimYaw();
	const double AimPitch = GetAimPitch();
	const double PitchRad = MI::DegToRad(AimPitch);
	const double YawRad = MI::DegToRad(AimYaw);
	const double CP = FMath::Cos(PitchRad);
	Forward = FVector(CP * FMath::Cos(YawRad), CP * FMath::Sin(YawRad), FMath::Sin(PitchRad));

	// Bob and the landing spring may lift the eye only as far as the body has headroom for.
	const double Headroom = (bCrouching ? T.Body.CrouchHeight - T.Body.CrouchEye : T.Body.Height - T.Body.Eye) - T.Body.HeadClearance;
	const double Lift = EyeHeight + FMath::Min(BobY + Spring.Offset, Headroom) + StepLag.Offset;
	const FVector Right(-FMath::Sin(YawRad), FMath::Cos(YawRad), 0.0);
	Eye = Feet + Right * BobX + FVector(0.0, 0.0, Lift);

	if (!bEnabled)
	{
		return;
	}
	CameraRotation = FRotator(AimPitch + ViewPitch + Shake.Pitch, AimYaw + Shake.Yaw, ViewRoll + Shake.Roll);
}
