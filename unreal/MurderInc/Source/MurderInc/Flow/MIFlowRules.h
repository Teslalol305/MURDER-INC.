#pragma once

#include "CoreMinimal.h"
#include "World/MILevelData.h"

class FJsonObject;
class FJsonValue;

/**
 * The flow's pure rules (src/game/spawn.js, waves.js, stats.js, music.js, radio.js and src/config/flow.js) and its
 * tables: config.json `flow` in web units, the copy deck of text.json. Checked by MurderInc.Golden.FlowRules.
 */

/** A one-parameter formula exported as {"$function": {"source": "(n) => Math.min(5 + 2 * n, 30)"}}. */
struct MURDERINC_API FMIFormula
{
	FString Source;
	double Eval(double Arg) const;
	static FMIFormula From(const TSharedPtr<FJsonValue>& V);
};

struct FMIFlowDifficulty
{
	double RegenDelay = 0, RegenRate = 0;
	int32 PatrolBuzzard = 0, PatrolGoon = 0;
	TArray<TPair<int32, int32>> Waves;  // (buzzard, goon) after each reel
	int32 MaxAlive = 0;
	double PursuitEvery = 0;
	int32 PursuitBudget = 0;
};

struct MURDERINC_API FMIFlowTune
{
	// timing
	double Intro = 0, IntroQuick = 0, IntroFadeA = 0, IntroFadeB = 0, LocationCardAt = 0, IntroRadioAt = 0, PauseDebounce = 0, DeathCard = 0, DebriefCard = 0;
	// post
	double DeadSat = 0, DeadSatRate = 0, DeadFade = 0, DeadFadeRate = 0, DoneSat = 0, DoneSatRate = 0, DoneFade = 0, DoneFadeRate = 0;
	// interact, extraction
	double InteractRange = 0, InteractVertical = 0, FacingDot = 0, FreeRange = 0, Hold = 0, Decay = 0, InteractShake = 0;
	double ExtractVertical = 0, RefuseSecs = 0, RefuseEvery = 0;
	// spawn
	double FirstDelay = 0, Stagger = 0, Far = 0, PatrolMinDistance = 0;
	double ScoreRandom = 0, ScoreFar = 0, ScoreFarExtra = 0, ScoreFarExtraOver = 0, ScoreNearDivisor = 0, ScoreHidden = 0, ScoreRecent = 0, ScoreRecentSecs = 0;
	double Jitter = 0, AirMinHeight = 0, AirLiftA = 0, AirLiftB = 0, EyeHeight = 0, ProbeHeight = 0, TooClose = 0, CapRetry = 0, PoolRetry = 0;
	int32 PoolTries = 0;
	double AlertRadius = 0, FallbackRing = 0, BannerSecs = 0;
	// pursuit
	double PursuitFirstDelay = 0;
	int32 PursuitMinAlive = 0;
	double PursuitSpawnDelay = 0, PursuitBuzzardShare = 0, PursuitRealertEvery = 0, PursuitRealertRadius = 0;
	// holdout
	double HoldFirstDelay = 0, Breather = 0;
	int32 CountdownFrom = 0;
	double FirstSpawn = 0, HoldBannerSecs = 0, HoldRealertEvery = 0, HoldRealertRadius = 0;
	FMIFormula Total, BuzzardShare, StaggerOf, HpScale, DamageScale, CooldownScale, ExtraAlive, KillScale, WaveClear;
	double KillGoon = 0, KillBuzzard = 0;
	double ResupplyReserve = 0, ResupplyReserveCap = 0, ResupplyHeal = 0;
	int32 ExplosivesEvery = 2;
	// rating
	TArray<TPair<double, int32>> RatingTime, RatingAccuracy;
	int32 RatingNoRetries = 0;
	// music
	double MusicCalm = 0, MusicAlert = 0, MusicHot = 0, AlertHold = 0, HitHold = 0, NearDistance = 0, WaveHot = 0, WaveMinOut = 0;
	// pacing
	double RadioCharsPerSec = 0, CountdownSecs = 0, RadioGap = 0;
	FName DefaultDifficulty;
	TMap<FName, FMIFlowDifficulty> Difficulties;
	double LowWarning = 30;  // player.health.lowWarning

	const FMIFlowDifficulty& Difficulty(FName Name) const;
	static bool Parse(const TSharedPtr<FJsonObject>& Config, FMIFlowTune& Out, FString& OutError);
};

/** text.json `text`: the copy deck, with its {name} templates. */
struct MURDERINC_API FMIText
{
	TSharedPtr<FJsonObject> Root;

	/** A plain string at a dotted path ("objectives.holdout.hold"); arrays by index ("compass.3"). */
	FString Get(const FString& Path) const;
	double Secs(const FString& Path) const;
	/** A {"$template"} at Path with its arguments by name; numbers given as text are put in verbatim. */
	FString Format(const FString& Path, const TMap<FString, FString>& Args) const;
	int32 Count(const FString& Path) const;
	static bool Load(FMIText& Out, FString& OutError);
	/** Math.round(x).toLocaleString('en-US'): 12,345. */
	static FString Grouped(double X);
};

/** An authored spawn point as pickSpawn sees it. */
struct FMISpawnCandidate
{
	double Distance = 0;
	bool bHidden = false;
	double UsedAgo = 0;  // seconds, MIEnemy::Inf when never
	double Random = 0;
};

namespace MIFlow
{
	int32 CompassSector(double Dx, double Dz);
	double SpawnScore(const FMISpawnCandidate& C, const FMIFlowTune& T, double MinDistance);
	TArray<FName> MissionOrder(int32 Buzzards, int32 Goons);
	TArray<FName> HoldoutOrder(int32 Total, int32 Buzzards);

	struct FHoldoutWave
	{
		int32 Wave = 1, Total = 0, Buzzards = 0, Goons = 0;
		TArray<FName> Order;
		double Stagger = 0, Hp = 1, Damage = 1, Cooldown = 1;
		int32 ExtraAlive = 0;
	};
	FHoldoutWave HoldoutWave(int32 N, const FMIFlowTune& T);
	int32 KillScore(bool bGoon, int32 Wave, const FMIFlowTune& T);
	inline FName PursuitType(double Roll, double Share) { return Roll < Share ? FName(TEXT("buzzard")) : FName(TEXT("goon")); }
	int32 RatingPoints(double Time, int32 Shots, int32 Hits, int32 Retries, const FMIFlowTune& T);
	/** Hits per shot 0..1, or -1 when no shot was fired. */
	inline double Accuracy(int32 Shots, int32 Hits) { return Shots > 0 ? FMath::Min(1.0, static_cast<double>(Hits) / Shots) : -1.0; }

	struct FMusicState
	{
		bool bAllDone = false;
		int32 Queued = 0, Alive = 0;
		double WaveAge = 0, SinceAlert = 0, SinceHit = 0, Nearest = 0;
	};
	double MusicIntensity(const FMusicState& S, const FMIFlowTune& T);
	inline bool WaveIsOver(const FMusicState& S, const FMIFlowTune& T) { return S.WaveAge >= T.WaveMinOut && S.Alive == 0 && S.Queued == 0; }
}

/** src/game/radio.js: one speaker, lines in order. */
struct FMIRadio
{
	struct FLine
	{
		FString Text;
		double Secs = 0;
	};
	TArray<FLine> Queue;
	double Busy = 0;
	double CharsPerSec = 58, Gap = 0.3;
	FString Current;  // the line that is up ("" when none)
	double CurrentSecs = 0;
	double CurrentAge = 0;
	TFunction<void(const FString&, double)> OnLine;

	void Say(const FString& Text, double Secs);
	void Clear();
	void Update(double Dt);
};
