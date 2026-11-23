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

	FMIMenu& GetMenu() { return Menu; }
	void MenuMove(int32 Dy);
	void MenuAdjust(int32 Dx);
	void MenuConfirm();
	void MenuBack();

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
	AMIPlayerCharacter* GetPlayer() const;
	AActor* GetEnemyActor(int32 Slot) const;
	AMIReelCase* GetCase(int32 Index) const;
	AMITruck* GetTruck() const { return Truck; }
	AMIBlockGeometry* GetGeometry() const { return Geometry; }
	bool IsSimulationLive() const { return bSimLive; }
	bool HasArt() const { return bArt; }

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
	void SaveSettings();
	void ApplySettings();
	void RebuildMenu();
	double RayPlayer(const FVector& Origin, const FVector& Dir, double MaxDist) const;
	int32 SlotOf(int32 EnemyId) const;

	FMIGameFrameTick FlowTick;
	FMIGameFrameTick EnemyTick;

	FMIFlowTune FlowTune;
	FMIText Copy;
	FMIText Ui;
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

	mutable TWeakObjectPtr<AMIPlayerCharacter> Player;
	TSet<int32> RemovedOwners;
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
};
