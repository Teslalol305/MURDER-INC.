#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Weapons/MILoadoutResolver.h"
#include "Weapons/MIViewmodel.h"
#include "MIShowroom.generated.h"

class UCameraComponent;
class UMIGunAssembly;
class UPostProcessComponent;
class USkeletalMeshComponent;
class UStaticMeshComponent;
struct FMICrewEntry;

/**
 * The 3D stage behind the set-up screens (docs/unreal/LOADOUT.md 2.10, frontend.json stage): a closed room spawned at
 * run time 1 km above the block, so the block's sun, sky light and fog do not reach it; its own lights and a
 * fixed-exposure post volume bounded by the room. Two set-ups: the turntable (Loadout, Workbench), which shows a gun
 * with its build through UMIGunAssembly, and the arms at the first-person eye (Crew), holding the first carried gun.
 * Every value comes from frontend.json stage and is a placeholder for the art pass (engine shapes stand in).
 */
UCLASS()
class MURDERINC_API AMIShowroom : public AActor
{
	GENERATED_BODY()

public:
	AMIShowroom();

	/** Builds the room from frontend.json stage. View: the viewmodel data (arms mesh, hand socket, hip pose). */
	void Setup(const TSharedPtr<FJsonObject>& Frontend, const FMIViewmodelData* View);

	enum class EShot : uint8 { Turntable, Arms };
	void UseShot(EShot Shot);
	EShot GetShot() const { return Shot; }

	/** The turntable gun: swaps with a 0.2 s scale-out and in when the gun changes; new parts slide in. */
	void ShowGun(const FMIResolvedGun& Gun);
	/** The Workbench's slot focus (frontend.json stage.cameras.focus), eased in 0.4 s; None: the whole gun. */
	void FocusSlot(FName Slot);
	/** The arms of a crew member at the eye, holding Gun (Crew screen); a change dips to black for 0.15 s. */
	void ShowArms(const FMICrewEntry* Crew, const FMIResolvedGun& Gun);

	/** Mouse drag (pixels), wheel steps, right stick (-1..1 per axis), triggers (zoom). */
	void Drag(const FVector2D& Pixels);
	void Zoom(float Steps);
	void Stick(const FVector2D& Value, float ZoomAxis);
	void SetReducedMotion(bool bOn) { bReducedMotion = bOn; }

	UCameraComponent* GetActiveCamera() const;
	virtual void Tick(float DeltaSeconds) override;

private:
	void Touch() { SinceTouch = 0.0; }
	void PlaceGunOnPivot();

	UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Root;
	UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Pivot;
	UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Gun;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UMIGunAssembly> Assembly;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UCameraComponent> TurntableCamera;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UCameraComponent> ArmsCamera;
	UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Arms;
	UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> ArmsGun;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UMIGunAssembly> ArmsAssembly;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UPostProcessComponent> Post;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Set;

	const FMIViewmodelData* ViewData = nullptr;
	EShot Shot = EShot::Turntable;
	FName ShownGun;
	FName ShownCrew;
	FMIResolvedGun Pending;
	bool bPendingSwap = false;
	double SwapT = 1.0;
	double ArmsDip = 1.0;
	double Yaw = -30.0, Pitch = 0.0, ZoomK = 1.0;
	double SinceTouch = 1e9;
	double Spin = 18.0, IdleAfter = 3.0, DragK = 0.35, StickK = 120.0, PitchMin = -25.0, PitchMax = 35.0, ZoomMin = 0.65, ZoomMax = 1.6, ZoomStep = 0.1;
	double FocusSecs = 0.4;
	FVector CamFrom = FVector(-110, -20, 115), CamTo = FVector(0, 0, 95);
	double CamFov = 30.0;
	FVector FocusOffset = FVector::ZeroVector, FocusFrom = FVector::ZeroVector, FocusTo = FVector::ZeroVector;
	double FocusZoom = 1.0, FocusZoomFrom = 1.0, FocusZoomTo = 1.0, FocusT = 1.0;
	TSharedPtr<FJsonObject> Focus;
	FVector GunCentre = FVector::ZeroVector;
	double GunRadius = 40.0;  // cm, the shown gun's bounding sphere: the camera stands off to frame it
	bool bReducedMotion = false;
};
