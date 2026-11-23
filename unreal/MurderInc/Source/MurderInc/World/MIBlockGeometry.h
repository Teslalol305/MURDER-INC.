#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MIBlockGeometry.generated.h"

class UBoxComponent;
class UInstancedStaticMeshComponent;
struct FMILevelData;

/**
 * The block's collision at run time, in every map (the grey box and the art map L_Block alike): one box component per
 * level.json collider that no explosive owns (the explosives bring their own), plus the ground slab under the play
 * bounds. Responses follow the collider flags: bullet-only boxes stop rounds and sight but not bodies, player-only
 * boxes (the seal walls) stop bodies and nothing else. In a map without art the boxes are also drawn (one instanced
 * cube mesh); in an art map they stay invisible and the art map's own collision boxes (actors tagged MIBlock) are
 * switched off so that exactly one collision set, the data's, decides.
 */
UCLASS()
class MURDERINC_API AMIBlockGeometry : public AActor
{
	GENERATED_BODY()

public:
	AMIBlockGeometry();

	/** Builds the boxes; bDraw also draws them (grey box). Returns the number of boxes. */
	int32 Build(const FMILevelData& Level, bool bDraw);

	/** True when the world holds level art (an actor carrying presentation.json block.artTag). */
	static bool WorldHasArt(UWorld* World, FName ArtTag);
	/** Turns off the collision of every art actor tagged ArtTag (the data's boxes replace it). */
	static int32 DisableArtCollision(UWorld* World, FName ArtTag);

	int32 NumBoxes() const { return Boxes.Num(); }

private:
	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<USceneComponent> Root;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UInstancedStaticMeshComponent> Grey;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UBoxComponent>> Boxes;
};
