#pragma once

#include "CoreMinimal.h"

class FJsonObject;

/**
 * Multi-layer nav, step A (MAPS.md lane N, midtown.md 17.3 and 17.4): what a level file's `nav` object says.
 * A level with more than one layer gets one nav grid per layer in FMIBoxWorld; a level without `nav.layers` (the Block)
 * has no spec, one plane layer, and every call behaves as it always did.
 * Units are web metres.
 */
struct FMINavLayer
{
	FName Id;
	double Y = 0.0;
	/** false: the plane (the street, today's rule). true: the walkable tops of the colliders at Y (a roof). */
	bool bBoxes = false;
	double MinX = -1e9, MaxX = 1e9, MinZ = -1e9, MaxZ = 1e9;
};

struct MURDERINC_API FMINavSpec
{
	TArray<FMINavLayer> Layers;
	/** Player layer index -> spawn layer indices a ground spawn may use. A layer with no entry allows every layer. */
	TMap<int32, TArray<int32>> Reach;
	/** The most a Goon looks for a firing cell from where he is (metres). */
	double FiringCellRange = 30.0;
	/** Seconds a Goon with no way to fight waits before he is returned to the pool. */
	double StrandedAfter = 10.0;

	bool IsMulti() const { return Layers.Num() > 1; }
	int32 IndexOf(FName Id) const;
	/** May a ground spawn on SpawnLayer be used while the player is on PlayerLayer? */
	bool Allows(int32 PlayerLayer, int32 SpawnLayer) const;

	/** Reads a level file's `nav` object (layers, spawnReach, firingCellRange, strandedAfter). False when it has no layers. */
	static bool Parse(const TSharedPtr<FJsonObject>& Nav, FMINavSpec& Out);
};
