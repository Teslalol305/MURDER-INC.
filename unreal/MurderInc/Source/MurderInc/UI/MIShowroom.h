#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Weapons/MILoadoutResolver.h"
#include "Weapons/MIViewmodel.h"
#include "MIShowroom.generated.h"

class UCameraComponent;
class UMIGunAssembly;
class UPostProcessComponent;
class USpotLightComponent;
class USceneCaptureComponent2D;
class UTextureRenderTarget2D;
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
	/** The Workbench's slot focus, eased in 0.4 s; None: the whole gun. The camera aims at the slot's mount socket on
	 *  the shown mesh (Socket), or at frontend.json stage.cameras.focus.<slot>.offset where the mesh has no such socket
	 *  (template stand-ins, the stock variant); the gun turns that side to the camera and stays whole in the free part
	 *  of the screen, and a spot lights the mount. */
	void FocusSlot(FName Slot, FName Socket = NAME_None);
	/** The arms of a crew member at the eye, holding Gun (Crew screen); a change dips to black for 0.15 s. False (and
	 *  nothing shown) when the member's own arms mesh cannot be loaded: the caller then shows the turntable. */
	bool ShowArms(const FMICrewEntry* Crew, const FMIResolvedGun& Gun);

	/** Where the turntable camera frames: the screen part right of the controls column (normalised device x, -1..1),
	 *  and the vertical half-extent; the whole gun stays inside it. */
	static constexpr double FreeLeft = -0.14, FreeRight = 0.94, FreeHalfHeight = 0.80;
	/** The point the camera aims at (stage space) and the stage-space bounding sphere of the shown gun, for tests. */
	FVector GetAimPoint() const { return AimPoint; }
	FSphere GetGunSphere() const;
	/** The turntable gun with its parts: the gap (cm) between its lowest point and the turntable plate's top (negative:
	 *  something goes into the plate), and how far the gun stands raised so that a long magazine clears the plate. */
	double GetPlateGap() const { return LowestInPivot() - PlateTop; }
	double GetStandLift() const { return StandLift; }
	/** True once the turntable shows a gun mesh (false where the gun's art is not installed). */
	bool HasGunMesh() const;
	static constexpr double PlateClearance = 1.5;  // cm the lowest point of a raised gun stays above the plate

	/** Mouse drag (pixels), wheel steps, right stick (-1..1 per axis), triggers (zoom). */
	void Drag(const FVector2D& Pixels);
	void Zoom(float Steps);
	void Stick(const FVector2D& Value, float ZoomAxis);
	void SetReducedMotion(bool bOn) { bReducedMotion = bOn; }

	/** Draws the current shot once into a tiny target the screen never shows (v6 release pass, H3: the Crew screen's first
	 *  draw was one 70 to 85 ms frame in every cold run; the first draw of the stage's meshes, lights and textures now
	 *  happens behind the title card instead). */
	void DrawOnce();

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
	UPROPERTY(Transient) TObjectPtr<USpotLightComponent> SlotLight;
	UPROPERTY(Transient) TObjectPtr<USceneCaptureComponent2D> WarmCapture;
	UPROPERTY(Transient) TObjectPtr<UTextureRenderTarget2D> WarmTarget;
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
	FName FocusedSlot, FocusSocket;
	FVector SlotLocal = FVector::ZeroVector;  // the focused mount in the turntable's frame (unrotated, unscaled)
	bool bAimSlot = false;                    // turn the gun to the focused mount once its mesh is in place
	FVector AimPoint = FVector::ZeroVector;
	FTransform ArmsGrip = FTransform::Identity;  // the grip in the arms camera's space: the hand is placed on it each frame
	bool FindSlotLocal(FVector& Out) const;
	void PlaceArmsOnGrip();
	FVector GunCentre = FVector::ZeroVector;
	double GunRadius = 40.0;  // cm, the shown gun's bounding sphere: the camera stands off to frame it
	/** The lowest point (cm, z in the turntable's frame without its spin or swap scale) of the gun and every visible
	 *  part on it. */
	double LowestInPivot() const;
	/** The raise that keeps that lowest point PlateClearance above the plate (0 when it already is): an extended
	 *  magazine reaches below the factory one and went into the plate (READY.md W4). */
	double WantedLift() const;
	void ApplyStandLift(double Lift);
	double PlateTop = -14.0;  // the plate's top in the turntable's frame (cm; Setup)
	double StandLift = 0.0;   // cm the gun now stands raised above its centred place
	bool bReducedMotion = false;
};
