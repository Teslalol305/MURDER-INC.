// Release 3c (the session): what a streamed game does when nobody watches, when its session is over and when its launcher
// is gone, how the encoder's range is worked out around the QPs E3DS asks for, and how the round trip is read. Pure
// logic (Cloud/MISession.h, Cloud/MIStreamQuality.h): no world, no renderer, no stream.
//   MurderInc.Cloud.SessionDecision   viewers, seconds since the last change, options -> keep, idle, exit; a viewer that
//                                     is present keeps the game for hours, a join cancels every countdown, a reload
//                                     (leave and join within seconds) never ends the game; -MIKeepAlive; zero turns
//                                     a part off; bad numbers fall back
//   MurderInc.Cloud.SessionClock      the bookkeeping the game keeps, driven through whole sessions
//   MurderInc.Cloud.LauncherWatch     the launcher's answers: gone for 5 s quits, "cannot tell" never does, an id that
//                                     was never seen alive is not watched; and the real looking at processes
//   MurderInc.Cloud.EncoderRange      Medium 34 gives 24 to 42, High 16 gives 8 to 24; the floor, the ceiling, -MIQpExact;
//                                     the quality the plugin is given gives the QP back for every QP; the page's commands
//                                     and the launch options are read as Pixel Streaming reads them
//   MurderInc.Cloud.RoundTrip         a 0 is not a measurement, a steady value stays, the viewers' change clears it
//   MurderInc.Cloud.SessionDefaults   the console variables a package starts with

#include "Cloud/MICloud.h"
#include "Cloud/MISession.h"
#include "Cloud/MIStreamQuality.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformProcess.h"
#include "Misc/AutomationTest.h"
#include "Tests/MITestUtil.h"

#include <limits>

#if PLATFORM_LINUX
#include <csignal>
#include <unistd.h>
#endif

#if WITH_AUTOMATION_TESTS

namespace MISessionTestsPrivate
{
	using EAction = FMISession::EAction;
	using EWhy = FMISession::EWhy;

	FMISession::FDecision Decide(const FMISession::FOptions& O, const FMISessionClock& C, double Now, double LauncherGoneFor = -1.0)
	{
		return FMISession::Decide(O, C.Snapshot(Now, LauncherGoneFor));
	}

	/** The state of a game whose process started at 0 and in which the viewer count last changed SinceChange seconds ago. */
	FMISession::FState State(int32 Viewers, bool bHad, double SinceChange, double SinceStart, double LauncherGone = -1.0)
	{
		FMISession::FState S;
		S.Viewers = Viewers;
		S.bHadViewer = bHad;
		S.SecondsSinceChange = SinceChange;
		S.SecondsSinceStart = SinceStart;
		S.SecondsSinceReady = SinceStart;
		S.LauncherGoneFor = LauncherGone;
		return S;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICloudSessionDecisionTest, "MurderInc.Cloud.SessionDecision", MITest::Flags)

bool FMICloudSessionDecisionTest::RunTest(const FString& Parameters)
{
	using namespace MISessionTestsPrivate;
	const FMISession::FOptions O;  // 2 s, 2 frames a second, 10 s of start-up, 60 s, 600 s, 5 s
	TestEqual(TEXT("the defaults: idle after 2 s"), O.IdleAfter, 2.0);
	TestEqual(TEXT("the defaults: 2 frames a second"), O.IdleFps, 2);
	TestEqual(TEXT("the defaults: the last viewer gone for 60 s ends the game"), O.ExitAfterEmpty, 60.0);
	TestEqual(TEXT("the defaults: nobody in 600 s ends the game"), O.ExitIfNoViewer, 600.0);
	TestEqual(TEXT("the defaults: the launcher gone for 5 s ends the game"), O.LauncherGoneAfter, 5.0);

	// A game that is not streamed has no session: whatever the numbers say, it keeps drawing and never quits.
	{
		FMISession::FOptions N = O;
		N.bStreamed = false;
		for (const double T : {0.0, 5.0, 25.0, 700.0, 1e7})
		{
			const FMISession::FDecision D = FMISession::Decide(N, State(0, true, T, T, T));
			TestTrue(FString::Printf(TEXT("not streamed, nobody for %.0f s, launcher gone: keeps"), T), D.Action == EAction::Keep && D.Why == EWhy::NotStreamed);
		}
	}
	// -MIKeepAlive: the same, whatever happens (the box's test scripts).
	{
		FMISession::FOptions K = O;
		K.bKeepAlive = true;
		for (const double T : {0.0, 5.0, 25.0, 700.0, 1e7})
		{
			const FMISession::FDecision D = FMISession::Decide(K, State(0, T > 100.0, T, T, T));
			TestTrue(FString::Printf(TEXT("-MIKeepAlive, nobody for %.0f s, launcher gone: keeps"), T), D.Action == EAction::Keep && D.Why == EWhy::KeepAlive);
		}
	}

	// After the last viewer left (a viewer had been there).
	{
		const auto After = [&O](double Seconds) { return FMISession::Decide(O, State(0, true, Seconds, 1000.0 + Seconds)).Action; };
		TestTrue(TEXT("left 0 s ago: keeps drawing"), After(0.0) == EAction::Keep);
		TestTrue(TEXT("1.9 s: keeps drawing (a reload reconnects before this)"), After(1.9) == EAction::Keep);
		TestTrue(TEXT("2.0 s: idles"), After(2.0) == EAction::Idle);
		TestTrue(TEXT("10 s: idles"), After(10.0) == EAction::Idle);
		TestTrue(TEXT("19.9 s: idles, does not quit"), After(19.9) == EAction::Idle);
		TestTrue(TEXT("20.0 s: quits"), After(20.0) == EAction::Exit);
		TestTrue(TEXT("an hour: quits"), After(3600.0) == EAction::Exit);
		TestTrue(TEXT("the reason is named"), FMISession::Decide(O, State(0, true, 25.0, 1025.0)).Why == EWhy::EmptyTooLong);
		AddInfo(FString::Printf(TEXT("log line: %s"), *FMISession::Describe(FMISession::Decide(O, State(0, true, 25.0, 1025.0)), O, State(0, true, 25.0, 1025.0))));
	}
	// A viewer present keeps the game: for any time, whatever the other numbers say.
	{
		for (const double T : {0.0, 25.0, 600.0, 36000.0, 1e9})
		{
			const FMISession::FDecision D = FMISession::Decide(O, State(1, true, T, T + 5.0));
			TestTrue(FString::Printf(TEXT("a viewer for %.0f s: keeps drawing, never quits"), T), D.Action == EAction::Keep && D.Why == EWhy::ViewerPresent);
		}
		TestTrue(TEXT("two viewers: keeps"), FMISession::Decide(O, State(2, true, 7000.0, 8000.0)).Action == EAction::Keep);
	}
	// Nobody has come yet.
	{
		const auto Before = [&O](double Seconds) { return FMISession::Decide(O, State(0, false, Seconds, Seconds)).Action; };
		TestTrue(TEXT("0 s after the start: keeps drawing"), Before(0.0) == EAction::Keep);
		TestTrue(TEXT("5 s: keeps drawing (the game is starting up)"), Before(5.0) == EAction::Keep);
		TestTrue(TEXT("9.9 s: keeps drawing"), Before(9.9) == EAction::Keep);
		TestTrue(TEXT("10 s: idles"), Before(10.0) == EAction::Idle);
		TestTrue(TEXT("599.9 s: idles, does not quit"), Before(599.9) == EAction::Idle);
		TestTrue(TEXT("600 s: quits"), Before(600.0) == EAction::Exit);
		TestTrue(TEXT("the reason is named"), FMISession::Decide(O, State(0, false, 700.0, 700.0)).Why == EWhy::NeverConnected);
	}
	// A cold start: the process is minutes old when the game becomes streamed; its start-up grace counts from there.
	{
		FMISession::FState S = State(0, false, 40.0, 40.0);
		S.SecondsSinceReady = 3.0;
		TestTrue(TEXT("40 s after the process's start but 3 s after the game became streamed: still starting up, keeps drawing"), FMISession::Decide(O, S).Action == EAction::Keep);
		S.SecondsSinceReady = 10.0;
		TestTrue(TEXT("10 s after it became streamed: idles"), FMISession::Decide(O, S).Action == EAction::Idle);
		FMISessionClock C;
		C.Start(0.0);
		TestEqual(TEXT("a clock that was never told the game is ready counts from the process's start"), C.Snapshot(25.0).SecondsSinceReady, 25.0);
		C.MarkReady(20.0);
		TestEqual(TEXT("... and one that was counts from the mark"), C.Snapshot(25.0).SecondsSinceReady, 5.0);
		TestTrue(TEXT("a game 5 s after it became streamed: keeps drawing"), Decide(O, C, 25.0).Action == EAction::Keep);
		TestTrue(TEXT("a game 11 s after it became streamed: idles"), Decide(O, C, 31.0).Action == EAction::Idle);
	}
	// The launcher: gone for 5 s ends the game, even with a viewer (its own watchdog does the same from outside).
	{
		TestTrue(TEXT("launcher not watched: -1"), FMISession::Decide(O, State(1, true, 100.0, 100.0, -1.0)).Action == EAction::Keep);
		TestTrue(TEXT("launcher gone for 4.9 s: keeps"), FMISession::Decide(O, State(1, true, 100.0, 100.0, 4.9)).Action == EAction::Keep);
		TestTrue(TEXT("launcher gone for 5 s: quits"), FMISession::Decide(O, State(1, true, 100.0, 100.0, 5.0)).Action == EAction::Exit);
		TestTrue(TEXT("... and the reason is the launcher"), FMISession::Decide(O, State(1, true, 100.0, 100.0, 5.0)).Why == EWhy::LauncherGone);
	}
	// Each part can be turned off with zero.
	{
		FMISession::FOptions N = O;
		N.IdleFps = 0;
		TestTrue(TEXT("IdleFps 0: never idles ..."), FMISession::Decide(N, State(0, true, 10.0, 1010.0)).Action == EAction::Keep);
		TestTrue(TEXT("... and still quits"), FMISession::Decide(N, State(0, true, 20.0, 1020.0)).Action == EAction::Exit);
		N = O;
		N.ExitAfterEmpty = 0.0;
		TestTrue(TEXT("ExitAfterEmpty 0: idles, never quits"), FMISession::Decide(N, State(0, true, 1e6, 1e6)).Action == EAction::Idle);
		N = O;
		N.ExitIfNoViewer = 0.0;
		TestTrue(TEXT("ExitIfNoViewer 0: idles, never quits"), FMISession::Decide(N, State(0, false, 1e6, 1e6)).Action == EAction::Idle);
		N = O;
		N.LauncherGoneAfter = 0.0;
		TestTrue(TEXT("LauncherGoneAfter 0: never"), FMISession::Decide(N, State(1, true, 100.0, 100.0, 1e6)).Action == EAction::Keep);
	}
	// Numbers from a link or a console: a number that is not one, or is under its floor, is the default or its floor.
	{
		FMISession::FOptions B = O;
		B.IdleAfter = std::numeric_limits<double>::quiet_NaN();
		B.ExitAfterEmpty = -5.0;
		B.ExitIfNoViewer = std::numeric_limits<double>::infinity();
		B.IdleFps = 5000;
		B.LauncherGoneAfter = 0.1;
		const FMISession::FOptions S = FMISession::Sanitize(B);
		TestEqual(TEXT("not a number: the default"), S.IdleAfter, 2.0);
		TestEqual(TEXT("negative: off"), S.ExitAfterEmpty, 0.0);
		TestEqual(TEXT("infinite: the default"), S.ExitIfNoViewer, 600.0);
		TestEqual(TEXT("a silly frame rate: 30 at most"), S.IdleFps, 30);
		TestEqual(TEXT("a launcher that must be gone for a tenth of a second: 2 s at least"), S.LauncherGoneAfter, 2.0);
		FMISession::FOptions Small = O;
		Small.ExitAfterEmpty = 0.5;
		TestEqual(TEXT("an exit after half a second would end a reload: 2 s at least"), FMISession::Sanitize(Small).ExitAfterEmpty, 2.0);
		FMISession::FOptions Sane = O;
		Sane.IdleAfter = 5.0;
		Sane.IdleFps = 4;
		Sane.ExitAfterEmpty = 45.0;
		const FMISession::FOptions Kept = FMISession::Sanitize(Sane);
		TestTrue(TEXT("numbers in range stay as they are"), Kept.IdleAfter == 5.0 && Kept.IdleFps == 4 && Kept.ExitAfterEmpty == 45.0);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICloudSessionClockTest, "MurderInc.Cloud.SessionClock", MITest::Flags)

bool FMICloudSessionClockTest::RunTest(const FString& Parameters)
{
	using namespace MISessionTestsPrivate;
	const FMISession::FOptions O;

	// A whole session as the stream reports it: nobody for a while, a viewer who stays for ten hours, a leave, a join.
	{
		FMISessionClock C;
		C.Start(100.0);
		TestTrue(TEXT("start-up: keeps"), Decide(O, C, 105.0).Action == EAction::Keep);
		TestTrue(TEXT("nobody for 20 s after the start: idles"), Decide(O, C, 120.0).Action == EAction::Idle);
		C.Joined(130.0);
		TestTrue(TEXT("a viewer joins: keeps"), Decide(O, C, 130.0).Action == EAction::Keep);
		bool bEverLeft = false;
		for (double T = 130.0; T < 130.0 + 36000.0; T += 1.0)
		{
			bEverLeft |= Decide(O, C, T).Action != EAction::Keep;
		}
		TestFalse(TEXT("a viewer present for ten hours: the game keeps drawing and never idles or quits"), bEverLeft);
		const double Left = 130.0 + 36000.0;
		C.AllLeft(Left);
		TestTrue(TEXT("he leaves: keeps for the first 2 s"), Decide(O, C, Left + 1.9).Action == EAction::Keep);
		TestTrue(TEXT("idles from 2 s"), Decide(O, C, Left + 2.0).Action == EAction::Idle);
		TestTrue(TEXT("still idling at 59.9 s"), Decide(O, C, Left + 59.9).Action == EAction::Idle);
		// A join at 59.9 s cancels the countdown ...
		C.Joined(Left + 59.9);
		TestTrue(TEXT("a join 0.1 s before the end: keeps"), Decide(O, C, Left + 60.0).Action == EAction::Keep);
		TestTrue(TEXT("... for as long as he stays"), Decide(O, C, Left + 5000.0).Action == EAction::Keep);
		// ... and the next one starts again from zero.
		C.AllLeft(Left + 6000.0);
		TestTrue(TEXT("a new leave: 59.9 s later it is idling, not quitting"), Decide(O, C, Left + 6059.9).Action == EAction::Idle);
		TestTrue(TEXT("60 s later it quits"), Decide(O, C, Left + 6060.0).Action == EAction::Exit);
	}
	// A page reload: the viewer leaves and a viewer joins a few seconds later, again and again: the game never quits.
	{
		FMISessionClock C;
		C.Start(0.0);
		C.Joined(30.0);
		bool bQuit = false;
		double T = 60.0;
		for (int32 Reload = 0; Reload < 200; ++Reload)
		{
			C.AllLeft(T);
			for (double D = 0.0; D < 8.0; D += 0.5)
			{
				bQuit |= Decide(O, C, T + D).Action == EAction::Exit;
			}
			T += 8.0;
			C.Joined(T);
			bQuit |= Decide(O, C, T).Action != EAction::Keep;
			T += 30.0;
		}
		TestFalse(TEXT("two hundred reloads of eight seconds each: no exit and the viewer found the game at full speed"), bQuit);
	}
	// A second viewer (E3DS's Share link) joining a session in progress, and a spurious "all left" with nobody there.
	{
		FMISessionClock C;
		C.Start(0.0);
		C.AllLeft(5.0);
		TestFalse(TEXT("an 'all left' before anyone joined is nothing"), C.HadViewer());
		C.Joined(10.0);
		C.Joined(50.0);
		TestEqual(TEXT("two viewers"), C.GetViewers(), 2);
		TestTrue(TEXT("the second join does not move the clock: the count did not change from zero"), FMath::IsNearlyEqual(C.Snapshot(60.0).SecondsSinceChange, 50.0));
		C.AllLeft(100.0);
		TestEqual(TEXT("all gone"), C.GetViewers(), 0);
		TestTrue(TEXT("a viewer had been there"), C.HadViewer());
		C.AllLeft(110.0);
		TestTrue(TEXT("a second 'all left' does not restart the countdown"), FMath::IsNearlyEqual(C.Snapshot(120.0).SecondsSinceChange, 20.0));
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICloudLauncherWatchTest, "MurderInc.Cloud.LauncherWatch", MITest::Flags)

bool FMICloudLauncherWatchTest::RunTest(const FString& Parameters)
{
	using EProbe = FMILauncherWatch::EProbe;
	{
		FMILauncherWatch W;
		TestFalse(TEXT("nothing is watched before it is started"), W.IsWatching());
		W.Start(0, 0.0);
		TestFalse(TEXT("no process id: not watched"), W.IsWatching());
		W.Start(1, 0.0);
		TestFalse(TEXT("process 1 is init, not a launcher: not watched"), W.IsWatching());
		TestEqual(TEXT("a watch that is off never reports a launcher gone"), W.Feed(EProbe::Gone, 100.0), -1.0);
	}
	{
		FMILauncherWatch W;
		W.Start(4242, 10.0);
		TestTrue(TEXT("looked at once, at the start"), W.IsDue(10.0));
		TestEqual(TEXT("alive: not gone"), W.Feed(EProbe::Alive, 10.0), -1.0);
		TestFalse(TEXT("next look in 2 s: not at 11.9"), W.IsDue(11.9));
		TestTrue(TEXT("... at 12"), W.IsDue(12.0));
		TestTrue(TEXT("gone, first answer: gone for 0 s"), W.Feed(EProbe::Gone, 12.0) >= 0.0 && W.Feed(EProbe::Gone, 12.0) < 0.01);
		TestTrue(TEXT("gone for 2 s"), FMath::IsNearlyEqual(W.Feed(EProbe::Gone, 14.0), 2.0));
		TestTrue(TEXT("gone for 4 s: not yet 5"), FMath::IsNearlyEqual(W.Feed(EProbe::Gone, 16.0), 4.0));
		TestTrue(TEXT("gone for 6 s: past 5"), FMath::IsNearlyEqual(W.Feed(EProbe::Gone, 18.0), 6.0));
		// And what the game does with that: the decision.
		FMISession::FOptions O;
		TestTrue(TEXT("4 s gone: the game keeps"), FMISession::Decide(O, MISessionTestsPrivate::State(1, true, 50.0, 100.0, 4.0)).Action == FMISession::EAction::Keep);
		TestTrue(TEXT("6 s gone: the game quits"), FMISession::Decide(O, MISessionTestsPrivate::State(1, true, 50.0, 100.0, 6.0)).Action == FMISession::EAction::Exit);
	}
	{
		// A launcher that answers again (a busy machine that missed a look): the clock starts over.
		FMILauncherWatch W;
		W.Start(4242, 0.0);
		W.Feed(EProbe::Alive, 0.0);
		TestTrue(TEXT("gone once"), W.Feed(EProbe::Gone, 2.0) >= 0.0);
		TestEqual(TEXT("alive again: not gone"), W.Feed(EProbe::Alive, 4.0), -1.0);
		TestEqual(TEXT("... and its clock is back to nothing"), W.GetGoneFor(5.0), -1.0);
		W.Feed(EProbe::Gone, 6.0);
		TestTrue(TEXT("gone again: counts from 6, not from 2"), FMath::IsNearlyEqual(W.Feed(EProbe::Gone, 8.0), 2.0));
	}
	{
		// "Cannot tell" (no /proc, another user's process, not Linux) is never a reason to quit.
		FMILauncherWatch W;
		W.Start(4242, 0.0);
		W.Feed(EProbe::Alive, 0.0);
		double Worst = -1.0;
		for (double T = 2.0; T < 4000.0; T += 2.0)
		{
			Worst = FMath::Max(Worst, W.Feed(EProbe::Unknown, T));
		}
		TestEqual(TEXT("an hour of 'cannot tell': never gone"), Worst, -1.0);
		TestTrue(TEXT("still watching"), W.IsWatching());
	}
	{
		// An id that was never seen alive is not this launcher (another process namespace): the watch turns itself off.
		FMILauncherWatch W;
		W.Start(4242, 0.0);
		TestEqual(TEXT("gone at the very first look: not gone"), W.Feed(EProbe::Gone, 0.0), -1.0);
		TestTrue(TEXT("the watch is off"), W.IsDisarmed() && !W.IsWatching());
		TestEqual(TEXT("and it stays off"), W.Feed(EProbe::Gone, 100.0), -1.0);
		FMILauncherWatch U;
		U.Start(4242, 0.0);
		U.Feed(EProbe::Unknown, 0.0);
		TestEqual(TEXT("'cannot tell' first, then gone: still never seen alive, off"), U.Feed(EProbe::Gone, 2.0), -1.0);
		TestTrue(TEXT("... off"), U.IsDisarmed());
	}
#if PLATFORM_LINUX
	{
		// The real looking. This process is there, as the same process every time.
		uint64 Start = 0;
		const int32 Me = (int32)getpid();
		TestTrue(TEXT("this process is alive"), MIProbeProcess(Me, Start) == EProbe::Alive);
		TestTrue(TEXT("its start time is remembered"), Start != 0);
		TestTrue(TEXT("and it is alive the second time too"), MIProbeProcess(Me, Start) == EProbe::Alive);
		uint64 Other = Start + 12345;
		TestTrue(TEXT("a process id that now belongs to a process started at another time is another process: gone"), MIProbeProcess(Me, Other) == EProbe::Gone);
		uint64 None = 0;
		TestTrue(TEXT("a process id nobody has: gone"), MIProbeProcess(4194000, None) == EProbe::Gone);
		TestTrue(TEXT("process 1 and 0 are not looked at"), MIProbeProcess(1, None) == EProbe::Unknown && MIProbeProcess(0, None) == EProbe::Unknown);

		// A process that is killed: gone, whether it is a zombie (nobody collected it) or collected already.
		uint32 Pid = 0;
		FProcHandle Handle = FPlatformProcess::CreateProc(TEXT("/bin/sleep"), TEXT("60"), true, false, false, &Pid, 0, nullptr, nullptr, nullptr);
		if (TestTrue(TEXT("a child process (sleep 60) started"), Handle.IsValid() && Pid > 1))
		{
			uint64 ChildStart = 0;
			TestTrue(TEXT("the child is alive"), MIProbeProcess((int32)Pid, ChildStart) == EProbe::Alive);
			kill((pid_t)Pid, SIGKILL);
			bool bGone = false;
			for (int32 I = 0; I < 100 && !bGone; ++I)
			{
				bGone = MIProbeProcess((int32)Pid, ChildStart) == EProbe::Gone;
				if (!bGone)
				{
					FPlatformProcess::Sleep(0.03f);
				}
			}
			TestTrue(TEXT("killed: gone within 3 s (a zombie counts as gone)"), bGone);
			FPlatformProcess::CloseProc(Handle);
		}
	}
#endif
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICloudEncoderRangeTest, "MurderInc.Cloud.EncoderRange", MITest::Flags)

bool FMICloudEncoderRangeTest::RunTest(const FString& Parameters)
{
	const FMIEncoderRange::FSettings S;  // 10 below, 8 above, floor 8, ceiling 48
	TestTrue(TEXT("the defaults: 10 below, 8 above, floor 8, ceiling 48, a range"),
		S.Below == 10 && S.Above == 8 && S.Floor == 8 && S.Ceiling == 48 && !S.bExact);
	const auto Check = [this](const TCHAR* What, int32 WantedMin, int32 WantedMax, const FMIEncoderRange::FSettings& Settings, int32 ExpectMin, int32 ExpectMax)
	{
		const FMIEncoderRange::FRange R = FMIEncoderRange::Widen(WantedMin, WantedMax, Settings);
		TestTrue(FString::Printf(TEXT("%s: %d and %d give %d to %d (got %d to %d)"), What, WantedMin, WantedMax, ExpectMin, ExpectMax, R.MinQp, R.MaxQp), R.MinQp == ExpectMin && R.MaxQp == ExpectMax);
	};
	Check(TEXT("Medium"), 34, 34, S, 24, 42);
	Check(TEXT("High"), 16, 16, S, 8, 24);
	Check(TEXT("the launch options of lag-test.sh"), 18, 36, S, 8, 44);
	Check(TEXT("a request under the floor keeps its own number"), 5, 5, S, 5, 13);
	Check(TEXT("a very soft picture: the ceiling"), 45, 45, S, 35, 48);
	Check(TEXT("a request over the ceiling keeps its own number"), 50, 50, S, 40, 50);
	Check(TEXT("the lowest QP of all"), 0, 0, S, 0, 8);
	Check(TEXT("the highest QP of all"), 51, 51, S, 41, 51);
	Check(TEXT("the numbers the wrong way round are the same two numbers"), 36, 18, S, 8, 44);
	Check(TEXT("out of range numbers are cut to 0 and 51"), -20, 200, S, 0, 51);
	FMIEncoderRange::FSettings Exact = S;
	Exact.bExact = true;
	Check(TEXT("-MIQpExact: Medium as it comes"), 34, 34, Exact, 34, 34);
	Check(TEXT("-MIQpExact: High as it comes"), 16, 16, Exact, 16, 16);
	FMIEncoderRange::FSettings Wide = S;
	Wide.Below = 20;
	Wide.Above = 30;
	Check(TEXT("a wider range stops at the floor and the ceiling"), 34, 34, Wide, 14, 48);
	Wide.Floor = 20;
	Wide.Ceiling = 40;
	Check(TEXT("a narrower floor and ceiling"), 34, 34, Wide, 20, 40);
	FMIEncoderRange::FSettings None = S;
	None.Below = 0;
	None.Above = 0;
	Check(TEXT("no widening is the request"), 34, 34, None, 34, 34);
	FMIEncoderRange::FSettings Negative = S;
	Negative.Below = -5;
	Negative.Above = -5;
	Check(TEXT("negative numbers are no widening"), 34, 34, Negative, 34, 34);
	// The range always holds the request, and is never wider than the engine's 0 to 51.
	for (int32 A = 0; A <= 51; ++A)
	{
		for (int32 B = A; B <= 51; B += 3)
		{
			const FMIEncoderRange::FRange R = FMIEncoderRange::Widen(A, B, S);
			if (!(R.MinQp <= A && R.MaxQp >= B && R.MinQp >= 0 && R.MaxQp <= 51 && R.MinQp <= R.MaxQp))
			{
				AddError(FString::Printf(TEXT("%d and %d gave %d to %d: it does not hold the request"), A, B, R.MinQp, R.MaxQp));
				break;
			}
		}
	}

	// The quality the plugin is given: its encoder works out exactly the QP back, for every QP.
	for (int32 Qp = 0; Qp <= 51; ++Qp)
	{
		const int32 Quality = FMIEncoderRange::QualityForQp(Qp);
		if (FMIEncoderRange::QpForQuality(Quality) != Qp)
		{
			AddError(FString::Printf(TEXT("QP %d -> quality %d -> QP %d"), Qp, Quality, FMIEncoderRange::QpForQuality(Quality)));
		}
	}
	TestEqual(TEXT("QP 34 is quality 33 (what Pixel Streaming makes of the launch option)"), FMIEncoderRange::QualityForQp(34), 33);
	TestEqual(TEXT("QP 16 is quality 68"), FMIEncoderRange::QualityForQp(16), 68);
	TestEqual(TEXT("QP 24 is quality 52"), FMIEncoderRange::QualityForQp(24), 52);
	TestEqual(TEXT("QP 42 is quality 17"), FMIEncoderRange::QualityForQp(42), 17);
	TestEqual(TEXT("QP 8 is quality 84"), FMIEncoderRange::QualityForQp(8), 84);
	TestEqual(TEXT("QP 0 is quality 100"), FMIEncoderRange::QualityForQp(0), 100);
	TestEqual(TEXT("QP 51 is quality 0"), FMIEncoderRange::QualityForQp(51), 0);

	// A viewer's console command.
	int32 Qp = -1;
	TestTrue(TEXT("MinQP 34"), FMIEncoderRange::ParseCommand(TEXT("PixelStreaming.Encoder.MinQP 34"), Qp) == FMIEncoderRange::ECommand::MinQp && Qp == 34);
	TestTrue(TEXT("MaxQP 34"), FMIEncoderRange::ParseCommand(TEXT("PixelStreaming.Encoder.MaxQP 34"), Qp) == FMIEncoderRange::ECommand::MaxQp && Qp == 34);
	TestTrue(TEXT("any case, name=value"), FMIEncoderRange::ParseCommand(TEXT("pixelstreaming.ENCODER.maxqp=16"), Qp) == FMIEncoderRange::ECommand::MaxQp && Qp == 16);
	TestTrue(TEXT("the plugin's own name"), FMIEncoderRange::ParseCommand(TEXT("PixelStreaming2.Encoder.MinQP 20"), Qp) == FMIEncoderRange::ECommand::MinQp && Qp == 20);
	TestTrue(TEXT("spaces around"), FMIEncoderRange::ParseCommand(TEXT("  PixelStreaming.Encoder.MinQP   8  "), Qp) == FMIEncoderRange::ECommand::MinQp && Qp == 8);
	TestTrue(TEXT("a fraction is rounded"), FMIEncoderRange::ParseCommand(TEXT("PixelStreaming.Encoder.MinQP 34.4"), Qp) == FMIEncoderRange::ECommand::MinQp && Qp == 34);
	TestTrue(TEXT("over 51 is 51"), FMIEncoderRange::ParseCommand(TEXT("PixelStreaming.Encoder.MaxQP 99"), Qp) == FMIEncoderRange::ECommand::MaxQp && Qp == 51);
	TestTrue(TEXT("no number: not a QP command"), FMIEncoderRange::ParseCommand(TEXT("PixelStreaming.Encoder.MinQP"), Qp) == FMIEncoderRange::ECommand::None);
	TestTrue(TEXT("not a number: not a QP command"), FMIEncoderRange::ParseCommand(TEXT("PixelStreaming.Encoder.MinQP abc"), Qp) == FMIEncoderRange::ECommand::None);
	TestTrue(TEXT("quality commands are the plugin's own"), FMIEncoderRange::ParseCommand(TEXT("PixelStreaming.Encoder.MinQuality 50"), Qp) == FMIEncoderRange::ECommand::None);
	TestTrue(TEXT("another variable"), FMIEncoderRange::ParseCommand(TEXT("t.MaxFPS 30"), Qp) == FMIEncoderRange::ECommand::None);
	TestTrue(TEXT("another family"), FMIEncoderRange::ParseCommand(TEXT("Foo.Encoder.MinQP 30"), Qp) == FMIEncoderRange::ECommand::None);
	TestTrue(TEXT("empty"), FMIEncoderRange::ParseCommand(TEXT(""), Qp) == FMIEncoderRange::ECommand::None);
	// And the allowlist still lets E3DS's commands through to this code.
	TestTrue(TEXT("the allowlist admits the page's command"), UMICloudSubsystem::IsViewerCommandAllowed(TEXT("PixelStreaming.Encoder.MinQP 34")));

	// The launch options as E3DS writes them (Medium, from a session's log), and Pixel Streaming reads them: the first of each.
	int32 Min = 0, Max = 0;
	FMIEncoderRange::ReadLaunchOptions(TEXT("-MICloud -PixelStreamingEncoderCodec=H264 -AudioMixer -AllowPixelStreamingCommands -PixelStreamingURL=ws://127.0.0.1:3000 -PixelStreamingWebRTCMinBitrate=100000 -PixelStreamingWebRTCMaxBitrate=20000000 -PixelStreamingEncoderMinQP=34 -PixelStreamingEncoderMaxQP=34 -Windowed -ForceRes -ResX=1920 -ResY=1080 -PixelStreamingEncoderMaxQP=31"), Min, Max);
	TestTrue(TEXT("E3DS Medium: 34 and 34 (the second MaxQP counts for nothing)"), Min == 34 && Max == 34);
	FMIEncoderRange::ReadLaunchOptions(TEXT("-pixelstreamingencoderminqp=16 -PIXELSTREAMINGENCODERMAXQP=16"), Min, Max);
	TestTrue(TEXT("E3DS High, any case: 16 and 16"), Min == 16 && Max == 16);
	FMIEncoderRange::ReadLaunchOptions(TEXT("-PixelStreamingEncoderMinQP=20"), Min, Max);
	TestTrue(TEXT("only the lowest"), Min == 20 && Max == -1);
	FMIEncoderRange::ReadLaunchOptions(TEXT("-MICloud -PixelStreamingEncoderMinQuality=60"), Min, Max);
	TestTrue(TEXT("none (a quality option is the plugin's own)"), Min == -1 && Max == -1);
	FMIEncoderRange::ReadLaunchOptions(nullptr, Min, Max);
	TestTrue(TEXT("no command line"), Min == -1 && Max == -1);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICloudRoundTripTest, "MurderInc.Cloud.RoundTrip", MITest::Flags)

bool FMICloudRoundTripTest::RunTest(const FString& Parameters)
{
	FMIRoundTrip R;
	TestFalse(TEXT("nothing measured: unknown"), R.IsKnown());
	TestEqual(TEXT("... and 0 ms, never a number from nowhere"), R.Ms(), 0.0);
	TestTrue(TEXT("... with no age"), R.AgeSeconds(100.0) > 1e6);
	// What the sender reports before it has measured anything, and what is not a time.
	R.Add(0.0, 1.0);
	R.Add(-0.01, 1.0);
	R.Add(std::numeric_limits<double>::quiet_NaN(), 1.0);
	R.Add(std::numeric_limits<double>::infinity(), 1.0);
	R.Add(61.0, 1.0);
	TestFalse(TEXT("0, negative, not a number, infinite, over a minute: not measurements"), R.IsKnown());
	TestEqual(TEXT("five reports ignored, counted"), R.GetIgnored(), 5);
	R.Add(0.040, 10.0);
	TestTrue(TEXT("40 ms measured"), R.IsKnown() && FMath::IsNearlyEqual(R.Ms(), 40.0, 1e-3));
	TestTrue(TEXT("its age"), FMath::IsNearlyEqual(R.AgeSeconds(13.0), 3.0));
	// A steady link reports nothing new: the value stays (no 5 s expiry), with its age.
	TestTrue(TEXT("still 40 ms two minutes later"), R.IsKnown() && FMath::IsNearlyEqual(R.Ms(), 40.0, 1e-3));
	TestTrue(TEXT("and its age says how old it is"), FMath::IsNearlyEqual(R.AgeSeconds(130.0), 120.0));
	// Video and audio report under one name, interleaved: the median of the last five.
	R.Add(0.042, 11.0);
	R.Add(0.038, 12.0);
	R.Add(0.041, 13.0);
	R.Add(0.900, 14.0);  // one bad report
	TestTrue(TEXT("a spike among five reports does not move the median much: 41 ms"), FMath::IsNearlyEqual(R.Ms(), 41.0, 1e-3));
	R.Add(0.039, 15.0);
	R.Add(0.040, 16.0);
	TestTrue(TEXT("only the last five count: the spike is still among them"), FMath::IsNearlyEqual(R.Ms(), 40.0, 1e-3));
	R.Add(0.040, 17.0);
	R.Add(0.040, 18.0);
	TestTrue(TEXT("a spike never moves the median of five"), FMath::IsNearlyEqual(R.Ms(), 40.0, 1e-3));
	TestEqual(TEXT("nine measured"), R.GetAccepted(), 9);
	// The viewers change: the next one is another connection.
	R.Reset();
	TestFalse(TEXT("after a reset nothing is known"), R.IsKnown());
	TestEqual(TEXT("the counts start again"), R.GetAccepted() + R.GetIgnored(), 0);
	R.Add(0.0009, 200.0);
	TestTrue(TEXT("a round trip under a millisecond is a measurement too (a local peer)"), R.IsKnown() && R.Ms() < 1.0 && R.Ms() > 0.5);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICloudSessionDefaultsTest, "MurderInc.Cloud.SessionDefaults", MITest::Flags)

bool FMICloudSessionDefaultsTest::RunTest(const FString& Parameters)
{
	// The numbers a package starts with are the ones the docs say (docs/LAUNCH.md, MICloud.h), and a visitor's value is
	// sanitized before it ends a session.
	const auto Int = [this](const TCHAR* Name, int32 Expect)
	{
		IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(Name);
		if (!V)
		{
			AddError(FString::Printf(TEXT("no console variable %s"), Name));
			return;
		}
		TestEqual(Name, V->GetInt(), Expect);
	};
	const auto Float = [this](const TCHAR* Name, float Expect)
	{
		IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(Name);
		if (!V)
		{
			AddError(FString::Printf(TEXT("no console variable %s"), Name));
			return;
		}
		TestEqual(Name, V->GetFloat(), Expect);
	};
	Int(TEXT("MI.Cloud.IdleFps"), 2);
	Float(TEXT("MI.Cloud.IdleAfter"), 2.f);
	Float(TEXT("MI.Cloud.ExitAfterEmpty"), 60.f);
	Float(TEXT("MI.Cloud.ExitIfNoViewer"), 600.f);
	Int(TEXT("MI.Cloud.KeepAlive"), 0);
	Int(TEXT("MI.Cloud.QpBelow"), 10);
	Int(TEXT("MI.Cloud.QpAbove"), 8);
	Int(TEXT("MI.Cloud.QpFloor"), 8);
	Int(TEXT("MI.Cloud.QpCeiling"), 48);
	Int(TEXT("MI.Cloud.QpExact"), 0);
	const FMISession::FOptions O = UMICloudSubsystem::ReadSessionOptions(true);
	TestTrue(TEXT("the options as the game reads them"), O.bStreamed && !O.bKeepAlive && O.IdleFps == 2 && O.IdleAfter == 2.0 && O.ExitAfterEmpty == 60.0 && O.ExitIfNoViewer == 600.0);
	TestFalse(TEXT("a desktop game is not streamed"), UMICloudSubsystem::ReadSessionOptions(false).bStreamed);
	const FMIEncoderRange::FSettings E = UMICloudSubsystem::ReadEncoderSettings();
	TestTrue(TEXT("the encoder settings as the game reads them"), E.Below == 10 && E.Above == 8 && E.Floor == 8 && E.Ceiling == 48 && !E.bExact);
	// A viewer may set most of the MI.Cloud. family (the console variables take any value, the options are sanitized), but not
	// what keeps the game alive or ends it with its session: a visitor's game would outlive the visitor (review of release 3c).
	TestTrue(TEXT("a visitor can still tune the pacing from a link"), UMICloudSubsystem::IsViewerCommandAllowed(TEXT("MI.Cloud.FpsDropAfter 2")));
	for (const TCHAR* Name : {TEXT("MI.Cloud.KeepAlive"), TEXT("MI.Cloud.ExitAfterEmpty"), TEXT("MI.Cloud.ExitIfNoViewer"), TEXT("MI.Cloud.IdleFps"), TEXT("MI.Cloud.IdleAfter"), TEXT("MI.Cloud.QpExact")})
	{
		TestFalse(FString::Printf(TEXT("a viewer cannot set %s"), Name), UMICloudSubsystem::IsViewerCommandAllowed(FString::Printf(TEXT("%s 1"), Name)));
		TestFalse(FString::Printf(TEXT("... nor %s through -MICVars"), Name), MITuning::IsAllowed(Name, TEXT("1")));
		TestFalse(FString::Printf(TEXT("... nor in other letters (%s)"), Name), MITuning::IsAllowed(FString(Name).ToUpper(), TEXT("1")));
	}
	return true;
}

#endif
