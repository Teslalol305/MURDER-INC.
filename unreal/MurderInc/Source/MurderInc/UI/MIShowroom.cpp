#include "UI/MIShowroom.h"

#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/BoxComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/RectLightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SpotLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Core/Data/MILoadoutData.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Weapons/MIGunAssembly.h"

namespace MIShowroomPrivate
{
	FVector Vec(const TSharedPtr<FJsonObject>& O, const FString& Path, const FVector& Fallback)
	{
		const TSharedPtr<FJsonValue> V = MIJson::Get(O, Path);
		if (!V.IsValid() || V->Type != EJson::Array || V->AsArray().Num() < 3) return Fallback;
		const TArray<TSharedPtr<FJsonValue>>& A = V->AsArray();
		return FVector(A[0]->AsNumber(), A[1]->AsNumber(), A[2]->AsNumber());
	}

	/** A slow ease for camera moves (cut when reduced motion is on). */
	double Ease(double T) { T = FMath::Clamp(T, 0.0, 1.0); return T * T * (3.0 - 2.0 * T); }
}

AMIShowroom::AMIShowroom()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bTickEvenWhenPaused = true;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);
	Pivot = CreateDefaultSubobject<USceneComponent>(TEXT("Turntable"));
	Pivot->SetupAttachment(Root);
	Gun = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Gun"));
	Gun->SetupAttachment(Pivot);
	Gun->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Assembly = CreateDefaultSubobject<UMIGunAssembly>(TEXT("Assembly"));
	TurntableCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("TurntableCamera"));
	TurntableCamera->SetupAttachment(Root);
	TurntableCamera->bConstrainAspectRatio = false;
	ArmsCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("ArmsCamera"));
	ArmsCamera->SetupAttachment(Root);
	ArmsCamera->bConstrainAspectRatio = false;
	ArmsCamera->SetAutoActivate(false);
	Arms = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Arms"));
	Arms->SetupAttachment(ArmsCamera);
	Arms->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Arms->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	ArmsGun = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("ArmsGun"));
	ArmsGun->SetupAttachment(ArmsCamera);
	ArmsGun->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	ArmsAssembly = CreateDefaultSubobject<UMIGunAssembly>(TEXT("ArmsAssembly"));
	Post = CreateDefaultSubobject<UPostProcessComponent>(TEXT("Exposure"));
	Post->SetupAttachment(Root);
}

void AMIShowroom::Setup(const TSharedPtr<FJsonObject>& Frontend, const FMIViewmodelData* View)
{
	using namespace MIShowroomPrivate;
	ViewData = View;
	const FString S = TEXT("stage.");
	const FVector Room = Vec(Frontend, S + TEXT("room.size"), FVector(1200, 1200, 600));
	UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	UStaticMesh* Cylinder = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
	const auto Piece = [this, Base](UStaticMesh* Mesh, const FVector& Centre, const FVector& SizeCm, const FLinearColor& Colour)
	{
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
		C->SetStaticMesh(Mesh);
		C->SetMobility(EComponentMobility::Movable);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetupAttachment(Root);
		C->SetRelativeLocation(Centre);
		C->SetRelativeScale3D(SizeCm / 100.0);
		if (Base)
		{
			UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(Base, C);
			M->SetVectorParameterValue(TEXT("Color"), Colour);
			C->SetMaterial(0, M);
		}
		C->RegisterComponent();
		Set.Add(C);
		return C;
	};
	// The closed room: a dark cyclorama (engine cubes until the art exists, frontend.json stage.room.mesh null).
	const FLinearColor Wall(0.018f, 0.019f, 0.022f), Floor(0.012f, 0.012f, 0.014f);
	const double T = 20.0;
	Piece(Cube, FVector(0, 0, -T * 0.5), FVector(Room.X, Room.Y, T), Floor);
	Piece(Cube, FVector(0, 0, Room.Z + T * 0.5), FVector(Room.X, Room.Y, T), Wall);
	Piece(Cube, FVector(Room.X * 0.5 + T * 0.5, 0, Room.Z * 0.5), FVector(T, Room.Y, Room.Z), Wall);
	Piece(Cube, FVector(-Room.X * 0.5 - T * 0.5, 0, Room.Z * 0.5), FVector(T, Room.Y, Room.Z), Wall);
	Piece(Cube, FVector(0, Room.Y * 0.5 + T * 0.5, Room.Z * 0.5), FVector(Room.X, T, Room.Z), Wall);
	Piece(Cube, FVector(0, -Room.Y * 0.5 - T * 0.5, Room.Z * 0.5), FVector(Room.X, T, Room.Z), Wall);
	// The steel bench under the turntable, and the turntable plate.
	const FVector BenchAt = Vec(Frontend, S + TEXT("bench.at"), FVector::ZeroVector);
	const double BenchH = MIJson::NumberOr(Frontend, S + TEXT("bench.height"), 90.0);
	Piece(Cube, BenchAt + FVector(0, 0, BenchH * 0.5), FVector(170, 90, BenchH), FLinearColor(0.05f, 0.052f, 0.056f));
	const FVector TableAt = Vec(Frontend, S + TEXT("turntable.at"), FVector(0, 0, 92));
	Piece(Cylinder, TableAt - FVector(0, 0, 1.5), FVector(74, 74, 3), FLinearColor(0.02f, 0.02f, 0.022f));
	Pivot->SetRelativeLocation(TableAt + FVector(0, 0, 14.0));

	// Lights (lux at the aim point, colour temperature in kelvin).
	if (const TSharedPtr<FJsonValue> Lights = MIJson::Get(Frontend, S + TEXT("lights")); Lights.IsValid() && Lights->Type == EJson::Array)
	{
		for (const TSharedPtr<FJsonValue>& LV : Lights->AsArray())
		{
			const TSharedPtr<FJsonObject> L = LV->AsObject();
			const FVector At = Vec(L, TEXT("at"), FVector(0, 0, 200));
			const FVector Aim = Vec(L, TEXT("aim"), FVector::ZeroVector);
			const double Lux = MIJson::NumberOr(L, TEXT("lux"), 500.0);
			const double Metres = FMath::Max(0.5, FVector::Dist(At, Aim) / 100.0);
			ULocalLightComponent* Light = nullptr;
			if (MIJson::StringOr(L, TEXT("kind")) == TEXT("spot"))
			{
				USpotLightComponent* Spot = NewObject<USpotLightComponent>(this);
				Spot->SetOuterConeAngle(MIJson::NumberOr(L, TEXT("cone"), 35.0));
				Spot->SetInnerConeAngle(MIJson::NumberOr(L, TEXT("cone"), 35.0) * 0.6);
				Light = Spot;
			}
			else
			{
				URectLightComponent* Rect = NewObject<URectLightComponent>(this);
				const FVector Size = Vec(L, TEXT("size"), FVector(100, 100, 0));
				Rect->SetSourceWidth(Size.X);
				Rect->SetSourceHeight(Size.Y);
				Light = Rect;
			}
			Light->SetupAttachment(Root);
			Light->SetMobility(EComponentMobility::Movable);
			Light->SetRelativeLocation(At);
			Light->SetRelativeRotation((Aim - At).Rotation());
			Light->SetIntensityUnits(ELightUnits::Candelas);
			Light->SetIntensity(Lux * Metres * Metres);  // E = I / d^2 at the aim point
			Light->SetAttenuationRadius(2000.0);
			Light->SetUseTemperature(true);
			Light->SetTemperature(MIJson::NumberOr(L, TEXT("kelvin"), 5000.0));
			Light->SetCastShadows(true);
			Light->RegisterComponent();
		}
	}
	// Fixed exposure, bounded by the room so the block keeps its own.
	UBoxComponent* Volume = NewObject<UBoxComponent>(this);
	Volume->SetupAttachment(Root);
	Volume->SetBoxExtent(Room * 0.5);
	Volume->SetRelativeLocation(FVector(0, 0, Room.Z * 0.5));
	Volume->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Volume->RegisterComponent();
	Post->AttachToComponent(Volume, FAttachmentTransformRules::KeepRelativeTransform);
	Post->bUnbound = false;
	const double Ev = MIJson::NumberOr(Frontend, S + TEXT("exposure.ev100"), 9.5);
	Post->Settings.bOverride_AutoExposureMinBrightness = Post->Settings.bOverride_AutoExposureMaxBrightness = true;
	Post->Settings.AutoExposureMinBrightness = Post->Settings.AutoExposureMaxBrightness = Ev;
	Post->Settings.bOverride_VignetteIntensity = true;
	Post->Settings.VignetteIntensity = 0.55f;
	Post->Settings.bOverride_BloomIntensity = true;
	Post->Settings.BloomIntensity = 0.35f;

	// Cameras and the turntable's feel.
	CamFrom = Vec(Frontend, S + TEXT("cameras.turntable.from"), CamFrom);
	CamTo = Vec(Frontend, S + TEXT("cameras.turntable.to"), CamTo);
	CamFov = MIJson::NumberOr(Frontend, S + TEXT("cameras.turntable.fov"), 30.0);
	TurntableCamera->SetFieldOfView(CamFov);
	Spin = MIJson::NumberOr(Frontend, S + TEXT("turntable.spin"), Spin);
	IdleAfter = MIJson::NumberOr(Frontend, S + TEXT("turntable.idleAfter"), IdleAfter);
	DragK = MIJson::NumberOr(Frontend, S + TEXT("turntable.drag"), DragK);
	StickK = MIJson::NumberOr(Frontend, S + TEXT("turntable.stick"), StickK);
	ZoomStep = MIJson::NumberOr(Frontend, S + TEXT("turntable.zoomStep"), ZoomStep);
	if (const TSharedPtr<FJsonValue> P = MIJson::Get(Frontend, S + TEXT("turntable.pitchClamp")); P.IsValid() && P->Type == EJson::Array && P->AsArray().Num() == 2)
	{
		PitchMin = P->AsArray()[0]->AsNumber();
		PitchMax = P->AsArray()[1]->AsNumber();
	}
	if (const TSharedPtr<FJsonValue> Z = MIJson::Get(Frontend, S + TEXT("turntable.zoom")); Z.IsValid() && Z->Type == EJson::Array && Z->AsArray().Num() == 2)
	{
		ZoomMin = Z->AsArray()[0]->AsNumber();
		ZoomMax = Z->AsArray()[1]->AsNumber();
	}
	const TSharedPtr<FJsonValue> F = MIJson::Get(Frontend, S + TEXT("cameras.focus"));
	Focus = F.IsValid() && F->Type == EJson::Object ? F->AsObject() : nullptr;
	// The arms at the eye, in a corner of the room away from the turntable.
	ArmsCamera->SetRelativeLocation(FVector(Room.X * 0.25, Room.Y * 0.25, 165.0));
	ArmsCamera->SetRelativeRotation(FRotator(-4.0, 200.0, 0.0));
	ArmsCamera->SetFieldOfView(MIJson::NumberOr(Frontend, S + TEXT("cameras.arms.fov"), 54.0));
	UseShot(EShot::Turntable);
}

void AMIShowroom::UseShot(EShot In)
{
	Shot = In;
	TurntableCamera->SetActive(In == EShot::Turntable);
	ArmsCamera->SetActive(In == EShot::Arms);
}

UCameraComponent* AMIShowroom::GetActiveCamera() const
{
	return Shot == EShot::Arms ? ArmsCamera : TurntableCamera;
}

void AMIShowroom::PlaceGunOnPivot()
{
	// Bore along the turntable's X (the presentation mesh offset), centred on the turntable.
	Gun->SetRelativeTransform(Pending.View.MeshOffset);
	Gun->UpdateBounds();
	const FVector Centre = Pivot->GetComponentTransform().InverseTransformPosition(Gun->Bounds.Origin);
	Gun->AddRelativeLocation(-Centre);
	GunCentre = FVector::ZeroVector;
}

void AMIShowroom::ShowGun(const FMIResolvedGun& InGun)
{
	if (InGun.Id != ShownGun)
	{
		// A different gun: scale out, swap, scale in (0.2 s).
		Pending = InGun;
		bPendingSwap = true;
		SwapT = ShownGun.IsNone() || bReducedMotion ? 0.1 : 0.0;
		ShownGun = InGun.Id;
		return;
	}
	if (!bPendingSwap)
	{
		Pending = InGun;
		Assembly->Assemble(Gun, InGun, true, 0.25);  // the same gun: parts slide into their sockets
	}
	else
	{
		Pending = InGun;
	}
}

void AMIShowroom::FocusSlot(FName Slot)
{
	FVector Offset = FVector::ZeroVector;
	double Z = 1.0;
	if (!Slot.IsNone() && Focus.IsValid())
	{
		Offset = MIShowroomPrivate::Vec(Focus, Slot.ToString() + TEXT(".offset"), FVector::ZeroVector);
		Z = MIJson::NumberOr(Focus, Slot.ToString() + TEXT(".zoom"), 1.0);
	}
	FocusFrom = FocusOffset;
	FocusTo = Offset;
	FocusZoomFrom = FocusZoom;
	FocusZoomTo = Z;
	FocusT = bReducedMotion ? 1.0 : 0.0;
	if (!Slot.IsNone())
	{
		Yaw = -90.0;  // the slot side faces the camera
		Touch();
	}
}

void AMIShowroom::ShowArms(const FMICrewEntry* Crew, const FMIResolvedGun& InGun)
{
	if (!ViewData)
	{
		return;
	}
	if (Crew && Crew->Id != ShownCrew)
	{
		ArmsDip = 0.0;  // the swap hides behind a 0.15 s dip
		ShownCrew = Crew->Id;
	}
	USkeletalMesh* Body = nullptr;
	if (Crew && !Crew->Arms.IsEmpty())
	{
		Body = Cast<USkeletalMesh>(FSoftObjectPath(Crew->Arms).TryLoad());
	}
	if (!Body)
	{
		Body = Cast<USkeletalMesh>(ViewData->Body.TryLoad());
	}
	if (Arms->GetSkinnedAsset() != Body)
	{
		Arms->SetSkinnedAssetAndUpdate(Body, true);
		for (const FName Bone : ViewData->BodyHiddenBones)
		{
			Arms->HideBoneByName(Bone, PBO_None);
		}
	}
	Arms->EmptyOverrideMaterials();
	if (Crew)
	{
		for (const TPair<FName, FString>& M : Crew->Materials)
		{
			if (UMaterialInterface* Mat = Cast<UMaterialInterface>(FSoftObjectPath(M.Value).TryLoad()))
			{
				Arms->SetMaterialByName(M.Key, Mat);
			}
		}
	}
	ArmsAssembly->Assemble(ArmsGun, InGun, true);
	// The hip pose of the first-person rig, settled, exactly as in play.
	FMIViewmodelData Local = *ViewData;
	Local.Guns = {InGun.View};
	FMIViewmodelRig Rig;
	Rig.Init(&Local);
	FMIWeaponView W;
	W.Weapon = InGun.Id;
	W.MagSize = W.Mag = InGun.Def.MagSize;
	for (int32 I = 0; I < 90; ++I)
	{
		Rig.Update(1.0 / 60.0, W, 0.0, false, FMIViewmodelPlayer());
	}
	const FTransform GunT = InGun.View.MeshOffset * Rig.GetGunTransform();
	ArmsGun->SetRelativeTransform(GunT);
	if (Arms->GetSkinnedAsset() && !ViewData->BodyHandSocket.IsNone() && Arms->DoesSocketExist(ViewData->BodyHandSocket))
	{
		const FTransform Grip(GunT.GetRotation(), Rig.GunPointInCamera(InGun.View.Marker(TEXT("grip"))));
		const FTransform Hand = Arms->GetSocketTransform(ViewData->BodyHandSocket, RTS_Component);
		Arms->SetRelativeTransform(Hand.Inverse() * Grip);
	}
	if (UAnimSequence* Idle = Cast<UAnimSequence>(InGun.View.Idle.TryLoad()))
	{
		Arms->SetAnimationMode(EAnimationMode::AnimationSingleNode);
		Arms->PlayAnimation(Idle, true);
	}
}

void AMIShowroom::Drag(const FVector2D& Pixels)
{
	Yaw += Pixels.X * DragK;
	Pitch = FMath::Clamp(Pitch - Pixels.Y * DragK, PitchMin, PitchMax);
	Touch();
}

void AMIShowroom::Zoom(float Steps)
{
	ZoomK = FMath::Clamp(ZoomK * (1.0 - Steps * ZoomStep), ZoomMin, ZoomMax);
	Touch();
}

void AMIShowroom::Stick(const FVector2D& Value, float ZoomAxis)
{
	if (Value.SizeSquared() > 0.04 || FMath::Abs(ZoomAxis) > 0.1f)
	{
		Yaw += Value.X * StickK * 0.016;
		Pitch = FMath::Clamp(Pitch + Value.Y * StickK * 0.016, PitchMin, PitchMax);
		ZoomK = FMath::Clamp(ZoomK * (1.0 - ZoomAxis * 0.016), ZoomMin, ZoomMax);
		Touch();
	}
}

void AMIShowroom::Tick(float DeltaSeconds)
{
	using namespace MIShowroomPrivate;
	Super::Tick(DeltaSeconds);
	const double Dt = DeltaSeconds;
	SinceTouch += Dt;
	if (SinceTouch > IdleAfter && !bReducedMotion)
	{
		Yaw += Spin * Dt;  // spins by itself until touched, and again 3 s after the last touch
	}
	// Gun swap: 0.1 s out, swap, 0.1 s in.
	double Scale = 1.0;
	if (SwapT < 0.2)
	{
		const double Before = SwapT;
		SwapT += Dt;
		if (bPendingSwap && Before < 0.1 && SwapT >= 0.1)
		{
			bPendingSwap = false;
			Assembly->Clear();
			Assembly->Assemble(Gun, Pending, true);
			PlaceGunOnPivot();
		}
		Scale = SwapT < 0.1 ? 1.0 - SwapT / 0.1 : (SwapT - 0.1) / 0.1;
	}
	else if (bPendingSwap)
	{
		bPendingSwap = false;
		Assembly->Assemble(Gun, Pending, true);
		PlaceGunOnPivot();
	}
	Pivot->SetRelativeScale3D(FVector(FMath::Max(0.01, Ease(Scale))));
	Pivot->SetRelativeRotation(FRotator(0.0, Yaw, 0.0));
	// The turntable camera: orbit pitch about the look-at point, zoom along the line, eased slot focus.
	FocusT = FMath::Min(1.0, FocusT + Dt / FMath::Max(0.01, FocusSecs));
	const double K = Ease(FocusT);
	FocusOffset = FMath::Lerp(FocusFrom, FocusTo, K);
	FocusZoom = FMath::Lerp(FocusZoomFrom, FocusZoomTo, K);
	const FVector Target = CamTo + Pivot->GetRelativeRotation().RotateVector(FocusOffset);
	const FVector Arm = FRotator(Pitch, 0.0, 0.0).RotateVector(CamFrom - CamTo) / (ZoomK * FocusZoom);
	TurntableCamera->SetRelativeLocation(Target + Arm);
	TurntableCamera->SetRelativeRotation((-Arm).Rotation());
	// The arms' dip to black on a crew change.
	if (ArmsDip < 0.15)
	{
		ArmsDip += Dt;
	}
	Arms->SetVisibility(ArmsDip >= 0.075);
	ArmsGun->SetVisibility(ArmsDip >= 0.075);
}
