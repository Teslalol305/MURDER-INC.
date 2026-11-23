#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Core/Data/MIData.h"
#include "Weapons/MILoadoutResolver.h"
#include "Weapons/MIViewmodel.h"
#include "Weapons/MIWeaponRules.h"
#include "MIWeaponComponent.generated.h"

class AMIPlayerCharacter;
class UCameraComponent;
class UMIFirstPersonRig;
class UMIGunAssembly;
class UMaterialInstanceDynamic;
class UPoseableMeshComponent;
class UStaticMeshComponent;
class USkeletalMeshComponent;

/**
 * The player's guns in the world: hosts FMIWeaponRules (answers its traces with the weapon channel and applies
 * damage through IMIDamageable), poses the first-person gun and arms with FMIViewmodelRig, moves the gun's parts,
 * and draws the placeholder tracers. Stepped by AMIPlayerCharacter after the body has moved (spec 02 3.1); it does
 * not tick on its own.
 */
UCLASS()
class MURDERINC_API UMIWeaponComponent : public UActorComponent, public IMIWeaponHost
{
	GENERATED_BODY()

public:
	UMIWeaponComponent();

	/** Rules, viewmodel and meshes. Called by the character once its tuning is known. */
	void Setup(AMIPlayerCharacter* InPlayer, const FMIConfigData& Config, UCameraComponent* InCamera, UPoseableMeshComponent* InGun, USkeletalMeshComponent* InArms);
	void ResetRun();
	/** The run's set-up (LOADOUT.md 3.7): the resolved guns replace config.json's, and the first-person gun is built
	 *  with UMIGunAssembly from each gun's build. Called by the run reset; the parity set-up is config.json's data. */
	void ApplyRun(const FMIResolvedRun& Run);
	const TArray<FMIResolvedGun>& GetResolvedGuns() const { return Resolved; }

	/** One frame: the rules, then the viewmodel pose, the parts and the tracers. LookDelta: degrees (X right, Y down). */
	void Step(double Dt, const FMIWeaponInput& Input, const FVector2D& LookDelta);

	const FMIWeaponRules& GetRules() const { return Rules; }
	/** Resupply (Hold the Block between waves): rounds onto the reserve, capped. */
	void AddReserve(double Rounds, double Cap) { Rules.AddReserve(Rounds, Cap); }
	FMIWeaponView GetView() const { return Rules.GetView(); }
	const FMIViewmodelRig& GetRig() const { return Rig; }
	bool IsReady() const { return bReady; }

	/** Seconds since the last round or strike that hurt an enemy, and whether it killed (HUD hit marker). */
	double GetSinceHit() const { return SinceHit; }
	bool WasLastHitKill() const { return bLastHitKill; }
	bool WasLastHitHead() const { return bLastHitHead; }

	/** A camera-space point (cm) drawn with the first-person field of view, moved to the world point on the same pixel. */
	FVector FirstPersonToWorld(const FVector& CameraSpace) const;
	/** A camera-space transform of the first-person view as a world transform drawn on the same pixels at the depth the
	 *  first-person pass draws it (the camera's FirstPersonScale): location (s x, s k y, s k z), scale s k, where k is
	 *  the ratio of the world's and the first-person view's half-angle tangents. Flash cards, casings and dropped
	 *  magazines drawn this way sit exactly on the muzzle, port or well, in front of the world as the gun is. */
	FTransform FirstPersonToNearWorld(const FTransform& CameraSpace) const;

	/** The first-person (arms and gun) vertical field of view this frame: the hip value blended by the aim to the
	 *  irons' or the optic's (presentation.json firstPerson.recipe, ANIMATION.md 9). */
	double GetFirstPersonFov(double HipVertical) const;
	/** The inspect key (presentation only: inspect, or the magazine check when the magazine is not full). */
	void RequestInspect();
	/** The character shows or hides the viewmodel: the pack gun and the jewels follow. */
	void SyncVisibility(bool bGun, bool bArms);
	UMIFirstPersonRig* GetFirstPersonRig() const { return FPRig; }

	// IMIWeaponHost
	virtual FMIWeaponPlayerState GetPlayerState() const override;
	virtual void SetPlayerAds(double Ads) override;
	virtual void SetPlayerAimView(double AdsFov, double AdsLook) override;
	virtual void AddRecoil(double PitchDeg, double YawDeg) override;
	virtual void AddShake(double Trauma) override;
	virtual FMIShotResult Hitscan(const FMIShotRequest& Shot) override;
	virtual EMIStrikeResult Melee(const FMIStrikeRequest& Strike) override;
	virtual double ProbeWall(const FVector& Origin, const FVector& Direction, double MaxDistance) override;
	virtual bool AimTarget(const FVector& Origin, const FVector& Direction, double Range) override;
	virtual void OnRoundFired(const FMIShotRequest& Shot, const FMIShotResult& Result, double FlashScale) override;

protected:
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	struct FTracer
	{
		FVector Start;
		FVector End;
		double Age = 0.0;
	};
	struct FPartBone
	{
		int32 Index = INDEX_NONE;
		FTransform Ref;  // component space, reference pose
	};

	void BindEvents();
	void EquipMesh(FName Gun);
	void PoseView();
	void PoseParts();
	void DrawTracers(double Dt);
	void DrawLaser();
	const FMIResolvedGun* ResolvedOf(FName Gun) const { return Resolved.FindByPredicate([Gun](const FMIResolvedGun& G) { return G.Id == Gun; }); }
	void NoteHit(bool bKilled, bool bHead);
	void MuzzleFlash(double FlashScale);
	bool MuzzleCamera(FVector& Pos, FVector& Dir) const;

	UPROPERTY(Transient)
	TObjectPtr<AMIPlayerCharacter> Player;
	UPROPERTY(Transient)
	TObjectPtr<UCameraComponent> Camera;
	UPROPERTY(Transient)
	TObjectPtr<UPoseableMeshComponent> GunMesh;
	UPROPERTY(Transient)
	TObjectPtr<USkeletalMeshComponent> Arms;
	UPROPERTY(Transient)
	TObjectPtr<UMIGunAssembly> Assembly;
	UPROPERTY(Transient)
	TObjectPtr<UMIFirstPersonRig> FPRig;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> FlashCards;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> FlashMids;
	double FlashAge = 1e9, FlashLife = 0.045;
	TArray<FMIResolvedGun> Resolved;
	uint32 Seed = 0;

	FMIWeaponRules Rules;
	FMIViewmodelData ViewData;
	FMIViewmodelRig Rig;
	FMIGameEvents* Events = nullptr;
	TArray<FDelegateHandle> Handles;
	FColor TracerColor = FColor::White;
	double TracerSpeed = 0.0;  // cm/s
	double ViewmodelFov = 0.0;
	TArray<FTracer> Tracers;
	FName MeshFor;
	FPartBone Bolt, Barrel, Trigger, Magazine;
	double SinceHit = 1e30;
	bool bLastHitKill = false;
	bool bLastHitHead = false;
	bool bReady = false;
	bool bHaveView = false;
};
