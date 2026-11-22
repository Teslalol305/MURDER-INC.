#pragma once

#include "CoreMinimal.h"
#include "Core/Data/MIData.h"
#include "Core/MIEvents.h"
#include "Core/MIMath.h"

/**
 * The explosives of the web game (src/explosives.js) without the drawing: hit points, fuse, the pop, the chain rule
 * and the blast falloff of src/combat.js explode(). AMIExplosive actors own one item each through the world's
 * UMICombatSubsystem; the automation tests drive a field directly.
 */

enum class EMIExplosiveState : uint8
{
	Idle,
	Lit,
	Gone
};

struct FMIExplosiveItem
{
	FName Kind;
	FVector Foot = FVector::ZeroVector;  // cm
	double Height = 0.0;                 // cm, collider height (the blast centre is at half of it)
	EMIExplosiveState State = EMIExplosiveState::Idle;
	double Hp = 0.0;
	double Fuse = 0.0;
	double FuseTotal = 0.0;
	int32 ChainedBy = 0;
	double JetAngle = 0.0;  // radians: direction of the jet when lit by a blast (from the valve)
	bool bJetAtHole = false;

	FVector Centre() const { return Foot + FVector(0.0, 0.0, Height * 0.5); }
};

namespace MIBlast
{
	/** Linear falloff to zero at the radius; no inner core. Zero at or beyond the radius. */
	inline double Falloff(double Distance, double Radius) { return Distance < Radius && Radius > 0.0 ? 1.0 - Distance / Radius : 0.0; }
}

class MURDERINC_API FMIExplosiveField
{
public:
	void Init(const FMIExplosivesData& InData, uint32 Seed, FMIGameEvents* InEvents);
	void SetEvents(FMIGameEvents* InEvents) { Events = InEvents; }

	int32 Add(FName Kind, const FVector& Foot);
	/** Every item back to full hit points, idle. */
	void Reset();

	/**
	 * A round (Source Player or Enemy) or a blast (Source Blast) reached the item. Rounds wear the hit points down and
	 * light the fuse; an enemy round always does DamageFromEnemyRound. A blast costs no hit points: only the chain
	 * rule of the blast being resolved applies. bStruckByRay: the jet starts at the hole (no random draw).
	 */
	void Damage(int32 Index, double Amount, EMIDamageSource Source, bool bStruckByRay = true);

	/**
	 * Every explosion, from any cause, before its damage is applied (the web game's "explosion" event): lights or
	 * shortens the fuse of every item in chain range, seen or not. SourceIndex: the item that blew, or INDEX_NONE.
	 */
	void OnExplosion(const FVector& Position, double Radius, int32 SourceIndex);

	/**
	 * Runs the fuses in item order. An item whose fuse runs out is handed to BlowItem at once (which calls Blow and
	 * resolves the blast); items after it in the list then run their fuses on the same frame, as in the web game.
	 */
	void Update(double Dt, TFunctionRef<void(int32)> BlowItem);

	/** The item is gone; returns its blast centre. The caller resolves the blast (UMICombatSubsystem::Explode). */
	FVector Blow(int32 Index);

	/** No blast is being resolved any more (called at the start of Update). */
	void EndBlast() { bBlastLive = false; }

	const TArray<FMIExplosiveItem>& GetItems() const { return Items; }
	const FMIExplosiveKindData* KindOf(int32 Index) const;
	const FMIExplosivesData& GetData() const { return Data; }

private:
	void Ignite(int32 Index, double Fuse, bool bStruckByRay);
	void Chain(int32 Index);

	FMIExplosivesData Data;
	FMIGameEvents* Events = nullptr;
	FMIRng Rng;
	TArray<FMIExplosiveItem> Items;

	int32 BlastId = 0;
	bool bBlastLive = false;
	FVector BlastPos = FVector::ZeroVector;
	double BlastRange = 0.0;
	int32 BlastSource = INDEX_NONE;
};
