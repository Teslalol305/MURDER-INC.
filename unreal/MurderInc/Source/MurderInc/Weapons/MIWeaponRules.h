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
};

struct FMIShotRequest
{
	FVector Origin = FVector::ZeroVector;
	FVector Direction = FVector::ForwardVector;
	double Range = 0.0;
	double Damage = 0.0;
	double HeadMultiplier = 1.0;
	FName Weapon;
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
	Dropped
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
	double GetReserve() const { return Ammo[Current].Reserve; }
	int32 GetOtherIndex() const { return OtherOf(Current); }
	int32 GetMagOf(int32 Gun) const { return Ammo[Gun].Mag; }
	double GetReserveOf(int32 Gun) const { return Ammo[Gun].Reserve; }
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
	bool IsDropped() const { return bDropped; }
	const FMIWeaponsData& GetData() const { return Data; }

private:
	struct FAmmo
	{
		int32 Mag = 0;
		double Reserve = 0.0;
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
	bool Busy() const { return Reload.bActive || Swap.bActive || Strike.bActive; }
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

	int32 Current = 0;
	double Cooldown = 0.0;
	double SinceShot = 1e30;
	int32 Burst = 0;
	double WeavePhase = 0.0;
	double Bloom = 0.0;
	double Heat = 0.0;
	double FireBuffer = 0.0;
	bool bDryLatch = false;
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
