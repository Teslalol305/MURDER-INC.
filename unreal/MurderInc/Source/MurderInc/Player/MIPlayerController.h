#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "MIPlayerController.generated.h"

class AMIPlayerCharacter;
class UInputAction;
class UInputMappingContext;
struct FInputActionValue;

/**
 * Owns the player's input: the Enhanced Input actions and the mapping context are created here in code
 * (no input assets), bound once, and forwarded to the possessed AMIPlayerCharacter.
 */
UCLASS()
class MURDERINC_API AMIPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	const UInputMappingContext* GetMappingContext() const { return MappingContext; }

	/** Creates the actions and the key mappings; safe to call more than once. Public for the tests. */
	void BuildInputAssets();

protected:
	virtual void SetupInputComponent() override;

private:
	AMIPlayerCharacter* GetMICharacter() const;

	void OnMove(const FInputActionValue& Value);
	void OnMoveEnded(const FInputActionValue& Value);
	void OnLook(const FInputActionValue& Value);
	void OnJumpPressed();
	void OnJumpReleased();
	void OnSprintPressed();
	void OnSprintReleased();
	void OnCrouchPressed();
	void OnCrouchReleased();

	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> MappingContext;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> MoveAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> LookAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> JumpAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> SprintAction;

	UPROPERTY(Transient)
	TObjectPtr<UInputAction> CrouchAction;
};
