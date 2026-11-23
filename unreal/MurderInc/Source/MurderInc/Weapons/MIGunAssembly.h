#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Weapons/MILoadoutResolver.h"
#include "MIGunAssembly.generated.h"

class USkinnedMeshComponent;
class UStaticMeshComponent;

/**
 * What you see is what you carry (docs/unreal/LOADOUT.md 2.10): one gun built from its build, used by the first-person
 * gun and by the showroom alike. The base mesh is the build's variant (the stock slot picks it); every fitted add-on
 * part is a child mesh at its mount socket; the gun parts a part replaces are hidden (mounts.<slot>.hide); a part's
 * own sockets (SightEye, Muzzle, SupportHand, Beam) replace the viewmodel's markers. A slot whose mount does not exist
 * is never offered, so no fitted part can be invisible. On the Workbench a part slides into its socket.
 */
UCLASS(ClassGroup = (MurderInc))
class MURDERINC_API UMIGunAssembly : public UActorComponent
{
	GENERATED_BODY()

public:
	UMIGunAssembly();

	/** Builds Gun on Base. bSetBase: also load the variant mesh onto Base (the showroom; the first-person gun does it
	 *  itself from the view data). Slide: seconds a newly fitted part takes to slide in (0: at once). */
	void Assemble(USkinnedMeshComponent* Base, const FMIResolvedGun& Gun, bool bSetBase, double Slide = 0.0);
	void Clear();

	/** Marker -> position in the base component's space, for every fitted part whose mesh carries the marker's socket. */
	TMap<FName, FVector> MarkerOverrides() const;
	/** The laser's beam origin and direction in world space (the Beam socket, else the muzzle line); false without one. */
	bool BeamWorld(FVector& OutStart, FVector& OutDir) const;
	int32 NumParts() const { return Parts.Num(); }
	/** The fitted part's mesh in a slot (the magazine the first-person rig shows and hides), or null. */
	UStaticMeshComponent* PartMesh(FName Slot) const;
	const FString& GetBaseMesh() const { return BaseMesh; }

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

private:
	struct FPart
	{
		FMIResolvedPart Data;
		TWeakObjectPtr<UStaticMeshComponent> Mesh;
		FTransform Rest;
		double Age = 1e9;
		double Slide = 0.0;
	};

	UPROPERTY(Transient)
	TObjectPtr<USkinnedMeshComponent> Base;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> Owned;

	TArray<FPart> Parts;
	TArray<FName> Hidden;
	FString BaseMesh;
	TMap<FName, FVector> MarkerFallback;  // web markers in the base mesh's space (when the mesh has no socket)
	FName LaserSlot;
};
