// MurderInc.Audio.*: the voice-line rules (cooldowns, seeded chances, no repeats, priority and interruption, the
// clean-language switch, per-character sets, triggers from the bus), the event-to-sound table (every bus event has
// an entry), the director's mix decisions, and an offline mix-down of a recorded fight (docs/unreal/AUDIO.md 7).

#include "Audio/MIAudioData.h"
#include "Audio/MIAudioDirector.h"
#include "Audio/MIAudioEventLog.h"
#include "Audio/MIOfflineMix.h"
#include "Audio/MIVoiceRules.h"
#include "Audio/MIVoiceTriggers.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Core/MIEvents.h"
#include "Dom/JsonObject.h"
#include "Enemies/MIEnemies.h"
#include "Flow/MIGameRules.h"
#include "HAL/FileManager.h"
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Sound/SoundWave.h"
#include "Misc/PackageName.h"

#if WITH_AUTOMATION_TESTS

namespace MIAudioTestsPrivate
{
	constexpr EAutomationTestFlags Flags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter;

	/** A small voice set written for the tests, so retuning voice.json never changes what the rule tests prove. */
	const TCHAR* TestVoice = TEXT(R"JSON({
		"triggers": { "kill": "", "big": "", "story": "", "progress": "", "second": "", "kill.streak": "" },
		"settings": {
			"seed": 99, "globalCooldown": 4.0, "coalesceWindow": 0.2, "afterLineGap": 0.5, "interruptMargin": 30,
			"duck": { "music": 0.5, "attack": 0.05, "release": 0.4 },
			"frequency": {
				"off": { "chance": 0.0, "cooldown": 1, "globalCooldown": 1 },
				"rare": { "chance": 0.5, "cooldown": 2, "globalCooldown": 2 },
				"normal": { "chance": 1.0, "cooldown": 1, "globalCooldown": 1 },
				"often": { "chance": 2.0, "cooldown": 0.5, "globalCooldown": 0.5 } },
			"options": { "voiceVolume": 1, "subtitles": true, "frequency": "normal", "cleanLanguage": false }
		},
		"default": "hero",
		"characters": {
			"hero": { "speaker": "HERO", "lines": {
				"common": { "text": "Common!", "priority": 20, "cooldown": 10, "triggers": { "kill": 1.0 },
					"takes": [ { "file": "common_01.wav" }, { "file": "common_02.wav" }, { "file": "common_03.wav" } ] },
				"rare": { "text": "Rare!", "priority": 25, "cooldown": 0, "triggers": { "progress": 0.25 },
					"takes": [ { "file": "rare_01.wav" } ] },
				"second": { "text": "Second!", "priority": 22, "cooldown": 0, "triggers": { "second": 1.0 },
					"takes": [ { "file": "second_01.wav" } ] },
				"big": { "text": "Big!", "priority": 60, "cooldown": 5, "triggers": { "big": 1.0 }, "queueable": 3.0,
					"takes": [ { "file": "big_01.wav" }, { "file": "big_02.wav" } ] },
				"story": { "text": "What's my f***in' name?!", "priority": 90, "cooldown": 30, "interruptible": false, "profane": true,
					"clean": { "mode": "swap", "text": "What's my name?!", "takes": [ { "file": "story_clean_01.wav" } ] },
					"answer": { "line": "crowd", "delay": 0.3 },
					"triggers": { "story": 1.0, "kill.streak": { "chance": 1.0, "atLeast": 10 } },
					"takes": [ { "file": "story_01.wav", "bleep": [0.3, 0.6] } ] },
				"crowd": { "text": "R-U-L-E!", "speaker": "CROWD", "priority": 95, "cooldown": 0, "interruptible": false, "answerOnly": true,
					"triggers": {}, "takes": [ { "file": "crowd_01.wav" } ] }
			} },
			"other": { "speaker": "OTHER", "lines": {
				"mine": { "text": "Mine!", "priority": 20, "cooldown": 1, "triggers": { "kill": 1.0 }, "takes": [ { "file": "mine_01.wav" } ] }
			} },
			"quiet": { "speaker": "QUIET", "lines": {} }
		}
	})JSON");

	bool ParseJson(const TCHAR* Text, TSharedPtr<FJsonObject>& Out)
	{
		const TSharedRef<TJsonReader<>> R = TJsonReaderFactory<>::Create(Text);
		return FJsonSerializer::Deserialize(R, Out) && Out.IsValid();
	}

	bool LoadTestVoice(FAutomationTestBase& T, FMIVoiceData& Out)
	{
		TSharedPtr<FJsonObject> Root;
		FString Error;
		if (!ParseJson(TestVoice, Root) || !FMIVoiceData::Parse(Root, Out, Error))
		{
			T.AddError(TEXT("test voice data: ") + Error);
			return false;
		}
		return true;
	}

	/** Rules on the test data with every take 1 s long. */
	void Make(FMIVoiceRules& R, const FMIVoiceData& D, FName Character = TEXT("hero"), FName Frequency = TEXT("normal"), bool bClean = false)
	{
		FMIVoiceOptions O;
		O.Frequency = Frequency;
		O.bClean = bClean;
		R.TakeSecs = [](FName, const FString&) { return 1.0; };
		R.Init(&D, Character, O);
	}

	/** Trigger at T, then tick through the coalescing window; returns what started. */
	TArray<FMIVoicePlay> Fire(FMIVoiceRules& R, FName Trigger, double T, int32 Value = 0)
	{
		R.Trigger(Trigger, T, Value);
		TArray<FMIVoicePlay> Out;
		R.Tick(T + 0.25, Out);
		return Out;
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

	FMIFlowEvent Flow(const TCHAR* Name, const TCHAR* Text = TEXT(""), double A = 0, double B = 0)
	{
		FMIFlowEvent F;
		F.Name = Name;
		F.Text = Text;
		F.A = A;
		F.B = B;
		return F;
	}
}

using namespace MIAudioTestsPrivate;

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioVoiceDataTest, "MurderInc.Audio.VoiceData", Flags)
bool FMIAudioVoiceDataTest::RunTest(const FString& Parameters)
{
	FMIVoiceData D;
	FString Error;
	if (!FMIVoiceData::Load(D, Error))
	{
		AddError(TEXT("voice.json: ") + Error);
		return false;
	}
	const FMIVoiceCharacter* Rule = D.Characters.Find(TEXT("rule"));
	TestNotNull(TEXT("the player character's set"), Rule);
	if (!Rule)
	{
		return false;
	}
	// The five lines the user asked for, word for word (the profane one starred in its subtitle), plus the crowd.
	const TPair<const TCHAR*, const TCHAR*> Wanted[] = {
		{TEXT("murda"), TEXT("It's Murda!")}, {TEXT("holla"), TEXT("Holla, holla!")}, {TEXT("rulebaby"), TEXT("Rule Baby!")},
		{TEXT("name"), TEXT("What's my motherf***in' name?!")}, {TEXT("rule_chant"), TEXT("R-U-L-E!")}, {TEXT("inc"), TEXT("I-N-C!")}};
	int32 Missing = 0;
	for (const auto& W : Wanted)
	{
		const FMIVoiceLine* L = Rule->Find(W.Key);
		if (!L)
		{
			AddError(FString::Printf(TEXT("line %s missing"), W.Key));
			continue;
		}
		TestEqual(FString::Printf(TEXT("%s text"), W.Key), L->Text, FString(W.Value));
		TestTrue(FString::Printf(TEXT("%s has three or more takes"), W.Key), L->Takes.Num() >= 3);
		for (const FMIVoiceTake& T : L->Takes)
		{
			const FString Path = FPaths::Combine(FMIAudioData::AudioDir(), TEXT("Voice/rule"), T.File);
			FMIWav Wav;
			if (!FMIWav::Load(Path, Wav))
			{
				++Missing;
				AddError(TEXT("take missing: ") + Path);
			}
			else if (Wav.Rate != 48000 || Wav.Channels != 1)
			{
				AddError(FString::Printf(TEXT("%s: %d Hz %d channels, want 48000 mono"), *T.File, Wav.Rate, Wav.Channels));
			}
		}
	}
	const FMIVoiceLine* Name = Rule->Find(TEXT("name"));
	TestTrue(TEXT("the profane line is flagged and has clean takes"), Name && Name->bProfane && Name->CleanTakes.Num() >= 1);
	TestTrue(TEXT("the profane line is answered by the crowd"), Name && Name->AnswerLine == TEXT("rule_chant"));
	// Every crew member of crew.json has a voice set (empty is allowed: silent until recorded).
	for (const TCHAR* Crew : {TEXT("rule"), TEXT("deuce"), TEXT("smoke"), TEXT("keys")})
	{
		TestTrue(FString::Printf(TEXT("voice set for %s"), Crew), D.Characters.Contains(FName(Crew)));
	}
	AddInfo(FString::Printf(TEXT("%d lines for rule, %d known triggers, %d takes missing"), Rule->Lines.Num(), D.KnownTriggers.Num(), Missing));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioVoiceCooldownTest, "MurderInc.Audio.VoiceCooldowns", Flags)
bool FMIAudioVoiceCooldownTest::RunTest(const FString& Parameters)
{
	FMIVoiceData D;
	if (!LoadTestVoice(*this, D))
	{
		return false;
	}
	FMIVoiceRules R;
	Make(R, D);
	TestEqual(TEXT("first kill speaks"), Fire(R, TEXT("kill"), 0.0).Num(), 1);
	TestEqual(TEXT("within the line's 10 s cooldown: silent"), Fire(R, TEXT("kill"), 5.0).Num(), 0);
	TestEqual(TEXT("after the cooldown: speaks"), Fire(R, TEXT("kill"), 10.5).Num(), 1);

	// The global cooldown (4 s) holds a different line of similar priority...
	FMIVoiceRules G;
	Make(G, D);
	Fire(G, TEXT("kill"), 0.0);
	TestEqual(TEXT("another line inside the global cooldown (4 s): silent"), Fire(G, TEXT("second"), 2.0).Num() + Fire(G, TEXT("second"), 3.0).Num(), 0);
	TestEqual(TEXT("...and speaks once it is over"), Fire(G, TEXT("second"), 4.5).Num(), 1);
	// ...but a line far above the last one cuts through it.
	FMIVoiceRules B;
	Make(B, D);
	Fire(B, TEXT("kill"), 0.0);
	TestEqual(TEXT("a much bigger line inside the global cooldown: speaks"), Fire(B, TEXT("big"), 2.0).Num(), 1);

	// "How often": rare doubles the cooldowns, often halves them; off silences.
	FMIVoiceRules Rare;
	Make(Rare, D, TEXT("hero"), TEXT("rare"));
	int32 RarePlays = 0;
	for (int32 I = 0; I < 40; ++I)
	{
		RarePlays += Fire(Rare, TEXT("kill"), I * 11.0).Num();
	}
	TestTrue(TEXT("rare: cooldown 20 s and chance 0.5 keep it well under every other kill"), RarePlays > 0 && RarePlays <= 20);
	FMIVoiceRules Often;
	Make(Often, D, TEXT("hero"), TEXT("often"));
	TestEqual(TEXT("often: 5 s cooldown"), Fire(Often, TEXT("kill"), 0.0).Num() + Fire(Often, TEXT("kill"), 6.0).Num(), 2);
	FMIVoiceRules Off;
	Make(Off, D, TEXT("hero"), TEXT("off"));
	int32 OffPlays = 0;
	for (int32 I = 0; I < 20; ++I)
	{
		OffPlays += Fire(Off, TEXT("kill"), I * 20.0).Num() + Fire(Off, TEXT("story"), I * 20.0 + 5).Num();
	}
	TestEqual(TEXT("off: never"), OffPlays, 0);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioVoiceChanceTest, "MurderInc.Audio.VoiceChances", Flags)
bool FMIAudioVoiceChanceTest::RunTest(const FString& Parameters)
{
	FMIVoiceData D;
	if (!LoadTestVoice(*this, D))
	{
		return false;
	}
	// 'rare' has chance 0.25 and no cooldown; triggers 10 s apart clear the global cooldown every time.
	auto Run = [&D](TArray<int32>& Hits)
	{
		FMIVoiceRules R;
		Make(R, D);
		for (int32 I = 0; I < 4000; ++I)
		{
			if (Fire(R, TEXT("progress"), I * 10.0).Num() > 0)
			{
				Hits.Add(I);
			}
		}
	};
	TArray<int32> A, B;
	Run(A);
	Run(B);
	const double Rate = A.Num() / 4000.0;
	AddInfo(FString::Printf(TEXT("chance 0.25 over 4000 triggers: %.4f"), Rate));
	TestTrue(TEXT("the rate matches the chance (+-0.03)"), FMath::Abs(Rate - 0.25) < 0.03);
	TestTrue(TEXT("the same seed gives the same sequence"), A == B);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioVoiceRepeatTest, "MurderInc.Audio.VoiceNoRepeats", Flags)
bool FMIAudioVoiceRepeatTest::RunTest(const FString& Parameters)
{
	FMIVoiceData D;
	if (!LoadTestVoice(*this, D))
	{
		return false;
	}
	FMIVoiceRules R;
	Make(R, D);
	int32 Last = -1, Repeats = 0, Plays = 0;
	TSet<int32> Used;
	for (int32 I = 0; I < 300; ++I)
	{
		for (const FMIVoicePlay& P : Fire(R, TEXT("kill"), I * 11.0))
		{
			++Plays;
			Repeats += P.Take == Last ? 1 : 0;
			Last = P.Take;
			Used.Add(P.Take);
		}
	}
	TestEqual(TEXT("300 plays"), Plays, 300);
	TestEqual(TEXT("never the same take twice in a row"), Repeats, 0);
	TestEqual(TEXT("every take is used"), Used.Num(), 3);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioVoicePriorityTest, "MurderInc.Audio.VoicePriority", Flags)
bool FMIAudioVoicePriorityTest::RunTest(const FString& Parameters)
{
	FMIVoiceData D;
	if (!LoadTestVoice(*this, D))
	{
		return false;
	}
	// Two triggers in one coalescing window: the more important line speaks, the other does not.
	{
		FMIVoiceRules R;
		Make(R, D);
		R.Trigger(TEXT("kill"), 0.0);
		R.Trigger(TEXT("story"), 0.05);
		TArray<FMIVoicePlay> Out;
		R.Tick(0.3, Out);
		TestTrue(TEXT("one line from the window, the story beat"), Out.Num() == 1 && Out[0].Line == TEXT("story"));
		// Its answer a beat after the take ends (1 s + 0.3 s).
		TArray<FMIVoicePlay> Later;
		R.Tick(1.2, Later);
		TestEqual(TEXT("no answer before the take ends"), Later.Num(), 0);
		R.Tick(1.65, Later);
		TestTrue(TEXT("the crowd answers"), Later.Num() == 1 && Later[0].Line == TEXT("crowd") && Later[0].bAnswer && Later[0].Speaker == TEXT("CROWD"));
	}
	// Interruption: a much bigger line cuts an interruptible one; a smaller one does not.
	{
		FMIVoiceRules R;
		Make(R, D);
		Fire(R, TEXT("kill"), 0.0);
		const TArray<FMIVoicePlay> Cut = Fire(R, TEXT("big"), 0.1);
		TestTrue(TEXT("big (60) cuts common (20)"), Cut.Num() == 1 && Cut[0].bInterrupt);
	}
	{
		FMIVoiceRules R;
		Make(R, D);
		Fire(R, TEXT("story"), 0.0);
		TestEqual(TEXT("nothing cuts the uninterruptible story line"), Fire(R, TEXT("big"), 0.1).Num(), 0);
		// big is queueable (3 s): it speaks after the line and its gap, the crowd first.
		TArray<FMIVoicePlay> Out;
		for (double T = 0.4; T < 4.0; T += 0.05)
		{
			R.Tick(T, Out);
		}
		const bool bOrder = Out.Num() == 2 && Out[0].Line == TEXT("crowd") && Out[1].Line == TEXT("big");
		TestTrue(TEXT("queued: crowd answer, then the queued big line"), bOrder);
	}
	// Silence (death): nothing pending survives.
	{
		FMIVoiceRules R;
		Make(R, D);
		Fire(R, TEXT("story"), 0.0);
		R.Silence(0.5);
		TArray<FMIVoicePlay> Out;
		R.Tick(3.0, Out);
		TestEqual(TEXT("no answer after a silence"), Out.Num(), 0);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioVoiceCleanTest, "MurderInc.Audio.VoiceCleanLanguage", Flags)
bool FMIAudioVoiceCleanTest::RunTest(const FString& Parameters)
{
	FMIVoiceData D;
	if (!LoadTestVoice(*this, D))
	{
		return false;
	}
	{
		FMIVoiceRules R;
		Make(R, D);
		const TArray<FMIVoicePlay> P = Fire(R, TEXT("story"), 0.0);
		TestTrue(TEXT("clean off: the profane take and text"), P.Num() == 1 && P[0].File == TEXT("story_01.wav") && P[0].Text.Contains(TEXT("f***in")) && !P[0].bBleep);
	}
	{
		FMIVoiceRules R;
		Make(R, D, TEXT("hero"), TEXT("normal"), true);
		const TArray<FMIVoicePlay> P = Fire(R, TEXT("story"), 0.0);
		TestTrue(TEXT("clean on, swap: the clean take and text"), P.Num() == 1 && P[0].File == TEXT("story_clean_01.wav") && P[0].Text == TEXT("What's my name?!"));
	}
	{
		FMIVoiceData Bleep = D;
		FMIVoiceLine* L = const_cast<FMIVoiceLine*>(Bleep.Characters[TEXT("hero")].Find(TEXT("story")));
		L->CleanMode = TEXT("bleep");
		FMIVoiceRules R;
		Make(R, Bleep, TEXT("hero"), TEXT("normal"), true);
		const TArray<FMIVoicePlay> P = Fire(R, TEXT("story"), 0.0);
		TestTrue(TEXT("clean on, bleep: the normal take with its bleep range"), P.Num() == 1 && P[0].File == TEXT("story_01.wav") && P[0].bBleep
			&& FMath::IsNearlyEqual(P[0].BleepStart, 0.3) && FMath::IsNearlyEqual(P[0].BleepEnd, 0.6));
	}
	{
		FMIVoiceRules R;
		Make(R, D, TEXT("hero"), TEXT("normal"), true);
		const TArray<FMIVoicePlay> P = Fire(R, TEXT("kill"), 0.0);
		TestTrue(TEXT("clean on leaves clean lines alone"), P.Num() == 1 && P[0].File.StartsWith(TEXT("common_")) && !P[0].bBleep);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioVoiceCharacterTest, "MurderInc.Audio.VoiceCharacters", Flags)
bool FMIAudioVoiceCharacterTest::RunTest(const FString& Parameters)
{
	FMIVoiceData D;
	if (!LoadTestVoice(*this, D))
	{
		return false;
	}
	FMIVoiceRules R;
	Make(R, D, TEXT("other"));
	const TArray<FMIVoicePlay> P = Fire(R, TEXT("kill"), 0.0);
	TestTrue(TEXT("another crew member speaks his own line"), P.Num() == 1 && P[0].Line == TEXT("mine") && P[0].Speaker == TEXT("OTHER") && P[0].Character == TEXT("other"));
	TestEqual(TEXT("...and has no line for a story beat"), Fire(R, TEXT("story"), 10.0).Num(), 0);
	R.SetCharacter(TEXT("quiet"));
	int32 N = 0;
	for (const TCHAR* T : {TEXT("kill"), TEXT("big"), TEXT("story"), TEXT("progress")})
	{
		N += Fire(R, T, 30.0 + N * 10.0).Num();
	}
	TestEqual(TEXT("a member with an empty set is silent (no fallback to another voice)"), N, 0);
	R.SetCharacter(TEXT("hero"));
	TestEqual(TEXT("back to the hero"), Fire(R, TEXT("kill"), 100.0).Num(), 1);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioVoiceTriggerTest, "MurderInc.Audio.VoiceTriggers", Flags)
bool FMIAudioVoiceTriggerTest::RunTest(const FString& Parameters)
{
	FMIVoiceData D;
	FString Error;
	if (!FMIVoiceData::Load(D, Error))
	{
		AddError(Error);
		return false;
	}
	FMIVoiceTriggers T;
	T.Init(D.Settings);
	TArray<FString> Got;
	T.OnTrigger = [&Got](FName N, int32 V) { Got.Add(V ? FString::Printf(TEXT("%s=%d"), *N.ToString(), V) : N.ToString()); };
	int32 Silences = 0;
	T.OnSilence = [&Silences]() { ++Silences; };

	T.OnFlow(Flow(TEXT("game:state"), TEXT("title")), 0.0);
	T.OnFlow(Flow(TEXT("game:state"), TEXT("intro")), 1.0);
	T.OnFlow(Flow(TEXT("game:state"), TEXT("playing")), 3.0);
	T.OnEnemy(Kill(0, TEXT("body"), TEXT("chopper")), 10.0);
	T.OnEnemy(Kill(1, TEXT("head"), TEXT("chopper")), 10.8);
	T.OnEnemy(Kill(2, TEXT("body"), TEXT("melee")), 30.0);
	T.OnEnemy(Kill(3, TEXT("body"), TEXT("blast")), 40.0);
	T.OnEnemy(Kill(12, TEXT("body"), TEXT("nine"), true), 45.0);
	FMIEnemyEvent NotMine = Kill(4, TEXT("head"), TEXT("smg"));
	NotMine.bByPlayer = false;
	T.OnEnemy(NotMine, 46.0);
	T.OnFlow(Flow(TEXT("objective:done"), TEXT("reel_1"), 1, 3), 50.0);
	T.OnFlow(Flow(TEXT("hud:objective"), TEXT("Find the second reel")), 50.1);
	FMIPlayerHitEvent Hit;
	Hit.Amount = 30;
	Hit.Health = 20;
	T.OnPlayerHit(Hit, 55.0);
	T.Tick(58.0);
	T.Tick(61.5);
	T.OnFlow(Flow(TEXT("objective:all")), 70.0);
	T.OnFlow(Flow(TEXT("extraction:reached")), 80.0);
	T.OnFlow(Flow(TEXT("menus:card"), TEXT("complete")), 84.0);

	const TArray<FString> Want = {TEXT("run.start"), TEXT("kill.ordinary"), TEXT("kill.headshot"), TEXT("kill.multi=2"), TEXT("kill.melee"), TEXT("kill.explosive"),
		TEXT("kill.buzzard"), TEXT("reel.collected=1"), TEXT("objective.update"), TEXT("health.lowSurvived"), TEXT("extraction.called"), TEXT("run.win"), TEXT("results.complete")};
	TestEqual(TEXT("triggers in order"), FString::Join(Got, TEXT(" ")), FString::Join(Want, TEXT(" ")));
	TestEqual(TEXT("the title silences"), Silences, 1);

	// Hold the Block: the last kill of a wave, the wave, streaks, the death card is the results card.
	Got.Reset();
	T.OnFlow(Flow(TEXT("game:state"), TEXT("title")), 100.0);
	T.OnFlow(Flow(TEXT("game:state"), TEXT("playing")), 101.0);
	T.OnFlow(Flow(TEXT("holdout:wave"), TEXT(""), 1, 6), 102.0);
	for (int32 I = 0; I < 6; ++I)
	{
		T.OnEnemy(Kill(I, TEXT("body"), TEXT("chopper")), 110.0 + I * 3.0);
	}
	T.OnFlow(Flow(TEXT("objective:done"), TEXT("wave"), 1, 1), 125.02);
	FMIPlayerHitEvent Small;
	Small.Amount = 5;
	Small.Health = 80;
	T.OnPlayerHit(Small, 126.0);
	T.OnEnemy(Kill(7, TEXT("body"), TEXT("chopper")), 127.0);
	T.OnPlayerDead(130.0);
	T.OnFlow(Flow(TEXT("game:state"), TEXT("dead")), 130.0);
	T.OnFlow(Flow(TEXT("menus:card"), TEXT("dead")), 133.0);
	TestTrue(TEXT("the streak reaches its first threshold (6)"), Got.Contains(TEXT("kill.streak=6")));
	TestTrue(TEXT("the kill that cleared the wave"), Got.Contains(TEXT("kill.lastOfWave")));
	TestTrue(TEXT("the wave"), Got.Contains(TEXT("wave.cleared=1")));
	TestTrue(TEXT("a real hit breaks the streak"), T.GetStreak() == 0);
	TestTrue(TEXT("the Hold the Block card"), Got.Contains(TEXT("results.holdout")));
	TestFalse(TEXT("no kill bark after death"), Got.Last() == TEXT("kill.ordinary"));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioVoiceRateTest, "MurderInc.Audio.VoiceRate", Flags)
bool FMIAudioVoiceRateTest::RunTest(const FString& Parameters)
{
	// A typical Story run on Boss (spec 04 2.10: 33 to 41 enemies in "about five minutes", about 7 kills a minute):
	// 36 kills over 300 s in fights of a few kills, a quarter of them headshots, 5 Buzzards, one blast and one melee
	// kill, three reels, two close calls, the truck and the debrief. 20 seeds; the real voice.json.
	FMIVoiceData D;
	FString Error;
	if (!FMIVoiceData::Load(D, Error))
	{
		AddError(Error);
		return false;
	}
	double Total = 0.0;
	int32 Kills = 0, KillLines = 0;
	TMap<FName, int32> PerLine;
	const int32 Seeds = 20;
	for (int32 Seed = 0; Seed < Seeds; ++Seed)
	{
		FMIVoiceRules R;
		R.TakeSecs = [](FName, const FString&) { return 1.6; };
		R.Init(&D, TEXT("rule"), D.Settings.Defaults, Seed);
		FMIVoiceTriggers T;
		T.Init(D.Settings);
		double Now = 0.0;
		T.OnTrigger = [&R, &Now](FName N, int32 V) { R.Trigger(N, Now, V); };
		FRandomStream Rng(1000 + Seed);
		TArray<TPair<double, TFunction<void()>>> Script;
		auto At = [&Script](double Time, TFunction<void()> F) { Script.Add({Time, MoveTemp(F)}); };
		At(0.0, [&T, &Now]() { T.OnFlow(Flow(TEXT("game:state"), TEXT("intro")), Now); });
		// Twelve fights of three kills: within each fight kills 1 to 4 s apart.
		int32 Id = 0;
		for (int32 F = 0; F < 12; ++F)
		{
			double Time = 12.0 + F * 24.0 + Rng.FRandRange(0, 6);
			for (int32 K = 0; K < 3; ++K)
			{
				const int32 Kind = Rng.RandRange(0, 99);
				const bool bBuzzard = Id % 7 == 3;
				const FName Part = Kind < 25 ? FName(TEXT("head")) : FName(TEXT("body"));
				const FName Weapon = Id == 10 ? FName(TEXT("melee")) : Id == 20 ? FName(TEXT("blast")) : FName(TEXT("chopper"));
				const FMIEnemyEvent E = Kill(Id++, Part, Weapon, bBuzzard);
				At(Time, [&T, &Now, E]() { T.OnEnemy(E, Now); });
				Time += Rng.FRandRange(1.0, 4.0);
			}
		}
		for (int32 Reel = 1; Reel <= 3; ++Reel)
		{
			At(70.0 * Reel, [&T, &Now, Reel]() { T.OnFlow(Flow(TEXT("objective:done"), *FString::Printf(TEXT("reel_%d"), Reel), Reel, 3), Now); });
		}
		At(212.0, [&T, &Now]() { T.OnFlow(Flow(TEXT("objective:all")), Now); });
		for (const double Close : {95.0, 180.0})
		{
			At(Close, [&T, &Now]() { FMIPlayerHitEvent H; H.Amount = 25; H.Health = 22; T.OnPlayerHit(H, Now); });
		}
		At(295.0, [&T, &Now]() { T.OnFlow(Flow(TEXT("extraction:reached")), Now); });
		At(299.0, [&T, &Now]() { T.OnFlow(Flow(TEXT("menus:card"), TEXT("complete")), Now); });
		Script.StableSort([](const auto& A, const auto& B) { return A.Key < B.Key; });

		int32 Next = 0;
		TArray<FMIVoicePlay> Plays;
		for (Now = 0.0; Now <= 305.0; Now += 1.0 / 30.0)
		{
			while (Next < Script.Num() && Script[Next].Key <= Now)
			{
				Script[Next++].Value();
			}
			T.Tick(Now);
			R.Tick(Now, Plays);
		}
		Kills += Id;
		for (const FMIVoicePlay& P : Plays)
		{
			PerLine.FindOrAdd(P.Line)++;
			KillLines += P.Trigger.ToString().StartsWith(TEXT("kill.")) ? 1 : 0;
		}
		Total += Plays.Num();
	}
	const double PerMinute = Total / Seeds / 5.0;
	FString Lines;
	for (const auto& Pair : PerLine)
	{
		Lines += FString::Printf(TEXT(" %s %.2f/run"), *Pair.Key.ToString(), double(Pair.Value) / Seeds);
	}
	AddInfo(FString::Printf(TEXT("typical Story run: %.2f lines a minute (%.1f a run, %.1f on kills of %d kills),%s"), PerMinute, Total / Seeds, double(KillLines) / Seeds, Kills / Seeds, *Lines));
	TestTrue(TEXT("rare enough to stay a reward: 1 to 3.5 lines a minute"), PerMinute >= 1.0 && PerMinute <= 3.5);
	TestTrue(TEXT("most kills stay silent (under a third speak)"), double(KillLines) / Kills < 0.34);
	TestTrue(TEXT("the win is always called"), PerLine.FindRef(TEXT("name")) >= Seeds && PerLine.FindRef(TEXT("rule_chant")) >= Seeds);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioEventTableTest, "MurderInc.Audio.EventTable", Flags)
bool FMIAudioEventTableTest::RunTest(const FString& Parameters)
{
	FMIAudioData D;
	FString Error;
	if (!FMIAudioData::Load(D, Error))
	{
		AddError(TEXT("audio data: ") + Error);
		return false;
	}
	TSet<FName> Keys(FMIAudioDirector::BusEventKeys());
	// Flow lines the gameplay code emits now (the source ships with the project on the box): a new one must get an
	// entry here, even if it is "silent".
	const FString Src = FPaths::Combine(FPaths::GameSourceDir(), TEXT("MurderInc"));
	TArray<FString> Files;
	IFileManager::Get().FindFilesRecursive(Files, *Src, TEXT("*.cpp"), true, false);
	int32 FromSource = 0;
	for (const FString& F : Files)
	{
		if (F.Contains(TEXT("/Tests/")) || F.Contains(TEXT("/Audio/")))
		{
			continue;
		}
		FString Text;
		FFileHelper::LoadFileToString(Text, *F);
		int32 At = 0;
		const FString Needle = TEXT("Note(TEXT(\"");
		while ((At = Text.Find(Needle, ESearchCase::CaseSensitive, ESearchDir::FromStart, At)) != INDEX_NONE)
		{
			At += Needle.Len();
			const int32 End = Text.Find(TEXT("\""), ESearchCase::CaseSensitive, ESearchDir::FromStart, At);
			if (End > At)
			{
				Keys.Add(FName(Text.Mid(At, End - At)));
				++FromSource;
			}
		}
	}
	int32 Silent = 0, Played = 0, Ruled = 0;
	for (const FName K : Keys)
	{
		const TSharedPtr<FJsonObject> E = D.Event(K);
		if (!E.IsValid())
		{
			AddError(FString::Printf(TEXT("event %s has no entry in audio.json events"), *K.ToString()));
			continue;
		}
		const bool bSilent = E->HasField(TEXT("silent")), bPlay = E->HasField(TEXT("play")), bRule = E->HasField(TEXT("rule"));
		if (!bSilent && !bPlay && !bRule)
		{
			AddError(FString::Printf(TEXT("event %s: neither play, rule nor silent"), *K.ToString()));
		}
		Silent += bSilent;
		Played += bPlay;
		Ruled += bRule;
		// Every literal sound an entry plays exists.
		const TArray<TSharedPtr<FJsonValue>>* List = nullptr;
		if (E->TryGetArrayField(TEXT("play"), List))
		{
			for (const TSharedPtr<FJsonValue>& V : *List)
			{
				const FString S = V->AsObject()->GetStringField(TEXT("sound"));
				if (!S.Contains(TEXT("{")) && !D.Find(FName(S)))
				{
					AddError(FString::Printf(TEXT("event %s plays %s, which is not a sound"), *K.ToString(), *S));
				}
			}
		}
	}
	// The names the code rules ask for exist.
	for (const TCHAR* S : {TEXT("chopper_shot"), TEXT("nine_shot"), TEXT("chopper_tail_out"), TEXT("chopper_tail_in"), TEXT("nine_tail_out"), TEXT("nine_tail_in"),
		TEXT("chopper_shot_silenced"), TEXT("nine_shot_silenced"), TEXT("ricochet"), TEXT("whizz"), TEXT("hurt"), TEXT("ear_ring"), TEXT("land"), TEXT("grunt_hit"),
		TEXT("rotor"), TEXT("heartbeat"), TEXT("hiss"), TEXT("reel_grab"), TEXT("train_rumble"), TEXT("train_clack"), TEXT("train_squeal"), TEXT("explosion_far"),
		TEXT("brass_concrete"), TEXT("rifle_magout"), TEXT("pistol_slide")})
	{
		TestNotNull(FString::Printf(TEXT("sound %s"), S), D.Find(FName(S)));
	}
	// Every surface maps to sounds that exist, steps both ways.
	const TSharedPtr<FJsonObject> Surfaces = D.Table(TEXT("surfaces"));
	for (const auto& Pair : Surfaces->Values)
	{
		const TSharedPtr<FJsonObject> S = Pair.Value->Type == EJson::Object ? Pair.Value->AsObject() : nullptr;
		if (!S.IsValid())
		{
			continue;
		}
		const FString Steps = S->GetStringField(TEXT("steps"));
		for (const FString& N : {S->GetStringField(TEXT("impact")), S->GetStringField(TEXT("brass")), TEXT("step_") + Steps, TEXT("step_") + Steps + TEXT("_run")})
		{
			if (!D.Find(FName(N)))
			{
				AddError(FString::Printf(TEXT("surface %s: %s is not a sound"), *FString(*Pair.Key), *N));
			}
		}
	}
	// Every web file exists (node tools/ue-export/audio.mjs); replacement files may be missing (the web sound plays).
	int32 WebMissing = 0, GenMissing = 0, GenFiles = 0;
	for (const auto& Pair : D.Sounds)
	{
		for (const FString& F : Pair.Value.Files)
		{
			WebMissing += FPaths::FileExists(FPaths::Combine(FMIAudioData::AudioDir(), F)) ? 0 : 1;
		}
	}
	for (const auto& Pair : D.Replace)
	{
		for (const FMIReplaceLayer& L : Pair.Value.Layers)
		{
			for (const FString& F : L.Files)
			{
				++GenFiles;
				GenMissing += FPaths::FileExists(FPaths::Combine(FMIAudioData::AudioDir(), F)) ? 0 : 1;
			}
		}
	}
	if (WebMissing)
	{
		AddError(FString::Printf(TEXT("%d web sound files missing (node tools/ue-export/audio.mjs)"), WebMissing));
	}
	AddInfo(FString::Printf(TEXT("%d bus event keys (%d flow lines found in the source): %d play, %d rules, %d silent; %d sounds; %d of %d replacement files present"),
		Keys.Num(), FromSource, Played, Ruled, Silent, D.Sounds.Num(), GenFiles - GenMissing, GenFiles));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioDirectorTest, "MurderInc.Audio.Director", Flags)
bool FMIAudioDirectorTest::RunTest(const FString& Parameters)
{
	FMIAudioData D;
	FMIVoiceData V;
	FString Error;
	if (!FMIAudioData::Load(D, Error) || !FMIVoiceData::Load(V, Error))
	{
		AddError(Error);
		return false;
	}
	FMIAudioDirector A;
	A.Exists = [](const FString&) { return true; };
	A.Init(&D, &V, 3);
	FMIGameEvents Bus;
	A.Bind(Bus);
	A.SetListener(FVector(1000, 1200, 170), FVector::ForwardVector);
	TArray<FMIAudioCmd> Cmds;
	auto Step = [&A, &Cmds](double Secs)
	{
		for (double T = 0; T < Secs - 1e-9; T += 0.01)
		{
			A.Tick(0.01);
			A.TakeCommands(Cmds);
		}
	};
	Bus.Flow.Broadcast(Flow(TEXT("game:state"), TEXT("playing")));
	Step(0.5);
	Cmds.Reset();

	// A CHOPPER burst: each round a shot, its layers and a street tail; the earlier tails are pushed down.
	FMIShotFiredEvent Shot;
	Shot.Weapon = TEXT("chopper");
	for (int32 I = 0; I < 4; ++I)
	{
		Bus.WeaponFire.Broadcast(Shot);
		Step(0.083);
	}
	int32 Shots = 0, Tails = 0, PushDowns = 0, Layers = 0;
	for (const FMIAudioCmd& C : Cmds)
	{
		Shots += C.Type == EMIAudioCmd::Start && C.Sound == TEXT("chopper_shot") && C.File.StartsWith(TEXT("Web/")) ? 1 : 0;
		Layers += C.Type == EMIAudioCmd::Start && C.Sound == TEXT("chopper_shot") && C.File.StartsWith(TEXT("Gen/")) ? 1 : 0;
		Tails += C.Type == EMIAudioCmd::Start && C.Sound == TEXT("chopper_tail_out") && C.File.StartsWith(TEXT("Web/")) ? 1 : 0;
		PushDowns += C.Type == EMIAudioCmd::Set ? 1 : 0;
	}
	TestEqual(TEXT("four dry shots"), Shots, 4);
	TestEqual(TEXT("two replacement layers per shot (close, mechanical)"), Layers, 8);
	TestEqual(TEXT("four street tails (outside, interior 0)"), Tails, 4);
	TestTrue(TEXT("earlier tails pushed down"), PushDowns >= 3);
	const double GunDuck = A.GetMix().Gain[TEXT("ambience")];
	Step(1.0);
	TestTrue(TEXT("gunfire ducked the ambience, which recovers"), GunDuck < A.GetMix().Gain[TEXT("ambience")]);

	// A big blast 8 m away muffles the effects; pause silences the world and thins the music.
	FMIExplosionEvent X;
	X.Position = FVector(1800, 1200, 100);
	X.bBig = true;
	Bus.Explosion.Broadcast(X);
	Step(0.05);
	TestTrue(TEXT("the blast muffles (cut-off under 3 kHz)"), A.GetMix().MuffleCutoff < 3000.0);
	Step(3.0);
	TestTrue(TEXT("and it reopens"), A.GetMix().MuffleCutoff > 12000.0);
	Bus.Flow.Broadcast(Flow(TEXT("game:state"), TEXT("paused")));
	Step(0.1);
	const int32 Before = A.Refused();
	FMIImpactEvent Imp;
	Imp.Point = FVector(1500, 1300, 100);
	Imp.Surface = TEXT("concrete");
	Bus.Impact.Broadcast(Imp);
	TestEqual(TEXT("paused: a world sound is refused"), A.Refused(), Before + 1);
	TestTrue(TEXT("paused: the music low-pass closes"), A.GetMix().MusicCutoff < 2000.0);
	Bus.Flow.Broadcast(Flow(TEXT("game:state"), TEXT("playing")));
	Step(0.1);

	// Death: muffle to 1, settling at 0.85.
	Bus.PlayerDead.Broadcast(TOptional<FVector>());
	Step(2.0);
	TestTrue(TEXT("dead: muffled near 1 kHz"), A.GetMix().MuffleCutoff < 1200.0);

	// The voice ducks the rest while it speaks.
	Bus.Flow.Broadcast(Flow(TEXT("game:state"), TEXT("title")));
	Bus.Flow.Broadcast(Flow(TEXT("game:state"), TEXT("intro")));
	Bus.Flow.Broadcast(Flow(TEXT("extraction:reached")));
	Step(0.6);
	TestTrue(TEXT("a line speaks with its subtitle"), !A.GetSubtitle().Text.IsEmpty());
	TestTrue(TEXT("the music ducks under the voice"), A.GetMix().VoiceDuck > 0.5);
	A.Unbind();
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioMixdownTest, "MurderInc.Audio.Mixdown", Flags)
bool FMIAudioMixdownTest::RunTest(const FString& Parameters)
{
	// Replays a recorded bus stream (Content/Data/audio_fight.json, or Saved/Audio/recorded.json when present after a
	// MIAudio.Record session) through the director and renders the result with the offline mixer.
	FMIAudioData D;
	FMIVoiceData V;
	FString Error;
	if (!FMIAudioData::Load(D, Error) || !FMIVoiceData::Load(V, Error))
	{
		AddError(Error);
		return false;
	}
	FMIAudioEventLog Log;
	const FString Recorded = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Audio"), TEXT("recorded.json"));
	const FString Path = FPaths::FileExists(Recorded) ? Recorded : FPaths::Combine(UMIDataSubsystem::GetDataDir(), TEXT("audio_fight.json"));
	if (!Log.Load(Path, Error))
	{
		AddError(Error);
		return false;
	}
	FMIOfflineMix Mix;
	FMIAudioDirector A;
	A.Exists = [&Mix](const FString& F) { return FPaths::FileExists(FPaths::Combine(Mix.Root.IsEmpty() ? FMIAudioData::AudioDir() : Mix.Root, F)); };
	A.FileSecs = [&Mix](const FString& F) { return Mix.FileSecs(F); };
	A.Init(&D, &V, 11);
	FMIGameEvents Bus;
	A.Bind(Bus);
	const double Secs = Log.Duration() + 4.0;
	Mix.Begin(&D, Secs);
	int32 Lines = 0;
	TArray<FString> Said;
	TArray<FMIAudioCmd> Cmds;
	const double Dt = 0.01;
	for (double T = 0.0; T < Secs; T += Dt)
	{
		Log.ReplayRange(T - 1e-9 - (T == 0.0 ? 1.0 : 0.0), T + Dt - 1e-9, Bus, &A);
		A.Tick(Dt);
		Cmds.Reset();
		A.TakeCommands(Cmds);
		for (const FMIAudioCmd& C : Cmds)
		{
			if (C.Type == EMIAudioCmd::Start && C.Category == TEXT("voice") && C.File.StartsWith(TEXT("Voice/")))
			{
				++Lines;
				Said.Add(FString::Printf(TEXT("%.1fs %s"), A.Now(), *FPaths::GetBaseFilename(C.File)));
			}
		}
		Mix.Apply(Cmds);
		Mix.RenderTo(A.Now(), A.GetMix(), A.GetListener(), A.GetListenerForward());
	}
	A.Unbind();
	const FString Out = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Audio"), TEXT("fight_mixdown.wav"));
	IFileManager::Get().MakeDirectory(*FPaths::GetPath(Out), true);
	TestTrue(TEXT("the mix-down is written"), Mix.Save(Out));
	const double Peak = Mix.PeakDb();
	AddInfo(FString::Printf(TEXT("%s: %.1f s, %d voices, peak %.1f dBFS, %d voice lines: %s; %d files missing"), *Out, Secs, Mix.VoicesStarted(), Peak, Lines,
		*FString::Join(Said, TEXT(", ")), Mix.Missing.Num()));
	for (const FString& M : Mix.Missing)
	{
		AddWarning(TEXT("missing in the mix: ") + M);
	}
	TestTrue(TEXT("hundreds of voices"), Mix.VoicesStarted() > 200);
	TestTrue(TEXT("never clips (soft clip keeps it under 0 dBFS)"), Peak < 0.0);
	TestTrue(TEXT("not silent (peak above -30 dBFS)"), Peak > -30.0);
	TestTrue(TEXT("the voice speaks a few times"), Lines >= 3);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioAssetsTest, "MurderInc.Audio.Assets", Flags)
bool FMIAudioAssetsTest::RunTest(const FString& Parameters)
{
	// After tools/box/audio-import.sh: every WAV under Content/Audio is a Sound Wave of the same length, loops loop.
	TArray<FString> Files;
	IFileManager::Get().FindFilesRecursive(Files, *FMIAudioData::AudioDir(), TEXT("*.wav"), true, false);
	int32 Checked = 0, Missing = 0, Wrong = 0, Loops = 0;
	for (const FString& Path : Files)
	{
		FString Rel = Path;
		FPaths::MakePathRelativeTo(Rel, *(FMIAudioData::AudioDir() + TEXT("/")));
		if (FPaths::GetCleanFilename(Rel).StartsWith(TEXT("IR_")))
		{
			continue;
		}
		const USoundWave* W = LoadObject<USoundWave>(nullptr, *FMIAudioData::AssetPath(Rel), nullptr, LOAD_NoWarn | LOAD_Quiet);
		if (!W)
		{
			++Missing;
			continue;
		}
		FMIWav Wav;
		if (FMIWav::Load(Path, Wav) && FMath::Abs(W->Duration - Wav.Secs()) > 0.02)
		{
			++Wrong;
			AddError(FString::Printf(TEXT("%s: asset %.3f s, file %.3f s"), *Rel, W->Duration, Wav.Secs()));
		}
		Loops += W->bLooping ? 1 : 0;
		++Checked;
	}
	if (Checked == 0)
	{
		AddWarning(TEXT("no audio assets imported yet: run tools/box/audio-import.sh"));
		return true;
	}
	AddInfo(FString::Printf(TEXT("%d of %d files imported as Sound Waves (%d missing, %d with a wrong length, %d looping)"), Checked, Checked + Missing, Missing, Wrong, Loops));
	TestEqual(TEXT("every file has its asset"), Missing, 0);
	TestTrue(TEXT("the loops loop (stems, beds, rotor, train ...)"), Loops >= 15);
	return true;
}

#endif
