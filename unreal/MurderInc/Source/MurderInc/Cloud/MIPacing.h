#pragma once

#include "CoreMinimal.h"

/**
 * Why a streamed game needs its own pacing (measured on the box, docs/unreal/PROGRESS.md "Version 3, release A"):
 * a game that renders off screen has no display to wait for, and Unreal then never waits for the GPU at the end of
 * a frame. When the GPU is slower than the game's frame rate, the game keeps handing it frames (up to the 60 a second
 * of the cap), the unfinished frames pile up, and the first thing that does wait for a GPU result (the occlusion
 * read-back at the start of a frame, Pixel Streaming's capture fence) waits for the whole pile: one frame of half a
 * second to seven seconds. Turning made it visible because the engine skips that read-back while the view moves.
 *
 * Two parts keep that from happening:
 *  - FMIGpuPacer: the game does not start a frame while the GPU still owes it more than a set number of frames, so
 *    the pile cannot grow, whatever the GPU's speed;
 *  - FMIFrameRateGovernor: the frame-rate target (60, 45 or 30 a second) drops when the GPU cannot keep up even at
 *    the smallest picture dynamic resolution may draw, so the GPU keeps head-room and the pacer has nothing to do.
 */

/**
 * The frame-rate target of a streamed game: 60, 45 or 30 frames a second. Pure decision logic (no engine state): the
 * caller feeds it the GPU's time per frame and applies the target (t.MaxFPS, the stream's frame rate, dynamic
 * resolution's frame time).
 *
 * Down, at once, and only in live play: the GPU's time has been over OverShare of the frame time for DropAfter
 * seconds although dynamic resolution is already at its smallest picture (or the pacer had to hold the game back
 * for the GPU). Lowering the target needs no new shaders, so it is safe in the middle of a fight. Outside live play
 * nothing drops: the start of the game is full of long frames on any card, and a target lost there would stay lost
 * for the first run on a card that is not idle enough for a rise. OverShare is 90 %: measured, a GPU at 80 to
 * 87 % of the frame time holds the rate (the pacer takes the odd late frame), and at 70 % a card that held 60 was
 * put at 45 (docs/unreal/PROGRESS.md "Version 3, release A", runs d2, d5, d6).
 * Up, only at a safe moment (a card, a set-up screen: not in live play): the GPU's time has been under UnderShare of
 * the frame time for RaiseAfter seconds. A rise that does not hold (the target drops again within RetryWindow
 * seconds) doubles the wait before the next try.
 */
struct MURDERINC_API FMIFrameRateGovernor
{
	static constexpr int32 NumTargets = 3;
	static constexpr int32 Targets[NumTargets] = {60, 45, 30};

	// Tuning ([MICloud] and the MI.Cloud.* console variables).
	double OverShare = 0.90;
	double DropAfter = 1.0;
	double UnderShare = 0.45;
	double RaiseAfter = 10.0;
	double RetryWindow = 30.0;
	double MaxRaiseAfter = 160.0;

	struct FInput
	{
		/** Time since the last update. */
		double Seconds = 0.0;
		/** The GPU's time per frame, averaged since the last update, in ms (0: not known). */
		double GpuMs = 0.0;
		/** Dynamic resolution cannot draw a smaller picture (it is at its minimum, or it is off). */
		bool bSmallestPicture = false;
		/** The pacer held the game back for the GPU for a good part of the time since the last update. */
		bool bHeldBack = false;
		/** Not in live play: the target may rise, and it does not drop. */
		bool bSafeMoment = false;
	};

	/** One step. True: the target changed (Target() is the new one, Why() says why in words for the log). */
	bool Update(const FInput& In);

	int32 Target() const { return Targets[Index]; }
	double FrameMs() const { return 1000.0 / Target(); }
	int32 GetIndex() const { return Index; }
	const FString& Why() const { return Reason; }

	/** Fixes the target (launch option -MIFps=, MI.Cloud.FpsTarget, or a t.MaxFPS set by hand): 0 lets it move again. */
	void Pin(int32 FramesPerSecond);
	bool IsPinned() const { return bPinned; }

	/** The target at or below a frame rate (60 for 0 or anything above 60: a cap that is off). */
	static int32 TargetFor(int32 FramesPerSecond);

private:
	int32 Index = 0;
	bool bPinned = false;
	double OverFor = 0.0, UnderFor = 0.0, SinceRaise = 1e9, RaiseWait = 0.0;
	FString Reason;
};

/**
 * What a visitor may tune from outside the game: the launch option -MICVars= and a viewer's console commands
 * (E3DS's "Unreal console commands to run at start" field, the player page). Only the listed families of console
 * variables, and the ones that could exhaust the server's GPU only within a range: both reach the game from a
 * stream link anybody can edit.
 */
namespace MITuning
{
	/** True when the variable may be set to the value (an empty value: only read). */
	MURDERINC_API bool IsAllowed(const FString& Name, const FString& Value);
	/** The families, for the log and the docs. */
	MURDERINC_API FString AllowedList();
	/**
	 * Splits the launch option's text "name=value,name=value" (commas or semicolons; spaces and quotes around it are
	 * dropped) into the pairs that may be set and the entries that are refused (not in the list, out of range, or not
	 * of the form name=value).
	 */
	MURDERINC_API void ParseOption(const FString& Text, TArray<TPair<FString, FString>>& OutAllowed, TArray<FString>& OutRefused);
}

/**
 * Holds the game back while the GPU still owes it frames. At the end of every frame the game thread asks the render
 * thread to put a GPU fence behind that frame's commands; at the start of the next frame, after the frame cap's
 * sleep and right before input is read, it waits (asleep in steps of a fifth of a millisecond) until no more than
 * MaxInFlight of those fences are still unsignalled, or until WaitLimitMs has passed (then it goes on and counts a
 * time-out: the game must never hang on this; see GetPauses). With a GPU that keeps up nothing is ever waited for.
 */
class MURDERINC_API FMIGpuPacer : public TSharedFromThis<FMIGpuPacer, ESPMode::ThreadSafe>
{
public:
	FMIGpuPacer();
	~FMIGpuPacer();
	/** Game thread. Needs a renderer (not -NullRHI). */
	void Start();
	void Stop();
	bool IsRunning() const { return bRunning; }

	/** Frames the GPU may still owe when a frame starts; below 0: no limit, they are only counted. */
	int32 MaxInFlight = 1;
	double WaitLimitMs = 250.0;

	struct FStats
	{
		int32 Frames = 0;          // frames since the last Take()
		int32 Held = 0;            // of them: frames that had to wait for the GPU for more than 1 ms
		int32 TimeOuts = 0;        // waits given up at the limit
		int32 MaxInFlight = 0;     // most frames the GPU owed at the start of a frame
		double WaitMs = 0.0;       // total time waited
		double WorstWaitMs = 0.0;  // longest wait
	};
	/** The numbers since the last call (the probe line); a second, independent set for the governor. */
	FStats Take(int32 Reader);
	/**
	 * How often three waits in a row ran into the limit (a GPU that needs more than WaitLimitMs for a frame: a long
	 * hitch, a cold start, or fences that are never signalled). The pacer then lets the game run for PauseSeconds
	 * and tries again: a game held at four frames a second would be worse than the pile it guards against, and a
	 * pacer that gave up for good would bring the pile back after the first hitch.
	 */
	int32 GetPauses() const { return Pauses; }
	double PauseSeconds = 3.0;

private:
	void OnBeginFrame();
	void OnEndFrame();
	int32 PollCompleted();

	/** The fences: written by the render thread, read and emptied by the game thread (the RHI types stay in the .cpp). */
	struct FFences;
	TSharedPtr<FFences, ESPMode::ThreadSafe> Fences;
	uint64 Enqueued = 0, Completed = 0;
	FStats Stats[2];
	FDelegateHandle BeginHandle, EndHandle;
	bool bRunning = false;
	int32 TimeOutsInARow = 0, Pauses = 0;
	double PausedUntil = 0.0;
};
