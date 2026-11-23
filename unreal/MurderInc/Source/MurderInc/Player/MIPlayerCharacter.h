#pragma once

#include "CoreMinimal.h"
#include "Core/Data/MIData.h"
#include "Core/MIDamageable.h"
#include "Engine/EngineBaseTypes.h"
#include "GameFramework/Character.h"
#include "Player/MIPlayerRules.h"
#include "Weapons/MIWeaponRules.h"
#include "MIPlayerCharacter.generated.h"

class AMIPlayerCharacter;
class UCameraComponent;
class UMICharacterMovement;
class UMIWeaponComponent;
class UPoseableMeshComponent;
class USkeletalMeshComponent;

/**
 * The two halves of the player's frame (spec 01 3.1): the early one (pre-physics, a prerequisite of the movement
 * component) decides; the late one (post-physics, after the movement component) reads the moved body and runs the
 * view, the weapon and the viewmodel. The actor's own tick cannot be the early half: the character's movement
 * component already has the actor tick after it (adding the reverse forms a cycle).
 */
USTRUCT()
struct FMIPlayerFrameTick : public FTickFunction
{
	GENERATED_BODY()

	AMIPlayerCharacter* Target = nullptr;
	bool bLate = false;

	virtual void ExecuteTick(float DeltaTime, ELevelTick TickType, ENamedThreads::Type CurrentThread, const FGraphEventRef& MyCompletionGraphEvent) override;
	virtual FString DiagnosticMessage() override { return bLate ? TEXT("AMIPlayerCharacter late frame") : TEXT("AMIPlayerCharacter early frame"); }
};

template<>
struct TStructOpsTypeTraits<FMIPlayerFrameTick> : public TStructOpsTypeTraitsBase2<FMIPlayerFrameTick>
{
	enum { WithCopy = false };
};

/** The player's input of one frame, gathered by AMIPlayerController (edges are consumed by the frame). */
struct FMIPlayerInputState
{
	FVector2D Move = FVector2D::ZeroVector;         // X right, Y forward
	FVector2D LookDegrees = FVector2D::ZeroVector;  // accumulated: X > 0 turns right, Y > 0 looks down
	bool bSprint = false, bCrouch = false, bFire = false, bAds = false;
	bool bJumpPressed = false, bFirePressed = false, bReloadPressed = false, bSwapPressed = false;
	bool bWeapon1Pressed = false, bWeapon2Pressed = false, bMeleePressed = false;
	bool bPad = false;
};

/**
 * The player (spec 01): FMIPlayerRules decide movement, health and the view every frame; UMICharacterMovement moves
 * the capsule with the rules' velocity; the camera is placed where the rules put the eye; UMIWeaponComponent runs
 * the guns after the move. The first-person gun and arms are first-person primitives (the engine's first-person
 * rendering: own field of view, scaled toward the camera so they never clip). Every number comes from config.json.
 */
UCLASS()
class MURDERINC_API AMIPlayerCharacter : public ACharacter, public IMIDamageable
{
	GENERATED_BODY()

public:
	AMIPlayerCharacter(const FObjectInitializer& ObjectInitializer);

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;
	/** The first half of the frame: the rules decide, the movement component is told (FMIPlayerFrameTick). */
	void EarlyTick(float DeltaSeconds);
	/** The second half of the frame (FMIPlayerFrameTick). */
	void LateTick(float DeltaSeconds);

	/** Copies the tuning into the rules, the capsule, the movement component and the weapons; resets the run. */
	void ApplyTuning(const FMIConfigData& Config);
	bool HasTuning() const { return bHasTuning; }
	/** Start of a run: full health, the first gun, every camera layer cleared, at the current place. */
	void ResetRun();
	/** Start of a run at a place: standing at Feet facing Yaw (Unreal degrees), then ResetRun. */
	void ResetAt(const FVector& Feet, double Yaw);
	/** Moves the body so that its feet are at Feet (keeps the view and the run). */
	void TeleportFeet(const FVector& Feet);

	// --- what the game flow switches (UMIGameSubsystem, spec 04 3.2) ---------------------------------------
	/** Off on the title and while paused: nothing of the player updates, the camera stays. */
	void SetSimulationLive(bool bLive) { bSimLive = bLive; }
	/** Off outside intro and playing: the input of the frame is dropped. */
	void SetGameplayInput(bool bOn) { bGameplayInput = bOn; }
	void SetViewmodelVisible(bool bVisible);
	/** The play bounds (cm, X and Y); the body centre is kept body.boundsMargin inside them. */
	void SetPlayBounds(const FBox2D& Bounds) { PlayBounds = Bounds; }
	/** Runs the player's early frame after Tick (the flow comes first). */
	void AddFramePrerequisite(UObject* Object, FTickFunction& Tick) { EarlyTickFunction.AddPrerequisite(Object, Tick); }
	FTickFunction& GetLateTickFunction() { return LateTickFunction; }

	FMIPlayerInputState& GetInput() { return Input; }
	FMIPlayerRules& GetPlayerRules() { return Rules; }
	const FMIPlayerRules& GetPlayerRules() const { return Rules; }
	UMIWeaponComponent* GetWeapon() const { return Weapon; }
	UCameraComponent* GetFirstPersonCamera() const { return FirstPersonCamera; }
	bool IsSprinting() const { return Rules.bSprinting; }

	// --- what an animation layer reads (the presentation contract, docs/unreal/GAMEPLAY.md) ---------------
	double GetAimAlpha() const { return Rules.Ads; }
	double GetGroundSpeed() const { return Rules.Speed; }
	bool IsAirborne() const { return !Rules.bOnGround; }
	/** stand, crouch, sprint, dead */
	FName GetStance() const;
	/** Unit vector from the player toward the last damage source, or zero. */
	FVector GetLastDamageDirection() const { return LastDamageDirection; }

	// IMIDamageable
	virtual FMIDamageResult ApplyMIDamage(const FMIDamage& Damage) override;
	virtual bool IsMIDamageableAlive() const override { return Rules.bAlive; }
	virtual FName GetMIDamageableKind() const override { return TEXT("player"); }
	virtual FVector GetMIBlastTarget() const override;
	virtual FName GetMISurface() const override { return TEXT("flesh"); }

private:
	bool CanStand() const;
	/** The 8 cm air step (spec 01 4.3 item 5): airborne and blocked by a ledge at most AirStepHeight above the feet. */
	void AirStep(float DeltaSeconds);
	/** The bounds clamp and the fall-out return (src/player.js:564-592). */
	void KeepInside();
	void PlaceCamera();
	double HorizontalFov(double VerticalDegrees) const;
	FVector GetFeet() const;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UCameraComponent> FirstPersonCamera;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UPoseableMeshComponent> GunMesh;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<USkeletalMeshComponent> ArmsMesh;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UMIWeaponComponent> Weapon;

	UPROPERTY(Transient)
	TObjectPtr<UMICharacterMovement> Movement;

	FMIPlayerFrameTick EarlyTickFunction;
	FMIPlayerFrameTick LateTickFunction;
	FMIConfigData Tuning;
	FMIPlayerRules Rules;
	FMIPlayerInputState Input;
	FVector2D FrameLook = FVector2D::ZeroVector;
	FVector LastDamageDirection = FVector::ZeroVector;
	bool bHasTuning = false;
	bool bDeathCapsule = false;
	bool bSimLive = true;
	bool bGameplayInput = true;
	FBox2D PlayBounds = FBox2D(ForceInit);
	FVector LastGroundFeet = FVector::ZeroVector;
	bool bHaveGround = false;
};
