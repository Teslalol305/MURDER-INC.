#include "World/MIExplosive.h"

#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"
#include "Weapons/MICombatSubsystem.h"

AMIExplosive::AMIExplosive()
{
	PrimaryActorTick.bCanEverTick = false;
	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	Box->SetCollisionProfileName(TEXT("BlockAll"));
	Box->SetCollisionResponseToChannel(MIBulletChannel, ECR_Block);
	RootComponent = Box;

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Box);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (Cube.Succeeded())
	{
		Mesh->SetStaticMesh(Cube.Object);
	}
	Wreck = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Wreck"));
	Wreck->SetupAttachment(Box);
	Wreck->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Wreck->SetVisibility(false);
}

void AMIExplosive::BeginPlay()
{
	Super::BeginPlay();
	UMICombatSubsystem* Combat = UMICombatSubsystem::Get(this);
	if (!Combat)
	{
		return;
	}
	// The actor stands on its foot: the box is sized from the kind (X length, Y width, Z height, cm).
	const FVector Foot = GetActorLocation();
	if (const FMIExplosiveKindData* K = Combat->GetExplosiveKind(Kind))
	{
		Height = K->Box.Z;
		Box->SetBoxExtent(K->Box * 0.5);
		Mesh->SetRelativeLocation(FVector::ZeroVector);
		Mesh->SetRelativeScale3D(K->Box / 100.0);  // the engine cube is 100 cm
		// The root is the box centre: lift it so that the actor location given in the level stays the foot.
		AddActorWorldOffset(FVector(0, 0, Height * 0.5));
		// The wreck: presentation.json explosives.<kind> (a soft path and its height as a share of the box).
		TSharedPtr<FJsonObject> Presentation;
		FString Error;
		const TSharedPtr<FJsonObject>* Section = nullptr;
		const TSharedPtr<FJsonObject>* Look = nullptr;
		if (UMIDataSubsystem::LoadJsonFile(TEXT("presentation.json"), Presentation, Error) && Presentation->TryGetObjectField(TEXT("explosives"), Section) && (*Section)->TryGetObjectField(Kind.ToString(), Look))
		{
			FString Path, ArtPath;
			double Share = 0.1;
			(*Look)->TryGetStringField(TEXT("wreck"), Path);
			(*Look)->TryGetNumberField(TEXT("wreckHeight"), Share);
			// The prop art (`mesh`): drawn as modelled with its pivot on the foot; the wreck is then art too.
			(*Look)->TryGetStringField(TEXT("mesh"), ArtPath);
			UStaticMesh* ArtMesh = ArtPath.IsEmpty() ? nullptr : LoadObject<UStaticMesh>(nullptr, *ArtPath);
			if (ArtMesh)
			{
				Mesh->SetStaticMesh(ArtMesh);
				Mesh->SetRelativeScale3D(FVector::OneVector);
				Mesh->SetRelativeLocation(FVector(0, 0, -Height * 0.5));
			}
			UStaticMesh* WreckMesh = Path.IsEmpty() ? nullptr : LoadObject<UStaticMesh>(nullptr, *Path);
			if (WreckMesh && ArtMesh)
			{
				Wreck->SetStaticMesh(WreckMesh);
				Wreck->SetRelativeScale3D(FVector::OneVector);
				Wreck->SetRelativeLocation(FVector(0, 0, -Height * 0.5));
			}
			else if (WreckMesh)
			{
				Wreck->SetStaticMesh(WreckMesh);
				const FVector Size(K->Box.X * 0.9, K->Box.Y * 0.9, FMath::Max(1.0, K->Box.Z * Share));
				Wreck->SetRelativeScale3D(Size / 100.0);
				Wreck->SetRelativeLocation(FVector(0, 0, -Height * 0.5 + Size.Z * 0.5));
			}
		}
	}
	Index = Combat->AddExplosive(this, Kind, Foot);
	Combat->Register(this);
}

void AMIExplosive::EndPlay(const EEndPlayReason::Type Reason)
{
	if (UMICombatSubsystem* Combat = UMICombatSubsystem::Get(this))
	{
		Combat->Unregister(this);
	}
	Super::EndPlay(Reason);
}

FMIDamageResult AMIExplosive::ApplyMIDamage(const FMIDamage& Damage)
{
	FMIDamageResult Result;
	UMICombatSubsystem* Combat = UMICombatSubsystem::Get(this);
	if (!Combat || Index == INDEX_NONE || State == EMIExplosiveState::Gone)
	{
		return Result;
	}
	Combat->GetExplosives().Damage(Index, Damage.Amount, Damage.Source, Damage.Kind != EMIDamageKind::Blast);
	SyncFromItem(Combat->GetExplosives().GetItems()[Index]);
	Result.bAccepted = true;
	Result.Dealt = Damage.Kind == EMIDamageKind::Blast ? 0.0 : Damage.Amount;
	return Result;
}

bool AMIExplosive::IsMIDamageableAlive() const
{
	return State != EMIExplosiveState::Gone;
}

FVector AMIExplosive::GetMIBlastTarget() const
{
	return GetActorLocation();  // the root is the box centre
}

void AMIExplosive::OnBlown()
{
	State = EMIExplosiveState::Gone;
	Mesh->SetVisibility(false);
	Wreck->SetVisibility(true);
	Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

void AMIExplosive::Restore()
{
	State = EMIExplosiveState::Idle;
	Mesh->SetVisibility(true);
	Wreck->SetVisibility(false);
	Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
}

void AMIExplosive::SyncFromItem(const FMIExplosiveItem& Item)
{
	State = Item.State;
	if (State == EMIExplosiveState::Gone && Mesh->IsVisible())
	{
		OnBlown();
	}
}
