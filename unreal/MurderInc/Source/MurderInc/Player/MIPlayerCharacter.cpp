#include "Player/MIPlayerCharacter.h"

#include "Core/MIMath.h"

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
#include "Core/Data/MILoadoutData.h"
#include "Materials/MaterialInterface.h"
#include "Weapons/MICombatSubsystem.h"
#include "Weapons/MIViewmodel.h"
#include "Weapons/MIWeaponComponent.h"

namespace MIPlayerCharacterPrivate
{
	double BlastStanding = 0.0;
	double BlastCrouching = 0.0;
	double FallOutBelow = -3000.0;  // cm
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
			const TSharedPtr<FJsonObject>* FallOut = nullptr;
			if (Root->GetObjectField(TEXT("player"))->TryGetObjectField(TEXT("fallOut"), FallOut))
			{
				FallOutBelow = (*FallOut)->GetNumberField(TEXT("below")) * 100.0;
			}
			bBlastLoaded = true;
		}
		else
		{
			UE_LOG(LogMI, Error, TEXT("Player: rules.json: %s"), *Error);
		}
	}
}

void FMIPlayerFrameTick::ExecuteTick(float DeltaTime, ELevelTick TickType, ENamedThreads::Type CurrentThread, const FGraphEventRef& MyCompletionGraphEvent)
{
	if (Target && IsValid(Target) && TickType != LEVELTICK_ViewportsOnly)
	{
		if (bLate)
		{
			Target->LateTick(DeltaTime);
		}
		else
		{
			Target->EarlyTick(DeltaTime);
		}
	}
}

AMIPlayerCharacter::AMIPlayerCharacter(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer.SetDefaultSubobjectClass<UMICharacterMovement>(ACharacter::CharacterMovementComponentName))
{
	PrimaryActorTick.bCanEverTick = false;  // the frame runs in FMIPlayerFrameTick
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

	// The rules decide before the move; the late half runs after it.
	EarlyTickFunction.Target = this;
	EarlyTickFunction.bLate = false;
	EarlyTickFunction.TickGroup = TG_PrePhysics;
	EarlyTickFunction.bCanEverTick = true;
	EarlyTickFunction.RegisterTickFunction(GetLevel());
	LateTickFunction.Target = this;
	LateTickFunction.bLate = true;
	LateTickFunction.TickGroup = TG_PostPhysics;
	LateTickFunction.bCanEverTick = true;
	LateTickFunction.RegisterTickFunction(GetLevel());
	if (Movement)
	{
		Movement->PrimaryComponentTick.AddPrerequisite(this, EarlyTickFunction);
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
	EarlyTickFunction.UnRegisterTickFunction();
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

	FMIViewmodelData View;
	FString Error;
	if (FMIViewmodelData::Load(View, Error))
	{
		FirstPersonCamera->SetFirstPersonScale(View.FirstPersonScale);
		if (USkeletalMesh* Body = Cast<USkeletalMesh>(View.Body.TryLoad()))
		{
			ArmsMesh->SetSkinnedAssetAndUpdate(Body, true);
			for (const FName Bone : View.BodyHiddenBones)
			{
				ArmsMesh->HideBoneByName(Bone, PBO_None);
			}
		}
	}
	if (Weapon)
	{
		// After the template body: the weapon's first-person rig puts the real arms in its place when they exist.
		Weapon->Setup(this, Config, FirstPersonCamera, GunMesh, ArmsMesh);
	}
	bHasTuning = true;
	ResetRun();
}

void AMIPlayerCharacter::ApplyCrewLook(const FMICrewEntry* Crew)
{
	if (!ArmsMesh)
	{
		return;
	}
	ArmsMesh->EmptyOverrideMaterials();
	if (!Crew)
	{
		return;
	}
	for (const TPair<FName, FString>& M : Crew->Materials)
	{
		if (UMaterialInterface* Mat = Cast<UMaterialInterface>(FSoftObjectPath(M.Value).TryLoad()))
		{
			ArmsMesh->SetMaterialByName(M.Key, Mat);
		}
	}
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

void AMIPlayerCharacter::ResetAt(const FVector& Feet, double Yaw)
{
	if (Movement)
	{
		Movement->bWantsToCrouch = false;
		if (bIsCrouched)
		{
			Movement->UnCrouch(false);
		}
		Movement->StopMovementImmediately();
		Movement->SetMovementMode(MOVE_Walking);
	}
	if (bHasTuning)
	{
		GetCapsuleComponent()->SetCapsuleSize(Tuning.Player.Body.Radius, Tuning.Player.Body.Height * 0.5);
	}
	bDeathCapsule = false;
	SetActorLocationAndRotation(Feet + FVector(0, 0, GetCapsuleComponent()->GetScaledCapsuleHalfHeight()), FRotator(0, Yaw, 0), false, nullptr, ETeleportType::TeleportPhysics);
	if (Controller)
	{
		Controller->SetControlRotation(FRotator(0, Yaw, 0));
	}
	Input = FMIPlayerInputState();
	LastGroundFeet = Feet;
	bHaveGround = true;
	ResetRun();
}

void AMIPlayerCharacter::TeleportFeet(const FVector& Feet)
{
	SetActorLocation(Feet + FVector(0, 0, GetCapsuleComponent()->GetScaledCapsuleHalfHeight()), false, nullptr, ETeleportType::TeleportPhysics);
	Rules.Feet = Feet;
	if (Movement)
	{
		Movement->StopMovementImmediately();
		Movement->SetMovementMode(MOVE_Walking);
	}
}

void AMIPlayerCharacter::SetViewmodelVisible(bool bVisible)
{
	const bool bArms = bVisible && !bArmsHidden;
	if (GunMesh->IsVisible() != bVisible)
	{
		GunMesh->SetVisibility(bVisible, true);  // with its children: the fitted parts, the seated magazine and its top round
	}
	if (ArmsMesh->IsVisible() != bArms)
	{
		ArmsMesh->SetVisibility(bArms);
	}
	if (Weapon)
	{
		Weapon->SyncVisibility(bVisible, bArms);
	}
}

void AMIPlayerCharacter::SetArmsHidden(bool bHidden)
{
	bArmsHidden = bHidden;
	SetViewmodelVisible(GunMesh->IsVisible());
}

void AMIPlayerCharacter::AirStep(float DeltaSeconds)
{
	const UWorld* World = GetWorld();
	const double Step = Tuning.Player.Body.AirStepHeight;
	if (!World || !Movement || Movement->IsMovingOnGround() || Step <= 0.0 || !Rules.bAlive)
	{
		return;
	}
	const FVector Wish(Movement->RuleVelocity.X, Movement->RuleVelocity.Y, 0.0);
	if (Wish.SizeSquared() < 1.0)
	{
		return;
	}
	const UCapsuleComponent* Capsule = GetCapsuleComponent();
	const double Radius = Capsule->GetScaledCapsuleRadius();
	const double Half = Capsule->GetScaledCapsuleHalfHeight();
	const FVector Dir = Wish.GetSafeNormal();
	const double Reach = FMath::Max(2.0, Wish.Size() * DeltaSeconds);
	const FCollisionShape Shape = FCollisionShape::MakeCapsule(Radius, Half);
	FCollisionQueryParams Params(SCENE_QUERY_STAT(MIAirStep), false, this);
	const FVector At = GetActorLocation();
	FHitResult Hit;
	// Blocked where it is, free once lifted by the air step: a ledge whose top is within the step.
	if (!World->SweepSingleByChannel(Hit, At, At + Dir * Reach, FQuat::Identity, ECC_Pawn, Shape, Params) || Hit.ImpactNormal.Z > 0.7)
	{
		return;
	}
	const FVector Lifted = At + FVector(0, 0, Step);
	if (World->OverlapBlockingTestByChannel(Lifted, FQuat::Identity, ECC_Pawn, Shape, Params)
		|| World->SweepSingleByChannel(Hit, Lifted, Lifted + Dir * Reach, FQuat::Identity, ECC_Pawn, Shape, Params))
	{
		return;
	}
	// Land on the top: down from the lifted, advanced place.
	const FVector Ahead = Lifted + Dir * Reach;
	if (World->SweepSingleByChannel(Hit, Ahead, Ahead - FVector(0, 0, Step + 1.0), FQuat::Identity, ECC_Pawn, Shape, Params) && Hit.ImpactNormal.Z > 0.7)
	{
		SetActorLocation(Hit.Location, false, nullptr, ETeleportType::TeleportPhysics);
		Movement->Velocity.Z = 0.0;
		Movement->SetMovementMode(MOVE_Walking);
	}
}

void AMIPlayerCharacter::KeepInside()
{
	using namespace MIPlayerCharacterPrivate;
	FVector Location = GetActorLocation();
	const FVector Feet = GetFeet();
	if (!Location.ContainsNaN() && Feet.Z >= FallOutBelow && Movement && Movement->IsMovingOnGround())
	{
		LastGroundFeet = Feet;
		bHaveGround = true;
	}
	if (Location.ContainsNaN() || Feet.Z < FallOutBelow)
	{
		if (bHaveGround)
		{
			TeleportFeet(LastGroundFeet);
		}
		return;
	}
	if (!PlayBounds.bIsValid)
	{
		return;
	}
	const double M = Tuning.Player.Body.BoundsMargin;
	const double X = FMath::Clamp(Location.X, PlayBounds.Min.X + M, PlayBounds.Max.X - M);
	const double Y = FMath::Clamp(Location.Y, PlayBounds.Min.Y + M, PlayBounds.Max.Y - M);
	if (X != Location.X || Y != Location.Y)
	{
		SetActorLocation(FVector(X, Y, Location.Z), false, nullptr, ETeleportType::TeleportPhysics);
		if (Movement)
		{
			if (X != Location.X) Movement->Velocity.X = 0.0;
			if (Y != Location.Y) Movement->Velocity.Y = 0.0;
		}
	}
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

void AMIPlayerCharacter::EarlyTick(float DeltaSeconds)
{
	if (!bHasTuning || !Movement)
	{
		return;
	}
	if (!bSimLive)
	{
		Movement->RuleVelocity = FVector::ZeroVector;
		Movement->Velocity = FVector::ZeroVector;
		return;
	}
	if (!bGameplayInput)
	{
		Input = FMIPlayerInputState();
	}
	// The rules' view of the body is the capsule's.
	Rules.Feet = GetFeet();

	// The aim assist's turn: the view moves by exactly that, whatever the aimed look rate (zero unless the assist is on).
	if (!Input.AssistDegrees.IsZero())
	{
		const double Limit = Tuning.Player.Look.PitchLimit;
		Rules.Yaw = MI::WrapDegrees(Rules.Yaw + Input.AssistDegrees.X);
		Rules.Pitch = FMath::Clamp(Rules.Pitch + Input.AssistDegrees.Y, -Limit, Limit);
		Input.AssistDegrees = FVector2D::ZeroVector;
	}

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
	if (!bSimLive)
	{
		PlaceCamera();
		return;
	}
	AirStep(DeltaSeconds);
	KeepInside();
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
		W.bWeapon3Pressed = Input.bWeapon3Pressed;
		W.bWeapon4Pressed = Input.bWeapon4Pressed;
		W.bNextPressed = Input.bNextPressed;
		W.bPreviousPressed = Input.bPreviousPressed;
		W.WheelPick = Input.WheelPick;
		W.bFireModePressed = Input.bFireModePressed;
		Input.bWeapon3Pressed = Input.bWeapon4Pressed = Input.bNextPressed = Input.bPreviousPressed = Input.bFireModePressed = false;
		if (Input.bInspectPressed)
		{
			Weapon->RequestInspect();  // presentation only: the rules have no inspect
		}
		Input.bInspectPressed = false;
		Input.WheelPick = INDEX_NONE;
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
	FirstPersonCamera->SetFirstPersonFieldOfView(HorizontalFov(Weapon ? Weapon->GetFirstPersonFov(Tuning.Player.Fov.Viewmodel) : Tuning.Player.Fov.Viewmodel));
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
