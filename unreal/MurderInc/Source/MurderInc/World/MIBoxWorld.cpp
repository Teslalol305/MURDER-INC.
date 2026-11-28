#include "World/MIBoxWorld.h"

// A line-for-line port of src/physics.js (rays, sight, floors, the capsule move, the nav grid). Comments that
// explain the rules are in the web file; the order of every floating-point operation is kept so that the golden
// vectors (MurderInc.Golden.World) are met.

namespace
{
	constexpr double LosSlack = 0.05;
	constexpr double SubStep = 0.6;
	constexpr int32 PushIterations = 3;
	constexpr double Footprint = 0.7;
	constexpr uint8 BulletOnly = 1;
	constexpr uint8 PlayerOnly = 2;
	constexpr int32 Ground = -2;
	const int32 DirX[8] = {1, -1, 0, 0, 1, 1, -1, -1};
	const int32 DirZ[8] = {0, 0, 1, -1, 1, -1, 1, -1};
	const FName GroundSurface(TEXT("asphalt"));

	uint8 FlagsOf(const FMIBox& B) { return (B.bBulletOnly ? BulletOnly : 0) | (B.bPlayerOnly ? PlayerOnly : 0); }
}

void FMIBoxWorld::Reset(const FMIBounds& InBounds, const FMIRng& Root)
{
	Boxes.Reset();
	Bounds.MinX = FMath::Min(InBounds.MinX, InBounds.MaxX);
	Bounds.MaxX = FMath::Max(InBounds.MinX, InBounds.MaxX);
	Bounds.MinZ = FMath::Min(InBounds.MinZ, InBounds.MaxZ);
	Bounds.MaxZ = FMath::Max(InBounds.MinZ, InBounds.MaxZ);
	NavRng = Root.Fork(TEXT("nav"));
	Spec = FMINavSpec();
	bNavDirty = true;
	++Revision;
}

void FMIBoxWorld::SetNavSpec(const FMINavSpec& InSpec)
{
	Spec = InSpec.IsMulti() ? InSpec : FMINavSpec();
	bNavDirty = true;
	++Revision;
}

int32 FMIBoxWorld::AddBox(const FMIBox& In)
{
	FMIBox B = In;
	B.Min = FVector(FMath::Min(In.Min.X, In.Max.X), FMath::Min(In.Min.Y, In.Max.Y), FMath::Min(In.Min.Z, In.Max.Z));
	B.Max = FVector(FMath::Max(In.Min.X, In.Max.X), FMath::Max(In.Min.Y, In.Max.Y), FMath::Max(In.Min.Z, In.Max.Z));
	if (B.Surface.IsNone())
	{
		B.Surface = TEXT("concrete");
	}
	if (BlocksNav(B))
	{
		bNavDirty = true;
	}
	++Revision;
	return Boxes.Add(B);
}

void FMIBoxWorld::RemoveIds(const TArray<int32>& Ids)
{
	for (int32 I = Boxes.Num() - 1; I >= 0; --I)
	{
		if (Ids.Contains(Boxes[I].Id))
		{
			if (BlocksNav(Boxes[I]))
			{
				bNavDirty = true;
			}
			Boxes.RemoveAt(I);
			++Revision;
		}
	}
}

void FMIBoxWorld::RemoveOwner(int32 Owner)
{
	const int32 Before = Boxes.Num();
	for (int32 I = Boxes.Num() - 1; I >= 0; --I)
	{
		if (Boxes[I].Owner == Owner)
		{
			if (BlocksNav(Boxes[I]))
			{
				bNavDirty = true;
			}
			Boxes.RemoveAt(I);
		}
	}
	if (Boxes.Num() != Before)
	{
		++Revision;
	}
}

bool FMIBoxWorld::BlocksNav(const FMIBox& B) const
{
	return !B.bNoNav && !B.bBulletOnly && !B.bPlayerOnly && B.Max.Y >= NavBandMin && B.Min.Y <= NavBandMax;
}

// ------------------------------------------------------------------------------------------------------ rays

bool FMIBoxWorld::Cast(const FRay& R, bool bAny, uint8 Skip, double& OutDist, int32& OutIndex, int32& OutAxis) const
{
	const double Ox = R.O[0], Oy = R.O[1], Oz = R.O[2];
	const double Dx = R.D[0], Dy = R.D[1], Dz = R.D[2];
	const double Ix = Dx != 0.0 ? 1.0 / Dx : 0.0;
	const double Iy = Dy != 0.0 ? 1.0 / Dy : 0.0;
	const double Iz = Dz != 0.0 ? 1.0 / Dz : 0.0;
	double Best = R.Reach;
	int32 Index = -1;
	int32 Face = 0;
	for (int32 I = 0; I < Boxes.Num(); ++I)
	{
		const FMIBox& B = Boxes[I];
		if (FlagsOf(B) & Skip)
		{
			continue;
		}
		double TMin = 0.0, TMax = Best, T1, T2;
		int32 Axis = -1;
		const double Lo[3] = {B.Min.X, B.Min.Y, B.Min.Z};
		const double Hi[3] = {B.Max.X, B.Max.Y, B.Max.Z};
		const double O[3] = {Ox, Oy, Oz};
		const double D[3] = {Dx, Dy, Dz};
		const double Inv[3] = {Ix, Iy, Iz};
		bool bMiss = false;
		for (int32 A = 0; A < 3 && !bMiss; ++A)
		{
			if (D[A] != 0.0)
			{
				T1 = (Lo[A] - O[A]) * Inv[A];
				T2 = (Hi[A] - O[A]) * Inv[A];
				if (T1 > T2)
				{
					Swap(T1, T2);
				}
				if (T1 >= TMin)
				{
					TMin = T1;
					Axis = A;
				}
				if (T2 < TMax)
				{
					TMax = T2;
				}
				if (TMin > TMax)
				{
					bMiss = true;
				}
			}
			else if (O[A] < Lo[A] || O[A] > Hi[A])
			{
				bMiss = true;
			}
		}
		if (bMiss || Axis < 0 || TMin >= Best)
		{
			continue;
		}
		Best = TMin;
		Index = I;
		Face = Axis;
		if (bAny)
		{
			break;
		}
	}
	if (Dy < 0.0 && Oy >= 0.0 && !(bAny && Index != -1))
	{
		const double T = -Oy / Dy;
		if (T < Best)
		{
			Best = T;
			Index = Ground;
			Face = 1;
		}
	}
	OutDist = Best;
	OutIndex = Index;
	OutAxis = Face;
	return Index != -1;
}

bool FMIBoxWorld::Raycast(const FVector& Origin, const FVector& Dir, double MaxDist, FMIRayHit& Out) const
{
	double Dx = Dir.X, Dy = Dir.Y, Dz = Dir.Z;
	const double LenSq = Dx * Dx + Dy * Dy + Dz * Dz;
	if (LenSq == 0.0)
	{
		return false;
	}
	if (FMath::Abs(LenSq - 1.0) > 1e-6)
	{
		const double Inv = 1.0 / FMath::Sqrt(LenSq);
		Dx *= Inv;
		Dy *= Inv;
		Dz *= Inv;
	}
	const FRay R{{Origin.X, Origin.Y, Origin.Z}, {Dx, Dy, Dz}, MaxDist};
	double Dist;
	int32 Index, Axis;
	if (!Cast(R, false, PlayerOnly, Dist, Index, Axis))
	{
		return false;
	}
	Out.Dist = Dist;
	Out.Point = FVector(Origin.X + Dx * Dist, Origin.Y + Dy * Dist, Origin.Z + Dz * Dist);
	const double D = Axis == 0 ? Dx : (Axis == 1 ? Dy : Dz);
	Out.Normal = FVector::ZeroVector;
	Out.Normal[Axis] = D > 0.0 ? -1.0 : 1.0;
	Out.Box = Index == Ground ? INDEX_NONE : Index;
	Out.Surface = Index == Ground ? GroundSurface : Boxes[Index].Surface;
	return true;
}

bool FMIBoxWorld::LineOfSight(const FVector& A, const FVector& B, bool bMovement) const
{
	const double Dx = B.X - A.X, Dy = B.Y - A.Y, Dz = B.Z - A.Z;
	const double Len = FMath::Sqrt(Dx * Dx + Dy * Dy + Dz * Dz);
	if (Len <= LosSlack)
	{
		return true;
	}
	const double Inv = 1.0 / Len;
	const FRay R{{A.X, A.Y, A.Z}, {Dx * Inv, Dy * Inv, Dz * Inv}, Len - LosSlack};
	double Dist;
	int32 Index, Axis;
	return !Cast(R, true, bMovement ? BulletOnly : PlayerOnly, Dist, Index, Axis);
}

double FMIBoxWorld::GroundHeight(double X, double Z, double MaxY) const
{
	double H = 0.0;
	for (const FMIBox& B : Boxes)
	{
		if (FlagsOf(B))
		{
			continue;
		}
		const double Top = B.Max.Y;
		if (Top <= H || Top > MaxY)
		{
			continue;
		}
		if (X < B.Min.X || X > B.Max.X || Z < B.Min.Z || Z > B.Max.Z)
		{
			continue;
		}
		H = Top;
	}
	return H;
}

bool FMIBoxWorld::OverlapsCylinder(double X, double Z, double Radius, double Y0, double Y1) const
{
	const double R2 = Radius * Radius;
	for (const FMIBox& B : Boxes)
	{
		if (FlagsOf(B) & BulletOnly)
		{
			continue;
		}
		if (B.Max.Y <= Y0 || B.Min.Y >= Y1)
		{
			continue;
		}
		const double Cx = X < B.Min.X ? B.Min.X : (X > B.Max.X ? B.Max.X : X);
		const double Cz = Z < B.Min.Z ? B.Min.Z : (Z > B.Max.Z ? B.Max.Z : Z);
		if ((X - Cx) * (X - Cx) + (Z - Cz) * (Z - Cz) < R2)
		{
			return true;
		}
	}
	return false;
}

// -------------------------------------------------------------------------------------------------- movement

void FMIBoxWorld::ScanColumn(double X, double Z, double Radius, double StepTop, double Head, double& Floor, double& Ceiling, int32& FloorIndex) const
{
	const double Foot = Footprint * Radius;
	const double R2 = Radius * Radius;
	double FloorY = 0.0;
	double CeilingY = TNumericLimits<double>::Max();
	FloorIndex = Ground;
	for (int32 I = 0; I < Boxes.Num(); ++I)
	{
		const FMIBox& B = Boxes[I];
		if (FlagsOf(B) & BulletOnly)
		{
			continue;
		}
		const double X0 = B.Min.X, X1 = B.Max.X, Z0 = B.Min.Z, Z1 = B.Max.Z, Top = B.Max.Y;
		if (Top <= StepTop)
		{
			if (Top > FloorY && X + Foot > X0 && X - Foot < X1 && Z + Foot > Z0 && Z - Foot < Z1)
			{
				FloorY = Top;
				FloorIndex = I;
			}
		}
		else if (B.Min.Y >= Head - 1e-4 && B.Min.Y < CeilingY)
		{
			const double Dx = X - (X < X0 ? X0 : (X > X1 ? X1 : X));
			const double Dz = Z - (Z < Z0 ? Z0 : (Z > Z1 ? Z1 : Z));
			if (Dx * Dx + Dz * Dz < R2)
			{
				CeilingY = B.Min.Y;
			}
		}
	}
	Floor = FloorY;
	Ceiling = CeilingY;
}

bool FMIBoxWorld::KeepInside(FVector& Pos, FVector& Vel, double Radius) const
{
	bool bMoved = false;
	if (Pos.X < Bounds.MinX + Radius)
	{
		Pos.X = Bounds.MinX + Radius;
		if (Vel.X < 0.0) Vel.X = 0.0;
		bMoved = true;
	}
	else if (Pos.X > Bounds.MaxX - Radius)
	{
		Pos.X = Bounds.MaxX - Radius;
		if (Vel.X > 0.0) Vel.X = 0.0;
		bMoved = true;
	}
	if (Pos.Z < Bounds.MinZ + Radius)
	{
		Pos.Z = Bounds.MinZ + Radius;
		if (Vel.Z < 0.0) Vel.Z = 0.0;
		bMoved = true;
	}
	else if (Pos.Z > Bounds.MaxZ - Radius)
	{
		Pos.Z = Bounds.MaxZ - Radius;
		if (Vel.Z > 0.0) Vel.Z = 0.0;
		bMoved = true;
	}
	return bMoved;
}

FMIMoveResult FMIBoxWorld::MoveCapsule(FVector& Pos, FVector& Vel, double Dt, double Radius, double Height, bool bAllowStep) const
{
	const double StartX = Pos.X, StartZ = Pos.Z, Feet = Pos.Y;
	const double Head = Feet + Height;
	const double StepTop = Feet + (bAllowStep ? StepHeight : AirStep);
	const double R2 = Radius * Radius;
	bool bHitWall = false;

	const double Travel = FMath::Sqrt(Vel.X * Vel.X + Vel.Z * Vel.Z) * Dt;
	const int32 Steps = FMath::Max(1, static_cast<int32>(FMath::CeilToDouble(Travel / (SubStep * Radius))));
	const double H = Dt / Steps;
	for (int32 S = 0; S < Steps; ++S)
	{
		Pos.X += Vel.X * H;
		Pos.Z += Vel.Z * H;
		for (int32 Iter = 0; Iter < PushIterations; ++Iter)
		{
			bool bPushed = KeepInside(Pos, Vel, Radius);
			for (const FMIBox& B : Boxes)
			{
				if (FlagsOf(B) & BulletOnly)
				{
					continue;
				}
				if (B.Max.Y <= StepTop || B.Min.Y >= Head)
				{
					continue;
				}
				const double X0 = B.Min.X, X1 = B.Max.X, Z0 = B.Min.Z, Z1 = B.Max.Z;
				const double Px = Pos.X, Pz = Pos.Z;
				double Nx = Px - (Px < X0 ? X0 : (Px > X1 ? X1 : Px));
				double Nz = Pz - (Pz < Z0 ? Z0 : (Pz > Z1 ? Z1 : Pz));
				const double D2 = Nx * Nx + Nz * Nz;
				if (D2 >= R2)
				{
					continue;
				}
				double Push;
				if (D2 > 1e-12)
				{
					const double D = FMath::Sqrt(D2);
					Nx /= D;
					Nz /= D;
					Push = Radius - D;
				}
				else
				{
					const double Left = Px - X0, Right = X1 - Px, Back = Pz - Z0, Front = Z1 - Pz;
					const double M = FMath::Min(FMath::Min(Left, Right), FMath::Min(Back, Front));
					Nx = M == Left ? -1.0 : (M == Right ? 1.0 : 0.0);
					Nz = Nx != 0.0 ? 0.0 : (M == Back ? -1.0 : 1.0);
					Push = M + Radius;
				}
				Pos.X += Nx * Push;
				Pos.Z += Nz * Push;
				const double Vn = Vel.X * Nx + Vel.Z * Nz;
				if (Vn < 0.0)
				{
					Vel.X -= Vn * Nx;
					Vel.Z -= Vn * Nz;
				}
				bPushed = true;
			}
			if (!bPushed)
			{
				break;
			}
			bHitWall = true;
		}
	}
	if (KeepInside(Pos, Vel, Radius))
	{
		bHitWall = true;
	}

	double Floor, Ceiling;
	int32 FloorIndex;
	ScanColumn(Pos.X, Pos.Z, Radius, StepTop, Head, Floor, Ceiling, FloorIndex);
	if (Floor > Feet && Floor + Height > Ceiling + 1e-4)
	{
		Pos.X = StartX;
		Pos.Z = StartZ;
		Vel.X = 0.0;
		Vel.Z = 0.0;
		bHitWall = true;
		ScanColumn(StartX, StartZ, Radius, StepTop, Head, Floor, Ceiling, FloorIndex);
		if (Floor > Feet && Floor + Height > Ceiling + 1e-4)
		{
			Floor = Feet;
		}
	}

	double Y = Feet + Vel.Y * Dt;
	FMIMoveResult Res;
	if (Vel.Y > 0.0 && Y + Height > Ceiling)
	{
		Y = Ceiling - Height;
		Vel.Y = 0.0;
		Res.bHitCeil = true;
	}
	if (Y <= Floor)
	{
		Y = Floor;
		if (Vel.Y < 0.0) Vel.Y = 0.0;
		Res.bOnGround = true;
	}
	else if (bAllowStep && Vel.Y <= 0.0 && Y - Floor <= StepHeight)
	{
		Y = Floor;
		Vel.Y = 0.0;
		Res.bOnGround = true;
	}
	Pos.Y = Y;
	Res.bHitWall = bHitWall;
	Res.Surface = FloorIndex == Ground ? GroundSurface : Boxes[FloorIndex].Surface;
	return Res;
}

// ------------------------------------------------------------------------------------------------------- nav

void FMIBoxWorld::RebuildNav()
{
	bNavDirty = false;
	OriginX = Bounds.MinX;
	OriginZ = Bounds.MinZ;
	Cols = FMath::Max(3, static_cast<int32>(FMath::CeilToDouble((Bounds.MaxX - Bounds.MinX) / NavCell - 1e-9)));
	Rows = FMath::Max(3, static_cast<int32>(FMath::CeilToDouble((Bounds.MaxZ - Bounds.MinZ) / NavCell - 1e-9)));
	const int32 N = Cols * Rows;
	Blocked.Init(0, N);
	Region.Init(0, N);
	GCost.SetNumZeroed(N);
	FCost.SetNumZeroed(N);
	Parent.SetNumZeroed(N);
	Heap.SetNumZeroed(N);
	HeapPos.SetNumZeroed(N);
	PathBuf.SetNumZeroed(N);
	Seen.Init(0, N);
	Closed.Init(0, N);
	SearchId = 0;
	for (int32 D = 0; D < 8; ++D)
	{
		Offsets[D] = DirZ[D] * Cols + DirX[D];
	}
	ExpansionCap = FMath::Max(NavMinExpansions, N >> 1);
	for (int32 I = 0; I < Cols; ++I)
	{
		Blocked[I] = Blocked[N - Cols + I] = 1;
	}
	for (int32 J = 0; J < Rows; ++J)
	{
		Blocked[J * Cols] = Blocked[J * Cols + Cols - 1] = 1;
	}
	for (const FMIBox& B : Boxes)
	{
		if (!BlocksNav(B))
		{
			continue;
		}
		const int32 I0 = FMath::Max(0, static_cast<int32>(FMath::CeilToDouble((B.Min.X - NavInflate - OriginX) / NavCell - 0.5 - 1e-9)));
		const int32 I1 = FMath::Min(Cols - 1, static_cast<int32>(FMath::FloorToDouble((B.Max.X + NavInflate - OriginX) / NavCell - 0.5 + 1e-9)));
		const int32 J0 = FMath::Max(0, static_cast<int32>(FMath::CeilToDouble((B.Min.Z - NavInflate - OriginZ) / NavCell - 0.5 - 1e-9)));
		const int32 J1 = FMath::Min(Rows - 1, static_cast<int32>(FMath::FloorToDouble((B.Max.Z + NavInflate - OriginZ) / NavCell - 0.5 + 1e-9)));
		for (int32 J = J0; J <= J1; ++J)
		{
			for (int32 I = I0; I <= I1; ++I)
			{
				Blocked[J * Cols + I] = 1;
			}
		}
	}
	FloodRegions(Blocked, Region);
	LayerBlocked.Reset();
	LayerRegion.Reset();
	LayerBlocked.SetNum(NumLayers());
	LayerRegion.SetNum(NumLayers());
	ActiveLayer = 0;
	for (int32 L = 1; L < Spec.Layers.Num(); ++L)
	{
		BuildBoxLayer(Spec.Layers[L], LayerBlocked[L]);
		FloodRegions(LayerBlocked[L], LayerRegion[L]);
	}
}

void FMIBoxWorld::FloodRegions(const TArray<uint8>& Blk, TArray<int32>& Reg)
{
	const int32 N = Cols * Rows;
	Reg.Init(0, N);
	int32 Id = 0;
	for (int32 C = 0; C < N; ++C)
	{
		if (Blk[C] || Reg[C])
		{
			continue;
		}
		++Id;
		int32 Top = 0;
		PathBuf[Top++] = C;
		Reg[C] = Id;
		while (Top > 0)
		{
			const int32 Cur = PathBuf[--Top];
			for (int32 D = 0; D < 4; ++D)
			{
				const int32 Nb = Cur + Offsets[D];
				if (Blk[Nb] || Reg[Nb])
				{
					continue;
				}
				Reg[Nb] = Id;
				PathBuf[Top++] = Nb;
			}
		}
	}
}

bool FMIBoxWorld::BlocksNavAt(const FMIBox& B, double LayerY) const
{
	return !B.bNoNav && !B.bBulletOnly && !B.bPlayerOnly && B.Max.Y >= LayerY + NavBandMin && B.Min.Y <= LayerY + NavBandMax;
}

/** A roof layer (midtown.md 17.3): a cell is walkable when a support top lies within 0.45 of the layer's y at its
 *  centre and nothing that blocks nav spans [y + 0.47, y + 1.5] within 0.5 m of it; cells outside the layer's rect are not. */
void FMIBoxWorld::BuildBoxLayer(const FMINavLayer& L, TArray<uint8>& Blk)
{
	constexpr double SupportBand = 0.45;
	const int32 N = Cols * Rows;
	Blk.Init(1, N);
	TArray<uint8> Support;
	Support.Init(0, N);
	for (const FMIBox& B : Boxes)
	{
		if (B.bBulletOnly || B.bPlayerOnly || FMath::Abs(B.Max.Y - L.Y) > SupportBand)
		{
			continue;
		}
		const int32 I0 = FMath::Max(0, static_cast<int32>(FMath::CeilToDouble((B.Min.X - OriginX) / NavCell - 0.5 - 1e-9)));
		const int32 I1 = FMath::Min(Cols - 1, static_cast<int32>(FMath::FloorToDouble((B.Max.X - OriginX) / NavCell - 0.5 + 1e-9)));
		const int32 J0 = FMath::Max(0, static_cast<int32>(FMath::CeilToDouble((B.Min.Z - OriginZ) / NavCell - 0.5 - 1e-9)));
		const int32 J1 = FMath::Min(Rows - 1, static_cast<int32>(FMath::FloorToDouble((B.Max.Z - OriginZ) / NavCell - 0.5 + 1e-9)));
		for (int32 J = J0; J <= J1; ++J)
		{
			for (int32 I = I0; I <= I1; ++I)
			{
				Support[J * Cols + I] = 1;
			}
		}
	}
	for (int32 J = 1; J < Rows - 1; ++J)
	{
		const double Z = OriginZ + (J + 0.5) * NavCell;
		for (int32 I = 1; I < Cols - 1; ++I)
		{
			const double X = OriginX + (I + 0.5) * NavCell;
			if (Support[J * Cols + I] && X >= L.MinX && X <= L.MaxX && Z >= L.MinZ && Z <= L.MaxZ)
			{
				Blk[J * Cols + I] = 0;
			}
		}
	}
	for (const FMIBox& B : Boxes)
	{
		if (!BlocksNavAt(B, L.Y))
		{
			continue;
		}
		const int32 I0 = FMath::Max(0, static_cast<int32>(FMath::CeilToDouble((B.Min.X - NavInflate - OriginX) / NavCell - 0.5 - 1e-9)));
		const int32 I1 = FMath::Min(Cols - 1, static_cast<int32>(FMath::FloorToDouble((B.Max.X + NavInflate - OriginX) / NavCell - 0.5 + 1e-9)));
		const int32 J0 = FMath::Max(0, static_cast<int32>(FMath::CeilToDouble((B.Min.Z - NavInflate - OriginZ) / NavCell - 0.5 - 1e-9)));
		const int32 J1 = FMath::Min(Rows - 1, static_cast<int32>(FMath::FloorToDouble((B.Max.Z + NavInflate - OriginZ) / NavCell - 0.5 + 1e-9)));
		for (int32 J = J0; J <= J1; ++J)
		{
			for (int32 I = I0; I <= I1; ++I)
			{
				Blk[J * Cols + I] = 1;
			}
		}
	}
}

void FMIBoxWorld::UseLayer(int32 Layer)
{
	EnsureNav();
	if (Layer < 0 || Layer >= LayerBlocked.Num() || Layer == ActiveLayer)
	{
		return;
	}
	Swap(Blocked, LayerBlocked[ActiveLayer]);
	Swap(Region, LayerRegion[ActiveLayer]);
	Swap(Blocked, LayerBlocked[Layer]);
	Swap(Region, LayerRegion[Layer]);
	ActiveLayer = Layer;
}

int32 FMIBoxWorld::LayerForY(double Y) const
{
	int32 Best = 0;
	for (int32 L = 1; L < Spec.Layers.Num(); ++L)
	{
		if (Spec.Layers[L].Y <= Y + 0.5 && Spec.Layers[L].Y >= Spec.Layers[Best].Y)
		{
			Best = L;
		}
	}
	return Best;
}

int32 FMIBoxWorld::LayerAt(const FVector& P)
{
	if (!HasLayers())
	{
		return 0;
	}
	int32 Best = INDEX_NONE;
	for (int32 L = 0; L < Spec.Layers.Num(); ++L)
	{
		if (Spec.Layers[L].Y <= P.Y + 0.5 && (Best == INDEX_NONE || Spec.Layers[L].Y >= Spec.Layers[Best].Y) && IsWalkable(P.X, P.Z, L))
		{
			Best = L;
		}
	}
	return Best == INDEX_NONE ? LayerForY(P.Y) : Best;
}

bool FMIBoxWorld::SameRegion(int32 Layer, const FVector& A, const FVector& B)
{
	UseLayer(Layer);
	const int32 Start = NearestFree(A.X, A.Z, NavSnapRings, 0);
	return Start >= 0 && NearestFree(B.X, B.Z, NavSnapRings, Region[Start]) >= 0;
}

int32 FMIBoxWorld::CellAt(double X, double Z) const
{
	const int32 I = static_cast<int32>(FMath::FloorToDouble((X - OriginX) / NavCell));
	const int32 J = static_cast<int32>(FMath::FloorToDouble((Z - OriginZ) / NavCell));
	return I < 0 || J < 0 || I >= Cols || J >= Rows ? -1 : J * Cols + I;
}

int32 FMIBoxWorld::NearestFree(double X, double Z, int32 MaxRings, int32 InRegion) const
{
	const double Fx = (X - OriginX) / NavCell;
	const double Fz = (Z - OriginZ) / NavCell;
	const int32 Ci = FMath::Clamp(static_cast<int32>(FMath::FloorToDouble(Fx)), 0, Cols - 1);
	const int32 Cj = FMath::Clamp(static_cast<int32>(FMath::FloorToDouble(Fz)), 0, Rows - 1);
	const int32 C = Cj * Cols + Ci;
	if (!Blocked[C] && (!InRegion || Region[C] == InRegion))
	{
		return C;
	}
	int32 Best = -1;
	double BestD = TNumericLimits<double>::Max();
	for (int32 R = 1; R <= MaxRings; ++R)
	{
		if ((R - 0.5) * (R - 0.5) >= BestD)
		{
			break;
		}
		for (int32 J = Cj - R; J <= Cj + R; ++J)
		{
			if (J < 0 || J >= Rows)
			{
				continue;
			}
			const int32 Stride = (J == Cj - R || J == Cj + R) ? 1 : 2 * R;
			for (int32 I = Ci - R; I <= Ci + R; I += Stride)
			{
				if (I < 0 || I >= Cols)
				{
					continue;
				}
				const int32 K = J * Cols + I;
				if (Blocked[K] || (InRegion && Region[K] != InRegion))
				{
					continue;
				}
				const double D = (I + 0.5 - Fx) * (I + 0.5 - Fx) + (J + 0.5 - Fz) * (J + 0.5 - Fz);
				if (D < BestD)
				{
					BestD = D;
					Best = K;
				}
			}
		}
	}
	return BestD <= (MaxRings + 1.0) * (MaxRings + 1.0) ? Best : -1;
}

bool FMIBoxWorld::LineFree(double X0, double Z0, double X1, double Z1) const
{
	const double Gx = (X0 - OriginX) / NavCell;
	const double Gz = (Z0 - OriginZ) / NavCell;
	const double Ex = (X1 - OriginX) / NavCell;
	const double Ez = (Z1 - OriginZ) / NavCell;
	int32 I = static_cast<int32>(FMath::FloorToDouble(Gx));
	int32 J = static_cast<int32>(FMath::FloorToDouble(Gz));
	const int32 IEnd = static_cast<int32>(FMath::FloorToDouble(Ex));
	const int32 JEnd = static_cast<int32>(FMath::FloorToDouble(Ez));
	const double Dx = Ex - Gx;
	const double Dz = Ez - Gz;
	const int32 Si = Dx > 0.0 ? 1 : -1;
	const int32 Sj = Dz > 0.0 ? 1 : -1;
	const double Inf = TNumericLimits<double>::Max();
	const double StepX = Dx != 0.0 ? FMath::Abs(1.0 / Dx) : Inf;
	const double StepZ = Dz != 0.0 ? FMath::Abs(1.0 / Dz) : Inf;
	double Tx = Dx != 0.0 ? (Dx > 0.0 ? I + 1 - Gx : Gx - I) * StepX : Inf;
	double Tz = Dz != 0.0 ? (Dz > 0.0 ? J + 1 - Gz : Gz - J) * StepZ : Inf;
	for (int32 Guard = Cols + Rows + 4; Guard > 0; --Guard)
	{
		if (CellBlocked(I, J))
		{
			return false;
		}
		if ((I == IEnd && J == JEnd) || (Tx > 1.0 && Tz > 1.0))
		{
			return true;
		}
		if (FMath::Abs(Tx - Tz) < 1e-9)
		{
			if (CellBlocked(I + Si, J) || CellBlocked(I, J + Sj))
			{
				return false;
			}
			I += Si;
			J += Sj;
			Tx += StepX;
			Tz += StepZ;
		}
		else if (Tx < Tz)
		{
			I += Si;
			Tx += StepX;
		}
		else
		{
			J += Sj;
			Tz += StepZ;
		}
	}
	return false;
}

void FMIBoxWorld::SiftUp(int32 I)
{
	const int32 Cell = Heap[I];
	while (I > 0)
	{
		const int32 P = (I - 1) >> 1;
		const int32 Up = Heap[P];
		if (!Before(Cell, Up))
		{
			break;
		}
		Heap[I] = Up;
		HeapPos[Up] = I;
		I = P;
	}
	Heap[I] = Cell;
	HeapPos[Cell] = I;
}

void FMIBoxWorld::SiftDown(int32 I)
{
	const int32 Cell = Heap[I];
	for (;;)
	{
		int32 Child = 2 * I + 1;
		if (Child >= HeapSize)
		{
			break;
		}
		if (Child + 1 < HeapSize && Before(Heap[Child + 1], Heap[Child]))
		{
			++Child;
		}
		const int32 Down = Heap[Child];
		if (!Before(Down, Cell))
		{
			break;
		}
		Heap[I] = Down;
		HeapPos[Down] = I;
		I = Child;
	}
	Heap[I] = Cell;
	HeapPos[Cell] = I;
}

int32 FMIBoxWorld::HeapPop()
{
	const int32 Top = Heap[0];
	const int32 Last = Heap[--HeapSize];
	if (HeapSize > 0)
	{
		Heap[0] = Last;
		SiftDown(0);
	}
	return Top;
}

int32 FMIBoxWorld::Search(int32 Start, int32 Goal)
{
	if (++SearchId == 0xffffffffu)
	{
		for (uint32& S : Seen) S = 0;
		for (uint32& S : Closed) S = 0;
		SearchId = 1;
	}
	const int32 GoalX = Goal % Cols;
	const int32 GoalZ = Goal / Cols;
	HeapSize = 0;
	GCost[Start] = 0.0;
	FCost[Start] = 0.0;
	Parent[Start] = -1;
	Seen[Start] = SearchId;
	Heap[HeapSize++] = Start;
	HeapPos[Start] = 0;
	int32 Expansions = 0;
	while (HeapSize > 0)
	{
		const int32 Cur = HeapPop();
		if (Cur == Goal)
		{
			int32 N = 0;
			for (int32 C = Goal; C != -1; C = Parent[C])
			{
				PathBuf[N++] = C;
			}
			for (int32 I = 0, J = N - 1; I < J; ++I, --J)
			{
				Swap(PathBuf[I], PathBuf[J]);
			}
			return N;
		}
		Closed[Cur] = SearchId;
		if (++Expansions > ExpansionCap)
		{
			return 0;
		}
		const int32 Cx = Cur % Cols;
		const int32 Cz = Cur / Cols;
		const double G = GCost[Cur];
		for (int32 D = 0; D < 8; ++D)
		{
			const int32 Nb = Cur + Offsets[D];
			if (Blocked[Nb] || Closed[Nb] == SearchId)
			{
				continue;
			}
			if (D >= 4 && (Blocked[Cur + DirX[D]] || Blocked[Cur + DirZ[D] * Cols]))
			{
				continue;
			}
			const double Ng = G + (D < 4 ? 1.0 : UE_DOUBLE_SQRT_2);
			if (Seen[Nb] == SearchId)
			{
				if (Ng >= GCost[Nb])
				{
					continue;
				}
				FCost[Nb] += Ng - GCost[Nb];
				GCost[Nb] = Ng;
				Parent[Nb] = Cur;
				SiftUp(HeapPos[Nb]);
			}
			else
			{
				const double Ax = FMath::Abs(Cx + DirX[D] - GoalX);
				const double Az = FMath::Abs(Cz + DirZ[D] - GoalZ);
				Seen[Nb] = SearchId;
				GCost[Nb] = Ng;
				FCost[Nb] = Ng + (Ax > Az ? Ax + (UE_DOUBLE_SQRT_2 - 1.0) * Az : Az + (UE_DOUBLE_SQRT_2 - 1.0) * Ax) * NavHScale;
				Parent[Nb] = Cur;
				Heap[HeapSize] = Nb;
				SiftUp(HeapSize++);
			}
		}
	}
	return 0;
}

bool FMIBoxWorld::FindPath(const FVector& A, const FVector& B, TArray<FVector>& Out, int32 Layer)
{
	UseLayer(Layer);
	Out.Reset();
	const int32 Start = NearestFree(A.X, A.Z, NavSnapRings, 0);
	if (Start < 0)
	{
		return false;
	}
	const int32 Goal = NearestFree(B.X, B.Z, NavSnapRings, Region[Start]);
	if (Goal < 0)
	{
		return false;
	}
	int32 Len = 1;
	PathBuf[0] = Start;
	if (Goal != Start)
	{
		Len = Search(Start, Goal);
		if (Len == 0)
		{
			return false;
		}
	}
	const int32 Last = Len - 1;
	const bool bExactStart = CellAt(A.X, A.Z) == Start;
	const bool bExactGoal = CellAt(B.X, B.Z) == Goal;
	const double GoalX = bExactGoal ? B.X : CentreX(Goal);
	const double GoalZ = bExactGoal ? B.Z : CentreZ(Goal);
	double Sx = bExactStart ? A.X : CentreX(Start);
	double Sz = bExactStart ? A.Z : CentreZ(Start);
	Out.Add(FVector(Sx, 0.0, Sz));
	int32 I = 0;
	while (I < Last)
	{
		int32 J = Last;
		const double Fx = Sx, Fz = Sz;
		Sx = GoalX;
		Sz = GoalZ;
		while (J > I + 1 && !LineFree(Fx, Fz, Sx, Sz))
		{
			--J;
			const int32 Cell = PathBuf[J];
			Sx = OriginX + ((Cell % Cols) + 0.5) * NavCell;
			Sz = OriginZ + ((Cell / Cols) + 0.5) * NavCell;
		}
		Out.Add(FVector(Sx, 0.0, Sz));
		I = J;
	}
	if (Last == 0)
	{
		Out.Add(FVector(GoalX, 0.0, GoalZ));
	}
	return true;
}

bool FMIBoxWorld::IsWalkable(double X, double Z, int32 Layer)
{
	UseLayer(Layer);
	const int32 C = CellAt(X, Z);
	return C >= 0 && Blocked[C] == 0;
}

bool FMIBoxWorld::ClearLine(const FVector& A, const FVector& B, int32 Layer)
{
	UseLayer(Layer);
	return LineFree(A.X, A.Z, B.X, B.Z);
}

bool FMIBoxWorld::RandomPoint(const FVector& Center, double Radius, FVector& Out, int32 Layer)
{
	UseLayer(Layer);
	const int32 Home = NearestFree(Center.X, Center.Z, NavSnapRings, 0);
	if (Home < 0)
	{
		return false;
	}
	for (int32 K = 0; K < NavRandomTries; ++K)
	{
		const double Angle = NavRng.Next() * UE_DOUBLE_PI * 2.0;
		const double R = Radius * FMath::Sqrt(NavRng.Next());
		const double X = Center.X + FMath::Cos(Angle) * R;
		const double Z = Center.Z + FMath::Sin(Angle) * R;
		const int32 C = CellAt(X, Z);
		if (C >= 0 && !Blocked[C] && Region[C] == Region[Home])
		{
			Out = FVector(X, 0.0, Z);
			return true;
		}
	}
	return false;
}

bool FMIBoxWorld::NearestWalkable(double X, double Z, double MaxR, FVector& Out, int32 Layer)
{
	UseLayer(Layer);
	const int32 C = CellAt(X, Z);
	if (C >= 0 && !Blocked[C])
	{
		Out = FVector(X, 0.0, Z);
		return true;
	}
	const int32 K = NearestFree(X, Z, static_cast<int32>(FMath::CeilToDouble(MaxR / NavCell)) + 1, 0);
	if (K < 0)
	{
		return false;
	}
	const double Px = CentreX(K), Pz = CentreZ(K);
	if ((Px - X) * (Px - X) + (Pz - Z) * (Pz - Z) <= MaxR * MaxR)
	{
		Out = FVector(Px, 0.0, Pz);
		return true;
	}
	return false;
}
