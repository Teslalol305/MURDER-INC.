#include "Cloud/MIStreamQuality.h"

#include "Misc/Parse.h"

#include <algorithm>

// ---- the quantiser --------------------------------------------------------------------------------------------------

int32 FMIEncoderRange::QualityForQp(int32 Qp)
{
	// Pixel Streaming's own conversion of a launch option (PixelStreaming2PluginSettings.cpp, ParseLegacyCommandlineArgs):
	// 100 * (1 - QP / 51), cut. The encoder's arithmetic (QpForQuality) then gives the same QP back for every QP.
	const int32 Q = FMath::Clamp(Qp, 0, TopQp);
	return FMath::Clamp((int32)(100.0f * (1.0f - (Q / (float)TopQp))), 0, 100);
}

int32 FMIEncoderRange::QpForQuality(int32 Quality)
{
	// VideoEncoderConfigNVENC.cpp: (1.0f - (Quality / 100.0f)) * QPRange, cut into a uint32.
	const float Range = (float)TopQp;
	return (int32)(uint32)((1.0f - (FMath::Clamp(Quality, 0, 100) / 100.0f)) * Range);
}

FMIEncoderRange::FRange FMIEncoderRange::Widen(int32 WantedMin, int32 WantedMax, const FSettings& S)
{
	int32 A = FMath::Clamp(WantedMin, 0, TopQp);
	int32 B = FMath::Clamp(WantedMax, 0, TopQp);
	if (A > B)
	{
		Swap(A, B);  // a page that sends them the wrong way round: the same two numbers
	}
	FRange R;
	if (S.bExact)
	{
		R.MinQp = A;
		R.MaxQp = B;
		return R;
	}
	const int32 Below = FMath::Max(0, S.Below), Above = FMath::Max(0, S.Above);
	const int32 Floor = FMath::Clamp(S.Floor, 0, TopQp), Ceiling = FMath::Clamp(S.Ceiling, 0, TopQp);
	// Never sharper than the floor allows, and never less sharp than asked: a request that is under the floor already
	// (QP 5) keeps its own number. The same at the other end: a request over the ceiling keeps its own.
	R.MinQp = FMath::Min(A, FMath::Max(Floor, A - Below));
	R.MaxQp = FMath::Max(B, FMath::Min(Ceiling, B + Above));
	return R;
}

FMIEncoderRange::ECommand FMIEncoderRange::ParseCommand(const FString& Command, int32& OutQp)
{
	FString C = Command.TrimStartAndEnd();
	FString Name, Value;
	int32 Cut = INDEX_NONE;
	for (int32 I = 0; I < C.Len(); ++I)
	{
		if (C[I] == TEXT(' ') || C[I] == TEXT('='))
		{
			Cut = I;
			break;
		}
	}
	if (Cut == INDEX_NONE)
	{
		return ECommand::None;
	}
	Name = C.Left(Cut);
	Value = C.Mid(Cut + 1).TrimStartAndEnd();
	if (Value.StartsWith(TEXT("=")))
	{
		Value = Value.Mid(1).TrimStartAndEnd();
	}
	ECommand Kind = ECommand::None;
	for (const TCHAR* Prefix : {TEXT("PixelStreaming."), TEXT("PixelStreaming2.")})
	{
		if (Name.StartsWith(Prefix, ESearchCase::IgnoreCase))
		{
			const FString Rest = Name.Mid(FCString::Strlen(Prefix));
			if (Rest.Equals(TEXT("Encoder.MinQP"), ESearchCase::IgnoreCase))
			{
				Kind = ECommand::MinQp;
			}
			else if (Rest.Equals(TEXT("Encoder.MaxQP"), ESearchCase::IgnoreCase))
			{
				Kind = ECommand::MaxQp;
			}
			break;
		}
	}
	if (Kind == ECommand::None || Value.IsEmpty() || !Value.IsNumeric())
	{
		return ECommand::None;
	}
	const double V = FCString::Atod(*Value);
	if (!FMath::IsFinite(V))
	{
		return ECommand::None;
	}
	OutQp = FMath::Clamp(FMath::RoundToInt32(V), 0, TopQp);
	return Kind;
}

void FMIEncoderRange::ReadLaunchOptions(const TCHAR* CommandLine, int32& OutMinQp, int32& OutMaxQp)
{
	OutMinQp = OutMaxQp = -1;
	if (!CommandLine)
	{
		return;
	}
	int32 V = 0;
	if (FParse::Value(CommandLine, TEXT("PixelStreamingEncoderMinQP="), V))
	{
		OutMinQp = FMath::Clamp(V, 0, TopQp);
	}
	if (FParse::Value(CommandLine, TEXT("PixelStreamingEncoderMaxQP="), V))
	{
		OutMaxQp = FMath::Clamp(V, 0, TopQp);
	}
}

// ---- the round trip -------------------------------------------------------------------------------------------------

void FMIRoundTrip::Reset()
{
	Count = Next = Accepted = Ignored = 0;
	Newest = -1e9;
	for (float& V : Values)
	{
		V = 0.f;
	}
}

void FMIRoundTrip::Add(double Seconds, double Now)
{
	if (!FMath::IsFinite(Seconds) || Seconds <= 0.0 || Seconds > 60.0)
	{
		++Ignored;
		return;
	}
	Values[Next] = (float)Seconds;
	Next = (Next + 1) % Kept;
	Count = FMath::Min(Count + 1, Kept);
	++Accepted;
	Newest = Now;
}

double FMIRoundTrip::Ms() const
{
	if (Count <= 0)
	{
		return 0.0;
	}
	float Sorted[Kept];
	for (int32 I = 0; I < Count; ++I)
	{
		Sorted[I] = Values[I];
	}
	std::sort(Sorted, Sorted + Count);
	// The median; of an even number the lower one of the middle two (never a value that no report had).
	return (double)Sorted[(Count - 1) / 2] * 1000.0;
}

double FMIRoundTrip::AgeSeconds(double Now) const
{
	return Count > 0 ? FMath::Max(0.0, Now - Newest) : 1e9;
}
