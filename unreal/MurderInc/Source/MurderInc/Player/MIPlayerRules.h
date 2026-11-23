#pragma once

#include "CoreMinimal.h"
#include "Core/Data/MIData.h"
#include "Core/MIEvents.h"

/**
 * The web game's player (src/player.js) as plain C++: every decision about movement, health and the view, without
 * the body move itself. The character movement component (UMICharacterMovement) moves the body between
 * BeginFrame and EndFrame; the automation tests move it with the web game's flat-ground rule instead and compare
 * every frame with the golden vectors of tools/ue-export/golden.mjs.
 *
 * Units: centimetres, cm/s, degrees. Signs are Unreal's: yaw 0 looks along +X and grows turning right, pitch grows
 * looking up, positive roll tilts the head to the right. Kicks: pitch up, yaw right.
 */

namespace MIPlayerRules
{
	/** The ground speed the player is trying to reach (cm/s). Forward is the forward input -1..1. */
	MURDERINC_API double TargetSpeed(const FMIPlayerSpeedData& Speeds, bool bCrouching, bool bSprinting, double Ads, double Forward);

	/** Sprint wanted: held, pushing forward, not strafing hard, standing, not aiming, not firing. */
	MURDERINC_API bool SprintWanted(const FMIPlayerSprintData& Rules, bool bHeld, double Forward, double Strafe, bool bCrouching, double Ads, bool bFiring);

	/** Moves (VX, VY) straight toward the wish velocity by at most Rate * Dt; snaps when closer if bSnap. */
	MURDERINC_API void ApproachVelocity(double& VX, double& VY, double WishX, double WishY, double Rate, double Dt, bool bSnap);
}

/** The recoverable share of the camera recoil (createRecoil). Degrees, Unreal signs. */
struct MURDERINC_API FMIRecoil
{
	double Pitch = 0.0;
	double Yaw = 0.0;
	double TargetPitch = 0.0;
	double TargetYaw = 0.0;
	double SinceKick = 1e30;

	void Kick(const FMIPlayerRecoilData& Tune, double PitchDeg, double YawDeg);
	void Update(const FMIPlayerRecoilData& Tune, double Dt);
	void Reset() { *this = FMIRecoil(); }
};

/** Trauma screen shake (createShake): trauma^2 times two sines per axis. Degrees, Unreal signs. */
struct MURDERINC_API FMIShake
{
	double Trauma = 0.0;
	double Time = 0.0;
	double Pitch = 0.0;
	double Yaw = 0.0;
	double Roll = 0.0;
	double Trickle = 0.0;
	double Sustained = 0.0;
	double Impulse = 0.0;

	void Add(const FMIPlayerShakeData& Tune, double X);
	void AtLeast(double X);
	void Update(const FMIPlayerShakeData& Tune, double Dt);
	void Reset() { *this = FMIShake(); }
};

/** The landing dip and the stair glide (createSpring): a damped spring held inside [Min, Max], 1/120 s sub-steps. */
struct MURDERINC_API FMIClampedSpring
{
	double Offset = 0.0;
	double Velocity = 0.0;

	void Kick(double V) { Velocity += V; }
	void Update(double Dt, double Stiffness, double Damping, double Min, double Max);
	void Reset() { Offset = Velocity = 0.0; }
};

/** One frame of player input, already in game terms. */
struct FMIPlayerInputFrame
{
	FVector2D Move = FVector2D::ZeroVector;         // X = right, Y = forward, length up to 1 (larger is scaled back)
	FVector2D LookDegrees = FVector2D::ZeroVector;  // X > 0 turns right, Y > 0 looks down (sensitivity applied)
	bool bSprintHeld = false;
	bool bCrouchHeld = false;
	bool bFireHeld = false;
	bool bJumpPressed = false;
};

/** What the rules ask of the body mover this frame. */
struct FMIBodyMove
{
	bool bMove = false;        // false: frozen (disabled player), nothing moves
	bool bDead = false;        // the death slide: full gravity before the move, no step
	FVector Velocity = FVector::ZeroVector;  // horizontal step and take-off done, gravity not applied
	double Height = 0.0;       // collision height this frame
	bool bAllowStep = false;   // grounded at the start and did not jump: may step up and snap down 42 cm
	bool bJumped = false;
};

/** What the body mover did. */
struct FMIBodyResult
{
	FVector Feet = FVector::ZeroVector;
	FVector Velocity = FVector::ZeroVector;
	bool bOnGround = true;
	FName Surface = TEXT("asphalt");
};

class MURDERINC_API FMIPlayerRules
{
public:
	void Init(const FMIPlayerData& InTuning, FMIGameEvents* InEvents);
	const FMIPlayerData& GetTuning() const { return T; }
	void SetEvents(FMIGameEvents* InEvents) { Events = InEvents; }

	/** Start of a run (player.reset): full health, every camera layer cleared. */
	void Reset(const FVector& InFeet, double InYaw);

	/** The decisions before the body moves: look, crouch, jump, sprint, the velocity step. CanStand: headroom test. */
	FMIBodyMove BeginFrame(double Dt, const FMIPlayerInputFrame& Input, TFunctionRef<bool()> CanStand);

	/** Everything after the move: landing, stride, health, eye height, field of view, recoil, shake, the view. */
	void EndFrame(double Dt, const FMIBodyResult& Body);

	void Damage(double Amount, const TOptional<FVector>& From, EMIDamageKind Kind);
	void Heal(double Amount);
	/** A weapon kick (degrees, pitch up, yaw right): Keep of it stays in the aim, the rest springs back. */
	void AddRecoil(double PitchDeg, double YawDeg);
	void AddShake(double Trauma);
	void SetFov(double VerticalDegrees);
	/** An explosion somewhere: the camera shakes by distance on the next frame (raise, never stack). */
	void OnExplosion(const FVector& Position, bool bBig);

	// --- public state (spec 01 2.16) -----------------------------------------------------------------
	FVector Feet = FVector::ZeroVector;
	FVector Velocity = FVector::ZeroVector;
	double Yaw = 0.0;    // aim yaw without the recoil offset (the control rotation)
	double Pitch = 0.0;
	double Health = 0.0;
	double MaxHealth = 0.0;
	bool bAlive = true;
	bool bOnGround = true;
	bool bSprinting = false;
	bool bCrouching = false;
	bool bEnabled = true;
	bool bInvulnerable = false;
	double Speed = 0.0;  // horizontal, cm/s
	double Ads = 0.0;    // written by the weapon every frame
	/** The gun in hand's aimed field of view (vertical degrees; 0 = player.fov.ads) and aimed look factor
	 *  (LOADOUT.md 4.5), written by the weapon every frame. */
	double AimFov = 0.0;
	double AimLook = 1.0;
	double RegenDelay = 0.0;
	double RegenRate = 0.0;
	FName Surface = TEXT("asphalt");

	// --- the view --------------------------------------------------------------------------------------
	FVector Eye = FVector::ZeroVector;          // where rounds leave from
	FVector Forward = FVector::ForwardVector;   // aim + recoil offset, never shake
	FRotator CameraRotation = FRotator::ZeroRotator;
	double ViewFov = 0.0;                       // vertical degrees
	double EyeHeight = 0.0;
	double StridePhase = 0.0;
	double Hurt = 0.0;       // red flash 0..1 (post-process "damage")
	double LowHealth = 0.0;  // 0..1 (post-process "lowHealth")
	double GetTrauma() const { return Shake.Trauma; }
	double GetAimYaw() const { return Yaw + Recoil.Yaw; }
	double GetAimPitch() const { return FMath::Clamp(Pitch + Recoil.Pitch, -T.Look.ViewPitchLimit, T.Look.ViewPitchLimit); }
	const FMIRecoil& GetRecoil() const { return Recoil; }

private:
	void PlaceView();
	void Land(double LandSpeed);
	void Die(const TOptional<FVector>& From);
	void UpdateStride(double Dt);
	void UpdateHealth(double Dt);
	void EaseLowHealth(double Dt);
	void DeadView(double Dt);
	FVector RightOf(double YawDeg) const;

	FMIPlayerData T;
	FMIGameEvents* Events = nullptr;

	FMIRecoil Recoil;
	FMIShake Shake;
	FMIClampedSpring Spring;
	FMIClampedSpring StepLag;

	double BaseFov = 0.0;
	double Coyote = 0.0;
	double JumpBuffer = 0.0;
	double AirTime = 0.0;
	double FallSpeed = 0.0;
	double BobAmp = 0.0;
	double StrafeRoll = 0.0;
	double SinceHit = 1e30;
	double Blast = 0.0;
	double DeadTime = 0.0;
	double EyeAtDeath = 0.0;
	double DeathSide = 1.0;
	double BobX = 0.0;
	double BobY = 0.0;
	double ViewPitch = 0.0;
	double ViewRoll = 0.0;

	// Carried from BeginFrame to EndFrame.
	bool bWasGrounded = true;
	bool bJumpedThisFrame = false;
	bool bWantSprint = false;
	bool bDeadMove = false;
	double FeetBefore = 0.0;
};
