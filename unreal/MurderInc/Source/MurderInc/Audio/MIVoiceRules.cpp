#include "Audio/MIVoiceRules.h"

#include "Core/Data/MIDataSubsystem.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"

namespace MIVoicePrivate
{
	double Num(const TSharedPtr<FJsonObject>& O, const TCHAR* Key, double Default)
	{
		double V = Default;
		return O.IsValid() && O->TryGetNumberField(Key, V) ? V : Default;
	}

	bool Flag(const TSharedPtr<FJsonObject>& O, const TCHAR* Key, bool Default)
	{
		bool V = Default;
		return O.IsValid() && O->TryGetBoolField(Key, V) ? V : Default;
	}

	FString Str(const TSharedPtr<FJsonObject>& O, const TCHAR* Key, const FString& Default = FString())
	{
		FString V;
		return O.IsValid() && O->TryGetStringField(Key, V) ? V : Default;
	}

	TSharedPtr<FJsonObject> Obj(const TSharedPtr<FJsonObject>& O, const TCHAR* Key)
	{
		const TSharedPtr<FJsonObject>* V = nullptr;
		return O.IsValid() && O->TryGetObjectField(Key, V) && V ? *V : nullptr;
	}

	void Takes(const TSharedPtr<FJsonObject>& O, const TCHAR* Key, TArray<FMIVoiceTake>& Out)
	{
		const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
		if (!O.IsValid() || !O->TryGetArrayField(Key, A))
		{
			return;
		}
		for (const TSharedPtr<FJsonValue>& V : *A)
		{
			const TSharedPtr<FJsonObject> T = V->AsObject();
			if (!T.IsValid())
			{
				continue;
			}
			FMIVoiceTake Take;
			Take.File = Str(T, TEXT("file"));
			Take.Intensity = FName(Str(T, TEXT("intensity"), TEXT("spoken")));
			Take.bPlaceholder = Flag(T, TEXT("placeholder"), true);
			const TArray<TSharedPtr<FJsonValue>>* B = nullptr;
			if (T->TryGetArrayField(TEXT("bleep"), B) && B->Num() == 2)
			{
				Take.BleepStart = (*B)[0]->AsNumber();
				Take.BleepEnd = (*B)[1]->AsNumber();
			}
			if (!Take.File.IsEmpty())
			{
				Out.Add(Take);
			}
		}
	}
}

const FMIVoiceLine* FMIVoiceCharacter::Find(FName Line) const
{
	return Lines.FindByPredicate([Line](const FMIVoiceLine& L) { return L.Id == Line; });
}

bool FMIVoiceData::Parse(const TSharedPtr<FJsonObject>& Root, FMIVoiceData& Out, FString& OutError)
{
	using namespace MIVoicePrivate;
	Out = FMIVoiceData();
	if (!Root.IsValid())
	{
		OutError = TEXT("voice.json: no document");
		return false;
	}
	if (const TSharedPtr<FJsonObject> T = Obj(Root, TEXT("triggers")))
	{
		for (const auto& Pair : T->Values)
		{
			const FString Key(*Pair.Key);
			if (Key != TEXT("about"))
			{
				Out.KnownTriggers.Add(FName(Key));
			}
		}
	}

	const TSharedPtr<FJsonObject> S = Obj(Root, TEXT("settings"));
	if (!S.IsValid())
	{
		OutError = TEXT("voice.json: settings missing");
		return false;
	}
	FMIVoiceSettings& Set = Out.Settings;
	Set.Seed = (int32)Num(S, TEXT("seed"), 1);
	Set.GlobalCooldown = Num(S, TEXT("globalCooldown"), Set.GlobalCooldown);
	Set.CoalesceWindow = Num(S, TEXT("coalesceWindow"), Set.CoalesceWindow);
	Set.AfterLineGap = Num(S, TEXT("afterLineGap"), Set.AfterLineGap);
	Set.InterruptMargin = (int32)Num(S, TEXT("interruptMargin"), Set.InterruptMargin);
	Set.LastOfWaveWindow = Num(S, TEXT("lastOfWaveWindow"), Set.LastOfWaveWindow);
	if (const TSharedPtr<FJsonObject> D = Obj(S, TEXT("duck")))
	{
		for (const auto& Pair : D->Values)
		{
			const FString Key(*Pair.Key);
			double V = 0;
			if (Key == TEXT("attack"))
			{
				Set.DuckAttack = Pair.Value->AsNumber();
			}
			else if (Key == TEXT("release"))
			{
				Set.DuckRelease = Pair.Value->AsNumber();
			}
			else if (Pair.Value->TryGetNumber(V))
			{
				Set.Duck.Add(FName(Key), V);
			}
		}
	}
	Set.MultiKillWindow = Num(Obj(S, TEXT("multiKill")), TEXT("window"), Set.MultiKillWindow);
	if (const TSharedPtr<FJsonObject> St = Obj(S, TEXT("streak")))
	{
		const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
		if (St->TryGetArrayField(TEXT("thresholds"), A))
		{
			for (const TSharedPtr<FJsonValue>& V : *A)
			{
				Set.StreakThresholds.Add((int32)V->AsNumber());
			}
		}
		Set.StreakGap = Num(St, TEXT("gap"), Set.StreakGap);
		Set.StreakBreakDamage = Num(St, TEXT("breakDamage"), Set.StreakBreakDamage);
	}
	if (const TSharedPtr<FJsonObject> L = Obj(S, TEXT("lowHealth")))
	{
		Set.LowHealthBelow = Num(L, TEXT("below"), Set.LowHealthBelow);
		Set.LowHealthSurvive = Num(L, TEXT("survive"), Set.LowHealthSurvive);
	}
	if (const TSharedPtr<FJsonObject> F = Obj(S, TEXT("frequency")))
	{
		for (const auto& Pair : F->Values)
		{
			const TSharedPtr<FJsonObject> E = Pair.Value->Type == EJson::Object ? Pair.Value->AsObject() : nullptr;
			if (E.IsValid())
			{
				FMIVoiceFrequency Q;
				Q.Chance = Num(E, TEXT("chance"), 1);
				Q.Cooldown = Num(E, TEXT("cooldown"), 1);
				Q.GlobalCooldown = Num(E, TEXT("globalCooldown"), 1);
				Set.Frequency.Add(FName(FString(*Pair.Key)), Q);
			}
		}
	}
	for (const TCHAR* Needed : {TEXT("off"), TEXT("rare"), TEXT("normal"), TEXT("often")})
	{
		if (!Set.Frequency.Contains(FName(Needed)))
		{
			OutError = FString::Printf(TEXT("voice.json: settings.frequency.%s missing"), Needed);
			return false;
		}
	}
	if (const TSharedPtr<FJsonObject> O = Obj(S, TEXT("options")))
	{
		Set.Defaults.Volume = Num(O, TEXT("voiceVolume"), 1);
		Set.Defaults.bSubtitles = Flag(O, TEXT("subtitles"), true);
		Set.Defaults.Frequency = FName(Str(O, TEXT("frequency"), TEXT("normal")));
		Set.Defaults.bClean = Flag(O, TEXT("cleanLanguage"), false);
	}
	if (const TSharedPtr<FJsonObject> Sub = Obj(S, TEXT("subtitle")))
	{
		Set.SubtitleExtra = Num(Sub, TEXT("extra"), Set.SubtitleExtra);
		Set.SubtitleMin = Num(Sub, TEXT("minSecs"), Set.SubtitleMin);
	}

	Out.Default = FName(Str(Root, TEXT("default"), TEXT("rule")));
	const TSharedPtr<FJsonObject> Chars = Obj(Root, TEXT("characters"));
	if (!Chars.IsValid())
	{
		OutError = TEXT("voice.json: characters missing");
		return false;
	}
	for (const auto& CPair : Chars->Values)
	{
		const TSharedPtr<FJsonObject> C = CPair.Value->Type == EJson::Object ? CPair.Value->AsObject() : nullptr;
		if (!C.IsValid())
		{
			continue;
		}
		FMIVoiceCharacter Ch;
		Ch.Id = FName(FString(*CPair.Key));
		Ch.Speaker = Str(C, TEXT("speaker"), Ch.Id.ToString().ToUpper());
		if (const TSharedPtr<FJsonObject> Lines = Obj(C, TEXT("lines")))
		{
			for (const auto& LPair : Lines->Values)
			{
				const TSharedPtr<FJsonObject> L = LPair.Value->Type == EJson::Object ? LPair.Value->AsObject() : nullptr;
				if (!L.IsValid())
				{
					continue;
				}
				FMIVoiceLine Line;
				Line.Id = FName(FString(*LPair.Key));
				Line.Text = Str(L, TEXT("text"));
				Line.Speaker = Str(L, TEXT("speaker"));
				Line.Priority = (int32)Num(L, TEXT("priority"), 10);
				Line.Cooldown = Num(L, TEXT("cooldown"), 10);
				Line.bInterruptible = Flag(L, TEXT("interruptible"), true);
				Line.Volume = Num(L, TEXT("volume"), 1);
				Line.Queueable = Num(L, TEXT("queueable"), 0);
				Line.bProfane = Flag(L, TEXT("profane"), false);
				Line.bAnswerOnly = Flag(L, TEXT("answerOnly"), false);
				if (const TSharedPtr<FJsonObject> A = Obj(L, TEXT("answer")))
				{
					Line.AnswerLine = FName(Str(A, TEXT("line")));
					Line.AnswerDelay = Num(A, TEXT("delay"), 0.3);
				}
				if (const TSharedPtr<FJsonObject> Tr = Obj(L, TEXT("triggers")))
				{
					for (const auto& TPair : Tr->Values)
					{
						FMIVoiceTriggerRule Rule;
						double Chance = 1;
						if (TPair.Value->TryGetNumber(Chance))
						{
							Rule.Chance = Chance;
						}
						else if (const TSharedPtr<FJsonObject> R = TPair.Value->Type == EJson::Object ? TPair.Value->AsObject() : nullptr)
						{
							Rule.Chance = Num(R, TEXT("chance"), 1);
							Rule.AtLeast = (int32)Num(R, TEXT("atLeast"), 0);
							Rule.Priority = (int32)Num(R, TEXT("priority"), 0);
						}
						Line.Triggers.Add(FName(FString(*TPair.Key)), Rule);
					}
				}
				Takes(L, TEXT("takes"), Line.Takes);
				if (const TSharedPtr<FJsonObject> Clean = Obj(L, TEXT("clean")))
				{
					Line.CleanMode = FName(Str(Clean, TEXT("mode"), TEXT("swap")));
					Line.CleanText = Str(Clean, TEXT("text"), Line.Text);
					Takes(Clean, TEXT("takes"), Line.CleanTakes);
				}
				if (Line.Takes.Num() == 0)
				{
					OutError = FString::Printf(TEXT("voice.json: %s.%s has no takes"), *Ch.Id.ToString(), *Line.Id.ToString());
					return false;
				}
				Ch.Lines.Add(MoveTemp(Line));
			}
		}
		// A stable order (the JSON object's order is not guaranteed): by priority, then id.
		Ch.Lines.Sort([](const FMIVoiceLine& A, const FMIVoiceLine& B)
		{
			return A.Priority != B.Priority ? A.Priority > B.Priority : A.Id.LexicalLess(B.Id);
		});
		Out.Characters.Add(Ch.Id, MoveTemp(Ch));
	}
	for (const auto& Pair : Out.Characters)
	{
		for (const FMIVoiceLine& L : Pair.Value.Lines)
		{
			if (!L.AnswerLine.IsNone() && !Pair.Value.Find(L.AnswerLine))
			{
				OutError = FString::Printf(TEXT("voice.json: %s.%s answers with %s, which does not exist"), *Pair.Key.ToString(), *L.Id.ToString(), *L.AnswerLine.ToString());
				return false;
			}
			for (const auto& T : L.Triggers)
			{
				if (Out.KnownTriggers.Num() > 0 && !Out.KnownTriggers.Contains(T.Key))
				{
					OutError = FString::Printf(TEXT("voice.json: %s.%s listens to the unknown trigger %s"), *Pair.Key.ToString(), *L.Id.ToString(), *T.Key.ToString());
					return false;
				}
			}
		}
	}
	if (!Out.Characters.Contains(Out.Default))
	{
		OutError = FString::Printf(TEXT("voice.json: the default character %s has no entry"), *Out.Default.ToString());
		return false;
	}
	return true;
}

bool FMIVoiceData::Load(FMIVoiceData& Out, FString& OutError)
{
	TSharedPtr<FJsonObject> Root;
	return UMIDataSubsystem::LoadJsonFile(TEXT("voice.json"), Root, OutError) && Parse(Root, Out, OutError);
}

// ---------------------------------------------------------------------------------------------------------- rules

void FMIVoiceRules::Init(const FMIVoiceData* InData, FName InCharacter, const FMIVoiceOptions& InOptions, int32 SeedOffset)
{
	Data = InData;
	Options = InOptions;
	Rng.Initialize(Data ? Data->Settings.Seed + SeedOffset : SeedOffset);
	SetCharacter(InCharacter.IsNone() && Data ? Data->Default : InCharacter);
}

void FMIVoiceRules::SetCharacter(FName InCharacter)
{
	Character = InCharacter;
	Window.Reset();
	WindowOpened = -1.0;
	Queue.Reset();
	Answers.Reset();
	LastPlay.Reset();
	LastTake.Reset();
	LastAnyStart = LastAnyEnd = SpeakingUntil = -1e9;
	Current = NAME_None;
}

const FMIVoiceCharacter* FMIVoiceRules::Set() const
{
	return Data ? Data->Characters.Find(Character) : nullptr;
}

const FMIVoiceFrequency& FMIVoiceRules::Freq() const
{
	static const FMIVoiceFrequency Normal;
	const FMIVoiceFrequency* F = Data ? Data->Settings.Frequency.Find(Options.Frequency) : nullptr;
	return F ? *F : Normal;
}

double FMIVoiceRules::LastStart(FName Line) const
{
	const double* T = LastPlay.Find(Line);
	return T ? *T : -1e9;
}

void FMIVoiceRules::Trigger(FName TriggerName, double Now, int32 Value)
{
	if (!Data || !Set())
	{
		return;
	}
	if (Window.Num() == 0)
	{
		WindowOpened = Now;
	}
	Window.Add({TriggerName, Value, WindowOrder++});
}

bool FMIVoiceRules::CoolingDown(const FMIVoiceLine& Line, double Now) const
{
	return Now - LastStart(Line.Id) < Line.Cooldown * Freq().Cooldown;
}

bool FMIVoiceRules::CanStart(int32 Priority, double Now, bool bQueued, bool& bOutInterrupt) const
{
	const int32 Margin = Data->Settings.InterruptMargin;
	bOutInterrupt = false;
	if (IsSpeaking(Now))
	{
		// Cut the playing line only for a much more important one, and never a line that may not be cut.
		if (bCurrentInterruptible && Priority >= CurrentPriority + Margin)
		{
			bOutInterrupt = true;
			return true;
		}
		return false;
	}
	// Breathing room after any line, then the global cooldown: both waived for a line far above the last one.
	const bool bBig = Priority >= LastPriority + Margin;
	if (Now - LastAnyEnd < Data->Settings.AfterLineGap && !bBig)
	{
		return false;
	}
	if (!bQueued && !bBig && Now - LastAnyStart < Data->Settings.GlobalCooldown * Freq().GlobalCooldown)
	{
		return false;
	}
	return true;
}

void FMIVoiceRules::Start(const FMIVoiceLine& Line, int32 Priority, FName TriggerName, double Now, bool bInterrupt, bool bAnswer, TArray<FMIVoicePlay>& Out)
{
	const FMIVoiceCharacter* Ch = Set();
	const bool bClean = Options.bClean && Line.bProfane;
	const bool bSwap = bClean && Line.CleanMode == TEXT("swap") && Line.CleanTakes.Num() > 0;
	const TArray<FMIVoiceTake>& Takes = bSwap ? Line.CleanTakes : Line.Takes;

	// A take at random, never the one this line played last time (when it has more than one).
	int32 Take = 0;
	if (Takes.Num() > 1)
	{
		const int32* Last = LastTake.Find(Line.Id);
		Take = Rng.RandRange(0, Takes.Num() - 1);
		if (Last && Take == *Last)
		{
			Take = (Take + 1 + Rng.RandRange(0, Takes.Num() - 2)) % Takes.Num();
		}
	}
	LastTake.Add(Line.Id, Take);
	const FMIVoiceTake& T = Takes[Take];

	FMIVoicePlay P;
	P.Character = Character;
	P.Line = Line.Id;
	P.Trigger = TriggerName;
	P.Take = Take;
	P.File = T.File;
	P.Text = bSwap ? Line.CleanText : Line.Text;
	P.Speaker = Line.Speaker.IsEmpty() ? (Ch ? Ch->Speaker : FString()) : Line.Speaker;
	P.Volume = Line.Volume * Options.Volume;
	P.Start = Now;
	P.Secs = TakeSecs ? TakeSecs(Character, T.File) : 1.5;
	P.bInterrupt = bInterrupt;
	P.bBleep = bClean && !bSwap && T.BleepEnd > T.BleepStart;
	P.BleepStart = T.BleepStart;
	P.BleepEnd = T.BleepEnd;
	P.bAnswer = bAnswer;
	P.bPlaceholder = T.bPlaceholder;
	Out.Add(P);

	++PlayedCount;
	LastPlay.Add(Line.Id, Now);
	LastAnyStart = Now;
	LastAnyEnd = Now + P.Secs;
	LastPriority = Priority;
	Current = Line.Id;
	CurrentPriority = Priority;
	bCurrentInterruptible = Line.bInterruptible;
	SpeakingUntil = Now + P.Secs;
	if (bInterrupt)
	{
		Answers.Reset();  // the cut line's answer goes with it
	}
	if (!Line.AnswerLine.IsNone())
	{
		Answers.Add({Line.AnswerLine, Now + P.Secs + Line.AnswerDelay});
	}
}

void FMIVoiceRules::Tick(double Now, TArray<FMIVoicePlay>& Out)
{
	const FMIVoiceCharacter* Ch = Set();
	if (!Data || !Ch)
	{
		return;
	}

	// 1. Answers (the crowd after "What's my name"): on time, whatever else is going on.
	for (int32 I = 0; I < Answers.Num(); ++I)
	{
		if (Now >= Answers[I].At)
		{
			const FAnswer A = Answers[I];
			Answers.RemoveAt(I--);
			if (const FMIVoiceLine* L = Ch->Find(A.Line))
			{
				Start(*L, L->Priority, TEXT("answer"), Now, false, true, Out);
			}
		}
	}

	// 2. The queue: lines that already won their roll, waiting for the line in front of them.
	for (int32 I = 0; I < Queue.Num(); ++I)
	{
		if (Now > Queue[I].Deadline)
		{
			Queue.RemoveAt(I--);
			continue;
		}
		const FMIVoiceLine* L = Ch->Find(Queue[I].Line);
		bool bInterrupt = false;
		if (L && Answers.Num() == 0 && CanStart(Queue[I].Priority, Now, true, bInterrupt) && !bInterrupt)
		{
			const FQueued Q = Queue[I];
			Queue.RemoveAt(I--);
			Start(*L, Q.Priority, Q.Trigger, Now, false, false, Out);
		}
	}

	// 3. The coalescing window: every trigger of the last moments judged together, the most important line first.
	if (Window.Num() == 0 || Now < WindowOpened + Data->Settings.CoalesceWindow)
	{
		return;
	}
	struct FCandidate
	{
		const FMIVoiceLine* Line;
		FName Trigger;
		double Chance;
		int32 Order;
		int32 Priority;
	};
	TArray<FCandidate> Candidates;
	for (const FPending& P : Window)
	{
		for (const FMIVoiceLine& L : Ch->Lines)
		{
			const FMIVoiceTriggerRule* R = L.bAnswerOnly ? nullptr : L.Triggers.Find(P.Trigger);
			if (R && P.Value >= R->AtLeast)
			{
				Candidates.Add({&L, P.Trigger, R->Chance, P.Order, R->Priority > 0 ? R->Priority : L.Priority});
			}
		}
	}
	Window.Reset();
	Candidates.StableSort([](const FCandidate& A, const FCandidate& B)
	{
		return A.Priority != B.Priority ? A.Priority > B.Priority : A.Order < B.Order;
	});
	TSet<FName> Tried;
	bool bSpoke = false;
	for (const FCandidate& C : Candidates)
	{
		if (Tried.Contains(C.Line->Id) || CoolingDown(*C.Line, Now))
		{
			continue;
		}
		// Once a line has won, only lines that can wait their turn are still considered (they queue behind it).
		if (bSpoke && C.Line->Queueable <= 0.0)
		{
			continue;
		}
		Tried.Add(C.Line->Id);
		// Every candidate rolls in turn (fixed order, seeded): the first that wins speaks.
		const double Chance = FMath::Clamp(C.Chance * Freq().Chance, 0.0, 1.0);
		if (Chance <= 0.0 || Rng.GetFraction() >= Chance)
		{
			continue;
		}
		bool bInterrupt = false;
		if (!bSpoke && Answers.Num() == 0 && CanStart(C.Priority, Now, false, bInterrupt))
		{
			Start(*C.Line, C.Priority, C.Trigger, Now, bInterrupt, false, Out);
			bSpoke = true;
		}
		else if (C.Line->Queueable > 0.0 && !Queue.ContainsByPredicate([&C](const FQueued& Q) { return Q.Line == C.Line->Id; }))
		{
			Queue.Add({C.Line->Id, C.Trigger, C.Priority, Now + C.Line->Queueable});
			if (!bSpoke)
			{
				break;
			}
		}
		else if (!bSpoke)
		{
			break;
		}
	}
}

void FMIVoiceRules::Silence(double Now)
{
	Window.Reset();
	Queue.Reset();
	Answers.Reset();
	if (IsSpeaking(Now))
	{
		LastAnyEnd = Now;
	}
	SpeakingUntil = -1e9;
	Current = NAME_None;
}
