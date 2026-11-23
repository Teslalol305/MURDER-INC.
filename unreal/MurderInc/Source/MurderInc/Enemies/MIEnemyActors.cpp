#include "Enemies/MIEnemyActors.h"

#include "Animation/AnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Flow/MIGameSubsystem.h"
#include "MurderInc.h"
#include "Weapons/MICombatSubsystem.h"
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
	Out.GoonAnimClass = FSoftClassPath(G->GetStringField(TEXT("animClass")));
	G->TryGetNumberField(TEXT("meshYaw"), Out.GoonMeshYaw);
	Out.GoonWeapon = FSoftObjectPath(G->GetStringField(TEXT("weapon")));
	Out.GoonWeaponSocket = FName(G->GetStringField(TEXT("weaponSocket")));
	Out.GoonMuzzleSocket = FName(G->GetStringField(TEXT("muzzleSocket")));
	if (const TSharedPtr<FJsonObject> Death = Obj(G, TEXT("death")))
	{
		for (const auto& Pair : Death->Values)
		{
			Out.GoonDeath.Add(FName(FString(*Pair.Key)), FSoftObjectPath(Pair.Value->AsString()));
		}
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
	: Super(ObjectInitializer.SetDefaultSubobjectClass<UMIGoonMovement>(ACharacter::CharacterMovementComponentName))
{
	using namespace MIEnemyActorsPrivate;
	PrimaryActorTick.bCanEverTick = false;
	AutoPossessAI = EAutoPossessAI::Disabled;
	AIControllerClass = nullptr;
	Off(GetCapsuleComponent());
	Off(GetMesh());
	GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
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
	GetMesh()->SetRelativeLocationAndRotation(FVector(0, 0, -Tune.Height * 50.0), FRotator(0, Look.GoonMeshYaw, 0));
	for (const FSoftObjectPath& Path : Look.GoonVariants)
	{
		Variants.Add(Cast<USkeletalMesh>(Path.TryLoad()));
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
	if (USkeletalMesh* Weapon = Cast<USkeletalMesh>(Look.GoonWeapon.TryLoad()))
	{
		Gun->SetSkinnedAssetAndUpdate(Weapon, true);
	}
	Gun->AttachToComponent(GetMesh(), FAttachmentTransformRules::SnapToTargetNotIncludingScale, Look.GoonWeaponSocket);
	Lamp->AttachToComponent(Gun, FAttachmentTransformRules::SnapToTargetNotIncludingScale, Look.GoonMuzzleSocket);
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
	GetMesh()->SetComponentTickEnabled(bOn);
	Lamp->SetVisibility(bOn);
	if (!bOn)
	{
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
	SetActorLocationAndRotation(Feet + FVector(0, 0, Half), FRotator(0, YawToUnreal(E.Yaw), 0), false, nullptr, ETeleportType::TeleportPhysics);
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
		bDying = true;
		// The killing shot's direction in model space (x right, z back): fall away from it.
		const FVector D = E.DeathDir;
		View.DeathDirection = FVector(-D.Z, D.X, 0.0).GetSafeNormal();
		const FName Clip = FMath::Abs(D.X) > FMath::Abs(D.Z) ? (D.X > 0.0 ? FName(TEXT("left")) : FName(TEXT("right"))) : (D.Z > 0.0 ? FName(TEXT("back")) : FName(TEXT("front")));
		const TObjectPtr<UAnimSequence>* Seq = Deaths.Find(Clip);
		if (!Seq || !*Seq)
		{
			Seq = Deaths.Find(TEXT("front"));
		}
		if (Seq && *Seq)
		{
			GetMesh()->PlayAnimation(*Seq, false);
		}
		Lamp->SetIntensity(0.f);
	}
}

void AMIGoon::OnRuleEvent(const FMIEnemyEvent& Event)
{
	View.LastEvent = Event.Kind;
	View.SinceEvent = 0.0;
	if (Event.Kind == FMIEnemyEvent::EKind::Hit)
	{
		View.Flash = FMath::Min(1.0, View.Flash + 0.55 + 0.25 * FMath::Clamp(Event.Damage / FMath::Max(1.0, Tune.Hp), 0.0, 1.0));
	}
}

FMIDamageResult AMIGoon::ApplyMIDamage(const FMIDamage& Damage)
{
	UMIGameSubsystem* Game = UMIGameSubsystem::Get(this);
	return Game ? Game->DamageEnemy(Slot, Damage) : FMIDamageResult();
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
	for (int32 I = 0; I < Rotors.Num(); ++I)
	{
		Rotors[I]->SetVisibility(I != E.LostRotor);
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
