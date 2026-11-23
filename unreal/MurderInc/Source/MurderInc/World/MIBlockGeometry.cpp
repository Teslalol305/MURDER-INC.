#include "World/MIBlockGeometry.h"

#include "Components/BoxComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "MurderInc.h"
#include "Weapons/MICombatSubsystem.h"
#include "World/MILevelData.h"

AMIBlockGeometry::AMIBlockGeometry()
{
	PrimaryActorTick.bCanEverTick = false;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Root->SetMobility(EComponentMobility::Static);
	RootComponent = Root;
	Grey = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Grey"));
	Grey->SetupAttachment(Root);
	Grey->SetMobility(EComponentMobility::Static);
	Grey->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

int32 AMIBlockGeometry::Build(const FMILevelData& Level, bool bDraw)
{
	using namespace MI::Web;
	FString CubePath = TEXT("/Engine/BasicShapes/Cube.Cube");
	double FloorDepth = 50.0;
	TSharedPtr<FJsonObject> Presentation;
	FString Error;
	if (UMIDataSubsystem::LoadJsonFile(TEXT("presentation.json"), Presentation, Error))
	{
		if (const TSharedPtr<FJsonObject>* Block; Presentation->TryGetObjectField(TEXT("block"), Block))
		{
			(*Block)->TryGetStringField(TEXT("cube"), CubePath);
			(*Block)->TryGetNumberField(TEXT("floorDepth"), FloorDepth);
		}
	}
	if (bDraw)
	{
		if (UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, *CubePath))
		{
			Grey->SetStaticMesh(Cube);
		}
	}

	auto AddBox = [this, bDraw](const FVector& Centre, const FVector& Extent, bool bBulletOnly, bool bPlayerOnly)
	{
		UBoxComponent* Box = NewObject<UBoxComponent>(this);
		Box->SetMobility(EComponentMobility::Static);
		Box->SetupAttachment(Root);
		Box->SetBoxExtent(Extent.ComponentMax(FVector(0.5)), false);
		Box->SetRelativeLocation(Centre);
		Box->SetCollisionObjectType(ECC_WorldStatic);
		Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
		if (bPlayerOnly)
		{
			// Seal walls: bodies stop, rounds, sight and the camera pass.
			Box->SetCollisionResponseToAllChannels(ECR_Ignore);
			Box->SetCollisionResponseToChannel(ECC_Pawn, ECR_Block);
		}
		else
		{
			Box->SetCollisionResponseToAllChannels(ECR_Block);
			if (bBulletOnly)
			{
				Box->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
				Box->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
			}
		}
		Box->SetCanEverAffectNavigation(false);
		Box->RegisterComponent();
		Boxes.Add(Box);
		if (bDraw && !bPlayerOnly)
		{
			Grey->AddInstance(FTransform(FRotator::ZeroRotator, Centre, Extent.ComponentMax(FVector(0.5)) / 50.0));
		}
	};

	for (const FMIBox& B : Level.Colliders)
	{
		if (B.Owner != INDEX_NONE)
		{
			continue;  // an explosive's own box (AMIExplosive)
		}
		const FVector A = ToUnreal(B.Min);
		const FVector C = ToUnreal(B.Max);
		AddBox((A + C) * 0.5, (C - A).GetAbs() * 0.5, B.bBulletOnly, B.bPlayerOnly);
	}
	// The ground plane of the web world (physics.js: y = 0 everywhere) as a slab under the bounds and well beyond.
	const FMIBounds& Bd = Level.Bounds;
	const FVector Lo = ToUnreal(FVector(Bd.MinX - 20.0, 0.0, Bd.MinZ - 20.0));
	const FVector Hi = ToUnreal(FVector(Bd.MaxX + 20.0, 0.0, Bd.MaxZ + 20.0));
	AddBox(FVector((Lo.X + Hi.X) * 0.5, (Lo.Y + Hi.Y) * 0.5, -FloorDepth * 0.5), FVector(FMath::Abs(Hi.X - Lo.X) * 0.5, FMath::Abs(Hi.Y - Lo.Y) * 0.5, FloorDepth * 0.5), false, false);
	Grey->SetVisibility(bDraw);
	UE_LOG(LogMI, Log, TEXT("Block: %d collision boxes from level.json%s"), Boxes.Num(), bDraw ? TEXT(", drawn as grey boxes") : TEXT(" under the art"));
	return Boxes.Num();
}

bool AMIBlockGeometry::WorldHasArt(UWorld* World, FName ArtTag)
{
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		if (It->Tags.Contains(ArtTag))
		{
			return true;
		}
	}
	return false;
}

int32 AMIBlockGeometry::DisableArtCollision(UWorld* World, FName ArtTag)
{
	int32 Count = 0;
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		if (!It->Tags.Contains(ArtTag))
		{
			continue;
		}
		TInlineComponentArray<UPrimitiveComponent*> Primitives(*It);
		for (UPrimitiveComponent* P : Primitives)
		{
			if (P->GetCollisionEnabled() != ECollisionEnabled::NoCollision)
			{
				P->SetCollisionEnabled(ECollisionEnabled::NoCollision);
				++Count;
			}
		}
	}
	return Count;
}
