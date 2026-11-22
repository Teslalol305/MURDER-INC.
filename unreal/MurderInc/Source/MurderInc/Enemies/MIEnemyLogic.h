#pragma once

#include "CoreMinimal.h"
#include "Enemies/MIEnemyTune.h"
#include "World/MIBoxWorld.h"
#include "World/MILevelData.h"

/**
 * src/enemies/logic.js in C++: the enemy rules that need no scene (attack tokens, perception, the accuracy ramp,
 * fire-position cost, hit-volume rays, bolt sweeps, flight planning around the El, climbing, push-out, doorways).
 * Web units. Checked by MurderInc.Golden.EnemyLogic and, through the whole AI, MurderInc.Golden.Enemies.
 */
namespace MIEnemy
{
	constexpr double Inf = TNumericLimits<double>::Max();

	enum class EType : uint8 { Goon, Buzzard };

	/** The global counter of ranged attacks (logic.js createTokens). */
	struct FTokens
	{
		int32 Held = 0;
		double LastGrantAt = -Inf;
		int32 LastGrantType = -1;  // EType or -1
		double RefusedAt[2] = {-Inf, -Inf};

		bool Request(EType Type, double Now, int32 Alive, const FMIAiTune& Ai);
		void Release() { if (Held > 0) { --Held; } }
		void Reset() { *this = FTokens(); }
	};

	bool InFov(double Yaw, double Dx, double Dz, double Fov);
	bool InSight(double Dist, double Dx, double Dz, double Yaw, bool bEngaged, const FMIAiTune& Ai);
	inline double SeenStep(double Seen, bool bVisible, double Tick, const FMIAiTune& Ai)
	{
		return bVisible ? Seen + Tick : FMath::Max(0.0, Seen - Ai.SeenDecay * Tick);
	}
	inline double ReactionTime(double Base, bool bPatrol, const FMIAiTune& Ai) { return bPatrol ? Base : Base * Ai.InvestigateReaction; }
	inline double ExposureStep(double Exposure, bool bSees, double Dt, const FMIAiTune& Ai)
	{
		return MI::Clamp01(Exposure + (bSees ? Ai.ExposureUp : -Ai.ExposureDown) * Dt);
	}
	inline double AimSpread(double Far, double Near, double Exposure, double TargetSpeed, double PerSpeed, double Extra = 1.0)
	{
		return (Far + (Near - Far) * MI::Clamp01(Exposure)) * (1.0 + TargetSpeed * PerSpeed) * Extra;
	}

	enum class ECandidate : uint8 { Authored, Random, Arc };
	struct FCandidate
	{
		double X = 0, Z = 0;
		ECandidate Kind = ECandidate::Random;
		bool bSight = false;
		bool bCover = false;
	};
	struct FOther
	{
		double X = 0, Z = 0, DestX = 0, DestZ = 0;
	};
	double FirePositionCost(const FCandidate& C, double SelfX, double SelfZ, double PlayerX, double PlayerZ, const TArray<FOther>& Others, double Jitter, const FMIGoonTune& K);
	inline bool InFireBand(double Dist, const FMIGoonTune& G) { return Dist >= G.RangeMin && Dist <= G.RangeMax; }
	inline double FollowSpeed(double Cap, double Error, double Remaining, const FMIGoonTune& G)
	{
		if (Error > G.TurnInPlace)
		{
			return 0.0;
		}
		return FMath::Min(Cap * (1.0 - 0.5 * Error), 0.4 + 2.6 * Remaining);
	}

	double RaySphere(const FVector& O, const FVector& D, const FVector& C, double Radius);
	double RayCapsule(const FVector& O, const FVector& D, const FVector& A, const FVector& B, double Radius);
	double RayEllipsoid(const FVector& O, const FVector& D, const FVector& C, double Radius, double Half);
	/** Parameter 0..1 along P -> Q of the closest approach to the upright segment, or -1 when it stays outside. */
	double SegmentHitsUpright(const FVector& P, const FVector& Q, double Cx, double Y0, double Y1, double Cz, double Radius);
	FVector LeadPoint(const FVector& S, const FVector& T, const FVector& V, double Speed, double Lead);
	double SegmentEntersRect(double Ax, double Az, double Bx, double Bz, double MinX, double MaxX, double MinZ, double MaxZ);

	/** 0 untouched, 1 capped under, 2 leaving over the top, 3 holding outside to descend. */
	int32 PlanAroundDeck(const FVector& Pos, FVector& Want, const FMIDeck* El, const FMIFlightK& K);

	/** The boxes a drone must stay out of (droneSolid), packed; refilled when the world's box list changes. */
	struct FSolid
	{
		FVector Min, Max;
		bool bPole = false;
		bool bInDeck = false;
		bool bPlayerOnly = false;
		int32 Box = INDEX_NONE;  // index into the world's boxes
	};
	struct FSolids
	{
		TArray<FSolid> List;
		uint32 Revision = MAX_uint32;
		void Refresh(const FMIBoxWorld& World, const FMIDeck* El);
	};
	bool DroneSolid(const FMIBox& Q);
	inline bool IsPole(const FVector& Min, const FVector& Max) { return Max.X - Min.X < 1.0 && Max.Z - Min.Z < 1.0; }

	/** climbOver: raises Want.Y over what lies ahead; HitBox / HitHeight say what decided it. */
	bool ClimbOver(const FSolids& Pack, const FVector& Pos, FVector& Want, const FMIFlightK& K, int32& HitSolid, double& HitHeight);
	double GroundUnder(const FSolids& Pack, const FVector& Pos, double Lift);
	int32 PushOut(const FSolids& Pack, FVector& Pos, FVector& Vel, const FMIFlightK& K, const FMIBounds* Bounds);
	bool DroneOverlaps(const FSolids& Pack, const FVector& Pos, const FMIFlightK& K);
	void DeckEntry(const FVector& Pos, FVector& Want, const FMIDeck& El, const FMIFlightK& K);
	void DeckSlide(const FVector& Pos, FVector& Want, const FSolid& Box, const FMIFlightK& K);
	bool InRoom(const FMIRoom& B, const FVector& P, double M, bool bCheckY);
	/** 0 untouched, 1 heading for the doorway, 2 going through. */
	int32 RouteIndoors(const FVector& Pos, FVector& Want, const FMIRoom& Room);
}
