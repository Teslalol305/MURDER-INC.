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
	void Tick(double Dt);

	FMIFrontEndRules& GetRules() { return Rules; }
	const FMIFrontEndRules& GetRules() const { return Rules; }
	UMIGameSubsystem* GetGame() const { return Game.Get(); }
	AMIShowroom* GetShowroom() const { return Showroom; }
	int32 GetVersion() const { return Version; }
	void Changed() { ++Version; }

	/** One action by name (the console twin of every control): see the .cpp for the list. */
	bool Act(const FString& Action, const FString& Arg = FString());
	/** A key or button from the widget; true when it was used. */
	bool Key(const FKey& Key, bool bDown, bool bRepeat, bool bCtrl, bool bShift);

	/** The focused row or card of the current screen, and the pane on Loadout (0 rack, 1 slots). */
	int32 Focus = 0;
	int32 Pane = 0;
	FName RackFilter = TEXT("all");
	/** Home: the summary line's links and the pickers; Briefing: the four lines and Go. */
	int32 NumFocusable() const;

	/** After a run (the death and debrief cards): Change set-up opens the Briefing; Back to title opens Home. */
	void OpenBriefing();
	void OpenHome();

	/** The resolved gun a screen shows (the focused rack gun, the bench gun with the previewed option). */
	bool ResolveShown(FName Gun, const FMIGunBuild* Build, FMIResolvedGun& Out) const;
	const FMIReadiness& GetReadiness() const { return Rules.GetReadiness(); }
	double GetHoldReset() const { return Rules.GetResetHold(); }

private:
	void SyncStage(bool bForce);
	void SyncViewTarget();
	void Remember();
	void StartRun();
	void Move(int32 Dx, int32 Dy);
	void Activate();
	void WriteSetting(FName Which, FName Value);
	void AfterScreenChange();

	TWeakObjectPtr<UMIGameSubsystem> Game;
	UPROPERTY(Transient) TObjectPtr<AMIShowroom> Showroom;
	TSharedPtr<SMIFrontEnd> Widget;
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
	int32 ViewTargetFor = -1;
};
