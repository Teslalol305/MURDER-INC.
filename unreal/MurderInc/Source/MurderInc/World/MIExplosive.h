#pragma once

#include "CoreMinimal.h"
#include "Core/MIDamageable.h"
#include "GameFramework/Actor.h"
#include "Weapons/MIExplosiveRules.h"
#include "MIExplosive.generated.h"

class UBoxComponent;
class UStaticMeshComponent;

/**
 * A propane tank or a welding rack (config.json explosives.kinds): a box that blocks pawns and rounds, one item of
 * the world's explosive field (UMICombatSubsystem). Rounds wear it down and light the fuse; it blows when the fuse
 * runs out. The mesh is a grey-box placeholder until the prop art arrives (props.json names it).
 */
UCLASS()
class MURDERINC_API AMIExplosive : public AActor, public IMIDamageable
{
	GENERATED_BODY()

public:
	AMIExplosive();

	/** propane or rack */
	UPROPERTY(EditAnywhere, Category = "MurderInc")
	FName Kind = TEXT("propane");

	virtual FMIDamageResult ApplyMIDamage(const FMIDamage& Damage) override;
	virtual bool IsMIDamageableAlive() const override;
	virtual FName GetMIDamageableKind() const override { return TEXT("explosive"); }
	virtual FVector GetMIBlastTarget() const override;
	virtual FName GetMISurface() const override { return TEXT("metal"); }

	void OnBlown();
	void SyncFromItem(const FMIExplosiveItem& Item);
	int32 GetIndex() const { return Index; }
	UBoxComponent* GetBox() const { return Box; }
	EMIExplosiveState GetState() const { return State; }

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UBoxComponent> Box;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UStaticMeshComponent> Mesh;

	int32 Index = INDEX_NONE;
	EMIExplosiveState State = EMIExplosiveState::Idle;
	double Height = 0.0;
};
