#pragma once

#include "CoreMinimal.h"
#include "Core/MIDamageable.h"
#include "GameFramework/Actor.h"
#include "MITargetDummy.generated.h"

class UCapsuleComponent;
class USphereComponent;
class UStaticMeshComponent;

/**
 * A standing target with a Goon's hit shapes (config.json enemies.goon: body capsule, head sphere, hit points):
 * rounds, strikes and blasts hurt it, a head hit takes the head multiplier. It stands back up at full health after
 * a moment, so the block and the tests can shoot it again. Both shapes answer only to the weapon channel.
 */
UCLASS()
class MURDERINC_API AMITargetDummy : public AActor, public IMIDamageable
{
	GENERATED_BODY()

public:
	AMITargetDummy();

	virtual FMIDamageResult ApplyMIDamage(const FMIDamage& Damage) override;
	virtual bool IsMIDamageableAlive() const override { return Health > 0.0; }
	virtual FName GetMIDamageableKind() const override { return TEXT("enemy"); }
	virtual FVector GetMIBlastTarget() const override;
	virtual FName GetMISurface() const override { return TEXT("flesh"); }
	virtual void Tick(float DeltaSeconds) override;

	/** Seconds before a dropped dummy stands up again; 0 = stays down. */
	UPROPERTY(EditAnywhere, Category = "MurderInc")
	float StandUpAfter = 3.f;

	double GetHealth() const { return Health; }
	double GetMaxHealth() const { return MaxHealth; }
	double GetTotalDamage() const { return TotalDamage; }
	int32 GetHeadHits() const { return HeadHits; }

	/** Reads the Goon's shapes and hit points; called at BeginPlay, public for tests that build a dummy by hand. */
	void ApplyTuning();

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UCapsuleComponent> Body;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<USphereComponent> Head;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UStaticMeshComponent> BodyMesh;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UStaticMeshComponent> HeadMesh;

	double Health = 1.0;
	double MaxHealth = 1.0;
	double TotalDamage = 0.0;
	int32 HeadHits = 0;
	double DownFor = 0.0;
	double BodyHeight = 0.0;  // cm
};
