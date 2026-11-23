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
	FName GoonMuzzleSocket = TEXT("Muzzle");
	TMap<FName, FSoftObjectPath> GoonDeath;  // front, back, left, right
	FName HeadBone = TEXT("head");
	FLinearColor GoonLampColour = FLinearColor(1.0f, 0.74f, 0.42f);
	double GoonLampCandela = 60.0, GoonLampRadius = 900.0, GoonLampRise = 30.0, GoonLampFall = 9.0;

	FSoftObjectPath BuzzardBody;
	FVector BuzzardBodySize = FVector(100, 100, 44);
	FSoftObjectPath BuzzardRotor;
	FVector BuzzardRotorSize = FVector(37, 37, 2);
	FLinearColor BuzzardEyeColour = FLinearColor(1.0f, 0.09f, 0.05f);
	double BuzzardEyeCandela = 40.0, BuzzardEyeRadius = 1200.0;

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
	USphereComponent* GetHeadHit() const { return HeadHit; }

	// IMIDamageable
	virtual FMIDamageResult ApplyMIDamage(const FMIDamage& Damage) override;
	virtual bool IsMIDamageableAlive() const override { return View.bAlive; }
	virtual FName GetMIDamageableKind() const override { return TEXT("enemy"); }
	virtual FVector GetMIBlastTarget() const override { return BlastTarget; }
	virtual FName GetMISurface() const override { return TEXT("flesh"); }

private:
	void Show(bool bOn);

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

	FMIEnemyView View;
	int32 Slot = INDEX_NONE;
	double EyeCandela = 40.0;
};
