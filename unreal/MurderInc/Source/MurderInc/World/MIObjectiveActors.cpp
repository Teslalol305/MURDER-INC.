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

	/** A mesh component made at run time (Setup runs after spawning) under Parent, drawing the art as modelled. */
	UStaticMeshComponent* AddArt(AActor* Owner, USceneComponent* Parent, const FString& Path, const FTransform& At)
	{
		UStaticMesh* Mesh = Path.IsEmpty() ? nullptr : LoadObject<UStaticMesh>(nullptr, *Path);
		if (!Mesh)
		{
			return nullptr;
		}
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(Owner);
		C->SetMobility(EComponentMobility::Movable);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetCanEverAffectNavigation(false);
		C->SetStaticMesh(Mesh);
		C->SetupAttachment(Parent);
		C->SetRelativeTransform(At);
		C->RegisterComponent();
		Owner->AddInstanceComponent(C);
		return C;
	}

	/** {at [x, y, z] cm, rot [pitch, yaw, roll] deg} of a presentation.json part. */
	FTransform PartTransform(const TSharedPtr<FJsonObject>& O)
	{
		const FVector R = Vec(O, TEXT("rot"), FVector::ZeroVector);
		return FTransform(FRotator(R.X, R.Y, R.Z), Vec(O, TEXT("at"), FVector::ZeroVector));
	}

	FString Str(const TSharedPtr<FJsonObject>& O, const TCHAR* Field)
	{
		FString Out;
		if (O.IsValid())
		{
			O->TryGetStringField(Field, Out);
		}
		return Out;
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

	// The prop art (`art`): the case on its hand truck and the fixed parts as modelled in one frame (pivot on the
	// floor), the reel of this objective and the beacon (hidden once taken), the lid on its hinge (opens while grabbed).
	const TSharedPtr<FJsonObject>* Art = nullptr;
	if (P.IsValid() && P->TryGetObjectField(TEXT("art"), Art))
	{
		const TArray<TSharedPtr<FJsonValue>>* Parts = nullptr;
		if ((*Art)->TryGetArrayField(TEXT("parts"), Parts))
		{
			for (const TSharedPtr<FJsonValue>& V : *Parts)
			{
				const TSharedPtr<FJsonObject> O = V->AsObject();
				UStaticMeshComponent* C = AddArt(this, RootComponent, Str(O, TEXT("mesh")), PartTransform(O));
				if (C && !bArt)
				{
					bArt = true;  // the art is in this project: the basic-shape case goes
					Case->SetVisibility(false);
				}
				bool bHide = false;
				if (C && O->TryGetBoolField(TEXT("hideWhenTaken"), bHide) && bHide)
				{
					TakenParts.Add(C);
				}
			}
		}
		const TArray<TSharedPtr<FJsonValue>>* Reels = nullptr;
		if ((*Art)->TryGetArrayField(TEXT("reels"), Reels) && Reels->Num() > 0)
		{
			if (UStaticMeshComponent* C = AddArt(this, RootComponent, (*Reels)[Index % Reels->Num()]->AsString(), FTransform::Identity))
			{
				TakenParts.Add(C);
			}
		}
		const TSharedPtr<FJsonObject>* Lid = nullptr;
		if ((*Art)->TryGetObjectField(TEXT("lid"), Lid))
		{
			LidHinge = NewObject<USceneComponent>(this);
			LidHinge->SetupAttachment(RootComponent);
			LidHinge->SetRelativeLocation(Vec(*Lid, TEXT("hinge"), FVector::ZeroVector));
			LidHinge->RegisterComponent();
			AddInstanceComponent(LidHinge);
			AddArt(this, LidHinge, Str(*Lid, TEXT("mesh")), FTransform::Identity);
			(*Lid)->TryGetNumberField(TEXT("openRoll"), LidOpenRoll);
		}
		const FVector Light = Vec(*Art, TEXT("beaconAt"), FVector(0, 0, 140.0));
		Beacon->SetRelativeLocation(Light);
	}
	Sync(false, 0.0);
}

void AMIReelCase::Sync(bool bTaken, double InProgress)
{
	Progress = bTaken ? 1.0 : InProgress;
	State = bTaken ? EMIReelCaseState::Taken : (InProgress > 0.0 ? EMIReelCaseState::Grabbing : EMIReelCaseState::Live);
	if (!bArt && Case->IsVisible() == bTaken)
	{
		Case->SetVisibility(!bTaken);
	}
	for (UStaticMeshComponent* C : TakenParts)
	{
		if (C && C->IsVisible() == bTaken)
		{
			C->SetVisibility(!bTaken);
		}
	}
	if (LidHinge)
	{
		// The lid is up while the reel is being lifted out and stays up once it is gone.
		const double Open = bTaken ? 1.0 : FMath::Clamp(InProgress * 4.0, 0.0, 1.0);
		LidHinge->SetRelativeRotation(FRotator(0, 0, LidOpenRoll * Open));
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

	// The truck art (`art`): body as modelled (pivot on the ground at the truck's position), each door leaf on its
	// hinge with its own opening angle; drawn in every map (the level does not draw the truck).
	const TSharedPtr<FJsonObject>* Art = nullptr;
	UStaticMesh* BodyArt = nullptr;
	if (P.IsValid() && P->TryGetObjectField(TEXT("art"), Art) && (BodyArt = LoadObject<UStaticMesh>(nullptr, *Str(*Art, TEXT("body")))) != nullptr)
	{
		Body->SetStaticMesh(BodyArt);
		Body->SetRelativeLocation(FVector::ZeroVector);
		Body->SetRelativeScale3D(FVector::OneVector);
		const TArray<TSharedPtr<FJsonValue>>* Doors = nullptr;
		if ((*Art)->TryGetArrayField(TEXT("doors"), Doors) && Doors->Num() >= 2)
		{
			USceneComponent* Hinges[2] = {HingeL, HingeR};
			UStaticMeshComponent* Leaves[2] = {DoorL, DoorR};
			for (int32 I = 0; I < 2; ++I)
			{
				const TSharedPtr<FJsonObject> D = (*Doors)[I]->AsObject();
				Hinges[I]->SetRelativeLocation(Vec(D, TEXT("hinge"), FVector::ZeroVector));
				Leaves[I]->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, *Str(D, TEXT("mesh"))));
				Leaves[I]->SetRelativeLocation(FVector::ZeroVector);
				Leaves[I]->SetRelativeScale3D(FVector::OneVector);
				D->TryGetNumberField(TEXT("open"), DoorOpen[I]);
			}
		}
		bDraw = true;
	}
	else
	{
		DoorOpen[0] = -OpenDegrees;
		DoorOpen[1] = OpenDegrees;
	}
	SetActorHiddenInGame(!bDraw);
	Sync(false, 0.0);
}

void AMITruck::Sync(bool bOpen, double Dt)
{
	State = bOpen ? EMITruckState::Open : EMITruckState::Idle;
	const double Target = bOpen ? 1.0 : 0.0;
	Swing = Dt > 0.0 ? FMath::FInterpTo(Swing, Target, Dt, 2.5) : Target;
	HingeL->SetRelativeRotation(FRotator(0, DoorOpen[0] * Swing, 0));
	HingeR->SetRelativeRotation(FRotator(0, DoorOpen[1] * Swing, 0));
}
