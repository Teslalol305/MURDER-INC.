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
	/** Dev: MIKey <key> [down|up] [ctrl] [shift]: a real key event through Slate (FSlateApplication::ProcessKeyDownEvent
	 *  / ProcessKeyUpEvent): to the set-up screens while they are up, else to the game viewport (the controller's own
	 *  mappings). Key names as FKey (Enter, Tab, Down, Gamepad_Special_Right, Gamepad_FaceButton_Bottom, Q, Three ...).
	 *  Not in shipping builds. */
	UFUNCTION(Exec)
	void MIKey(const FString& Command);
	/** Dev: MIViewSize <width> <height>: resizes the window around the game viewport so the viewport is that size
	 *  (picture checks at 16:9, 21:9 and 3840 x 2160 in the headless editor). Not in shipping builds. */
	UFUNCTION(Exec)
	void MIViewSize(int32 Width, int32 Height);
	/** Debug: stand Metres (default 8) from the nearest living enemy, looking at it. */
	UFUNCTION(Exec)
	void MIFaceEnemy(float Metres);
	/** Dev: MIFreezeAfter <seconds>: after that much game time the world's time nearly stops (time dilation 0.0001),
	 *  so a headless picture catches one instant of an animation or effect; `slomo 1` resumes. Not in shipping builds. */
	UFUNCTION(Exec)
	void MIFreezeAfter(float Seconds);
	/** Dev: MIFreezeOn <enemyfire|explosion|fire> [delay]: freeze (as MIFreezeAfter) that long after the next such event. */
	UFUNCTION(Exec)
	void MIFreezeOn(const FString& Event, float Delay);
	/** Dev: MIPose <x> <y> <feet z> <yaw> <pitch>: the player's feet there (Unreal cm) looking that way (degrees). */
	UFUNCTION(Exec)
	void MIPose(float X, float Y, float Z, float Yaw, float Pitch);
	/** Dev: MIBlowNearest: the nearest live explosive in front of the player takes a lethal round from him. */
	UFUNCTION(Exec)
	void MIBlowNearest();

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
	float FreezeIn = -1.f;
	FName FreezeEvent;
	float FreezeDelay = 0.f;
	bool bFreezeBound = false;

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
