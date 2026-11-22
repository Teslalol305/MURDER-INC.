#pragma once

#include "CoreMinimal.h"
#include "Core/MIDamageable.h"
#include "Subsystems/WorldSubsystem.h"
#include "Weapons/MIExplosiveRules.h"
#include "MICombatSubsystem.generated.h"

class AMIExplosive;

/** The weapon trace channel ("Bullet", Config/DefaultEngine.ini): world geometry and hit shapes block it. */
constexpr ECollisionChannel MIBulletChannel = ECC_GameTraceChannel1;

/**
 * The world's combat services (src/combat.js): the registry of everything that can be hurt, explosions with the
 * linear falloff, cover and the player's share (spec 02 3.13), and the explosives with their fuses and the chain
 * rule (FMIExplosiveField, one item per AMIExplosive).
 */
UCLASS()
class MURDERINC_API UMICombatSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	static UMICombatSubsystem* Get(const UObject* WorldContextObject);

	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;
	virtual bool IsTickable() const override { return bReady; }

	void Register(TScriptInterface<IMIDamageable> Target);
	void Unregister(UObject* Target);

	/** An explosive prop joins the field (Foot: the middle of its base); returns its item index. */
	int32 AddExplosive(AMIExplosive* Actor, FName Kind, const FVector& Foot);
	FMIExplosiveField& GetExplosives() { return Field; }
	const FMIExplosiveKindData* GetExplosiveKind(FName Kind) const { return Data.FindKind(Kind); }

	/**
	 * combat.explode: the explosion event, then every living target in range and in sight takes
	 * Damage x (1 - distance / Radius) (the player x PlayerScale). SourceIndex: the explosive that blew, or INDEX_NONE.
	 */
	void Explode(const FVector& Centre, double Radius, double Damage, int32 SourceIndex, bool bBig = true, AActor* SourceActor = nullptr);

	/** True when nothing on the weapon channel blocks the line (the ends' own actors ignored). */
	bool LineOfSight(const FVector& From, const FVector& To, const AActor* IgnoreA, const AActor* IgnoreB) const;

private:
	bool EnsureData();
	void Blow(int32 Index);

	FMIExplosivesData Data;
	FMIExplosiveField Field;
	TArray<TWeakObjectPtr<AMIExplosive>> ExplosiveActors;
	TArray<TWeakObjectPtr<UObject>> Targets;
	bool bReady = false;
	bool bHaveData = false;
};
