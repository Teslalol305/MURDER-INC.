#pragma once

#include "CoreMinimal.h"
#include "Enemies/MIEnemies.h"
#include "Flow/MIFlowRules.h"

/**
 * src/game.js as rules: the state machine (title, intro, playing, paused, dead, complete), the run reset, Story
 * (the starting patrol, the three master reels held with Interact, the reinforcement waves, the pursuit, the IPX
 * truck), Hold the Block (waves, breathers, resupply, scoring), the spawn queue and its pump, the radio, the music
 * driver and the cards. Web units; the enemies are FMIEnemyField on the same box world.
 * UMIGameFlowSubsystem hosts it in a world; MurderInc.Golden.Directors replays whole runs of the web game.
 */

enum class EMIGameState : uint8 { Title, Intro, Playing, Paused, Dead, Complete };

/** What the HUD and the menus show; the rules keep it current, the host draws it. */
struct FMIFlowView
{
	FString Objective;
	FString Tally;
	int32 Reels = 0, ReelsTotal = 3;
	FString Prompt;            // "" when hidden
	double PromptProgress = 0;
	FString Message;           // timed lines
	double MessageLeft = 0;
	FString Warn;
	double WarnLeft = 0;
	bool bLocationCard = false;
	double Fade = 1, Saturation = 1;
	double Music = 0.15;
	struct FMarker
	{
		FName Id;
		FString Code, Label;
		FVector Pos;
		bool bExit = false;
	};
	TArray<FMarker> Markers;
};

/** cardData (src/game/stats.js): what the death and debrief cards say. */
struct FMIRunCard
{
	FName Screen;  // dead / complete
	FName Mode, Difficulty;
	double Time = 0;
	int32 Reels = 0, Total = 0, Wave = 0, Kills = 0, Headshots = 0, Shots = 0, Hits = 0, Score = 0, Best = 0;
	bool bNewBest = false;
	/** flow.drones: with the drones out of the game, the cards leave out the "Vultures dropped" row (the text is untouched). */
	bool bDrones = true;
	double Accuracy = -1;
	int32 Retries = 0, Rating = 0;
	FString RatingName;
};

/** One thing the flow did, in order (for the event bus, the HUD's feeds and the tests). */
struct FMIFlowEvent
{
	FName Name;   // game:state, objective:done, objective:all, holdout:wave, extraction:reached, hud:*, audio:sting ...
	FString Text;
	double A = 0, B = 0, C = 0;
};

/** The player as the flow reads him (web units). */
struct FMIFlowPlayer
{
	FVector Pos = FVector::ZeroVector;
	FVector Forward = FVector(0, 0, -1);
	bool bAlive = true;
	double Health = 100;
};

/** What the flow asks of the rest of the game. */
class IMIGameHost
{
public:
	virtual ~IMIGameHost() = default;
	virtual void ResetPlayer(const FVector& Pos, double Yaw) = 0;
	virtual void HealPlayer(double Amount) = 0;
	virtual void AddReserve(double Amount, double Cap) = 0;
	virtual void ResetExplosives() = 0;
	virtual void ResetCombat() = 0;
	virtual void SetRegen(double Delay, double Rate) = 0;
	virtual void SetInvulnerable(bool bOn) = 0;
	virtual void AddShake(double Amount) {}
	/** combat.stats: kills by the player, rounds fired, rounds that hit, head hits. */
	virtual void Stats(int32& Kills, int32& Shots, int32& Hits, int32& Headshots) const = 0;
	/** The enemies' table for a difficulty (resolved), and its id. */
	virtual const FMIEnemyTune* EnemyTune(FName Difficulty) const = 0;
	virtual int32 Best() const { return 0; }
	virtual bool SetBest(int32 Score) { return false; }
};

class MURDERINC_API FMIGameRules
{
public:
	/**
	 * What the grab control is called in the prompt (G.input.glyph('interact')): E on the keyboard, the game layer
	 * puts a controller's name here while a controller is the device in use.
	 */
	FString InteractGlyph = TEXT("E");

	void Init(const FMIFlowTune& InTune, const FMIText& InText, const FMILevelData* InLevel, FMIBoxWorld* InWorld, FMIEnemyField* InEnemies, IMIGameHost* InHost, const FMIRng& Root);

	// The contract of G.game.
	void Start(FName Mode, bool bSkipIntro = false);
	void Pause();
	void Resume();
	void Restart();
	void Retry() { Restart(); }
	void Redeploy();
	void ToTitle();
	void SetDifficulty(FName Name);
	/** One frame. Returns whether the simulation is live (the player, the weapon and the enemies update after). */
	bool Update(double Dt, const FMIFlowPlayer& Player, bool bInteractHeld);

	// What the rest of the game tells the flow (src/game.js listeners).
	void OnPlayerDead();
	void OnPlayerHit() { SinceHit = 0; }
	void OnEnemyEvent(const FMIEnemyEvent& Ev);
	/** Hands the enemies' events of this frame to the caller (after the flow has reacted to each, once). */
	void DrainEnemies(TArray<FMIEnemyEvent>& Out);

	EMIGameState GetState() const { return State; }
	FName GetMode() const { return Mode; }
	FName GetDifficulty() const { return Difficulty; }
	double GetClock() const { return Clock; }
	double GetStateTime() const { return StateTime; }
	const FMIFlowView& View() const { return ViewState; }
	const TOptional<FMIRunCard>& Card() const { return CardShown; }
	TArray<FMIFlowEvent>& Events() { return PendingEvents; }
	const FMIRadio& GetRadio() const { return Radio; }

	struct FRun
	{
		double Time = 0;
		int32 Reels = 0, Total = 3, Retries = 0, Wave = 0, Kills = 0, Shots = 0, Hits = 0;
		double Score = 0;
	};
	const FRun& GetRun() const { return Run; }
	int32 QueueLength() const { return Queue.Num(); }
	int32 MaxAliveNow() const { return MaxAlive; }
	int32 PursuitLeftNow() const { return PursuitLeft; }
	double Progress() const { return GrabProgress; }
	/** The objective being held (its index), or INDEX_NONE. */
	int32 GrabbingObjective() const { return GrabTarget; }
	bool AllSecured() const { return Mode == FName(TEXT("mission")) && Run.Total > 0 && Run.Reels >= Run.Total; }
	bool IsSecured(int32 Objective) const { return Secured.Contains(Objective); }
	/** Dev (the demo capture, MIDemo `secure`): counts an objective as taken with no event, no radio and no wave,
	 *  as if it had been taken earlier in the run. Not in shipping builds. */
	void DevSecureQuietly(int32 Objective);
	int32 WavesCleared() const { return Cleared; }
	bool HoldoutActive() const { return bHoldoutActive; }

private:
	struct FArrival
	{
		FName Type;
		double At = 0;
		FVector Pos = FVector::ZeroVector;
		int32 Tries = 0;
	};

	void ForwardEnemyEvents();
	void RequeueRecycled();
	void SetState(EMIGameState Next);
	void Note(FName Name, const FString& Text = FString(), double A = 0, double B = 0, double C = 0);
	void ApplyWaveScale();
	void ApplyDifficulty();
	void Reset();
	void Begin(FName InMode, bool bSkipIntro, bool bQuick);
	void FinishIntro();
	void RefreshObjective();
	void RefreshTally();
	void ShowPrompt(const FString* Text, double Progress);
	bool ChoosePosition(FName Type, double MinDistance, bool bStrict, FVector& Out);
	void SpawnPatrol();
	bool QueueWave(const TArray<FName>& Order, double FirstDelay, double Stagger, FString& OutFrom);
	void PumpQueue();
	int32 ReelInReach() const;
	void UpdateInteraction(double Dt, bool bHeld);
	void Secure(int32 Objective);
	void UpdatePursuit(double Dt);
	void UpdateExtraction();
	void Complete();
	void StartWave();
	void ClearWave();
	void UpdateHoldout(double Dt);
	void SyncStats();
	void ShowCard(FName Screen);
	void EasePost(double Sat, double SatRate, double FadeTo, double FadeRate, double Dt);
	void UpdateMusic(double Dt);
	void Say(const FString& Path, const TMap<FString, FString>* Args = nullptr);
	void Hush();
	void Message(const FString& Text, double Secs);
	void Warn(const FString& Text, double Secs);

	FMIFlowTune Tune;
	FMIText Text;
	const FMILevelData* Level = nullptr;
	FMIBoxWorld* World = nullptr;
	FMIEnemyField* Enemies = nullptr;
	IMIGameHost* Host = nullptr;
	FMIRng Rng;

	EMIGameState State = EMIGameState::Title;
	FName Mode = TEXT("mission");
	FName Difficulty = TEXT("boss");
	FRun Run;
	TArray<FArrival> Queue;
	FMIFlowDifficulty Diff;
	int32 MaxAlive = 11;
	double StateTime = 0, Clock = 0, IntroLength = 0;
	bool bFullIntro = false, bIntroCard = false, bIntroRadio = false, bCardShown = false;
	TSet<int32> Secured;
	TMap<int32, double> LastUsed;
	int32 GrabTarget = INDEX_NONE;
	double GrabProgress = 0;
	bool bPromptOn = false;
	FString PromptText;
	double RefusedAt = -MIEnemy::Inf;
	bool bSaidContact = false, bSaidLow = false;
	int32 PursuitLeft = 0;
	double PursuitTimer = 0;
	double WaveAge = MIEnemy::Inf, SinceAlert = MIEnemy::Inf, SinceHit = MIEnemy::Inf;
	bool bHoldoutActive = false;
	double BreakLeft = 0;
	int32 Countdown = 0, Cleared = 0;
	double RealertIn = 0;
	FMIRadio Radio;
	FMIFlowPlayer Player;
	FMIFlowView ViewState;
	TOptional<FMIRunCard> CardShown;
	TArray<FMIFlowEvent> PendingEvents;
	int32 Handled = 0;  // enemy events already reacted to
};
