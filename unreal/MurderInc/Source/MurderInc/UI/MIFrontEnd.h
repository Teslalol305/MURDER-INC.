#pragma once

#include "CoreMinimal.h"
#include "Flow/MIFrontEndRules.h"
#include "InputCoreTypes.h"
#include "UObject/Object.h"
#include "MIFrontEnd.generated.h"

class AMIShowroom;
class SMIFrontEnd;
class UMIGameSubsystem;

/**
 * The set-up flow in the game (docs/unreal/LOADOUT.md 2): owns FMIFrontEndRules, the 3D stage (AMIShowroom) and the
 * Slate screens (SMIFrontEnd), lives inside the flow's title state, and hands the run's set-up to UMIGameSubsystem on
 * Hit the block. Every input (mouse in the widgets, keyboard and gamepad keys, the console's MIMenu fe ...) ends in
 * Act(), so the screens, the console and the tests take the same path.
 */
UCLASS()
class MURDERINC_API UMIFrontEnd : public UObject
{
	GENERATED_BODY()

public:
	bool Init(UMIGameSubsystem* InGame);
	void Show();
	void Hide();
	bool IsShown() const { return bShown; }
	/** The Briefing shows the player's own first-person view: the arms and the first carried gun stay visible. */
	bool WantsViewmodel() const { return bShown && Rules.GetScreen() == EMIFrontScreen::Briefing; }
	void Tick(double Dt);

	FMIFrontEndRules& GetRules() { return Rules; }
	const FMIFrontEndRules& GetRules() const { return Rules; }
	UMIGameSubsystem* GetGame() const { return Game.Get(); }
	AMIShowroom* GetShowroom() const { return Showroom; }
	int32 GetVersion() const { return Version; }
	void Changed() { ++Version; }
	/** A fit or a removal (Backspace, X) was just made: the pointer resting on the option it came from is told it is hovered
	 *  again by the rebuild, and its preview put the removed part back on the stage (PLAY.md E7). Until the pointer moves,
	 *  that hover is ignored (HoverBlocked). */
	void NoteFit();
	bool HoverBlocked();

	/** One action by name (the console twin of every control): see the .cpp for the list. */
	bool Act(const FString& Action, const FString& Arg = FString());
	/** A key or button from the widget; true when it was used. */
	bool Key(const FKey& Key, bool bDown, bool bRepeat, bool bCtrl, bool bShift);
	/** A real key press and release through Slate's routing (FSlateApplication::ProcessKeyDownEvent / ProcessKeyUpEvent)
	 *  to the focused set-up widget, as a keyboard or pad would send it: the console's MIKey and the tests use it. Where
	 *  the widget is in no window (a headless test world) it is hosted in a virtual window for the press. Returns true
	 *  when the widget handled the press. */
	bool PressKey(const FKey& Key, bool bCtrl = false, bool bShift = false);
	/** Press only or release only (for chords such as View+Start and the 0.6 s reset hold). */
	bool SendKey(const FKey& Key, bool bDown, bool bCtrl = false, bool bShift = false);

	/** The focused row or card of the current screen, and the pane on Loadout (0 rack, 1 slots). */
	int32 Focus = 0;
	int32 Pane = 0;
	/** The bottom bar's Next (Done, Hit the block) has the focus: Tab, or Down past the last row, reaches it. */
	bool bOnNext = false;
	/** The focus the screens draw: none while Next has it. */
	int32 FocusShown() const { return bOnNext ? -1 : Focus; }
	/** The device the player used last: true for a gamepad (the glyphs follow it). */
	bool IsPad() const { return bPad; }
	void UsePad(bool bIn) { if (bIn != bPad) { bPad = bIn; Changed(); } }
	/** frontend.glyphs.<kbm|pad>.<Key>: the key or button name for the device in use. */
	FString Glyph(const TCHAR* Key) const;
	/** A controller's button name from the data (Xbox names) in the names chosen in Settings. */
	FString PadName(const FString& Name) const;
	FName RackFilter = TEXT("all");
	/** Home: the full controls list is open (the CONTROLS button, focus 9). */
	bool bShowControls = false;
	bool bFitCursor = false;
	FVector2D FitCursor = FVector2D::ZeroVector;
	/** Home: the summary line's links and the pickers; Briefing: the four lines and Go. */
	int32 NumFocusable() const;

	/** After a run (the death and debrief cards): Change set-up opens the Briefing; Back to title opens Home. */
	void OpenBriefing();
	void OpenHome();

	/** Every string of a text document the screens may draw (notes for the reader left out). */
	static void CollectDrawnText(const TSharedPtr<FJsonObject>& Root, TArray<FString>& Out);

	/** The resolved gun a screen shows (the focused rack gun, the bench gun with the previewed option). */
	bool ResolveShown(FName Gun, const FMIGunBuild* Build, FMIResolvedGun& Out) const;
	const FMIReadiness& GetReadiness() const { return Rules.GetReadiness(); }
	double GetHoldReset() const { return Rules.GetResetHold(); }
	/** The Slate screens (tests drive their hover and their layout). */
	TSharedPtr<SMIFrontEnd> GetWidget() const { return Widget; }

private:
	void SyncStage(bool bForce);
	/** Once, behind the title card: the Crew arms and the turntable drawn once so the first real draw is not a long frame. */
	void WarmStage();
	bool bWarmed = false;
	/** The warm-up waits this many frames after the first screen is up (SMOOTH.md, engine start: its loads were 175 ms inside
	 *  the first frames, which is time before the game's first line); -1 once it has run or is not wanted. */
	int32 WarmFramesLeft = -1;
	/** The Briefing's first-person gun is set up in the frame the view changes (SyncViewTarget) and first stepped in the next one: its
	 *  equip (the rig's clips, the magazine) is 5 to 6 ms, and with the set-up in the same frame the frame was 28 ms (SMOOTH.md, v8). */
	bool bSkipBriefingStep = false;
	void SyncViewTarget();
	void Remember();
	void StartRun();
	void Move(int32 Dx, int32 Dy);
	void Activate();
	void WriteSetting(FName Which, FName Value);
	void AfterScreenChange();
	/** Marks a camera cut on this frame and the next (fix pass: TSR and Lumen kept the last view's history, vertical
	 *  banding for a few frames after each stage cut). */
	void CutCamera();

	TWeakObjectPtr<UMIGameSubsystem> Game;
	UPROPERTY(Transient) TObjectPtr<AMIShowroom> Showroom;
	TSharedPtr<SMIFrontEnd> Widget;
	TSharedPtr<class SWindow> KeyWindow;  // the virtual window that hosts the widget for SendKey when no viewport does
	TSharedPtr<FJsonObject> ConfigRoot, PresentationRoot, TextRoot;
	TUniquePtr<FMILoadoutResolver> Resolver;
	FMIFrontEndRules Rules;
	TUniquePtr<FMIViewmodelData> ViewData;
	TUniquePtr<FMILoadoutData> OwnData;  // without a game instance (headless world tests) the front end loads its own
	EMIFrontScreen StageScreen = EMIFrontScreen::Home;
	FString StageKey;
	int32 Version = 0;
	bool bShown = false;
	bool bResetDown = false;
	bool bInputMode = false;  // the UI-only input mode, set once the player controller exists
	bool bPad = false;
	bool bKeysSeen = false;  // a key or a pad button worked these screens (a mouse alone says nothing about the device)
	bool bViewHeld = false;   // the pad's View button, held: View+Start jumps to the Briefing
	int32 ViewTargetFor = -1;
	int32 CameraCutFrames = 0;  // frames still to mark as camera cuts
};
