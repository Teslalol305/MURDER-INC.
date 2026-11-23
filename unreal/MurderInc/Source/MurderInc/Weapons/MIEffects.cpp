#include "Weapons/MIEffects.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/DecalComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Core/Data/MILoadoutData.h"
#include "Core/MIDamageable.h"
#include "Core/MIEvents.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Weapons/MICombatSubsystem.h"
#include "MurderInc.h"

namespace MIEffectsPrivate
{
	constexpr int32 NumPuffs = 96, NumCards = 9, NumLights = 6, NumMarks = 72, NumStreaks = 24;

	template <typename T>
	T* LoadAs(const FString& Path)
	{
		return Path.IsEmpty() ? nullptr : Cast<T>(FSoftObjectPath(Path).TryLoad());
	}

	FLinearColor Color(const TSharedPtr<FJsonObject>& O, const FString& Path, const FLinearColor& Fallback)
	{
		const TSharedPtr<FJsonValue> V = MIJson::Get(O, Path);
		if (!V.IsValid() || V->Type != EJson::Array || V->AsArray().Num() < 3)
		{
			return Fallback;
		}
		const TArray<TSharedPtr<FJsonValue>>& A = V->AsArray();
		return FLinearColor(A[0]->AsNumber(), A[1]->AsNumber(), A[2]->AsNumber(), 1.f);
	}

	bool IsEnemy(const AActor* A)
	{
		const IMIDamageable* D = Cast<IMIDamageable>(A);
		return D && D->GetMIDamageableKind() == TEXT("enemy");
	}

	void Quiet(UPrimitiveComponent* C)
	{
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetCastShadow(false);
		C->SetMobility(EComponentMobility::Movable);
		C->SetVisibility(false);
		C->SetUsingAbsoluteLocation(true);
		C->SetUsingAbsoluteRotation(true);
		C->SetUsingAbsoluteScale(true);
	}
}

UMIEffects* UMIEffects::Get(const UObject* WorldContext)
{
	const UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	return World ? World->GetSubsystem<UMIEffects>() : nullptr;
}

void UMIEffects::OnWorldBeginPlay(UWorld& InWorld)
{
	using namespace MIEffectsPrivate;
	Super::OnWorldBeginPlay(InWorld);
	if (!InWorld.IsGameWorld())
	{
		return;
	}
	TSharedPtr<FJsonObject> Root;
	FString Error;
	if (!UMIDataSubsystem::LoadJsonFile(TEXT("presentation.json"), Root, Error))
	{
		return;
	}
	const TSharedPtr<FJsonValue> F = MIJson::Get(Root, TEXT("fx"));
	Fx = F.IsValid() && F->Type == EJson::Object ? F->AsObject() : nullptr;
	FlashMat = LoadAs<UMaterialInterface>(MIJson::StringOr(Fx, TEXT("materials.flash")));
	SmokeMat = LoadAs<UMaterialInterface>(MIJson::StringOr(Fx, TEXT("materials.smoke")));
	TracerMat = LoadAs<UMaterialInterface>(MIJson::StringOr(Fx, TEXT("materials.tracer")));
	MarkMat = LoadAs<UMaterialInterface>(MIJson::StringOr(Fx, TEXT("materials.mark")));
	DebrisMat = LoadAs<UMaterialInterface>(MIJson::StringOr(Fx, TEXT("materials.debris")));
	BrassMat = LoadAs<UMaterialInterface>(MIJson::StringOr(Fx, TEXT("materials.brass")));
	Plane = LoadAs<UStaticMesh>(TEXT("/Engine/BasicShapes/Plane.Plane"));
	Cylinder = LoadAs<UStaticMesh>(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	Cube = LoadAs<UStaticMesh>(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (!FlashMat || !SmokeMat || !Plane)
	{
		UE_LOG(LogMI, Log, TEXT("Effects: the /Game/FX materials are not in this project (tools/box/fp/import-chars.sh fx): none drawn"));
		return;
	}
	FActorSpawnParameters P;
	P.ObjectFlags |= RF_Transient;
	Host = InWorld.SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity, P);
	if (!Host)
	{
		return;
	}
	USceneComponent* HostRoot = NewObject<USceneComponent>(Host, TEXT("Root"));
	Host->SetRootComponent(HostRoot);
	HostRoot->RegisterComponent();
	const auto Mesh = [this](UStaticMesh* M, UMaterialInterface* Mat, UMaterialInstanceDynamic*& OutMid)
	{
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(Host);
		C->SetStaticMesh(M);
		Quiet(C);
		OutMid = Mat ? UMaterialInstanceDynamic::Create(Mat, C) : nullptr;
		if (OutMid) C->SetMaterial(0, OutMid);
		C->RegisterComponent();
		return C;
	};
	for (int32 I = 0; I < NumPuffs; ++I)
	{
		FPuff& X = Puffs.AddDefaulted_GetRef();
		UMaterialInstanceDynamic* Mid = nullptr;
		X.Mesh = Mesh(Plane, SmokeMat, Mid);
		X.Mat = Mid;
		X.Mesh->SetTranslucentSortPriority(1);
	}
	for (int32 I = 0; I < NumCards; ++I)
	{
		FCard& X = Cards.AddDefaulted_GetRef();
		UMaterialInstanceDynamic* Mid = nullptr;
		X.Mesh = Mesh(Plane, FlashMat, Mid);
		X.Mat = Mid;
	}
	for (int32 I = 0; I < NumStreaks && TracerMat && Cylinder; ++I)
	{
		FStreak& X = Streaks.AddDefaulted_GetRef();
		UMaterialInstanceDynamic* Mid = nullptr;
		X.Mesh = Mesh(Cylinder, TracerMat, Mid);
	}
	for (int32 I = 0; I < NumLights; ++I)
	{
		FLight& X = Lights.AddDefaulted_GetRef();
		X.Light = NewObject<UPointLightComponent>(Host);
		X.Light->SetMobility(EComponentMobility::Movable);
		X.Light->SetUsingAbsoluteLocation(true);
		X.Light->SetIntensityUnits(ELightUnits::Candelas);
		X.Light->SetIntensity(0.f);
		X.Light->SetCastShadows(false);
		X.Light->SetVisibility(false);
		X.Light->RegisterComponent();
	}
	for (int32 I = 0; I < NumMarks && MarkMat; ++I)
	{
		FMark& X = Marks.AddDefaulted_GetRef();
		X.Decal = NewObject<UDecalComponent>(Host);
		X.Decal->SetUsingAbsoluteLocation(true);
		X.Decal->SetUsingAbsoluteRotation(true);
		X.Mat = UMaterialInstanceDynamic::Create(MarkMat, X.Decal);
		X.Decal->SetDecalMaterial(X.Mat);
		X.Decal->SetFadeScreenSize(0.f);
		X.Decal->SetVisibility(false);
		X.Decal->RegisterComponent();
	}
	Bind();
	bReady = true;
}

void UMIEffects::Bind()
{
	FMIGameEvents* Events = UMIEventSubsystem::Get(this);
	if (!Events)
	{
		return;
	}
	Handles.Add(Events->Impact.AddUObject(this, &UMIEffects::OnImpact));
	Handles.Add(Events->Explosion.AddUObject(this, &UMIEffects::OnExplosion));
}

void UMIEffects::Deinitialize()
{
	if (FMIGameEvents* Events = UMIEventSubsystem::Get(this))
	{
		if (Handles.Num() == 2)
		{
			Events->Impact.Remove(Handles[0]);
			Events->Explosion.Remove(Handles[1]);
		}
	}
	Handles.Reset();
	bReady = false;
	Super::Deinitialize();
}

// --- the pieces ----------------------------------------------------------------------------------------------

void UMIEffects::Puff(const FVector& Pos, const FVector& Vel, double Life, double Size0, double Size1, double Opacity, const FLinearColor& Color, double Fire, double Drag, double Rise)
{
	if (Puffs.Num() == 0)
	{
		return;
	}
	FPuff& X = Puffs[NextPuff];
	NextPuff = (NextPuff + 1) % Puffs.Num();
	X.Pos = Pos;
	X.Vel = Vel;
	X.Age = 0.0;
	X.Life = Life;
	X.Size0 = Size0;
	X.Size1 = Size1;
	X.Opacity = Opacity;
	X.Fire = Fire;
	X.Drag = Drag;
	X.Rise = Rise;
	X.Roll = FMath::FRandRange(0.0, 360.0);
	X.Spin = FMath::FRandRange(-25.0, 25.0);
	if (X.Mat)
	{
		X.Mat->SetVectorParameterValue(TEXT("Color"), Color);
		X.Mat->SetScalarParameterValue(TEXT("Seed"), FMath::FRandRange(0.f, 50.f));
		X.Mat->SetScalarParameterValue(TEXT("Fire"), static_cast<float>(Fire));
	}
	X.Mesh->SetVisibility(true);
}

void UMIEffects::Mark(const FVector& Point, const FVector& Normal, double Size, double Kind, const FLinearColor& Tint, double Life)
{
	if (Marks.Num() == 0)
	{
		return;
	}
	FMark& X = Marks[NextMark];
	NextMark = (NextMark + 1) % Marks.Num();
	X.Age = 0.0;
	X.Life = Life;
	FRotator R = FRotationMatrix::MakeFromX(-Normal).Rotator();
	R.Roll = FMath::FRandRange(0.0, 360.0);
	X.Decal->SetWorldLocationAndRotation(Point, R);
	X.Decal->DecalSize = FVector(6.0, Size * 0.5, Size * 0.5);
	X.Decal->MarkRenderStateDirty();
	X.Mat->SetScalarParameterValue(TEXT("Kind"), static_cast<float>(Kind));
	X.Mat->SetScalarParameterValue(TEXT("Seed"), FMath::FRandRange(0.f, 50.f));
	X.Mat->SetScalarParameterValue(TEXT("Fade"), 1.f);
	X.Mat->SetVectorParameterValue(TEXT("Tint"), Tint);
	X.Decal->SetVisibility(true);
}

void UMIEffects::Light(const FVector& At, double Candela, double Radius, double Life, const FLinearColor& Color)
{
	if (Lights.Num() == 0)
	{
		return;
	}
	FLight& X = Lights[NextLight];
	NextLight = (NextLight + 1) % Lights.Num();
	X.Age = 0.0;
	X.Life = Life;
	X.Peak = Candela;
	X.Light->SetWorldLocation(At);
	X.Light->SetAttenuationRadius(Radius);
	X.Light->SetLightColor(Color);
	X.Light->SetIntensity(Candela);
	X.Light->SetVisibility(true);
}

void UMIEffects::FlashLight(const FVector& At, double Scale)
{
	const double Cd = MIJson::NumberOr(Fx, TEXT("flash.candela"), 900.0) * Scale;
	Light(At, Cd, MIJson::NumberOr(Fx, TEXT("flash.radius"), 700.0), MIJson::NumberOr(Fx, TEXT("flash.light"), 0.05),
		MIEffectsPrivate::Color(Fx, TEXT("flash.color"), FLinearColor(1.0f, 0.62f, 0.3f)));
}

void UMIEffects::WorldFlash(const FVector& Muzzle, const FVector& Dir, double Scale, bool bLight)
{
	if (Cards.Num() < 3)
	{
		return;
	}
	const double L = MIJson::NumberOr(Fx, TEXT("flash.life"), 0.045);
	const FVector D = Dir.GetSafeNormal();
	// One card across the bore (the star seen down the barrel), two along it (the jet seen from the side), crossed.
	for (int32 K = 0; K < 3; ++K)
	{
		FCard& X = Cards[NextCard];
		NextCard = (NextCard + 1) % Cards.Num();
		X.Age = 0.0;
		X.Life = L;
		const double Len = (K == 0 ? 14.0 : 26.0) * Scale;
		FRotator R;
		FVector At = Muzzle;
		if (K == 0)
		{
			R = FRotationMatrix::MakeFromZ(D).Rotator();
		}
		else
		{
			// the plane's normal square to the bore, its +X (U) along the bore
			const FVector Side = FVector::CrossProduct(D, K == 1 ? FVector::UpVector : FVector::RightVector).GetSafeNormal();
			R = FRotationMatrix::MakeFromXZ(D, Side).Rotator();
			At += D * Len * 0.5;
		}
		X.Mesh->SetWorldLocationAndRotation(At, R);
		X.Mesh->SetWorldScale3D(FVector(Len / 100.0, (K == 0 ? Len : Len * 0.45) / 100.0, 1.0));
		X.Mat->SetScalarParameterValue(TEXT("Mode"), K == 0 ? 0.f : 1.f);
		X.Mat->SetScalarParameterValue(TEXT("Seed"), FMath::FRandRange(0.f, 50.f));
		X.Mesh->SetVisibility(true);
	}
	if (bLight)
	{
		FlashLight(Muzzle + D * 10.0, Scale);
	}
}

void UMIEffects::Tracer(const FVector& From, const FVector& To, double SpeedCmPerS)
{
	if (Streaks.Num() == 0 || SpeedCmPerS <= 0.0)
	{
		return;
	}
	FStreak& X = Streaks[NextStreak];
	NextStreak = (NextStreak + 1) % Streaks.Num();
	X.From = From;
	X.To = To;
	X.Age = 0.0;
	X.Length = MIJson::NumberOr(Fx, TEXT("tracer.length"), 260.0);
	X.Life = FVector::Dist(From, To) / SpeedCmPerS;
	const double R = MIJson::NumberOr(Fx, TEXT("tracer.radius"), 0.5);
	X.Mesh->SetWorldScale3D(FVector(R / 50.0, R / 50.0, X.Length / 100.0));
	X.Mesh->SetWorldRotation(FRotationMatrix::MakeFromZ(To - From).Rotator());
	X.Mesh->SetWorldLocation(From);
	X.Mesh->SetVisibility(false);  // shown from its second frame, once it has left the muzzle flash
}

void UMIEffects::EnemyShot(const AActor* Shooter, const FVector& Muzzle, const FVector& Dir)
{
	if (!bReady)
	{
		return;
	}
	WorldFlash(Muzzle, Dir, MIJson::NumberOr(Fx, TEXT("flash.enemyScale"), 0.8), true);
	UWorld* World = GetWorld();
	FHitResult Hit;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(MIFxTracer), false, Shooter);
	const FVector End = Muzzle + Dir.GetSafeNormal() * 8000.0;
	const FVector To = World && World->LineTraceSingleByChannel(Hit, Muzzle, End, ECC_Visibility, Q) ? Hit.ImpactPoint : End;
	Tracer(Muzzle + Dir.GetSafeNormal() * 40.0, To, MIJson::NumberOr(Fx, TEXT("tracer.speed"), 26000.0));
}

void UMIEffects::Casing(UStaticMesh* Mesh, const FTransform& At, const FVector& Velocity)
{
	const bool bOwn = Mesh != nullptr;
	SpawnBody(this, bOwn ? Mesh : Cylinder.Get(), bOwn ? At : FTransform(At.GetRotation(), At.GetLocation(), FVector(0.009, 0.009, 0.019)), Velocity,
		FVector(FMath::FRandRange(-900.0, 900.0), FMath::FRandRange(-1400.0, 1400.0), FMath::FRandRange(-300.0, 300.0)),
		MIJson::NumberOr(Fx, TEXT("casing.life"), 4.0), bOwn ? nullptr : BrassMat.Get());
}

void UMIEffects::SpawnBody(const UObject* WorldContext, UStaticMesh* Mesh, const FTransform& At, const FVector& Velocity, const FVector& SpinDeg, double Life, UMaterialInterface* Material)
{
	UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	if (!World || !Mesh || !World->IsGameWorld())
	{
		return;
	}
	FActorSpawnParameters P;
	P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	P.ObjectFlags |= RF_Transient;
	AStaticMeshActor* A = World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), At, P);
	if (!A)
	{
		return;
	}
	UStaticMeshComponent* C = A->GetStaticMeshComponent();
	C->SetMobility(EComponentMobility::Movable);
	C->SetStaticMesh(Mesh);
	C->SetWorldScale3D(At.GetScale3D());
	if (Material) C->SetMaterial(0, Material);
	C->SetCollisionProfileName(TEXT("PhysicsActor"));
	C->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
	C->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
	C->SetCollisionResponseToChannel(MIBulletChannel, ECR_Ignore);
	C->BodyInstance.bUseCCD = true;
	C->SetCastShadow(true);
	C->SetSimulatePhysics(true);
	C->SetPhysicsLinearVelocity(Velocity);
	C->SetPhysicsAngularVelocityInDegrees(SpinDeg);
	A->SetLifeSpan(Life);
}

// --- the hooks -----------------------------------------------------------------------------------------------

FLinearColor UMIEffects::SurfaceColor(FName Surface, bool& bSparks) const
{
	const FString Key = TEXT("surfaces.") + Surface.ToString();
	const TSharedPtr<FJsonValue> S = MIJson::Get(Fx, Key);
	bSparks = false;
	if (!S.IsValid())
	{
		return MIEffectsPrivate::Color(Fx, TEXT("surfaces.default.dust"), FLinearColor(0.32f, 0.30f, 0.27f));
	}
	S->AsObject()->TryGetBoolField(TEXT("sparks"), bSparks);
	return MIEffectsPrivate::Color(Fx, Key + TEXT(".dust"), FLinearColor(0.32f, 0.30f, 0.27f));
}

void UMIEffects::OnImpact(const FMIImpactEvent& E)
{
	using namespace MIEffectsPrivate;
	const FVector N = E.Normal.GetSafeNormal();
	const FVector D = E.Direction.GetSafeNormal();
	if (IsEnemy(E.Actor.Get()))
	{
		// Blood: a short dark mist out of the wound both ways, and a spatter on the wall behind within reach.
		const FLinearColor Blood = Color(Fx, TEXT("blood.color"), FLinearColor(0.16f, 0.012f, 0.01f));
		for (int32 I = 0; I < 3; ++I)
		{
			const FVector V = (I == 0 ? -D * 90.0 : D * FMath::FRandRange(140.0, 260.0)) + FMath::VRand() * 60.0;
			Puff(E.Point + D * 4.0, V, FMath::FRandRange(0.3, 0.5), 5.0, FMath::FRandRange(26.0, 40.0), 0.75, Blood, 0.0, 4.0, -40.0);
		}
		FHitResult Hit;
		FCollisionQueryParams Q(SCENE_QUERY_STAT(MIFxBlood), false, E.Actor.Get());
		if (UWorld* World = GetWorld(); World && World->LineTraceSingleByChannel(Hit, E.Point, E.Point + D * MIJson::NumberOr(Fx, TEXT("blood.reach"), 260.0), ECC_Visibility, Q) && !IsEnemy(Hit.GetActor()))
		{
			Mark(Hit.ImpactPoint, Hit.ImpactNormal, FMath::FRandRange(28.0, 46.0), 1.0, Blood, 40.0);
		}
		return;
	}
	bool bSparks = false;
	const FLinearColor Dust = SurfaceColor(E.Surface, bSparks);
	const FVector Bounce = (D - 2.0 * FVector::DotProduct(D, N) * N).GetSafeNormal();
	Puff(E.Point + N * 3.0, N * 140.0 + Bounce * 60.0, FMath::FRandRange(0.9, 1.4), 4.0, FMath::FRandRange(34.0, 48.0), 0.5, Dust, 0.0, 3.0, 15.0);
	Puff(E.Point + N * 2.0, Bounce * 220.0 + FMath::VRand() * 40.0, FMath::FRandRange(0.5, 0.8), 3.0, 22.0, 0.42, Dust * 0.85f, 0.0, 5.0, 0.0);
	Mark(E.Point, N, FMath::FRandRange(7.0, 10.0), 0.0, Dust, MIJson::NumberOr(Fx, TEXT("markLife"), 30.0));
	if (bSparks && Cards.Num() > 0)
	{
		FCard& X = Cards[NextCard];
		NextCard = (NextCard + 1) % Cards.Num();
		X.Age = 0.0;
		X.Life = 0.03;
		X.Mesh->SetWorldLocationAndRotation(E.Point + N * 1.5, FRotationMatrix::MakeFromZ(N).Rotator());
		X.Mesh->SetWorldScale3D(FVector(0.07));
		X.Mat->SetScalarParameterValue(TEXT("Mode"), 0.f);
		X.Mat->SetScalarParameterValue(TEXT("Seed"), FMath::FRandRange(0.f, 50.f));
		X.Mesh->SetVisibility(true);
	}
}

void UMIEffects::OnExplosion(const FMIExplosionEvent& E)
{
	using namespace MIEffectsPrivate;
	if (!bReady)
	{
		return;
	}
	const double S = E.bBig ? 1.0 : 0.6;
	const FVector P = E.Position;
	Light(P + FVector(0, 0, 120), MIJson::NumberOr(Fx, TEXT("explosion.candela"), 40000.0) * S, 3500.0 * S, 0.45,
		Color(Fx, TEXT("explosion.light"), FLinearColor(1.0f, 0.55f, 0.25f)));
	const FLinearColor Smoke = Color(Fx, TEXT("explosion.smoke"), FLinearColor(0.06f, 0.055f, 0.05f));
	const FLinearColor Dust = Color(Fx, TEXT("explosion.dust"), FLinearColor(0.30f, 0.27f, 0.23f));
	for (int32 I = 0; I < 7; ++I)
	{
		const FVector V = (FMath::VRand() + FVector(0, 0, 0.7)).GetSafeNormal() * FMath::FRandRange(250.0, 600.0) * S;
		Puff(P + FVector(0, 0, 60), V, FMath::FRandRange(0.35, 0.6), 60.0 * S, FMath::FRandRange(180.0, 260.0) * S, 0.95, FLinearColor(0.05f, 0.03f, 0.02f), 60.0, 4.0, 80.0);
	}
	for (int32 I = 0; I < 12; ++I)
	{
		const FVector V = (FMath::VRand() * FVector(1, 1, 0.3) + FVector(0, 0, 0.8)) * FMath::FRandRange(80.0, 260.0) * S;
		Puff(P + FVector(0, 0, 80) + FMath::VRand() * 60.0 * S, V, FMath::FRandRange(4.5, 8.0), 120.0 * S, FMath::FRandRange(420.0, 620.0) * S, 0.55, Smoke, 0.0, 0.9, 90.0);
	}
	for (int32 I = 0; I < 8; ++I)
	{
		const double A = I * UE_DOUBLE_PI / 4.0 + FMath::FRandRange(-0.3, 0.3);
		const FVector Out(FMath::Cos(A), FMath::Sin(A), 0.05);
		Puff(P + Out * 80.0 + FVector(0, 0, 20), Out * 650.0 * S, FMath::FRandRange(1.6, 2.6), 70.0 * S, 300.0 * S, 0.45, Dust, 0.0, 2.6, 20.0);
	}
	if (Cube && DebrisMat)
	{
		for (int32 I = 0; I < 10; ++I)
		{
			const FVector V = (FMath::VRand() * FVector(1, 1, 0.4) + FVector(0, 0, 1.0)).GetSafeNormal() * FMath::FRandRange(600.0, 1400.0) * S;
			const double Sz = FMath::FRandRange(0.03, 0.09);
			SpawnBody(this, Cube, FTransform(FRotator(FMath::FRandRange(0.0, 360.0), FMath::FRandRange(0.0, 360.0), 0.0).Quaternion(), P + FVector(0, 0, 60) + FMath::VRand() * 30.0,
				FVector(Sz, Sz * FMath::FRandRange(0.5, 1.5), Sz * FMath::FRandRange(0.3, 0.8))), V, FMath::VRand() * 720.0, 7.0, DebrisMat);
		}
	}
	FHitResult Hit;
	if (UWorld* World = GetWorld(); World && World->LineTraceSingleByChannel(Hit, P + FVector(0, 0, 50), P - FVector(0, 0, 300), ECC_Visibility))
	{
		Mark(Hit.ImpactPoint, Hit.ImpactNormal, FMath::Max(150.0, E.Radius * 0.35) * S, 2.0, FLinearColor::Black, 90.0);
	}
}

// --- the frame -----------------------------------------------------------------------------------------------

void UMIEffects::Tick(float DeltaTime)
{
	UWorld* World = GetWorld();
	if (!World || World->IsPaused())
	{
		return;
	}
	const double Dt = DeltaTime;
	FVector Cam = FVector::ZeroVector;
	if (const APlayerController* PC = World->GetFirstPlayerController(); PC && PC->PlayerCameraManager)
	{
		Cam = PC->PlayerCameraManager->GetCameraLocation();
	}
	for (FPuff& X : Puffs)
	{
		if (X.Age >= X.Life)
		{
			continue;
		}
		X.Age += Dt;
		if (X.Age >= X.Life)
		{
			X.Mesh->SetVisibility(false);
			continue;
		}
		const double K = X.Age / X.Life;
		X.Vel *= FMath::Exp(-X.Drag * Dt);
		X.Vel.Z += X.Rise * Dt;
		X.Pos += X.Vel * Dt;
		X.Roll += X.Spin * Dt;
		const double Size = FMath::Lerp(X.Size0, X.Size1, 1.0 - FMath::Pow(1.0 - K, 2.2));
		X.Mesh->SetWorldLocationAndRotation(X.Pos, FQuat(FRotationMatrix::MakeFromZ(Cam - X.Pos).ToQuat()) * FQuat(FVector::UpVector, FMath::DegreesToRadians(X.Roll)));
		X.Mesh->SetWorldScale3D(FVector(Size / 100.0, Size / 100.0, 1.0));
		const double Fade = FMath::Min(1.0, X.Age / 0.06) * FMath::Pow(1.0 - K, 1.4);
		X.Mat->SetScalarParameterValue(TEXT("Opacity"), static_cast<float>(X.Opacity * Fade));
		X.Mat->SetScalarParameterValue(TEXT("Erode"), static_cast<float>(K * 0.8));
		if (X.Fire > 0.0)
		{
			X.Mat->SetScalarParameterValue(TEXT("Fire"), static_cast<float>(X.Fire * FMath::Pow(FMath::Max(0.0, 1.0 - K * 1.8), 2.0)));
		}
	}
	for (FCard& X : Cards)
	{
		if (X.Age < X.Life && (X.Age += Dt) >= X.Life)
		{
			X.Mesh->SetVisibility(false);
		}
	}
	for (FLight& X : Lights)
	{
		if (X.Age >= X.Life)
		{
			continue;
		}
		X.Age += Dt;
		const double K = FMath::Clamp(X.Age / X.Life, 0.0, 1.0);
		X.Light->SetIntensity(static_cast<float>(X.Peak * FMath::Square(1.0 - K)));
		if (X.Age >= X.Life) X.Light->SetVisibility(false);
	}
	for (FMark& X : Marks)
	{
		if (X.Age >= X.Life)
		{
			continue;
		}
		X.Age += Dt;
		const double Left = X.Life - X.Age;
		if (Left < 3.0) X.Mat->SetScalarParameterValue(TEXT("Fade"), static_cast<float>(FMath::Max(0.0, Left / 3.0)));
		if (X.Age >= X.Life) X.Decal->SetVisibility(false);
	}
	for (FStreak& X : Streaks)
	{
		if (X.Age >= X.Life)
		{
			continue;
		}
		X.Age += Dt;
		if (X.Age >= X.Life)
		{
			X.Mesh->SetVisibility(false);
			continue;
		}
		const FVector Dir = (X.To - X.From).GetSafeNormal();
		const double Dist = FVector::Dist(X.From, X.To);
		const double Head = FMath::Min(Dist, Dist * X.Age / X.Life);
		const double Tail = FMath::Max(0.0, Head - X.Length);
		X.Mesh->SetWorldLocation(X.From + Dir * (Head + Tail) * 0.5);
		X.Mesh->SetWorldScale3D(FVector(X.Mesh->GetComponentScale().X, X.Mesh->GetComponentScale().Y, FMath::Max(1.0, Head - Tail) / 100.0));
		X.Mesh->SetVisibility(true);
	}
}
