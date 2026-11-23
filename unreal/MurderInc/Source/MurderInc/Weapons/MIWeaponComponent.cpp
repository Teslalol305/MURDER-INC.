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
#include "Weapons/MIEffects.h"
#include "Weapons/MIFirstPersonRig.h"
#include "Weapons/MIGunAssembly.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Dom/JsonObject.h"

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
	Seed = static_cast<uint32>(Config.Seed);
	Rules.Init(Config.Weapons, Seed, Events);
	if (!Assembly && GetOwner())
	{
		Assembly = NewObject<UMIGunAssembly>(GetOwner(), TEXT("GunAssembly"), RF_Transient);
		Assembly->RegisterComponent();
	}
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
	if (!FPRig && GetOwner())
	{
		FPRig = NewObject<UMIFirstPersonRig>(GetOwner(), TEXT("FirstPersonRig"), RF_Transient);
		FPRig->RegisterComponent();
	}
	TSharedPtr<FJsonObject> ConfigRoot, PresentationRoot;
	FString RootError;
	if (FPRig && FMILoadoutResolver::LoadRoots(ConfigRoot, PresentationRoot, RootError))
	{
		FPRig->Init(this, Arms, Camera, PresentationRoot);
		// The recipe's near plane (ANIMATION.md 9): the receiver is 8.9 cm from the eye when aimed.
		const double Near = MIJson::NumberOr(PresentationRoot, TEXT("firstPerson.recipe.nearClip"), 0.0);
		if (Near > 0.0 && GetWorld() && GetWorld()->IsGameWorld())
		{
			GNearClippingPlane = static_cast<float>(Near);
		}
		// The player's muzzle flash: three first-person cards (the star across the bore, two crossed jets along it).
		UMaterialInterface* Flash = Cast<UMaterialInterface>(FSoftObjectPath(MIJson::StringOr(PresentationRoot, TEXT("fx.materials.flash"))).TryLoad());
		UStaticMesh* Plane = Cast<UStaticMesh>(FSoftObjectPath(TEXT("/Engine/BasicShapes/Plane.Plane")).TryLoad());
		FlashLife = MIJson::NumberOr(PresentationRoot, TEXT("fx.flash.life"), 0.045);
		for (int32 I = 0; Flash && Plane && Camera && FlashCards.Num() < 3 && I < 3; ++I)
		{
			UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(GetOwner(), NAME_None, RF_Transient);
			C->SetStaticMesh(Plane);
			C->SetMobility(EComponentMobility::Movable);
			C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			C->SetCastShadow(false);
			C->SetOnlyOwnerSee(true);
			// Not a first-person primitive (review 2026-11-23: the additive cards drawn in the first-person pass never
			// showed): a plain card on the camera at the depth and size the first-person pass draws the muzzle at.
			C->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::None);
			C->SetTranslucentSortPriority(10);
			UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(Flash, C);
			M->SetScalarParameterValue(TEXT("Intensity"), static_cast<float>(MIJson::NumberOr(PresentationRoot, TEXT("fx.flash.emissive"), 40000.0)));
			C->SetMaterial(0, M);
			C->SetupAttachment(Camera);
			C->RegisterComponent();
			C->SetVisibility(false);
			FlashCards.Add(C);
			FlashMids.Add(M);
		}
	}
	BindEvents();
	bReady = true;
	ResetRun();
}

void UMIWeaponComponent::ApplyRun(const FMIResolvedRun& Run)
{
	Resolved = Run.Guns;
	Rules.Init(Run.Weapons, Seed, Events);
	ViewData = Run.View;
	bHaveView = ViewData.Guns.Num() > 0;
	Rig.Init(bHaveView ? &ViewData : nullptr);
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
		if (FPRig) FPRig->OnFire(E.Ads);
	}));
	Handles.Add(Events->WeaponDry.AddLambda([this](FName) { Rig.OnDry(); }));
	Handles.Add(Events->WeaponReload.AddLambda([this](const FMIReloadEvent& E) { Rig.OnReloadPhase(E.Phase, E.bEmpty); }));
	Handles.Add(Events->PlayerJump.AddLambda([this]() { Rig.OnJump(); if (FPRig) FPRig->OnJump(); }));
	Handles.Add(Events->PlayerLand.AddLambda([this](const FMIPlayerLandEvent& E) { Rig.OnLand(E.Speed); if (FPRig) FPRig->OnLand(E.Speed); }));
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
	if (FPRig && FPRig->GetMode() != EMIFPMode::Template)
	{
		FPRig->Update(Dt, View, Rig, VP, P.Yaw);
	}
	PoseView();
	if (FPRig && FPRig->GetMode() == EMIFPMode::HandIK)
	{
		FPRig->UpdateHands(GunMesh);
	}
	// At most a 60 fps frame per step: the flash stays up for its life's worth of frames even when a frame is long
	// (the headless editor runs at 10 to 20 fps: one step hid it before it was ever drawn).
	FlashAge += FMath::Min(Dt, 1.0 / 60.0);
	if (FlashAge >= FlashLife)
	{
		if (FlashCards.Num() > 0 && FlashCards[0] && FlashCards[0]->IsVisible())
		{
			UE_LOG(LogMI, Verbose, TEXT("Flash: hidden at age %.4f s (frame %.4f s)"), FlashAge, Dt);
		}
		for (UStaticMeshComponent* C : FlashCards)
		{
			if (C && C->IsVisible()) C->SetVisibility(false);
		}
	}
	DrawTracers(Dt);
	DrawLaser();
	// The clear magazine shows the rounds left (LOADOUT.md 4.5): a scalar on the gun's materials.
	if (GunMesh && View.MagSize > 0)
	{
		GunMesh->SetScalarParameterValueOnMaterials(TEXT("RoundsShown"), static_cast<float>(View.Mag) / View.MagSize);
	}
}

void UMIWeaponComponent::DrawLaser()
{
	const FMIResolvedGun* G = ResolvedOf(Rules.GetCurrentId());
	FVector Start, Dir;
	UWorld* World = GetWorld();
	if (!G || !G->bLaser || !Assembly || !World || !Assembly->BeamWorld(Start, Dir) || Rules.IsDropped())
	{
		return;
	}
	// The dot sits where the eye ray meets the Bullet channel (rounds leave the eye), so it shows where hip fire
	// goes; the beam fades out while aimed (attachments.json laser.presentation.beam).
	const double Fade = 1.0 - FMath::Clamp((Rules.GetAds() - 0.45) / 0.15, 0.0, 1.0);
	if (Fade <= 0.0)
	{
		return;
	}
	const FMIPlayerRules& P = Player->GetPlayerRules();
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(MILaser), false, GetOwner());
	const FVector End = P.Eye + P.Forward * 6000.0;
	const FVector Dot = World->LineTraceSingleByChannel(Hit, P.Eye, End, MIBulletChannel, Params) ? Hit.ImpactPoint : End;
	if (ULineBatchComponent* Lines = World->GetLineBatcher(UWorld::ELineBatcherType::World))
	{
		const FLinearColor Red(1.f, 0.16f, 0.1f, static_cast<float>(0.55 * Fade));
		Lines->DrawLine(FirstPersonToWorld(Camera ? Camera->GetComponentTransform().InverseTransformPosition(Start) : Start), Dot, Red, SDPG_World, 0.25f, 0.f);
		Lines->DrawPoint(Dot, FLinearColor(1.f, 0.2f, 0.1f, static_cast<float>(Fade)), 5.f, SDPG_World, 0.f);
	}
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
	// The build: add-on parts at their mounts, and their sockets in place of the markers (the optic's sight, the
	// silencer's muzzle, a grip's support hand).
	if (Assembly)
	{
		if (const FMIResolvedGun* G = ResolvedOf(Gun))
		{
			Assembly->Assemble(GunMesh, *G, false);
			for (const TPair<FName, FVector>& M : Assembly->MarkerOverrides())
			{
				Rig.OverrideMarker(M.Key, FMIViewmodelRig::UEToWeb(D->MeshOffset.TransformPosition(M.Value)));
			}
		}
		else
		{
			Assembly->Clear();
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

	EMIFPMode Mode = EMIFPMode::Template;
	if (FPRig)
	{
		Mode = FPRig->Equip(Gun, D, ResolvedOf(Gun), Assembly, GunMesh);
	}
	if (FPRig)
	{
		FPRig->SetVisible(GunMesh->IsVisible(), Arms && Arms->IsVisible());
	}
	if (Mode == EMIFPMode::Pack)
	{
		// The pack rifle is drawn by the rig's own gun on the arms' gun bone; the poseable placeholder draws nothing.
		GunMesh->SetSkinnedAssetAndUpdate(nullptr, false);
		Rig.SetClipDriven(true, FPRig->GetBobScale());
	}
	else
	{
		Rig.SetClipDriven(false);
	}
	if (Arms && Mode == EMIFPMode::Template)
	{
		if (UAnimSequence* Idle = Cast<UAnimSequence>(D->Idle.TryLoad()))
		{
			Arms->SetAnimationMode(EAnimationMode::AnimationSingleNode);
			Arms->PlayAnimation(Idle, true);
		}
	}
}

double UMIWeaponComponent::GetFirstPersonFov(double HipVertical) const
{
	return FPRig ? FPRig->FirstPersonFovV(HipVertical, Rules.GetAds()) : HipVertical;
}

void UMIWeaponComponent::RequestInspect()
{
	const FMIWeaponView V = Rules.GetView();
	if (FPRig) FPRig->RequestInspect(V.Mag, V.MagSize);
}

void UMIWeaponComponent::SyncVisibility(bool bGun, bool bArms)
{
	if (FPRig) FPRig->SetVisible(bGun, bArms);
}

void UMIWeaponComponent::PoseView()
{
	const FMIGunViewData* D = Rig.GetGunData();
	if (!bHaveView || !D || !GunMesh || (FPRig && FPRig->GetMode() == EMIFPMode::Pack))
	{
		return;
	}
	// The gun: mesh space -> gun space -> camera space.
	const FTransform Gun = D->MeshOffset * Rig.GetGunTransform();
	GunMesh->SetRelativeTransform(Gun);
	PoseParts();

	// The arms hold the grip: the body is placed so that its hand socket sits on the gun's grip marker.
	FTransform Hand;
	if (Arms && Arms->GetSkinnedAsset() && !ViewData.BodyHandSocket.IsNone() && FPRig && FPRig->HandSocket(ViewData.BodyHandSocket, Hand))
	{
		const FTransform Grip(Gun.GetRotation(), Rig.GunPointInCamera(D->Marker(TEXT("grip"))));
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
	const double First = FMath::Tan(FMath::DegreesToRadians(GetFirstPersonFov(ViewmodelFov)) * 0.5);
	const double K = First > 0.0 ? World / First : 1.0;
	const FVector Local(CameraSpace.X, CameraSpace.Y * K, CameraSpace.Z * K);
	return Camera->GetComponentLocation() + Camera->GetComponentQuat().RotateVector(Local);
}

FTransform UMIWeaponComponent::FirstPersonToNearWorld(const FTransform& CameraSpace) const
{
	if (!Camera)
	{
		return CameraSpace;
	}
	const double World = FMath::Tan(FMath::DegreesToRadians(Player->GetPlayerRules().ViewFov) * 0.5);
	const double First = FMath::Tan(FMath::DegreesToRadians(GetFirstPersonFov(ViewmodelFov)) * 0.5);
	const double K = First > 0.0 ? World / First : 1.0;
	const double S = ViewData.FirstPersonScale > 0.0 ? ViewData.FirstPersonScale : 1.0;
	const FVector L = CameraSpace.GetLocation();
	const FQuat Cam = Camera->GetComponentQuat();
	return FTransform(Cam * CameraSpace.GetRotation(), Camera->GetComponentLocation() + Cam.RotateVector(FVector(S * L.X, S * K * L.Y, S * K * L.Z)),
		CameraSpace.GetScale3D() * (S * K));
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

bool UMIWeaponComponent::MuzzleCamera(FVector& Pos, FVector& Dir) const
{
	if (FPRig && FPRig->MuzzleInCamera(Pos, Dir))
	{
		return true;
	}
	const FMIGunViewData* D = Rig.GetGunData();
	if (!D)
	{
		return false;
	}
	Pos = Rig.GunPointInCamera(D->Marker(TEXT("muzzle")));
	Dir = (Pos - Rig.GunPointInCamera(D->Marker(TEXT("sightRear")))).GetSafeNormal();
	if (Dir.IsNearlyZero()) Dir = FVector::ForwardVector;
	return true;
}

void UMIWeaponComponent::MuzzleFlash(double FlashScale)
{
	FVector Pos, Dir;
	if (!Camera || !MuzzleCamera(Pos, Dir))
	{
		return;
	}
	const FMIResolvedGun* G = ResolvedOf(Rules.GetCurrentId());
	if (G && G->Def.bSuppressed)
	{
		return;  // a silencer: no flash, no light
	}
	if (FlashCards.Num() == 3 && FlashScale > 0.01)
	{
		FlashAge = 0.0;
		const double S = FMath::Clamp(FlashScale, 0.3, 1.5);
		for (int32 K = 0; K < 3; ++K)
		{
			const double Len = (K == 0 ? 9.0 : 15.0) * S * FMath::FRandRange(0.85, 1.15);
			FRotator R;
			FVector At = Pos;
			if (K == 0)
			{
				R = FRotationMatrix::MakeFromZ(Dir).Rotator();
			}
			else
			{
				const FVector Side = FVector::CrossProduct(Dir, K == 1 ? FVector::UpVector : FVector::RightVector).GetSafeNormal();
				R = FRotationMatrix::MakeFromXZ(Dir, Side).Rotator();
				At += Dir * Len * 0.5;
			}
			const FTransform Near = FirstPersonToNearWorld(FTransform(R, At, FVector(Len / 100.0, (K == 0 ? Len : Len * 0.42) / 100.0, 1.0)));
			FlashCards[K]->SetWorldTransform(Near);
			FlashMids[K]->SetScalarParameterValue(TEXT("Mode"), K == 0 ? 0.f : 1.f);
			FlashMids[K]->SetScalarParameterValue(TEXT("Seed"), FMath::FRandRange(0.f, 50.f));
			FlashCards[K]->SetVisibility(true);
		}
		UE_LOG(LogMI, Verbose, TEXT("Flash: shown, %.1f cm from the eye"), FVector::Dist(FlashCards[0]->GetComponentLocation(), Camera->GetComponentLocation()));
	}
	if (UMIEffects* Fx = UMIEffects::Get(this))
	{
		Fx->FlashLight(FirstPersonToWorld(Pos + Dir * 8.0), FlashScale);
	}
}

void UMIWeaponComponent::OnRoundFired(const FMIShotRequest& Shot, const FMIShotResult& Result, double FlashScale)
{
	if (!bHaveView)
	{
		return;
	}
	MuzzleFlash(FlashScale);
	UMIEffects* Fx = UMIEffects::Get(this);
	// Brass out of the ejection port along the port's +X (ANIMATION.md 8.3), a little back and up, with the body's motion.
	FTransform Eject;
	if (Fx && Camera && FPRig && FPRig->EjectInCamera(Eject))
	{
		const FQuat Cam = Camera->GetComponentQuat();
		const FVector Out = Cam.RotateVector(Eject.GetRotation().GetAxisX());
		const FVector V = Out * FMath::FRandRange(220.0, 320.0) + Cam.RotateVector(FVector(-60.0, 0.0, 90.0)) + FMath::VRand() * 30.0 + Player->GetPlayerRules().Velocity;
		// Drawn at the first-person depth and size (FirstPersonToNearWorld), so it leaves the port on screen instead of
		// flying behind the gun at the world depth.
		const FTransform At = FirstPersonToNearWorld(Eject);
		Fx->Casing(FPRig->GetCasingMesh(), At, V * At.GetScale3D().X + Player->GetPlayerRules().Velocity * (1.0 - At.GetScale3D().X));
	}
	if (Result.Distance < ViewData.TracerMinHit * 100.0)
	{
		return;
	}
	FVector Pos, Dir;
	const FVector Muzzle = MuzzleCamera(Pos, Dir) ? FirstPersonToWorld(Pos) : Shot.Origin;
	if (Fx && Fx->CanDrawTracers())
	{
		// Leaves the screen a little ahead of the muzzle (spec 02 2.8: hidden for the first metre when it flies far).
		const FVector Path = Result.Point - Muzzle;
		// Starts a metre past the muzzle (review 2026-11-23), more when the rules hide the first stretch.
		const double Skip = FMath::Max(100.0, Path.Size() > ViewData.TracerHiddenFrom * 100.0 ? ViewData.TracerHidden * 100.0 : 0.0);
		if (Path.Size() <= Skip + 50.0)
		{
			return;
		}
		Fx->Tracer(Muzzle + Path.GetSafeNormal() * Skip, Result.Point, TracerSpeed);
		return;
	}
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
