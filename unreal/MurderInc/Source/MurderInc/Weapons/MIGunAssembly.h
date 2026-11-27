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
	/** The world transform of a fitted part's socket for a viewmodel marker (support: a grip's SupportHand); false when no
	 *  fitted part carries it. */
	bool MarkerTransform(FName Marker, FTransform& Out) const;
	/** The laser's beam origin and direction in world space (the Beam socket, else the muzzle line); false without one. */
	bool BeamWorld(FVector& OutStart, FVector& OutDir) const;
	/** The same assembly in steps (the Loadout's gun swap did a gun's worth of component work in one 6 to 10 ms tick, SMOOTH.md v7):
	 *  BeginStaged does the base mesh, StepStaged adds up to PartsPerStep parts a call and the factory magazine last, and returns
	 *  true once the gun is complete. Assemble is the three in one go. */
	void BeginStaged(USkinnedMeshComponent* InBase, const FMIResolvedGun& Gun, bool bSetBase, double Slide = 0.0);
	bool StepStaged(int32 PartsPerStep);
	bool IsStaging() const { return bStaging; }
	int32 NumParts() const { return Parts.Num(); }
	/** The fitted part's mesh in a slot (the magazine the first-person rig shows and hides), or null. */
	UStaticMeshComponent* PartMesh(FName Slot) const;
	/** Shows or hides every magazine top round (first person: no round in the magazine, no round on top of it). */
	void SetTopRoundsVisible(bool bVisible);
	/** The factory magazine drawn on the stage (bSetBase) when no magazine part is fitted, or null. */
	UStaticMeshComponent* GetFactoryMagazine() const { return FactoryMagazine.Get(); }
	const FString& GetBaseMesh() const { return BaseMesh; }

	/** A bone's reference pose in the mesh's own space (the frame the gun was modelled in). The importer gives every bone
	 *  of an exported skeleton the turn of the glTF axes, so a part snapped to a bone socket is turned back by the
	 *  inverse of this rotation (docs/unreal/ANIMATION.md 3: a magazine on its bone stuck out sideways). */
	static bool BoneRestInMesh(const USkinnedMeshComponent* Base, FName Bone, FTransform& Out);
	/** True when Name is a bone of the base mesh's skeleton and no socket of that name shadows it. */
	static bool IsBoneSocket(const USkinnedMeshComponent* Base, FName Name);

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

	void AddTopRound(UStaticMeshComponent* Magazine, const FString& Path);
	bool AssembleBegin(USkinnedMeshComponent* InBase, const FMIResolvedGun& Gun, bool bSetBase);
	void AssemblePart(const FMIResolvedPart& R, const TSet<FName>& Before, double Slide);
	void AssembleEnd(const FMIResolvedGun& Gun, bool bSetBase);

	FMIResolvedGun StagedGun;
	TSet<FName> StagedBefore;
	int32 StagedIndex = 0;
	double StagedSlide = 0.0;
	bool bStagedSetBase = false;
	bool bStaging = false;

	TArray<FPart> Parts;
	TArray<FName> Hidden;
	TWeakObjectPtr<UStaticMeshComponent> FactoryMagazine;  // the factory magazine the stage shows when no magazine part is fitted
	TArray<TWeakObjectPtr<UStaticMeshComponent>> TopRounds;
	FString BaseMesh;
	TMap<FName, FVector> MarkerFallback;  // web markers in the base mesh's space (when the mesh has no socket)
	FName LaserSlot;
};
