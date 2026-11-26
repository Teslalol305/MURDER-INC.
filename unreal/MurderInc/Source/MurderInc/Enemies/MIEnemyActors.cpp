#include "Enemies/MIEnemyActors.h"
#include "Enemies/MIGoonMesh.h"

#include "Animation/AnimInstance.h"
#include "Animation/AnimSequence.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/BodyInstance.h"
#include "HAL/PlatformTime.h"
#include "HAL/IConsoleManager.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "AnimationRuntime.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Core/Data/MILoadoutData.h"
#include "Dom/JsonObject.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Flow/MIGameSubsystem.h"
#include "MurderInc.h"
#include "Weapons/MICombatSubsystem.h"
#include "Weapons/MIEffects.h"
#include "World/MIBoxWorld.h"

namespace MIEnemyActorsPrivate
{
	void BulletOnly(UPrimitiveComponent* C)
	{
		C->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
		C->SetCollisionObjectType(ECC_Pawn);
		C->SetCollisionResponseToAllChannels(ECR_Ignore);
		C->SetCollisionResponseToChannel(MIBulletChannel, ECR_Block);
		C->SetCanEverAffectNavigation(false);
	}

	void Off(UPrimitiveComponent* C)
	{
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetCanEverAffectNavigation(false);
		C->SetGenerateOverlapEvents(false);
	}

	FVector DirToUnreal(const FVector& D) { return FVector(D.X, D.Z, D.Y); }

	// The death pass's switch: 1 a killed Goon falls as a ragdoll from its killing hit, 0 the death clip by direction
	// (the behaviour before the pass). A launch option can set it (-MICVars=mi.Goon.Ragdoll=0).
	/** One ragdoll start of this frame's budget (GFrameCounter: the engine frame), or false when it is spent. */
	bool TakeRagdollStart(int32 Budget)
	{
		static uint64 Frame = 0;
		static int32 Used = 0;
		if (Frame != GFrameCounter)
		{
			Frame = GFrameCounter;
			Used = 0;
		}
		if (Budget > 0 && Used >= Budget)
		{
			return false;
		}
		++Used;
		return true;
	}

	TAutoConsoleVariable<int32> CVarRagdoll(TEXT("mi.Goon.Ragdoll"), 1,
		TEXT("1: a killed Goon falls as a ragdoll from its killing hit; 0: the death clip by the shot's direction"));

	double Ease(double Current, double Target, double Rate, double Dt) { return Current + (Target - Current) * (1.0 - FMath::Exp(-Rate * Dt)); }

	FLinearColor Colour(const TSharedPtr<FJsonObject>& O, const TCHAR* Field, FLinearColor Default)
	{
		const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
		if (O.IsValid() && O->TryGetArrayField(Field, A) && A->Num() >= 3)
		{
			return FLinearColor((*A)[0]->AsNumber(), (*A)[1]->AsNumber(), (*A)[2]->AsNumber());
		}
		return Default;
	}

	FVector Vec(const TSharedPtr<FJsonObject>& O, const TCHAR* Field, FVector Default)
	{
		const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
		if (O.IsValid() && O->TryGetArrayField(Field, A) && A->Num() >= 3)
		{
			return FVector((*A)[0]->AsNumber(), (*A)[1]->AsNumber(), (*A)[2]->AsNumber());
		}
		return Default;
	}

	TSharedPtr<FJsonObject> Obj(const TSharedPtr<FJsonObject>& O, const TCHAR* Field)
	{
		const TSharedPtr<FJsonObject>* Out = nullptr;
		return O.IsValid() && O->TryGetObjectField(Field, Out) ? *Out : nullptr;
	}
}

bool FMIEnemyLook::Load(FMIEnemyLook& Out, FString& OutError)
{
	using namespace MIEnemyActorsPrivate;
	TSharedPtr<FJsonObject> Root;
	if (!UMIDataSubsystem::LoadJsonFile(TEXT("presentation.json"), Root, OutError))
	{
		return false;
	}
	const TSharedPtr<FJsonObject> Enemies = Obj(Root, TEXT("enemies"));
	const TSharedPtr<FJsonObject> G = Obj(Enemies, TEXT("goon"));
	const TSharedPtr<FJsonObject> B = Obj(Enemies, TEXT("buzzard"));
	if (!G.IsValid() || !B.IsValid())
	{
		OutError = TEXT("presentation.json: enemies.goon / enemies.buzzard missing");
		return false;
	}
	Out = FMIEnemyLook();
	const TArray<TSharedPtr<FJsonValue>>* Variants = nullptr;
	if (G->TryGetArrayField(TEXT("variants"), Variants))
	{
		for (const TSharedPtr<FJsonValue>& V : *Variants)
		{
			Out.GoonVariants.Add(FSoftObjectPath(V->AsString()));
		}
	}
	if (G->TryGetArrayField(TEXT("variantsFallback"), Variants))
	{
		for (const TSharedPtr<FJsonValue>& V : *Variants)
		{
			Out.GoonVariantsFallback.Add(FSoftObjectPath(V->AsString()));
		}
	}
	G->TryGetNumberField(TEXT("meshScale"), Out.GoonMeshScale);
	Out.GoonAnimClass = FSoftClassPath(G->GetStringField(TEXT("animClass")));
	G->TryGetNumberField(TEXT("meshYaw"), Out.GoonMeshYaw);
	Out.GoonWeapon = FSoftObjectPath(G->GetStringField(TEXT("weapon")));
	Out.GoonWeaponFallback = FSoftObjectPath(G->HasField(TEXT("weaponFallback")) ? G->GetStringField(TEXT("weaponFallback")) : FString());
	Out.GoonWeaponSocket = FName(G->GetStringField(TEXT("weaponSocket")));
	Out.GoonWeaponSocketFallback = G->HasField(TEXT("weaponSocketFallback")) ? FName(G->GetStringField(TEXT("weaponSocketFallback"))) : Out.GoonWeaponSocket;
	{
		const TSharedPtr<FJsonValue> SG = MIJson::Get(G, TEXT("supportGrip"));
		if (SG.IsValid() && SG->Type == EJson::Array && SG->AsArray().Num() == 3)
		{
			Out.GoonSupportGrip = FVector(SG->AsArray()[0]->AsNumber(), SG->AsArray()[1]->AsNumber(), SG->AsArray()[2]->AsNumber());
		}
	}
	if (const TSharedPtr<FJsonObject> W = Obj(G, TEXT("weaponOffset")))
	{
		const FVector L = Vec(W, TEXT("loc"), FVector::ZeroVector);
		const FVector R = Vec(W, TEXT("rot"), FVector::ZeroVector);  // pitch, yaw, roll (degrees)
		Out.GoonWeaponOffset = FTransform(FRotator(R.X, R.Y, R.Z), L);
	}
	Out.GoonMuzzleOffset = Vec(G, TEXT("muzzleOffset"), FVector::ZeroVector);
	Out.GoonMuzzleSocket = FName(G->GetStringField(TEXT("muzzleSocket")));
	if (const TSharedPtr<FJsonObject> Death = Obj(G, TEXT("death")))
	{
		for (const auto& Pair : Death->Values)
		{
			Out.GoonDeath.Add(FName(FString(*Pair.Key)), FSoftObjectPath(Pair.Value->AsString()));
		}
	}
	if (const TSharedPtr<FJsonObject> R = Obj(G, TEXT("ragdoll")))
	{
		FRagdoll& D = Out.GoonRagdoll;
		D.PhysicsAsset = FSoftObjectPath(MIJson::StringOr(R, TEXT("physicsAsset")));
		R->TryGetNumberField(TEXT("bone"), D.Bone);
		R->TryGetNumberField(TEXT("boneHead"), D.BoneHead);
		R->TryGetNumberField(TEXT("carry"), D.Carry);
		R->TryGetNumberField(TEXT("carryHead"), D.CarryHead);
		R->TryGetNumberField(TEXT("blast"), D.Blast);
		R->TryGetNumberField(TEXT("blastUp"), D.BlastUp);
		R->TryGetNumberField(TEXT("maxSpeed"), D.MaxSpeed);
		R->TryGetNumberField(TEXT("settleSpeed"), D.SettleSpeed);
		R->TryGetNumberField(TEXT("settleFor"), D.SettleFor);
		R->TryGetNumberField(TEXT("minSim"), D.MinSim);
		R->TryGetNumberField(TEXT("maxSim"), D.MaxSim);
		R->TryGetNumberField(TEXT("poolFade"), D.PoolFade);
		R->TryGetNumberField(TEXT("linearDamping"), D.LinearDamping);
		R->TryGetNumberField(TEXT("angularDamping"), D.AngularDamping);
		R->TryGetNumberField(TEXT("startsPerFrame"), D.StartsPerFrame);
	}
	if (const TSharedPtr<FJsonObject> Bones = Obj(G, TEXT("bones")))
	{
		Out.HeadBone = FName(Bones->GetStringField(TEXT("head")));
	}
	if (const TSharedPtr<FJsonObject> L = Obj(G, TEXT("lamp")))
	{
		Out.GoonLampColour = Colour(L, TEXT("colour"), Out.GoonLampColour);
		L->TryGetNumberField(TEXT("candelaPerLamp"), Out.GoonLampCandela);
		L->TryGetNumberField(TEXT("radius"), Out.GoonLampRadius);
		L->TryGetNumberField(TEXT("rise"), Out.GoonLampRise);
		L->TryGetNumberField(TEXT("fall"), Out.GoonLampFall);
	}
	Out.BuzzardBody = FSoftObjectPath(B->GetStringField(TEXT("body")));
	Out.BuzzardBodySize = Vec(B, TEXT("bodySize"), Out.BuzzardBodySize);
	Out.BuzzardRotor = FSoftObjectPath(B->GetStringField(TEXT("rotor")));
	Out.BuzzardRotorSize = Vec(B, TEXT("rotorSize"), Out.BuzzardRotorSize);
	Out.BuzzardMesh = FSoftObjectPath(MIJson::StringOr(B, TEXT("mesh")));
	Out.BuzzardEyeMaterial = FSoftObjectPath(MIJson::StringOr(B, TEXT("eyeMaterial")));
	B->TryGetNumberField(TEXT("eyeNits"), Out.BuzzardEyeNits);
	if (const TSharedPtr<FJsonObject> E = Obj(B, TEXT("eye")))
	{
		Out.BuzzardEyeColour = Colour(E, TEXT("colour"), Out.BuzzardEyeColour);
		E->TryGetNumberField(TEXT("candelaPerLamp"), Out.BuzzardEyeCandela);
		E->TryGetNumberField(TEXT("radius"), Out.BuzzardEyeRadius);
	}
	return true;
}

// ================================================================================================== AMIGoon

AMIGoon::AMIGoon(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer.SetDefaultSubobjectClass<UMIGoonMovement>(ACharacter::CharacterMovementComponentName)
		.SetDefaultSubobjectClass<UMIGoonMeshComponent>(ACharacter::MeshComponentName))
{
	using namespace MIEnemyActorsPrivate;
	PrimaryActorTick.bCanEverTick = false;
	AutoPossessAI = EAutoPossessAI::Disabled;
	AIControllerClass = nullptr;
	Off(GetCapsuleComponent());
	Off(GetMesh());
	GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
	// The ragdoll's bodies (death pass) collide with the world's geometry only: never with the player, other bodies,
	// rounds (the Bullet channel), the camera or a sight line. Off until the killing hit.
	GetMesh()->SetCollisionObjectType(ECC_PhysicsBody);
	GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);
	GetMesh()->SetCollisionResponseToChannel(ECC_WorldStatic, ECR_Block);
	GetMesh()->SetCollisionResponseToChannel(ECC_WorldDynamic, ECR_Block);
	GetMesh()->bReceivesDecals = false;  // blood and bullet marks land on the world, not on a Goon
	if (UCharacterMovementComponent* Move = GetCharacterMovement())
	{
		Move->PrimaryComponentTick.bStartWithTickEnabled = false;
		Move->bOrientRotationToMovement = false;
		Move->SetComponentTickEnabled(false);
	}

	BodyHit = CreateDefaultSubobject<UCapsuleComponent>(TEXT("BodyHit"));
	BodyHit->SetupAttachment(GetCapsuleComponent());
	BulletOnly(BodyHit);
	BodyHit->SetUsingAbsoluteLocation(true);
	BodyHit->SetUsingAbsoluteRotation(true);
	HeadHit = CreateDefaultSubobject<USphereComponent>(TEXT("HeadHit"));
	HeadHit->SetupAttachment(GetCapsuleComponent());
	HeadHit->ComponentTags.Add(TEXT("head"));
	BulletOnly(HeadHit);
	HeadHit->SetUsingAbsoluteLocation(true);

	Gun = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Gun"));
	Gun->SetupAttachment(GetMesh());
	Off(Gun);
	Gun->bReceivesDecals = false;
	GunStatic = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("GunStatic"));
	GunStatic->SetupAttachment(GetMesh());
	Off(GunStatic);
	GunStatic->bReceivesDecals = false;
	GunStatic->SetCastShadow(true);
	Lamp = CreateDefaultSubobject<UPointLightComponent>(TEXT("Lamp"));
	Lamp->SetupAttachment(Gun);
	Lamp->SetIntensityUnits(ELightUnits::Candelas);
	Lamp->SetIntensity(0.f);
	Lamp->SetCastShadows(false);
}

void AMIGoon::Setup(int32 InSlot, const FMIEnemyLook& Look, const FMIGoonTune& InTune)
{
	Slot = InSlot;
	Tune = InTune;
	GetCapsuleComponent()->SetCapsuleSize(Tune.Radius * 100.0, Tune.Height * 50.0);
	MeshRotation = FRotator(0, Look.GoonMeshYaw, 0);
	GetMesh()->SetRelativeLocationAndRotation(FVector(0, 0, -Tune.Height * 50.0), MeshRotation);
	for (const FSoftObjectPath& Path : Look.GoonVariants)
	{
		Variants.Add(Cast<USkeletalMesh>(Path.TryLoad()));
	}
	// The real Goons when every outfit is in the project, else the template mannequins (a clean checkout).
	const bool bReal = Variants.Num() > 0 && !Variants.Contains(nullptr);
	if (!bReal)
	{
		Variants.Reset();
		for (const FSoftObjectPath& Path : Look.GoonVariantsFallback)
		{
			Variants.Add(Cast<USkeletalMesh>(Path.TryLoad()));
		}
	}
	MeshScale = FVector(bReal ? Look.GoonMeshScale : 1.0);
	GetMesh()->SetRelativeScale3D(MeshScale);
	// The mannequin skeleton's physics asset for the ragdoll (the Goons are skinned on it bone for bone).
	RagTune = Look.GoonRagdoll;
	HeadBone = Look.HeadBone;
	Ragdoll = RagTune.PhysicsAsset.IsValid() ? Cast<UPhysicsAsset>(RagTune.PhysicsAsset.TryLoad()) : nullptr;
	if (Ragdoll)
	{
		GetMesh()->SetPhysicsAsset(Ragdoll, false);
	}
	if (Variants.Num() > 0 && Variants[0])
	{
		GetMesh()->SetSkinnedAssetAndUpdate(Variants[0], true);  // the sockets the gun hangs on
		ShownVariant = 0;
	}
	AnimClass = Look.GoonAnimClass.TryLoadClass<UAnimInstance>();
	for (const TPair<FName, FSoftObjectPath>& D : Look.GoonDeath)
	{
		Deaths.Add(D.Key, Cast<UAnimSequence>(D.Value.TryLoad()));
	}
	// The Goon SMG (a static mesh whose origin is the grip) on hand_r at its offset, else the template rifle on its socket.
	UObject* WeaponAsset = Look.GoonWeapon.TryLoad();
	if (UStaticMesh* SMG = Cast<UStaticMesh>(WeaponAsset))
	{
		GunStatic->SetStaticMesh(SMG);
		GunStatic->AttachToComponent(GetMesh(), FAttachmentTransformRules::SnapToTargetNotIncludingScale, Look.GoonWeaponSocket);
		GunStatic->SetRelativeTransform(Look.GoonWeaponOffset);
		Gun->SetSkinnedAssetAndUpdate(nullptr, false);
		Lamp->AttachToComponent(GunStatic, FAttachmentTransformRules::SnapToTargetNotIncludingScale);
		Lamp->SetRelativeLocation(Look.GoonMuzzleOffset);
		// The support hand on the SMG's SupportHand point (weapons.py), through the weapon's offset on the hand bone.
		if (UMIGoonMeshComponent* Body = Cast<UMIGoonMeshComponent>(GetMesh()); Body && Look.GoonSupportGrip.IsSet())
		{
			Body->SetSupportGrip(Look.GoonWeaponSocket, FTransform(Look.GoonSupportGrip.GetValue()) * Look.GoonWeaponOffset);
		}
	}
	else
	{
		USkeletalMesh* Weapon = Cast<USkeletalMesh>(WeaponAsset);
		if (!Weapon) Weapon = Cast<USkeletalMesh>(Look.GoonWeaponFallback.TryLoad());
		if (Weapon)
		{
			Gun->SetSkinnedAssetAndUpdate(Weapon, true);
		}
		Gun->AttachToComponent(GetMesh(), FAttachmentTransformRules::SnapToTargetNotIncludingScale, Weapon == WeaponAsset ? Look.GoonWeaponSocket : Look.GoonWeaponSocketFallback);
		Lamp->AttachToComponent(Gun, FAttachmentTransformRules::SnapToTargetNotIncludingScale, Look.GoonMuzzleSocket);
	}
	Lamp->SetLightColor(Look.GoonLampColour);
	Lamp->SetAttenuationRadius(Look.GoonLampRadius);
	LampCandela = Look.GoonLampCandela;
	LampRise = Look.GoonLampRise;
	LampFall = Look.GoonLampFall;
	HeadHit->SetSphereRadius(Tune.HeadRadius * 100.0);
	BodyHit->SetCapsuleSize(Tune.BodyRadius * 100.0, Tune.Height * 40.0);
	Show(false);
}

void AMIGoon::Show(bool bOn)
{
	if (bShown == bOn)
	{
		return;
	}
	bShown = bOn;
	SetActorHiddenInGame(!bOn);
	GetMesh()->SetComponentTickEnabled(bOn && !bSettled);
	Lamp->SetVisibility(bOn);
	if (!bOn)
	{
		// The body is gone (the rules removed it): its pool fades with it.
		if (PoolHandle != 0)
		{
			if (UMIEffects* Fx = UMIEffects::Get(this))
			{
				Fx->EndBloodPool(PoolHandle, RagTune.PoolFade);
			}
			PoolHandle = 0;
		}
		BodyHit->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		HeadHit->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	}
}

void AMIGoon::Sync(const FMIEnemy& E, const FVector& HeadWeb, double Dt)
{
	using namespace MI::Web;
	using namespace MIEnemyActorsPrivate;
	View.SinceEvent += Dt;
	if (!E.bActive)
	{
		View.bAlive = false;
		Show(false);
		return;
	}
	if (E.Id != SpawnId)
	{
		// A fresh unit in this slot: its outfit, the living animation, nothing left of the last one.
		SpawnId = E.Id;
		bDying = false;
		View = FMIEnemyView();
		ResetBody();
		const int32 V = Variants.Num() > 0 ? FMath::Clamp(E.Variant, 0, Variants.Num() - 1) : -1;
		if (V >= 0 && Variants[V] && V != ShownVariant)
		{
			GetMesh()->SetSkinnedAssetAndUpdate(Variants[V], true);
			ShownVariant = V;
		}
		GetMesh()->SetAnimationMode(EAnimationMode::AnimationBlueprint);
		if (AnimClass)
		{
			GetMesh()->SetAnimInstanceClass(AnimClass);
		}
	}
	Show(true);
	const double Half = Tune.Height * 50.0;
	const FVector Feet = ToUnreal(E.Pos);
	if (!bRagdoll && !bStaged)  // a ragdoll lies where it fell; the rules' unit does not move once dead
	{
		SetActorLocationAndRotation(Feet + FVector(0, 0, Half), FRotator(0, YawToUnreal(E.Yaw), 0), false, nullptr, ETeleportType::TeleportPhysics);
	}
	BlastTarget = Feet + FVector(0, 0, Tune.Height * 50.0);

	const FVector Velocity = DirToUnreal(E.Vel) * 100.0;
	if (UMIGoonMovement* Move = Cast<UMIGoonMovement>(GetCharacterMovement()))
	{
		// Animation blueprints gate locomotion on "accelerating": report a push along the motion while it moves.
		Move->Present(Velocity, Velocity.SizeSquared2D() > 1.0 ? Velocity.GetSafeNormal2D() * Tune.Accel * 100.0 : FVector::ZeroVector, !E.bOnGround);
	}
	View.Mode = E.Mode;
	View.Sub = E.Sub;
	View.bAlive = E.bAlive;
	View.Velocity = Velocity;
	View.Speed = E.Speed * 100.0;
	View.YawRate = -FMath::RadiansToDegrees(E.YawRate);
	View.Crouch = E.WantCrouch;
	View.Aim = E.WantAim;
	View.AimYaw = -FMath::RadiansToDegrees(E.AimYawRel);
	View.AimPitch = FMath::RadiansToDegrees(E.AimPitch);
	View.LookYaw = -FMath::RadiansToDegrees(E.LookYawRel);
	View.LookPitch = FMath::RadiansToDegrees(E.LookPitch);
	View.RushPhase = E.RushPhase;
	View.RushK = E.RushK;
	View.Variant = E.Variant;
	View.Flash = FMath::Max(0.0, View.Flash - 7.0 * Dt);
	View.Lamp = Ease(View.Lamp, E.LampWant, E.LampWant > View.Lamp ? LampRise : LampFall, Dt);
	Lamp->SetIntensity(View.Lamp * LampCandela);
	SetRemoteViewPitch(View.AimPitch);
	// Presentation: the template rifle set aims along the body, so the drawn body turns onto the rules' aim while
	// aiming (the hit volumes stay the rules'); the support hand holds the SMG while alive.
	const double WantTurn = E.bAlive ? FMath::Clamp(View.AimYaw, -75.0, 75.0) * FMath::Clamp(View.Aim, 0.0, 1.0) : 0.0;
	AimTurn += (WantTurn - AimTurn) * FMath::Min(1.0, 12.0 * Dt);
	if (!bDying)
	{
		GetMesh()->SetRelativeRotation(MeshRotation + FRotator(0, AimTurn, 0));
	}
	if (UMIGoonMeshComponent* Body = Cast<UMIGoonMeshComponent>(GetMesh()))
	{
		Body->SetSupportWeight(E.bAlive && !bDying ? 1.f : bRagdoll ? 0.f : FMath::Max(0.f, Body->GetSupportWeight() - static_cast<float>(4.0 * Dt)));
	}

	// Hit volumes from the rule state (config.json sizes), never from the drawn pose.
	const FVector Head = ToUnreal(HeadWeb);
	const double HeadR = Tune.HeadRadius * 100.0, BodyR = Tune.BodyRadius * 100.0;
	const double Top = Head.Z - HeadR, Bottom = Feet.Z + BodyR;
	HeadHit->SetWorldLocation(Head);
	BodyHit->SetCapsuleSize(BodyR, FMath::Max(BodyR, (Top - Bottom) * 0.5), false);
	BodyHit->SetWorldLocation(FVector(Feet.X, Feet.Y, (Top + Bottom) * 0.5));
	const ECollisionEnabled::Type Hits = E.bAlive ? ECollisionEnabled::QueryOnly : ECollisionEnabled::NoCollision;
	if (HeadHit->GetCollisionEnabled() != Hits)
	{
		HeadHit->SetCollisionEnabled(Hits);
		BodyHit->SetCollisionEnabled(Hits);
	}

	if (!E.bAlive && !bDying)
	{
		// Ragdolls start at most RagTune.StartsPerFrame a frame (each makes 22 bodies and their joints): a grenade's
		// eight deaths fall over four frames instead of in one long frame. The blood of the killing hit is already out.
		if (!Ragdoll || MIEnemyActorsPrivate::CVarRagdoll.GetValueOnGameThread() == 0 || MIEnemyActorsPrivate::TakeRagdollStart(RagTune.StartsPerFrame))
		{
			StartDeath(E);
		}
	}
	else if (bRagdoll && !bSettled)
	{
		UpdateRagdoll(Dt);
	}
}

void AMIGoon::StartDeath(const FMIEnemy& E)
{
	bDying = true;
	DeadFor = StillFor = 0.0;
	// The killing shot's direction in model space (x right, z back): fall away from it.
	const FVector D = E.DeathDir;
	View.DeathDirection = FVector(-D.Z, D.X, 0.0).GetSafeNormal();
	const FVector ShotDir = KillHit.bSet && !KillHit.Dir.IsNearlyZero() ? KillHit.Dir.GetSafeNormal() : GetActorRotation().RotateVector(View.DeathDirection);
	const FName Clip = FMath::Abs(D.X) > FMath::Abs(D.Z) ? (D.X > 0.0 ? FName(TEXT("left")) : FName(TEXT("right"))) : (D.Z > 0.0 ? FName(TEXT("back")) : FName(TEXT("front")));
	const TObjectPtr<UAnimSequence>* Seq = Deaths.Find(Clip);
	if (!Seq || !*Seq)
	{
		Seq = Deaths.Find(TEXT("front"));
	}
	Lamp->SetIntensity(0.f);
	const double T0 = FPlatformTime::Seconds();
	// The body falls from the hit as a ragdoll (bodies made from this frame's pose); the clip still plays underneath for
	// the bones that have no body (fingers, twists), so the hands go slack instead of keeping the grip.
	bRagdoll = StartRagdoll(ShotDir);
	if (Seq && *Seq)
	{
		GetMesh()->PlayAnimation(*Seq, false);
	}
	RagdollStartCost = FPlatformTime::Seconds() - T0;
}

bool AMIGoon::StartRagdoll(const FVector& ShotDir)
{
	USkeletalMeshComponent* M = GetMesh();
	if (!Ragdoll || MIEnemyActorsPrivate::CVarRagdoll.GetValueOnGameThread() == 0 || !M->GetSkinnedAsset() || !GetWorld() || !GetWorld()->GetPhysicsScene())
	{
		return false;
	}
	if (UMIGoonMeshComponent* Body = Cast<UMIGoonMeshComponent>(M))
	{
		Body->SetSupportWeight(0.f);
	}
	M->SetCollisionEnabled(ECollisionEnabled::PhysicsOnly);
	if (M->Bodies.Num() == 0)
	{
		M->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		return false;
	}
	M->SetSimulatePhysics(true);
	// While it falls the pose follows the bodies even off screen, so the pose kept at rest is the one the physics made.
	M->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	for (FBodyInstance* B : M->Bodies)
	{
		if (B)
		{
			B->LinearDamping = static_cast<float>(RagTune.LinearDamping);
			B->AngularDamping = static_cast<float>(RagTune.AngularDamping);
			B->UpdateDampingProperties();
		}
	}
	M->WakeAllRigidBodies();
	const FVector Dir = ShotDir.IsNearlyZero() ? -GetActorForwardVector() : ShotDir.GetSafeNormal();
	if (KillHit.bBlast)
	{
		// Thrown away from the blast and up off the ground.
		FVector Away = GetActorLocation() - KillHit.From;
		Away.Z = 0.0;
		Away = Away.IsNearlyZero() ? Dir.GetSafeNormal2D() : Away.GetSafeNormal();
		M->SetAllPhysicsLinearVelocity((Away * RagTune.Blast + FVector(0, 0, RagTune.BlastUp)).GetClampedToMaxSize(RagTune.MaxSpeed));
		M->AddImpulse(FVector(0, 0, RagTune.BlastUp * 0.5), TEXT("pelvis"), true);
	}
	else
	{
		// The whole body carried a little along the shot, the bone that was hit pushed hard (a head shot snaps the head).
		const bool bHead = KillHit.bHead;
		M->SetAllPhysicsLinearVelocity(Dir * (bHead ? RagTune.CarryHead : RagTune.Carry));
		FName Bone = bHead ? HeadBone : NAME_None;
		if (Bone.IsNone() && KillHit.bSet)
		{
			Bone = M->FindClosestBone(KillHit.Point, nullptr, 0.f, true);
		}
		if (Bone.IsNone() || M->GetBodyInstance(Bone) == nullptr)
		{
			Bone = TEXT("spine_03");
		}
		M->AddImpulse((Dir * (bHead ? RagTune.BoneHead : RagTune.Bone)).GetClampedToMaxSize(RagTune.MaxSpeed), Bone, true);
	}
	return true;
}

void AMIGoon::UpdateRagdoll(double Dt)
{
	USkeletalMeshComponent* M = GetMesh();
	DeadFor += Dt;
	const FVector V = M->GetPhysicsLinearVelocity(TEXT("pelvis"));
	StillFor = V.Size() < RagTune.SettleSpeed ? StillFor + Dt : 0.0;
	if (!((DeadFor > RagTune.MinSim && StillFor > RagTune.SettleFor) || DeadFor > RagTune.MaxSim))
	{
		return;
	}
	// At rest: a pool spreads under the hips, and the body is frozen as it lies (no bodies, no pose updates: a body
	// costs nothing more until the rules remove it).
	// The hips where the physics has them (a body nobody looks at gets no bone update from the animation tick).
	const FBodyInstance* Hips = M->GetBodyInstance(TEXT("pelvis"));
	const FVector Pelvis = Hips ? Hips->GetUnrealWorldTransform().GetLocation() : M->GetBoneLocation(TEXT("pelvis"));
	FHitResult Floor;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(MIGoonPool), false, this);
	if (GetWorld() && GetWorld()->LineTraceSingleByChannel(Floor, Pelvis + FVector(0, 0, 30), Pelvis - FVector(0, 0, 150), ECC_Visibility, Q))
	{
		if (UMIEffects* Fx = UMIEffects::Get(this))
		{
			PoolHandle = Fx->BloodPool(Floor.ImpactPoint, Floor.ImpactNormal);
		}
	}
	UE_LOG(LogMI, Log, TEXT("Goon %d at rest after %.2f s: hips %s, %.0f cm over the floor under them (%s), %.0f cm from where it died"), Slot, DeadFor,
		*Pelvis.ToCompactString(), Floor.bBlockingHit ? Pelvis.Z - Floor.ImpactPoint.Z : -1.0, Floor.bBlockingHit ? TEXT("found") : TEXT("none within 1.5 m"),
		FVector::Dist2D(Pelvis, GetActorLocation()));
	M->SetComponentTickEnabled(false);
	M->bNoSkeletonUpdate = true;
	M->SetSimulatePhysics(false);
	M->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	bSettled = true;
}

void AMIGoon::StageBodyAt(const FVector& Feet, double Yaw)
{
	bStaged = true;
	SetActorLocationAndRotation(Feet + FVector(0, 0, Tune.Height * 50.0), FRotator(0, Yaw, 0), false, nullptr, ETeleportType::TeleportPhysics);
}

void AMIGoon::ResetBody()
{
	KillHit = FKillHit();
	bStaged = false;
	DeadFor = StillFor = 0.0;
	if (!bRagdoll && !bSettled)
	{
		return;
	}
	USkeletalMeshComponent* M = GetMesh();
	M->SetSimulatePhysics(false);
	M->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	M->bNoSkeletonUpdate = false;
	M->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
	bRagdoll = bSettled = false;
	M->SetComponentTickEnabled(bShown);
	if (M->GetAttachParent() != GetCapsuleComponent())
	{
		M->AttachToComponent(GetCapsuleComponent(), FAttachmentTransformRules::KeepRelativeTransform);
	}
	M->SetRelativeLocationAndRotation(FVector(0, 0, -Tune.Height * 50.0), MeshRotation, false, nullptr, ETeleportType::ResetPhysics);
	M->SetRelativeScale3D(MeshScale);
}

void AMIGoon::OnRuleEvent(const FMIEnemyEvent& Event)
{
	View.LastEvent = Event.Kind;
	View.SinceEvent = 0.0;
	if (Event.Kind == FMIEnemyEvent::EKind::Hit)
	{
		View.Flash = FMath::Min(1.0, View.Flash + 0.55 + 0.25 * FMath::Clamp(Event.Damage / FMath::Max(1.0, Tune.Hp), 0.0, 1.0));
	}
	if (Event.Kind == FMIEnemyEvent::EKind::Fire)
	{
		// Presentation: the flash at the SMG's muzzle and the round's tracer (the rules already decided the hit).
		if (UMIEffects* Fx = UMIEffects::Get(this))
		{
			using namespace MIEnemyActorsPrivate;
			FVector Dir = DirToUnreal(Event.Dir).GetSafeNormal();
			if (Dir.IsNearlyZero()) Dir = GetActorForwardVector();
			Fx->EnemyShot(this, Lamp->GetComponentLocation(), Dir);
		}
	}
}

FMIDamageResult AMIGoon::ApplyMIDamage(const FMIDamage& Damage)
{
	UMIGameSubsystem* Game = UMIGameSubsystem::Get(this);
	const FMIDamageResult R = Game ? Game->DamageEnemy(Slot, Damage) : FMIDamageResult();
	if (R.bKilled)
	{
		// Presentation of the killing hit (death pass): where and how it struck, for the fall and the blood.
		KillHit.bSet = true;
		KillHit.bBlast = Damage.Kind == EMIDamageKind::Blast;
		KillHit.bHead = !KillHit.bBlast && Damage.Part == TEXT("head");
		KillHit.From = Damage.From.Get(Damage.Point);
		KillHit.Point = KillHit.bBlast ? BlastTarget : Damage.Point;
		KillHit.Dir = KillHit.bBlast ? (BlastTarget - KillHit.From).GetSafeNormal() : Damage.Direction.GetSafeNormal();
		if (UMIEffects* Fx = UMIEffects::Get(this))
		{
			Fx->BloodKill(KillHit.Point, KillHit.Dir, KillHit.bHead, KillHit.bBlast, this);
		}
	}
	return R;
}

// ================================================================================================ AMIBuzzard

AMIBuzzard::AMIBuzzard()
{
	using namespace MIEnemyActorsPrivate;
	PrimaryActorTick.bCanEverTick = false;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;
	HitBox = CreateDefaultSubobject<UBoxComponent>(TEXT("HitBox"));
	HitBox->SetupAttachment(Root);
	BulletOnly(HitBox);
	Body = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Body"));
	Body->SetupAttachment(Root);
	Off(Body);
	Eye = CreateDefaultSubobject<UPointLightComponent>(TEXT("Eye"));
	Eye->SetupAttachment(Root);
	Eye->SetIntensityUnits(ELightUnits::Candelas);
	Eye->SetIntensity(0.f);
	Eye->SetCastShadows(false);
}

void AMIBuzzard::Setup(int32 InSlot, const FMIEnemyLook& Look, const FMIBuzzardTune& Tune, const FMIBuzzardModel& Model)
{
	using namespace MIEnemyActorsPrivate;
	Slot = InSlot;
	// The ellipsoid (radius r, half height h) as a box of the same volume's proportions: 0.8 r across, h tall.
	HitBox->SetBoxExtent(FVector(Tune.Radius * 80.0, Tune.Radius * 80.0, Tune.HalfHeight * 100.0));
	if (UStaticMesh* Mesh = Cast<UStaticMesh>(Look.BuzzardBody.TryLoad()))
	{
		Body->SetStaticMesh(Mesh);
		Body->SetRelativeScale3D(Look.BuzzardBodySize / 100.0);
	}
	UStaticMesh* RotorMesh = Cast<UStaticMesh>(Look.BuzzardRotor.TryLoad());
	for (const FVector& R : Model.Rotors)
	{
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
		C->SetupAttachment(Root);
		Off(C);
		C->SetStaticMesh(RotorMesh);
		// Model space (x right, y up, z back, metres) to actor space (X forward, Y right, Z up, cm).
		C->SetRelativeLocation(FVector(-R.Z, R.X, R.Y) * 100.0);
		C->SetRelativeScale3D(Look.BuzzardRotorSize / 100.0);
		C->RegisterComponent();
		Rotors.Add(C);
	}
	// The real drone (art/blender/assets/buzzard.py: nose +X, up +Z; imported nose +X, up +Z, right +Y).
	USkeletalMesh* DroneMesh = Look.BuzzardMesh.IsValid() ? Cast<USkeletalMesh>(Look.BuzzardMesh.TryLoad()) : nullptr;
	if (DroneMesh)
	{
		Drone = NewObject<UPoseableMeshComponent>(this, TEXT("Drone"));
		Drone->SetupAttachment(Root);
		Drone->SetSkinnedAssetAndUpdate(DroneMesh, true);
		Drone->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Drone->SetCastShadow(true);
		Drone->RegisterComponent();
		const FReferenceSkeleton& Ref = DroneMesh->GetRefSkeleton();
		for (const TCHAR* B : {TEXT("prop_fr"), TEXT("prop_fl"), TEXT("prop_rr"), TEXT("prop_rl"), TEXT("gimbal")})
		{
			const int32 I = Ref.FindBoneIndex(B);
			DroneRef.Add(I == INDEX_NONE ? FTransform::Identity : FAnimationRuntime::GetComponentSpaceTransformRefPose(Ref, I));
		}
		if (UMaterialInterface* EyeMat = Look.BuzzardEyeMaterial.IsValid() ? Cast<UMaterialInterface>(Look.BuzzardEyeMaterial.TryLoad()) : nullptr)
		{
			const int32 EyeSlot = Drone->GetMaterialIndex(TEXT("M_Buzzard_Eye"));
			if (EyeSlot != INDEX_NONE)
			{
				EyeMid = UMaterialInstanceDynamic::Create(EyeMat, this);
				EyeMid->SetVectorParameterValue(TEXT("Color"), Look.BuzzardEyeColour);
				EyeMid->SetScalarParameterValue(TEXT("Intensity"), 0.f);
				Drone->SetMaterial(EyeSlot, EyeMid);
			}
		}
		EyeNits = Look.BuzzardEyeNits;
		Body->SetVisibility(false);
		for (UStaticMeshComponent* C : Rotors) C->SetVisibility(false);
	}
	Eye->SetRelativeLocation(FVector(-Model.Eye.Z, Model.Eye.X, Model.Eye.Y) * 100.0);
	Eye->SetLightColor(Look.BuzzardEyeColour);
	Eye->SetAttenuationRadius(Look.BuzzardEyeRadius);
	EyeCandela = Look.BuzzardEyeCandela;
	SetActorHiddenInGame(true);
	HitBox->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

void AMIBuzzard::Sync(const FMIEnemy& E, double Dt)
{
	using namespace MI::Web;
	View.SinceEvent += Dt;
	if (!E.bActive)
	{
		View.bAlive = false;
		if (!IsHidden())
		{
			SetActorHiddenInGame(true);
			HitBox->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		}
		return;
	}
	if (IsHidden())
	{
		SetActorHiddenInGame(false);
	}
	SetActorLocationAndRotation(ToUnreal(E.Pos), FRotator(FMath::RadiansToDegrees(E.Pitch), YawToUnreal(E.Yaw), FMath::RadiansToDegrees(E.Roll)), false, nullptr, ETeleportType::TeleportPhysics);
	const ECollisionEnabled::Type Hits = E.bAlive ? ECollisionEnabled::QueryOnly : ECollisionEnabled::NoCollision;
	if (HitBox->GetCollisionEnabled() != Hits)
	{
		HitBox->SetCollisionEnabled(Hits);
	}
	View.Mode = E.Mode;
	View.bAlive = E.bAlive;
	View.Velocity = FVector(E.Vel.X, E.Vel.Z, E.Vel.Y) * 100.0;
	View.Speed = View.Velocity.Size();
	View.RotorSpeed = E.RotorSpeed;
	View.RotorAngle = FMath::RadiansToDegrees(E.RotorAngle);
	View.EyeYaw = -FMath::RadiansToDegrees(E.EyeYaw);
	View.EyePitch = FMath::RadiansToDegrees(E.EyePitch);
	View.LostRotor = E.LostRotor;
	View.Lamp = E.Lamp;
	View.Flash = E.Flash;
	if (Drone && DroneRef.Num() == 5)
	{
		// Props (rules' rotor order: front-right, front-left, rear-right, rear-left) about their hub's +Z; fl and rr
		// counter-clockwise seen from above, fr and rl clockwise (buzzard.py); a lost rotor is hidden.
		static const FName Props[4] = {TEXT("prop_fr"), TEXT("prop_fl"), TEXT("prop_rr"), TEXT("prop_rl")};
		static const double Turn[4] = {-1.0, 1.0, 1.0, -1.0};
		for (int32 I = 0; I < 4; ++I)
		{
			const FTransform& R = DroneRef[I];
			const FQuat Spin(FVector::UpVector, FMath::DegreesToRadians(Turn[I] * View.RotorAngle));
			Drone->SetBoneTransformByName(Props[I], FTransform(Spin * R.GetRotation(), R.GetLocation(), I == E.LostRotor ? FVector(0.001) : FVector::OneVector), EBoneSpaces::ComponentSpace);
		}
		// The gimbal turned to the rules' eye (yaw, then pitch up positive) about its own pivot.
		const FTransform& G = DroneRef[4];
		Drone->SetBoneTransformByName(TEXT("gimbal"), FTransform(FRotator(View.EyePitch, View.EyeYaw, 0.0).Quaternion() * G.GetRotation(), G.GetLocation()), EBoneSpaces::ComponentSpace);
		if (EyeMid)
		{
			EyeMid->SetScalarParameterValue(TEXT("Intensity"), static_cast<float>(E.Lamp * EyeNits));
		}
	}
	for (int32 I = 0; I < Rotors.Num(); ++I)
	{
		Rotors[I]->SetVisibility(!Drone && I != E.LostRotor);
		Rotors[I]->SetRelativeRotation(FRotator(0, (I % 2 ? -1.0 : 1.0) * View.RotorAngle, 0));
	}
	Eye->SetIntensity(E.Lamp * EyeCandela);
}

void AMIBuzzard::OnRuleEvent(const FMIEnemyEvent& Event)
{
	View.LastEvent = Event.Kind;
	View.SinceEvent = 0.0;
}

FMIDamageResult AMIBuzzard::ApplyMIDamage(const FMIDamage& Damage)
{
	UMIGameSubsystem* Game = UMIGameSubsystem::Get(this);
	return Game ? Game->DamageEnemy(Slot, Damage) : FMIDamageResult();
}
