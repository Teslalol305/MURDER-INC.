#pragma once

#include "CoreMinimal.h"
#include "Core/MIEvents.h"
#include "UObject/Interface.h"
#include "MIDamageable.generated.h"

/** One hit, as every damageable thing receives it (the web game's damage(amount, from, kind) calls). */
struct FMIDamage
{
	double Amount = 0.0;
	EMIDamageKind Kind = EMIDamageKind::Bullet;
	EMIDamageSource Source = EMIDamageSource::Player;
	TOptional<FVector> From;          // the muzzle, the blast centre; unset for a fall
	FVector Point = FVector::ZeroVector;
	FVector Direction = FVector::ForwardVector;
	FName Part = TEXT("body");        // head or body
	FName Weapon;                     // chopper, nine, melee, blast
	TWeakObjectPtr<AActor> Instigator;
};

struct FMIDamageResult
{
	bool bAccepted = false;
	bool bKilled = false;
	double Dealt = 0.0;
};

UINTERFACE(MinimalAPI)
class UMIDamageable : public UInterface
{
	GENERATED_BODY()
};

/**
 * Anything rounds, strikes and blasts can hurt: the player, enemies, explosives, the target dummy.
 * Hit volumes answer to the weapon trace channel (ECC_GameTraceChannel1, "Bullet", Config/DefaultEngine.ini).
 */
class MURDERINC_API IMIDamageable
{
	GENERATED_BODY()

public:
	virtual FMIDamageResult ApplyMIDamage(const FMIDamage& Damage) = 0;

	/** False once dead or gone: traces and blasts skip it. */
	virtual bool IsMIDamageableAlive() const { return true; }

	/** "enemy" (hit markers, statistics), "explosive", "player" or "world". */
	virtual FName GetMIDamageableKind() const { return TEXT("enemy"); }

	/** The point a blast is measured to (web: an enemy's centre, the player's feet + 1.0 m, an explosive's middle). */
	virtual FVector GetMIBlastTarget() const = 0;

	/** Surface name for impact effects (flesh, drone, metal ...). */
	virtual FName GetMISurface() const { return TEXT("flesh"); }
};
