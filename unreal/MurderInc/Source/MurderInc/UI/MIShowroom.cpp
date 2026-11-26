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
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
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
	// The block's art materials dress the set where the project has them (frontend.json stage.materials: world-projected
	// instances of the street's scans, review 2026-11-24: a flat brown slab and a navy wall read as a grey box); a piece
	// whose material does not load keeps its flat colour.
	const auto Dress = [&Frontend, &S](UStaticMeshComponent* C, const TCHAR* Key)
	{
		const FString Path = MIJson::StringOr(Frontend, S + TEXT("materials.") + Key);
		if (C && !Path.IsEmpty())
		{
			if (UMaterialInterface* M = Cast<UMaterialInterface>(FSoftObjectPath(Path).TryLoad()))
			{
				C->SetMaterial(0, M);
			}
		}
	};
	// The closed room: a dark cyclorama (engine cubes until the art exists, frontend.json stage.room.mesh null).
	const FLinearColor Wall(0.018f, 0.019f, 0.022f), Floor(0.012f, 0.012f, 0.014f);
	const double T = 20.0;
	Dress(Piece(Cube, FVector(0, 0, -T * 0.5), FVector(Room.X, Room.Y, T), Floor), TEXT("floor"));
	Dress(Piece(Cube, FVector(0, 0, Room.Z + T * 0.5), FVector(Room.X, Room.Y, T), Wall), TEXT("ceiling"));
	Dress(Piece(Cube, FVector(Room.X * 0.5 + T * 0.5, 0, Room.Z * 0.5), FVector(T, Room.Y, Room.Z), Wall), TEXT("backWall"));
	Dress(Piece(Cube, FVector(-Room.X * 0.5 - T * 0.5, 0, Room.Z * 0.5), FVector(T, Room.Y, Room.Z), Wall), TEXT("walls"));
	Dress(Piece(Cube, FVector(0, Room.Y * 0.5 + T * 0.5, Room.Z * 0.5), FVector(Room.X, T, Room.Z), Wall), TEXT("walls"));
	Dress(Piece(Cube, FVector(0, -Room.Y * 0.5 - T * 0.5, Room.Z * 0.5), FVector(Room.X, T, Room.Z), Wall), TEXT("walls"));
	// The steel bench under the turntable (a top on a darker frame), and the turntable plate.
	const FVector BenchAt = Vec(Frontend, S + TEXT("bench.at"), FVector::ZeroVector);
	const double BenchH = MIJson::NumberOr(Frontend, S + TEXT("bench.height"), 90.0);
	const double TopT = 5.0;
	Dress(Piece(Cube, BenchAt + FVector(0, 0, (BenchH - TopT) * 0.5), FVector(160, 80, BenchH - TopT), FLinearColor(0.03f, 0.031f, 0.034f)), TEXT("benchFrame"));
	Dress(Piece(Cube, BenchAt + FVector(0, 0, BenchH - TopT * 0.5), FVector(176, 94, TopT), FLinearColor(0.05f, 0.052f, 0.056f)), TEXT("bench"));
	const FVector TableAt = Vec(Frontend, S + TEXT("turntable.at"), FVector(0, 0, 92));
	Dress(Piece(Cylinder, TableAt - FVector(0, 0, 1.5), FVector(74, 74, 3), FLinearColor(0.02f, 0.02f, 0.022f)), TEXT("turntable"));
	Pivot->SetRelativeLocation(TableAt + FVector(0, 0, 14.0));
	PlateTop = TableAt.Z - Pivot->GetRelativeLocation().Z;

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
	// The arms at the eye, over the bench where the stage lights fall (the turntable gun hides meanwhile).
	ArmsCamera->SetRelativeLocation(TableAt + FVector(-60.0, -4.0, 62.0));
	ArmsCamera->SetRelativeRotation(FRotator(-6.0, 0.0, 0.0));
	// The arms exactly as in play: first-person rendering with the viewmodel field of view and scale (the player rig's
	// camera settings), so the closed shoulders and the body never show.
	const double ArmsFov = MIJson::NumberOr(Frontend, S + TEXT("cameras.arms.fov"), 54.0);
	const double HFov = FMath::RadiansToDegrees(2.0 * FMath::Atan(FMath::Tan(FMath::DegreesToRadians(ArmsFov) * 0.5) * 16.0 / 9.0));
	ArmsCamera->SetFieldOfView(HFov);
	ArmsCamera->bEnableFirstPersonFieldOfView = true;
	ArmsCamera->bEnableFirstPersonScale = true;
	ArmsCamera->SetFirstPersonFieldOfView(HFov);
	ArmsCamera->SetFirstPersonScale(View ? View->FirstPersonScale : 0.6);
	Arms->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::FirstPerson);
	ArmsGun->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::FirstPerson);
	// The Workbench's slot light: a tight warm spot on the mount being fitted (off until a slot is focused).
	SlotLight = NewObject<USpotLightComponent>(this);
	SlotLight->SetupAttachment(Root);
	SlotLight->SetMobility(EComponentMobility::Movable);
	SlotLight->SetIntensityUnits(ELightUnits::Candelas);
	SlotLight->SetOuterConeAngle(14.f);
	SlotLight->SetInnerConeAngle(6.f);
	SlotLight->SetAttenuationRadius(600.f);
	SlotLight->SetUseTemperature(true);
	SlotLight->SetTemperature(4600.f);
	SlotLight->SetIntensity(0.f);
	SlotLight->RegisterComponent();
	UseShot(EShot::Turntable);
}

FSphere AMIShowroom::GetGunSphere() const
{
	return FSphere(Pivot->GetRelativeLocation() + Pivot->GetRelativeRotation().RotateVector(GunCentre), GunRadius);
}

bool AMIShowroom::FindSlotLocal(FVector& Out) const
{
	// The mount socket on the shown mesh, in the turntable's own frame (no spin, no swap scale).
	if (!FocusSocket.IsNone() && Gun->GetSkinnedAsset() && Gun->DoesSocketExist(FocusSocket))
	{
		Out = (Gun->GetSocketTransform(FocusSocket, RTS_Component) * Gun->GetRelativeTransform()).GetLocation();
		return true;
	}
	// No such socket (a template stand-in, the stock): frontend.json's offset for the slot, in the gun's frame.
	if (!FocusedSlot.IsNone() && Focus.IsValid())
	{
		Out = MIShowroomPrivate::Vec(Focus, FocusedSlot.ToString() + TEXT(".offset"), FVector::ZeroVector) + GunCentre;  // the gun's frame, raised with it
		return true;
	}
	return false;
}

void AMIShowroom::UseShot(EShot In)
{
	Shot = In;
	TurntableCamera->SetActive(In == EShot::Turntable);
	ArmsCamera->SetActive(In == EShot::Arms);
	Pivot->SetVisibility(In == EShot::Turntable, true);
	Arms->SetVisibility(In == EShot::Arms);
	ArmsGun->SetVisibility(In == EShot::Arms, true);
}

UCameraComponent* AMIShowroom::GetActiveCamera() const
{
	return Shot == EShot::Arms ? ArmsCamera : TurntableCamera;
}

void AMIShowroom::PlaceGunOnPivot()
{
	// Bore along the turntable's X (the presentation mesh offset), centred on the turntable.
	// From the mesh asset's own bounds (not the component's, which follow the swap's scale animation).
	Gun->SetRelativeTransform(Pending.View.MeshOffset);
	if (const USkinnedAsset* Asset = Gun->GetSkinnedAsset())
	{
		const FBoxSphereBounds B = Asset->GetBounds();
		const FVector Centre = Pending.View.MeshOffset.TransformPosition(B.Origin);
		Gun->AddRelativeLocation(-Centre);
		GunRadius = FMath::Clamp(B.BoxExtent.Size(), 10.0, 120.0);  // the box's own sphere: the whole gun at any turn
	}
	GunCentre = FVector::ZeroVector;
	StandLift = 0.0;
	ApplyStandLift(WantedLift());  // a new gun: stood clear of the plate at once (it is scaled out meanwhile)
}

bool AMIShowroom::HasGunMesh() const
{
	return Gun && Gun->GetSkinnedAsset() != nullptr && Gun->IsVisible();
}

double AMIShowroom::LowestInPivot() const
{
	// Every visible primitive of the gun (the mesh and the parts the assembly attached to it, the factory magazine
	// included), in the turntable's own frame: the spin is about z and the swap scale about the origin, so neither
	// changes the order of heights.
	const FTransform PivotT = Pivot->GetComponentTransform();
	double Low = TNumericLimits<double>::Max();
	const auto Take = [&Low](const FBoxSphereBounds& B) { Low = FMath::Min(Low, B.Origin.Z - B.BoxExtent.Z); };
	if (const USkinnedAsset* Asset = Gun->GetSkinnedAsset(); Asset && Gun->IsVisible())
	{
		Take(Asset->GetBounds().TransformBy(Gun->GetComponentTransform().GetRelativeTransform(PivotT)));
	}
	TArray<USceneComponent*> Pieces;
	Gun->GetChildrenComponents(true, Pieces);
	for (const USceneComponent* C : Pieces)
	{
		const UStaticMeshComponent* P = Cast<UStaticMeshComponent>(C);
		if (P && P->IsVisible() && P->GetStaticMesh())
		{
			Take(P->GetStaticMesh()->GetBounds().TransformBy(P->GetComponentTransform().GetRelativeTransform(PivotT)));
		}
	}
	return Low == TNumericLimits<double>::Max() ? PlateTop + PlateClearance + StandLift : Low;
}

double AMIShowroom::WantedLift() const
{
	// The lowest point as it would be with no raise, and the raise that puts it PlateClearance above the plate.
	return FMath::Max(0.0, PlateTop + PlateClearance - (LowestInPivot() - StandLift));
}

void AMIShowroom::ApplyStandLift(double Lift)
{
	Gun->AddRelativeLocation(FVector(0.0, 0.0, Lift - StandLift));
	StandLift = Lift;
	GunCentre = FVector(0.0, 0.0, StandLift);  // the camera frames the raised gun
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

void AMIShowroom::FocusSlot(FName Slot, FName Socket)
{
	if (Slot == FocusedSlot && Socket == FocusSocket)
	{
		return;
	}
	FocusedSlot = Slot;
	FocusSocket = Socket;
	FocusFrom = FocusOffset;
	FocusZoomFrom = FocusZoom;
	FocusZoomTo = 1.0;
	FocusT = bReducedMotion ? 1.0 : 0.0;
	bAimSlot = !Slot.IsNone();
	if (Slot.IsNone())
	{
		FocusTo = FVector::ZeroVector;
	}
	Touch();
}

bool AMIShowroom::ShowArms(const FMICrewEntry* Crew, const FMIResolvedGun& InGun)
{
	if (!ViewData)
	{
		return false;
	}
	if (Crew && Crew->Id != ShownCrew)
	{
		ArmsDip = 0.0;  // the swap hides behind a 0.15 s dip
		ShownCrew = Crew->Id;
	}
	// Only the member's own arms: the template body seen this close shows its open shoulders (LOADOUT.md 2.4).
	USkeletalMesh* Body = nullptr;
	if (Crew && !Crew->Arms.IsEmpty())
	{
		Body = Cast<USkeletalMesh>(FSoftObjectPath(Crew->Arms).TryLoad());
	}
	if (!Body)
	{
		return false;
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
	ArmsGrip = FTransform(GunT.GetRotation(), Rig.GunPointInCamera(InGun.View.Marker(TEXT("grip"))));
	if (UAnimSequence* Idle = Cast<UAnimSequence>(InGun.View.Idle.TryLoad()))
	{
		Arms->SetAnimationMode(EAnimationMode::AnimationSingleNode);
		Arms->PlayAnimation(Idle, true);
	}
	PlaceArmsOnGrip();
	return true;
}

void AMIShowroom::PlaceArmsOnGrip()
{
	// As in play (UMIWeaponComponent::PoseView): every frame the body is placed so that its hand socket, in the pose the
	// clip gives it now, holds the gun's grip.
	if (ViewData && Arms->GetSkinnedAsset() && !ViewData->BodyHandSocket.IsNone() && Arms->DoesSocketExist(ViewData->BodyHandSocket))
	{
		const FTransform Hand = Arms->GetSocketTransform(ViewData->BodyHandSocket, RTS_Component);
		Arms->SetRelativeTransform(Hand.Inverse() * ArmsGrip);
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
	if (SinceTouch > IdleAfter && !bReducedMotion && FocusedSlot.IsNone())
	{
		Yaw += Spin * Dt;  // spins by itself until touched, and again 3 s after the last touch; never on a slot focus
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
	// The same gun with a part changed (a longer magazine slides in): the stand rises or settles with it, eased.
	if (!bPendingSwap && Shot == EShot::Turntable)
	{
		const double Want = WantedLift();
		if (!FMath::IsNearlyEqual(Want, StandLift, 0.01))
		{
			ApplyStandLift(bReducedMotion ? Want : FMath::FInterpTo(StandLift, Want, static_cast<float>(Dt), 14.f));
		}
	}
	// The slot focus: once the mesh is in place, the gun turns the mount's side to the camera and the camera looks
	// from above for a top mount, from below for an underbarrel one.
	FVector Local;
	const bool bSlot = !bPendingSwap && FindSlotLocal(Local);
	if (bSlot)
	{
		SlotLocal = Local;
		if (bAimSlot)
		{
			bAimSlot = false;
			Yaw = SlotLocal.Y > 0.5 ? 90.0 : -90.0;  // the camera stands on the -X side: this turns the mount's side to it
			Pitch = FMath::Clamp(SlotLocal.Z > 2.0 ? 18.0 : SlotLocal.Z < -2.0 ? -14.0 : 6.0, PitchMin, PitchMax);
		}
		FocusTo = SlotLocal;
	}
	FocusT = FMath::Min(1.0, FocusT + Dt / FMath::Max(0.01, FocusSecs));
	const double K = Ease(FocusT);
	FocusOffset = FMath::Lerp(FocusFrom, FocusTo, K);
	FocusZoom = FMath::Lerp(FocusZoomFrom, FocusZoomTo, K);
	const FVector Centre = Pivot->GetRelativeLocation() + Pivot->GetRelativeRotation().RotateVector(GunCentre);
	const FVector Mount = Pivot->GetRelativeLocation() + Pivot->GetRelativeRotation().RotateVector(FocusOffset);
	// The camera aims half way to the mount, so the part sits near the middle of the free part of the screen while the
	// whole gun still fits there.
	AimPoint = FMath::Lerp(Centre, Mount, 0.5);
	const FVector Fwd = -FRotator(Pitch, 0.0, 0.0).RotateVector((CamFrom - CamTo).GetSafeNormal());
	const FRotator Look = Fwd.Rotation();
	const FVector Right = FRotationMatrix(Look).GetScaledAxis(EAxis::Y);
	const FVector Up = FRotationMatrix(Look).GetScaledAxis(EAxis::Z);
	double Aspect = 16.0 / 9.0;
	if (const UGameViewportClient* Viewport = GetWorld() ? GetWorld()->GetGameViewport() : nullptr)
	{
		FVector2D Size;
		Viewport->GetViewportSize(Size);
		Aspect = Size.Y > 1.0 ? Size.X / Size.Y : Aspect;
	}
	const double TanH = FMath::Tan(FMath::DegreesToRadians(CamFov * 0.5));
	const double TanV = TanH / Aspect;
	// The aim point sits at the middle of the free part (X0); the gun's sphere must fit between its edges.
	const double X0 = (FreeLeft + FreeRight) * 0.5;
	const FVector O = Centre - AimPoint;
	const double Ox = O | Right, Oy = O | Up, Oz = O | Fwd;
	const double Depth = FMath::Max3((GunRadius - Ox) / ((X0 - FreeLeft) * TanH), (GunRadius + Ox) / ((FreeRight - X0) * TanH), (FMath::Abs(Oy) + GunRadius) / (FreeHalfHeight * TanV));
	const double Distance = FMath::Max(60.0, Depth - Oz) / (ZoomK * FocusZoom);
	const FVector Camera = AimPoint - Fwd * Distance - Right * (X0 * Distance * TanH);
	TurntableCamera->SetRelativeLocation(Camera);
	TurntableCamera->SetRelativeRotation(Look);
	// The slot light follows the mount.
	if (SlotLight)
	{
		const bool bLit = !FocusedSlot.IsNone() && bSlot;
		const FVector From = Mount + FVector(0.0, 0.0, 55.0) - Fwd * 45.0;
		SlotLight->SetRelativeLocation(From);
		SlotLight->SetRelativeRotation((Mount - From).Rotation());
		const double M = FVector::Dist(From, Mount) / 100.0;
		SlotLight->SetIntensity(bLit ? static_cast<float>(900.0 * M * M * K) : 0.f);  // about 900 lux on the mount
	}
	if (Shot == EShot::Arms)
	{
		PlaceArmsOnGrip();
	}
	// The arms' dip to black on a crew change.
	if (ArmsDip < 0.15)
	{
		ArmsDip += Dt;
	}
	if (Shot == EShot::Arms)
	{
		Arms->SetVisibility(ArmsDip >= 0.075);
		ArmsGun->SetVisibility(ArmsDip >= 0.075, true);
	}
}
