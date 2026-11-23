// MurderInc.Audio.Voice* on the shipped voice.json and the real take lengths: the win is always called, a burst of
// kills stays one line, takes follow the moment's intensity, a pause or a restart leaves nothing behind, and how often
// the voice speaks over a whole Story run (spec 04 2.10) and a Hold the Block run (spec 04 2.11). Also the generated
// effect files: no variant cut far shorter than its siblings, one loudness per variant set (AUDIO.md 6).

#include "Audio/MIAudioData.h"
#include "Audio/MIAudioDirector.h"
#include "Audio/MIAudioMaster.h"
#include "Audio/MIOfflineMix.h"
#include "Audio/MIVoiceRules.h"
#include "Audio/MIVoiceTriggers.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Core/MIEvents.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Enemies/MIEnemies.h"
#include "Flow/MIGameRules.h"
#include "Misc/AutomationTest.h"
#include "Misc/Paths.h"

#if WITH_AUTOMATION_TESTS

namespace MIAudioVoicePrivate
{
	constexpr EAutomationTestFlags Flags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter;

	FMIFlowEvent Flow(const TCHAR* Name, const TCHAR* Text = TEXT(""), double A = 0, double B = 0)
	{
		FMIFlowEvent F;
		F.Name = Name;
		F.Text = Text;
		F.A = A;
		F.B = B;
		return F;
	}

	FMIEnemyEvent Kill(int32 Id, FName Part, FName Weapon, bool bBuzzard = false)
	{
		FMIEnemyEvent E;
		E.Kind = FMIEnemyEvent::EKind::Killed;
		E.Id = Id;
		E.Type = bBuzzard ? MIEnemy::EType::Buzzard : MIEnemy::EType::Goon;
		E.Part = Part;
		E.Weapon = Weapon;
		E.bByPlayer = true;
		return E;
	}

	/** The real length of a take (Content/Audio/Voice/<character>/<file>), cached; 1.5 s when the file is missing. */
	double RealSecs(FName Character, const FString& File)
	{
		static TMap<FString, double> Cache;
		const FString Key = Character.ToString() + TEXT("/") + File;
		if (const double* S = Cache.Find(Key))
		{
			return *S;
		}
		FMIWav W;
		const double Secs = FMIWav::Load(FPaths::Combine(FMIAudioData::AudioDir(), TEXT("Voice"), Key), W) ? W.Secs() : 1.5;
		Cache.Add(Key, Secs);
		return Secs;
	}

	/** Triggers and rules on the shipped data, driven by a time-ordered script at 30 frames a second. */
	struct FSim
	{
		FMIVoiceRules R;
		FMIVoiceTriggers T;
		double Now = 0.0;
		TArray<TPair<double, TFunction<void()>>> Script;
		TArray<FMIVoicePlay> Plays;
		TArray<FString> Fired;
		int32 Next = 0;

		void Init(const FMIVoiceData& D, int32 Seed)
		{
			R.TakeSecs = [](FName C, const FString& F) { return RealSecs(C, F); };
			R.Init(&D, TEXT("rule"), D.Settings.Defaults, Seed);
			T.Init(D.Settings);
			T.OnTrigger = [this](FName N, int32 V) { Fired.Add(N.ToString()); R.Trigger(N, Now, V); };
			T.OnSilence = [this]() { R.Silence(Now); };
			T.OnRunStart = [this]() { R.NewRun(); };
		}
		void At(double Time, TFunction<void()> F) { Script.Add({Time, MoveTemp(F)}); }
		void FlowAt(double Time, const FMIFlowEvent& E) { At(Time, [this, E]() { T.OnFlow(E, Now); }); }
		void KillAt(double Time, const FMIEnemyEvent& E) { At(Time, [this, E]() { T.OnEnemy(E, Now); }); }
		void HitAt(double Time, double Amount, double Health)
		{
			At(Time, [this, Amount, Health]() { FMIPlayerHitEvent H; H.Amount = Amount; H.Health = Health; T.OnPlayerHit(H, Now); });
		}
		void Run(double Until)
		{
			if (Next == 0)
			{
				Script.StableSort([](const auto& A, const auto& B) { return A.Key < B.Key; });
			}
			for (; Now <= Until; Now += 1.0 / 30.0)
			{
				while (Next < Script.Num() && Script[Next].Key <= Now)
				{
					Script[Next++].Value();
				}
				T.Tick(Now);
				R.Tick(Now, Plays);
			}
		}
		int32 Count(FName Line, double From = -1e9, double To = 1e9) const
		{
			int32 N = 0;
			for (const FMIVoicePlay& P : Plays)
			{
				N += P.Line == Line && P.Start >= From && P.Start <= To ? 1 : 0;
			}
			return N;
		}
	};

	bool LoadVoice(FAutomationTestBase& Test, FMIVoiceData& D)
	{
		FString Error;
		if (!FMIVoiceData::Load(D, Error))
		{
			Test.AddError(TEXT("voice.json: ") + Error);
			return false;
		}
		return true;
	}

	/** config.json flow numbers (spec 04 2.10, 2.11), with the spec's values when a key is missing. */
	struct FFlowNumbers
	{
		int32 PatrolGoons = 4, PatrolBuzzards = 2;
		TArray<FIntPoint> Waves = {FIntPoint(5, 2), FIntPoint(6, 3), FIntPoint(7, 4)};  // goons, buzzards after each reel
		int32 PursuitBudget = 8;
		double PursuitEvery = 5.5;
		double Breather = 9.0, FirstDelay = 3.5;
		double GoonShot = 6.0, GoonRush = 22.0;

		void Load()
		{
			TSharedPtr<FJsonObject> Root;
			FString Error;
			if (!UMIDataSubsystem::LoadJsonFile(TEXT("config.json"), Root, Error))
			{
				return;
			}
			using namespace MIAudioJson;
			const TSharedPtr<FJsonObject> FlowT = Obj(Root, TEXT("flow"));
			const TSharedPtr<FJsonObject> Boss = Obj(Obj(FlowT, TEXT("difficulty")), TEXT("boss"));
			if (const TSharedPtr<FJsonObject> P = Obj(Boss, TEXT("patrol")))
			{
				PatrolGoons = (int32)Num(P, TEXT("goon"), PatrolGoons);
				PatrolBuzzards = (int32)Num(P, TEXT("buzzard"), PatrolBuzzards);
			}
			const TArray<TSharedPtr<FJsonValue>>* W = nullptr;
			if (Boss.IsValid() && Boss->TryGetArrayField(TEXT("waves"), W))
			{
				Waves.Reset();
				for (const TSharedPtr<FJsonValue>& V : *W)
				{
					const TSharedPtr<FJsonObject> O = V->AsObject();
					Waves.Add(FIntPoint((int32)Num(O, TEXT("goon"), 5), (int32)Num(O, TEXT("buzzard"), 2)));
				}
			}
			PursuitBudget = (int32)Num(Boss, TEXT("pursuitBudget"), PursuitBudget);
			PursuitEvery = Num(Boss, TEXT("pursuitEvery"), PursuitEvery);
			const TSharedPtr<FJsonObject> H = Obj(FlowT, TEXT("holdout"));
			Breather = Num(H, TEXT("breather"), Breather);
			FirstDelay = Num(H, TEXT("firstDelay"), FirstDelay);
			const TSharedPtr<FJsonObject> G = Obj(Obj(Obj(Obj(Root, TEXT("enemies")), TEXT("difficulty")), TEXT("boss")), TEXT("goon"));
			GoonShot = Num(G, TEXT("shotDamage"), GoonShot);
			GoonRush = Num(G, TEXT("rushDamage"), GoonRush);
		}
	};

	/**
	 * One fight: N enemies (the first B of them Buzzards) killed from Start on, 1 to 4 s apart with one kill in five
	 * a quick follow-up (0.3 to 0.9 s); a quarter of the Goons by headshot. The player is hit every 1.5 to 5 s while it
	 * lasts. Returns the time of the last kill.
	 */
	double Fight(FSim& S, FRandomStream& Rng, double Start, int32 N, int32 B, int32& Id, double& Health, double Shot, double Rush, double DamageScale = 1.0)
	{
		double T = Start;
		for (int32 K = 0; K < N; ++K)
		{
			T += Rng.FRand() < 0.2 ? Rng.FRandRange(0.3, 0.9) : Rng.FRandRange(1.0, 4.0);
			const bool bBuzzard = K < B;
			const FName Part = !bBuzzard && Rng.FRand() < 0.25 ? FName(TEXT("head")) : FName(TEXT("body"));
			const FName Weapon = Id % 17 == 9 ? FName(TEXT("melee")) : Id % 23 == 11 ? FName(TEXT("blast")) : FName(TEXT("chopper"));
			S.KillAt(T, Kill(Id++, Part, Weapon, bBuzzard));
		}
		for (double H = Start + Rng.FRandRange(1.5, 5.0); H < T; H += Rng.FRandRange(1.5, 5.0))
		{
			const double Amount = (Rng.FRand() < 0.1 ? Rush : Shot) * DamageScale;
			Health = FMath::Max(12.0, Health - Amount);
			S.HitAt(H, Amount, Health);
		}
		return T;
	}
}

using namespace MIAudioVoicePrivate;

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioVoiceWinTest, "MurderInc.Audio.VoiceWin", Flags)
bool FMIAudioVoiceWinTest::RunTest(const FString& Parameters)
{
	FMIVoiceData D;
	if (!LoadVoice(*this, D))
	{
		return false;
	}
	// A 20-kill streak says "What's my name" (cooldown 60 s); the truck reached 25 s later must say it again.
	int32 Bad = 0, Shouted = 0;
	for (int32 Seed = 0; Seed < 10; ++Seed)
	{
		FSim S;
		S.Init(D, Seed);
		S.FlowAt(0.0, Flow(TEXT("game:state"), TEXT("intro")));
		S.FlowAt(2.0, Flow(TEXT("game:state"), TEXT("playing")));
		for (int32 K = 0; K < 20; ++K)
		{
			S.KillAt(10.0 + K * 1.0, Kill(K, TEXT("body"), TEXT("chopper")));
		}
		S.FlowAt(54.0, Flow(TEXT("extraction:reached")));
		S.Run(64.0);
		const FMIVoicePlay* Streak = S.Plays.FindByPredicate([](const FMIVoicePlay& P) { return P.Line == TEXT("name") && P.Trigger == TEXT("kill.streak"); });
		const FMIVoicePlay* Win = S.Plays.FindByPredicate([](const FMIVoicePlay& P) { return P.Line == TEXT("name") && P.Trigger == TEXT("run.win"); });
		const bool bAnswered = Win && S.Count(TEXT("rule_chant"), Win->Start, Win->Start + 4.0) == 1;
		if (!Streak || !Win || !bAnswered)
		{
			++Bad;
			AddError(FString::Printf(TEXT("seed %d: streak line %s, win line %s, crowd answer %s"), Seed, Streak ? TEXT("yes") : TEXT("no"), Win ? TEXT("yes") : TEXT("no"), bAnswered ? TEXT("yes") : TEXT("no")));
		}
		Shouted += Win && Win->Intensity == TEXT("shout") ? 1 : 0;
	}
	TestEqual(TEXT("the win is called after a streak 25 s earlier, and answered"), Bad, 0);
	TestEqual(TEXT("the win is always a shouted take"), Shouted, 10);

	// The win while "I-N-C!" (70) speaks: it cuts it (100 >= 70 + 30); behind the uninterruptible streak line it waits.
	for (int32 Seed = 0; Seed < 40; ++Seed)
	{
		FMIVoiceRules R;
		R.TakeSecs = [](FName C, const FString& F) { return RealSecs(C, F); };
		R.Init(&D, TEXT("rule"), D.Settings.Defaults, Seed);
		TArray<FMIVoicePlay> Out;
		R.Trigger(TEXT("run.start"), 0.0);
		R.Tick(0.4, Out);
		if (Out.Num() != 1 || Out[0].Line != TEXT("inc"))
		{
			continue;  // run.start has chance 0.8: find a seed where it spoke
		}
		R.Trigger(TEXT("run.win"), 0.5);
		R.Tick(0.9, Out);
		TestTrue(TEXT("the win cuts I-N-C!"), Out.Num() == 2 && Out[1].Line == TEXT("name") && Out[1].bInterrupt);
		break;
	}
	{
		FMIVoiceRules R;
		R.TakeSecs = [](FName C, const FString& F) { return RealSecs(C, F); };
		R.Init(&D, TEXT("rule"), D.Settings.Defaults, 3);
		TArray<FMIVoicePlay> Out;
		R.Trigger(TEXT("kill.streak"), 0.0, 20);
		R.Tick(0.4, Out);
		R.Trigger(TEXT("run.win"), 0.6);
		for (double T = 0.7; T < 9.0; T += 1.0 / 30.0)
		{
			R.Tick(T, Out);
		}
		const int32 Names = Out.FilterByPredicate([](const FMIVoicePlay& P) { return P.Line == TEXT("name"); }).Num();
		TestEqual(TEXT("a win during the uninterruptible streak line waits and is still called"), Names, 2);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioVoiceBurstTest, "MurderInc.Audio.VoiceBurst", Flags)
bool FMIAudioVoiceBurstTest::RunTest(const FString& Parameters)
{
	FMIVoiceData D;
	if (!LoadVoice(*this, D))
	{
		return false;
	}
	// Ten kills 0.3 s apart (every third a headshot): at most one line, never a cut ("Holla, ho- It's Murda!").
	int32 Worst = 0, Cuts = 0, Spoke = 0;
	for (int32 Seed = 0; Seed < 40; ++Seed)
	{
		FSim S;
		S.Init(D, Seed);
		S.FlowAt(0.0, Flow(TEXT("game:state"), TEXT("title")));
		S.FlowAt(0.1, Flow(TEXT("game:state"), TEXT("playing")));
		for (int32 K = 0; K < 10; ++K)
		{
			S.KillAt(10.0 + K * 0.3, Kill(K, K % 3 == 2 ? FName(TEXT("head")) : FName(TEXT("body")), TEXT("chopper")));
		}
		S.Run(16.0);
		const int32 N = S.Plays.FilterByPredicate([](const FMIVoicePlay& P) { return P.Start >= 9.0; }).Num();
		Worst = FMath::Max(Worst, N);
		Spoke += N > 0 ? 1 : 0;
		for (const FMIVoicePlay& P : S.Plays)
		{
			Cuts += P.bInterrupt ? 1 : 0;
		}
	}
	AddInfo(FString::Printf(TEXT("ten kills in three seconds, 40 seeds: %d spoke, at most %d line(s), %d cut(s)"), Spoke, Worst, Cuts));
	TestTrue(TEXT("a burst is at most one line"), Worst <= 1);
	TestEqual(TEXT("no kill bark cuts another"), Cuts, 0);
	TestTrue(TEXT("a burst of ten kills usually gets its line"), Spoke >= 20);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioVoiceDirectorTest, "MurderInc.Audio.VoiceDirector", Flags)
bool FMIAudioVoiceDirectorTest::RunTest(const FString& Parameters)
{
	// The voice through the whole director, as the game runs it: the event bus in, audio commands out.
	FMIAudioData Data;
	FMIVoiceData Base;
	FString Error;
	if (!FMIAudioData::Load(Data, Error) || !FMIVoiceData::Load(Base, Error))
	{
		AddError(Error);
		return false;
	}
	FMIOfflineMix Files;
	Files.Root = FMIAudioData::AudioDir();
	if (Files.FileSecs(TEXT("Voice/rule/holla_01.wav")) <= 0.0)
	{
		AddError(TEXT("the take lengths cannot be read (Content/Audio/Voice/rule)"));
		return false;
	}
	struct FRig
	{
		FMIAudioDirector A;
		FMIGameEvents Bus;
		TArray<FString> Triggers;
		TArray<TPair<double, FString>> Lines;  // voice starts: time, file stem
		TSet<int32> VoiceIds;
		int32 VoiceStops = 0;
		void Step(double Secs)
		{
			for (double T = 0; T < Secs - 1e-9; T += 0.01)
			{
				A.Tick(0.01);
				TArray<FMIAudioCmd> Cmds;
				A.TakeCommands(Cmds);
				for (const FMIAudioCmd& C : Cmds)
				{
					if (C.Type == EMIAudioCmd::Start && C.Category == TEXT("voice") && C.File.StartsWith(TEXT("Voice/")))
					{
						Lines.Add({A.Now(), FPaths::GetBaseFilename(C.File)});
						VoiceIds.Add(C.Id);
					}
					else if (C.Type == EMIAudioCmd::Stop && VoiceIds.Contains(C.Id))
					{
						++VoiceStops;
					}
				}
			}
		}
		int32 LinesAfter(double T, const TCHAR* Stem = nullptr) const
		{
			int32 N = 0;
			for (const auto& L : Lines)
			{
				N += L.Key >= T && (!Stem || L.Value.StartsWith(Stem)) ? 1 : 0;
			}
			return N;
		}
	};
	auto Make = [&Data, &Files](FRig& Rig, const FMIVoiceData& V)
	{
		Rig.A.Exists = [](const FString&) { return true; };
		Rig.A.FileSecs = [&Files](const FString& F) { return Files.FileSecs(F); };
		Rig.A.Init(&Data, &V, 5);
		Rig.A.Bind(Rig.Bus);
		FMIVoiceTriggers& T = Rig.A.GetTriggers();
		TFunction<void(FName, int32)> Forward = T.OnTrigger;
		TArray<FString>* Log = &Rig.Triggers;
		T.OnTrigger = [Forward, Log](FName N, int32 V) { Log->Add(N.ToString()); Forward(N, V); };
		Rig.Bus.Flow.Broadcast(Flow(TEXT("game:state"), TEXT("title")));
		Rig.Bus.Flow.Broadcast(Flow(TEXT("game:state"), TEXT("playing")));
		Rig.Step(8.0);  // past the run start's line
	};

	// 1. A burst of ten kills: one line at most, nothing cut.
	{
		FRig Rig;
		Make(Rig, Base);
		const double T0 = Rig.A.Now();
		for (int32 K = 0; K < 10; ++K)
		{
			Rig.Bus.Enemy.Broadcast(Kill(K, K % 3 == 2 ? FName(TEXT("head")) : FName(TEXT("body")), TEXT("chopper")));
			Rig.Step(0.3);
		}
		Rig.Step(3.0);
		TestTrue(TEXT("director: a burst of ten kills is at most one line"), Rig.LinesAfter(T0) <= 1);
		TestEqual(TEXT("director: and no voice is cut"), Rig.VoiceStops, 0);
		Rig.A.Unbind();
	}
	// 2. A pause in the middle of the win line: nothing new while paused, no close call fires on the frozen clock,
	//    and the crowd answers once play resumes.
	{
		FRig Rig;
		Make(Rig, Base);
		FMIPlayerHitEvent Hit;
		Hit.Amount = 30;
		Hit.Health = 20;
		Rig.Bus.PlayerHit.Broadcast(Hit);
		Rig.Bus.Flow.Broadcast(Flow(TEXT("extraction:reached")));
		Rig.Step(0.5);
		const int32 Before = Rig.Lines.Num();
		TestTrue(TEXT("director: the win line starts"), Before >= 1 && Rig.Lines.Last().Value.StartsWith(TEXT("name_")));
		Rig.Bus.Flow.Broadcast(Flow(TEXT("game:state"), TEXT("paused")));
		Rig.Step(12.0);
		TestEqual(TEXT("director: nothing starts while paused (not even the crowd)"), Rig.Lines.Num(), Before);
		TestFalse(TEXT("director: no close call survived on the frozen clock"), Rig.Triggers.Contains(TEXT("health.lowSurvived")));
		Rig.Bus.Flow.Broadcast(Flow(TEXT("game:state"), TEXT("playing")));
		Rig.Step(4.0);
		TestEqual(TEXT("director: after the pause the crowd answers"), Rig.LinesAfter(0.0, TEXT("rule_chant")), 1);
		Rig.Step(6.0);
		TestTrue(TEXT("director: the close call counts once play time has passed"), Rig.Triggers.Contains(TEXT("health.lowSurvived")));
		Rig.A.Unbind();
	}
	// 3. Restart from the pause menu in the middle of the win line: the line stops, no answer, no queued line.
	{
		FRig Rig;
		Make(Rig, Base);
		Rig.Bus.Flow.Broadcast(Flow(TEXT("extraction:reached")));
		Rig.Step(0.5);
		Rig.Bus.Flow.Broadcast(Flow(TEXT("objective:all")));  // a queueable 'Rule Baby!' waiting behind it
		Rig.Step(0.4);
		Rig.Bus.Flow.Broadcast(Flow(TEXT("game:state"), TEXT("paused")));
		Rig.Step(0.5);
		const double T0 = Rig.A.Now();
		Rig.Bus.Flow.Broadcast(Flow(TEXT("player:reset")));
		Rig.Bus.Flow.Broadcast(Flow(TEXT("game:state"), TEXT("intro")));
		Rig.Step(5.0);
		TestTrue(TEXT("director: the old line is stopped"), Rig.VoiceStops >= 1);
		TestEqual(TEXT("director: no crowd answer after a restart"), Rig.LinesAfter(T0, TEXT("rule_chant")), 0);
		TestEqual(TEXT("director: no queued line of the old run"), Rig.LinesAfter(T0, TEXT("rulebaby")) + Rig.LinesAfter(T0, TEXT("name")), 0);
		Rig.A.Unbind();
	}
	// 4. Interruption: a progress beat cuts a kill bark (melee kill, then a reel half a second later).
	{
		FMIVoiceData V = Base;
		FMIVoiceCharacter& Rule = V.Characters[TEXT("rule")];
		for (FMIVoiceLine& L : Rule.Lines)
		{
			if (L.Id == TEXT("holla"))
			{
				L.Triggers[TEXT("kill.melee")].Chance = 1.0;
			}
			if (L.Id == TEXT("rulebaby"))
			{
				L.Triggers[TEXT("reel.collected")].Chance = 1.0;
			}
		}
		FRig Rig;
		Make(Rig, V);
		const double T0 = Rig.A.Now();
		Rig.Bus.Enemy.Broadcast(Kill(1, TEXT("body"), TEXT("melee")));
		Rig.Step(0.35);  // the bark starts at the end of its 0.3 s window; the reel comes while it speaks
		Rig.Bus.Flow.Broadcast(Flow(TEXT("objective:done"), TEXT("reel_1"), 1, 3));
		Rig.Step(1.0);
		const bool bOrder = Rig.LinesAfter(T0) == 2 && Rig.Lines[Rig.Lines.Num() - 2].Value.StartsWith(TEXT("holla")) && Rig.Lines.Last().Value.StartsWith(TEXT("rulebaby"));
		TestTrue(TEXT("director: 'Rule Baby!' cuts 'Holla, holla!'"), bOrder);
		TestEqual(TEXT("director: the cut line is stopped"), Rig.VoiceStops, 1);
		Rig.A.Unbind();
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioVoiceRateTest, "MurderInc.Audio.VoiceRate", Flags)
bool FMIAudioVoiceRateTest::RunTest(const FString& Parameters)
{
	// A Story run on Boss as spec 04 2.10 and config.json have it: the patrol (4 Goons, 2 Buzzards), a wave after each
	// reel (5+2, 6+3, 7+4), 8 pursuit arrivals, the truck, the debrief; intro then playing, the objective line after
	// each reel, the player hit every 1.5 to 5 s in every fight. Real take lengths. 20 seeds.
	FMIVoiceData D;
	if (!LoadVoice(*this, D))
	{
		return false;
	}
	FFlowNumbers F;
	F.Load();
	double Minutes = 0.0, Total = 0.0;
	int32 Kills = 0, KillLines = 0, WinCalled = 0;
	TMap<FName, int32> PerLine;
	const int32 Seeds = 20;
	for (int32 Seed = 0; Seed < Seeds; ++Seed)
	{
		FSim S;
		S.Init(D, Seed);
		FRandomStream Rng(1000 + Seed);
		int32 Id = 0;
		double Health = 100.0;
		S.FlowAt(0.0, Flow(TEXT("game:state"), TEXT("intro")));
		S.FlowAt(4.0, Flow(TEXT("game:state"), TEXT("playing")));
		S.FlowAt(4.05, Flow(TEXT("hud:objective"), TEXT("Find the first reel")));
		double T = Fight(S, Rng, 20.0, F.PatrolGoons + F.PatrolBuzzards, F.PatrolBuzzards, Id, Health, F.GoonShot, F.GoonRush);
		const int32 Reels = F.Waves.Num();
		int32 Pursuit = F.PursuitBudget;
		for (int32 Reel = 1; Reel <= Reels; ++Reel)
		{
			T += Rng.FRandRange(30.0, 50.0);  // the search, the walk to the reel and the grab (about five minutes a run)
			Health = 100.0;
			S.FlowAt(T, Flow(TEXT("objective:done"), *FString::Printf(TEXT("reel_%d"), Reel), Reel, Reels));
			if (Reel == Reels)
			{
				S.FlowAt(T, Flow(TEXT("objective:all")));
			}
			S.FlowAt(T + 0.5, Flow(TEXT("hud:objective"), Reel == Reels ? TEXT("Get to the truck") : TEXT("Find the next reel")));
			const FIntPoint W = F.Waves[Reel - 1];
			// The pursuit's arrivals join the waves (budget spread over the three).
			const int32 Extra = Reel == Reels ? Pursuit : FMath::Min(Pursuit, F.PursuitBudget / Reels);
			Pursuit -= Extra;
			T = Fight(S, Rng, T + 3.0, W.X + W.Y + Extra, W.Y, Id, Health, F.GoonShot, F.GoonRush);
		}
		T += Rng.FRandRange(20.0, 35.0);  // the run to the truck
		S.FlowAt(T, Flow(TEXT("extraction:reached")));
		S.FlowAt(T + 0.1, Flow(TEXT("game:state"), TEXT("complete")));
		S.FlowAt(T + 4.0, Flow(TEXT("menus:card"), TEXT("complete")));
		const double End = T + 8.0;
		S.Run(End);
		Minutes += End / 60.0;
		Kills += Id;
		bool bWin = false;
		for (const FMIVoicePlay& P : S.Plays)
		{
			PerLine.FindOrAdd(P.Line)++;
			KillLines += P.Trigger.ToString().StartsWith(TEXT("kill.")) ? 1 : 0;
			bWin |= P.Line == TEXT("name") && P.Trigger == TEXT("run.win") && S.Count(TEXT("rule_chant"), P.Start, P.Start + 4.0) > 0;
		}
		WinCalled += bWin ? 1 : 0;
		Total += S.Plays.Num();
	}
	const double PerMinute = Total / Minutes;
	const double KillShare = double(KillLines) / FMath::Max(1, Kills);
	FString Lines;
	for (const auto& Pair : PerLine)
	{
		Lines += FString::Printf(TEXT(" %s %.2f/run"), *Pair.Key.ToString(), double(Pair.Value) / Seeds);
	}
	AddInfo(FString::Printf(TEXT("Story run on Boss (%.1f min, %d kills): %.2f lines a minute (%.1f a run), %.0f%% of the kills speak,%s"),
		Minutes / Seeds, Kills / Seeds, PerMinute, Total / Seeds, 100.0 * KillShare, *Lines));
	TestTrue(FString::Printf(TEXT("rare enough to stay a reward: 1 to 3 lines a minute (%.2f)"), PerMinute), PerMinute >= 1.0 && PerMinute <= 3.0);
	TestTrue(FString::Printf(TEXT("most kills stay silent: under a quarter speak (%.0f%%)"), 100.0 * KillShare), KillShare < 0.25);
	TestEqual(TEXT("the win is called and answered in every run"), WinCalled, Seeds);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioVoiceRateHoldoutTest, "MurderInc.Audio.VoiceRateHoldout", Flags)
bool FMIAudioVoiceRateHoldoutTest::RunTest(const FString& Parameters)
{
	// Hold the Block as spec 04 2.11 has it: waves of min(5 + 2n, 30) enemies (a third Buzzards), a 9 s breather after
	// each, enemy damage x min(2, 1 + 0.05 (n - 1)), the player hit every 1.5 to 5 s while a wave lasts (so no streak
	// survives), dead after wave 12 and the card. 20 seeds.
	FMIVoiceData D;
	if (!LoadVoice(*this, D))
	{
		return false;
	}
	FFlowNumbers F;
	F.Load();
	const int32 Seeds = 20, LastWave = 12;
	double Minutes = 0.0, Total = 0.0, MurdaPerMinWorst = 0.0;
	int32 NameByTen = 0;
	TMap<FName, int32> PerLine;
	for (int32 Seed = 0; Seed < Seeds; ++Seed)
	{
		FSim S;
		S.Init(D, Seed);
		FRandomStream Rng(5000 + Seed);
		int32 Id = 0;
		double Health = 100.0;
		S.FlowAt(0.0, Flow(TEXT("game:state"), TEXT("title")));
		S.FlowAt(0.5, Flow(TEXT("game:state"), TEXT("playing")));
		double T = 0.5 + F.FirstDelay;
		double WaveTen = 0.0;
		for (int32 N = 1; N <= LastWave; ++N)
		{
			const int32 Count = FMath::Min(5 + 2 * N, 30);
			S.FlowAt(T, Flow(TEXT("holdout:wave"), TEXT(""), N, Count));
			Health = 100.0;  // the resupply heals between waves
			T = Fight(S, Rng, T + 1.2, Count, Count / 3, Id, Health, F.GoonShot, F.GoonRush, FMath::Min(2.0, 1.0 + 0.05 * (N - 1)));
			S.FlowAt(T + 0.01, Flow(TEXT("objective:done"), TEXT("wave"), N, N));
			S.FlowAt(T + 0.01, Flow(TEXT("audio:sting"), TEXT("reel")));
			if (N == 10)
			{
				WaveTen = T + 3.0;
			}
			T += F.Breather + 3.0;  // breather and countdown
		}
		S.At(T, [&S]() { S.T.OnPlayerDead(S.Now); });
		S.FlowAt(T, Flow(TEXT("game:state"), TEXT("dead")));
		S.FlowAt(T + 3.0, Flow(TEXT("menus:card"), TEXT("dead"), 2, 30000));
		const double End = T + 8.0;
		S.Run(End);
		Minutes += End / 60.0;
		Total += S.Plays.Num();
		for (const FMIVoicePlay& P : S.Plays)
		{
			PerLine.FindOrAdd(P.Line)++;
		}
		NameByTen += S.Count(TEXT("name"), 0.0, WaveTen) > 0 ? 1 : 0;
		MurdaPerMinWorst = FMath::Max(MurdaPerMinWorst, S.Count(TEXT("murda")) / (End / 60.0));
	}
	const double PerMinute = Total / Minutes;
	const double Murda = PerLine.FindRef(TEXT("murda")) / Minutes;
	FString Lines;
	for (const auto& Pair : PerLine)
	{
		Lines += FString::Printf(TEXT(" %s %.2f/run (%.2f/min)"), *Pair.Key.ToString(), double(Pair.Value) / Seeds, Pair.Value / Minutes);
	}
	AddInfo(FString::Printf(TEXT("Hold the Block, %d waves (%.1f min): %.2f lines a minute (%.1f a run), It's Murda! %.2f a minute (worst run %.2f),%s"),
		LastWave, Minutes / Seeds, PerMinute, Total / Seeds, Murda, MurdaPerMinWorst, *Lines));
	TestTrue(FString::Printf(TEXT("'It's Murda!' at most once a minute in any run (worst %.2f)"), MurdaPerMinWorst), MurdaPerMinWorst <= 1.0);
	TestEqual(TEXT("'What's my name' by wave 10 in every run"), NameByTen, Seeds);
	TestTrue(FString::Printf(TEXT("the voice stays a reward: at most 3 lines a minute (%.2f)"), PerMinute), PerMinute <= 3.0);
	TestTrue(TEXT("the crowd answers every 'What's my name'"), PerLine.FindRef(TEXT("rule_chant")) == PerLine.FindRef(TEXT("name")));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioGenFilesTest, "MurderInc.Audio.GenFiles", Flags)
bool FMIAudioGenFilesTest::RunTest(const FString& Parameters)
{
	// The generated effects (Content/Audio/Gen, tools/audio/sfx_process.py): each variant set of a replacement layer is
	// cut alike (no variant under half the median length of its set) and levelled alike (the loudest 400 ms of each,
	// K-weighted, within 3 dB of the set's median), and the silenced shots sit 8 to 14 dB under the open ones.
	FMIAudioData D;
	FString Error;
	if (!FMIAudioData::Load(D, Error))
	{
		AddError(Error);
		return false;
	}
	auto Loudest = [](const FMIWav& W)
	{
		// The loudest 400 ms window (100 ms hop) of the K-weighted signal (BS.1770 at 48 kHz, two biquads), the mean
		// square over every channel: momentary loudness in LUFS, as tools/audio/sfx_process.py levels the sets.
		const int32 Frames = W.Frames(), Chs = W.Channels;
		TArray<double> K;
		K.SetNumZeroed(Frames);
		for (int32 C = 0; C < Chs; ++C)
		{
			double X1 = 0, X2 = 0, Y1 = 0, Y2 = 0, U1 = 0, U2 = 0, Z1 = 0, Z2 = 0;
			for (int32 F = 0; F < Frames; ++F)
			{
				const double X = W.Samples[F * Chs + C];
				const double Y = 1.53512485958697 * X - 2.69169618940638 * X1 + 1.19839281085285 * X2 + 1.69065929318241 * Y1 - 0.73248077421585 * Y2;
				X2 = X1; X1 = X; Y2 = Y1; Y1 = Y;
				const double Z = Y - 2.0 * U1 + U2 + 1.99004745483398 * Z1 - 0.99007225036621 * Z2;
				U2 = U1; U1 = Y; Z2 = Z1; Z1 = Z;
				K[F] += Z * Z / Chs;
			}
		}
		const int32 Win = W.Rate * 2 / 5, Hop = W.Rate / 10;
		double Best = 0.0;
		for (int32 F = 0;; F += Hop)
		{
			const int32 To = FMath::Min(Frames, F + Win);
			double E = 0.0;
			for (int32 I = F; I < To; ++I)
			{
				E += K[I];
			}
			Best = FMath::Max(Best, E / FMath::Max(1, To - F));
			if (F + Win >= Frames)
			{
				break;
			}
		}
		return -0.691 + 10.0 * FMath::LogX(10.0, Best + 1e-20);
	};
	int32 Sets = 0;
	TMap<FString, double> SetLoudness;  // "sound/layer" -> median loudness + layer volume, dB
	FString Report;
	for (const auto& Pair : D.Replace)
	{
		for (const FMIReplaceLayer& L : Pair.Value.Layers)
		{
			TArray<double> Secs, Loud;
			TArray<FString> Names;
			for (const FString& File : L.Files)
			{
				FMIWav W;
				if (FMIWav::Load(FPaths::Combine(FMIAudioData::AudioDir(), File), W))
				{
					Secs.Add(W.Secs());
					Loud.Add(Loudest(W));
					Names.Add(FPaths::GetBaseFilename(File));
				}
			}
			if (Names.Num() == 0)
			{
				continue;
			}
			TArray<double> SortedSecs = Secs, SortedLoud = Loud;
			SortedSecs.Sort();
			SortedLoud.Sort();
			const double MedSecs = SortedSecs[SortedSecs.Num() / 2], MedLoud = SortedLoud[SortedLoud.Num() / 2];
			SetLoudness.Add(Pair.Key.ToString() + TEXT("/") + L.Name.ToString(), MedLoud + 20.0 * FMath::LogX(10.0, FMath::Max(1e-6, L.Volume)));
			if (Names.Num() < 2)
			{
				continue;
			}
			++Sets;
			for (int32 I = 0; I < Names.Num(); ++I)
			{
				if (Secs[I] < 0.5 * MedSecs)
				{
					AddError(FString::Printf(TEXT("%s is %.3f s: under half the median length of its set (%.3f s)"), *Names[I], Secs[I], MedSecs));
				}
				if (FMath::Abs(Loud[I] - MedLoud) > 3.0)
				{
					AddError(FString::Printf(TEXT("%s: momentary loudness %.1f LUFS, %.1f dB off its set's %.1f"), *Names[I], Loud[I], Loud[I] - MedLoud, MedLoud));
				}
			}
			Report += FString::Printf(TEXT(" %s/%s %.2fs %.1fdB;"), *Pair.Key.ToString(), *L.Name.ToString(), MedSecs, MedLoud);
		}
	}
	for (const TCHAR* Gun : {TEXT("chopper"), TEXT("nine")})
	{
		const double* Open = SetLoudness.Find(FString::Printf(TEXT("%s_shot/close"), Gun));
		const double* Sup = SetLoudness.Find(FString::Printf(TEXT("%s_shot_silenced/close"), Gun));
		if (Open && Sup)
		{
			const double Under = *Open - *Sup;
			TestTrue(FString::Printf(TEXT("%s: the silenced shot sits 8 to 14 dB under the open one (%.1f dB)"), Gun, Under), Under >= 8.0 && Under <= 14.0);
		}
	}
	AddInfo(FString::Printf(TEXT("%d variant sets checked:%s"), Sets, *Report));
	TestTrue(TEXT("the generated variant sets are there"), Sets >= 20);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioMasterChainTest, "MurderInc.Audio.MasterChain", Flags)
bool FMIAudioMasterChainTest::RunTest(const FString& Parameters)
{
	// Spec 07 2.11: compressor -6 dB threshold, 8 dB knee, 2.5 : 1, attack 6 ms, release 140 ms, x 1.15, soft clip;
	// read from audio.json "master"; the ambience low-pass by interior and the music bus at 0.5 come from the same data.
	FMIAudioData D;
	FString Error;
	if (!FMIAudioData::Load(D, Error))
	{
		AddError(Error);
		return false;
	}
	const FMIMasterChain C = FMIMasterChain::FromData(D);
	TestTrue(TEXT("the chain's numbers are spec 07's"), C.bEnabled && FMath::IsNearlyEqual(C.ThresholdDb, -6.0) && FMath::IsNearlyEqual(C.KneeDb, 8.0)
		&& FMath::IsNearlyEqual(C.Ratio, 2.5) && FMath::IsNearlyEqual(C.AttackMs, 6.0) && FMath::IsNearlyEqual(C.ReleaseMs, 140.0) && FMath::IsNearlyEqual(C.Makeup, 1.15));
	FMIMasterCompressor M;
	M.Init(C, 48000);
	TestTrue(TEXT("under the knee: no reduction"), FMath::Abs(M.CurveDb(-20.0)) < 1e-6);
	TestTrue(TEXT("6 dB over the threshold: 6 - 6 / 2.5 = 3.6 dB of reduction"), FMath::IsNearlyEqual(M.CurveDb(0.0), -3.6, 0.01));
	TestTrue(TEXT("at the threshold the soft knee already reduces (0 < r < 1 dB)"), M.CurveDb(-6.0) < -0.1 && M.CurveDb(-6.0) > -1.0);
	TestTrue(TEXT("soft clip: linear to 0.6, never past 1"), FMath::IsNearlyEqual(FMIMasterCompressor::SoftClip(0.5f), 0.5f) && FMIMasterCompressor::SoftClip(4.0f) < 1.0f && FMIMasterCompressor::SoftClip(-4.0f) > -1.0f);
	// A full-scale 100 Hz sine for a second: pulled down by the compressor, then capped by the clip.
	float Peak = 0.f;
	for (int32 I = 0; I < 48000; ++I)
	{
		float L = FMath::Sin(2.f * PI * 100.f * I / 48000.f), R = L;
		M.Process(L, R);
		if (I > 4800)
		{
			Peak = FMath::Max(Peak, FMath::Abs(L));
		}
	}
	AddInfo(FString::Printf(TEXT("full-scale sine: deepest reduction %.1f dB, output peak %.3f"), M.MaxReductionDb(), Peak));
	TestTrue(TEXT("the compressor acts on a full-scale sine (3 dB or more)"), M.MaxReductionDb() < -3.0);
	TestTrue(TEXT("and the output stays under full scale"), Peak < 1.0f);
	const FMIAudioCategory* Music = D.Categories.Find(TEXT("music"));
	TestTrue(TEXT("the music bus is 0.5 (x 0.9 stem trim = spec 07's 0.45)"), Music && FMath::IsNearlyEqual(Music->Volume, 0.5));
	TestTrue(TEXT("the ambience low-pass base is 0.08 (20 kHz x 0.08^i)"), FMath::IsNearlyEqual(MIAudioJson::Num(MIAudioJson::Obj(D.Table(TEXT("mix")), TEXT("ambienceLowpass")), TEXT("base"), 0.0), 0.08));
	return true;
}

#endif
