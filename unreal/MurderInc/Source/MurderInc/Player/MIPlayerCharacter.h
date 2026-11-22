#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "Core/Data/MIData.h"
#include "MIPlayerCharacter.generated.h"

class UCameraComponent;

/**
 * The player: a capsule with a first-person camera. Walk, sprint, crouch, jump and mouse look on the stock
 * character movement, with every number taken from config.json "player" (UMIDataSubsystem).
 * Bootstrap slice: the exact web-game movement rules (docs/unreal/spec/01-player.md) replace this later.
 */
UCLASS()
class MURDERINC_API AMIPlayerCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	AMIPlayerCharacter();

	virtual void PostInitializeComponents() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void OnStartCrouch(float HalfHeightAdjust, float ScaledHalfHeightAdjust) override;
	virtual void OnEndCrouch(float HalfHeightAdjust, float ScaledHalfHeightAdjust) override;
	virtual void RecalculateBaseEyeHeight() override;

	/** Copies the tuning into the capsule, the movement component and the camera. */
	void ApplyTuning(const FMIPlayerData& Data);
	bool HasTuning() const { return bHasTuning; }

	/** Input, set by AMIPlayerController. Move: X = right, Y = forward, each -1..1. Look: mouse counts, Y = up. */
	void SetMoveInput(const FVector2D& Input) { MoveInput = Input; }
	void AddLookInput(const FVector2D& MouseCounts);
	void SetSprintHeld(bool bHeld) { bSprintHeld = bHeld; }
	void SetCrouchHeld(bool bHeld) { bCrouchHeld = bHeld; }

	/** Sprint is held, allowed by the input rule, and the character is actually moving fast enough. */
	bool IsSprinting() const { return bSprinting; }
	UCameraComponent* GetFirstPersonCamera() const { return FirstPersonCamera; }

private:
	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UCameraComponent> FirstPersonCamera;

	FMIPlayerData Tuning;
	bool bHasTuning = false;

	FVector2D MoveInput = FVector2D::ZeroVector;
	bool bSprintHeld = false;
	bool bCrouchHeld = false;
	bool bSprinting = false;

	float StandEyeOffset = 0.f;   // camera height above the capsule centre, standing
	float CrouchEyeOffset = 0.f;  // the same, crouched
	float CameraHeight = 0.f;     // current camera height above the capsule centre
	float CurrentFov = 0.f;       // vertical degrees
};
