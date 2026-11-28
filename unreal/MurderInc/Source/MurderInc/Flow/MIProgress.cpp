#include "Flow/MIProgress.h"

namespace
{
	const TCHAR* Alphabet = TEXT("0123456789ABCDEFGHJKMNPQRSTVWXYZ");
	const char Salt[] = "MURDERINC-PROGRESS-1";
}

const TArray<FName>& FMIProgress::CodeOrder()
{
	static const TArray<FName> Order = {TEXT("block"), TEXT("chinatown"), TEXT("midtown")};
	return Order;
}

int32 FMIProgress::DifficultyRank(FName D)
{
	if (D == FName(TEXT("hustler"))) return 0;
	if (D == FName(TEXT("boss"))) return 1;
	if (D == FName(TEXT("kingpin"))) return 2;
	return -1;
}

bool FMIProgress::IsCleared(FName Id) const
{
	const FMILevelRecord* R = Levels.Find(Id);
	return R && R->bCleared;
}

bool FMIProgress::IsOpen(FName Id, const TArray<FName>& Order) const
{
	const int32 I = Order.IndexOfByKey(Id);
	return I == 0 || (I > 0 && IsCleared(Order[I - 1]));
}

FName FMIProgress::FurthestOpen(const TArray<FName>& Order) const
{
	FName Out = Order.Num() > 0 ? Order[0] : FName(TEXT("block"));
	for (int32 I = 1; I < Order.Num() && IsCleared(Order[I - 1]); ++I)
	{
		Out = Order[I];
	}
	return Out;
}

FName FMIProgress::NextAfter(FName Id, const TArray<FName>& Order) const
{
	const int32 I = Order.IndexOfByKey(Id);
	return (I != INDEX_NONE && I + 1 < Order.Num() && IsCleared(Id)) ? Order[I + 1] : NAME_None;
}

void FMIProgress::RecordStory(FName Id, int32 Points, FName Difficulty)
{
	FMILevelRecord& R = Levels.FindOrAdd(Id);
	R.bCleared = true;
	R.Clears += 1;
	Points = FMath::Clamp(Points, 0, 5);
	const int32 Rank = DifficultyRank(Difficulty);
	if (R.BestPoints < 0 || Points > R.BestPoints || (Points == R.BestPoints && Rank > DifficultyRank(R.BestDifficulty)))
	{
		R.BestPoints = Points;
		R.BestDifficulty = Rank >= 0 ? Difficulty : FName(TEXT("hustler"));
	}
}

void FMIProgress::RecordHold(FName Id, int32 Score)
{
	FMILevelRecord& R = Levels.FindOrAdd(Id);
	R.HoldBest = FMath::Max(R.HoldBest, Score);
}

void FMIProgress::Merge(const FMIProgress& O)
{
	for (const TPair<FName, FMILevelRecord>& P : O.Levels)
	{
		FMILevelRecord& R = Levels.FindOrAdd(P.Key);
		const FMILevelRecord& B = P.Value;
		R.bCleared |= B.bCleared;
		R.Clears = FMath::Max(R.Clears, B.Clears);
		R.HoldBest = FMath::Max(R.HoldBest, B.HoldBest);
		if (B.BestPoints >= 0 && (R.BestPoints < 0 || B.BestPoints > R.BestPoints
			|| (B.BestPoints == R.BestPoints && DifficultyRank(B.BestDifficulty) > DifficultyRank(R.BestDifficulty))))
		{
			R.BestPoints = B.BestPoints;
			R.BestDifficulty = B.BestDifficulty;
		}
	}
	bAlbumSeen |= O.bAlbumSeen;
}

uint16 FMIProgress::Crc16(const uint8* Data, int32 Num, uint16 Crc)
{
	for (int32 I = 0; I < Num; ++I)
	{
		Crc ^= static_cast<uint16>(Data[I]) << 8;
		for (int32 K = 0; K < 8; ++K)
		{
			Crc = (Crc & 0x8000) ? static_cast<uint16>((Crc << 1) ^ 0x1021) : static_cast<uint16>(Crc << 1);
		}
	}
	return Crc;
}

static uint16 CheckOf(uint32 Payload)
{
	uint8 Buf[sizeof(Salt) - 1 + 3];
	FMemory::Memcpy(Buf, Salt, sizeof(Salt) - 1);
	Buf[sizeof(Salt) - 1] = (Payload >> 16) & 0xFF;
	Buf[sizeof(Salt)] = (Payload >> 8) & 0xFF;
	Buf[sizeof(Salt) + 1] = Payload & 0xFF;
	return FMIProgress::Crc16(Buf, sizeof(Buf));
}

FString FMIProgress::EncodeCode() const
{
	uint32 P = 1u << 21;
	const TArray<FName>& Order = CodeOrder();
	for (int32 I = 0; I < 3; ++I)
	{
		const FMILevelRecord* R = Levels.Find(Order[I]);
		const bool bClear = R && R->bCleared;
		const uint32 Points = bClear && R->BestPoints >= 0 ? static_cast<uint32>(FMath::Min(R->BestPoints, 5)) : 7u;
		const int32 Rank = bClear ? DifficultyRank(R->BestDifficulty) : -1;
		P |= (bClear ? 1u : 0u) << (16 + I);
		P |= (bClear ? Points : 7u) << (7 + 3 * I);
		P |= (bClear ? static_cast<uint32>(Rank >= 0 ? Rank : 0) : 3u) << (1 + 2 * I);
	}
	P |= bAlbumSeen ? 1u : 0u;
	const uint64 V = (static_cast<uint64>(P) << 16) | CheckOf(P);
	FString S;
	for (int32 K = 0; K < 8; ++K)
	{
		S.AppendChar(Alphabet[(V >> (35 - 5 * K)) & 31]);
	}
	return S.Left(4) + TEXT("-") + S.Mid(4);
}

bool FMIProgress::DecodeCode(const FString& In, FMIProgress& Out)
{
	FString S;
	for (const TCHAR C : In.ToUpper())
	{
		if (C == TEXT('-') || C == TEXT(' ')) continue;
		S.AppendChar(C == TEXT('O') ? TEXT('0') : (C == TEXT('I') || C == TEXT('L')) ? TEXT('1') : C);
	}
	if (S.Len() != 8)
	{
		return false;
	}
	uint64 V = 0;
	const FString Alpha(Alphabet);
	for (const TCHAR C : S)
	{
		int32 At;
		if (!Alpha.FindChar(C, At))
		{
			return false;
		}
		V = (V << 5) | static_cast<uint64>(At);
	}
	const uint32 P = static_cast<uint32>(V >> 16);
	if (CheckOf(P) != (V & 0xFFFF) || (P >> 21) != 1 || ((P >> 19) & 3) != 0)
	{
		return false;
	}
	bool Cleared[3];
	int32 Pts[3], Dif[3];
	for (int32 I = 0; I < 3; ++I)
	{
		Cleared[I] = (P >> (16 + I)) & 1;
		Pts[I] = (P >> (7 + 3 * I)) & 7;
		Dif[I] = (P >> (1 + 2 * I)) & 3;
		if (Pts[I] == 6 || Cleared[I] != (Pts[I] != 7) || Cleared[I] != (Dif[I] != 3) || (Cleared[I] && I > 0 && !Cleared[I - 1]))
		{
			return false;
		}
	}
	const bool bAlbum = (P & 1) != 0;
	if (bAlbum && !(Cleared[0] && Cleared[1] && Cleared[2]))
	{
		return false;
	}
	Out = FMIProgress();
	static const TCHAR* Names[3] = {TEXT("hustler"), TEXT("boss"), TEXT("kingpin")};
	for (int32 I = 0; I < 3; ++I)
	{
		if (Cleared[I])
		{
			FMILevelRecord& R = Out.Levels.Add(CodeOrder()[I]);
			R.bCleared = true;
			R.Clears = 1;
			R.BestPoints = Pts[I];
			R.BestDifficulty = FName(Names[Dif[I]]);
		}
	}
	Out.bAlbumSeen = bAlbum;
	return true;
}
