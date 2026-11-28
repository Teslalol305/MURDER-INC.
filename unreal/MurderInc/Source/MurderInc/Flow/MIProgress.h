#pragma once

#include "CoreMinimal.h"

/**
 * The campaign's progress (docs/unreal/maps/progression.md 2 and 4): per level whether its Story was cleared, how many
 * times, the best rating (points 0..5 at a difficulty) and the best Hold score. Pure logic: no engine objects, so the
 * tests drive it directly. Progress only ever goes up (Merge takes the maximum of every field).
 */
struct MURDERINC_API FMILevelRecord
{
	bool bCleared = false;
	int32 Clears = 0;
	int32 BestPoints = -1;  // -1: none, else 0..5
	FName BestDifficulty;   // hustler / boss / kingpin, None while nothing is cleared
	int32 HoldBest = 0;
};

struct MURDERINC_API FMIProgress
{
	TMap<FName, FMILevelRecord> Levels;
	bool bAlbumSeen = false;

	/** The campaign order of this release; the code format v1 carries exactly these three. */
	static const TArray<FName>& CodeOrder();
	/** 0 hustler, 1 boss, 2 kingpin, -1 anything else. */
	static int32 DifficultyRank(FName Difficulty);

	bool IsCleared(FName Id) const;
	/** Level 1 is always open; level i when level i-1 is cleared. `Order` is levels.json order. An unknown id is not open. */
	bool IsOpen(FName Id, const TArray<FName>& Order) const;
	/** The last open level of the order (the Block at the least). */
	FName FurthestOpen(const TArray<FName>& Order) const;
	/** The level after Id in the order that is open, or None (Id is last, or not cleared). */
	FName NextAfter(FName Id, const TArray<FName>& Order) const;

	/** A Story Complete: clears += 1, cleared, and the best rating (higher points, or equal points at a higher difficulty). */
	void RecordStory(FName Id, int32 Points, FName Difficulty);
	void RecordHold(FName Id, int32 Score);
	/** The maximum of each field of both (4.5): commutative, idempotent, never lowers anything. */
	void Merge(const FMIProgress& Other);

	/** XXXX-XXXX (4.3). A level the format does not know is left out; a state the format cannot hold (cleared levels not a prefix) encodes what it can. */
	FString EncodeCode() const;
	/** False for anything that is not a valid code (check, version, reserved bits, consistency). On success Out holds the records (Clears = 1 for a cleared level). */
	static bool DecodeCode(const FString& Code, FMIProgress& Out);
	static uint16 Crc16(const uint8* Data, int32 Num, uint16 Crc = 0xFFFF);
};
