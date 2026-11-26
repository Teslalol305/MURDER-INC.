// Version 3, release A (the lag): the decisions that keep a streamed game from running ahead of its GPU, and what
// a visitor may tune from outside. No world, no renderer.
//   MurderInc.Cloud.FrameRate   the frame-rate target: down at once, in live play only, when the GPU cannot keep up at
//                               the smallest picture; up in live play and on a card alike (Hold the Block shows no card
//                               between its waves: docs/unreal/SMOOTH.md H2), judged at the smallest picture too; a
//                               rise that does not hold waits longer, one that holds earns the short wait back; the
//                               old rule (up only outside live play) on request; a fixed target stays
//   MurderInc.Cloud.Tuning      the variables -MICVars and a viewer's console command may set, their ranges, the
//                               launch option's text split into pairs

#include "Cloud/MICloud.h"
#include "Cloud/MIPacing.h"
#include "Misc/AutomationTest.h"
#include "Tests/MITestUtil.h"

#if WITH_AUTOMATION_TESTS

namespace MICloudPacingTestsPrivate
{
	/** Feeds the governor the same half-second steps the game does, for a time. Returns how often the target changed. */
	int32 Run(FMIFrameRateGovernor& G, double Seconds, double GpuMs, bool bSmallestPicture, bool bSafeMoment, bool bHeldBack = false, double GpuMsSmallest = 0.0)
	{
		int32 Changes = 0;
		for (double T = 0.0; T < Seconds - 1e-9; T += 0.5)
		{
			FMIFrameRateGovernor::FInput In;
			In.Seconds = 0.5;
			In.GpuMs = GpuMs;
			In.GpuMsSmallest = GpuMsSmallest;
			In.bSmallestPicture = bSmallestPicture;
			In.bSafeMoment = bSafeMoment;
			In.bHeldBack = bHeldBack;
			Changes += G.Update(In) ? 1 : 0;
		}
		return Changes;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICloudFrameRateTest, "MurderInc.Cloud.FrameRate", MITest::Flags)

bool FMICloudFrameRateTest::RunTest(const FString& Parameters)
{
	using namespace MICloudPacingTestsPrivate;
	{
		FMIFrameRateGovernor G;
		TestEqual(TEXT("it starts at 60"), G.Target(), 60);
		// The line is the whole frame time: 16.7 ms at 60.
		TestEqual(TEXT("16 ms of 16.7: under the line, nothing changes"), Run(G, 20.0, 16.0, true, false), 0);
		TestEqual(TEXT("18 ms while dynamic resolution can still draw a smaller picture: nothing changes"), Run(G, 20.0, 18.0, false, false), 0);
		TestEqual(TEXT("18 ms at the smallest picture for half a second: not yet"), Run(G, 0.5, 18.0, true, false), 0);
		TestEqual(TEXT("... for a second: down, in the middle of play"), Run(G, 0.5, 18.0, true, false), 1);
		TestEqual(TEXT("60 -> 45"), G.Target(), 45);
		AddInfo(FString::Printf(TEXT("log line: %s"), *G.Why()));
		// 22.2 ms at 45.
		TestEqual(TEXT("21.5 ms of 22.2: it holds at 45"), Run(G, 20.0, 21.5, true, false), 0);
		TestEqual(TEXT("24 ms at the smallest picture for a second: down again"), Run(G, 1.0, 24.0, true, false), 1);
		TestEqual(TEXT("45 -> 30"), G.Target(), 30);
		TestEqual(TEXT("40 ms at 30: there is no lower target"), Run(G, 20.0, 40.0, true, false), 0);
		TestEqual(TEXT("still 30"), G.Target(), 30);
		// The rise is judged by the rate it goes to: four fifths of 22.2 ms (17.8 ms) to go to 45.
		TestEqual(TEXT("19 ms on a card for a minute: over four fifths of what a frame has at 45, it stays at 30"), Run(G, 60.0, 19.0, false, true), 0);
		TestEqual(TEXT("10 ms in live play for 9.5 s: not yet"), Run(G, 9.5, 10.0, false, false), 0);
		TestEqual(TEXT("... for 10 s: it rises in play (SMOOTH.md H2: it used to wait for a card that Hold the Block never shows)"), Run(G, 0.5, 10.0, false, false), 1);
		TestEqual(TEXT("30 -> 45"), G.Target(), 45);
		TestTrue(TEXT("the log line says it rose in play"), G.Why().Contains(TEXT("in play")));
		// Four fifths of 16.7 ms are 13.3 ms: 14 ms is not under it.
		TestEqual(TEXT("14 ms on a card: over four fifths of what a frame has at 60, it stays at 45"), Run(G, 60.0, 14.0, false, true), 0);
		TestEqual(TEXT("8 ms on a card for 9.5 s: not yet"), Run(G, 9.5, 8.0, false, true), 0);
		TestEqual(TEXT("... for 10 s: up"), Run(G, 0.5, 8.0, false, true), 1);
		TestEqual(TEXT("45 -> 60"), G.Target(), 60);
		TestEqual(TEXT("8 ms at 60 on a card: there is no higher target"), Run(G, 60.0, 5.0, false, true), 0);
	}
	{
		// A rise that does not hold: the next one waits twice as long.
		FMIFrameRateGovernor G;
		Run(G, 1.0, 18.0, true, false);
		TestEqual(TEXT("down to 45"), G.Target(), 45);
		TestEqual(TEXT("up after 10 s on a card"), Run(G, 10.0, 8.0, false, true), 1);
		TestEqual(TEXT("down again a second into the run"), Run(G, 1.0, 18.0, true, false), 1);
		TestEqual(TEXT("at 45"), G.Target(), 45);
		TestEqual(TEXT("10 s on a card are not enough now"), Run(G, 10.0, 8.0, false, true), 0);
		TestEqual(TEXT("20 s are"), Run(G, 10.0, 8.0, false, true), 1);
		TestEqual(TEXT("at 60"), G.Target(), 60);
	}
	{
		// Hold the Block under E3DS's GPU time (SMOOTH.md H2, run v6-hold-l20): the first fight drops 60 -> 45 -> 30,
		// the GPU is light again between the waves, and the target must come back without a card.
		FMIFrameRateGovernor G;
		TestEqual(TEXT("a fight's second over the line: 60 -> 45"), Run(G, 1.0, 21.0, true, false), 1);
		TestEqual(TEXT("another: 45 -> 30"), Run(G, 1.0, 24.0, true, false), 1);
		TestEqual(TEXT("at 30"), G.Target(), 30);
		TestEqual(TEXT("the fight goes on, 20 ms at the smallest picture (over 17.8 ms): it stays at 30"), Run(G, 60.0, 20.0, true, false), 0);
		const double At50 = MITuning::GpuMsAtSmallest(12.0, 0.75, 0.50, 0.12);
		TestEqual(TEXT("between the waves, 12 ms at the 75 % picture in play for 10 s: 30 -> 45"), Run(G, 10.0, 12.0, false, false, false, At50), 1);
		TestEqual(TEXT("10 s more: 45 -> 60"), Run(G, 10.0, 12.0, false, false, false, At50), 1);
		TestEqual(TEXT("at 60, in play, no card shown"), G.Target(), 60);
		AddInfo(FString::Printf(TEXT("log line: %s"), *G.Why()));
		TestEqual(TEXT("the calm goes on at 60: nothing changes"), Run(G, 50.0, 12.0, false, false, false, At50), 0);
		TestEqual(TEXT("the next wave's fight, almost a minute after the rise: down"), Run(G, 1.0, 21.0, true, false), 1);
		TestEqual(TEXT("the rise had held past the retry window: 10 s of calm bring 60 back"), Run(G, 10.0, 12.0, false, false, false, At50), 1);
		TestEqual(TEXT("5 s later the fight is back: down (this rise did not hold)"), Run(G, 5.0, 12.0, false, false, false, At50) + Run(G, 1.0, 21.0, true, false), 1);
		TestEqual(TEXT("the next try waits twice as long: 10 s are not enough"), Run(G, 10.0, 12.0, false, false, false, At50), 0);
		TestEqual(TEXT("20 s are"), Run(G, 10.0, 12.0, false, false, false, At50), 1);
		TestEqual(TEXT("two minutes at 60"), Run(G, 120.0, 12.0, false, false, false, At50), 0);
		TestEqual(TEXT("a fight: down"), Run(G, 1.0, 21.0, true, false), 1);
		TestEqual(TEXT("the last rise held for two minutes: the short wait is earned back (10 s)"), Run(G, 10.0, 12.0, false, false, false, At50), 1);
		TestEqual(TEXT("at 60"), G.Target(), 60);
	}
	{
		// A shared card for two minutes (SMOOTH.md H2, run v6-long): after it the GPU reads 7 to 9 ms and 60 comes back in play.
		FMIFrameRateGovernor G;
		TestEqual(TEXT("the other game's load: 60 -> 45"), Run(G, 1.0, 20.6, true, false), 1);
		TestEqual(TEXT("two minutes of it at 45 (17 ms, under 22.2, over 13.3): it stays"), Run(G, 120.0, 17.0, true, false), 0);
		TestEqual(TEXT("the other game leaves: 8 ms for 10 s, back to 60"), Run(G, 10.0, 8.0, false, false), 1);
		TestEqual(TEXT("60"), G.Target(), 60);
	}
	{
		// The old rule on request (MI.Cloud.FpsRiseInPlay 0): up only at a safe moment.
		FMIFrameRateGovernor G;
		G.bRiseInPlay = false;
		Run(G, 1.0, 21.0, true, false);
		TestEqual(TEXT("down to 45"), G.Target(), 45);
		TestEqual(TEXT("8 ms for a minute in live play: it does not rise"), Run(G, 60.0, 8.0, false, false), 0);
		TestEqual(TEXT("the same on the pause card: it rises at once (it has been under for long enough)"), Run(G, 0.5, 8.0, false, true), 1);
		TestEqual(TEXT("60"), G.Target(), 60);
	}
	{
		// The pacer's word counts even when the GPU's measured time looks fine or is not known.
		FMIFrameRateGovernor G;
		TestEqual(TEXT("short of the rate for the GPU's sake at the smallest picture, GPU time unknown: down after a second"), Run(G, 1.0, 0.0, true, false, true), 1);
		AddInfo(FString::Printf(TEXT("log line: %s"), *G.Why()));
		TestEqual(TEXT("45"), G.Target(), 45);
		TestEqual(TEXT("GPU time unknown and not held back: nothing to go by, nothing changes"), Run(G, 60.0, 0.0, true, true, false), 0);
		TestEqual(TEXT("held back while the picture can still shrink: dynamic resolution's turn first"), Run(G, 10.0, 30.0, false, false, true), 0);
	}
	{
		// Outside live play nothing drops: the start of the game and the set-up screens say little about a run.
		FMIFrameRateGovernor G;
		TestEqual(TEXT("30 ms at the smallest picture on a card for a minute: it stays at 60"), Run(G, 60.0, 30.0, true, true), 0);
		TestEqual(TEXT("held back by the GPU on a card for a minute: it stays at 60"), Run(G, 60.0, 0.0, true, true, true), 0);
		TestEqual(TEXT("60"), G.Target(), 60);
		TestEqual(TEXT("half a second into the run: not yet (the time on the card did not count)"), Run(G, 0.5, 30.0, true, false), 0);
		TestEqual(TEXT("a second into the run: down"), Run(G, 0.5, 30.0, true, false), 1);
		TestEqual(TEXT("45"), G.Target(), 45);
	}
	{
		// A card that takes 12 ms a frame holds 60 (box runs k-l12, d6). Put at 45 by one bad second, it must get 60
		// back at the next card: with the first rule (under 45 % of the frame time now, 10 ms at 45) it never did.
		FMIFrameRateGovernor G;
		Run(G, 1.0, 18.0, true, false);
		TestEqual(TEXT("down to 45 by a bad second"), G.Target(), 45);
		// At the smallest picture the GPU needs a little less: an eighth of its time follows the pixels (measured).
		const double At50 = MITuning::GpuMsAtSmallest(12.0, 0.75, 0.50, 0.12);
		AddInfo(FString::Printf(TEXT("12 ms at the 75 %% picture is %.2f ms at the 50 %% picture (12 %% of the time follows the pixels)"), At50));
		TestTrue(TEXT("12 ms at 75 % is 11.2 ms at 50 %"), FMath::IsNearlyEqual(At50, 12.0 * (0.88 + 0.12 * 0.25 / 0.5625), 1e-9) && At50 < 12.0 && At50 > 11.0);
		TestEqual(TEXT("12 ms at the 75 % picture on a card, 9.5 s: not yet"), Run(G, 9.5, 12.0, false, true, false, At50), 0);
		TestEqual(TEXT("... 10 s: it rises (11.2 ms is under four fifths of 16.7 ms)"), Run(G, 0.5, 12.0, false, true, false, At50), 1);
		TestEqual(TEXT("45 -> 60"), G.Target(), 60);
		AddInfo(FString::Printf(TEXT("log line: %s"), *G.Why()));
	}
	{
		// The time at the smallest picture is what counts: 14 ms at the 75 % picture is over 13.3 ms as measured, and
		// under it at the 50 % picture when most of the time follows the pixels (a card and scene unlike the box's).
		FMIFrameRateGovernor G;
		Run(G, 1.0, 18.0, true, false);
		TestEqual(TEXT("down to 45"), G.Target(), 45);
		TestEqual(TEXT("14 ms, nothing known about a smaller picture: it stays at 45"), Run(G, 60.0, 14.0, false, true), 0);
		const double Pixels = MITuning::GpuMsAtSmallest(14.0, 0.75, 0.50, 0.6);
		TestTrue(TEXT("14 ms at 75 % is 9.3 ms at 50 % when 60 % of the time follows the pixels"), FMath::IsNearlyEqual(Pixels, 14.0 * (0.4 + 0.6 * 0.25 / 0.5625), 1e-9));
		TestEqual(TEXT("then it rises after 10 s"), Run(G, 10.0, 14.0, false, true, false, Pixels), 1);
		TestEqual(TEXT("at 60"), G.Target(), 60);
	}
	{
		FMIFrameRateGovernor G;
		Run(G, 1.0, 18.0, true, false);
		TestEqual(TEXT("down to 45"), G.Target(), 45);
		// The picture is the smallest already: nothing is left to gain.
		const double At50 = MITuning::GpuMsAtSmallest(14.0, 0.50, 0.50, 0.6);
		TestEqual(TEXT("at the smallest picture the time is the time"), At50, 14.0);
		TestEqual(TEXT("14 ms at the 50 % picture on a card for a minute: it stays at 45"), Run(G, 60.0, 14.0, true, true, false, At50), 0);
		// The sum never comes out above the measured time, and the parts are what they say.
		TestEqual(TEXT("dynamic resolution off (no share known): the measured time"), MITuning::GpuMsAtSmallest(12.0, -1.0, 0.5, 0.6), 12.0);
		TestEqual(TEXT("nothing follows the pixels: the measured time"), MITuning::GpuMsAtSmallest(12.0, 0.75, 0.5, 0.0), 12.0);
		TestTrue(TEXT("everything follows the pixels: the ratio of the pixels"), FMath::IsNearlyEqual(MITuning::GpuMsAtSmallest(12.0, 0.75, 0.5, 1.0), 12.0 * 0.25 / 0.5625, 1e-9));
		TestEqual(TEXT("no GPU time known"), MITuning::GpuMsAtSmallest(0.0, 0.75, 0.5, 0.6), 0.0);
	}
	{
		// A fixed target (-MIFps=, MI.Cloud.FpsTarget, a t.MaxFPS set by hand).
		FMIFrameRateGovernor G;
		G.Pin(30);
		TestEqual(TEXT("fixed at 30"), G.Target(), 30);
		TestTrue(TEXT("it says so"), G.IsPinned());
		TestEqual(TEXT("an idle GPU on a card does not raise it"), Run(G, 60.0, 3.0, false, true), 0);
		G.Pin(45);
		TestEqual(TEXT("fixed at 45: a full GPU does not lower it"), Run(G, 60.0, 30.0, true, false), 0);
		TestEqual(TEXT("45"), G.Target(), 45);
		G.Pin(0);
		TestFalse(TEXT("free again"), G.IsPinned());
		TestEqual(TEXT("and it moves again"), Run(G, 1.0, 30.0, true, false), 1);
		TestEqual(TEXT("30"), G.Target(), 30);
		TestEqual(TEXT("a cap of 50 is the 45 target"), FMIFrameRateGovernor::TargetFor(50), 45);
		TestEqual(TEXT("a cap of 20 is the 30 target"), FMIFrameRateGovernor::TargetFor(20), 30);
		TestEqual(TEXT("no cap is the 60 target"), FMIFrameRateGovernor::TargetFor(0), 60);
		TestEqual(TEXT("a cap of 120 is the 60 target"), FMIFrameRateGovernor::TargetFor(120), 60);
	}
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICloudTuningTest, "MurderInc.Cloud.Tuning", MITest::Flags)

bool FMICloudTuningTest::RunTest(const FString& Parameters)
{
	const auto Ok = [](const TCHAR* Name, const TCHAR* Value) { return MITuning::IsAllowed(Name, Value); };
	// The families of docs/unreal/PREFLIGHT.md V3-9 and V3-11.
	TestTrue(TEXT("a scalability group"), Ok(TEXT("sg.ShadowQuality"), TEXT("2")));
	TestTrue(TEXT("dynamic resolution"), Ok(TEXT("r.DynamicRes.OperationMode"), TEXT("2")));
	TestTrue(TEXT("its frame time"), Ok(TEXT("r.DynamicRes.FrameTimeBudget"), TEXT("22.2")));
	TestTrue(TEXT("the frame cap"), Ok(TEXT("t.MaxFPS"), TEXT("30")));
	TestTrue(TEXT("the frame cap off"), Ok(TEXT("t.MaxFPS"), TEXT("0")));
	TestTrue(TEXT("the texture pool"), Ok(TEXT("r.Streaming.PoolSize"), TEXT("1000")));
	TestTrue(TEXT("the thread sync"), Ok(TEXT("r.GTSyncType"), TEXT("1")));
	TestTrue(TEXT("TSR's history at Epic's 200 %"), Ok(TEXT("r.TSR.History.ScreenPercentage"), TEXT("200")));
	TestTrue(TEXT("the thread lag"), Ok(TEXT("r.OneFrameThreadLag"), TEXT("0")));
	TestTrue(TEXT("volumetric fog: the size of a cell on screen"), Ok(TEXT("r.VolumetricFog.GridPixelSize"), TEXT("16")));
	TestTrue(TEXT("volumetric fog: the cells in depth"), Ok(TEXT("r.VolumetricFog.GridSizeZ"), TEXT("64")));
	TestTrue(TEXT("the highest scalability level of the Settings card"), Ok(TEXT("sg.GlobalIlluminationQuality"), TEXT("3")));
	TestTrue(TEXT("the stream's own settings"), Ok(TEXT("PixelStreaming2.WebRTC.Fps"), TEXT("30")));
	TestTrue(TEXT("a text value of the stream"), Ok(TEXT("PixelStreaming2.Encoder.Codec"), TEXT("H264")));
	TestTrue(TEXT("the game's pacing"), Ok(TEXT("MI.Cloud.GpuFramesInFlight"), TEXT("0")));
	TestTrue(TEXT("any letter case"), Ok(TEXT("T.MAXFPS"), TEXT("45")));
	TestTrue(TEXT("only read"), Ok(TEXT("t.MaxFPS"), TEXT("")));
	// The ranges: a visitor can put these on a link, and a server out of GPU memory is a crash email to the owner.
	TestFalse(TEXT("a screen percentage above the output size"), Ok(TEXT("r.ScreenPercentage"), TEXT("200")));
	TestTrue(TEXT("a screen percentage below it"), Ok(TEXT("r.ScreenPercentage"), TEXT("60")));
	TestFalse(TEXT("dynamic resolution's largest picture above the output size"), Ok(TEXT("r.DynamicRes.MaxScreenPercentage"), TEXT("400")));
	TestFalse(TEXT("its smallest picture below a quarter"), Ok(TEXT("r.DynamicRes.MinScreenPercentage"), TEXT("5")));
	TestFalse(TEXT("a 20 GB texture pool"), Ok(TEXT("r.Streaming.PoolSize"), TEXT("20000")));
	TestFalse(TEXT("a TSR history four times the output"), Ok(TEXT("r.TSR.History.ScreenPercentage"), TEXT("400")));
	TestFalse(TEXT("TSR's other variables are not on the list"), Ok(TEXT("r.TSR.ShadingRejection.Flickering"), TEXT("0")));
	TestFalse(TEXT("a frame cap of 1000"), Ok(TEXT("t.MaxFPS"), TEXT("1000")));
	TestFalse(TEXT("a number where a number belongs"), Ok(TEXT("t.MaxFPS"), TEXT("fast")));
	// The fog's grid is (width / cell) x (height / cell) x depth cells, and the engine limits neither from above: one
	// pixel a cell and 2048 cells in depth would ask for volumes of tens of GB.
	TestFalse(TEXT("fog cells of one pixel"), Ok(TEXT("r.VolumetricFog.GridPixelSize"), TEXT("1")));
	TestFalse(TEXT("2048 fog cells in depth"), Ok(TEXT("r.VolumetricFog.GridSizeZ"), TEXT("2048")));
	TestFalse(TEXT("the fog's other variables are not on the list"), Ok(TEXT("r.VolumetricFog.HistoryMissSupersampleCount"), TEXT("16")));
	TestFalse(TEXT("the engine's cinematic scalability level (above the Settings card's ultra)"), Ok(TEXT("sg.ShadowQuality"), TEXT("4")));
	// Inside the stream's own family, but they write files on the server for as long as they are on.
	TestFalse(TEXT("the encoder's frame dump"), Ok(TEXT("PixelStreaming2.Encoder.DumpDebugFrames"), TEXT("1")));
	TestFalse(TEXT("the audio dump"), Ok(TEXT("PixelStreaming2.DumpDebugAudio"), TEXT("true")));
	TestFalse(TEXT("in any letter case"), Ok(TEXT("pixelstreaming2.encoder.dumpdebugframes"), TEXT("1")));
	TestFalse(TEXT("not even to read"), Ok(TEXT("PixelStreaming2.Encoder.DumpDebugFrames"), TEXT("")));
	// Everything else.
	TestFalse(TEXT("another render setting"), Ok(TEXT("r.Lumen.DiffuseIndirect.Allow"), TEXT("0")));
	TestFalse(TEXT("a name that only starts like the frame cap"), Ok(TEXT("t.MaxFPSx"), TEXT("30")));
	TestFalse(TEXT("a family's name without its dot"), Ok(TEXT("sg"), TEXT("1")));
	TestFalse(TEXT("a command"), Ok(TEXT("quit"), TEXT("")));
	TestFalse(TEXT("a second command in the value"), Ok(TEXT("sg.ShadowQuality"), TEXT("2 | quit")));
	TestFalse(TEXT("a name with a space"), Ok(TEXT("t.MaxFPS 30"), TEXT("30")));
	TestFalse(TEXT("no name"), Ok(TEXT(""), TEXT("1")));

	// The launch option's text.
	{
		TArray<TPair<FString, FString>> Allowed;
		TArray<FString> Refused;
		MITuning::ParseOption(TEXT("\"t.MaxFPS=30, sg.ShadowQuality=2;r.DynamicRes.MinScreenPercentage=40,quit,r.ScreenPercentage=400,PixelStreaming2.WebRTC.Fps=30\""), Allowed, Refused);
		TestEqual(TEXT("four pairs may be set"), Allowed.Num(), 4);
		if (Allowed.Num() == 4)
		{
			TestEqual(TEXT("first name"), Allowed[0].Key, FString(TEXT("t.MaxFPS")));
			TestEqual(TEXT("first value"), Allowed[0].Value, FString(TEXT("30")));
			TestEqual(TEXT("second, after a comma and a space"), Allowed[1].Key, FString(TEXT("sg.ShadowQuality")));
			TestEqual(TEXT("third, after a semicolon"), Allowed[2].Key, FString(TEXT("r.DynamicRes.MinScreenPercentage")));
			TestEqual(TEXT("fourth"), Allowed[3].Value, FString(TEXT("30")));
		}
		TestEqual(TEXT("two entries are refused"), Refused.Num(), 2);
		if (Refused.Num() == 2)
		{
			TestEqual(TEXT("the command"), Refused[0], FString(TEXT("quit")));
			TestEqual(TEXT("the value out of range"), Refused[1], FString(TEXT("r.ScreenPercentage=400")));
		}
		Allowed.Reset();
		Refused.Reset();
		MITuning::ParseOption(TEXT(""), Allowed, Refused);
		TestTrue(TEXT("an empty option sets and refuses nothing"), Allowed.Num() == 0 && Refused.Num() == 0);
		MITuning::ParseOption(TEXT("t.MaxFPS="), Allowed, Refused);
		TestTrue(TEXT("a name without a value is refused"), Allowed.Num() == 0 && Refused.Num() == 1);
	}

	// A viewer's console command: the same list, as "name value", "name=value" or "name".
	{
		FString Run;
		TestTrue(TEXT("E3DS's own advice for its console-commands field"), UMICloudSubsystem::IsViewerCommandAllowed(TEXT("t.MaxFPS 30"), &Run));
		TestEqual(TEXT("it runs as written"), Run, FString(TEXT("t.MaxFPS 30")));
		TestTrue(TEXT("with an equals sign"), UMICloudSubsystem::IsViewerCommandAllowed(TEXT(" sg.ShadowQuality=1 "), &Run));
		TestEqual(TEXT("it runs as name and value"), Run, FString(TEXT("sg.ShadowQuality 1")));
		TestTrue(TEXT("with spaces around the equals sign"), UMICloudSubsystem::IsViewerCommandAllowed(TEXT("r.DynamicRes.MinScreenPercentage = 40"), &Run));
		TestEqual(TEXT("it runs as name and value too"), Run, FString(TEXT("r.DynamicRes.MinScreenPercentage 40")));
		TestTrue(TEXT("only the name: the game prints the value"), UMICloudSubsystem::IsViewerCommandAllowed(TEXT("MI.Cloud.FpsTarget"), &Run));
		TestEqual(TEXT("it runs as the name"), Run, FString(TEXT("MI.Cloud.FpsTarget")));
		TestFalse(TEXT("quit"), UMICloudSubsystem::IsViewerCommandAllowed(TEXT("quit")));
		TestFalse(TEXT("a screen percentage of 400"), UMICloudSubsystem::IsViewerCommandAllowed(TEXT("r.ScreenPercentage 400")));
		TestFalse(TEXT("an allowed variable with a second command behind it"), UMICloudSubsystem::IsViewerCommandAllowed(TEXT("t.MaxFPS 30 | quit")));
	}
	AddInfo(FString::Printf(TEXT("allowed: %s"), *MITuning::AllowedList()));
	return !HasAnyErrors();
}

#endif  // WITH_AUTOMATION_TESTS
