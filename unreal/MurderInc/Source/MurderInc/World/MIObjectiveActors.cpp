#include "World/MIObjectiveActors.h"

#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"

namespace MIObjectiveActorsPrivate
{
	TSharedPtr<FJsonObject> Section(const TCHAR* Name)
	{
		TSharedPtr<FJsonObject> Root;
		FString Error;
		const TSharedPtr<FJsonObject>* Objectives = nullptr;
		const TSharedPtr<FJsonObject>* Out = nullptr;
		if (UMIDataSubsystem::LoadJsonFile(TEXT("presentation.json"), Root, Error) && Root->TryGetObjectField(TEXT("objectives"), Objectives) && (*Objectives)->TryGetObjectField(Name, Out))
		{
			return *Out;
		}
		return nullptr;
	}

	FVector Vec(const TSharedPtr<FJsonObject>& O, const TCHAR* Field, const FVector& Default)
	{
		const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
		return O.IsValid() && O->TryGetArrayField(Field, A) && A->Num() >= 3 ? FVector((*A)[0]->AsNumber(), (*A)[1]->AsNumber(), (*A)[2]->AsNumber()) : Default;
	}

	UStaticMeshComponent* MakeMesh(AActor* Owner, const TCHAR* Name)
	{
		UStaticMeshComponent* C = Owner->CreateDefaultSubobject<UStaticMeshComponent>(Name);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetCanEverAffectNavigation(false);
		return C;
	}
}

AMIReelCase::AMIReelCase()
{
	PrimaryActorTick.bCanEverTick = false;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Case = MIObjectiveActorsPrivate::MakeMesh(this, TEXT("Case"));
	Case->SetupAttachment(RootComponent);
	Beacon = CreateDefaultSubobject<UPointLightComponent>(TEXT("Beacon"));
	Beacon->SetupAttachment(RootComponent);
	Beacon->SetIntensityUnits(ELightUnits::Candelas);
	Beacon->SetCastShadows(false);
}

void AMIReelCase::Setup(int32 InIndex, FName InId)
{
	using namespace MIObjectiveActorsPrivate;
	Index = InIndex;
	Id = InId;
	const TSharedPtr<FJsonObject> P = Section(TEXT("case"));
	FString MeshPath = TEXT("/Engine/BasicShapes/Cube.Cube");
	double Lift = 75.0, Radius = 600.0;
	if (P.IsValid())
	{
		P->TryGetStringField(TEXT("mesh"), MeshPath);
		P->TryGetNumberField(TEXT("lift"), Lift);
		P->TryGetNumberField(TEXT("beaconCandela"), BeaconCandela);
		P->TryGetNumberField(TEXT("beaconRadius"), Radius);
	}
	const FVector Size = Vec(P, TEXT("size"), FVector(60, 40, 22));
	Case->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, *MeshPath));
	Case->SetRelativeLocation(FVector(0, 0, Lift + Size.Z * 0.5));
	Case->SetRelativeScale3D(Size / 100.0);
	const FVector Colour = Vec(P, TEXT("beacon"), FVector(1.0, 0.62, 0.18));
	Beacon->SetLightColor(FLinearColor(Colour.X, Colour.Y, Colour.Z));
	Beacon->SetAttenuationRadius(Radius);
	Beacon->SetRelativeLocation(FVector(0, 0, Lift + Size.Z + 40.0));
	Sync(false, 0.0);
}

void AMIReelCase::Sync(bool bTaken, double InProgress)
{
	Progress = bTaken ? 1.0 : InProgress;
	State = bTaken ? EMIReelCaseState::Taken : (InProgress > 0.0 ? EMIReelCaseState::Grabbing : EMIReelCaseState::Live);
	if (Case->IsVisible() == bTaken)
	{
		Case->SetVisibility(!bTaken);
	}
	Beacon->SetIntensity(bTaken ? 0.f : BeaconCandela * (1.0 + 2.0 * Progress));
}

AMITruck::AMITruck()
{
	using namespace MIObjectiveActorsPrivate;
	PrimaryActorTick.bCanEverTick = false;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Body = MakeMesh(this, TEXT("Body"));
	Body->SetupAttachment(RootComponent);
	HingeL = CreateDefaultSubobject<USceneComponent>(TEXT("HingeL"));
	HingeL->SetupAttachment(RootComponent);
	HingeR = CreateDefaultSubobject<USceneComponent>(TEXT("HingeR"));
	HingeR->SetupAttachment(RootComponent);
	DoorL = MakeMesh(this, TEXT("DoorL"));
	DoorL->SetupAttachment(HingeL);
	DoorR = MakeMesh(this, TEXT("DoorR"));
	DoorR->SetupAttachment(HingeR);
}

void AMITruck::Setup(bool bDraw)
{
	using namespace MIObjectiveActorsPrivate;
	const TSharedPtr<FJsonObject> P = Section(TEXT("truck"));
	FString MeshPath = TEXT("/Engine/BasicShapes/Cube.Cube");
	if (P.IsValid())
	{
		P->TryGetStringField(TEXT("mesh"), MeshPath);
		P->TryGetNumberField(TEXT("doorOpenDegrees"), OpenDegrees);
	}
	const FVector Size = Vec(P, TEXT("size"), FVector(700, 250, 300));
	const FVector Door = Vec(P, TEXT("door"), FVector(6, 120, 260));
	UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *MeshPath);
	Body->SetStaticMesh(Mesh);
	Body->SetRelativeLocation(FVector(0, 0, Size.Z * 0.5));
	Body->SetRelativeScale3D(Size / 100.0);
	// The rear doors face the extraction zone (local -X); hinged at the outer edges.
	HingeL->SetRelativeLocation(FVector(-Size.X * 0.5 - Door.X, -Door.Y, 20.0));
	HingeR->SetRelativeLocation(FVector(-Size.X * 0.5 - Door.X, Door.Y, 20.0));
	DoorL->SetStaticMesh(Mesh);
	DoorL->SetRelativeLocation(FVector(0, Door.Y * 0.5, Door.Z * 0.5));
	DoorL->SetRelativeScale3D(Door / 100.0);
	DoorR->SetStaticMesh(Mesh);
	DoorR->SetRelativeLocation(FVector(0, -Door.Y * 0.5, Door.Z * 0.5));
	DoorR->SetRelativeScale3D(Door / 100.0);
	SetActorHiddenInGame(!bDraw);
	Sync(false, 0.0);
}

void AMITruck::Sync(bool bOpen, double Dt)
{
	State = bOpen ? EMITruckState::Open : EMITruckState::Idle;
	const double Target = bOpen ? 1.0 : 0.0;
	Swing = Dt > 0.0 ? FMath::FInterpTo(Swing, Target, Dt, 2.5) : Target;
	HingeL->SetRelativeRotation(FRotator(0, -OpenDegrees * Swing, 0));
	HingeR->SetRelativeRotation(FRotator(0, OpenDegrees * Swing, 0));
}
