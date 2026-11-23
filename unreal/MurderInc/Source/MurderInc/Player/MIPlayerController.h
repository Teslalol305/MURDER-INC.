#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "Player/MISwitchInput.h"
#include "MIPlayerController.generated.h"

class AMIPlayerCharacter;
class UInputAction;
class UInputMappingContext;

/**
 * Owns the player's input (spec 01 4.6): the Enhanced Input actions and the mapping context are created here in
 * code (no input assets), bound once, and written into the possessed AMIPlayerCharacter's input state. Mouse look
 * is turned into degrees here (counts x config player.input.mouse x sensitivity); the rules do the rest.
 */
UCLASS()
class MURDERINC_API AMIPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	const UInputMappingContext* GetMappingContext() const { return MappingContext; }

	/** Creates the actions and the key mappings; safe to call more than once. Public for the tests. */
	void BuildInputAssets();

	/**
	 * Console input for headless checks: MIInput <fire|ads|sprint|crouch|jump|reload|swap|melee|weapon1|weapon2|forward|right> <value>.
	 * Buttons: 1 presses and holds, 0 releases. forward and right set the move axis (-1..1).
	 */
	UFUNCTION(Exec)
	void MIInput(const FString& Action, float Value);

	/** The game flow from the console (headless play checks): MIStart [mission|holdout] [skip], MIPauseKey,
	 *  MIMenu <up|down|left|right|confirm|back>, MIInteract <0|1>. */
	UFUNCTION(Exec)
	void MIStart(const FString& Mode, const FString& Skip);
	UFUNCTION(Exec)
	void MIPauseKey();
	UFUNCTION(Exec)
	void MIMenu(const FString& Command);
	UFUNCTION(Exec)
	void MIInteract(float Value);
	/** MIShot <file.png>: the game viewport with its widgets (the set-up screens) and the HUD, as the player sees it. */
	UFUNCTION(Exec)
	void MIShot(const FString& Path);
	/** MISetup dump: the remembered set-up as JSON. */
	UFUNCTION(Exec)
	void MISetup(const FString& Command);
	/** Debug: stand Metres (default 8) from the nearest living enemy, looking at it. */
	UFUNCTION(Exec)
	void MIFaceEnemy(float Metres);

	/** The four-gun input layer: the wheel's state for the HUD (LOADOUT.md 4.6). */
	const FMISwitchInput& GetSwitch() const { return Switch; }
	FMISwitchInput& GetSwitch() { return Switch; }

	/** User settings (spec 01 4.8). */
	double Sensitivity = 1.0;
	bool bInvertY = false;

protected:
	virtual void BeginPlay() override;
	virtual void SetupInputComponent() override;
	virtual void PlayerTick(float DeltaTime) override;

private:
	AMIPlayerCharacter* GetMICharacter() const;
	UInputAction* MakeAction(const TCHAR* Name, bool bAxis2D);
	/** Moves the switch layer's edges into the pawn's input state (same frame as the key event). */
	void FlushSwitch();
	double Now() const;

	FMISwitchInput Switch;

	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> MappingContext;

	UPROPERTY(Transient)
	TMap<FName, TObjectPtr<UInputAction>> Actions;

	double MouseDegreesPerCount = 0.0;
	double WheelDebounce = 0.0;
};
