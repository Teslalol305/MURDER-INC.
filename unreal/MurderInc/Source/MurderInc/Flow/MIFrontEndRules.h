#pragma once

#include "CoreMinimal.h"
#include "Core/Data/MILoadoutData.h"
#include "Weapons/MILoadoutResolver.h"

/**
 * The set-up flow as rules (docs/unreal/LOADOUT.md 2, frontend.json screens / navigation / carry): which screen is
 * up, edit mode, what each screen offers and the choices on it, the carry rules, the Workbench's builds and its effect
 * lines, Back and Next, the step strip and the shortcuts. No widget: the Slate screens draw it and send it the
 * player's actions, the tests (Frontend.Walk) and the console (MIMenu) drive it the same way.
 */
enum class EMIFrontScreen : uint8
{
	Home,
	Crew,
	Loadout,
	Workbench,
	Where,
	Briefing
};

/** What the host should do after an action. */
enum class EMIFrontRequest : uint8
{
	None,
	StartRun,  // Hit the block (the set-up is saved first)
};

/** One effect line of the Workbench (frontend.effects.*): ▲ better, ▼ worse, • neutral, always with its sign. */
struct FMIEffectLine
{
	FString Text;
	int32 Sign = 0;  // +1 better, -1 worse, 0 neutral
};

class MURDERINC_API FMIFrontEndRules
{
public:
	/** Data, readiness and resolver must outlive the rules. Saved: the remembered set-up (validated here). */
	void Init(const FMILoadoutData* InData, const FMIReadiness& InReady, const FMILoadoutResolver* InResolver, const FMIRunSetup& Saved);

	// ---- state ------------------------------------------------------------------------------------------
	EMIFrontScreen GetScreen() const { return Screen; }
	bool IsEditMode() const { return bEdit; }
	const FMIRunSetup& GetSetup() const { return Setup; }
	FMIRunSetup& EditSetup() { return Setup; }
	const FMIReadiness& GetReadiness() const { return Ready; }
	/** mi.Setup.ShowUnready: the rack also shows the guns that are not ready, tagged DEV. */
	void SetShowUnready(bool bOn) { Ready.bShowUnready = bOn; }
	const FMILoadoutData& GetData() const { return *Data; }
	/** At least one gun carried and every required slot filled (always true after validation). */
	bool IsValid() const;
	/** The reason Next is disabled, or empty. */
	FString NextBlocked() const;
	/** Edges that save the set-up (frontend.json transitions "remember"); the host writes the save game. */
	bool ConsumeRemember() { const bool B = bRemember; bRemember = false; return B; }
	/** The step of a screen in the strip (1 Crew, 2 Loadout and Workbench, 3 Block & Style, 4 Briefing; 0 Home). */
	static int32 StepOf(EMIFrontScreen S);
	bool IsStepReachable(int32 Step) const;
	static FString ScreenName(EMIFrontScreen S);
	static bool ParseScreen(const FString& Name, EMIFrontScreen& Out);

	// ---- navigation -------------------------------------------------------------------------------------
	/** Hit the block on Home: starts at once once a run has been played; the first time it opens Crew. */
	EMIFrontRequest HitTheBlock();
	/** Gear up: the flow from the top. */
	void GearUp();
	/** A Home summary link or a Briefing Change link: the screen in edit mode (Next reads Done). */
	void Edit(EMIFrontScreen S);
	/** Next (or Done in edit mode). Returns StartRun on the Briefing. */
	EMIFrontRequest Next();
	void Back();
	/** Ctrl+Enter / Start: straight to the Briefing when the set-up is valid. */
	bool ToBriefing();
	/** A step bullet. */
	bool GoToStep(int32 Step);
	/** After a run: Change set-up (dead / complete card) opens the Briefing; Back to title opens Home. */
	void OpenBriefing();
	void OpenHome();

	// ---- Crew -------------------------------------------------------------------------------------------
	TArray<FName> OfferedCrew() const;
	void ChooseCrew(FName Crew);
	FString CrewTagline(FName Crew) const;

	// ---- Loadout ----------------------------------------------------------------------------------------
	/** The rack: offered guns of a class filter (all, rifle, smg, pistol, new), in roster order. */
	TArray<FName> Rack(FName Filter = TEXT("all")) const;
	int32 SlotOf(FName Gun) const { return Setup.Guns.IndexOfByKey(Gun); }
	/** Carry a gun: into the first empty slot, or into the selected slot when all are full. A carried gun focuses its
	 *  slot. False (and FullMessage) when all four are full and no slot is selected. */
	bool Carry(FName Gun);
	/** Put a gun in a given slot (1-4 on a card, a drag): an empty slot past the end fills the next free one. */
	bool PutInSlot(FName Gun, int32 Slot);
	void SwapSlots(int32 A, int32 B);
	void EmptySlot(int32 Slot);
	void SelectSlot(int32 Slot) { SelectedSlot = Setup.Guns.IsValidIndex(Slot) ? Slot : INDEX_NONE; }
	int32 GetSelectedSlot() const { return SelectedSlot; }
	void FocusGun(FName Gun);
	FName GetFocusGun() const { return FocusedGun; }
	bool IsNew(FName Id) const { return !Setup.Seen.Contains(Id); }
	/** Opens the Workbench for a gun (carried or not). */
	void OpenWorkbench(FName Gun);

	// ---- Workbench --------------------------------------------------------------------------------------
	FName GetBenchGun() const { return BenchGun; }
	TArray<FName> BenchSlots() const { return Ready.OfferedSlots(BenchGun); }
	FName GetBenchSlot() const { return BenchSlot; }
	void ChooseBenchSlot(FName Slot);
	/** The options of the slot: NAME_None is Factory (only where the slot is not required). */
	TArray<FName> BenchOptions(FName Slot) const;
	FName FittedIn(FName Slot) const;
	/** Focus previews (not fitted); Fit commits; Factory empties a non-required slot. */
	void PreviewPart(FName Part) { Previewed = Part; bPreview = true; }
	void StopPreview() { bPreview = false; }
	bool IsPreviewing() const { return bPreview; }
	FName GetPreviewed() const { return Previewed; }
	void Fit(FName Part);
	void FitFactory();
	/** The build shown on the stage: the fitted build with the previewed option in its slot. */
	FMIGunBuild ShownBuild() const;
	/** Reset build is a 0.6 s hold (input.holds.resetHold): Held true while the key or button is down. */
	bool HoldReset(double Dt, bool bHeld);
	double GetResetHold() const { return ResetHeld; }
	/** [ / ], LB / RB: the next or previous carried gun without leaving. */
	void BenchNextGun(int32 Dir);
	/** The effect lines of a part on the bench gun (against the gun without it in that slot). */
	TArray<FMIEffectLine> EffectLines(FName Gun, FName Part) const;
	/** The six bars of a gun with a build, at the set-up's difficulty. */
	FMIGunBars Bars(FName Gun, const FMIGunBuild* Build) const;

	// ---- Block & Style ----------------------------------------------------------------------------------
	TArray<FName> Levels() const { return Data->LevelOrder; }
	TArray<FName> Modes() const { return Ready.ModesOf(Setup.Level); }
	void SetLevel(FName Level);
	void SetMode(FName Mode);
	void SetDifficulty(FName Difficulty) { Setup.Difficulty = Difficulty; }
	void SetTime(FName Time) { Setup.Time = Time; }

	// ---- text -------------------------------------------------------------------------------------------
	/** Copy: frontend.* from frontend_text.json, text.* from text.json (Copy root = text.json). */
	FString Text(const FString& Key) const;
	FString GunName(FName Gun) const;
	FString PartName(FName Part) const;
	FString CrewName(FName Crew) const;
	/** "RULE · CHOPPER / NINE · The Block · Day · Story · Boss" */
	FString Summary() const;
	TSharedPtr<FJsonObject> TextJson;  // text.json, for the text.* keys (set by the host)
	double GoonHp(FName Difficulty) const;
	TSharedPtr<FJsonObject> ConfigJson;  // config.json, for the Goon's hit points (set by the host)

	FString LastMessage;  // the note under the rack (frontend.loadout.full ...)

private:
	void Go(EMIFrontScreen S);
	void Seen(FName Id) { Setup.Seen.AddUnique(Id); }
	FMIGunBuild& BuildOf(FName Gun);

	const FMILoadoutData* Data = nullptr;
	FMIReadiness Ready;
	const FMILoadoutResolver* Resolver = nullptr;
	FMIRunSetup Setup;
	EMIFrontScreen Screen = EMIFrontScreen::Home;
	EMIFrontScreen EditReturn = EMIFrontScreen::Briefing;
	bool bEdit = false;
	bool bRemember = false;
	int32 SelectedSlot = INDEX_NONE;
	FName FocusedGun;
	FName BenchGun;
	FName BenchSlot;
	FName Previewed;
	bool bPreview = false;
	double ResetHeld = 0.0;
};
