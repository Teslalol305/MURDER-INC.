#pragma once

#include "CoreMinimal.h"
#include "Math/RandomStream.h"

class FJsonObject;

/**
 * The player character's voice lines (barks): data (Content/Data/voice.json) and the rules that decide when a line
 * plays. Plain C++: no engine audio, no actors, so the automation tests drive it with a clock and a seed.
 * The triggers come from FMIVoiceTriggers (event bus only); the host (UMIAudioSubsystem) plays what Tick returns.
 * docs/unreal/AUDIO.md section 2.
 */

struct FMIVoiceTake
{
	FString File;       // relative to Content/Audio/Voice/<character>/
	FName Intensity;    // shout, spoken, breath
	bool bPlaceholder = true;
	double BleepStart = 0.0;
	double BleepEnd = 0.0;
};

struct FMIVoiceTriggerRule
{
	double Chance = 1.0;
	int32 AtLeast = 0;  // kill.streak: the streak value must be at least this
	int32 Priority = 0; // > 0: the line's priority when this trigger brought it (the line's own otherwise)
	/** Takes of these intensities are preferred for this trigger (any take when none matches). */
	TArray<FName> Intensity;
	/** A story beat that must be heard: ignores the line's cooldown, the global cooldown and the repeat decay. */
	bool bAlways = false;
	/** > 0: waits this many seconds behind a playing line (overrides the line's queueable). */
	double Queueable = -1.0;
	/** Speaks only when nothing else from the same coalescing window spoke (never queues). */
	bool bOnlyIfSilent = false;
};

struct FMIVoiceLine
{
	FName Id;
	FString Text;
	FString Speaker;            // empty: the character's speaker
	int32 Priority = 10;
	double Cooldown = 10.0;
	bool bInterruptible = true;
	double Volume = 1.0;
	double Queueable = 0.0;     // > 0: a line blocked by a playing one waits up to this many seconds
	bool bProfane = false;
	bool bAnswerOnly = false;
	FName AnswerLine;
	double AnswerDelay = 0.3;
	TMap<FName, FMIVoiceTriggerRule> Triggers;
	TArray<FMIVoiceTake> Takes;
	FName CleanMode;            // swap, bleep
	FString CleanText;
	TArray<FMIVoiceTake> CleanTakes;
};

struct FMIVoiceCharacter
{
	FName Id;
	FString Speaker;
	TArray<FMIVoiceLine> Lines;

	const FMIVoiceLine* Find(FName Line) const;
};

struct FMIVoiceFrequency
{
	double Chance = 1.0;
	double Cooldown = 1.0;
	double GlobalCooldown = 1.0;
};

struct FMIVoiceOptions
{
	double Volume = 1.0;
	bool bSubtitles = true;
	FName Frequency = TEXT("normal");  // off, rare, normal, often
	bool bClean = false;
};

struct FMIVoiceSettings
{
	int32 Seed = 1;
	double GlobalCooldown = 6.0;
	double CoalesceWindow = 0.3;
	double AfterLineGap = 0.8;
	int32 InterruptMargin = 30;
	TMap<FName, double> Duck;  // category -> factor while a line plays
	double DuckAttack = 0.06;
	double DuckRelease = 0.45;
	double MultiKillWindow = 1.5;
	TArray<int32> StreakThresholds;
	double StreakGap = 25.0;
	double StreakBreakDamage = 1.0;
	double LowHealthBelow = 30.0;
	double LowHealthSurvive = 6.0;
	double LastOfWaveWindow = 0.5;
	TMap<FName, FMIVoiceFrequency> Frequency;
	FMIVoiceOptions Defaults;
	double SubtitleExtra = 0.6;
	double SubtitleMin = 1.2;
	/** Each play of a line in a run multiplies its later chances by this (1: no decay). */
	double RepeatDecay = 1.0;
	/** Ordinary kill barks: a line one of these brought is never cut by another of these (only progress and story beats cut). */
	TArray<FName> BarkTriggers;
	/** Hold the Block: every this many waves cleared fires wave.milestone (0: never). */
	int32 WaveMilestone = 0;
};

struct MURDERINC_API FMIVoiceData
{
	FMIVoiceSettings Settings;
	FName Default;
	TMap<FName, FMIVoiceCharacter> Characters;
	/** Every trigger name voice.json documents (the "triggers" table). */
	TArray<FName> KnownTriggers;

	/** Takes of every character (clean takes included), and how many of them are placeholders. */
	void CountTakes(int32& OutTakes, int32& OutPlaceholders) const;

	static bool Parse(const TSharedPtr<FJsonObject>& Root, FMIVoiceData& Out, FString& OutError);
	/** Content/Data/voice.json. */
	static bool Load(FMIVoiceData& Out, FString& OutError);
};

/** One line to play now: what the host needs (asset, volume, subtitle) and why. */
struct FMIVoicePlay
{
	FName Character;
	FName Line;
	FName Trigger;
	int32 Take = 0;
	FString File;        // relative to Content/Audio/Voice/<character>/
	FString Text;        // the subtitle
	FString Speaker;
	double Volume = 1.0; // line volume x voice option volume
	double Start = 0.0;
	double Secs = 0.0;   // the take's length as the rules assumed it
	bool bInterrupt = false;  // stop the line that is playing first
	bool bBleep = false;
	double BleepStart = 0.0;
	double BleepEnd = 0.0;
	bool bAnswer = false;
	bool bPlaceholder = true;
	FName Intensity;
};

class MURDERINC_API FMIVoiceRules
{
public:
	/** Seconds of a take (the host measures its assets; tests and the offline mix read the WAV files). */
	TFunction<double(FName Character, const FString& File)> TakeSecs;

	void Init(const FMIVoiceData* InData, FName InCharacter, const FMIVoiceOptions& InOptions, int32 SeedOffset = 0);
	void SetOptions(const FMIVoiceOptions& InOptions) { Options = InOptions; }
	const FMIVoiceOptions& GetOptions() const { return Options; }
	/** Another crew member: his own line set (an empty set is silent). Cooldowns restart. */
	void SetCharacter(FName InCharacter);
	FName GetCharacter() const { return Character; }

	/** A trigger from FMIVoiceTriggers. Triggers within the coalescing window are judged together. */
	void Trigger(FName TriggerName, double Now, int32 Value = 0);
	/** Resolve the window, the queue and pending answers; appends what starts now. */
	void Tick(double Now, TArray<FMIVoicePlay>& Out);
	/** Death, a run reset: nothing pending, nothing queued; the playing line is cut (the host fades it). */
	void Silence(double Now);
	/** A new run: the repeat decay starts again. */
	void NewRun();
	/** Plays of a line in this run (the repeat decay). */
	int32 PlaysThisRun(FName Line) const { return RunPlays.FindRef(Line); }

	bool IsSpeaking(double Now) const { return Now < SpeakingUntil; }
	/** Time the line last started, or a large negative number. */
	double LastStart(FName Line) const;
	int32 Played() const { return PlayedCount; }
	FName CurrentLine() const { return Current; }

private:
	struct FPending
	{
		FName Trigger;
		int32 Value = 0;
		int32 Order = 0;
	};
	struct FQueued
	{
		FName Line;
		FName Trigger;
		int32 Priority = 0;
		double Deadline = 0.0;
		TArray<FName> Intensity;
	};
	struct FAnswer
	{
		FName Line;
		double At = 0.0;
	};

	const FMIVoiceCharacter* Set() const;
	const FMIVoiceFrequency& Freq() const;
	bool CoolingDown(const FMIVoiceLine& Line, double Now) const;
	bool CanStart(int32 Priority, FName TriggerName, double Now, bool bQueued, bool bAlways, bool& bOutInterrupt) const;
	bool IsBark(FName TriggerName) const;
	void Start(const FMIVoiceLine& Line, int32 Priority, FName TriggerName, const TArray<FName>& Intensity, double Now, bool bInterrupt, bool bAnswer, TArray<FMIVoicePlay>& Out);

	const FMIVoiceData* Data = nullptr;
	FName Character;
	FMIVoiceOptions Options;
	FRandomStream Rng;

	TArray<FPending> Window;
	double WindowOpened = -1.0;
	int32 WindowOrder = 0;
	TArray<FQueued> Queue;
	TArray<FAnswer> Answers;

	TMap<FName, double> LastPlay;
	TMap<FName, int32> LastTake;
	TMap<FName, int32> RunPlays;
	double LastAnyStart = -1e9;
	double LastAnyEnd = -1e9;
	int32 LastPriority = 0;
	FName Current;
	FName CurrentTrigger;
	int32 CurrentPriority = 0;
	bool bCurrentInterruptible = true;
	double SpeakingUntil = -1e9;
	int32 PlayedCount = 0;
};
