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

	/** The zone that holds (x, z), or None. */
	const FMILevelZone* ZoneAt(double X, double Z) const;

	/** Fills a box world with the level's colliders and bounds. */
	void FillWorld(FMIBoxWorld& World, const FMIRng& Root) const;

	static bool Load(FMILevelData& Out, FString& OutError);
	/** Loaded once per process; null (and an error in the log) when level.json is missing or malformed. */
	static const FMILevelData* Get();
};
