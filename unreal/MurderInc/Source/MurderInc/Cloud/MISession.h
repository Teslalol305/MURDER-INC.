#pragma once

#include "CoreMinimal.h"

/**
 * The life of a streamed game's session (release 3c): when it draws, when it idles, when it quits. Pure decision logic
 * (no engine state, no clock): UMICloudSubsystem feeds it what it knows once a frame and does what it says.
 *
 * Why the game has to do this itself. Measured on E3DS (docs/unreal/DECISIONS.md, 2026-11-25): the game of a session
 * that had ended kept running on the machine, drawing the menu at full speed, and the next session found the card
 * shared with it: 27 frames a second at 36 ms of GPU time for the second session, 18 at 55 ms for the third. E3DS's
 * documentation says an ended session "frees the machine"; it does not say that it stops the app. The launcher stops
 * other games of the package when the next session starts; this is the game's own part:
 *  - nobody watching (no viewer for IdleAfter seconds): the game idles, a few frames a second, so that it costs the
 *    card almost nothing (UMICloudSubsystem::SleepIdle);
 *  - the last viewer has been gone for ExitAfterEmpty seconds: the session is over, the game quits;
 *  - nobody ever came, ExitIfNoViewer seconds after the game started: a machine given to a session whose viewer never
 *    arrived, the game quits;
 *  - the launcher that started the game is gone (E3DS killed it, or it died): nobody can stop the game any more, it
 *    quits (FMILauncherWatch).
 * A live session is never ended: a viewer present keeps the game for as long as he stays, and a join cancels every
 * countdown (the page of a viewer who reloads reconnects within seconds: ExitAfterEmpty is 20).
 * -MIKeepAlive turns all of it off (the box's test scripts hold games with no viewer on purpose). A game that is not
 * streamed (the desktop) is never touched.
 */
struct MURDERINC_API FMISession
{
	enum class EAction : uint8
	{
		/** Draw as usual. */
		Keep,
		/** Nobody is watching: idle (a few frames a second). */
		Idle,
		/** The session is over: quit. */
		Exit,
	};

	enum class EWhy : uint8
	{
		NotStreamed,    // a desktop game: no session
		KeepAlive,      // -MIKeepAlive
		ViewerPresent,  // somebody is watching
		Waiting,        // nobody yet / nobody now, and not for long enough to do anything
		Empty,          // nobody for IdleAfter seconds: idle
		EmptyTooLong,   // the last viewer left ExitAfterEmpty seconds ago: quit
		NeverConnected, // no viewer ever came, ExitIfNoViewer seconds after the start: quit
		LauncherGone,   // the launcher is gone: quit
	};

	/** The numbers (cvars and launch options; zero turns a part off). */
	struct FOptions
	{
		bool bStreamed = true;
		bool bKeepAlive = false;
		/** Seconds with no viewer before the game idles. */
		double IdleAfter = 2.0;
		/** Frames a second while idle (0: the game never idles). */
		int32 IdleFps = 2;
		/**
		 * The game is never idled in the first seconds of its life while nobody has come yet: it is loading, compiling
		 * shaders and streaming textures then, and a first viewer should find it ready.
		 */
		double IdleStartupGrace = 10.0;
		/** Seconds after the last viewer left before the game quits (0: never). */
		double ExitAfterEmpty = 20.0;
		/** Seconds after the game's start before it quits for want of a first viewer (0: never). */
		double ExitIfNoViewer = 600.0;
		/** Seconds the launcher has to be gone before the game quits (0: not watched). */
		double LauncherGoneAfter = 5.0;
	};

	/** What the game knows. */
	struct FState
	{
		/** Viewers connected now. */
		int32 Viewers = 0;
		/** One has been connected since the game started. */
		bool bHadViewer = false;
		/** Seconds since the number of viewers last changed to or from zero (since the game's start until the first joins). */
		double SecondsSinceChange = 0.0;
		/** Seconds since the process started. */
		double SecondsSinceStart = 0.0;
		/** Seconds the launcher has been gone; below 0: it is there, or nobody watches it. */
		double LauncherGoneFor = -1.0;
	};

	struct FDecision
	{
		EAction Action = EAction::Keep;
		EWhy Why = EWhy::Waiting;
	};

	/** What to do now. */
	static FDecision Decide(const FOptions& Options, const FState& State);

	/** The decision in words, for the log. */
	static FString Describe(const FDecision& Decision, const FOptions& Options, const FState& State);

	/** The numbers as a cvar or a launch option gives them: out of range values fall back to the defaults. */
	static FOptions Sanitize(FOptions Options);
};

/**
 * Who is connected and since when: the bookkeeping that UMICloudSubsystem keeps for FMISession::Decide, kept apart so
 * that the tests drive the very code the game runs (a join cancels every countdown; a viewer present resets nothing).
 */
struct MURDERINC_API FMISessionClock
{
	/** The process started (or the game's clock begins) at Now. */
	void Start(double Now)
	{
		ProcessStart = Changed = Now;
		Viewers = 0;
		bHadViewer = false;
	}
	/** A viewer joined: whoever was counting down stops. */
	void Joined(double Now)
	{
		if (Viewers == 0)
		{
			Changed = Now;
		}
		++Viewers;
		bHadViewer = true;
	}
	/** The last viewer left (E3DS ended the stream, or the page was reloaded): the countdown starts. */
	void AllLeft(double Now)
	{
		if (Viewers > 0)
		{
			Viewers = 0;
			Changed = Now;
		}
	}
	int32 GetViewers() const { return Viewers; }
	bool HadViewer() const { return bHadViewer; }

	FMISession::FState Snapshot(double Now, double LauncherGoneFor = -1.0) const
	{
		FMISession::FState S;
		S.Viewers = Viewers;
		S.bHadViewer = bHadViewer;
		S.SecondsSinceChange = FMath::Max(0.0, Now - Changed);
		S.SecondsSinceStart = FMath::Max(0.0, Now - ProcessStart);
		S.LauncherGoneFor = LauncherGoneFor;
		return S;
	}

private:
	double ProcessStart = 0.0, Changed = 0.0;
	int32 Viewers = 0;
	bool bHadViewer = false;
};

/**
 * Whether the launcher that started the game is still there. The launcher gives the game its own process id
 * (-MILauncherPid=<pid>); the game looks at it every PollEvery seconds. Pure logic: UMICloudSubsystem does the looking
 * (ProbeProcess) and feeds the answer.
 *
 * Careful in both directions. A launcher that is gone leaves a game that nobody can stop, so after GoneAfter seconds the
 * game quits (the launcher's own watchdog does the same from the other side). But a game must never quit because a
 * process id means nothing to it (a launcher in another process namespace, a /proc that hides other users' processes):
 * the watch starts only when the launcher has been seen alive, and an answer of "cannot tell" is "alive". A zombie (the
 * launcher was killed and nobody collected it) and a process id taken by another process since are "gone".
 */
struct MURDERINC_API FMILauncherWatch
{
	enum class EProbe : uint8
	{
		/** The process is there. */
		Alive,
		/** The process is gone (or a zombie, or another process now). */
		Gone,
		/** Cannot tell (no /proc, no permission, not Linux). */
		Unknown,
	};

	double PollEvery = 2.0;
	double GoneAfter = 5.0;

	/** True when the launcher should be looked at now (every PollEvery seconds, from the start). */
	bool IsDue(double Now) const { return bWatching && Now >= NextPoll; }

	/** How long the launcher has been gone at Now, in seconds (below 0: it is there, or nobody watches it). */
	double GetGoneFor(double Now) const { return bWatching && GoneSince >= 0.0 ? Now - GoneSince : -1.0; }

	/** Starts the watch for a process id (0 or 1 or less: nothing is watched). */
	void Start(int32 InPid, double Now);
	bool IsWatching() const { return bWatching; }
	int32 GetPid() const { return Pid; }
	/** True once the first answer was "gone" before it was ever "alive": the id is not ours to watch, the watch is off. */
	bool IsDisarmed() const { return bDisarmed; }

	/** One answer. Returns how long the launcher has been gone, in seconds (below 0: not gone, or not watched). */
	double Feed(EProbe Answer, double Now);

private:
	int32 Pid = 0;
	bool bWatching = false, bDisarmed = false, bSeenAlive = false;
	double NextPoll = 0.0, GoneSince = -1.0;
};

/**
 * The looking itself, for the game (Linux; elsewhere always Unknown): kill(pid, 0) for "is there such a process" (it
 * says ESRCH for none and EPERM for one of another user, so a /proc that hides processes does not fool it), then
 * /proc/<pid>/stat for "is it a zombie" and "is it still the process the game saw first" (the start time).
 * InOutStartTime is 0 on the first call and remembered after it.
 */
MURDERINC_API FMILauncherWatch::EProbe MIProbeProcess(int32 Pid, uint64& InOutStartTime);
