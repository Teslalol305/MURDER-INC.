#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "Player/MIAimAssist.h"
#include "Player/MILookInput.h"
#include "Player/MISwitchInput.h"
#include "MIPlayerController.generated.h"

class AMIPlayerCharacter;
class UInputAction;
class UInputMappingContext;
enum class EInputActionValueType : uint8;

/**
 * Owns the player's input (spec 01 4.6): the Enhanced Input actions and the mapping context are created here in
 * code (no input assets), bound once, and written into the possessed AMIPlayerCharacter's input state. Mouse look
 * is turned into degrees here (counts x config player.input.mouse x sensitivity); the rules do the rest.
 *
 * The gamepad (spec 01 3.17, src/input.js): both sticks pass the web game's axial dead zone; the right stick turns
 * the view through its response curve and turn boost (FMIPadLook) and picks on the weapon wheel while that is open;
 * the triggers fire and aim from their analog axes too (a pad in a browser stream sends the triggers only as axes);
 * L3 latches the sprint; X reloads, unless a grab prompt is showing when it is pressed: then that hold grabs. The
 * device that produced real input last is the active one (3.16): the pad's aim slow-down runs only while that is the
 * pad.
 *
 * Mouse look through a Pixel Streaming data channel (Cloud/MICloud.h): the stream's mouse events arrive one by one
 * through StreamMouseEvent and are turned back into the browser's pixels (FMIStreamMouse); the engine's own mouse
 * axis is ignored meanwhile. On the desktop nothing of that applies.
 *
 * Nothing pressed on a card carries into play (3.16): the click, key or button that resumed or started a run does
 * not also fire, jump or strike when the run goes live.
 */
UCLASS()
class MURDERINC_API AMIPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	const UInputMappingContext* GetMappingContext() const { return MappingContext; }

	/** Creates the actions and the key mappings; safe to call more than once. Public for the tests. */
	void BuildInputAssets();

	/** Every key and axis event passes here on its way to the mappings: it tells which device is in use. */
	PRAGMA_DISABLE_DEPRECATION_WARNINGS
	using APlayerController::InputKey;
	PRAGMA_ENABLE_DEPRECATION_WARNINGS
	virtual bool InputKey(const FInputKeyEventArgs& Params) override;

	/** True while the gamepad is the device that produced real input last. */
	bool IsPadActive() const { return bPadActive; }
	/** A run is live and takes the look and the sticks (no card, no set-up screen, no intro). */
	bool IsInLivePlay() const;
	/** The set-up screens take their keys before the controller sees them: they say which device worked them. */
	void SetDeviceFromMenu(bool bPad) { UsePad(bPad); }
	const FMIPadLook& GetPadLook() const { return PadLook; }
	bool IsSprintLatched() const { return bSprintLatch; }

	/** The mouse comes through a stream from now on (UMICloudSubsystem, or a test): see the class comment. */
	void SetStreamMouse(const FMIStreamMouse& Shape);
	void ClearStreamMouse();
	bool UsesStreamMouse() const { return bStreamMouse; }
	const FMIStreamMouse& GetStreamMouse() const { return StreamMouse; }
	/** One mouse event of the stream, counts as Slate reports them (X right, Y down). False: a spike, dropped whole. */
	bool StreamMouseEvent(const FVector2D& Counts);
	/** Spikes dropped since the start (the cloud probe line). */
	int32 GetMouseSpikes() const { return MouseSpikes; }

	/** A card acted on a press (confirm, click, back, the pause key): what is still held does not carry into play. */
	void DropMenuPresses();
	/**
	 * Everything that is held is let go: every key, button, stick and trigger, in the engine's input and in this
	 * controller. For a player who is gone (a stream's last viewer left: UMICloudSubsystem::ReleaseForLeave): the
	 * releases of what he held never arrive. A key pressed afterwards counts as a fresh press.
	 */
	void DropAllHeld();

	// The console commands below are for headless checks and pictures on the box. None of them does anything in the
	// Shipping game (their bodies are compiled out): a stream's viewer can reach the console through launch options
	// on a link, and a command such as MIShot writes a file where its caller says.

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
	/** Dev: each finger's gap to the gun in hand and the curl to contact (UMIFirstPersonRig::ProbeGrip, "MI-GRIP" lines). */
	UFUNCTION(Exec)
	void MIGripProbe(const FString& Label);

	/** The four-gun input layer: the wheel's state for the HUD (LOADOUT.md 4.6). */
	const FMISwitchInput& GetSwitch() const { return Switch; }
	FMISwitchInput& GetSwitch() { return Switch; }

	/**
	 * The aim assist (Player/MIAimAssist.h, docs/unreal/DECISIONS.md 2026-11-27 ~22:20): the Settings switch and its
	 * strength id (low, normal, high). Off until the game flow applies the settings (a bare controller in a test has none).
	 */
	void SetAimAssist(bool bOn, FName Strength);
	bool IsAimAssistOn() const { return bAimAssist; }
	const FMIAimAssist& GetAimAssist() const { return Assist; }
	/** The look rate's factor the assist gives right now (1 when it is off or nothing is under the crosshair). */
	double GetAssistSlow() const { return bAimAssist ? Assist.GetSlow() : 1.0; }

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
	UInputAction* MakeAction(const TCHAR* Name, EInputActionValueType Type);
	/** Moves the switch layer's edges into the pawn's input state (same frame as the key event). */
	void FlushSwitch();
	double Now() const;
	/** Mouse travel of one frame or event, in the web game's pixels (X right, Y up): the look, or the weapon wheel. */
	void MouseLook(const FVector2D& Pixels);
	/** Gathers the Goons the assist may help (live, within reach, a clear line to the chest) and runs it; writes the
	 *  turn it asks for into the pawn's input. Returns the look rate's factor. */
	double UpdateAimAssist(double Dt, bool bLive);
	/** Which device an event came from (spec 01 3.16). */
	void NoteDevice(const FKey& Key, EInputEvent Event, float Value);
	void UsePad(bool bPad);
	/** Fire and aim have two sources each (the keys and buttons, and the trigger's axis): held while either holds. */
	void SetFire(bool& Source, bool bDown);
	void SetAim(bool& Source, bool bDown);
	bool SwallowsPresses() const { return SwallowTicks > 0; }

	FMISwitchInput Switch;

	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> MappingContext;

	UPROPERTY(Transient)
	TMap<FName, TObjectPtr<UInputAction>> Actions;

	double MouseDegreesPerCount = 0.0;
	double WheelDebounce = 0.0;
	double MouseWake = 0.0;

	// The aim assist.
	FMIAimAssist Assist;
	bool bAimAssist = false;
	double AssistStrength = 1.0;
	double AssistSlow = 1.0;
	TArray<FVector2D> AssistErrors;  // scratch, kept to avoid an allocation a frame

	// The gamepad.
	FMIPadLook PadLook;
	FVector2D LeftStick = FVector2D::ZeroVector;   // raw, X right, Y forward
	FVector2D RightStick = FVector2D::ZeroVector;  // raw, X right, Y up (the viewport's inverted Y put right)
	FVector2D KeyMove = FVector2D::ZeroVector;     // W A S D
	FVector2D PadMove = FVector2D::ZeroVector;     // the left stick after the dead zone
	bool bPadActive = false;
	bool bSprintLatch = false;
	bool bFireKey = false, bFireAxis = false, bAimKey = false, bAimAxis = false;
	bool bGrabKey = false, bGrabPad = false;       // the grab is held by E, or by a press of the pad's X that found a prompt
	double MouseTravel = 0.0;  // web pixels this frame: a nudge of the desk does not take the device back from a pad

	// The mouse through a stream.
	FMIStreamMouse StreamMouse;
	bool bStreamMouse = false;
	FVector2D StreamPending = FVector2D::ZeroVector;  // web pixels since the last frame, X right, Y up
	int32 MouseSpikes = 0;

	/** Frames of play left in which a fresh press of a play action is ignored (it was the press that left a card). */
	int32 SwallowTicks = 0;
};
