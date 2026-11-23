#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MIObjectiveActors.generated.h"

class UPointLightComponent;
class UStaticMeshComponent;

UENUM()
enum class EMIReelCaseState : uint8 { Live, Grabbing, Taken };

/**
 * A master reel case (level.json objectives): its state follows the flow every frame (live, being grabbed with the
 * hold progress, taken). A basic-shape case and a beacon light from presentation.json `objectives.case` until the
 * prop art arrives; the lid, reel and boombox hooks read GetState() / GetProgress(). Blocks nothing (the prop's own
 * collider in level.json does).
 */
UCLASS()
class MURDERINC_API AMIReelCase : public AActor
{
	GENERATED_BODY()

public:
	AMIReelCase();
	void Setup(int32 InIndex, FName InId);
	void Sync(bool bTaken, double Progress);

	int32 GetIndex() const { return Index; }
	FName GetObjectiveId() const { return Id; }
	EMIReelCaseState GetState() const { return State; }
	double GetProgress() const { return Progress; }

private:
	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UStaticMeshComponent> Case;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UPointLightComponent> Beacon;

	int32 Index = INDEX_NONE;
	FName Id;
	EMIReelCaseState State = EMIReelCaseState::Live;
	double Progress = 0.0;
	double BeaconCandela = 400.0;
};

UENUM()
enum class EMITruckState : uint8 { Idle, Open };

/**
 * The IPX truck at the extraction zone (level.json extraction.truck): Idle until every reel is secured, then Open
 * (the rear doors swing). Drawn as basic shapes only in a map without art; in the art map it keeps the state for the
 * truck art. The extraction test itself is the flow's (FMIGameRules).
 */
UCLASS()
class MURDERINC_API AMITruck : public AActor
{
	GENERATED_BODY()

public:
	AMITruck();
	void Setup(bool bDraw);
	void Sync(bool bOpen, double Dt);
	EMITruckState GetState() const { return State; }

private:
	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UStaticMeshComponent> Body;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<USceneComponent> HingeL;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<USceneComponent> HingeR;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UStaticMeshComponent> DoorL;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UStaticMeshComponent> DoorR;

	EMITruckState State = EMITruckState::Idle;
	double Swing = 0.0;  // 0..1
	double OpenDegrees = 100.0;
};
