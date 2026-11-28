#pragma once

#include "CoreMinimal.h"
#include "World/MIBoxWorld.h"

/**
 * What the flow and the enemies need from Content/Data/level.json, in web units (the `web` blocks: metres, +Y up,
 * north -Z). Read once per process (FMILevelData::Get) and shared by every world: the grey box built at run time
 * and the art map L_Block take their spawn points, objectives, cover and collision from here, never from actors
 * placed by hand.
 */
struct FMILevelPoint
{
	int32 Index = 0;
	FVector Pos = FVector::ZeroVector;
	double Yaw = 0.0;      // web yaw
	FName Type;            // ground / air (spawns)
	FName Zone;
	FString Place;
	bool bInterior = false;
	// Map levels (data_contract.md 1): the nav layer the point is on, whether it is used, the zones it overlooks.
	FName Layer;
	bool bEnabled = true;
	TArray<FName> Overlooks;  // when not empty, a spawn here is a candidate only while the player is in one of these zones
};

struct FMILevelObjective
{
	FName Id;
	FString Code;
	FString Label;
	FString Place;
	FName Zone;
	FVector Pos = FVector::ZeroVector;
	double Yaw = 0.0;
};

struct FMILevelZone
{
	FName Id;
	FString Name;
	double MinX = 0, MaxX = 0, MinZ = 0, MaxZ = 0;
};

struct FMIDeck
{
	double Y = 6.5;  // underside
	double MinX = 0, MaxX = 0, MinZ = 0, MaxZ = 0;
};

struct FMIDoorway
{
	double Ox = 0, Oz = 0, Ix = 0, Iz = 0, Y = 0;
};

struct FMIRoom
{
	FVector Min = FVector::ZeroVector;
	FVector Max = FVector::ZeroVector;
	TArray<FMIDoorway> Doorways;
};

/** `tuning` of a map level (data_contract.md 3, E7): its adds over config.json. Absent on the Block. */
struct FMILevelTuning
{
	int32 MaxAliveAdd = 0;
	int32 PursuitBudgetAdd = 0;
	bool bExcludePlayerRoom = false;
	TArray<TPair<double, int32>> RatingTime;  // seconds, stars; empty: the config table
	TOptional<double> StartPitch;             // degrees
};

struct FMILevelExplosive
{
	int32 Index = 0;
	FName Type;       // propane / rack
	FVector Pos = FVector::ZeroVector;
	double Yaw = 0.0;
	int32 Collider = INDEX_NONE;
};

struct MURDERINC_API FMILevelData
{
	FMIBounds Bounds;
	TArray<FMIBox> Colliders;  // level.json colliders.boxes, in order (Owner = explosive item index or INDEX_NONE)
	TArray<FMILevelPoint> Spawns;
	TArray<FMILevelPoint> Cover;
	TArray<FMILevelObjective> Objectives;
	FMILevelObjective Extraction;
	double ExtractionRadius = 2.5;
	FVector TruckPos = FVector::ZeroVector;
	double TruckYaw = 0.0;
	FMILevelPoint PlayerStart;
	TArray<FMILevelZone> Zones;
	FMIDeck Deck;
	TArray<FMIRoom> Rooms;
	TArray<FMILevelExplosive> Explosives;
	TArray<FVector> CinematicPos;
	TArray<FVector> CinematicLook;

	// ---- what only the map levels have ----
	FName Id = TEXT("block");
	/** False when the file has no `el` (Canal, Midtown): Deck is then a degenerate rectangle far outside the bounds. */
	bool bHasDeck = true;
	FMILevelTuning Tuning;
	/** extraction.arrival == "afterAll": the truck is hidden and its colliders stay out of the box world until every reel is in. */
	bool bTruckAfterAll = false;
	TArray<int32> TruckColliders;  // indices into Colliders
	/** `nav` of a map level: the raw object (layers, links, spawnReach), kept in the contract's shape for the nav lane. */
	TSharedPtr<FJsonObject> NavJson;
	TArray<FName> NavLayerIds;
	/** The room (index into Rooms) that holds a point, or INDEX_NONE. */
	int32 RoomAt(const FVector& WebPos) const;

	/** The zone that holds (x, z), or None. */
	const FMILevelZone* ZoneAt(double X, double Z) const;

	/** Fills a box world with the level's colliders and bounds. */
	void FillWorld(FMIBoxWorld& World, const FMIRng& Root) const;

	/** File: Content/Data/<File>. The Block's is level.json, a map level's is level_<id>.json. */
	static bool Load(FMILevelData& Out, FString& OutError, const FString& File = TEXT("level.json"));
	/** The Block, loaded once per process; null (and an error in the log) when level.json is missing or malformed. */
	static const FMILevelData* Get();
	/** One cached object per level id; "block" is the object Get() returns. Null (and an error in the log) when it does not load. */
	static const FMILevelData* ForLevel(FName Id);
	/** The level the running game plays: set by the game mode before the world begins (Block until then). */
	static void SetActive(FName Id);
	static FName ActiveId();
	static const FMILevelData* Current();
};
