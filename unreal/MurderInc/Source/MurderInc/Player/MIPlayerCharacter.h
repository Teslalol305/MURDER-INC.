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
};
