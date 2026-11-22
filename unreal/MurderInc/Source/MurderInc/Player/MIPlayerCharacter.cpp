#include "Player/MIPlayerCharacter.h"

#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "MurderInc.h"

namespace MIPlayerCharacterPrivate
{
	/** Frame-rate independent approach, the web game's damp(): 1 - e^(-rate * dt) of the way per step. */
	float Damp(float Current, float Target, float Rate, float DeltaSeconds)
	{
		return FMath::Lerp(Current, Target, 1.f - FMath::Exp(-Rate * DeltaSeconds));
	}
}

AMIPlayerCharacter::AMIPlayerCharacter()
{
	PrimaryActorTick.bCanEverTick = true;

	FirstPersonCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FirstPersonCamera"));
	FirstPersonCamera->SetupAttachment(GetCapsuleComponent());
	FirstPersonCamera->bUsePawnControlRotation = true;
	// The web game's field-of-view numbers are vertical: make the camera read its value as vertical.
	FirstPersonCamera->bOverrideAspectRatioAxisConstraint = true;
	FirstPersonCamera->SetAspectRatioAxisConstraint(AspectRatio_MaintainYFOV);

	bUseControllerRotationYaw = true;
	bUseControllerRotationPitch = false;
	bUseControllerRotationRoll = false;

	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->NavAgentProps.bCanCrouch = true;
	Movement->bCanWalkOffLedgesWhenCrouching = true;
	Movement->bOrientRotationToMovement = false;
	// Stop at a constant rate (config "accel.groundStop"), as the web game does, instead of friction-based braking.
	Movement->bUseSeparateBrakingFriction = true;
	Movement->BrakingFriction = 0.f;
}

void AMIPlayerCharacter::PostInitializeComponents()
{
	Super::PostInitializeComponents();

	const UWorld* World = GetWorld();
	if (!World || !World->IsGameWorld())
	{
		return;
	}
	const UMIDataSubsystem* Data = UMIDataSubsystem::Get(this);
	if (Data && Data->IsLoaded())
	{
		ApplyTuning(Data->GetPlayer());
	}
	else
	{
		UE_LOG(LogMI, Error, TEXT("Player: no tuning data (Content/Data/config.json not loaded): %s cannot move or look"), *GetNameSafe(this));
	}
}

void AMIPlayerCharacter::ApplyTuning(const FMIPlayerData& Data)
{
	Tuning = Data;
	bHasTuning = true;

	const float HalfHeight = Data.Body.Height * 0.5f;
	const float CrouchHalfHeight = Data.Body.CrouchHeight * 0.5f;
	GetCapsuleComponent()->SetCapsuleSize(Data.Body.Radius, HalfHeight);

	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->SetCrouchedHalfHeight(CrouchHalfHeight);
	Movement->MaxWalkSpeed = Data.Speed.Walk;
	Movement->MaxWalkSpeedCrouched = Data.Speed.Crouch;
	Movement->MaxAcceleration = Data.Accel.Ground;
	Movement->BrakingDecelerationWalking = Data.Accel.GroundStop;
	Movement->BrakingDecelerationFalling = Data.Accel.AirStop;
	Movement->AirControl = Data.Accel.Ground > 0.f ? Data.Accel.Air / Data.Accel.Ground : 0.f;
	Movement->MaxStepHeight = Data.Body.StepHeight;
	Movement->JumpZVelocity = Data.Jump.LaunchSpeed();
	const float WorldGravity = GetWorld() ? FMath::Abs(GetWorld()->GetDefaultGravityZ()) : 0.f;
	Movement->GravityScale = WorldGravity > 0.f ? Data.Jump.Gravity / WorldGravity : 1.f;

	StandEyeOffset = Data.Body.Eye - HalfHeight;
	CrouchEyeOffset = Data.Body.CrouchEye - CrouchHalfHeight;
	CrouchedEyeHeight = CrouchEyeOffset;
	RecalculateBaseEyeHeight();
	CameraHeight = BaseEyeHeight;
	FirstPersonCamera->SetRelativeLocation(FVector(0.f, 0.f, CameraHeight));

	CurrentFov = Data.Fov.Base;
	FirstPersonCamera->SetFieldOfView(CurrentFov);
}

void AMIPlayerCharacter::RecalculateBaseEyeHeight()
{
	// The engine resets this to the class default; ours comes from data.
	BaseEyeHeight = IsCrouched() ? CrouchEyeOffset : StandEyeOffset;
}

void AMIPlayerCharacter::OnStartCrouch(float HalfHeightAdjust, float ScaledHalfHeightAdjust)
{
	Super::OnStartCrouch(HalfHeightAdjust, ScaledHalfHeightAdjust);
	// The capsule centre just dropped by this much: keep the camera where it was and let Tick ease it down.
	CameraHeight += ScaledHalfHeightAdjust;
	FirstPersonCamera->SetRelativeLocation(FVector(0.f, 0.f, CameraHeight));
}

void AMIPlayerCharacter::OnEndCrouch(float HalfHeightAdjust, float ScaledHalfHeightAdjust)
{
	Super::OnEndCrouch(HalfHeightAdjust, ScaledHalfHeightAdjust);
	CameraHeight -= ScaledHalfHeightAdjust;
	FirstPersonCamera->SetRelativeLocation(FVector(0.f, 0.f, CameraHeight));
}

void AMIPlayerCharacter::AddLookInput(const FVector2D& MouseCounts)
{
	if (!Controller || !bHasTuning)
	{
		return;
	}
	const float DegreesPerCount = Tuning.Look.MouseDegreesPerCount;
	FRotator Rotation = Controller->GetControlRotation();
	Rotation.Yaw += MouseCounts.X * DegreesPerCount;
	Rotation.Pitch = FMath::Clamp(FRotator::NormalizeAxis(Rotation.Pitch) + MouseCounts.Y * DegreesPerCount,
		-Tuning.Look.PitchLimit, Tuning.Look.PitchLimit);
	Rotation.Roll = 0.f;
	Controller->SetControlRotation(Rotation);
}

void AMIPlayerCharacter::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bHasTuning)
	{
		return;
	}
	using namespace MIPlayerCharacterPrivate;
	UCharacterMovementComponent* Movement = GetCharacterMovement();

	// Keyboard diagonals arrive as (1, 1): bring the input back onto the unit circle before any rule reads it.
	FVector2D Input = MoveInput;
	if (Input.SizeSquared() > 1.0)
	{
		Input.Normalize();
	}

	// Hold to crouch. The engine refuses to stand up where the standing capsule does not fit.
	if (bCrouchHeld && !IsCrouched())
	{
		Crouch();
	}
	else if (!bCrouchHeld && IsCrouched())
	{
		UnCrouch();
	}

	// Sprint rule of the web game: held, mostly forward, not crouched.
	const bool bSprintWanted = bSprintHeld && !IsCrouched()
		&& Input.Y > Tuning.Sprint.MinForward && FMath::Abs(Input.X) < Tuning.Sprint.MaxStrafe;
	Movement->MaxWalkSpeed = bSprintWanted ? Tuning.Speed.Sprint : Tuning.Speed.Walk;
	if (Movement->IsMovingOnGround())
	{
		bSprinting = bSprintWanted && GetVelocity().Size2D() > Tuning.Sprint.MinSpeedFrac * Tuning.Speed.Walk;
	}
	else
	{
		bSprinting = bSprinting && bSprintWanted;
	}

	if (Controller && !Input.IsNearlyZero())
	{
		AddMovementInput(GetActorForwardVector(), Input.Y);
		AddMovementInput(GetActorRightVector(), Input.X);
	}

	// Camera: eye height eases between the stances, field of view widens while sprinting.
	CameraHeight = Damp(CameraHeight, IsCrouched() ? CrouchEyeOffset : StandEyeOffset, Tuning.Body.EyeRate, DeltaSeconds);
	FirstPersonCamera->SetRelativeLocation(FVector(0.f, 0.f, CameraHeight));

	const float TargetFov = FMath::Clamp(Tuning.Fov.Base + (bSprinting ? Tuning.Fov.SprintAdd : 0.f), Tuning.Fov.Min, Tuning.Fov.Max + Tuning.Fov.SprintAdd);
	CurrentFov = Damp(CurrentFov, TargetFov, Tuning.Fov.Rate, DeltaSeconds);
	FirstPersonCamera->SetFieldOfView(CurrentFov);
}
