#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "MIEvents.generated.h"

/**
 * The game's event bus: one native multicast delegate per web event (spec 01 2.16, spec 02 2.11). Rules emit into
 * an FMIGameEvents they are handed (the world's, or a test's own), the HUD, audio, effects and flow listen.
 * Payloads are in Unreal units (cm, degrees).
 */

UENUM()
enum class EMIDamageKind : uint8
{
	Bullet,
	Bolt,
	Melee,
	Blast,
	Fall
};

/** Who dealt the damage: decides what an explosive takes (a fixed amount from enemy rounds) and the HUD arc. */
UENUM()
enum class EMIDamageSource : uint8
{
	Player,
	Enemy,
	Blast,
	World
};

struct FMIShotFiredEvent
{
	FName Weapon;
	FVector Muzzle = FVector::ZeroVector;
	FVector Direction = FVector::ForwardVector;
	double Ads = 0.0;
};

struct FMIReloadEvent
{
	FName Weapon;
	FName Phase;  // start, magout, magin, bolt, done, cancel
	bool bEmpty = false;
};

struct FMISwitchEvent
{
	FName From;
	FName To;
	FName Phase;  // holster, draw
};

struct FMIImpactEvent
{
	FVector Point = FVector::ZeroVector;
	FVector Normal = FVector::UpVector;
	FName Surface;
	FVector Direction = FVector::ForwardVector;
	EMIDamageSource From = EMIDamageSource::Player;
	TWeakObjectPtr<AActor> Actor;
};

struct FMIHitEnemyEvent
{
	TWeakObjectPtr<AActor> Target;
	FName Part;  // head, body
	bool bKilled = false;
	double Damage = 0.0;
	FName Weapon;  // chopper, nine, melee
};

struct FMIExplosionEvent
{
	FVector Position = FVector::ZeroVector;
	double Radius = 0.0;  // cm
	bool bBig = true;
	const void* Source = nullptr;  // the explosive that blew, if any
};

struct FMIPlayerStepEvent
{
	FVector Position = FVector::ZeroVector;
	FName Surface;
	bool bSprint = false;
};

struct FMIPlayerLandEvent
{
	double Speed = 0.0;  // cm/s, fastest descent of the fall
	FName Surface;
};

struct FMIPlayerHitEvent
{
	double Amount = 0.0;
	TOptional<FVector> From;
	double Health = 0.0;
	EMIDamageKind Kind = EMIDamageKind::Bullet;
};

struct FMIGameEvents
{
	TMulticastDelegate<void(const FMIShotFiredEvent&)> WeaponFire;
	TMulticastDelegate<void(FName /*Weapon*/)> WeaponDry;
	TMulticastDelegate<void(const FMIReloadEvent&)> WeaponReload;
	TMulticastDelegate<void(const FMISwitchEvent&)> WeaponSwitch;
	TMulticastDelegate<void(FName /*Weapon*/)> WeaponSwing;
	TMulticastDelegate<void(bool /*bHit*/)> WeaponMelee;
	TMulticastDelegate<void(const FMIImpactEvent&)> Impact;
	TMulticastDelegate<void(const FMIHitEnemyEvent&)> PlayerHitEnemy;
	TMulticastDelegate<void(const FMIExplosionEvent&)> Explosion;
	TMulticastDelegate<void(int32 /*Index*/, const FVector& /*Position*/, double /*Fuse*/)> ExplosiveLit;
	TMulticastDelegate<void(int32 /*Index*/, const FVector& /*Centre*/)> ExplosiveBlast;
	TMulticastDelegate<void(const FMIPlayerStepEvent&)> PlayerStep;
	TMulticastDelegate<void()> PlayerJump;
	TMulticastDelegate<void(const FMIPlayerLandEvent&)> PlayerLand;
	TMulticastDelegate<void(const FMIPlayerHitEvent&)> PlayerHit;
	TMulticastDelegate<void(const TOptional<FVector>& /*From*/)> PlayerDead;
};

/** The world's event bus. */
UCLASS()
class MURDERINC_API UMIEventSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	FMIGameEvents Events;

	/** The bus of the world that owns this object, or null. */
	static FMIGameEvents* Get(const UObject* WorldContextObject);
};
