#include "World/MITargetDummy.h"

#include "Components/CapsuleComponent.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"
#include "MurderInc.h"
#include "UObject/ConstructorHelpers.h"
#include "Weapons/MICombatSubsystem.h"

namespace MITargetDummyPrivate
{
	void BulletOnly(UPrimitiveComponent* C)
	{
		C->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
		C->SetCollisionObjectType(ECC_Pawn);
		C->SetCollisionResponseToAllChannels(ECR_Ignore);
		C->SetCollisionResponseToChannel(MIBulletChannel, ECR_Block);
	}
}

AMITargetDummy::AMITargetDummy()
{
	PrimaryActorTick.bCanEverTick = true;
	USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Feet"));
	RootComponent = Root;

	Body = CreateDefaultSubobject<UCapsuleComponent>(TEXT("Body"));
	Body->SetupAttachment(Root);
	MITargetDummyPrivate::BulletOnly(Body);
	Head = CreateDefaultSubobject<USphereComponent>(TEXT("Head"));
	Head->SetupAttachment(Root);
	Head->ComponentTags.Add(TEXT("head"));
	MITargetDummyPrivate::BulletOnly(Head);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	BodyMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("BodyMesh"));
	BodyMesh->SetupAttachment(Body);
	BodyMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	HeadMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("HeadMesh"));
	HeadMesh->SetupAttachment(Head);
	HeadMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	if (Cylinder.Succeeded()) BodyMesh->SetStaticMesh(Cylinder.Object);
	if (Sphere.Succeeded()) HeadMesh->SetStaticMesh(Sphere.Object);
}

void AMITargetDummy::ApplyTuning()
{
	TSharedPtr<FJsonObject> Config;
	if (const UMIDataSubsystem* Data = UMIDataSubsystem::Get(this); Data && Data->IsLoaded())
	{
		Config = Data->GetConfigJson();
	}
	FString Error;
	if (!Config.IsValid() && !UMIDataSubsystem::LoadJsonFile(TEXT("config.json"), Config, Error))
	{
		UE_LOG(LogMI, Error, TEXT("Target dummy: config.json: %s"), *Error);
		return;
	}
	const TSharedPtr<FJsonObject> Goon = Config->GetObjectField(TEXT("enemies"))->GetObjectField(TEXT("goon"));
	const TSharedPtr<FJsonObject> HeadData = Goon->GetObjectField(TEXT("head"));
	MaxHealth = Health = Goon->GetNumberField(TEXT("hp"));
	BodyHeight = Goon->GetNumberField(TEXT("height")) * 100.0;
	const double BodyRadius = Goon->GetNumberField(TEXT("bodyRadius")) * 100.0;
	const double HeadRadius = HeadData->GetNumberField(TEXT("radius")) * 100.0;
	const double HeadHeight = HeadData->GetNumberField(TEXT("height")) * 100.0;
	// The body capsule runs from the shin to the shoulder (spec 02 2.8): it stops where the head sphere starts.
	const double Top = HeadHeight - HeadRadius;
	const double Bottom = BodyRadius;
	Body->SetCapsuleSize(BodyRadius, FMath::Max(BodyRadius, (Top - Bottom) * 0.5));
	Body->SetRelativeLocation(FVector(0, 0, (Top + Bottom) * 0.5));
	Head->SetSphereRadius(HeadRadius);
	Head->SetRelativeLocation(FVector(0, 0, HeadHeight));
	BodyMesh->SetRelativeScale3D(FVector(BodyRadius * 2.0 / 100.0, BodyRadius * 2.0 / 100.0, Body->GetScaledCapsuleHalfHeight() * 2.0 / 100.0));
	HeadMesh->SetRelativeScale3D(FVector(HeadRadius * 2.0 / 100.0));
}

void AMITargetDummy::BeginPlay()
{
	Super::BeginPlay();
	ApplyTuning();
	if (UMICombatSubsystem* Combat = UMICombatSubsystem::Get(this))
	{
		Combat->Register(this);
	}
}

void AMITargetDummy::EndPlay(const EEndPlayReason::Type Reason)
{
	if (UMICombatSubsystem* Combat = UMICombatSubsystem::Get(this))
	{
		Combat->Unregister(this);
	}
	Super::EndPlay(Reason);
}

FMIDamageResult AMITargetDummy::ApplyMIDamage(const FMIDamage& Damage)
{
	FMIDamageResult Result;
	if (Health <= 0.0 || !(Damage.Amount > 0.0))
	{
		return Result;
	}
	Result.bAccepted = true;
	Result.Dealt = FMath::Min(Health, Damage.Amount);
	Health -= Result.Dealt;
	TotalDamage += Damage.Amount;
	if (Damage.Part == TEXT("head"))
	{
		++HeadHits;
	}
	if (Health <= 0.0)
	{
		Health = 0.0;
		Result.bKilled = true;
		DownFor = 0.0;
		SetActorRelativeRotation(GetActorRotation() + FRotator(0.0, 0.0, 80.0));  // keels over (placeholder)
	}
	return Result;
}

FVector AMITargetDummy::GetMIBlastTarget() const
{
	return GetActorLocation() + FVector(0, 0, BodyHeight * 0.5);  // a Goon's feet + half his height
}

void AMITargetDummy::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (Health > 0.0 || StandUpAfter <= 0.f)
	{
		return;
	}
	DownFor += DeltaSeconds;
	if (DownFor >= StandUpAfter)
	{
		Health = MaxHealth;
		SetActorRelativeRotation(GetActorRotation() - FRotator(0.0, 0.0, 80.0));
	}
}
