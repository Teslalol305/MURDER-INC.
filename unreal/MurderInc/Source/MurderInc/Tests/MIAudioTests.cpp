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
		"triggers": { "kill": "", "big": "", "story": "", "progress": "", "second": "", "kill.streak": "", "loud": "", "soft": "", "odd": "" },
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
					"triggers": {}, "takes": [ { "file": "crowd_01.wav" } ] },
				"moody": { "text": "Moody!", "priority": 15, "cooldown": 0,
					"triggers": { "loud": { "chance": 1.0, "intensity": ["shout"] }, "soft": { "chance": 1.0, "intensity": ["breath", "spoken"] },
						"odd": { "chance": 1.0, "intensity": ["whisper"] } },
					"takes": [ { "file": "moody_s1.wav", "intensity": "shout" }, { "file": "moody_s2.wav", "intensity": "shout" },
						{ "file": "moody_sp.wav", "intensity": "spoken" }, { "file": "moody_b.wav", "intensity": "breath" } ] }
			} },
			"other": { "speaker": "OTHER", "lines": {
				"mine": { "text": "Mine!", "priority": 20, "cooldown": 1, "triggers": { "kill": 1.0 }, "takes": [ { "file": "mine_01.wav" } ] }
			} },
			"quiet": { "speaker": "QUIET", "lines": {} }
		}
	})JSON");

	/**
	 * The longest silence inside a take (10 ms frames 40 dB under its loudest frame, between its first and its last
	 * sound), and the silence before the first and after the last sound, in seconds.
	 */
	double InnerGap(const FMIWav& W, double& OutHead, double& OutTail)
	{
		const int32 Hop = FMath::Max(1, W.Rate / 100);
		const int32 Frames = W.Frames();
		TArray<double> Db;
		double Top = -200.0;
		for (int32 F = 0; F + Hop <= Frames; F += Hop)
		{
			double E = 0.0;
			for (int32 I = F; I < F + Hop; ++I)
			{
				const double S = W.Samples[I * W.Channels];
				E += S * S;
			}
			Db.Add(10.0 * FMath::LogX(10.0, E / Hop + 1e-20));
			Top = FMath::Max(Top, Db.Last());
		}
		int32 First = INDEX_NONE, Last = INDEX_NONE, Run = 0, Best = 0;
		for (int32 I = 0; I < Db.Num(); ++I)
		{
			if (Db[I] > Top - 40.0)
			{
				First = First == INDEX_NONE ? I : First;
				Last = I;
			}
		}
		for (int32 I = First; I != INDEX_NONE && I <= Last; ++I)
		{
			Run = Db[I] > Top - 40.0 ? 0 : Run + 1;
			Best = FMath::Max(Best, Run);
		}
		OutHead = First == INDEX_NONE ? 0.0 : First * 0.01;
		OutTail = Last == INDEX_NONE ? 0.0 : (Db.Num() - 1 - Last) * 0.01;
		return Best * 0.01;
	}

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
	}
	// Every take of every line (clean takes too): the format, and cut tight. A long tail or a hole inside a take keeps
	// the voice "speaking": it blocks other lines and holds the duck on the mix.
	FString Lengths;
	for (const FMIVoiceLine& L : Rule->Lines)
	{
		const double MaxSecs = L.Id == TEXT("rule_chant") ? 2.2 : 2.5;
		for (const TArray<FMIVoiceTake>* Set : {&L.Takes, &L.CleanTakes})
		{
			for (const FMIVoiceTake& T : *Set)
			{
				const FString Path = FPaths::Combine(FMIAudioData::AudioDir(), TEXT("Voice/rule"), T.File);
				FMIWav Wav;
				if (!FMIWav::Load(Path, Wav))
				{
					++Missing;
					AddError(TEXT("take missing: ") + Path);
					continue;
				}
				if (Wav.Rate != 48000 || Wav.Channels != 1)
				{
					AddError(FString::Printf(TEXT("%s: %d Hz %d channels, want 48000 mono"), *T.File, Wav.Rate, Wav.Channels));
				}
				double Head = 0, Tail = 0;
				const double Gap = InnerGap(Wav, Head, Tail);
				Lengths += FString::Printf(TEXT(" %s %.2f/%.2f"), *FPaths::GetBaseFilename(T.File), Wav.Secs(), Gap);
				if (Wav.Secs() > MaxSecs)
				{
					AddError(FString::Printf(TEXT("%s is %.2f s long: over %.1f s"), *T.File, Wav.Secs(), MaxSecs));
				}
				if (Gap > 0.5)
				{
					AddError(FString::Printf(TEXT("%s has %.2f s of silence inside it (at most 0.5 s)"), *T.File, Gap));
				}
				if (Tail > 0.45)
				{
					AddError(FString::Printf(TEXT("%s ends on %.2f s of silence (at most 0.45 s)"), *T.File, Tail));
				}
			}
		}
		// Bleep mode plays the profane takes with a tone over each take's range: an empty range would play the word.
		if (L.bProfane && L.CleanMode == TEXT("bleep"))
		{
			for (const FMIVoiceTake& T : L.Takes)
			{
				if (!(T.BleepEnd > T.BleepStart))
				{
					AddError(FString::Printf(TEXT("%s: clean mode is bleep, but its bleep range [%.2f, %.2f] is empty"), *T.File, T.BleepStart, T.BleepEnd));
				}
			}
		}
	}
	AddInfo(TEXT("takes (seconds / longest inner gap):") + Lengths);
	const FMIVoiceLine* Name = Rule->Find(TEXT("name"));
	TestTrue(TEXT("the profane line is flagged and has clean takes"), Name && Name->bProfane && Name->CleanTakes.Num() >= 1);
	TestTrue(TEXT("the profane line is answered by the crowd"), Name && Name->AnswerLine == TEXT("rule_chant"));
	// Every crew member of crew.json has a voice set (empty is allowed: silent until recorded).
	for (const TCHAR* Crew : {TEXT("rule"), TEXT("deuce"), TEXT("smoke"), TEXT("keys")})
	{
		TestTrue(FString::Printf(TEXT("voice set for %s"), Crew), D.Characters.Contains(FName(Crew)));
	}
	AddInfo(FString::Printf(TEXT("%d lines for rule, %d known triggers, %d takes missing"), Rule->Lines.Num(), D.KnownTriggers.Num(), Missing));
	int32 Takes = 0, Placeholders = 0;
	D.CountTakes(Takes, Placeholders);
	if (Placeholders > 0)
	{
		AddWarning(FString::Printf(TEXT("voice: %d of %d takes are placeholders (a stock synthetic voice; the real recordings replace them file for file, AUDIO.md section 5)"), Placeholders, Takes));
	}
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

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioVoiceIntensityTest, "MurderInc.Audio.VoiceIntensity", Flags)
bool FMIAudioVoiceIntensityTest::RunTest(const FString& Parameters)
{
	FMIVoiceData D;
	if (!LoadTestVoice(*this, D))
	{
		return false;
	}
	// 'moody' has two shouted takes, one spoken, one breathed. 'loud' wants a shout, 'soft' a breath or the spoken one,
	// 'odd' an intensity no take has (any take then). Triggers 10 s apart clear every cooldown.
	auto Run = [&D](FName Trigger, TMap<FString, int32>& Files, int32& Repeats)
	{
		FMIVoiceRules R;
		Make(R, D);
		FString Last;
		for (int32 I = 0; I < 120; ++I)
		{
			for (const FMIVoicePlay& P : Fire(R, Trigger, I * 10.0))
			{
				Files.FindOrAdd(P.File)++;
				Repeats += P.File == Last ? 1 : 0;
				Last = P.File;
			}
		}
	};
	TMap<FString, int32> Loud, Soft, Odd;
	int32 LoudRepeats = 0, SoftRepeats = 0, OddRepeats = 0;
	Run(TEXT("loud"), Loud, LoudRepeats);
	Run(TEXT("soft"), Soft, SoftRepeats);
	Run(TEXT("odd"), Odd, OddRepeats);
	TestTrue(TEXT("loud: only the shouted takes, both of them"), Loud.Num() == 2 && Loud.Contains(TEXT("moody_s1.wav")) && Loud.Contains(TEXT("moody_s2.wav")));
	TestTrue(TEXT("soft: only the spoken and the breathed take"), Soft.Num() == 2 && Soft.Contains(TEXT("moody_sp.wav")) && Soft.Contains(TEXT("moody_b.wav")));
	TestEqual(TEXT("an intensity no take has falls back to every take"), Odd.Num(), 4);
	TestEqual(TEXT("no take twice in a row, within the preferred ones too"), LoudRepeats + SoftRepeats + OddRepeats, 0);
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
	// A round already in the air when the player died: its kill is no bark.
	const int32 Before = Got.Num();
	T.OnEnemy(Kill(8, TEXT("head"), TEXT("chopper")), 134.0);
	bool bKillAfterDeath = false;
	for (int32 I = Before; I < Got.Num(); ++I)
	{
		bKillAfterDeath |= Got[I].StartsWith(TEXT("kill."));
	}
	TestFalse(TEXT("no kill trigger after death"), bKillAfterDeath);

	// A restart from the pause menu or the debrief (player:reset, then the new intro) silences what the old run had
	// queued; the first run from the title does not need to.
	T.OnFlow(Flow(TEXT("game:state"), TEXT("playing")), 140.0);
	T.OnFlow(Flow(TEXT("game:state"), TEXT("paused")), 150.0);
	const int32 S0 = Silences;
	T.OnFlow(Flow(TEXT("player:reset")), 151.0);
	TestEqual(TEXT("player:reset silences"), Silences, S0 + 1);
	T.OnFlow(Flow(TEXT("game:state"), TEXT("intro")), 151.0);
	TestEqual(TEXT("the intro of a restarted run silences again (it does not come from the title)"), Silences, S0 + 2);
	T.OnFlow(Flow(TEXT("game:state"), TEXT("title")), 160.0);
	const int32 S1 = Silences;
	T.OnFlow(Flow(TEXT("game:state"), TEXT("intro")), 161.0);
	TestEqual(TEXT("the first intro from the title does not"), Silences, S1);

	// Hold the Block progress: every fifth wave is a milestone; a card above the session's best is a new best.
	Got.Reset();
	T.OnFlow(Flow(TEXT("game:state"), TEXT("title")), 200.0);
	T.OnFlow(Flow(TEXT("game:state"), TEXT("playing")), 201.0);
	for (int32 W = 1; W <= 10; ++W)
	{
		T.OnFlow(Flow(TEXT("holdout:wave"), TEXT(""), W, 5 + 2 * W), 201.0 + W * 20.0);
		T.OnFlow(Flow(TEXT("objective:done"), TEXT("wave"), W, W), 215.0 + W * 20.0);
	}
	TestTrue(TEXT("wave 5 is a milestone"), Got.Contains(TEXT("wave.milestone=5")));
	TestTrue(TEXT("wave 10 is a milestone"), Got.Contains(TEXT("wave.milestone=10")));
	TestFalse(TEXT("wave 4 is not"), Got.Contains(TEXT("wave.milestone=4")));
	T.OnFlow(Flow(TEXT("menus:card"), TEXT("dead"), 3, 9000), 430.0);
	TestFalse(TEXT("the session's first card is no new best"), Got.ContainsByPredicate([](const FString& G) { return G.StartsWith(TEXT("score.newBest")); }));
	T.OnFlow(Flow(TEXT("game:state"), TEXT("title")), 440.0);
	T.OnFlow(Flow(TEXT("game:state"), TEXT("playing")), 441.0);
	T.OnFlow(Flow(TEXT("holdout:wave"), TEXT(""), 1, 7), 445.0);
	T.OnFlow(Flow(TEXT("menus:card"), TEXT("dead"), 3, 12000), 500.0);
	TestTrue(TEXT("a better card is a new best"), Got.Contains(TEXT("score.newBest=12000")));
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
	// Every delegate of the bus (Core/MIEvents.h, read as text so a new one cannot be missed) is one the director
	// listens to: a new event (the loadout's silencer, an attachment) fails here until it has a key and an entry.
	FString Header;
	const FString HeaderPath = FPaths::Combine(Src, TEXT("Core"), TEXT("MIEvents.h"));
	if (!FFileHelper::LoadFileToString(Header, *HeaderPath))
	{
		AddError(TEXT("cannot read ") + HeaderPath);
	}
	TSet<FName> Mapped;
	for (const TPair<FName, FString>& P : FMIAudioDirector::BusDelegates())
	{
		Mapped.Add(P.Key);
	}
	int32 Delegates = 0, At = 0;
	const FString Needle = TEXT("TMulticastDelegate<");
	while ((At = Header.Find(Needle, ESearchCase::CaseSensitive, ESearchDir::FromStart, At)) != INDEX_NONE)
	{
		// TMulticastDelegate<void(...)> Name;  (the signature may nest parentheses and templates)
		int32 Depth = 0, I = At + Needle.Len() - 1;
		for (; I < Header.Len(); ++I)
		{
			const TCHAR C = Header[I];
			Depth += C == TCHAR('<') ? 1 : C == TCHAR('>') ? -1 : 0;
			if (Depth == 0)
			{
				break;
			}
		}
		const int32 Semi = Header.Find(TEXT(";"), ESearchCase::CaseSensitive, ESearchDir::FromStart, I);
		At = I + 1;
		if (Semi == INDEX_NONE)
		{
			break;
		}
		const FString Name = Header.Mid(I + 1, Semi - I - 1).TrimStartAndEnd();
		if (Name.IsEmpty() || Name.Contains(TEXT("(")))
		{
			continue;
		}
		++Delegates;
		if (!Mapped.Contains(FName(Name)))
		{
			AddError(FString::Printf(TEXT("the bus delegate FMIGameEvents::%s is not in FMIAudioDirector::BusDelegates: bind it, give it a key in BusEventKeys and an entry in audio.json events"), *Name));
		}
	}
	TestTrue(TEXT("the bus header lists its delegates"), Delegates >= 19);
	// Placeholder material in the replacement layers.
	int32 PlaceholderLayers = 0, AllLayers = 0;
	for (const auto& Pair : D.Replace)
	{
		for (const FMIReplaceLayer& L : Pair.Value.Layers)
		{
			++AllLayers;
			PlaceholderLayers += L.bPlaceholder ? 1 : 0;
			if (!L.bPlaceholder && L.Files.ContainsByPredicate([](const FString& F) { return F.StartsWith(TEXT("Gen/")); }))
			{
				AddError(FString::Printf(TEXT("replace %s layer %s plays generated files but is not marked placeholder"), *Pair.Key.ToString(), *L.Name.ToString()));
			}
		}
	}
	AddInfo(FString::Printf(TEXT("%d bus event keys (%d flow lines found in the source): %d play, %d rules, %d silent; %d sounds; %d of %d replacement files present; %d bus delegates, all bound; %d of %d replacement layers are placeholders"),
		Keys.Num(), FromSource, Played, Ruled, Silent, D.Sounds.Num(), GenFiles - GenMissing, GenFiles, Delegates, PlaceholderLayers, AllLayers));
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
	// After tools/box/audio-import.sh: every WAV under Content/Audio is a Sound Wave of the same length, not older than
	// its WAV, and the loops loop. A clone without the assets fails here: every cloud package up to version 3a was made
	// from such a clone and was silent (this test only warned then).
	TArray<FString> Files;
	IFileManager::Get().FindFilesRecursive(Files, *FMIAudioData::AudioDir(), TEXT("*.wav"), true, false);
	int32 Checked = 0, Missing = 0, Wrong = 0, Stale = 0, Loops = 0;
	for (const FString& Path : Files)
	{
		FString Rel = Path;
		FPaths::MakePathRelativeTo(Rel, *(FMIAudioData::AudioDir() + TEXT("/")));
		if (FPaths::GetCleanFilename(Rel).StartsWith(TEXT("IR_")))
		{
			continue;  // the two reverb responses: not sounds the game plays (audio_sounds.json bus "ir"), not imported
		}
		const USoundWave* W = LoadObject<USoundWave>(nullptr, *FMIAudioData::AssetPath(Rel), nullptr, LOAD_NoWarn | LOAD_Quiet);
		if (!W)
		{
			if (++Missing <= 8)
			{
				AddError(FString::Printf(TEXT("%s has no Sound Wave asset (%s)"), *Rel, *FMIAudioData::AssetPath(Rel)));
			}
			continue;
		}
		FMIWav Wav;
		if (FMIWav::Load(Path, Wav) && FMath::Abs(W->Duration - Wav.Secs()) > 0.02)
		{
			++Wrong;
			AddError(FString::Printf(TEXT("%s: asset %.3f s, file %.3f s"), *Rel, W->Duration, Wav.Secs()));
		}
		// A WAV replaced after the import (a real recording under a placeholder's name) is not in the game yet.
		FString Package = FMIAudioData::AssetPath(Rel), AssetFile;
		Package.Split(TEXT("."), &Package, nullptr);
		if (FPackageName::TryConvertLongPackageNameToFilename(Package, AssetFile, FPackageName::GetAssetPackageExtension()))
		{
			const FDateTime AssetTime = IFileManager::Get().GetTimeStamp(*AssetFile), WavTime = IFileManager::Get().GetTimeStamp(*Path);
			if (AssetTime != FDateTime::MinValue() && WavTime > AssetTime + FTimespan::FromSeconds(2.0) && ++Stale <= 8)
			{
				AddError(FString::Printf(TEXT("%s is newer than its Sound Wave asset: import it again (tools/box/audio-import.sh)"), *Rel));
			}
		}
		Loops += W->bLooping ? 1 : 0;
		++Checked;
	}
	AddInfo(FString::Printf(TEXT("%d of %d files imported as Sound Waves (%d missing, %d with a wrong length, %d older than their WAV, %d looping)"), Checked, Checked + Missing, Missing, Wrong, Stale, Loops));
	if (Checked == 0)
	{
		AddError(TEXT("no audio assets imported: the game is silent in this clone and in every package made from it. Run tools/box/audio-import.sh (tools/box/sync.sh starts it when assets are missing)"));
		return false;
	}
	TestEqual(TEXT("every file has its asset"), Missing, 0);
	TestEqual(TEXT("no asset is older than its WAV"), Stale, 0);
	TestTrue(TEXT("the loops loop (stems, beds, rotor, train ...)"), Loops >= 15);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioSoundsResolveTest, "MurderInc.Audio.SoundsResolve", Flags)
bool FMIAudioSoundsResolveTest::RunTest(const FString& Parameters)
{
	// Every sound the game's data can play ends in a Sound Wave that loads: every variant of every web sound, every
	// file of every replacement layer, every take of every voice line of every character (the clean takes too), the
	// bleep tone. And every sound id a table of audio.json names is a sound of the data.
	FMIAudioData D;
	FMIVoiceData V;
	FString Error;
	if (!FMIAudioData::Load(D, Error) || !FMIVoiceData::Load(V, Error))
	{
		AddError(Error);
		return false;
	}
	TSet<FString> Files;
	for (const auto& Pair : D.Sounds)
	{
		for (const FString& F : Pair.Value.Files)
		{
			Files.Add(F);
		}
	}
	for (const auto& Pair : D.Replace)
	{
		for (const FMIReplaceLayer& L : Pair.Value.Layers)
		{
			for (const FString& F : L.Files)
			{
				Files.Add(F);
			}
		}
	}
	const int32 SoundFiles = Files.Num();
	for (const auto& Pair : V.Characters)
	{
		for (const FMIVoiceLine& L : Pair.Value.Lines)
		{
			for (const TArray<FMIVoiceTake>* Set : {&L.Takes, &L.CleanTakes})
			{
				for (const FMIVoiceTake& T : *Set)
				{
					Files.Add(FString::Printf(TEXT("Voice/%s/%s"), *Pair.Key.ToString(), *T.File));
				}
			}
		}
	}
	Files.Add(TEXT("Gen/bleep_1k.wav"));
	int32 Loaded = 0, Bad = 0;
	for (const FString& F : Files)
	{
		const USoundWave* W = LoadObject<USoundWave>(nullptr, *FMIAudioData::AssetPath(F), nullptr, LOAD_NoWarn | LOAD_Quiet);
		if (W && W->Duration > 0.01f && W->NumChannels >= 1)
		{
			++Loaded;
		}
		else if (++Bad <= 12)
		{
			AddError(W ? FString::Printf(TEXT("%s: its Sound Wave is empty (%.3f s, %d channels)"), *F, W->Duration, W->NumChannels)
				: FString::Printf(TEXT("%s: no Sound Wave loads from %s"), *F, *FMIAudioData::AssetPath(F)));
		}
	}
	TestEqual(TEXT("every file the data can play is a Sound Wave that loads"), Bad, 0);

	// The ids the tables name.
	int32 Ids = 0;
	auto Need = [this, &D, &Ids](const FString& Id, const TCHAR* Where)
	{
		if (Id.IsEmpty() || Id.Contains(TEXT("{")))
		{
			return;
		}
		++Ids;
		const FMISoundDef* Def = D.Find(FName(*Id));
		if (!Def)
		{
			AddError(FString::Printf(TEXT("%s names the sound %s, which the data does not have"), Where, *Id));
		}
		else if (Def->bReplaceOnly)
		{
			// A sound that exists only as layers must have material, or a fallback that is a sound.
			const FMIReplace* Rep = D.Replace.Find(Def->Name);
			const bool bLayers = Rep && Rep->Layers.ContainsByPredicate([](const FMIReplaceLayer& L) { return L.Files.Num() > 0; });
			if (!bLayers && !(Rep && D.Find(Rep->Fallback)))
			{
				AddError(FString::Printf(TEXT("%s names %s, which has no layer file and no fallback sound"), Where, *Id));
			}
		}
	};
	using namespace MIAudioJson;
	for (const auto& Pair : D.Events)
	{
		const FString Key = Pair.Key.ToString();
		const TSharedPtr<FJsonObject>& E = Pair.Value;
		for (const TCHAR* Field : {TEXT("sound"), TEXT("in"), TEXT("out")})
		{
			Need(Str(E, Field), *Key);
		}
		const TArray<TSharedPtr<FJsonValue>>* List = nullptr;
		if (E->TryGetArrayField(TEXT("play"), List))
		{
			for (const TSharedPtr<FJsonValue>& P : *List)
			{
				Need(Str(P->AsObject(), TEXT("sound")), *Key);
			}
		}
		if (E->TryGetArrayField(TEXT("layers"), List))
		{
			for (const TSharedPtr<FJsonValue>& P : *List)
			{
				Need(P->AsString(), *Key);
			}
		}
		if (const TSharedPtr<FJsonObject> Stings = Obj(E, TEXT("stings")))
		{
			for (const auto& S : Stings->Values)
			{
				Need(S.Value->AsString(), *Key);
			}
		}
	}
	const TSharedPtr<FJsonObject> Music = D.Table(TEXT("music")), Amb = D.Table(TEXT("ambience"));
	const TArray<TSharedPtr<FJsonValue>>* Stems = nullptr;
	if (Music.IsValid() && Music->TryGetArrayField(TEXT("stems"), Stems))
	{
		for (const TSharedPtr<FJsonValue>& S : *Stems)
		{
			Need(S->AsString(), TEXT("music.stems"));
		}
	}
	TestTrue(TEXT("the music has its stems"), Stems && Stems->Num() >= 7);
	Need(Str(Obj(Amb, TEXT("beds")), TEXT("day")), TEXT("ambience.beds"));
	Need(Str(Obj(Amb, TEXT("beds")), TEXT("night")), TEXT("ambience.beds"));
	Need(Str(Obj(Amb, TEXT("wind")), TEXT("sound")), TEXT("ambience.wind"));
	if (const TSharedPtr<FJsonObject> Schedule = Obj(Amb, TEXT("schedule")))
	{
		for (const auto& S : Schedule->Values)
		{
			if (S.Value->Type == EJson::Object)
			{
				Need(FString(*S.Key), TEXT("ambience.schedule"));
			}
		}
	}
	Need(Str(D.Table(TEXT("heartbeat")), TEXT("sound"), TEXT("heartbeat")), TEXT("heartbeat"));
	if (const TSharedPtr<FJsonObject> Families = D.Table(TEXT("weaponSounds")))
	{
		for (const auto& F : Families->Values)
		{
			if (FString(*F.Key) != TEXT("about"))
			{
				Need(F.Value->AsString() + TEXT("_shot"), TEXT("weaponSounds"));
				Need(F.Value->AsString() + TEXT("_tail_out"), TEXT("weaponSounds"));
				Need(F.Value->AsString() + TEXT("_tail_in"), TEXT("weaponSounds"));
			}
		}
	}
	AddInfo(FString::Printf(TEXT("%d of %d files load as Sound Waves (%d of sounds and layers, %d voice takes, the bleep); %d sound ids named by the tables"),
		Loaded, Files.Num(), SoundFiles, Files.Num() - SoundFiles - 1, Ids));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioEveryGunSoundsTest, "MurderInc.Audio.EveryGunSounds", Flags)
bool FMIAudioEveryGunSoundsTest::RunTest(const FString& Parameters)
{
	// Every gun of the roster (guns.json: the loadout offers six, the web game had two) fires with a shot and a tail,
	// its own or its family's (audio.json weaponSounds), reloads, clicks dry and switches with a sound; nothing the
	// game asks for in a magazine's worth of handling is an id the data does not have. And the menus' two sounds play,
	// on a card of a paused run too.
	FMIAudioData D;
	FMIVoiceData V;
	FString Error;
	TSharedPtr<FJsonObject> Guns;
	if (!FMIAudioData::Load(D, Error) || !FMIVoiceData::Load(V, Error) || !UMIDataSubsystem::LoadJsonFile(TEXT("guns.json"), Guns, Error))
	{
		AddError(Error);
		return false;
	}
	const TArray<TSharedPtr<FJsonValue>>* Roster = nullptr;
	if (!Guns->TryGetArrayField(TEXT("roster"), Roster) || Roster->Num() < 2)
	{
		AddError(TEXT("guns.json has no roster"));
		return false;
	}
	FMIAudioDirector A;
	A.Exists = [](const FString&) { return true; };
	A.Init(&D, &V, 5);
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
	auto Starts = [&Cmds](FName Category)
	{
		int32 N = 0;
		for (const FMIAudioCmd& C : Cmds)
		{
			N += C.Type == EMIAudioCmd::Start && C.Category == Category ? 1 : 0;
		}
		return N;
	};
	Bus.Flow.Broadcast(Flow(TEXT("game:state"), TEXT("playing")));
	Step(0.5);
	FString Heard;
	for (const TSharedPtr<FJsonValue>& G : *Roster)
	{
		const FName Gun(*G->AsString());
		Cmds.Reset();
		FMIShotFiredEvent Shot;
		Shot.Weapon = Gun;
		Bus.WeaponFire.Broadcast(Shot);
		Step(0.2);
		TestTrue(FString::Printf(TEXT("%s: a shot is heard (category gun)"), *Gun.ToString()), Starts(TEXT("gun")) >= 1);
		TestTrue(FString::Printf(TEXT("%s: its tail is heard (category tail)"), *Gun.ToString()), Starts(TEXT("tail")) >= 1);
		Heard += FString::Printf(TEXT(" %s as %s (%d shot layers, %d tails)"), *Gun.ToString(), *A.SoundFamily(Gun).ToString(), Starts(TEXT("gun")), Starts(TEXT("tail")));
		Cmds.Reset();
		Bus.WeaponDry.Broadcast(Gun);
		for (const TCHAR* Phase : {TEXT("start"), TEXT("magout"), TEXT("magin"), TEXT("bolt"), TEXT("done")})
		{
			FMIReloadEvent R;
			R.Weapon = Gun;
			R.Phase = Phase;
			Bus.WeaponReload.Broadcast(R);
			Step(0.3);
		}
		FMISwitchEvent Sw;
		Sw.From = Gun;
		Sw.To = Gun;
		Sw.Phase = TEXT("holster");
		Bus.WeaponSwitch.Broadcast(Sw);
		Sw.Phase = TEXT("draw");
		Bus.WeaponSwitch.Broadcast(Sw);
		Bus.WeaponMode.Broadcast(Gun, true);
		Bus.WeaponSwing.Broadcast(Gun);
		Step(0.5);
		TestTrue(FString::Printf(TEXT("%s: dry fire, the five reload stages, holster, draw, the selector and the swing are heard (%d starts)"), *Gun.ToString(), Cmds.Num()),
			Starts(TEXT("near")) + Starts(TEXT("ui")) >= 9);
		Step(1.0);
	}
	AddInfo(TEXT("guns:") + Heard);

	// The menus: a press and a focus move, in play and on the card of a paused run (the ui category is not pausable).
	for (const TCHAR* State : {TEXT("playing"), TEXT("paused")})
	{
		Bus.Flow.Broadcast(Flow(TEXT("game:state"), State));
		Step(0.2);
		Cmds.Reset();
		Bus.Flow.Broadcast(Flow(TEXT("ui:click")));
		Step(0.1);
		Bus.Flow.Broadcast(Flow(TEXT("ui:hover")));
		Step(0.1);
		int32 Clicks = 0, Hovers = 0;
		for (const FMIAudioCmd& C : Cmds)
		{
			Clicks += C.Type == EMIAudioCmd::Start && C.Sound == TEXT("ui_click") ? 1 : 0;
			Hovers += C.Type == EMIAudioCmd::Start && C.Sound == TEXT("ui_hover") ? 1 : 0;
		}
		TestEqual(FString::Printf(TEXT("%s: a press plays ui_click"), State), Clicks, 1);
		TestEqual(FString::Printf(TEXT("%s: a focus move plays ui_hover"), State), Hovers, 1);
	}
	FString Unknown;
	for (const FName N : A.Unknown())
	{
		Unknown += TEXT(" ") + N.ToString();
	}
	TestTrue(TEXT("nothing asked for is an id the data does not have:") + Unknown, A.Unknown().Num() == 0);
	A.Unbind();
	return true;
}

#endif
