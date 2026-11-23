#pragma once

#include "CoreMinimal.h"

struct FMIEnemyEvent;
struct FMIFlowEvent;
struct FMIPlayerHitEvent;
struct FMIVoiceSettings;

/**
 * Turns the event bus into voice triggers (voice.json "triggers"): the kind of a kill, multi-kills, streaks, the last
 * kill of a wave, progress beats, a close call survived. Reads only event payloads, never rule state.
 * Plain C++; the host and the tests feed it and forward OnTrigger to FMIVoiceRules::Trigger.
 */
class MURDERINC_API FMIVoiceTriggers
{
public:
	TFunction<void(FName Trigger, int32 Value)> OnTrigger;
	/** The player died or the run was reset: barks must stop. */
	TFunction<void()> OnSilence;

	void Init(const FMIVoiceSettings& InSettings);

	void OnEnemy(const FMIEnemyEvent& E, double Now);
	void OnFlow(const FMIFlowEvent& E, double Now);
	void OnPlayerHit(const FMIPlayerHitEvent& E, double Now);
	void OnPlayerDead(double Now);
	void Tick(double Now);

	int32 GetStreak() const { return Streak; }
	bool IsHoldout() const { return bHoldout; }
	FName GetState() const { return State; }

private:
	void Fire(FName Trigger, int32 Value = 0);
	void ResetRun();

	double MultiWindow = 1.5;
	TArray<int32> Thresholds;
	double StreakGap = 25.0;
	double StreakBreak = 1.0;
	double LowBelow = 30.0;
	double LowSurvive = 6.0;
	double LastOfWaveWindow = 0.5;

	FName State;
	bool bHoldout = false;
	bool bAlive = true;
	double RunStart = -1e9;
	double LastKill = -1e9;
	int32 MultiCount = 0;
	int32 Streak = 0;
	double LastHit = -1e9;
	bool bLow = false;
};
