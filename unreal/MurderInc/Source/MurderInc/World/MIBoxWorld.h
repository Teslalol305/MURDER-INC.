#pragma once

#include "CoreMinimal.h"
#include "Core/MIMath.h"

/**
 * The block as the web game's AI sees it (src/physics.js, ported line for line): axis-aligned boxes from
 * level.json `colliders`, the play bounds, rays, sight lines, floor heights, the capsule move and the nav grid
 * the Goons path on. The enemies and the flow run on this in every map (the grey box built at run time and the
 * art map L_Block, whose collision boxes are made from the same list), so their decisions equal the web game's
 * frame for frame (MurderInc.Golden.World, MurderInc.Golden.Enemies).
 *
 * Web units and axes throughout: metres, +Y up, north -Z, east +X. MI::Web converts to Unreal space.
 */

namespace MI::Web
{
	/** Web metres (x, y up, z south) to Unreal centimetres (X east, Y south, Z up). */
	inline FVector ToUnreal(const FVector& W) { return FVector(W.X, W.Z, W.Y) * 100.0; }
	inline FVector FromUnreal(const FVector& U) { return FVector(U.X, U.Z, U.Y) * 0.01; }
	/** Web yaw (0 = north -Z, + = left, radians) to Unreal yaw (0 = +X east, degrees). */
	inline double YawToUnreal(double WebYaw) { return MI::WrapDegrees(-MI::RadToDeg(WebYaw) - 90.0); }
	inline double YawFromUnreal(double UnrealYaw) { return -MI::DegToRad(UnrealYaw + 90.0); }

	/** wrapAngle / angleDelta of src/core/util.js (radians, (-pi, pi]). */
	inline double WrapAngle(double A)
	{
		A = FMath::Fmod(A + UE_DOUBLE_PI, 2.0 * UE_DOUBLE_PI);
		if (A <= 0.0)
		{
			A += 2.0 * UE_DOUBLE_PI;
		}
		return A - UE_DOUBLE_PI;
	}
	inline double AngleDelta(double From, double To) { return WrapAngle(To - From); }
	inline double Hypot(double A, double B) { return FMath::Sqrt(A * A + B * B); }
	inline double Hypot(double A, double B, double C) { return FMath::Sqrt(A * A + B * B + C * C); }
}

struct FMIBox
{
	FVector Min = FVector::ZeroVector;
	FVector Max = FVector::ZeroVector;
	FName Tag;
	FName Surface;
	bool bBulletOnly = false;  // hit by rays, ignored by movement and nav
	bool bPlayerOnly = false;  // blocks capsule movement, ignored by rays and nav
	bool bNoNav = false;
	int32 Owner = INDEX_NONE;  // the explosive item it belongs to, else INDEX_NONE
	int32 Id = INDEX_NONE;     // level.json collider index (or a new id for boxes added later)
};

struct FMIBounds
{
	double MinX = -46.0, MaxX = 46.0, MinZ = -34.0, MaxZ = 34.0;
};

struct FMIRayHit
{
	double Dist = 0.0;
	FVector Point = FVector::ZeroVector;
	FVector Normal = FVector::ZeroVector;
	int32 Box = INDEX_NONE;  // index into Boxes, INDEX_NONE for the ground plane
	FName Surface;
};

struct FMIMoveResult
{
	bool bOnGround = false;
	bool bHitWall = false;
	bool bHitCeil = false;
	FName Surface;
};

class MURDERINC_API FMIBoxWorld
{
public:
	static constexpr double StepHeight = 0.42;
	static constexpr double AirStep = 0.08;

	/** The nav grid's random points draw from Rng.Fork("nav") (physics.js takes G.rng.fork('nav')). */
	void Reset(const FMIBounds& InBounds, const FMIRng& Root);

	int32 AddBox(const FMIBox& Box);
	/** Removes every box of an explosive item (when it is gone). */
	void RemoveOwner(int32 Owner);

	const TArray<FMIBox>& GetBoxes() const { return Boxes; }
	const FMIBounds& GetBounds() const { return Bounds; }
	/** Grows whenever the box list changes (the enemies' packed solids follow it). */
	uint32 GetRevision() const { return Revision; }

	/** Nearest hit within MaxDist (rays ignore player-only boxes; a box that holds the origin is ignored). */
	bool Raycast(const FVector& Origin, const FVector& Dir, double MaxDist, FMIRayHit& Out) const;
	/** Nothing ray-solid between (bMovement: nothing that blocks a body; bullet-only boxes do not count). */
	bool LineOfSight(const FVector& A, const FVector& B, bool bMovement = false) const;
	/** Highest real top at (x, z) not above MaxY, or 0. */
	double GroundHeight(double X, double Z, double MaxY = 50.0) const;
	bool OverlapsCylinder(double X, double Z, double Radius, double Y0, double Y1) const;
	/** Moves an upright cylinder (origin at the feet) by Vel * Dt, sliding along walls and stepping up 0.42 m. */
	FMIMoveResult MoveCapsule(FVector& Pos, FVector& Vel, double Dt, double Radius, double Height, bool bAllowStep) const;

	// ---- nav (0.5 m cells, A* with string pulling) ----
	/** ClearCost > 0 (the Story guide's private copy only): every step onto a cell within 1 m of a blocked cell costs that much
	 *  more (twice for the next ring in), so the route keeps to open ground and takes a gap of one or two cells (a van and a
	 *  hoarding a body's width apart, with the art wider than the colliders) only when nothing roomier leads there. The Goons
	 *  never pass it: their path, and so every golden replay, is the plain search. */
	bool FindPath(const FVector& A, const FVector& B, TArray<FVector>& Out, double ClearCost = 0.0);
	bool IsWalkable(double X, double Z);
	bool ClearLine(const FVector& A, const FVector& B);
	/** A random walkable point within Radius of Center in the same connected area. */
	bool RandomPoint(const FVector& Center, double Radius, FVector& Out);
	/** The point itself when walkable, else the centre of the nearest free cell within MaxR. */
	bool NearestWalkable(double X, double Z, double MaxR, FVector& Out);
	int32 NavCols() { EnsureNav(); return Cols; }
	int32 NavRows() { EnsureNav(); return Rows; }
	bool NavBlocked(int32 I, int32 J) { EnsureNav(); return Blocked[J * Cols + I] != 0; }

private:
	struct FRay
	{
		double O[3];
		double D[3];
		double Reach;
	};
	bool Cast(const FRay& R, bool bAny, uint8 Skip, double& OutDist, int32& OutIndex, int32& OutAxis) const;
	bool BlocksNav(const FMIBox& B) const;
	void EnsureNav() { if (bNavDirty) { RebuildNav(); } }
	void RebuildNav();
	int32 CellAt(double X, double Z) const;
	int32 NearestFree(double X, double Z, int32 MaxRings, int32 InRegion) const;
	bool LineFree(double X0, double Z0, double X1, double Z1) const;
	bool CellBlocked(int32 I, int32 J) const { return I < 0 || J < 0 || I >= Cols || J >= Rows || Blocked[J * Cols + I] == 1; }
	double CentreX(int32 Cell) const { return OriginX + ((Cell % Cols) + 0.5) * NavCell; }
	double CentreZ(int32 Cell) const { return OriginZ + ((Cell / Cols) + 0.5) * NavCell; }
	int32 Search(int32 Start, int32 Goal);
	bool Before(int32 A, int32 B) const { return FCost[A] < FCost[B] || (FCost[A] == FCost[B] && GCost[A] > GCost[B]); }
	void SiftUp(int32 I);
	void SiftDown(int32 I);
	int32 HeapPop();
	void ScanColumn(double X, double Z, double Radius, double StepTop, double Head, double& Floor, double& Ceiling, int32& FloorIndex) const;
	bool KeepInside(FVector& Pos, FVector& Vel, double Radius) const;

	static constexpr double NavCell = 0.5;
	static constexpr double NavInflate = 0.5;
	static constexpr double NavBandMin = 0.47;
	static constexpr double NavBandMax = 1.5;
	static constexpr int32 NavSnapRings = 12;
	static constexpr int32 NavMinExpansions = 9000;
	static constexpr int32 NavRandomTries = 24;
	static constexpr double NavHScale = 1.001;

	TArray<FMIBox> Boxes;
	FMIBounds Bounds;
	uint32 Revision = 0;
	FMIRng NavRng;

	bool bNavDirty = true;
	int32 Cols = 0, Rows = 0;
	double OriginX = 0.0, OriginZ = 0.0;
	TArray<uint8> Blocked;
	TArray<int32> Region;
	TArray<double> GCost, FCost;
	TArray<int32> Parent, Heap, HeapPos, PathBuf;
	TArray<uint32> Seen, Closed;
	int32 HeapSize = 0;
	uint32 SearchId = 0;
	int32 ExpansionCap = NavMinExpansions;
	int32 Offsets[8] = {};
	TArray<uint8> Tight;
	double TightCost = 0.0;
	void BuildTight();
};
