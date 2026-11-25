#pragma once

#include "CoreMinimal.h"

/**
 * The quality ladder (release 3c, docs/unreal/PREFLIGHT.md V3-2, docs/unreal/PROGRESS.md "Release 3c: the quality ladder").
 *
 * The frame-rate governor (Cloud/MIPacing.h) has two things to give a card that is too slow: a smaller picture (dynamic
 * resolution, 75 % down to 50 % of the output) and a lower frame-rate target (60, 45, 30). Measured on E3DS's card
 * (docs/unreal/DECISIONS.md, 2026-11-25), which is about a quarter of the test box's speed and may be shared: at 60 frames a
 * second and the smallest picture the card has about 4 ms in hand, which a fight uses up; and a shared card gives 36 ms at
 * 30 frames a second, with nothing left to give. The ladder is the next thing to give: steps of console variables, listed in
 * order of what they save in GPU time against what the picture loses, each applied when the GPU's time has stayed over its
 * share of the frame time at the smallest picture, and taken off again only after a long calm and at a safe moment.
 *
 * The steps are DATA ([MICloud] QualitySteps= lines of DefaultGame.ini, one line per step); this file holds no constant
 * of the cards or of the game's looks. Two parts, both free of engine state so that the tests can drive them:
 *  - FMIQualityTable: the lines read, and the value every variable of the table has at every step;
 *  - FMIQualityLadder: when to go down a step and when to go up, as a function of the GPU's time. It never moves more than
 *    once in MinGap seconds, rises only after a long calm with a margin below the level at which it falls (hysteresis), and
 *    waits twice as long for the next rise when a rise did not hold.
 */

/** One rung: what it is called, what it is expected to save, when it may be applied, and the variables it sets. */
struct MURDERINC_API FMIQualityStep
{
	FString Name;
	/** Share of the GPU's frame time the step is expected to save (0 to 0.6): the ladder works out what going back up would cost with it. */
	double Saves = 0.0;
	/** True: applied only at a calm moment (a card, a set-up screen), because changing it in play can hitch. */
	bool bCalm = false;
	/** The variables the step sets, with their values. A later step may set the same variable again; the last one at or below the step in force wins. */
	TArray<TPair<FString, FString>> CVars;
};

struct MURDERINC_API FMIQualityTable
{
	/**
	 * One line of DefaultGame.ini: "name | saves | live or calm | variable=value, variable=value".
	 * saves is a percentage ("12" for 12 %, "12%" too). False with Error filled in when the line cannot be used (a name or
	 * value with a character that could start another command, no variable, a saving outside 0 to 60 %, an unknown word).
	 */
	static bool ParseStep(const FString& Line, FMIQualityStep& Out, FString* Error = nullptr);
	/** All the lines, in order; the ones that cannot be used are left out and named in Errors. At most MaxSteps. */
	static TArray<FMIQualityStep> Parse(const TArray<FString>& Lines, TArray<FString>* Errors = nullptr);
	static constexpr int32 MaxSteps = 12;

	/** Every variable the table mentions, once, in the order it first appears. */
	static TArray<FString> Names(const TArray<FMIQualityStep>& Steps);
	/**
	 * The value of Name when step Step is in force (0: none, the variable keeps its baseline): the value of the last step
	 * at or below Step that sets it. False when no step at or below sets it (the baseline holds).
	 */
	static bool ValueAt(const TArray<FMIQualityStep>& Steps, int32 Step, const FString& Name, FString& OutValue);
};

/**
 * When to go down and up. Pure decision logic: the caller feeds it the GPU's time and applies the step it ends on.
 *
 * Down, one step, when in live play (or, for a step that may only be applied at a calm moment, at the next one) with the
 * picture at its smallest the GPU's time has been over DownLoad of the frame time of the frame-rate target in force (or the
 * game was held back by the GPU) for DownAfter seconds, and the last change was MinGap seconds ago. DownLoad is under
 * the frame-rate governor's own limit (the whole frame time), so at 60 frames a second the ladder acts while the governor
 * still holds the rate: the head-room a fight needs; at 30 it is the last thing left to give.
 *
 * Up, one step, only at a safe moment, only when the target is the highest one (a rate comes back before a look does), when
 * the GPU's time, worked out for the step above with that step's expected saving, would be under UpLoad of the frame time for
 * UpAfter seconds. UpLoad is well under DownLoad (a fight costs about a fifth more than the average: 0.7 x 1.2 is under 0.85),
 * so a step that is taken off is not at once needed again. A rise that did not hold (the ladder fell again within RetryWindow
 * seconds) doubles the wait for the next one, up to MaxUpAfter.
 */
struct MURDERINC_API FMIQualityLadder
{
	// Tuning ([MICloud] and the MI.Cloud.Quality* console variables).
	double DownLoad = 0.85;
	double UpLoad = 0.70;
	double DownAfter = 3.0;
	double UpAfter = 60.0;
	double MinGap = 10.0;
	double RetryWindow = 120.0;
	double MaxUpAfter = 480.0;

	struct FInput
	{
		/** Time since the last update. */
		double Seconds = 0.0;
		/** The GPU's time per frame, averaged since the last update, in ms (0: not known). */
		double GpuMs = 0.0;
		/** What it would be at the smallest picture (0: not known, or the picture is the smallest: GpuMs is used). */
		double GpuMsSmallest = 0.0;
		/** The frame time of the frame-rate target in force, in ms. */
		double FrameMs = 1000.0 / 60.0;
		/** Dynamic resolution cannot draw a smaller picture (it is at its minimum, or it is off). */
		bool bSmallestPicture = false;
		/** The game fell short of the target's rate because it had to wait for the GPU. */
		bool bHeldBack = false;
		/** Not in live play: a card, a set-up screen. */
		bool bSafeMoment = false;
		/** The frame-rate target is the highest one. */
		bool bTargetAtTop = true;
	};
	enum class EChange { None, Down, Up };

	/** The rungs: what each saves, and whether it may only be applied at a calm moment. The step in force goes back to 0. */
	void Configure(const TArray<FMIQualityStep>& Steps);
	/** One update. Down or Up: Step() is the new step and Why() says why. */
	EChange Update(const FInput& In);

	/** The step in force: 0 is full quality, 1 the first rung. */
	int32 Step() const { return Current; }
	int32 NumSteps() const { return Rungs.Num(); }
	const FString& Why() const { return Reason; }

	/** Fixes the step (launch option -MIQuality=, MI.Cloud.QualityStep): below 0 lets it move again. A pin takes effect at once, whatever the load. */
	void Pin(int32 Step);
	bool IsPinned() const { return bPinned; }
	/** Off: the step goes back to 0 and stays there. */
	void SetEnabled(bool bOn);
	bool IsEnabled() const { return bEnabled; }
	/** How long the next rise waits, in seconds. */
	double UpWait() const { return UpWaitNow; }

private:
	struct FRung { double Saves = 0.0; bool bCalm = false; };
	TArray<FRung> Rungs;
	int32 Current = 0;
	bool bPinned = false, bEnabled = true;
	double OverFor = 0.0, UnderFor = 0.0, SinceChange = 1e9, SinceUp = 1e9, UpWaitNow = 0.0;
	FString Reason;
};
