#pragma once

#include "CoreMinimal.h"
#include "Core/Data/MIData.h"
#include "Core/MIEvents.h"
#include "Core/MIMath.h"

/**
 * The weapon rules of the web game (src/weapon/logic.js), ported as written: a tick with accumulators, not timers.
 * Ammunition, the trigger (catch-up rounds and the 1 ms credit), spread and bloom, camera recoil, aiming, reloads
 * with their marks, switching with reversal, melee, the sprint-lowered blend, the wall probe and the pad aim
 * slow-down. Owns nothing on screen; the host (UMIWeaponComponent, or a test) answers the few questions the rules ask.
 *
 * Units: cm, degrees, seconds. Kicks: pitch up, yaw right (Unreal signs).
 */

/** What the rules read of the player every frame (G.player). */
struct FMIWeaponPlayerState
{
	bool bAlive = true;
	bool bSprinting = false;
	bool bCrouching = false;
	bool bOnGround = true;
	double Speed = 0.0;  // horizontal cm/s
	FVector Eye = FVector::ZeroVector;
	FVector Forward = FVector::ForwardVector;  // aim with the recoil offset
	FVector Velocity = FVector::ZeroVector;
};

/** One frame of weapon input. */
struct FMIWeaponInput
{
	bool bFireDown = false;
	bool bFirePressed = false;
	bool bAdsDown = false;
	bool bSwapPressed = false;
	bool bWeapon1Pressed = false;
	bool bWeapon2Pressed = false;
	bool bMeleePressed = false;
	bool bReloadPressed = false;
	bool bPadActive = false;  // the gamepad is the active device (aim slow-down)
	// LOADOUT.md 4.2: four guns. All default to off, so the golden harness is unchanged.
	bool bWeapon3Pressed = false;
	bool bWeapon4Pressed = false;
	bool bNextPressed = false;      // mouse wheel down, D-pad up
	bool bPreviousPressed = false;  // mouse wheel up, D-pad down
	int32 WheelPick = INDEX_NONE;   // the gun chosen on the weapon wheel this frame
	bool bFireModePressed = false;  // the selector (B, View tap)
};

struct FMIShotRequest
{
	FVector Origin = FVector::ZeroVector;
	FVector Direction = FVector::ForwardVector;
	double Range = 0.0;
	double Damage = 0.0;
	double HeadMultiplier = 1.0;
	FName Weapon;
	// LOADOUT.md 4.5: damage x 1 up to FalloffStart (cm), linear to FalloffMin at FalloffEnd, FalloffMin beyond.
	double FalloffStart = TNumericLimits<double>::Max();
	double FalloffEnd = TNumericLimits<double>::Max();
	double FalloffMin = 1.0;
	double NoiseRadius = 0.0;  // cm
	bool bSuppressed = false;

	/** Damage at Distance cm: the branch is skipped while Distance <= FalloffStart, so no factor of 1 is computed. */
	double DamageAt(double Distance) const
	{
		if (!(Distance > FalloffStart))
		{
			return Damage;
		}
		if (!(FalloffEnd > FalloffStart) || Distance >= FalloffEnd)
		{
			return Damage * FalloffMin;
		}
		return Damage * (1.0 + (FalloffMin - 1.0) * (Distance - FalloffStart) / (FalloffEnd - FalloffStart));
	}
};

struct FMIShotResult
{
	bool bHit = false;
	double Distance = 0.0;
	FVector Point = FVector::ZeroVector;
};

enum class EMIStrikeResult : uint8
{
	None,
	World,
	Enemy
};

struct FMIStrikeRequest
{
	FVector Origin = FVector::ZeroVector;
	FVector Direction = FVector::ForwardVector;
	double Reach = 0.0;
	double ConeDegrees = 0.0;  // full apex angle
	double Damage = 0.0;
};

/** The questions the rules ask the world, and the player calls they make. */
class IMIWeaponHost
{
public:
	virtual ~IMIWeaponHost() = default;
	/** Read again before every round: a kick moves the aim of the next catch-up round. */
	virtual FMIWeaponPlayerState GetPlayerState() const = 0;
	virtual void SetPlayerAds(double Ads) = 0;
	/** The gun in hand's aimed field of view (vertical degrees) and aimed look factor, every frame (LOADOUT.md 4.5). */
	virtual void SetPlayerAimView(double AdsFov, double AdsLook) {}
	virtual void AddRecoil(double PitchDeg, double YawDeg) = 0;
	virtual void AddShake(double Trauma) = 0;
	virtual FMIShotResult Hitscan(const FMIShotRequest& Shot) = 0;
	virtual EMIStrikeResult Melee(const FMIStrikeRequest& Strike) = 0;
	/** Distance to the first wall along the ray within MaxDistance, or a negative number when clear. */
	virtual double ProbeWall(const FVector& Origin, const FVector& Direction, double MaxDistance) = 0;
	/** An unoccluded enemy under the ray within Range (pad aim slow-down). */
	virtual bool AimTarget(const FVector& Origin, const FVector& Direction, double Range) = 0;
	/** A round left: tracer, flash, casing, light. Result is what the hitscan answered. */
	virtual void OnRoundFired(const FMIShotRequest& Shot, const FMIShotResult& Result, double FlashScale) {}
	virtual void OnDry() {}
	virtual void Rumble(double Strong, double Weak, double Ms) {}
};

enum class EMIWeaponActivity : uint8
{
	Ready,
	Reloading,
	Holstering,
	Drawing,
	Striking,
	Dropped,
	Selector   // the fire selector moving (LOADOUT.md 4.4)
};

/** What a presentation layer reads of the rules each frame (spec 02 2.12): state, never internals to write. */
struct FMIWeaponView
{
	FName Weapon;
	EMIWeaponActivity Activity = EMIWeaponActivity::Ready;
	double ActivityTime = 0.0;    // s since the reload, holster, draw or strike began
	double ActivityLength = 0.0;  // s it lasts (progress = time / length)
	FName ReloadStage;            // the last reload mark passed: start, magout, magin, bolt
	bool bReloadEmpty = false;
	bool bTrigger = false;        // trigger held and allowed to fire
	int32 Mag = 0;
	int32 MagSize = 0;
	double Ads = 0.0;
	double SprintBlend = 0.0;
	double Wall = 0.0;
	double Spread = 0.0;          // degrees
	double SinceShot = 0.0;       // s
	int32 Burst = 0;
};

class MURDERINC_API FMIWeaponRules
{
public:
	/** Seed: the run's seed; the rules draw from its "weapon" fork as the web game does. */
	void Init(const FMIWeaponsData& InData, uint32 Seed, FMIGameEvents* InEvents);
	void SetEvents(FMIGameEvents* InEvents) { Events = InEvents; }

	/** Full magazines, start reserve, the first gun in hand, every timer cleared. */
	void Reset();
	/** Resupply: tops up every finite reserve to at most Cap. */
	void AddReserve(double Rounds, double Cap);
	/** The gun leaves the hands (death). */
	void Drop();
	void Update(double Dt, const FMIWeaponInput& Input, IMIWeaponHost& Host);

	// --- public state (spec 02 2.12) ------------------------------------------------------------------
	const FMIWeaponDef& GetDef() const { return Data.Guns[Current]; }
	int32 GetCurrentIndex() const { return Current; }
	FName GetCurrentId() const { return GetDef().Id; }
	int32 GetMag() const { return Ammo[Current].Mag; }
	double GetReserve() const { return Pools[Ammo[Current].Pool]; }
	/** The gun last put away (the quick swap's target); with two guns, the other one. */
	int32 GetOtherIndex() const { return LastUsed; }
	int32 GetLastUsed() const { return LastUsed; }
	int32 GetMagOf(int32 Gun) const { return Ammo[Gun].Mag; }
	double GetReserveOf(int32 Gun) const { return Pools[Ammo[Gun].Pool]; }
	int32 NumGuns() const { return Data.Guns.Num(); }
	/** The shared bag of rounds (LOADOUT.md 3.2.3): the first finite pool, or a negative number when none. */
	double GetBag() const;
	bool IsSemi(int32 Gun) const { return SemiMode.IsValidIndex(Gun) && SemiMode[Gun]; }
	bool HasTwoModes(int32 Gun) const { return Data.Guns.IsValidIndex(Gun) && Data.Guns[Gun].HasFireMode(TEXT("auto")) && Data.Guns[Gun].HasFireMode(TEXT("semi")); }
	double HolsterOf(int32 Gun) const;
	double DrawOf(int32 Gun) const;
	/** The gun the holster is heading to (Swap.To), or the gun in hand. */
	int32 GetAimIndex() const { return Swap.bActive && Swap.bHolster ? Swap.To : Current; }
	/** idle, firing, reloading, switching, melee, lowered */
	FName GetState() const;
	/** empty string, reloading, low, reload, empty */
	FName GetCue() const;
	double Spread = 0.0;  // degrees, the cone half-angle in use (HUD crosshair gap)
	double GetAds() const { return AdsValue; }
	double GetAdsLinear() const { return AdsLinear; }
	double GetSprintBlend() const { return SprintBlend.X; }
	double GetWall() const { return Wall; }
	double GetHeat() const { return Heat; }
	double GetAimSlow() const { return AimSlow; }
	EMIWeaponActivity GetActivity() const;
	double GetActivityTime() const;
	FMIWeaponView GetView() const;
	bool IsDropped() const { return bDropped; }
	const FMIWeaponsData& GetData() const { return Data; }

private:
	struct FAmmo
	{
		int32 Mag = 0;
		int32 Pool = 0;  // index into Pools: one finite pool (the bag) for every finite gun, one infinite per other gun
	};
	struct FMark
	{
		double T = 0.0;
		FName Phase;
	};
	struct FReload
	{
		bool bActive = false;
		double T = 0.0;
		bool bEmpty = false;
		int32 Next = 0;
	};
	struct FSwap
	{
		bool bActive = false;
		bool bHolster = true;
		double T = 0.0;
		int32 To = 0;
	};
	struct FStrike
	{
		bool bActive = false;
		double T = 0.0;
		bool bLanded = false;
	};

	int32 OtherOf(int32 Gun) const { return (Gun + 1) % Data.Guns.Num(); }
	bool Busy() const { return Reload.bActive || Swap.bActive || Strike.bActive || Selector.bActive; }
	double& PoolOf(int32 Gun) { return Pools[Ammo[Gun].Pool]; }
	const TArray<FMark>& Marks(int32 Gun, bool bEmpty) const { return Timelines[Gun * 2 + (bEmpty ? 1 : 0)]; }
	double Random() { return Rng.Next(); }
	double Signed() { return Random() * 2.0 - 1.0; }

	void Settle();
	void Equip(int32 Gun);
	void ReloadEvent(FName Phase, bool bEmpty);
	bool StartReload();
	void CancelReload();
	void AdvanceReload(double Dt);
	void SwitchEvent(int32 From, int32 To, bool bHolster);
	void CancelSelector();
	void AdvanceSelector(double Dt);
	void RequestSwitch(int32 Gun);
	void AdvanceSwitch(double Dt);
	void StartStrike();
	void AdvanceStrike(double Dt, IMIWeaponHost& Host);
	void Shoot(IMIWeaponHost& Host);
	void DryFire(IMIWeaponHost& Host);
	void PullTrigger(const FMIWeaponInput& Input, IMIWeaponHost& Host);
	void ProbeWall(double Dt, const FMIWeaponPlayerState& Player, IMIWeaponHost& Host);
	void AssistAim(double Dt, const FMIWeaponInput& Input, const FMIWeaponPlayerState& Player, IMIWeaponHost& Host);
	void SetAim(IMIWeaponHost& Host, bool bWant, double Dt);

	FMIWeaponsData Data;
	FMIGameEvents* Events = nullptr;
	FMIRng Rng;
	TArray<TArray<FMark>> Timelines;
	TArray<FAmmo> Ammo;
	TArray<double> Pools;
	TArray<bool> SemiMode;
	int32 LastUsed = 0;
	struct FSelector
	{
		bool bActive = false;
		double T = 0.0;
	} Selector;
	bool bReloadAfterSelector = false;

	int32 Current = 0;
	double Cooldown = 0.0;
	double SinceShot = 1e30;
	int32 Burst = 0;
	double WeavePhase = 0.0;
	double Bloom = 0.0;
	double Heat = 0.0;
	double FireBuffer = 0.0;
	bool bDryLatch = false;
	bool bTriggerHeld = false;
	bool bSustained = false;
	double AutoReload = 0.0;
	double AdsLinear = 0.0;
	double AdsValue = 0.0;
	FMIExactSpring SprintBlend;
	double Wall = 0.0;
	double WallTarget = 0.0;
	double WallTimer = 0.0;
	FReload Reload;
	FSwap Swap;
	FStrike Strike;
	double StrikeWait = 0.0;
	int32 QueuedSwap = INDEX_NONE;
	bool bDropped = false;
	double AimTimer = 0.0;
	double AimTargetValue = 1.0;
	double AimSlow = 1.0;
};
