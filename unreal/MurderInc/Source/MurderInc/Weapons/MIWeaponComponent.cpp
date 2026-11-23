#include "Weapons/MIWeaponComponent.h"

#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/LineBatchComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Core/MIDamageable.h"
#include "Core/MIEvents.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "MurderInc.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "Player/MIPlayerCharacter.h"
#include "Weapons/MICombatSubsystem.h"

namespace MIWeaponComponentPrivate
{
	FName SurfaceOf(const FHitResult& Hit)
	{
		if (const IMIDamageable* D = Cast<IMIDamageable>(Hit.GetActor()))
		{
			return D->GetMISurface();
		}
		if (const UPhysicalMaterial* Material = Hit.PhysMaterial.Get())
		{
			FString Name = Material->GetName();
			Name.RemoveFromStart(TEXT("PM_"));
			return FName(*Name.ToLower());
		}
		return TEXT("concrete");
	}

	bool IsHead(const FHitResult& Hit)
	{
		const UPrimitiveComponent* C = Hit.GetComponent();
		return (C && C->ComponentHasTag(TEXT("head"))) || Hit.BoneName.ToString().Contains(TEXT("head"));
	}
}

UMIWeaponComponent::UMIWeaponComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

void UMIWeaponComponent::Setup(AMIPlayerCharacter* InPlayer, const FMIConfigData& Config, UCameraComponent* InCamera, UPoseableMeshComponent* InGun, USkeletalMeshComponent* InArms)
{
	Player = InPlayer;
	Camera = InCamera;
	GunMesh = InGun;
	Arms = InArms;
	Events = UMIEventSubsystem::Get(this);
	Rules.Init(Config.Weapons, static_cast<uint32>(Config.Seed), Events);
	TracerColor = Config.Weapons.Common.TracerColor;
	TracerSpeed = Config.Weapons.Common.TracerSpeed;
	ViewmodelFov = Config.Player.Fov.Viewmodel;

	FString Error;
	bHaveView = FMIViewmodelData::Load(ViewData, Error);
	if (!bHaveView)
	{
		UE_LOG(LogMI, Error, TEXT("Weapons: %s (the guns are not drawn)"), *Error);
	}
	Rig.Init(bHaveView ? &ViewData : nullptr);
	BindEvents();
	bReady = true;
	ResetRun();
}

void UMIWeaponComponent::ResetRun()
{
	Rules.Reset();
	Rig.Reset();
	Tracers.Reset();
	SinceHit = 1e30;
	MeshFor = NAME_None;
}

void UMIWeaponComponent::BindEvents()
{
	if (!Events || Handles.Num() > 0)
	{
		return;
	}
	Handles.Add(Events->WeaponFire.AddLambda([this](const FMIShotFiredEvent& E)
	{
		const FMIWeaponPlayerState P = GetPlayerState();
		Rig.OnFire(E.Burst, P.bCrouching, E.Ads, E.MagLeft == 0);
	}));
	Handles.Add(Events->WeaponDry.AddLambda([this](FName) { Rig.OnDry(); }));
	Handles.Add(Events->WeaponReload.AddLambda([this](const FMIReloadEvent& E) { Rig.OnReloadPhase(E.Phase, E.bEmpty); }));
	Handles.Add(Events->PlayerJump.AddLambda([this]() { Rig.OnJump(); }));
	Handles.Add(Events->PlayerLand.AddLambda([this](const FMIPlayerLandEvent& E) { Rig.OnLand(E.Speed); }));
}

void UMIWeaponComponent::EndPlay(const EEndPlayReason::Type Reason)
{
	if (Events)
	{
		// The bus belongs to the world and lives as long as this component's world does.
		Events->WeaponFire.Remove(Handles.IsValidIndex(0) ? Handles[0] : FDelegateHandle());
		Events->WeaponDry.Remove(Handles.IsValidIndex(1) ? Handles[1] : FDelegateHandle());
		Events->WeaponReload.Remove(Handles.IsValidIndex(2) ? Handles[2] : FDelegateHandle());
		Events->PlayerJump.Remove(Handles.IsValidIndex(3) ? Handles[3] : FDelegateHandle());
		Events->PlayerLand.Remove(Handles.IsValidIndex(4) ? Handles[4] : FDelegateHandle());
	}
	Handles.Reset();
	Super::EndPlay(Reason);
}

void UMIWeaponComponent::Step(double Dt, const FMIWeaponInput& Input, const FVector2D& LookDelta)
{
	if (!bReady || !(Dt > 0.0))
	{
		return;
	}
	SinceHit += Dt;
	Rules.Update(Dt, Input, *this);

	const FMIWeaponView View = Rules.GetView();
	const FMIPlayerRules& P = Player->GetPlayerRules();
	FMIViewmodelPlayer VP;
	VP.Speed = P.Speed;
	VP.Velocity = P.Velocity;
	VP.Yaw = P.Yaw;
	VP.bOnGround = P.bOnGround;
	VP.bCrouching = P.bCrouching;
	VP.bSprinting = P.bSprinting;
	VP.LookDelta = LookDelta;
	Rig.Update(Dt, View, Rules.GetAdsLinear(), Rules.IsDropped(), VP);

	if (View.Weapon != MeshFor)
	{
		EquipMesh(View.Weapon);
	}
	PoseView();
	DrawTracers(Dt);
}

// --- the meshes --------------------------------------------------------------------------------------------

void UMIWeaponComponent::EquipMesh(FName Gun)
{
	MeshFor = Gun;
	const FMIGunViewData* D = ViewData.Find(Gun);
	if (!bHaveView || !D || !GunMesh)
	{
		return;
	}
	USkeletalMesh* Mesh = Cast<USkeletalMesh>(D->Mesh.TryLoad());
	if (!Mesh)
	{
		UE_LOG(LogMI, Warning, TEXT("Weapons: no mesh at %s for %s (tools/box/seed-content.sh installs the placeholders)"), *D->Mesh.ToString(), *Gun.ToString());
	}
	GunMesh->SetSkinnedAssetAndUpdate(Mesh, true);
	GunMesh->SetVisibility(Mesh != nullptr);

	// Real art brings its own markers as sockets; the data keeps the web values for meshes without them.
	for (const TPair<FName, FName>& Socket : D->Sockets)
	{
		if (Mesh && GunMesh->DoesSocketExist(Socket.Value))
		{
			const FVector MeshSpace = GunMesh->GetSocketTransform(Socket.Value, RTS_Component).GetLocation();
			Rig.OverrideMarker(Socket.Key, FMIViewmodelRig::UEToWeb(D->MeshOffset.TransformPosition(MeshSpace)));
		}
	}
	const auto Find = [this](const FMIGunPartData& Part, FPartBone& Out)
	{
		Out = FPartBone();
		if (!Part.Bone.IsNone() && GunMesh->GetSkinnedAsset())
		{
			Out.Index = GunMesh->GetBoneIndex(Part.Bone);
			if (Out.Index != INDEX_NONE)
			{
				Out.Ref = GunMesh->GetBoneTransformByName(Part.Bone, EBoneSpaces::ComponentSpace);
			}
		}
	};
	Find(D->Bolt, Bolt);
	Find(D->Barrel, Barrel);
	Find(D->Trigger, Trigger);
	Find(D->Magazine, Magazine);

	if (Arms)
	{
		if (UAnimSequence* Idle = Cast<UAnimSequence>(D->Idle.TryLoad()))
		{
			Arms->SetAnimationMode(EAnimationMode::AnimationSingleNode);
			Arms->PlayAnimation(Idle, true);
		}
	}
}

void UMIWeaponComponent::PoseView()
{
	const FMIGunViewData* D = Rig.GetGunData();
	if (!bHaveView || !D || !GunMesh)
	{
		return;
	}
	// The gun: mesh space -> gun space -> camera space.
	const FTransform Gun = D->MeshOffset * Rig.GetGunTransform();
	GunMesh->SetRelativeTransform(Gun);
	PoseParts();

	// The arms hold the grip: the body is placed so that its hand socket sits on the gun's grip marker.
	if (Arms && Arms->GetSkinnedAsset() && !ViewData.BodyHandSocket.IsNone() && Arms->DoesSocketExist(ViewData.BodyHandSocket))
	{
		const FTransform Grip(Gun.GetRotation(), Rig.GunPointInCamera(D->Marker(TEXT("grip"))));
		const FTransform Hand = Arms->GetSocketTransform(ViewData.BodyHandSocket, RTS_Component);
		Arms->SetRelativeTransform(Hand.Inverse() * Grip);
	}
}

void UMIWeaponComponent::PoseParts()
{
	const FMIGunViewData* D = Rig.GetGunData();
	const FMIGunParts& Parts = Rig.GetParts();
	const FTransform& Offset = D->MeshOffset;
	// Gun-space directions (web) in the mesh's own space.
	const auto MeshDir = [&Offset](const FVector& Web) { return Offset.InverseTransformVectorNoScale(FMIViewmodelRig::WebToUE(Web) / 100.0); };
	const FVector Right = MeshDir(FVector(1, 0, 0)).GetSafeNormal();

	if (Bolt.Index != INDEX_NONE)
	{
		FTransform T = Bolt.Ref;
		T.AddToTranslation(MeshDir(D->Bolt.Axis) * (D->Bolt.Travel * 100.0 * Parts.Bolt));
		GunMesh->SetBoneTransformByName(D->Bolt.Bone, T, EBoneSpaces::ComponentSpace);
	}
	if (Barrel.Index != INDEX_NONE)
	{
		FTransform T = Barrel.Ref;
		T.SetRotation(FQuat(Right, D->Barrel.Travel * Parts.Barrel) * Barrel.Ref.GetRotation());
		GunMesh->SetBoneTransformByName(D->Barrel.Bone, T, EBoneSpaces::ComponentSpace);
	}
	if (Trigger.Index != INDEX_NONE)
	{
		FTransform T = Trigger.Ref;
		T.SetRotation(FQuat(Right, -D->Trigger.Travel * Parts.Trigger) * Trigger.Ref.GetRotation());
		GunMesh->SetBoneTransformByName(D->Trigger.Bone, T, EBoneSpaces::ComponentSpace);
	}
	if (Magazine.Index != INDEX_NONE)
	{
		FTransform T = Magazine.Ref;
		T.AddToTranslation(MeshDir(D->Magazine.Drop) * (100.0 * Parts.Magazine));
		T.SetScale3D(Parts.bMagazineVisible ? Magazine.Ref.GetScale3D() : FVector(1e-3));
		GunMesh->SetBoneTransformByName(D->Magazine.Bone, T, EBoneSpaces::ComponentSpace);
	}
}

FVector UMIWeaponComponent::FirstPersonToWorld(const FVector& CameraSpace) const
{
	if (!Camera)
	{
		return CameraSpace;
	}
	// Horizontal and vertical both scale by the ratio of the tangents (the vertical one is kept on aspect changes).
	const double World = FMath::Tan(FMath::DegreesToRadians(Player->GetPlayerRules().ViewFov) * 0.5);
	const double First = FMath::Tan(FMath::DegreesToRadians(ViewmodelFov) * 0.5);
	const double K = First > 0.0 ? World / First : 1.0;
	const FVector Local(CameraSpace.X, CameraSpace.Y * K, CameraSpace.Z * K);
	return Camera->GetComponentLocation() + Camera->GetComponentQuat().RotateVector(Local);
}

// --- what the rules ask --------------------------------------------------------------------------------------

FMIWeaponPlayerState UMIWeaponComponent::GetPlayerState() const
{
	FMIWeaponPlayerState S;
	if (!Player)
	{
		return S;
	}
	const FMIPlayerRules& P = Player->GetPlayerRules();
	S.bAlive = P.bAlive;
	S.bSprinting = P.bSprinting;
	S.bCrouching = P.bCrouching;
	S.bOnGround = P.bOnGround;
	S.Speed = P.Speed;
	S.Eye = P.Eye;
	S.Forward = P.Forward;
	S.Velocity = P.Velocity;
	return S;
}

void UMIWeaponComponent::SetPlayerAds(double Ads)
{
	Player->GetPlayerRules().Ads = Ads;
}

void UMIWeaponComponent::SetPlayerAimView(double AdsFov, double AdsLook)
{
	Player->GetPlayerRules().AimFov = AdsFov;
	Player->GetPlayerRules().AimLook = AdsLook;
}

void UMIWeaponComponent::AddRecoil(double PitchDeg, double YawDeg)
{
	Player->GetPlayerRules().AddRecoil(PitchDeg, YawDeg);
}

void UMIWeaponComponent::AddShake(double Trauma)
{
	Player->GetPlayerRules().AddShake(Trauma);
}

void UMIWeaponComponent::NoteHit(bool bKilled, bool bHead)
{
	SinceHit = 0.0;
	bLastHitKill = bKilled;
	bLastHitHead = bHead;
}

FMIShotResult UMIWeaponComponent::Hitscan(const FMIShotRequest& Shot)
{
	using namespace MIWeaponComponentPrivate;
	FMIShotResult Result;
	UWorld* World = GetWorld();
	const FVector End = Shot.Origin + Shot.Direction * Shot.Range;
	Result.Point = End;
	Result.Distance = Shot.Range;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(MIHitscan), false, GetOwner());
	Params.bReturnPhysicalMaterial = true;
	FHitResult Hit;
	if (!World || !World->LineTraceSingleByChannel(Hit, Shot.Origin, End, MIBulletChannel, Params))
	{
		return Result;
	}
	Result.bHit = true;
	Result.Distance = Hit.Distance;
	Result.Point = Hit.ImpactPoint;

	IMIDamageable* Target = Cast<IMIDamageable>(Hit.GetActor());
	if (Target && Target->IsMIDamageableAlive())
	{
		const bool bEnemy = Target->GetMIDamageableKind() == TEXT("enemy");
		const bool bHead = bEnemy && IsHead(Hit);
		FMIDamage Damage;
		// Falloff first (skipped up to its start), then the head multiplier (LOADOUT.md 4.5).
		Damage.Amount = Shot.DamageAt(Hit.Distance) * (bHead ? Shot.HeadMultiplier : 1.0);
		Damage.Kind = EMIDamageKind::Bullet;
		Damage.Source = EMIDamageSource::Player;
		Damage.From = Shot.Origin;
		Damage.Point = Hit.ImpactPoint;
		Damage.Direction = Shot.Direction;
		Damage.Part = bHead ? FName(TEXT("head")) : FName(TEXT("body"));
		Damage.Weapon = Shot.Weapon;
		Damage.Instigator = GetOwner();
		const FMIDamageResult Dealt = Target->ApplyMIDamage(Damage);
		if (bEnemy && Dealt.bAccepted)
		{
			NoteHit(Dealt.bKilled, bHead);
			if (Events)
			{
				Events->PlayerHitEnemy.Broadcast({Hit.GetActor(), Damage.Part, Dealt.bKilled, Damage.Amount, Shot.Weapon});
			}
		}
	}
	if (Events)
	{
		FMIImpactEvent Impact;
		Impact.Point = Hit.ImpactPoint;
		Impact.Normal = Hit.ImpactNormal;
		Impact.Surface = SurfaceOf(Hit);
		Impact.Direction = Shot.Direction;
		Impact.From = EMIDamageSource::Player;
		Impact.Actor = Hit.GetActor();
		Events->Impact.Broadcast(Impact);
	}
	return Result;
}

EMIStrikeResult UMIWeaponComponent::Melee(const FMIStrikeRequest& Strike)
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return EMIStrikeResult::None;
	}
	// The nearest living enemy within reach, inside the cone, in sight.
	TArray<FOverlapResult> Overlaps;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(MIMelee), false, GetOwner());
	World->OverlapMultiByChannel(Overlaps, Strike.Origin, FQuat::Identity, MIBulletChannel, FCollisionShape::MakeSphere(Strike.Reach), Params);
	const double CosHalf = FMath::Cos(FMath::DegreesToRadians(Strike.ConeDegrees * 0.5));
	IMIDamageable* Best = nullptr;
	AActor* BestActor = nullptr;
	FVector BestPoint = FVector::ZeroVector;
	double BestDistance = TNumericLimits<double>::Max();
	const UMICombatSubsystem* Combat = UMICombatSubsystem::Get(this);
	for (const FOverlapResult& O : Overlaps)
	{
		AActor* Actor = O.GetActor();
		IMIDamageable* Target = Cast<IMIDamageable>(Actor);
		if (!Target || !Target->IsMIDamageableAlive() || Target->GetMIDamageableKind() != TEXT("enemy") || Actor == BestActor)
		{
			continue;
		}
		const FVector Point = O.GetComponent() ? O.GetComponent()->Bounds.Origin : Actor->GetActorLocation();
		const FVector To = Point - Strike.Origin;
		const double Distance = To.Size();
		if (Distance > Strike.Reach || Distance <= KINDA_SMALL_NUMBER || FVector::DotProduct(To / Distance, Strike.Direction) < CosHalf)
		{
			continue;
		}
		if (Combat && !Combat->LineOfSight(Strike.Origin, Point, GetOwner(), Actor))
		{
			continue;
		}
		if (Distance < BestDistance)
		{
			Best = Target;
			BestActor = Actor;
			BestPoint = Point;
			BestDistance = Distance;
		}
	}
	if (Best)
	{
		FMIDamage Damage;
		Damage.Amount = Strike.Damage;
		Damage.Kind = EMIDamageKind::Melee;
		Damage.Source = EMIDamageSource::Player;
		Damage.From = Strike.Origin;
		Damage.Point = BestPoint;
		Damage.Direction = Strike.Direction;
		Damage.Weapon = TEXT("melee");
		Damage.Instigator = GetOwner();
		const FMIDamageResult Dealt = Best->ApplyMIDamage(Damage);
		NoteHit(Dealt.bKilled, false);
		if (Events)
		{
			Events->PlayerHitEnemy.Broadcast({BestActor, TEXT("body"), Dealt.bKilled, Strike.Damage, TEXT("melee")});
		}
		Rig.OnMeleeLand(true, true);
		return EMIStrikeResult::Enemy;
	}
	const bool bWall = ProbeWall(Strike.Origin, Strike.Direction, Strike.Reach) >= 0.0;
	Rig.OnMeleeLand(false, bWall);
	return bWall ? EMIStrikeResult::World : EMIStrikeResult::None;
}

double UMIWeaponComponent::ProbeWall(const FVector& Origin, const FVector& Direction, double MaxDistance)
{
	UWorld* World = GetWorld();
	if (!World)
	{
		return -1.0;
	}
	FCollisionQueryParams Params(SCENE_QUERY_STAT(MIWallProbe), false, GetOwner());
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	FHitResult Hit;
	return World->LineTraceSingleByObjectType(Hit, Origin, Origin + Direction * MaxDistance, Objects, Params) ? Hit.Distance : -1.0;
}

bool UMIWeaponComponent::AimTarget(const FVector& Origin, const FVector& Direction, double Range)
{
	UWorld* World = GetWorld();
	FCollisionQueryParams Params(SCENE_QUERY_STAT(MIAimTarget), false, GetOwner());
	FHitResult Hit;
	if (!World || !World->LineTraceSingleByChannel(Hit, Origin, Origin + Direction * Range, MIBulletChannel, Params))
	{
		return false;
	}
	const IMIDamageable* Target = Cast<IMIDamageable>(Hit.GetActor());
	return Target && Target->IsMIDamageableAlive() && Target->GetMIDamageableKind() == TEXT("enemy");
}

void UMIWeaponComponent::OnRoundFired(const FMIShotRequest& Shot, const FMIShotResult& Result, double FlashScale)
{
	if (!bHaveView || Result.Distance < ViewData.TracerMinHit * 100.0)
	{
		return;
	}
	const FMIGunViewData* D = Rig.GetGunData();
	const FVector Muzzle = D ? FirstPersonToWorld(Rig.GunPointInCamera(D->Marker(TEXT("muzzle")))) : Shot.Origin;
	Tracers.Add({Muzzle, Result.Point, 0.0});
}

void UMIWeaponComponent::DrawTracers(double Dt)
{
	UWorld* World = GetWorld();
	ULineBatchComponent* Lines = World ? World->GetLineBatcher(UWorld::ELineBatcherType::World) : nullptr;
	const double Length = ViewData.TracerLength * 100.0;
	const double Hidden = ViewData.TracerHidden * 100.0;
	const double HiddenFrom = ViewData.TracerHiddenFrom * 100.0;
	for (int32 I = Tracers.Num() - 1; I >= 0; --I)
	{
		FTracer& T = Tracers[I];
		T.Age += Dt;
		const FVector Path = T.End - T.Start;
		const double Total = Path.Size();
		const double Head = TracerSpeed * T.Age;
		if (Total <= KINDA_SMALL_NUMBER || Head - Length >= Total)
		{
			Tracers.RemoveAtSwap(I);
			continue;
		}
		const double From = FMath::Max(Head - Length, Total > HiddenFrom ? Hidden : 0.0);
		const double To = FMath::Min(Head, Total);
		if (Lines && To > From)
		{
			const FVector Dir = Path / Total;
			Lines->DrawLine(T.Start + Dir * From, T.Start + Dir * To, FLinearColor(TracerColor), SDPG_World, ViewData.TracerThickness * 100.0, 0.f);
		}
	}
}
