#include "World/MIExplosive.h"

#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
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
	if (const FMIExplosiveKindData* K = Combat->GetExplosiveKind(Kind))
	{
		Height = K->Box.Z;
		Box->SetBoxExtent(K->Box * 0.5);
		Mesh->SetRelativeLocation(FVector::ZeroVector);
		Mesh->SetRelativeScale3D(K->Box / 100.0);  // the engine cube is 100 cm
		// The root is the box centre: lift it so that the actor location given in the level stays the foot.
		AddActorWorldOffset(FVector(0, 0, Height * 0.5));
	}
	Index = Combat->AddExplosive(this, Kind);
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
	Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

void AMIExplosive::SyncFromItem(const FMIExplosiveItem& Item)
{
	State = Item.State;
	if (State == EMIExplosiveState::Gone)
	{
		Mesh->SetVisibility(false);
		Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	}
}
