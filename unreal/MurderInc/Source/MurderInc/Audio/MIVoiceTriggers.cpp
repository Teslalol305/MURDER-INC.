#include "Audio/MIVoiceTriggers.h"

#include "Audio/MIVoiceRules.h"
#include "Core/MIEvents.h"
#include "Enemies/MIEnemies.h"
#include "Flow/MIGameRules.h"

void FMIVoiceTriggers::Init(const FMIVoiceSettings& S)
{
	MultiWindow = S.MultiKillWindow;
	Thresholds = S.StreakThresholds;
	StreakGap = S.StreakGap;
	StreakBreak = S.StreakBreakDamage;
	LowBelow = S.LowHealthBelow;
	LowSurvive = S.LowHealthSurvive;
	LastOfWaveWindow = S.LastOfWaveWindow;
	State = NAME_None;
	bHoldout = false;
	ResetRun();
}

void FMIVoiceTriggers::Fire(FName Trigger, int32 Value)
{
	if (OnTrigger)
	{
		OnTrigger(Trigger, Value);
	}
}

void FMIVoiceTriggers::ResetRun()
{
	bAlive = true;
	LastKill = -1e9;
	MultiCount = 0;
	Streak = 0;
	LastHit = -1e9;
	bLow = false;
}

void FMIVoiceTriggers::OnEnemy(const FMIEnemyEvent& E, double Now)
{
	if (E.Kind != FMIEnemyEvent::EKind::Killed || !E.bByPlayer || !bAlive)
	{
		return;
	}
	// The kind of the kill.
	if (E.Type == MIEnemy::EType::Buzzard)
	{
		Fire(TEXT("kill.buzzard"));
	}
	else if (E.Weapon == TEXT("melee"))
	{
		Fire(TEXT("kill.melee"));
	}
	else if (E.Weapon == TEXT("blast"))
	{
		Fire(TEXT("kill.explosive"));
	}
	else if (E.Part == TEXT("head"))
	{
		Fire(TEXT("kill.headshot"));
	}
	else
	{
		Fire(TEXT("kill.ordinary"));
	}

	// Several in quick succession.
	MultiCount = Now - LastKill <= MultiWindow ? MultiCount + 1 : 1;
	if (MultiCount >= 2)
	{
		Fire(TEXT("kill.multi"), MultiCount);
	}

	// The streak: broken by a long gap or by taking a real hit (OnPlayerHit).
	Streak = Now - LastKill <= StreakGap ? Streak + 1 : 1;
	if (Thresholds.Contains(Streak))
	{
		Fire(TEXT("kill.streak"), Streak);
	}
	LastKill = Now;
}

void FMIVoiceTriggers::OnFlow(const FMIFlowEvent& E, double Now)
{
	const FName N = E.Name;
	if (N == TEXT("game:state"))
	{
		const FName Prev = State;
		State = FName(E.Text);
		const bool bFromOutside = Prev.IsNone() || Prev == TEXT("title") || Prev == TEXT("dead") || Prev == TEXT("complete");
		if (State == TEXT("intro") || (State == TEXT("playing") && bFromOutside))
		{
			ResetRun();
			bHoldout = false;
			RunStart = Now;
			Fire(TEXT("run.start"));
		}
		else if (State == TEXT("title"))
		{
			ResetRun();
			if (OnSilence)
			{
				OnSilence();
			}
		}
	}
	else if (N == TEXT("player:reset"))
	{
		ResetRun();
	}
	else if (N == TEXT("holdout:wave"))
	{
		bHoldout = true;
	}
	else if (N == TEXT("objective:done"))
	{
		if (E.Text == TEXT("wave"))
		{
			bHoldout = true;
			if (Now - LastKill <= LastOfWaveWindow)
			{
				Fire(TEXT("kill.lastOfWave"));
			}
			Fire(TEXT("wave.cleared"), (int32)E.A);
		}
		else
		{
			Fire(TEXT("reel.collected"), (int32)E.A);
		}
	}
	else if (N == TEXT("objective:all"))
	{
		Fire(TEXT("extraction.called"));
	}
	else if (N == TEXT("extraction:reached"))
	{
		Fire(TEXT("run.win"));
	}
	else if (N == TEXT("hud:objective"))
	{
		// The first objective of a run arrives with its start: that moment belongs to run.start.
		if (State == TEXT("playing") && Now - RunStart > 2.0)
		{
			Fire(TEXT("objective.update"));
		}
	}
	else if (N == TEXT("menus:card"))
	{
		if (E.Text == TEXT("complete"))
		{
			Fire(TEXT("results.complete"));
		}
		else if (E.Text == TEXT("dead"))
		{
			Fire(bHoldout ? FName(TEXT("results.holdout")) : FName(TEXT("results.dead")));
		}
	}
}

void FMIVoiceTriggers::OnPlayerHit(const FMIPlayerHitEvent& E, double Now)
{
	LastHit = Now;
	if (E.Amount >= StreakBreak)
	{
		Streak = 0;
	}
	if (E.Health > 0.0 && E.Health < LowBelow)
	{
		bLow = true;
	}
}

void FMIVoiceTriggers::OnPlayerDead(double Now)
{
	bAlive = false;
	bLow = false;
	Streak = 0;
	if (OnSilence)
	{
		OnSilence();
	}
}

void FMIVoiceTriggers::Tick(double Now)
{
	if (bLow && bAlive && Now - LastHit >= LowSurvive)
	{
		bLow = false;
		Fire(TEXT("health.lowSurvived"));
	}
}
