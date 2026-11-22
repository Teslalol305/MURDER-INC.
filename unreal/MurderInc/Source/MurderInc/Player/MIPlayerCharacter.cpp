#include "Player/MIPlayerCharacter.h"

#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Core/MIEvents.h"
#include "Dom/JsonObject.h"
#include "Engine/GameViewportClient.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "MurderInc.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "Player/MICharacterMovement.h"
#include "Weapons/MICombatSubsystem.h"
#include "Weapons/MIViewmodel.h"
#include "Weapons/MIWeaponComponent.h"

namespace MIPlayerCharacterPrivate
{
	double BlastStanding = 0.0;
	double BlastCrouching = 0.0;
	bool bBlastLoaded = false;

	void LoadRules()
	{
		if (bBlastLoaded)
		{
			return;
		}
		TSharedPtr<FJsonObject> Root;
		FString Error;
		if (UMIDataSubsystem::LoadJsonFile(TEXT("rules.json"), Root, Error))
		{
			const TSharedPtr<FJsonObject> Target = Root->GetObjectField(TEXT("player"))->GetObjectField(TEXT("blastTarget"));
			BlastStanding = Target->GetNumberField(TEXT("standing")) * 100.0;
			BlastCrouching = Target->GetNumberField(TEXT("crouching")) * 100.0;
			bBlastLoaded = true;
		}
		else
		{
			UE_LOG(LogMI, Error, TEXT("Player: rules.json: %s"), *Error);
		}
	}
}

void FMIPlayerLateTick::ExecuteTick(float DeltaTime, ELevelTick TickType, ENamedThreads::Type CurrentThread, const FGraphEventRef& MyCompletionGraphEvent)
{
	if (Target && IsValid(Target) && TickType != LEVELTICK_ViewportsOnly)
	{
		Target->LateTick(DeltaTime);
	}
}

AMIPlayerCharacter::AMIPlayerCharacter(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer.SetDefaultSubobjectClass<UMICharacterMovement>(ACharacter::CharacterMovementComponentName))
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PrePhysics;
	bUseControllerRotationYaw = false;
	bUseControllerRotationPitch = false;
	bUseControllerRotationRoll = false;

	// The player passes through people (spec 01 4.3) and is never hit by his own rounds; enemy rounds use the
	// player's own hit cylinder (enemies package).
	GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
	GetCapsuleComponent()->SetCollisionResponseToChannel(MIBulletChannel, ECR_Ignore);

	FirstPersonCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FirstPersonCamera"));
	FirstPersonCamera->SetupAttachment(GetCapsuleComponent());
	FirstPersonCamera->bUsePawnControlRotation = false;
	FirstPersonCamera->bConstrainAspectRatio = false;
	FirstPersonCamera->bEnableFirstPersonFieldOfView = true;
	FirstPersonCamera->bEnableFirstPersonScale = true;

	// The first-person gun and arms (template mannequin and weapons until the real art; presentation.json).
	GunMesh = CreateDefaultSubobject<UPoseableMeshComponent>(TEXT("FirstPersonGun"));
	GunMesh->SetupAttachment(FirstPersonCamera);
	GunMesh->SetOnlyOwnerSee(true);
	GunMesh->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::FirstPerson);
	GunMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	GunMesh->CastShadow = false;

	ArmsMesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("FirstPersonArms"));
	ArmsMesh->SetupAttachment(FirstPersonCamera);
	ArmsMesh->SetOnlyOwnerSee(true);
	ArmsMesh->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::FirstPerson);
	ArmsMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	ArmsMesh->CastShadow = false;
	ArmsMesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;

	GetMesh()->SetOwnerNoSee(true);
	GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	Weapon = CreateDefaultSubobject<UMIWeaponComponent>(TEXT("Weapon"));
}

void AMIPlayerCharacter::BeginPlay()
{
	Super::BeginPlay();
	Movement = Cast<UMICharacterMovement>(GetCharacterMovement());

	FMIConfigData Config;
	bool bLoaded = false;
	if (const UMIDataSubsystem* Data = UMIDataSubsystem::Get(this); Data && Data->IsLoaded())
	{
		Config = Data->GetConfig();
		bLoaded = true;
	}
	else
	{
		FString Error;
		bLoaded = UMIDataSubsystem::LoadConfig(Config, Error);
		if (!bLoaded)
		{
			UE_LOG(LogMI, Error, TEXT("Player: config.json: %s"), *Error);
		}
	}
	if (bLoaded)
	{
		ApplyTuning(Config);
	}

	// The rules decide before the move; the late tick runs after it.
	if (Movement)
	{
		Movement->PrimaryComponentTick.AddPrerequisite(this, PrimaryActorTick);
	}
	LateTickFunction.Target = this;
	LateTickFunction.TickGroup = TG_PostPhysics;
	LateTickFunction.bCanEverTick = true;
	LateTickFunction.bTickEvenWhenPaused = false;
	LateTickFunction.RegisterTickFunction(GetLevel());
	if (Movement)
	{
		LateTickFunction.AddPrerequisite(Movement, Movement->PrimaryComponentTick);
	}

	if (UMICombatSubsystem* Combat = UMICombatSubsystem::Get(this))
	{
		Combat->Register(this);
	}
	if (FMIGameEvents* Events = UMIEventSubsystem::Get(this))
	{
		Rules.SetEvents(Events);
		Events->Explosion.AddWeakLambda(this, [this](const FMIExplosionEvent& E) { Rules.OnExplosion(E.Position, E.bBig); });
	}
}

void AMIPlayerCharacter::EndPlay(const EEndPlayReason::Type Reason)
{
	LateTickFunction.UnRegisterTickFunction();
	if (UMICombatSubsystem* Combat = UMICombatSubsystem::Get(this))
	{
		Combat->Unregister(this);
	}
	Super::EndPlay(Reason);
}

void AMIPlayerCharacter::ApplyTuning(const FMIConfigData& Config)
{
	MIPlayerCharacterPrivate::LoadRules();
	Tuning = Config;
	const FMIPlayerData& P = Config.Player;
	Rules.Init(P, UMIEventSubsystem::Get(this));

	GetCapsuleComponent()->SetCapsuleSize(P.Body.Radius, P.Body.Height * 0.5);
	if (UCharacterMovementComponent* Move = GetCharacterMovement())
	{
		const double WorldGravity = GetWorld() ? FMath::Abs(GetWorld()->GetDefaultGravityZ()) : 980.0;
		Move->GravityScale = WorldGravity > 0.0 ? P.Jump.Gravity / WorldGravity : 1.0;
		Move->MaxStepHeight = P.Body.StepHeight;
		Move->SetCrouchedHalfHeight(P.Body.CrouchHeight * 0.5);
		Move->NavAgentProps.bCanCrouch = true;
		Move->NavAgentProps.bCanJump = true;
		Move->bCanWalkOffLedgesWhenCrouching = true;
		Move->PerchRadiusThreshold = P.Body.Radius * (1.0 - P.Body.Footprint);
		Move->bOrientRotationToMovement = false;
		Move->MaxAcceleration = 0.f;  // the rules own the velocity (UMICharacterMovement::CalcVelocity)
	}
	JumpMaxCount = 1;
	JumpMaxHoldTime = 0.f;

	if (Weapon)
	{
		Weapon->Setup(this, Config, FirstPersonCamera, GunMesh, ArmsMesh);
	}
	FMIViewmodelData View;
	FString Error;
	if (FMIViewmodelData::Load(View, Error))
	{
		FirstPersonCamera->SetFirstPersonScale(View.FirstPersonScale);
		if (USkeletalMesh* Body = Cast<USkeletalMesh>(View.Body.TryLoad()))
		{
			ArmsMesh->SetSkinnedAssetAndUpdate(Body, true);
		}
	}
	bHasTuning = true;
	ResetRun();
}

void AMIPlayerCharacter::ResetRun()
{
	if (!bHasTuning)
	{
		return;
	}
	Rules.Reset(GetFeet(), GetActorRotation().Yaw);
	if (const FMIDifficultyData* D = Tuning.FindDifficulty(Tuning.DefaultDifficulty))
	{
		Rules.RegenDelay = D->RegenDelay;
		Rules.RegenRate = D->RegenRate;
	}
	if (Weapon)
	{
		Weapon->ResetRun();
	}
	bDeathCapsule = false;
	GetCapsuleComponent()->SetCapsuleSize(Tuning.Player.Body.Radius, Tuning.Player.Body.Height * 0.5);
	PlaceCamera();
}

FVector AMIPlayerCharacter::GetFeet() const
{
	return GetActorLocation() - FVector(0, 0, GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
}

bool AMIPlayerCharacter::CanStand() const
{
	const UWorld* World = GetWorld();
	if (!World)
	{
		return true;
	}
	const FMIPlayerBodyData& B = Tuning.Player.Body;
	const double Radius = B.Radius * B.Footprint;
	const double Lift = B.StandClearance;
	const double Half = FMath::Max(Radius, (B.Height - Lift) * 0.5);
	const FVector Centre = GetFeet() + FVector(0, 0, Lift + Half);
	FCollisionQueryParams Params(SCENE_QUERY_STAT(MIHeadroom), false, this);
	return !World->OverlapBlockingTestByChannel(Centre, FQuat::Identity, ECC_Pawn, FCollisionShape::MakeCapsule(Radius, Half), Params);
}

void AMIPlayerCharacter::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bHasTuning || !Movement)
	{
		return;
	}
	// The rules' view of the body is the capsule's.
	Rules.Feet = GetFeet();

	FMIPlayerInputFrame Frame;
	Frame.Move = Input.Move;
	Frame.LookDegrees = Input.LookDegrees;
	Frame.bSprintHeld = Input.bSprint;
	Frame.bCrouchHeld = Input.bCrouch;
	Frame.bFireHeld = Input.bFire;
	Frame.bJumpPressed = Input.bJumpPressed;
	FrameLook = Input.LookDegrees;
	Input.LookDegrees = FVector2D::ZeroVector;
	Input.bJumpPressed = false;

	const FMIBodyMove Move = Rules.BeginFrame(DeltaSeconds, Frame, [this]() { return CanStand(); });
	if (Controller)
	{
		Controller->SetControlRotation(FRotator(Rules.Pitch, Rules.Yaw, 0.0));
	}

	Movement->bRuleDriven = true;
	Movement->RuleVelocity = Move.bMove ? Move.Velocity : FVector::ZeroVector;
	if (!Move.bMove)
	{
		Movement->Velocity = FVector::ZeroVector;
		return;
	}
	if (Move.bJumped)
	{
		Movement->Velocity.Z = Move.Velocity.Z;
		Movement->SetMovementMode(MOVE_Falling);
	}
	if (Move.bDead)
	{
		Movement->bWantsToCrouch = false;
		if (!bDeathCapsule)
		{
			// The body drops to a sphere on the floor; the feet stay where they are.
			bDeathCapsule = true;
			const FVector Feet = GetFeet();
			const double Radius = GetCapsuleComponent()->GetScaledCapsuleRadius();
			const double Half = FMath::Max(Radius, Move.Height * 0.5);
			GetCapsuleComponent()->SetCapsuleSize(Radius, Half);
			SetActorLocation(Feet + FVector(0, 0, Half));
		}
	}
	else
	{
		Movement->bWantsToCrouch = Rules.bCrouching;
	}
}

void AMIPlayerCharacter::LateTick(float DeltaSeconds)
{
	if (!bHasTuning || !Movement)
	{
		return;
	}
	FMIBodyResult Body;
	Body.Feet = GetFeet();
	Body.Velocity = Movement->Velocity;
	Body.bOnGround = Movement->IsMovingOnGround();
	if (const UPhysicalMaterial* Material = Movement->CurrentFloor.HitResult.PhysMaterial.Get())
	{
		FString Name = Material->GetName();
		Name.RemoveFromStart(TEXT("PM_"));
		Body.Surface = FName(*Name.ToLower());
	}
	else
	{
		Body.Surface = NAME_None;
	}
	Rules.EndFrame(DeltaSeconds, Body);

	if (Weapon)
	{
		FMIWeaponInput W;
		W.bFireDown = Input.bFire;
		W.bFirePressed = Input.bFirePressed;
		W.bAdsDown = Input.bAds;
		W.bSwapPressed = Input.bSwapPressed;
		W.bWeapon1Pressed = Input.bWeapon1Pressed;
		W.bWeapon2Pressed = Input.bWeapon2Pressed;
		W.bMeleePressed = Input.bMeleePressed;
		W.bReloadPressed = Input.bReloadPressed;
		W.bPadActive = Input.bPad;
		Input.bFirePressed = Input.bSwapPressed = Input.bWeapon1Pressed = Input.bWeapon2Pressed = false;
		Input.bMeleePressed = Input.bReloadPressed = false;
		Weapon->Step(DeltaSeconds, W, FrameLook);
	}
	PlaceCamera();
}

double AMIPlayerCharacter::HorizontalFov(double VerticalDegrees) const
{
	double Aspect = 16.0 / 9.0;
	if (const UWorld* World = GetWorld(); World && World->GetGameViewport())
	{
		FVector2D Size;
		World->GetGameViewport()->GetViewportSize(Size);
		if (Size.X > 0.0 && Size.Y > 0.0)
		{
			Aspect = Size.X / Size.Y;
		}
	}
	return FMath::RadiansToDegrees(2.0 * FMath::Atan(FMath::Tan(FMath::DegreesToRadians(VerticalDegrees) * 0.5) * Aspect));
}

void AMIPlayerCharacter::PlaceCamera()
{
	// The web game keeps the vertical field of view; the engine's camera takes a horizontal one.
	FirstPersonCamera->SetWorldLocationAndRotation(Rules.Eye, Rules.CameraRotation);
	FirstPersonCamera->SetFieldOfView(HorizontalFov(Rules.ViewFov));
	FirstPersonCamera->SetFirstPersonFieldOfView(HorizontalFov(Tuning.Player.Fov.Viewmodel));
}

FName AMIPlayerCharacter::GetStance() const
{
	if (!Rules.bAlive) return TEXT("dead");
	if (Rules.bCrouching) return TEXT("crouch");
	if (Rules.bSprinting) return TEXT("sprint");
	return TEXT("stand");
}

FMIDamageResult AMIPlayerCharacter::ApplyMIDamage(const FMIDamage& Damage)
{
	FMIDamageResult Result;
	if (!Rules.bAlive || Rules.bInvulnerable || !(Damage.Amount > 0.0))
	{
		return Result;
	}
	const double Before = Rules.Health;
	Rules.Damage(Damage.Amount, Damage.From, Damage.Kind);
	if (Damage.From.IsSet())
	{
		LastDamageDirection = (Damage.From.GetValue() - Rules.Eye).GetSafeNormal();
	}
	Result.bAccepted = true;
	Result.Dealt = Before - Rules.Health;
	Result.bKilled = !Rules.bAlive;
	return Result;
}

FVector AMIPlayerCharacter::GetMIBlastTarget() const
{
	using namespace MIPlayerCharacterPrivate;
	return GetFeet() + FVector(0, 0, Rules.bCrouching ? BlastCrouching : BlastStanding);
}
