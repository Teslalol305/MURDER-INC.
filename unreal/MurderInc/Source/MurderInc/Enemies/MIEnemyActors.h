#pragma once

#include "CoreMinimal.h"
#include "Core/MIDamageable.h"
#include "Enemies/MIEnemies.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "MIEnemyActors.generated.h"

class UAnimSequence;
class UBoxComponent;
class UCapsuleComponent;
class UPointLightComponent;
class USkeletalMesh;
class USkeletalMeshComponent;
class USphereComponent;
class UStaticMeshComponent;

/** presentation.json `enemies`: what stands in for the Goon and the Buzzard (soft paths, swapped for the real art). */
struct MURDERINC_API FMIEnemyLook
{
	TArray<FSoftObjectPath> GoonVariants;
	TArray<FSoftObjectPath> GoonVariantsFallback;  // the template mannequins when the Goons are not in the project
	double GoonMeshScale = 1.0;                    // on the real Goons only (CHARACTERS.md: 0.98 for the briefed 1.78 m)
	FSoftClassPath GoonAnimClass;
	double GoonMeshYaw = -90.0;
	FSoftObjectPath GoonWeapon;                    // a static mesh (SM_Weapon_GoonSMG) or a skeletal one (the template)
	FSoftObjectPath GoonWeaponFallback;
	FName GoonWeaponSocket = TEXT("HandGrip_R");
	FName GoonWeaponSocketFallback = TEXT("HandGrip_R");
	FTransform GoonWeaponOffset = FTransform::Identity;  // relative to the weapon socket or bone (static weapon)
	FVector GoonMuzzleOffset = FVector::ZeroVector;       // the muzzle in the static weapon's own frame (cm)
	TOptional<FVector> GoonSupportGrip;                   // the left palm's point in the static weapon's frame (cm)
	FName GoonMuzzleSocket = TEXT("Muzzle");
	TMap<FName, FSoftObjectPath> GoonDeath;  // front, back, left, right
	/** The ragdoll of the death pass (presentation.json enemies.goon.ragdoll): the mannequin skeleton's physics asset and
	 *  the push the killing hit gives, as a change of speed in cm/s (bone: the bone hit; carry: the whole body). */
	struct FRagdoll
	{
		FSoftObjectPath PhysicsAsset;
		double Bone = 330.0, BoneHead = 480.0, Carry = 110.0, CarryHead = 140.0, Blast = 650.0, BlastUp = 320.0, MaxSpeed = 900.0;
		double SettleSpeed = 18.0, SettleFor = 0.5, MinSim = 1.2, MaxSim = 5.0, PoolFade = 2.5;
		double LinearDamping = 0.15, AngularDamping = 0.6;
		double FallPull = 0.0, FallFor = 0.0;  // extra downward cm/s^2 for the first FallFor s: a limp body drops at once instead of holding its stance
		double MaxUp = 250.0;  // cm/s: no part of a falling body rises faster (a blast: 1.5 x BlastUp)
		int32 StartsPerFrame = 2;  // ragdolls started in one frame at most; more deaths in the same frame fall a frame later
	} GoonRagdoll;
	FName HeadBone = TEXT("head");
	FLinearColor GoonLampColour = FLinearColor(1.0f, 0.74f, 0.42f);
	double GoonLampCandela = 60.0, GoonLampRadius = 900.0, GoonLampRise = 30.0, GoonLampFall = 9.0;

	FSoftObjectPath BuzzardBody;
	FVector BuzzardBodySize = FVector(100, 100, 44);
	FSoftObjectPath BuzzardRotor;
	FVector BuzzardRotorSize = FVector(37, 37, 2);
	FLinearColor BuzzardEyeColour = FLinearColor(1.0f, 0.09f, 0.05f);
	double BuzzardEyeCandela = 40.0, BuzzardEyeRadius = 1200.0;
	FSoftObjectPath BuzzardMesh;         // SK_Buzzard (props, gimbal driven); the placeholder shapes when absent
	FSoftObjectPath BuzzardEyeMaterial;  // an unlit additive material with Color / Intensity for the lens
	double BuzzardEyeNits = 4000.0;

	static bool Load(FMIEnemyLook& Out, FString& OutError);
};

/**
 * What an animation layer reads from an enemy (the presentation contract, docs/unreal/GAMEPLAY.md section 7): the
 * rule state and the pose parameters the web solver gets, in Unreal units (cm, cm/s, degrees). Nothing of it is
 * written back into the rules.
 */
struct FMIEnemyView
{
	EMIEnemyMode Mode = EMIEnemyMode::Idle;
	EMIGoonSub Sub = EMIGoonSub::Move;
	bool bAlive = false;
	FVector Velocity = FVector::ZeroVector;  // cm/s
	double Speed = 0.0;                      // cm/s, horizontal
	double YawRate = 0.0;                    // degrees/s
	double Crouch = 0.0, Aim = 0.0;          // 0..1
	double AimYaw = 0.0, AimPitch = 0.0;     // degrees, relative to the body
	double LookYaw = 0.0, LookPitch = 0.0;   // degrees, the head
	int32 RushPhase = 0;                     // 0 none, 1 wind-up, 2 dash, 3 swing, 4 recover
	double RushK = 0.0;
	double Lamp = 0.0;                       // the weapon light or the eye, as drawn (damped)
	double Flash = 0.0;                      // hit flash 0..1
	int32 Variant = 0;
	FVector DeathDirection = FVector::ZeroVector;  // actor space, the killing shot
	// Buzzard
	double RotorSpeed = 0.0, RotorAngle = 0.0, EyeYaw = 0.0, EyePitch = 0.0;
	int32 LostRotor = -1;
	/** The last rule event this unit took part in (telegraph, fire, melee, hit, killed) and how long ago. */
	FMIEnemyEvent::EKind LastEvent = FMIEnemyEvent::EKind::Spawn;
	double SinceEvent = 1e9;
};

/** The Goon's movement component in presentation only: velocity and acceleration as the rules move the unit. */
UCLASS()
class MURDERINC_API UMIGoonMovement : public UCharacterMovementComponent
{
	GENERATED_BODY()

public:
	void Present(const FVector& InVelocity, const FVector& InAcceleration, bool bFalling)
	{
		Velocity = InVelocity;
		Acceleration = InAcceleration;
		MovementMode = bFalling ? MOVE_Falling : MOVE_Walking;
	}
};

/**
 * A Goon as drawn: the rules (FMIEnemyField) move and decide, this actor follows the rule state every frame
 * (UMIGameSubsystem::Sync). The mesh is driven the way the template's shooter NPC is wired (an ACharacter whose
 * movement component reports the rules' velocity, the animation blueprint of presentation.json on the mesh);
 * a death clip by the shot's direction. Hit volumes: a head sphere (tag `head`) and a body capsule placed from the
 * rule state with config.json sizes, on the weapon channel only; nothing else collides.
 */
UCLASS()
class MURDERINC_API AMIGoon : public ACharacter, public IMIDamageable
{
	GENERATED_BODY()

public:
	AMIGoon(const FObjectInitializer& ObjectInitializer);

	void Setup(int32 InSlot, const FMIEnemyLook& Look, const FMIGoonTune& Tune);
	/** Follow the rule state of this frame (web units in E; HeadWeb: the head point the rules use). */
	void Sync(const FMIEnemy& E, const FVector& HeadWeb, double Dt);
	void OnRuleEvent(const FMIEnemyEvent& Event);

	int32 GetSlot() const { return Slot; }
	const FMIEnemyView& GetView() const { return View; }
	UCapsuleComponent* GetBodyHit() const { return BodyHit; }
	/** The body is a ragdoll (fell from its killing hit) / has come to rest and is frozen where it lies. */
	bool IsRagdoll() const { return bRagdoll; }
	bool IsBodySettled() const { return bSettled; }
	/** The death probe's staged test only (MI.Goon.Kill ... at): the drawn body stands at Feet until the next unit takes
	 *  the slot, wherever the rules' unit is (presentation only: a body placed on stairs or by a wall before it falls). */
	void StageBodyAt(const FVector& Feet, double Yaw);
	/** Seconds the last death's ragdoll start took on the game thread (the cost probe). */
	double GetRagdollStartCost() const { return RagdollStartCost; }
	USphereComponent* GetHeadHit() const { return HeadHit; }

	// IMIDamageable
	virtual FMIDamageResult ApplyMIDamage(const FMIDamage& Damage) override;
	virtual bool IsMIDamageableAlive() const override { return View.bAlive; }
	virtual FName GetMIDamageableKind() const override { return TEXT("enemy"); }
	virtual FVector GetMIBlastTarget() const override { return BlastTarget; }
	virtual FName GetMISurface() const override { return TEXT("flesh"); }

private:
	void Show(bool bOn);
	/** The death as drawn: the ragdoll from the killing hit, or (no physics asset) the death clip by direction. */
	void StartDeath(const FMIEnemy& E);
	bool StartRagdoll(const FVector& ShotDir);
	void UpdateRagdoll(double Dt);
	/** Back to a living body for a new unit in this slot (physics off, mesh on its place in the capsule). */
	void ResetBody();

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UCapsuleComponent> BodyHit;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<USphereComponent> HeadHit;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<USkeletalMeshComponent> Gun;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UStaticMeshComponent> GunStatic;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UPointLightComponent> Lamp;

	UPROPERTY(Transient)
	TArray<TObjectPtr<USkeletalMesh>> Variants;

	UPROPERTY(Transient)
	TMap<FName, TObjectPtr<UAnimSequence>> Deaths;

	UPROPERTY(Transient)
	TObjectPtr<UClass> AnimClass;

	UPROPERTY(Transient)
	TObjectPtr<class UPhysicsAsset> Ragdoll;

	/** The killing hit as the damage gave it (ApplyMIDamage): presentation only, never read by the rules. */
	struct FKillHit
	{
		bool bSet = false, bHead = false, bBlast = false;
		FVector Point = FVector::ZeroVector, Dir = FVector::ZeroVector, From = FVector::ZeroVector;
	} KillHit;
	FMIEnemyLook::FRagdoll RagTune;
	FName HeadBone = TEXT("head");
	FVector MeshScale = FVector::OneVector;
	double DeadFor = 0.0, StillFor = 0.0, RagdollStartCost = 0.0;
	int32 Clamps = 0;  // body speeds held back while this body fell (UpdateRagdoll)
	int32 PoolHandle = 0;
	bool bRagdoll = false, bSettled = false, bStaged = false;
	FRotator MeshRotation = FRotator::ZeroRotator;  // the mesh's rest rotation in the actor (presentation goon.meshYaw)
	double AimTurn = 0.0;                            // eased yaw (deg) turning the drawn body onto the rules' aim

	FMIGoonTune Tune;
	FMIEnemyView View;
	FVector BlastTarget = FVector::ZeroVector;
	int32 Slot = INDEX_NONE;
	int32 ShownVariant = -1;
	int32 SpawnId = 0;
	bool bShown = true;
	bool bDying = false;
	double LampCandela = 60.0, LampRise = 30.0, LampFall = 9.0;
};

/**
 * A Buzzard as drawn: a placeholder drone (basic shapes from presentation.json) placed, tilted and spun from the rule
 * state; one box hit volume approximating the 1.0 m x 0.44 m ellipsoid on the weapon channel; a red eye light that
 * follows the rules' lamp.
 */
UCLASS()
class MURDERINC_API AMIBuzzard : public AActor, public IMIDamageable
{
	GENERATED_BODY()

public:
	AMIBuzzard();

	void Setup(int32 InSlot, const FMIEnemyLook& Look, const FMIBuzzardTune& Tune, const FMIBuzzardModel& Model);
	void Sync(const FMIEnemy& E, double Dt);
	void OnRuleEvent(const FMIEnemyEvent& Event);

	int32 GetSlot() const { return Slot; }
	const FMIEnemyView& GetView() const { return View; }

	virtual FMIDamageResult ApplyMIDamage(const FMIDamage& Damage) override;
	virtual bool IsMIDamageableAlive() const override { return View.bAlive; }
	virtual FName GetMIDamageableKind() const override { return TEXT("enemy"); }
	virtual FVector GetMIBlastTarget() const override { return GetActorLocation(); }
	virtual FName GetMISurface() const override { return TEXT("drone"); }

private:
	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<USceneComponent> Root;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UBoxComponent> HitBox;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UStaticMeshComponent> Body;

	UPROPERTY(VisibleAnywhere, Category = "MurderInc")
	TObjectPtr<UPointLightComponent> Eye;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> Rotors;

	/** SK_Buzzard when it is in the project: props spun, the gimbal turned to the rules' eye, the lens lit. */
	UPROPERTY(Transient)
	TObjectPtr<class UPoseableMeshComponent> Drone;
	UPROPERTY(Transient)
	TObjectPtr<class UMaterialInstanceDynamic> EyeMid;
	TArray<FTransform> DroneRef;  // component-space reference pose of the props (fr, fl, rr, rl) and the gimbal
	double EyeNits = 4000.0;

	FMIEnemyView View;
	int32 Slot = INDEX_NONE;
	double EyeCandela = 40.0;
};
