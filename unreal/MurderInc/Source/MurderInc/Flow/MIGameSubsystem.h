#pragma once

#include "CoreMinimal.h"
#include "Core/MIDamageable.h"
#include "Enemies/MIEnemies.h"
#include "Engine/EngineBaseTypes.h"
#include "Flow/MIGameRules.h"
#include "Flow/MISettings.h"
#include "Subsystems/WorldSubsystem.h"
#include "UI/MIMenus.h"
#include "World/MIBoxWorld.h"
#include "MIGameSubsystem.generated.h"

class ACameraActor;
class AMIBlockGeometry;
class AMIBuzzard;
class AMIExplosive;
class AMIGoon;
class AMIPlayerCharacter;
class AMIReelCase;
class AMITruck;
class UMIGameSubsystem;
class UMIFrontEnd;
struct FMIRunSetup;
struct FMILevelData;

/** The two halves of the game's frame: the flow before the player (pre-physics), the enemies after him. */
USTRUCT()
struct FMIGameFrameTick : public FTickFunction
{
	GENERATED_BODY()

	UMIGameSubsystem* Target = nullptr;
	bool bEnemies = false;

	virtual void ExecuteTick(float DeltaTime, ELevelTick TickType, ENamedThreads::Type CurrentThread, const FGraphEventRef& MyCompletionGraphEvent) override;
	virtual FString DiagnosticMessage() override { return bEnemies ? TEXT("UMIGameSubsystem enemies") : TEXT("UMIGameSubsystem flow"); }
};

template<>
struct TStructOpsTypeTraits<FMIGameFrameTick> : public TStructOpsTypeTraitsBase2<FMIGameFrameTick>
{
	enum { WithCopy = false };
};

struct FMIBootOptions
{
	/** Start on the title screen (the game) or straight into a run (tests, autostart). */
	bool bTitle = true;
	FName Mode;           // None: the setting
	FName Difficulty;     // None: the setting
	bool bSkipIntro = false;
	/** Read and write the save-game slot (off in tests). */
	bool bPersist = true;
	/** Draw the block's boxes; unset: only when the map has no art. */
	TOptional<bool> bDrawGrey;
};

/** combat.stats: counted where the facts happen (spec 04 3.14). */
struct FMIRunStats
{
	int32 Kills = 0, Shots = 0, Hits = 0, Headshots = 0;
};

/**
 * The game in a world (spec 04 4.4: one flow object that ticks before the pawns, thin actors in the level, widgets
 * that only display). Boot builds the block from level.json (collision in every map, grey boxes where there is no
 * art), the explosives, the reel cases and the truck, both enemy pools (12 Goons, 8 Buzzards, pre-spawned and
 * hidden), and runs FMIGameRules (src/game.js) with FMIEnemyField (src/enemies.js) on the box world, which is the
 * same set of boxes. It answers the rules' questions with the engine (IMIGameHost, IMIEnemyHost), forwards their
 * events to the event bus, keeps the statistics, the settings and the save game, and drives the menus.
 *
 * Frame: flow (pre-physics, before the player's early tick) -> player and weapon -> enemies (post-update work):
 * the order of src/main.js.
 */
UCLASS()
class MURDERINC_API UMIGameSubsystem : public UWorldSubsystem, public IMIGameHost, public IMIEnemyHost
{
	GENERATED_BODY()

public:
	static UMIGameSubsystem* Get(const UObject* WorldContextObject);

	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Deinitialize() override;

	/** Builds the block and the pools and starts the flow; false (and LogMI errors) when data is missing. */
	bool Boot(const FMIBootOptions& Options);
	bool IsBooted() const { return bBooted; }

	// ---- commands: menus, input, the console and tests ---------------------------------------------------
	void StartRun(FName Mode = NAME_None, bool bSkipIntro = false);
	/** The console's MIStart: the saved set-up (or the parity one) resolved like the set-up screens, then StartRun. */
	void StartRunWithSetup(FName Mode, bool bSkipIntro);
	void Pause();
	void Resume();
	/** The pause key: pause in a run, resume after the debounce on the pause card, back out of settings. */
	void PauseKey();
	void Restart();
	void Retry();
	void Redeploy();
	void ToTitle();
	void SetDifficulty(FName Difficulty);
	void SetInteractHeld(bool bHeld) { bInteract = bHeld; }
	bool IsInteractHeld() const { return bInteract; }

	FMIMenu& GetMenu() { return Menu; }
	/** The set-up flow (LOADOUT.md 2) inside the title state, or null (no loadout data: the canvas title stays). */
	UMIFrontEnd* GetFrontEnd() const { return FrontEnd; }
	ACameraActor* GetTitleCamera() const { return TitleCamera; }
	/** Hit the block with a set-up: the settings it names, the resolved guns, the crew's look and lines, then the run. */
	void BeginWithSetup(const FMIRunSetup& Setup);
	/** The set-up in the player's hands without starting (the Briefing's first-person view). */
	void PreviewSetup(const FMIRunSetup& Setup);
	/** The canvas Settings card from the front end's Home; Back returns to Home. */
	void OpenSettingsFromFrontEnd();
	/** Writes the save game: the settings, the best score and the remembered set-up. */
	void SaveSettings();
	/**
	 * An interface sound: the web game's ui:click (every press) and ui:hover (every focus move, src/menus.js) as a
	 * flow line on the world's bus, which the audio director plays (audio.json events). At most one of each a frame,
	 * and no hover in the 0.15 s after a click (a card that is rebuilt under the pointer is not a move).
	 */
	static void UiNote(const TCHAR* Name, const UObject* WorldContext);
	void MenuMove(int32 Dy);
	void MenuAdjust(int32 Dx);
	void MenuConfirm();
	void MenuBack();
	/** The mouse on a card, Point in canvas pixels (the HUD stored where it drew the rows, FMIMenu::Layout). A click
	 *  selects the row under it and acts: a button as Enter does, an adjustable row one value back on its left half and
	 *  one forward on its right. Hover only selects. False: nothing under the point. */
	bool MenuClick(const FVector2D& Point);
	bool MenuHover(const FVector2D& Point);

	// ---- the frame (FMIGameFrameTick; tests may call them directly) ----------------------------------------
	void FlowFrame(double Dt);
	void EnemyFrame(double Dt);

	/** A hit on the unit in Slot (AMIGoon / AMIBuzzard::ApplyMIDamage). */
	FMIDamageResult DamageEnemy(int32 Slot, const FMIDamage& Damage);

	// ---- state ------------------------------------------------------------------------------------------
	FMIGameRules& GetRules() { return Rules; }
	FMIEnemyField& GetEnemies() { return Field; }
	FMIBoxWorld& GetBoxWorld() { return Box; }
	const FMILevelData* GetLevel() const { return Level; }
	const FMIRunStats& GetStats() const { return RunStats; }
	FMISettings& GetSettings() { return Settings; }
	const FMIText& GetCopy() const { return Copy; }
	const FMIText& GetInterfaceText() const { return Ui; }
	/**
	 * What a control is called on the device in use (text.json input.glyphs: "interact" is E on the keyboard and X on
	 * a controller); a controller's in the names the player chose in Settings. Empty when the data has none.
	 */
	FString ControlName(const TCHAR* Action, bool bPad) const;
	/** A controller's button name as the data gives it (Xbox names) in the names chosen in Settings. */
	FString PadName(const FString& Name) const;
	AMIPlayerCharacter* GetPlayer() const;
	AActor* GetEnemyActor(int32 Slot) const;
	AMIReelCase* GetCase(int32 Index) const;
	AMITruck* GetTruck() const { return Truck; }
	AMIBlockGeometry* GetGeometry() const { return Geometry; }
	bool IsSimulationLive() const { return bSimLive; }
	bool HasArt() const { return bArt; }

	/** Hold the Block: the ids of the last one or two living enemies of a wave with nothing left to spawn (the HUD marks
	 *  them, review 2026-11-24: a wave stood open for minutes with one Buzzard nobody could find). Empty otherwise. */
	const TArray<int32>& GetLastEnemies() const { return LastEnemies; }

	/** Debug (console MIFaceEnemy): stands the player Metres from the nearest living enemy, looking at it. */
	bool FaceNearestEnemy(double Metres);

	/** Web-space helpers for tests and bots. */
	FVector PlayerFeetWeb() const;
	void TeleportPlayerWeb(const FVector& Feet);

	// ---- IMIGameHost -------------------------------------------------------------------------------------
	virtual void ResetPlayer(const FVector& Pos, double Yaw) override;
	virtual void HealPlayer(double Amount) override;
	virtual void AddReserve(double Amount, double Cap) override;
	virtual void ResetExplosives() override;
	virtual void ResetCombat() override;
	virtual void SetRegen(double Delay, double Rate) override;
	virtual void SetInvulnerable(bool bOn) override;
	virtual void AddShake(double Amount) override;
	virtual void Stats(int32& Kills, int32& Shots, int32& Hits, int32& Headshots) const override;
	virtual const FMIEnemyTune* EnemyTune(FName Difficulty) const override { return Tunes.Find(Difficulty); }
	virtual int32 Best() const override { return Settings.GetBest(); }
	virtual bool SetBest(int32 Score) override;

	// ---- IMIEnemyHost ------------------------------------------------------------------------------------
	virtual FVector Hitscan(int32 EnemyId, const FVector& Origin, const FVector& Dir, double Range, double Damage) override;
	virtual void DamagePlayer(double Amount, const FVector& From, FName Kind) override;
	virtual void Explode(int32 EnemyId, const FVector& Pos, double Radius, double Damage, double PlayerScale) override;
	virtual void HitExplosive(int32 Item, double Amount) override;

private:
	void BindEvents();
	void DrainEnemies();
	void ForwardFlow();
	void ApplyState();
	void SyncActors(double Dt);
	void SyncView(double Dt);
	void ApplySettings();
	bool ApplySetup(const FMIRunSetup& Setup);
	void ApplyCrewLines(FName Crew);
	void PatchCards();
	void RebuildMenu();
	double RayPlayer(const FVector& Origin, const FVector& Dir, double MaxDist) const;
	int32 SlotOf(int32 EnemyId) const;

	FMIGameFrameTick FlowTick;
	FMIGameFrameTick EnemyTick;

	FMIFlowTune FlowTune;
	FMIText Copy;
	FMIText Ui;
	FMIText Keys;  // text.json `input`: what the controls are called on each device
	TMap<FName, FMIEnemyTune> Tunes;
	const FMILevelData* Level = nullptr;
	FMIBoxWorld Box;
	FMIEnemyField Field;
	FMIGameRules Rules;
	FMISettings Settings;
	FMIMenu Menu;
	FMIRunStats RunStats;
	FMIBootOptions Boots;

	UPROPERTY(Transient)
	TObjectPtr<AMIBlockGeometry> Geometry;

	UPROPERTY(Transient)
	TArray<TObjectPtr<AActor>> EnemyActors;  // slot order: Goons, then Buzzards

	UPROPERTY(Transient)
	TArray<TObjectPtr<AMIReelCase>> Cases;

	UPROPERTY(Transient)
	TObjectPtr<AMITruck> Truck;

	UPROPERTY(Transient)
	TArray<TObjectPtr<AMIExplosive>> Explosives;

	UPROPERTY(Transient)
	TObjectPtr<ACameraActor> TitleCamera;

	UPROPERTY(Transient)
	TObjectPtr<UMIFrontEnd> FrontEnd;
	TMap<FString, FString> OriginalLines;  // text.json lines a crew member's template replaces (crew.json lines)
	TSharedPtr<FJsonObject> ResolverConfig, ResolverPresentation;

	mutable TWeakObjectPtr<AMIPlayerCharacter> Player;
	TSet<int32> RemovedOwners;
	/** The hold wave's last enemies (GetLastEnemies) and how long they have stood unhurt (UpdateLastEnemies). */
	void UpdateLastEnemies(double Dt);
	TArray<int32> LastEnemies;
	double LastStandFor = 0, LastStandHp = -1;
	double RegenDelay = 0, RegenRate = 0;
	double ShotTargetRadius = 0.38, ShotTargetStand = 1.8, ShotTargetCrouch = 1.15;
	double TitleSpeed = 1.15, TitleFadeIn = 1.8, TitleT = 0;
	EMIGameState AppliedState = EMIGameState::Title;
	bool bStateApplied = false;
	bool bBooted = false;
	bool bInteract = false;
	bool bSimLive = false;
	bool bArt = false;
	bool bPrerequisite = false;
	/**
	 * In a stream the Graphics quality level waits while Settings is open and is written once when it closes: each level
	 * written cost one frame of 62 to 377 ms (docs/unreal/SMOOTH.md B3), so stepping Auto to Ultra froze the picture four times.
	 */
	bool bStreamedQualityPending = false;
	int32 PendingStreamedQuality = -1;
};
