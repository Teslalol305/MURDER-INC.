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
	bPinned = false;
	Reason.Reset();
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
	if (UpWaitNow <= 0.0)
	{
		UpWaitNow = UpAfter;
	}
	if (!bEnabled || bPinned || Rungs.Num() == 0)
	{
		OverFor = UnderFor = 0.0;
		return EChange::None;
	}
	const int32 N = Rungs.Num();
	const double Frame = FMath::Max(1.0, In.FrameMs);
	const bool bKnown = In.GpuMs > 0.0;

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
			const double Without = AtSmallest / FMath::Max(0.2, 1.0 - Rungs[Current - 1].Saves);   // the GPU's time with the last step taken off
			bUnder = Without < UpLoad * Frame;
		}
		UnderFor = bUnder ? UnderFor + Step : 0.0;
	}

	if (OverFor >= DownAfter && Current < N && SinceChange >= MinGap && (!Rungs[Current].bCalm || In.bSafeMoment))
	{
		const int32 From = Current;
		++Current;
		if (SinceUp < RetryWindow)
		{
			UpWaitNow = FMath::Min(UpWaitNow * 2.0, MaxUpAfter);   // the last rise did not hold: wait longer for the next
		}
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
