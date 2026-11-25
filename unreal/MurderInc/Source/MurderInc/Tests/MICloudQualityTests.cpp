// Release 3c (the quality ladder): the steps the game gives up when the GPU is still the limit at the smallest picture and the
// lowest frame-rate target, and when it takes them back. Pure logic (Cloud/MIQuality.h): no world, no renderer.
//   MurderInc.Cloud.QualityTable      a step's line is read (name, saving, live or calm, variables), lines that could start another
//                                     command are refused, a variable's value at every step, the baseline when no step sets it
//   MurderInc.Cloud.QualityLadder     down after 3 s over the line and at most once in 10 s; the walk down a heavy load stops where the
//                                     GPU is under the line; a free GPU never moves it; a calm step waits for a calm moment; up only
//                                     after a long calm in play and at a safe moment; a rise that does not hold doubles the wait; a
//                                     pin and "off" hold; a recorded series of a fight (the oscillation cases are in it)
//   MurderInc.Cloud.QualityDefaults   the console variables a package starts with; the steps of DefaultGame.ini all parse and name
//                                     console variables that exist

#include "Cloud/MICloud.h"
#include "Cloud/MIQuality.h"
#include "HAL/IConsoleManager.h"
#include "Misc/AutomationTest.h"
#include "Tests/MITestUtil.h"

#if WITH_AUTOMATION_TESTS

namespace MIQualityTestsPrivate
{
	FMIQualityStep MakeStep(const TCHAR* Name, double Saves, bool bCalm = false)
	{
		FMIQualityStep S;
		S.Name = Name;
		S.Saves = Saves;
		S.bCalm = bCalm;
		S.CVars.Emplace(FString::Printf(TEXT("r.Test.%s"), Name), TEXT("1"));
		return S;
	}

	/** A ladder driven the way the game drives it: half-second updates, the GPU's time following the step in force. */
	struct FSim
	{
		FMIQualityLadder L;
		TArray<double> Saves;
		double Time = 0.0;
		TArray<TPair<double, int32>> Changes;   // when (the clock after the update) and the step it ended on
		TArray<int32> Directions;               // +1 down (a lower quality), -1 up

		void Setup(const TArray<FMIQualityStep>& Steps)
		{
			L.Configure(Steps);
			Saves.Reset();
			for (const FMIQualityStep& S : Steps)
			{
				Saves.Add(S.Saves);
			}
		}

		double GpuNow(double Base) const
		{
			double G = Base;
			for (int32 I = 0; I < L.Step(); ++I)
			{
				G *= 1.0 - Saves[I];
			}
			return G;
		}

		/** Seconds of play (or of a safe moment) with the GPU needing Base ms at step 0. Returns how many times the step changed. */
		int32 Run(double Seconds, double Base, double FrameMs, bool bSafe = false, bool bSmallest = true, bool bTop = true, bool bHeld = false)
		{
			int32 N = 0;
			for (double T = 0.0; T < Seconds - 1e-9; T += 0.5)
			{
				FMIQualityLadder::FInput In;
				In.Seconds = 0.5;
				In.GpuMs = GpuNow(Base);
				In.FrameMs = FrameMs;
				In.bSmallestPicture = bSmallest;
				In.bSafeMoment = bSafe;
				In.bTargetAtTop = bTop;
				In.bHeldBack = bHeld;
				Time += 0.5;
				const FMIQualityLadder::EChange C = L.Update(In);
				if (C != FMIQualityLadder::EChange::None)
				{
					++N;
					Changes.Emplace(Time, L.Step());
					Directions.Add(C == FMIQualityLadder::EChange::Down ? 1 : -1);
				}
			}
			return N;
		}
	};

	TArray<FMIQualityStep> Five(double Saves = 0.10)
	{
		TArray<FMIQualityStep> Steps;
		Steps.Add(MakeStep(TEXT("a"), Saves));
		Steps.Add(MakeStep(TEXT("b"), Saves));
		Steps.Add(MakeStep(TEXT("c"), Saves));
		Steps.Add(MakeStep(TEXT("d"), Saves));
		Steps.Add(MakeStep(TEXT("e"), Saves));
		return Steps;
	}

	constexpr double F60 = 1000.0 / 60.0, F45 = 1000.0 / 45.0, F30 = 1000.0 / 30.0;
}

// ---- the table ------------------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICloudQualityTableTest, "MurderInc.Cloud.QualityTable", MITest::Flags)

bool FMICloudQualityTableTest::RunTest(const FString& Parameters)
{
	{
		FMIQualityStep S;
		FString Error;
		TestTrue(TEXT("a line is read"), FMIQualityTable::ParseStep(TEXT("shadows 2 | 12 | live | sg.ShadowQuality=2, r.Foo.Bar=0.5"), S, &Error));
		TestEqual(TEXT("name"), S.Name, FString(TEXT("shadows 2")));
		TestTrue(TEXT("12 % is 0.12"), FMath::IsNearlyEqual(S.Saves, 0.12));
		TestFalse(TEXT("live"), S.bCalm);
		TestEqual(TEXT("two variables"), S.CVars.Num(), 2);
		TestEqual(TEXT("first name"), S.CVars[0].Key, FString(TEXT("sg.ShadowQuality")));
		TestEqual(TEXT("first value"), S.CVars[0].Value, FString(TEXT("2")));
		TestEqual(TEXT("second value"), S.CVars[1].Value, FString(TEXT("0.5")));
		TestTrue(TEXT("a percent sign and the word calm"), FMIQualityTable::ParseStep(TEXT("x | 8% | CALM | r.A=1"), S, &Error));
		TestTrue(TEXT("calm"), S.bCalm);
		TestTrue(TEXT("8 %"), FMath::IsNearlyEqual(S.Saves, 0.08));
	}
	{
		// Each of these must be refused: the data is read from a file a host could be given another copy of, and the
		// values reach console commands.
		const TCHAR* Bad[] = {
			TEXT("only | two | parts"),
			TEXT(" | 10 | live | r.A=1"),
			TEXT("x | many | live | r.A=1"),
			TEXT("x | 90 | live | r.A=1"),
			TEXT("x | -5 | live | r.A=1"),
			TEXT("x | 10 | sometimes | r.A=1"),
			TEXT("x | 10 | live | "),
			TEXT("x | 10 | live | r.A"),
			TEXT("x | 10 | live | r.A="),
			TEXT("x | 10 | live | =1"),
			TEXT("x | 10 | live | r.A=1;quit"),
			TEXT("x | 10 | live | r.A=\"1\""),
			TEXT("x | 10 | live | r.A b=1"),
			TEXT("x | 10 | live | r.A=1 2 | extra"),
		};
		for (const TCHAR* Line : Bad)
		{
			FMIQualityStep S;
			FString Error;
			TestFalse(FString::Printf(TEXT("refused: %s"), Line), FMIQualityTable::ParseStep(Line, S, &Error));
			TestFalse(FString::Printf(TEXT("and it says why: %s"), Line), Error.IsEmpty());
		}
	}
	{
		TArray<FString> Lines;
		Lines.Add(TEXT("one | 5 | live | r.A=1"));
		Lines.Add(TEXT("broken"));
		Lines.Add(TEXT("   "));
		Lines.Add(TEXT("two | 7 | live | r.A=2, r.B=3"));
		Lines.Add(TEXT("three | 9 | calm | r.B=4, r.C=5"));
		TArray<FString> Errors;
		const TArray<FMIQualityStep> Steps = FMIQualityTable::Parse(Lines, &Errors);
		TestEqual(TEXT("three good lines"), Steps.Num(), 3);
		TestEqual(TEXT("one error, for the broken line"), Errors.Num(), 1);
		const TArray<FString> Names = FMIQualityTable::Names(Steps);
		TestEqual(TEXT("three variables, each once"), Names.Num(), 3);
		FString V;
		TestFalse(TEXT("step 0 sets nothing: the baseline holds"), FMIQualityTable::ValueAt(Steps, 0, TEXT("r.A"), V));
		TestTrue(TEXT("r.A at step 1"), FMIQualityTable::ValueAt(Steps, 1, TEXT("r.A"), V));
		TestEqual(TEXT("... is 1"), V, FString(TEXT("1")));
		TestTrue(TEXT("r.A at step 2"), FMIQualityTable::ValueAt(Steps, 2, TEXT("r.A"), V));
		TestEqual(TEXT("... is 2: the last step at or below wins"), V, FString(TEXT("2")));
		TestTrue(TEXT("r.A at step 3"), FMIQualityTable::ValueAt(Steps, 3, TEXT("r.A"), V));
		TestEqual(TEXT("... still 2: step 3 does not set it"), V, FString(TEXT("2")));
		TestFalse(TEXT("r.B is not set by step 1: the baseline holds"), FMIQualityTable::ValueAt(Steps, 1, TEXT("r.B"), V));
		TestTrue(TEXT("r.b at step 3 (the name is not case sensitive)"), FMIQualityTable::ValueAt(Steps, 3, TEXT("r.b"), V));
		TestEqual(TEXT("... is 4"), V, FString(TEXT("4")));
		TestTrue(TEXT("a step number past the table is the last step"), FMIQualityTable::ValueAt(Steps, 99, TEXT("r.C"), V));
		TestEqual(TEXT("... r.C is 5"), V, FString(TEXT("5")));
	}
	{
		TArray<FString> Lines;
		for (int32 I = 0; I < FMIQualityTable::MaxSteps + 3; ++I)
		{
			Lines.Add(FString::Printf(TEXT("s%d | 3 | live | r.A=%d"), I, I));
		}
		TArray<FString> Errors;
		TestEqual(TEXT("no more than the most"), FMIQualityTable::Parse(Lines, &Errors).Num(), FMIQualityTable::MaxSteps);
		TestEqual(TEXT("the rest are named"), Errors.Num(), 3);
	}
	return true;
}

// ---- the ladder -----------------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICloudQualityLadderTest, "MurderInc.Cloud.QualityLadder", MITest::Flags)

bool FMICloudQualityLadderTest::RunTest(const FString& Parameters)
{
	using namespace MIQualityTestsPrivate;
	{
		// A free GPU: 6 ms of a 16.7 ms frame, ten minutes of play: full quality, no change.
		FSim S;
		S.Setup(Five());
		TestEqual(TEXT("no change in ten minutes on a free GPU"), S.Run(600.0, 6.0, F60), 0);
		TestEqual(TEXT("step 0"), S.L.Step(), 0);
		// 12 ms of 16.7: 72 %, under the 85 % line: a card with room to spare keeps full quality.
		TestEqual(TEXT("12 ms at 60: no change"), S.Run(300.0, 12.0, F60), 0);
		// 14 ms is 84 %: under the line too.
		TestEqual(TEXT("14 ms at 60 (84 %): no change"), S.Run(300.0, 14.0, F60), 0);
	}
	{
		// E3DS's card with a fight on it: 15.5 ms of 16.7 at the smallest picture, 93 %: the ladder acts while the rate is still held.
		FSim S;
		S.Setup(Five(0.12));
		TestEqual(TEXT("2.5 s over the line: not yet"), S.Run(2.5, 15.5, F60), 0);
		TestEqual(TEXT("3 s: a step"), S.Run(0.5, 15.5, F60), 1);
		TestEqual(TEXT("step 1"), S.L.Step(), 1);
		AddInfo(FString::Printf(TEXT("log line: %s"), *S.L.Why()));
		TestTrue(TEXT("13.6 ms is under 14.2: it stays there"), S.Run(120.0, 15.5, F60) == 0);
		TestEqual(TEXT("still step 1"), S.L.Step(), 1);
	}
	{
		// The walk down a heavy load at 30 frames a second (33.3 ms): 40 ms, each step saves a tenth. The line is 28.3 ms:
		// 40, 36, 32.4, 29.2 are over it, 26.2 (step 4) is not. One step in ten seconds at most.
		FSim S;
		S.Setup(Five());
		TestEqual(TEXT("four steps"), S.Run(120.0, 40.0, F30), 4);
		TestEqual(TEXT("it ends on step 4"), S.L.Step(), 4);
		bool bOk = S.Changes.Num() == 4;
		if (bOk)
		{
			TestTrue(TEXT("the first after 3 s"), FMath::IsNearlyEqual(S.Changes[0].Key, 3.0, 0.01));
			TestTrue(TEXT("the second 10 s later"), FMath::IsNearlyEqual(S.Changes[1].Key, 13.0, 0.01));
			TestTrue(TEXT("the third"), FMath::IsNearlyEqual(S.Changes[2].Key, 23.0, 0.01));
			TestTrue(TEXT("the fourth"), FMath::IsNearlyEqual(S.Changes[3].Key, 33.0, 0.01));
		}
		TestTrue(TEXT("the GPU's time is under the line at the end"), S.GpuNow(40.0) < 0.85 * F30);
		// The heaviest load there is: 100 ms. All five steps, and then there is nothing left to give.
		FSim H;
		H.Setup(Five());
		TestEqual(TEXT("100 ms: every step is taken"), H.Run(300.0, 100.0, F30), 5);
		TestEqual(TEXT("step 5, the last"), H.L.Step(), 5);
		TestEqual(TEXT("and no more"), H.Run(300.0, 100.0, F30), 0);
	}
	{
		// Only at the smallest picture: dynamic resolution still has a smaller picture to give first.
		FSim S;
		S.Setup(Five());
		TestEqual(TEXT("40 ms at 30 while the picture can still shrink: nothing"), S.Run(120.0, 40.0, F30, false, false), 0);
		// A game that the pacer holds back counts although the time it measures is low.
		TestEqual(TEXT("held back by the GPU at the smallest picture, 3 s: a step"), S.Run(3.0, 5.0, F60, false, true, true, true), 1);
		// Not in a menu: a set-up screen is not what the player came for.
		FSim M;
		M.Setup(Five());
		TestEqual(TEXT("40 ms for ten minutes on a card or a set-up screen: nothing"), M.Run(600.0, 40.0, F30, true), 0);
		// An unknown GPU time is no time.
		FSim U;
		U.Setup(Five());
		TestEqual(TEXT("no GPU time known: nothing"), U.Run(120.0, 0.0, F30), 0);
	}
	{
		// A step that may only be applied at a calm moment waits for one, with its evidence kept.
		TArray<FMIQualityStep> Steps;
		Steps.Add(MakeStep(TEXT("hitchy"), 0.2, true));
		Steps.Add(MakeStep(TEXT("live"), 0.1, false));
		FSim S;
		S.Setup(Steps);
		TestEqual(TEXT("30 s in play over the line: a calm step is not taken in play"), S.Run(30.0, 40.0, F30), 0);
		TestEqual(TEXT("a calm moment: now"), S.Run(0.5, 40.0, F30, true), 1);
		TestEqual(TEXT("step 1"), S.L.Step(), 1);
		// The next one is a live step: it is taken in play, 10 s after.
		TestEqual(TEXT("the live step follows in play"), S.Run(15.0, 40.0, F30), 1);
		TestEqual(TEXT("step 2"), S.L.Step(), 2);
	}
	{
		// The way back: only at a safe moment, only after a minute of calm in play, only when the rate is at its highest.
		FSim S;
		S.Setup(Five());
		S.Run(60.0, 40.0, F30);
		const int32 Low = S.L.Step();
		TestEqual(TEXT("down to step 4 under the heavy load"), Low, 4);
		// The load goes: 8 ms at step 0 (7 ms at step 4: without the last step 8.1 ms, under 70 % of 16.7 = 11.7 ms).
		TestEqual(TEXT("a quiet minute less half a second in play: nothing"), S.Run(59.5, 8.0, F60), 0);
		TestEqual(TEXT("a safe moment before a minute is up: nothing"), S.Run(0.5, 8.0, F60, true), 0);
		TestEqual(TEXT("the minute is up in play: the step stays until a safe moment"), S.Run(0.5, 8.0, F60), 0);
		TestEqual(TEXT("in play for ten more minutes: still nothing without a safe moment"), S.Run(600.0, 8.0, F60), 0);
		TestEqual(TEXT("the first safe moment: up"), S.Run(0.5, 8.0, F60, true), 1);
		TestEqual(TEXT("step 3"), S.L.Step(), Low - 1);
		AddInfo(FString::Printf(TEXT("log line: %s"), *S.L.Why()));
		TestEqual(TEXT("the next one needs a minute of calm again"), S.Run(0.5, 8.0, F60, true), 0);
		TestEqual(TEXT("... and the 10 s between changes"), S.Run(60.0, 8.0, F60), 0);
		TestEqual(TEXT("... then a safe moment: step 2"), S.Run(0.5, 8.0, F60, true), 1);
		// A target that is not the highest one: the rate comes back first.
		FSim T;
		T.Setup(Five());
		T.Run(60.0, 40.0, F30);
		TestEqual(TEXT("at 30 or 45 the quality does not rise in play"), T.Run(600.0, 8.0, F45, false, true, false), 0);
		TestEqual(TEXT("... nor at a safe moment"), T.Run(1.0, 8.0, F45, true, true, false), 0);
		// A card that needed the steps to hold 60: the saving put back would take it over the up line: it stays.
		FSim K;
		K.Setup(Five(0.12));
		K.Run(10.0, 15.5, F60);
		TestEqual(TEXT("one step on a card that needs it"), K.L.Step(), 1);
		TestEqual(TEXT("13.6 ms now, 15.5 without the step: not under 70 % of 16.7: it stays"), K.Run(300.0, 15.5, F60), 0);
		TestEqual(TEXT("... also at a safe moment"), K.Run(1.0, 15.5, F60, true), 0);
	}
	{
		// A rise that does not hold: the next one waits twice as long.
		FSim S;
		S.Setup(Five());
		S.Run(15.0, 34.0, F30);
		TestEqual(TEXT("down"), S.L.Step(), 2);
		S.Run(61.0, 8.0, F60);
		TestEqual(TEXT("up at the first safe moment"), S.Run(0.5, 8.0, F60, true), 1);
		TestEqual(TEXT("step 1"), S.L.Step(), 1);
		TestTrue(TEXT("the wait for a rise is a minute"), FMath::IsNearlyEqual(S.L.UpWait(), 60.0));
		TestEqual(TEXT("the load comes back: down again, 10 s after the change"), S.Run(15.0, 34.0, F30), 1);
		TestTrue(TEXT("the wait is two minutes now"), FMath::IsNearlyEqual(S.L.UpWait(), 120.0));
		S.Run(61.0, 8.0, F60);
		TestEqual(TEXT("a minute is not enough any more"), S.Run(0.5, 8.0, F60, true), 0);
		S.Run(60.0, 8.0, F60);
		TestEqual(TEXT("two minutes are"), S.Run(0.5, 8.0, F60, true), 1);
	}
	{
		// Oscillation: a load that swings across the line every few seconds must not make it swing too.
		FSim S;
		S.Setup(Five(0.12));
		for (int32 Cycle = 0; Cycle < 200; ++Cycle)
		{
			S.Run(5.0, 19.0, F60);
			S.Run(5.0, 9.0, F60);
			if (Cycle % 9 == 8)
			{
				S.Run(1.0, 9.0, F60, true);   // a pause now and then
			}
		}
		TestTrue(TEXT("it changed at all"), S.Changes.Num() > 0);
		bool bGaps = true, bRange = true;
		for (int32 I = 0; I < S.Changes.Num(); ++I)
		{
			bRange = bRange && S.Changes[I].Value >= 0 && S.Changes[I].Value <= 5;
			bGaps = bGaps && (I == 0 || S.Changes[I].Key - S.Changes[I - 1].Key >= 10.0 - 1e-9);
		}
		TestTrue(TEXT("never within ten seconds of the change before"), bGaps);
		TestTrue(TEXT("always on a step of the table"), bRange);
		TestTrue(TEXT("a load that is over the line half of the time never calls for a rise: it only walks down, to the end"), S.Changes.Num() <= 5);
		// A load that stands right between the two lines: nothing at all.
		FSim B;
		B.Setup(Five(0.10));
		B.Run(30.0, 40.0, F30);                       // down some steps first
		const int32 Where = B.L.Step();
		// 25 ms on step 3 (34.3 at step 0): under the line of 28.3 ms, and 27.8 ms without the last step is over the up line of 23.3 ms.
		TestEqual(TEXT("between the lines for ten minutes: it stays"), B.Run(600.0, 34.3, F30), 0);
		TestEqual(TEXT("... also at a safe moment"), B.Run(1.0, 34.3, F30, true), 0);
		TestEqual(TEXT("... on the same step"), B.L.Step(), Where);
	}
	{
		// A series recorded the way the game feeds the ladder (every half second, the GPU's time in ms, 60 frames a second):
		// a minute of the street, twenty seconds of a fight on a card with little room, two minutes after it.
		TArray<double> Series;
		for (int32 I = 0; I < 120; ++I) { Series.Add(10.0 + (I % 5) * 0.1); }
		for (int32 I = 0; I < 40; ++I) { Series.Add(15.5 + (I % 3) * 0.2); }
		for (int32 I = 0; I < 240; ++I) { Series.Add(10.4 + (I % 4) * 0.1); }
		FMIQualityLadder L;
		TArray<FMIQualityStep> Steps = Five(0.12);
		L.Configure(Steps);
		double Time = 0.0, ChangeAt = -1.0;
		int32 Changes = 0;
		double Factor = 1.0;
		for (const double Gpu : Series)
		{
			Time += 0.5;
			FMIQualityLadder::FInput In;
			In.Seconds = 0.5;
			In.GpuMs = Gpu * Factor;
			In.FrameMs = F60;
			In.bSmallestPicture = true;
			const FMIQualityLadder::EChange C = L.Update(In);
			if (C != FMIQualityLadder::EChange::None)
			{
				++Changes;
				if (ChangeAt < 0.0)
				{
					ChangeAt = Time;
				}
				Factor = FMath::Pow(0.88, L.Step());
			}
		}
		TestEqual(TEXT("one change in the whole series"), Changes, 1);
		TestTrue(TEXT("three seconds into the fight"), FMath::IsNearlyEqual(ChangeAt, 63.0, 0.01));
		TestEqual(TEXT("on step 1"), L.Step(), 1);
	}
	{
		// A pin holds whatever the load; "off" puts full quality back and keeps it.
		FSim S;
		S.Setup(Five());
		S.L.Pin(3);
		TestEqual(TEXT("pinned at 3"), S.L.Step(), 3);
		TestEqual(TEXT("a heavy load moves nothing"), S.Run(120.0, 100.0, F30), 0);
		TestEqual(TEXT("a calm one neither"), S.Run(300.0, 3.0, F60), 0);
		TestEqual(TEXT("... not at a safe moment"), S.Run(1.0, 3.0, F60, true), 0);
		TestEqual(TEXT("still 3"), S.L.Step(), 3);
		S.L.Pin(99);
		TestEqual(TEXT("a pin past the end is the last step"), S.L.Step(), 5);
		S.L.Pin(-1);
		TestFalse(TEXT("free again"), S.L.IsPinned());
		TestEqual(TEXT("it moves again: nothing to give up on a calm card, the walk is down only when over"), S.Run(60.0, 3.0, F60), 0);
		S.L.SetEnabled(false);
		TestEqual(TEXT("off: step 0"), S.L.Step(), 0);
		TestEqual(TEXT("and it stays"), S.Run(120.0, 100.0, F30), 0);
		FMIQualityLadder Empty;
		FMIQualityLadder::FInput In;
		In.Seconds = 0.5;
		In.GpuMs = 100.0;
		In.bSmallestPicture = true;
		TestTrue(TEXT("no steps in the table: nothing to do"), Empty.Update(In) == FMIQualityLadder::EChange::None);
	}
	return true;
}

// ---- the defaults ---------------------------------------------------------------------------------------------------

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICloudQualityDefaultsTest, "MurderInc.Cloud.QualityDefaults", MITest::Flags)

bool FMICloudQualityDefaultsTest::RunTest(const FString& Parameters)
{
	const auto Num = [this](const TCHAR* Name, double Expect)
	{
		IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(Name);
		if (!V)
		{
			AddError(FString::Printf(TEXT("no console variable %s"), Name));
			return;
		}
		TestTrue(FString::Printf(TEXT("%s is %g (it is %s)"), Name, Expect, *V->GetString()), FMath::IsNearlyEqual((double)V->GetFloat(), Expect, 1e-4));
	};
	Num(TEXT("MI.Cloud.QualityLadder"), 1.0);
	Num(TEXT("MI.Cloud.QualityStep"), -1.0);
	Num(TEXT("MI.Cloud.QualityDownLoad"), 0.85);
	Num(TEXT("MI.Cloud.QualityUpLoad"), 0.70);
	Num(TEXT("MI.Cloud.QualityDownAfter"), 3.0);
	Num(TEXT("MI.Cloud.QualityUpAfter"), 60.0);
	Num(TEXT("MI.Cloud.QualityMinGap"), 10.0);

	// The steps of DefaultGame.ini (the cloud profile): every line is usable, and every variable exists. A misspelt name would be
	// a step that does nothing in a package, found out on E3DS.
	TArray<FString> Errors;
	const TArray<FMIQualityStep> Steps = UMICloudSubsystem::ReadQualityTable(&Errors);
	for (const FString& E : Errors)
	{
		AddError(FString::Printf(TEXT("DefaultGame.ini [MICloud] QualitySteps: %s"), *E));
	}
	TestTrue(TEXT("the cloud profile has a quality ladder"), Steps.Num() >= 3);
	for (const FMIQualityStep& S : Steps)
	{
		for (const TPair<FString, FString>& P : S.CVars)
		{
			TestNotNull(FString::Printf(TEXT("step \"%s\": console variable %s exists"), *S.Name, *P.Key), IConsoleManager::Get().FindConsoleVariable(*P.Key));
		}
		TestTrue(FString::Printf(TEXT("step \"%s\" saves something"), *S.Name), S.Saves > 0.0);
	}
	return true;
}

#endif
