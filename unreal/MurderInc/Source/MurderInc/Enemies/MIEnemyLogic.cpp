#include "Enemies/MIEnemyLogic.h"

// Line for line from src/enemies/logic.js; the comments explaining each rule are there.

namespace MIEnemy
{
	using MI::Web::AngleDelta;
	using MI::Web::Hypot;

	bool FTokens::Request(EType Type, double Now, int32 Alive, const FMIAiTune& Ai)
	{
		const double SinceGrant = Now - LastGrantAt;
		bool bOk = Held < (Alive > Ai.CrowdAbove ? Ai.TokensCrowd : Ai.Tokens) && SinceGrant >= Ai.TokenGap;
		if (bOk && LastGrantType == static_cast<int32>(Type))
		{
			const int32 Other = Type == EType::Goon ? 1 : 0;
			if (Now - RefusedAt[Other] <= Ai.FairRefusedWithin && SinceGrant < Ai.FairGapFactor * Ai.TokenGap)
			{
				bOk = false;
			}
		}
		if (!bOk)
		{
			RefusedAt[static_cast<int32>(Type)] = Now;
			return false;
		}
		++Held;
		LastGrantAt = Now;
		LastGrantType = static_cast<int32>(Type);
		return true;
	}

	bool InFov(double Yaw, double Dx, double Dz, double Fov)
	{
		const double Len = Hypot(Dx, Dz);
		if (Len < 1e-6)
		{
			return true;
		}
		return (-FMath::Sin(Yaw) * Dx - FMath::Cos(Yaw) * Dz) / Len >= FMath::Cos(Fov * 0.5);
	}

	bool InSight(double Dist, double Dx, double Dz, double Yaw, bool bEngaged, const FMIAiTune& Ai)
	{
		if (!(Dist < Ai.SightRange))
		{
			return false;
		}
		if (bEngaged || Dist <= Ai.CloseRange)
		{
			return true;
		}
		return InFov(Yaw, Dx, Dz, Ai.Fov);
	}

	double FirePositionCost(const FCandidate& C, double SelfX, double SelfZ, double PlayerX, double PlayerZ, const TArray<FOther>& Others, double Jitter, const FMIGoonTune& K)
	{
		constexpr double SameBearing = (30.0 * UE_DOUBLE_PI) / 180.0;
		constexpr double CrowdRadius = 3.0;
		const double KindCost = C.Kind == ECandidate::Authored ? K.CostAuthored : (C.Kind == ECandidate::Random ? K.CostRandom : K.CostArc);
		double Cost = K.CostTravel * Hypot(C.X - SelfX, C.Z - SelfZ) + KindCost + K.CostJitter * Jitter;
		const double Bearing = FMath::Atan2(C.X - PlayerX, C.Z - PlayerZ);
		for (const FOther& O : Others)
		{
			const double Off = FMath::Abs(AngleDelta(Bearing, FMath::Atan2(O.DestX - PlayerX, O.DestZ - PlayerZ)));
			if (Off < SameBearing)
			{
				Cost += K.CostSameBearing * (1.0 - Off / SameBearing);
			}
			if (Hypot(C.X - O.X, C.Z - O.Z) < CrowdRadius || Hypot(C.X - O.DestX, C.Z - O.DestZ) < CrowdRadius)
			{
				Cost += K.CostCrowded;
			}
		}
		if (!C.bSight)
		{
			Cost += K.CostNoSight;
		}
		else if (C.bCover)
		{
			Cost += K.CostCover;
		}
		return Cost;
	}

	double RaySphere(const FVector& O, const FVector& D, const FVector& Cn, double Radius)
	{
		const double Px = O.X - Cn.X, Py = O.Y - Cn.Y, Pz = O.Z - Cn.Z;
		const double C = Px * Px + Py * Py + Pz * Pz - Radius * Radius;
		if (C <= 0.0)
		{
			return 0.0;
		}
		const double B = Px * D.X + Py * D.Y + Pz * D.Z;
		if (B > 0.0)
		{
			return Inf;
		}
		const double Disc = B * B - C;
		return Disc < 0.0 ? Inf : -B - FMath::Sqrt(Disc);
	}

	double RayCapsule(const FVector& O, const FVector& D, const FVector& A, const FVector& Bp, double Radius)
	{
		const double Bax = Bp.X - A.X, Bay = Bp.Y - A.Y, Baz = Bp.Z - A.Z;
		const double Oax = O.X - A.X, Oay = O.Y - A.Y, Oaz = O.Z - A.Z;
		const double Baba = Bax * Bax + Bay * Bay + Baz * Baz;
		const double Bard = Bax * D.X + Bay * D.Y + Baz * D.Z;
		const double Baoa = Bax * Oax + Bay * Oay + Baz * Oaz;
		const double Rdoa = D.X * Oax + D.Y * Oay + D.Z * Oaz;
		const double Oaoa = Oax * Oax + Oay * Oay + Oaz * Oaz;
		const double R2 = Radius * Radius;
		if (Baba < 1e-10)
		{
			return RaySphere(O, D, A, Radius);
		}
		const double S = MI::Clamp01(Baoa / Baba);
		if (Oaoa - 2.0 * S * Baoa + S * S * Baba <= R2)
		{
			return 0.0;
		}
		const double Qa = Baba - Bard * Bard;
		const double Qb = Baba * Rdoa - Baoa * Bard;
		const double Qc = Baba * Oaoa - Baoa * Baoa - R2 * Baba;
		if (Qa > 1e-10)
		{
			const double H = Qb * Qb - Qa * Qc;
			if (H < 0.0)
			{
				return Inf;
			}
			const double T = (-Qb - FMath::Sqrt(H)) / Qa;
			const double Y = Baoa + T * Bard;
			if (Y > 0.0 && Y < Baba)
			{
				return T >= 0.0 ? T : Inf;
			}
			return Y <= 0.0 ? RaySphere(O, D, A, Radius) : RaySphere(O, D, Bp, Radius);
		}
		return FMath::Min(RaySphere(O, D, A, Radius), RaySphere(O, D, Bp, Radius));
	}

	double RayEllipsoid(const FVector& O, const FVector& D, const FVector& Cn, double Radius, double Half)
	{
		const double K = Radius / Half;
		const double Px = O.X - Cn.X, Py = (O.Y - Cn.Y) * K, Pz = O.Z - Cn.Z;
		const double Ey = D.Y * K;
		const double C = Px * Px + Py * Py + Pz * Pz - Radius * Radius;
		if (C <= 0.0)
		{
			return 0.0;
		}
		const double A = D.X * D.X + Ey * Ey + D.Z * D.Z;
		const double B = Px * D.X + Py * Ey + Pz * D.Z;
		if (B > 0.0)
		{
			return Inf;
		}
		const double Disc = B * B - A * C;
		return Disc < 0.0 ? Inf : (-B - FMath::Sqrt(Disc)) / A;
	}

	double SegmentHitsUpright(const FVector& P, const FVector& Q, double Cx, double Y0, double Y1, double Cz, double Radius)
	{
		const double D1x = Q.X - P.X, D1y = Q.Y - P.Y, D1z = Q.Z - P.Z;
		const double D2y = Y1 - Y0;
		const double Rx = P.X - Cx, Ry = P.Y - Y0, Rz = P.Z - Cz;
		const double A = D1x * D1x + D1y * D1y + D1z * D1z;
		const double E = D2y * D2y;
		const double F = D2y * Ry;
		double S, T;
		if (A <= 1e-12)
		{
			S = 0.0;
			T = E > 1e-12 ? MI::Clamp01(F / E) : 0.0;
		}
		else
		{
			const double C = D1x * Rx + D1y * Ry + D1z * Rz;
			if (E <= 1e-12)
			{
				T = 0.0;
				S = MI::Clamp01(-C / A);
			}
			else
			{
				const double B = D1y * D2y;
				const double Denom = A * E - B * B;
				S = Denom > 1e-12 ? MI::Clamp01((B * F - C * E) / Denom) : 0.0;
				T = (B * S + F) / E;
				if (T < 0.0)
				{
					T = 0.0;
					S = MI::Clamp01(-C / A);
				}
				else if (T > 1.0)
				{
					T = 1.0;
					S = MI::Clamp01((B - C) / A);
				}
			}
		}
		const double X = Rx + D1x * S;
		const double Y = Ry + D1y * S - D2y * T;
		const double Z = Rz + D1z * S;
		return X * X + Y * Y + Z * Z <= Radius * Radius ? S : -1.0;
	}

	FVector LeadPoint(const FVector& S, const FVector& T, const FVector& V, double Speed, double Lead)
	{
		const double Flight = Hypot(T.X - S.X, T.Y - S.Y, T.Z - S.Z) / Speed;
		return FVector(T.X + V.X * Flight * Lead, T.Y + V.Y * Flight * Lead, T.Z + V.Z * Flight * Lead);
	}

	double SegmentEntersRect(double Ax, double Az, double Bx, double Bz, double MinX, double MaxX, double MinZ, double MaxZ)
	{
		double T0 = 0.0, T1 = 1.0;
		const double Dx = Bx - Ax, Dz = Bz - Az;
		const double A[2] = {Ax, Az}, D[2] = {Dx, Dz}, Lo[2] = {MinX, MinZ}, Hi[2] = {MaxX, MaxZ};
		for (int32 K = 0; K < 2; ++K)
		{
			if (FMath::Abs(D[K]) < 1e-9)
			{
				if (A[K] < Lo[K] || A[K] > Hi[K])
				{
					return -1.0;
				}
			}
			else
			{
				double U0 = (Lo[K] - A[K]) / D[K];
				double U1 = (Hi[K] - A[K]) / D[K];
				if (U0 > U1)
				{
					Swap(U0, U1);
				}
				if (U0 > T0) T0 = U0;
				if (U1 < T1) T1 = U1;
				if (T0 > T1)
				{
					return -1.0;
				}
			}
		}
		return T0;
	}

	int32 PlanAroundDeck(const FVector& Pos, FVector& Out, const FMIDeck* El, const FMIFlightK& K)
	{
		if (!El)
		{
			return 0;
		}
		const double Px = Pos.X, Py = Pos.Y, Pz = Pos.Z;
		const double M = K.Margin;
		const double MinX = El->MinX - M, MaxX = El->MaxX + M, MinZ = El->MinZ - M, MaxZ = El->MaxZ + M;
		const double LowCap = El->Y - K.Under;
		const double HighFloor = El->Y + K.Thickness + K.Over;
		const bool bSelfIn = Px >= MinX && Px <= MaxX && Pz >= MinZ && Pz <= MaxZ;
		if (bSelfIn)
		{
			if (Py > El->Y)
			{
				if (Out.Y >= HighFloor)
				{
					return 0;
				}
				const double Mid = (El->MinZ + El->MaxZ) * 0.5;
				const bool bWantsOut = Out.Z < MinZ || Out.Z > MaxZ;
				const bool bToMax = bWantsOut ? Out.Z > Mid : Pz > Mid;
				Out.Z = bToMax ? MaxZ + K.Hold + 1.0 : MinZ - K.Hold - 1.0;
				Out.Y = FMath::Max(Py, HighFloor);
				return 2;
			}
			if (Out.Y > LowCap)
			{
				Out.Y = LowCap;
			}
			return 1;
		}
		const double Enter = SegmentEntersRect(Px, Pz, Out.X, Out.Z, MinX, MaxX, MinZ, MaxZ);
		if (Enter < 0.0)
		{
			return 0;
		}
		if (Out.Y >= HighFloor && Py >= HighFloor - 0.5)
		{
			return 0;
		}
		if (Out.Y > LowCap)
		{
			Out.Y = LowCap;
		}
		if (Py <= LowCap + 0.6)
		{
			return 1;
		}
		const double Len = Hypot(Out.X - Px, Out.Z - Pz);
		const double Stop = FMath::Max(0.0, Enter * Len - K.Hold);
		const double Kk = Len > 1e-6 ? Stop / Len : 0.0;
		Out.X = Px + (Out.X - Px) * Kk;
		Out.Z = Pz + (Out.Z - Pz) * Kk;
		return 3;
	}

	bool DroneSolid(const FMIBox& Q)
	{
		static const FName Hoist(TEXT("hoist")), OfficeGlass(TEXT("office-glass"));
		return !Q.bBulletOnly && (!Q.bPlayerOnly || Q.Tag == Hoist || Q.Tag == OfficeGlass);
	}

	void FSolids::Refresh(const FMIBoxWorld& World, const FMIDeck* El)
	{
		if (Revision == World.GetRevision())
		{
			return;
		}
		Revision = World.GetRevision();
		List.Reset();
		const TArray<FMIBox>& Boxes = World.GetBoxes();
		for (int32 I = 0; I < Boxes.Num(); ++I)
		{
			const FMIBox& Q = Boxes[I];
			if (!DroneSolid(Q))
			{
				continue;
			}
			FSolid S;
			S.Min = Q.Min;
			S.Max = Q.Max;
			S.bPole = IsPole(Q.Min, Q.Max);
			const double Cx = (Q.Min.X + Q.Max.X) * 0.5;
			const double Cz = (Q.Min.Z + Q.Max.Z) * 0.5;
			S.bInDeck = El && Cx >= El->MinX && Cx <= El->MaxX && Cz >= El->MinZ && Cz <= El->MaxZ;
			S.bPlayerOnly = Q.bPlayerOnly;
			S.Box = I;
			List.Add(S);
		}
	}

	bool ClimbOver(const FSolids& Pack, const FVector& Pos, FVector& Want, const FMIFlightK& K, int32& HitSolid, double& HitHeight)
	{
		const double X0 = Pos.X, Z0 = Pos.Z;
		double Dx = Want.X - X0, Dz = Want.Z - Z0;
		const double Len = FMath::Sqrt(Dx * Dx + Dz * Dz);
		if (Len > K.ClimbLook)
		{
			const double S = K.ClimbLook / Len;
			Dx *= S;
			Dz *= S;
		}
		const double R = K.Radius;
		const double Above = (Pos.Y > Want.Y ? Pos.Y : Want.Y) + K.HalfHeight + 0.3;
		const double Bottom = Pos.Y - K.HalfHeight;
		const double OverFloor = K.FloorClearance + K.HalfHeight;
		double Best = Want.Y;
		double Raised = 0.0;
		int32 HitAt = -1;
		for (int32 I = 0; I < Pack.List.Num(); ++I)
		{
			const FSolid& S = Pack.List[I];
			const double Top = S.Max.Y;
			const double Need = Top + (Top > Bottom ? K.MinHeight : OverFloor);
			if (Need <= Best || Top > K.MaxAltitude || S.Min.Y > Above || S.bPole || S.bInDeck)
			{
				continue;
			}
			const double MinX = S.Min.X - R, MaxX = S.Max.X + R, MinZ = S.Min.Z - R, MaxZ = S.Max.Z + R;
			double T0 = 0.0, T1 = 1.0;
			bool bMiss = false;
			const double A[2] = {X0, Z0}, D[2] = {Dx, Dz}, Lo[2] = {MinX, MinZ}, Hi[2] = {MaxX, MaxZ};
			for (int32 Ax = 0; Ax < 2 && !bMiss; ++Ax)
			{
				if (FMath::Abs(D[Ax]) < 1e-9)
				{
					bMiss = A[Ax] < Lo[Ax] || A[Ax] > Hi[Ax];
				}
				else
				{
					double U0 = (Lo[Ax] - A[Ax]) / D[Ax];
					double U1 = (Hi[Ax] - A[Ax]) / D[Ax];
					if (U0 > U1)
					{
						Swap(U0, U1);
					}
					if (U0 > T0) T0 = U0;
					if (U1 < T1) T1 = U1;
					bMiss = T0 > T1;
				}
			}
			if (bMiss)
			{
				continue;
			}
			Best = Need;
			Raised = Need;
			HitAt = I;
		}
		HitSolid = HitAt;
		HitHeight = Raised;
		Want.Y = Best;
		return HitAt >= 0;
	}

	double GroundUnder(const FSolids& Pack, const FVector& Pos, double Lift)
	{
		const double MaxY = Pos.Y + Lift;
		double H = 0.0;
		for (const FSolid& S : Pack.List)
		{
			if (S.bPlayerOnly)
			{
				continue;
			}
			const double Top = S.Max.Y;
			if (Top <= H || Top > MaxY)
			{
				continue;
			}
			if (Pos.X < S.Min.X || Pos.X > S.Max.X || Pos.Z < S.Min.Z || Pos.Z > S.Max.Z)
			{
				continue;
			}
			H = Top;
		}
		return H;
	}

	int32 PushOut(const FSolids& Pack, FVector& Pos, FVector& Vel, const FMIFlightK& K, const FMIBounds* Bounds)
	{
		constexpr double OutEps = 0.02;
		const double R = K.Radius, Hh = K.HalfHeight, M = K.BoundsMargin;
		int32 Pushes = 0;
		for (int32 Pass = 0; Pass < 8; ++Pass)
		{
			const bool bUpOnly = Pass >= 3;
			bool bAny = false;
			for (const FSolid& S : Pack.List)
			{
				const double Px = Pos.X, Py = Pos.Y, Pz = Pos.Z;
				if (S.Max.Y <= Py - Hh || S.Min.Y >= Py + Hh)
				{
					continue;
				}
				const double Cx = Px < S.Min.X ? S.Min.X : (Px > S.Max.X ? S.Max.X : Px);
				const double Cz = Pz < S.Min.Z ? S.Min.Z : (Pz > S.Max.Z ? S.Max.Z : Pz);
				if ((Px - Cx) * (Px - Cx) + (Pz - Cz) * (Pz - Cz) >= R * R)
				{
					continue;
				}
				int32 Axis = 1;
				double To = S.Max.Y + Hh + OutEps;
				if (!bUpOnly)
				{
					const bool bPole = S.bPole;
					double Best = bPole ? Inf : To - Py;
					const double Down = S.Min.Y - Hh - OutEps;
					if (!bPole && Py - Down < Best && Down >= K.FloorClearance)
					{
						Best = Py - Down;
						To = Down;
					}
					const double Left = S.Min.X - R - OutEps;
					if (Px - Left < Best && (!Bounds || Left >= Bounds->MinX + M))
					{
						Best = Px - Left;
						Axis = 0;
						To = Left;
					}
					const double Right = S.Max.X + R + OutEps;
					if (Right - Px < Best && (!Bounds || Right <= Bounds->MaxX - M))
					{
						Best = Right - Px;
						Axis = 0;
						To = Right;
					}
					const double Back = S.Min.Z - R - OutEps;
					if (Pz - Back < Best && (!Bounds || Back >= Bounds->MinZ + M))
					{
						Best = Pz - Back;
						Axis = 2;
						To = Back;
					}
					const double Front = S.Max.Z + R + OutEps;
					if (Front - Pz < Best && (!Bounds || Front <= Bounds->MaxZ - M))
					{
						Axis = 2;
						To = Front;
					}
				}
				if (Axis == 0)
				{
					if (To < Px ? Vel.X > 0.0 : Vel.X < 0.0) Vel.X = 0.0;
					Pos.X = To;
				}
				else if (Axis == 2)
				{
					if (To < Pz ? Vel.Z > 0.0 : Vel.Z < 0.0) Vel.Z = 0.0;
					Pos.Z = To;
				}
				else
				{
					if (To < Py ? Vel.Y > 0.0 : Vel.Y < 0.0) Vel.Y = 0.0;
					Pos.Y = To;
				}
				bAny = true;
				++Pushes;
			}
			if (!bAny)
			{
				break;
			}
		}
		return Pushes;
	}

	bool DroneOverlaps(const FSolids& Pack, const FVector& Pos, const FMIFlightK& K)
	{
		for (const FSolid& S : Pack.List)
		{
			if (S.Max.Y <= Pos.Y - K.HalfHeight || S.Min.Y >= Pos.Y + K.HalfHeight)
			{
				continue;
			}
			const double Cx = Pos.X < S.Min.X ? S.Min.X : (Pos.X > S.Max.X ? S.Max.X : Pos.X);
			const double Cz = Pos.Z < S.Min.Z ? S.Min.Z : (Pos.Z > S.Max.Z ? S.Max.Z : Pos.Z);
			if ((Pos.X - Cx) * (Pos.X - Cx) + (Pos.Z - Cz) * (Pos.Z - Cz) < K.Radius * K.Radius)
			{
				return true;
			}
		}
		return false;
	}

	void DeckEntry(const FVector& Pos, FVector& Want, const FMIDeck& El, const FMIFlightK& K)
	{
		Want.X = Pos.X < El.MinX ? El.MinX + 1.0 : (Pos.X > El.MaxX ? El.MaxX - 1.0 : Pos.X);
		Want.Z = Pos.Z < El.MinZ ? El.MinZ + 1.0 : (Pos.Z > El.MaxZ ? El.MaxZ - 1.0 : Pos.Z);
		Want.Y = El.Y - K.Under;
	}

	void DeckSlide(const FVector& Pos, FVector& Want, const FSolid& Box, const FMIFlightK& K)
	{
		Want.X = Pos.X + (Pos.X >= (Box.Min.X + Box.Max.X) * 0.5 ? K.Slide : -K.Slide);
		Want.Z = Pos.Z;
	}

	bool InRoom(const FMIRoom& B, const FVector& P, double M, bool bCheckY)
	{
		return P.X > B.Min.X + M && P.X < B.Max.X - M && P.Z > B.Min.Z + M && P.Z < B.Max.Z - M && (!bCheckY || P.Y < B.Max.Y);
	}

	int32 RouteIndoors(const FVector& Pos, FVector& Want, const FMIRoom& Room)
	{
		constexpr double DoorLevel = 0.35;
		if (!Room.Doorways.Num() || InRoom(Room, Pos, 0.0, true))
		{
			return 0;
		}
		if (!(Want.X > Room.Min.X + 0.2 && Want.X < Room.Max.X - 0.2 && Want.Z > Room.Min.Z + 0.2 && Want.Z < Room.Max.Z - 0.2))
		{
			return 0;
		}
		const FMIDoorway* Best = nullptr;
		double BestCost = Inf;
		for (const FMIDoorway& En : Room.Doorways)
		{
			const double Cost = Hypot(Pos.X - En.Ox, Pos.Z - En.Oz) + Hypot(Want.X - En.Ix, Want.Z - En.Iz);
			if (Cost < BestCost)
			{
				BestCost = Cost;
				Best = &En;
			}
		}
		const double Cx = Best->Ix - Best->Ox, Cz = Best->Iz - Best->Oz;
		const double Len2 = Cx * Cx + Cz * Cz;
		const double U = ((Pos.X - Best->Ox) * Cx + (Pos.Z - Best->Oz) * Cz) / Len2;
		const double Side = FMath::Abs((Pos.X - Best->Ox) * Cz - (Pos.Z - Best->Oz) * Cx) / FMath::Sqrt(Len2);
		const bool bThrough = U > -0.25 && U < 1.2 && Side < 1.0 && FMath::Abs(Pos.Y - Best->Y) < DoorLevel;
		Want.X = bThrough ? Best->Ix : Best->Ox;
		Want.Z = bThrough ? Best->Iz : Best->Oz;
		Want.Y = Best->Y;
		return bThrough ? 2 : 1;
	}
}
