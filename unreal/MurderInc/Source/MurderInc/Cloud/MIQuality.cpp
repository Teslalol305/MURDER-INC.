#include "Cloud/MIQuality.h"

// ---- the table ------------------------------------------------------------------------------------------------------

namespace MIQualityPrivate
{
	bool IsNameChar(TCHAR Ch)
	{
		return FChar::IsAlnum(Ch) || Ch == TEXT('.') || Ch == TEXT('_');
	}

	bool IsValueChar(TCHAR Ch)
	{
		// One value: nothing that starts another command or another argument (the same rule as a viewer's tuning, MITuning).
		return Ch >= TEXT(' ') && Ch != TEXT('|') && Ch != TEXT(';') && Ch != TEXT('"') && Ch != TEXT('\'') && Ch != TEXT(',');
	}

	bool Fail(FString* Error, const FString& Text)
	{
		if (Error)
		{
			*Error = Text;
		}
		return false;
	}
}

bool FMIQualityTable::ParseStep(const FString& Line, FMIQualityStep& Out, FString* Error)
{
	using namespace MIQualityPrivate;
	TArray<FString> Parts;
	Line.ParseIntoArray(Parts, TEXT("|"), false);
	if (Parts.Num() != 4)
	{
		return Fail(Error, FString::Printf(TEXT("\"%s\": write name | saves | live or calm | variable=value, variable=value"), *Line));
	}
	for (FString& P : Parts)
	{
		P.TrimStartAndEndInline();
	}
	FMIQualityStep S;
	S.Name = Parts[0];
	if (S.Name.IsEmpty() || S.Name.Len() > 40)
	{
		return Fail(Error, FString::Printf(TEXT("\"%s\": the name is empty or longer than 40 characters"), *Line));
	}
	for (const TCHAR Ch : S.Name)
	{
		if (Ch < TEXT(' '))
		{
			return Fail(Error, FString::Printf(TEXT("\"%s\": a control character in the name"), *Line));
		}
	}
	FString Percent = Parts[1];
	if (Percent.EndsWith(TEXT("%")))
	{
		Percent.LeftChopInline(1);
		Percent.TrimEndInline();
	}
	bool bNumber = !Percent.IsEmpty();
	for (const TCHAR Ch : Percent)
	{
		bNumber = bNumber && (FChar::IsDigit(Ch) || Ch == TEXT('.'));
	}
	const double Saves = bNumber ? FCString::Atod(*Percent) : -1.0;
	if (!bNumber || Saves < 0.0 || Saves > 60.0)
	{
		return Fail(Error, FString::Printf(TEXT("\"%s\": saves is a percentage from 0 to 60"), *Line));
	}
	S.Saves = Saves / 100.0;
	if (Parts[2].Equals(TEXT("live"), ESearchCase::IgnoreCase))
	{
		S.bCalm = false;
	}
	else if (Parts[2].Equals(TEXT("calm"), ESearchCase::IgnoreCase))
	{
		S.bCalm = true;
	}
	else
	{
		return Fail(Error, FString::Printf(TEXT("\"%s\": the third part is live or calm"), *Line));
	}
	TArray<FString> Items;
	Parts[3].ParseIntoArray(Items, TEXT(","), true);
	for (FString& Item : Items)
	{
		Item.TrimStartAndEndInline();
		FString Name, Value;
		if (!Item.Split(TEXT("="), &Name, &Value))
		{
			return Fail(Error, FString::Printf(TEXT("\"%s\": \"%s\" is not variable=value"), *Line, *Item));
		}
		Name.TrimStartAndEndInline();
		Value.TrimStartAndEndInline();
		int32 Dir = 0;
		if (Name.EndsWith(TEXT("<")))
		{
			Dir = -1;
			Name.LeftChopInline(1);
			Name.TrimEndInline();
		}
		else if (Name.EndsWith(TEXT(">")))
		{
			Dir = 1;
			Name.LeftChopInline(1);
			Name.TrimEndInline();
		}
		if (Dir != 0 && !Value.IsNumeric())
		{
			return Fail(Error, FString::Printf(TEXT("\"%s\": \"%s\": a sign (<= or >=) needs a number"), *Line, *Item));
		}
		bool bOk = !Name.IsEmpty() && Name.Len() <= 96 && !Value.IsEmpty() && Value.Len() <= 64;
		for (const TCHAR Ch : Name)
		{
			bOk = bOk && IsNameChar(Ch);
		}
		for (const TCHAR Ch : Value)
		{
			bOk = bOk && IsValueChar(Ch);
		}
		if (!bOk)
		{
			return Fail(Error, FString::Printf(TEXT("\"%s\": \"%s\" cannot be used (a name of letters, digits, dots and underscores; a value without | ; \" ' or a comma)"), *Line, *Item));
		}
		S.CVars.Emplace(Name, Value);
		if (Dir != 0)
		{
			S.Directions.Add(Name, Dir);
		}
	}
	if (S.CVars.Num() == 0 || S.CVars.Num() > 24)
	{
		return Fail(Error, FString::Printf(TEXT("\"%s\": a step sets 1 to 24 variables"), *Line));
	}
	Out = MoveTemp(S);
	return true;
}

TArray<FMIQualityStep> FMIQualityTable::Parse(const TArray<FString>& Lines, TArray<FString>* Errors)
{
	TArray<FMIQualityStep> Steps;
	for (const FString& Line : Lines)
	{
		if (Line.TrimStartAndEnd().IsEmpty())
		{
			continue;
		}
		FMIQualityStep S;
		FString Error;
		if (Steps.Num() >= MaxSteps)
		{
			if (Errors)
			{
				Errors->Add(FString::Printf(TEXT("\"%s\": more than %d steps"), *Line, MaxSteps));
			}
		}
		else if (ParseStep(Line, S, &Error))
		{
			Steps.Add(MoveTemp(S));
		}
		else if (Errors)
		{
			Errors->Add(Error);
		}
	}
	return Steps;
}

TArray<FString> FMIQualityTable::Names(const TArray<FMIQualityStep>& Steps)
{
	TArray<FString> Out;
	for (const FMIQualityStep& S : Steps)
	{
		for (const TPair<FString, FString>& P : S.CVars)
		{
			Out.AddUnique(P.Key);
		}
	}
	return Out;
}

bool FMIQualityTable::ValueAt(const TArray<FMIQualityStep>& Steps, int32 Step, const FString& Name, FString& OutValue)
{
	for (int32 I = FMath::Min(Step, Steps.Num()) - 1; I >= 0; --I)
	{
		for (int32 J = Steps[I].CVars.Num() - 1; J >= 0; --J)
		{
			if (Steps[I].CVars[J].Key.Equals(Name, ESearchCase::IgnoreCase))
			{
				OutValue = Steps[I].CVars[J].Value;
				return true;
			}
		}
	}
	return false;
}

TArray<FMIQualityStep> FMIQualityTable::Prune(const TArray<FMIQualityStep>& Steps, TFunctionRef<bool(const FString&)> Exists, TArray<FString>* Notes)
{
	TArray<FMIQualityStep> Out;
	for (const FMIQualityStep& S : Steps)
	{
		FMIQualityStep Kept = S;
		Kept.CVars.Reset();
		Kept.Directions.Reset();
		for (const TPair<FString, FString>& P : S.CVars)
		{
			if (Exists(P.Key))
			{
				Kept.CVars.Add(P);
				if (const int32* D = S.Directions.Find(P.Key))
				{
					Kept.Directions.Add(P.Key, *D);
				}
			}
			else if (Notes)
			{
				Notes->Add(FString::Printf(TEXT("step \"%s\": no console variable %s in this build, left out"), *S.Name, *P.Key));
			}
		}
		if (Kept.CVars.Num() > 0)
		{
			Out.Add(MoveTemp(Kept));
		}
		else if (Notes)
		{
			Notes->Add(FString::Printf(TEXT("step \"%s\": none of its variables exist in this build, the step is left out"), *S.Name));
		}
	}
	return Out;
}

int32 FMIQualityTable::Direction(const TArray<FMIQualityStep>& Steps, const FString& Name)
{
	FString First, Last;
	bool bFirst = false;
	int32 Explicit = 0;
	for (const FMIQualityStep& S : Steps)
	{
		for (const TPair<FString, FString>& P : S.CVars)
		{
			if (P.Key.Equals(Name, ESearchCase::IgnoreCase))
			{
				if (!bFirst)
				{
					First = P.Value;
					bFirst = true;
				}
				Last = P.Value;
				if (const int32* D = S.Directions.Find(P.Key))
				{
					Explicit = *D;
				}
			}
		}
	}
	if (Explicit != 0)
	{
		return Explicit;
	}
	if (bFirst && First.IsNumeric() && Last.IsNumeric() && !FMath::IsNearlyEqual(FCString::Atod(*First), FCString::Atod(*Last), 1e-9))
	{
		return FCString::Atod(*Last) < FCString::Atod(*First) ? -1 : 1;
	}
	return 0;
}

bool FMIQualityTable::Lowers(int32 Direction, const FString& Current, const FString& Target)
{
	if (Direction == 0 || !Current.IsNumeric() || !Target.IsNumeric())
	{
		return true;
	}
	const double C = FCString::Atod(*Current), T = FCString::Atod(*Target);
	return Direction < 0 ? C > T + 1e-9 : C < T - 1e-9;
}

// ---- the ladder -----------------------------------------------------------------------------------------------------

void FMIQualityLadder::Configure(const TArray<FMIQualityStep>& Steps)
{
	Rungs.Reset();
	for (const FMIQualityStep& S : Steps)
	{
		FRung R;
		R.Saves = FMath::Clamp(S.Saves, 0.0, 0.6);
		R.bCalm = S.bCalm;
		Rungs.Add(R);
	}
	Current = 0;
	OverFor = UnderFor = 0.0;
	SinceChange = SinceUp = 1e9;
	UpWaitNow = 0.0;
	UpMult = 1.0;
	WarmLeft = 0.0;
	bPinned = false;
	Reason.Reset();
}

void FMIQualityLadder::Hold(double Seconds)
{
	WarmLeft = FMath::Max(WarmLeft, FMath::Max(0.0, Seconds));
	OverFor = UnderFor = 0.0;
}

bool FMIQualityLadder::CanStepDown() const
{
	return bEnabled && !bPinned && Current < Rungs.Num() && !Rungs[Current].bCalm && WarmLeft <= 0.0;
}

void FMIQualityLadder::NoteEffect(int32 Rung, bool bChangedSomething, bool bAfterDescent)
{
	if (Rung >= 1 && Rung <= Rungs.Num())
	{
		Rungs[Rung - 1].bEffective = bChangedSomething;
	}
	if (!bChangedSomething && bAfterDescent && Rung == Current && Rung >= 1)
	{
		// A step that changed nothing has nothing to wait for: the evidence that called for it still stands, so does the next step.
		OverFor = DownAfter;
		SinceChange = MinGap;
	}
}

void FMIQualityLadder::Pin(int32 Step)
{
	bPinned = Step >= 0;
	if (bPinned)
	{
		Current = FMath::Clamp(Step, 0, Rungs.Num());
	}
	OverFor = UnderFor = 0.0;
}

void FMIQualityLadder::SetEnabled(bool bOn)
{
	bEnabled = bOn;
	OverFor = UnderFor = 0.0;
	if (!bOn)
	{
		Current = 0;
	}
}

FMIQualityLadder::EChange FMIQualityLadder::Update(const FInput& In)
{
	const double Step = FMath::Max(0.0, In.Seconds);
	SinceChange += Step;
	SinceUp += Step;
	UpWaitNow = FMath::Min(UpAfter * UpMult, FMath::Max(MaxUpAfter, UpAfter));   // follows UpAfter when that is changed
	// The warm-up runs down whatever else the ladder is doing (a pin by hand, off): it is time, not evidence.
	const bool bWarm = WarmLeft > 0.0;
	if (bWarm)
	{
		WarmLeft = FMath::Max(0.0, WarmLeft - Step);
	}
	if (!bEnabled || bPinned || Rungs.Num() == 0)
	{
		OverFor = UnderFor = 0.0;
		return EChange::None;
	}
	const int32 N = Rungs.Num();
	const double Frame = FMath::Max(1.0, In.FrameMs);
	const bool bKnown = In.GpuMs > 0.0;

	if (bWarm)
	{
		OverFor = UnderFor = 0.0;
		return EChange::None;
	}

	// Evidence is gathered in live play only: a card or a set-up screen costs the GPU less than a fight does (and the
	// start of the game is full of long frames). At a safe moment the counters stand still.
	if (!In.bSafeMoment)
	{
		const bool bOver = In.bSmallestPicture && Current < N && ((bKnown && In.GpuMs > DownLoad * Frame) || In.bHeldBack);
		OverFor = bOver ? OverFor + Step : 0.0;
		bool bUnder = false;
		if (Current > 0 && In.bTargetAtTop && bKnown && !In.bHeldBack)
		{
			const double AtSmallest = In.GpuMsSmallest > 0.0 ? FMath::Min(In.GpuMsSmallest, In.GpuMs) : In.GpuMs;
			const double Saved = Rungs[Current - 1].bEffective ? Rungs[Current - 1].Saves : 0.0;
			const double Without = AtSmallest / FMath::Max(0.2, 1.0 - Saved);   // the GPU's time with the last step taken off
			bUnder = Without < UpLoad * Frame;
		}
		// One bad half second takes a little off the calm counted, not all of it: a fight's GPU time swings by a fifth.
		UnderFor = bUnder ? UnderFor + Step : (CalmDecay > 0.0 ? FMath::Max(0.0, UnderFor - CalmDecay * Step) : 0.0);
	}

	if (OverFor >= DownAfter && Current < N && SinceChange >= MinGap && (!Rungs[Current].bCalm || In.bSafeMoment))
	{
		const int32 From = Current;
		++Current;
		if (SinceUp < RetryWindow)
		{
			UpMult = FMath::Min(UpMult * 2.0, FMath::Max(1.0, MaxUpAfter / FMath::Max(1.0, UpAfter)));   // the last rise did not hold: wait longer for the next
		}
		else
		{
			UpMult = 1.0;   // it held: the short wait is earned back
		}
		UpWaitNow = FMath::Min(UpAfter * UpMult, FMath::Max(MaxUpAfter, UpAfter));
		Reason = FString::Printf(TEXT("step %d -> %d: at the smallest picture the GPU took %.1f ms a frame%s, over %.0f %% of the %.1f ms a frame has, for %.1f s"),
			From, Current, In.GpuMs, In.bHeldBack ? TEXT(" and the game was held back by it") : TEXT(""), DownLoad * 100.0, Frame, OverFor);
		OverFor = UnderFor = 0.0;
		SinceChange = 0.0;
		return EChange::Down;
	}
	if (In.bSafeMoment && UnderFor >= UpWaitNow && Current > 0 && In.bTargetAtTop && SinceChange >= MinGap)
	{
		const int32 From = Current;
		--Current;
		Reason = FString::Printf(TEXT("step %d -> %d: for %.0f s of play the GPU's time without the last step (it saves about %.0f %%) would have been under %.0f %% of the %.1f ms a frame has, and no run is being played"),
			From, Current, UnderFor, Rungs[Current].Saves * 100.0, UpLoad * 100.0, Frame);
		OverFor = UnderFor = 0.0;
		SinceChange = 0.0;
		SinceUp = 0.0;
		return EChange::Up;
	}
	return EChange::None;
}
