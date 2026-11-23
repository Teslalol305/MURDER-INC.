#include "Weapons/MIFirstPersonRig.h"

#include "Animation/AnimSequenceBase.h"
#include "AnimationRuntime.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Core/Data/MILoadoutData.h"
#include "Dom/JsonObject.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/SkeletalMeshSocket.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"
#include "MurderInc.h"
#include "Weapons/MIEffects.h"
#include "Weapons/MIGunAssembly.h"
#include "Weapons/MILoadoutResolver.h"
#include "Weapons/MIViewmodel.h"
#include "Weapons/MIWeaponComponent.h"

namespace MIFirstPersonRigPrivate
{
	TSharedPtr<FJsonObject> Obj(const TSharedPtr<FJsonObject>& O, const FString& Path)
	{
		const TSharedPtr<FJsonValue> V = MIJson::Get(O, Path);
		return V.IsValid() && V->Type == EJson::Object ? V->AsObject() : nullptr;
	}

	double Num(const TSharedPtr<FJsonObject>& O, const FString& Path, double Fallback)
	{
		return MIJson::NumberOr(O, Path, Fallback);
	}

	template <typename T>
	T* LoadAs(const FString& Path)
	{
		return Path.IsEmpty() ? nullptr : Cast<T>(FSoftObjectPath(Path).TryLoad());
	}

	double Damp(double From, double To, double Rate, double Dt)
	{
		return To + (From - To) * FMath::Exp(-Rate * Dt);
	}

	double Smooth(double X)
	{
		X = FMath::Clamp(X, 0.0, 1.0);
		return X * X * (3.0 - 2.0 * X);
	}

	/** Blender world matrix (16 numbers, row-major, metres, Z up) -> Unreal transform (cm): through glTF, Blender
	 *  (x, y, z) lands as Unreal (x, -y, z) x 100 (docs/unreal/BOX.md 5, tools/box/chars/mi_chars.ue_from_blender). */
	FTransform FromBlender(const TArray<double>& M)
	{
		if (M.Num() < 16)
		{
			return FTransform::Identity;
		}
		const double Cv[3] = {1, -1, 1};
		double R[3][3];
		for (int32 I = 0; I < 3; ++I)
		{
			for (int32 J = 0; J < 3; ++J)
			{
				R[I][J] = Cv[I] * M[I * 4 + J] * Cv[J];
			}
		}
		const FVector T(M[3] * 100.0, -M[7] * 100.0, M[11] * 100.0);
		const FMatrix X(FPlane(R[0][0], R[1][0], R[2][0], 0), FPlane(R[0][1], R[1][1], R[2][1], 0), FPlane(R[0][2], R[1][2], R[2][2], 0), FPlane(T.X, T.Y, T.Z, 1));
		return FTransform(X);
	}

	void FirstPerson(UPrimitiveComponent* C, const UPrimitiveComponent* Like)
	{
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetCastShadow(false);
		C->bOnlyOwnerSee = Like->bOnlyOwnerSee;
		C->SetFirstPersonPrimitiveType(Like->FirstPersonPrimitiveType);
	}
}

UMIFirstPersonRig::UMIFirstPersonRig()
{
	PrimaryComponentTick.bCanEverTick = false;
}

void UMIFirstPersonRig::Init(UMIWeaponComponent* InWeapon, USkeletalMeshComponent* InArms, UCameraComponent* InCamera, const TSharedPtr<FJsonObject>& Presentation)
{
	using namespace MIFirstPersonRigPrivate;
	Weapon = InWeapon;
	Arms = InArms;
	Camera = InCamera;
	Root = Presentation;
	const TSharedPtr<FJsonObject> Recipe = Obj(Root, TEXT("firstPerson.recipe"));
	if (Recipe)
	{
		const TSharedPtr<FJsonValue> L = MIJson::Get(Recipe, TEXT("armsLocation"));
		FVector Loc(-0.66, 0.0, -162.0);
		if (L.IsValid() && L->Type == EJson::Array && L->AsArray().Num() == 3)
		{
			Loc = FVector(L->AsArray()[0]->AsNumber(), L->AsArray()[1]->AsNumber(), L->AsArray()[2]->AsNumber());
		}
		ArmsRest = FTransform(FRotator(0.0, Num(Recipe, TEXT("armsYaw"), -90.0), 0.0), Loc);
		FovIrons = Num(Recipe, TEXT("fovIrons"), 38.0);
		FovOptic = Num(Recipe, TEXT("fovOptic"), 32.0);
	}
	TemplateBody = LoadAs<USkeletalMesh>(MIJson::StringOr(Root, TEXT("firstPerson.body")));
	if (Arms)
	{
		Arms->SetTickGroup(TG_PostUpdateWork);  // the pose set by the weapon step this frame is evaluated this frame
		SetupArms();
	}
}

void UMIFirstPersonRig::SetupArms()
{
	using namespace MIFirstPersonRigPrivate;
	for (UStaticMeshComponent* J : Jewels)
	{
		if (J) J->DestroyComponent();
	}
	Jewels.Reset();
	USkeletalMesh* Real = LoadAs<USkeletalMesh>(MIJson::StringOr(Root, TEXT("firstPerson.arms")));
	RealArms = Real;
	if (!Real)
	{
		return;  // a clean checkout: the template body stays (AMIPlayerCharacter set it with its hidden bones)
	}
	// The jewels: their rest placement (Blender world) made relative to their bone's reference pose.
	const TSharedPtr<FJsonValue> List = MIJson::Get(Root, TEXT("firstPerson.jewels"));
	if (!List.IsValid() || List->Type != EJson::Array)
	{
		return;
	}
	const FReferenceSkeleton& Ref = Real->GetRefSkeleton();
	for (const TSharedPtr<FJsonValue>& V : List->AsArray())
	{
		const TSharedPtr<FJsonObject> J = V->AsObject();
		UStaticMesh* Mesh = J.IsValid() ? LoadAs<UStaticMesh>(MIJson::StringOr(J, TEXT("mesh"))) : nullptr;
		const FName Bone(*MIJson::StringOr(J, TEXT("bone")));
		const int32 Index = Ref.FindBoneIndex(Bone);
		if (!Mesh || Index == INDEX_NONE)
		{
			continue;
		}
		TArray<double> M;
		const TSharedPtr<FJsonValue> W = MIJson::Get(J, TEXT("blenderWorldRest"));
		if (W.IsValid() && W->Type == EJson::Array)
		{
			for (const TSharedPtr<FJsonValue>& X : W->AsArray()) M.Add(X->AsNumber());
		}
		const FTransform BoneCS = FAnimationRuntime::GetComponentSpaceTransformRefPose(Ref, Index);
		const FTransform Rel = FromBlender(M).GetRelativeTransform(BoneCS);
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(GetOwner(), NAME_None, RF_Transient);
		C->SetStaticMesh(Mesh);
		C->SetMobility(EComponentMobility::Movable);
		FirstPerson(C, Arms);
		C->RegisterComponent();
		C->AttachToComponent(Arms, FAttachmentTransformRules::SnapToTargetNotIncludingScale, Bone);
		C->SetRelativeTransform(Rel);
		C->SetVisibility(false);
		Jewels.Add(C);
	}
}

void UMIFirstPersonRig::UseRealArms(bool bReal)
{
	if (!Arms || !RealArms)
	{
		return;
	}
	USkeletalMesh* Want = bReal ? RealArms.Get() : TemplateBody.Get();
	if (Want && Arms->GetSkinnedAsset() != Want)
	{
		Arms->SetSkinnedAssetAndUpdate(Want, true);
		const TSharedPtr<FJsonValue> Hidden = MIJson::Get(Root, TEXT("firstPerson.hideBones"));
		if (Hidden.IsValid() && Hidden->Type == EJson::Array)
		{
			for (const TSharedPtr<FJsonValue>& B : Hidden->AsArray())
			{
				bReal ? Arms->UnHideBoneByName(FName(*B->AsString())) : Arms->HideBoneByName(FName(*B->AsString()), PBO_None);
			}
		}
	}
	for (UStaticMeshComponent* J : Jewels)
	{
		if (J) J->SetVisibility(bReal && Arms->IsVisible());
	}
}

UAnimSequenceBase* UMIFirstPersonRig::ArmsClip(FName Role) const
{
	const TObjectPtr<UAnimSequenceBase>* C = Clips.Arms.Find(Role);
	return C ? C->Get() : nullptr;
}

UAnimSequenceBase* UMIFirstPersonRig::GunClip(FName Role) const
{
	const TObjectPtr<UAnimSequenceBase>* C = Clips.Gun.Find(Role);
	return C ? C->Get() : nullptr;
}

EMIFPMode UMIFirstPersonRig::Equip(FName Gun, const FMIGunViewData* View, const FMIResolvedGun* Resolved, UMIGunAssembly* Assembly, USkinnedMeshComponent* LegacyGun)
{
	using namespace MIFirstPersonRigPrivate;
	GunId = Gun;
	Mode = EMIFPMode::Template;
	Clips = FClipSet();
	Loaded.Reset();
	Set.Reset();
	bOptic = false;
	GripVariant = NAME_None;
	Action = LastAction = Presented = NAME_None;
	ActionWeight = 0.0;
	FireAge = 1e9;
	if (OwnMag) { OwnMag->DestroyComponent(); OwnMag = nullptr; }
	if (ReserveMag) { ReserveMag->DestroyComponent(); ReserveMag = nullptr; }
	SeatedMag.Reset();
	if (PackGun)
	{
		PackGun->SetVisibility(false);
	}
	if (!Arms || !Root.IsValid())
	{
		return Mode;
	}
	if (Resolved)
	{
		for (const TPair<FName, FName>& F : Resolved->Def.Fitted)
		{
			if (F.Key == TEXT("optic") && F.Value != TEXT("irons")) bOptic = true;
			if (F.Key == TEXT("underbarrel")) GripVariant = F.Value;
		}
	}
	// The gun's anim set: presentation "animSet" of the resolved gun (or of presentation.json's own entry).
	const TSharedPtr<FJsonObject> P = Resolved && Resolved->Presentation.IsValid() ? Resolved->Presentation : Obj(Root, TEXT("guns.") + Gun.ToString());
	const FString SetName = MIJson::StringOr(P, TEXT("animSet"));
	Set = SetName.IsEmpty() ? nullptr : Obj(Root, TEXT("firstPerson.animSets.") + SetName);
	USkeletalMesh* ArmsMesh = RealArms ? RealArms.Get() : Cast<USkeletalMesh>(Arms->GetSkinnedAsset());
	UseRealArms(false);  // until the mode below says otherwise
	if (!Set.IsValid() || !ArmsMesh)
	{
		return Mode;
	}
	const FString Kind = MIJson::StringOr(Set, TEXT("mode"));
	// Every clip must exist and fit its skeleton; one missing clip and the gun keeps the template way.
	const auto LoadRoles = [this](const TSharedPtr<FJsonObject>& Roles, const USkeleton* Skeleton, TMap<FName, TObjectPtr<UAnimSequenceBase>>& Out)
	{
		if (!Roles.IsValid())
		{
			return false;
		}
		for (const auto& Pair : Roles->Values)
		{
			UAnimSequenceBase* A = LoadAs<UAnimSequenceBase>(Pair.Value->AsString());
			if (!A || (Skeleton && A->GetSkeleton() != Skeleton))
			{
				UE_LOG(LogMI, Warning, TEXT("First person: clip %s (%s) missing or on another skeleton: the template way"), *FString(*Pair.Key), *Pair.Value->AsString());
				return false;
			}
			Out.Add(FName(FString(*Pair.Key)), A);
			Loaded.Add(A);
		}
		return true;
	};
	if (!LoadRoles(Obj(Set, TEXT("arms")), ArmsMesh->GetSkeleton(), Clips.Arms))
	{
		return Mode;
	}
	BobScale = Num(Set, TEXT("bobScale"), 0.5);
	WalkSpeed = Num(Set, TEXT("walkSpeed"), 380.0);
	SprintSpeed = Num(Set, TEXT("sprintSpeed"), 640.0);
	FireWeight = Num(Set, TEXT("fireWeight"), 0.6);
	FireRate = Num(Set, TEXT("fireRate"), 1.0);
	DrawRange = Num(Set, TEXT("drawRange"), 0.53);
	MeleeRange = Num(Set, TEXT("meleeRange"), 1.0);
	InspectAfter = Resolved ? Resolved->Def.InspectAfter : 24.0;
	CasingMesh = LoadAs<UStaticMesh>(MIJson::StringOr(Set, TEXT("casing")));

	if (Kind == TEXT("ik"))
	{
		LeftSocket = FName(*MIJson::StringOr(Set, TEXT("ik.left")));
		RightSocket = FName(*MIJson::StringOr(Set, TEXT("ik.right")));
		Mode = EMIFPMode::HandIK;
		UseRealArms(true);
		Arms->SetAnimationMode(EAnimationMode::AnimationBlueprint);
		Arms->SetAnimInstanceClass(UMIFPAnimInstance::StaticClass());
		// The magazine on the gun's magazine bone (the rig drops and hides that bone in the reloads).
		const FName MagBone(*MIJson::StringOr(Set, TEXT("magazine.socket")));
		if (UStaticMesh* M = LoadAs<UStaticMesh>(MIJson::StringOr(Set, TEXT("magazine.full"))); M && LegacyGun && LegacyGun->DoesSocketExist(MagBone))
		{
			OwnMag = NewObject<UStaticMeshComponent>(GetOwner(), NAME_None, RF_Transient);
			OwnMag->SetStaticMesh(M);
			OwnMag->SetMobility(EComponentMobility::Movable);
			FirstPerson(OwnMag, Arms);
			OwnMag->RegisterComponent();
			OwnMag->AttachToComponent(LegacyGun, FAttachmentTransformRules::SnapToTargetNotIncludingScale, MagBone);
		}
		return Mode;
	}
	if (Kind != TEXT("pack") || !Resolved)
	{
		return Mode;
	}
	// The pack rifle on the arms' gun bone, its clips on its own skeleton.
	USkeletalMesh* GunMesh = LoadAs<USkeletalMesh>(Resolved->BaseMesh);
	if (!GunMesh || !LoadRoles(Obj(Set, TEXT("gun")), GunMesh->GetSkeleton(), Clips.Gun))
	{
		Clips = FClipSet();
		return Mode;
	}
	if (!PackGun)
	{
		PackGun = NewObject<USkeletalMeshComponent>(GetOwner(), TEXT("FirstPersonPackGun"), RF_Transient);
		FirstPerson(PackGun, Arms);
		PackGun->SetTickGroup(TG_PostUpdateWork);
		PackGun->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
		PackGun->RegisterComponent();
	}
	PackGun->AttachToComponent(Arms, FAttachmentTransformRules::SnapToTargetNotIncludingScale, FName(*MIJson::StringOr(Set, TEXT("gunSocket"), TEXT("ik_hand_gun"))));
	PackGun->SetRelativeTransform(FTransform::Identity);
	// The mesh first, so the parts find their sockets (the assembly already holds this base mesh's name from the
	// placeholder gun and would not load it again).
	PackGun->SetSkinnedAssetAndUpdate(GunMesh, true);
	if (Assembly)
	{
		Assembly->Assemble(PackGun, *Resolved, false);
	}
	UseRealArms(true);
	Arms->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	Arms->SetAnimInstanceClass(UMIFPAnimInstance::StaticClass());
	PackGun->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	PackGun->SetAnimInstanceClass(UMIFPAnimInstance::StaticClass());
	PackGun->SetVisibility(true);
	// The gun's own finish (the CHOPPER's dark earth): presentation "materials", slot -> material.
	if (const TSharedPtr<FJsonObject> Mats = Obj(P, TEXT("materials")))
	{
		for (const auto& Pair : Mats->Values)
		{
			if (UMaterialInterface* M = LoadAs<UMaterialInterface>(Pair.Value->AsString()))
			{
				PackGun->SetMaterialByName(FName(FString(*Pair.Key)), M);
			}
		}
	}
	// Magazines (9.1): the seated one is the build's magazine part, or our own; the reserve rides Magazine_Reserve.
	MagFull = LoadAs<UStaticMesh>(MIJson::StringOr(Set, TEXT("magazine.full")));
	MagEmpty = LoadAs<UStaticMesh>(MIJson::StringOr(Set, TEXT("magazine.empty")));
	const FName Hinge(*MIJson::StringOr(Set, TEXT("magazine.socket"), TEXT("MagHinge")));
	UStaticMeshComponent* Part = Assembly ? Assembly->PartMesh(TEXT("magazine")) : nullptr;
	if (!Part && MagFull)
	{
		OwnMag = NewObject<UStaticMeshComponent>(GetOwner(), NAME_None, RF_Transient);
		OwnMag->SetStaticMesh(MagFull);
		OwnMag->SetMobility(EComponentMobility::Movable);
		FirstPerson(OwnMag, PackGun);
		OwnMag->RegisterComponent();
		OwnMag->AttachToComponent(PackGun, FAttachmentTransformRules::SnapToTargetNotIncludingScale, Hinge);
		Part = OwnMag;
	}
	SeatedMag = Part;
	const FName ReserveBone(*MIJson::StringOr(Set, TEXT("magazine.reserveBone"), TEXT("Magazine_Reserve")));
	if (Part && Part->GetStaticMesh() && PackGun->GetBoneIndex(ReserveBone) != INDEX_NONE)
	{
		ReserveMag = NewObject<UStaticMeshComponent>(GetOwner(), NAME_None, RF_Transient);
		ReserveMag->SetStaticMesh(Part->GetStaticMesh());
		ReserveMag->SetMobility(EComponentMobility::Movable);
		FirstPerson(ReserveMag, PackGun);
		ReserveMag->RegisterComponent();
		ReserveMag->AttachToComponent(PackGun, FAttachmentTransformRules::SnapToTargetNotIncludingScale, ReserveBone);
		// The hinge socket's frame relative to its bone, so the reserve sits on its bone as the seated one on its own.
		if (const USkeletalMeshSocket* S = GunMesh->FindSocket(Hinge))
		{
			ReserveMag->SetRelativeTransform(S->GetSocketLocalTransform());
		}
		ReserveMag->SetVisibility(false);
	}
	// The reloads: the pack's marks mapped onto the rules' stage times (piecewise linear: every mark lands exactly).
	const auto Map = [this, View](const TCHAR* Which, double RuleTotal, FReloadMap& Out)
	{
		Out = FReloadMap();
		const TSharedPtr<FJsonObject> R = Obj(Set, FString(TEXT("reloads.")) + Which);
		UAnimSequenceBase* C = ArmsClip(FName(*MIJson::StringOr(R, TEXT("clip"))));
		if (!R || !C)
		{
			return;
		}
		Out.Keys.Add(FVector2D(0.0, 0.0));
		const TSharedPtr<FJsonValue> Marks = MIJson::Get(R, TEXT("marks"));
		if (Marks.IsValid() && Marks->Type == EJson::Array && View)
		{
			for (const TSharedPtr<FJsonValue>& M : Marks->AsArray())
			{
				const TArray<TSharedPtr<FJsonValue>>& A = M->AsArray();
				if (A.Num() < 2) continue;
				TArray<FString> Names;
				A[0]->AsString().ParseIntoArray(Names, TEXT("|"));
				for (const FString& N : Names)
				{
					if (const double* T = View->ReloadMarks.Find(FName(*N)))
					{
						if (*T > Out.Keys.Last().X && A[1]->AsNumber() > Out.Keys.Last().Y)
						{
							Out.Keys.Add(FVector2D(*T, A[1]->AsNumber()));
						}
						break;
					}
				}
			}
		}
		Out.Keys.Add(FVector2D(FMath::Max(RuleTotal, Out.Keys.Last().X + 0.05), C->GetPlayLength()));
		Out.Reserve = Num(R, TEXT("reserve"), 0.27);
		Out.Out = Num(R, TEXT("out"), 0.4);
		Out.Seated = Num(R, TEXT("seated"), 1.4);
		bool bB = true;
		Out.bDrop = !R->TryGetBoolField(TEXT("drop"), bB) || bB;
		Out.bDropFull = R->TryGetBoolField(TEXT("dropFull"), bB) && bB;
	};
	Map(TEXT("tactical"), View ? View->ReloadTactical : 2.0, ReloadTactical);
	Map(TEXT("empty"), View ? View->ReloadEmpty : 2.5, ReloadEmpty);
	Mode = EMIFPMode::Pack;
	UE_LOG(LogMI, Log, TEXT("First person: %s drawn with the pack's clips (%d arm clips, %d gun clips, optic %d, grip %s)"),
		*Gun.ToString(), Clips.Arms.Num(), Clips.Gun.Num(), bOptic ? 1 : 0, *GripVariant.ToString());
	return Mode;
}

double UMIFirstPersonRig::WarpReload(const FReloadMap& Map, double RuleT) const
{
	if (Map.Keys.Num() < 2)
	{
		return RuleT;
	}
	for (int32 I = 1; I < Map.Keys.Num(); ++I)
	{
		const FVector2D& A = Map.Keys[I - 1];
		const FVector2D& B = Map.Keys[I];
		if (RuleT <= B.X || I == Map.Keys.Num() - 1)
		{
			const double K = FMath::Clamp((RuleT - A.X) / FMath::Max(1e-6, B.X - A.X), 0.0, 1.0);
			return A.Y + (B.Y - A.Y) * K;
		}
	}
	return Map.Keys.Last().Y;
}

void UMIFirstPersonRig::OnFire(double Ads)
{
	FireAge = 0.0;
	bFireAimed = Ads > 0.5;
	Presented = NAME_None;
	IdleFor = 0.0;
}

void UMIFirstPersonRig::RequestInspect(int32 Mag, int32 MagSize)
{
	if (Mode == EMIFPMode::Pack && Presented.IsNone())
	{
		Presented = Mag < MagSize && ArmsClip(TEXT("magCheck")) ? FName(TEXT("magCheck")) : FName(TEXT("inspect"));
		PresentedT = 0.0;
	}
}

double UMIFirstPersonRig::FirstPersonFovV(double Hip, double Ads) const
{
	const double To = bOptic ? FovOptic : FovIrons;
	return Hip + (To - Hip) * FMath::Clamp(Ads, 0.0, 1.0);
}

FTransform UMIFirstPersonRig::CameraSpace(const FTransform& World) const
{
	return Camera ? World.GetRelativeTransform(Camera->GetComponentTransform()) : World;
}

bool UMIFirstPersonRig::MuzzleInCamera(FVector& OutPos, FVector& OutDir) const
{
	if (Mode != EMIFPMode::Pack || !PackGun || !PackGun->GetSkinnedAsset())
	{
		return false;
	}
	// A fitted muzzle device's own Muzzle socket wins (the silencer's end).
	FTransform T = PackGun->GetSocketTransform(TEXT("Muzzle"));
	TArray<USceneComponent*> Children;
	PackGun->GetChildrenComponents(false, Children);
	for (USceneComponent* C : Children)
	{
		if (const UStaticMeshComponent* S = Cast<UStaticMeshComponent>(C); S && S->DoesSocketExist(TEXT("Muzzle")))
		{
			T = S->GetSocketTransform(TEXT("Muzzle"));
		}
	}
	const FTransform CS = CameraSpace(T);
	OutPos = CS.GetLocation();
	// Gun space +Y is the muzzle direction on the pack's sockets (identity in gun space, ANIMATION.md 8.3).
	OutDir = CameraSpace(PackGun->GetComponentTransform()).GetRotation().RotateVector(FVector(0, 1, 0));
	return true;
}

bool UMIFirstPersonRig::EjectInCamera(FTransform& Out) const
{
	if (Mode != EMIFPMode::Pack || !PackGun || !PackGun->DoesSocketExist(TEXT("Eject")))
	{
		return false;
	}
	Out = CameraSpace(PackGun->GetSocketTransform(TEXT("Eject")));
	return true;
}

bool UMIFirstPersonRig::HandSocket(FName Socket, FTransform& Out) const
{
	if (!Arms || Socket.IsNone())
	{
		return false;
	}
	if (Arms->DoesSocketExist(Socket))
	{
		Out = Arms->GetSocketTransform(Socket, RTS_Component);
		return true;
	}
	// SK_RuleArms carries no HandGrip_R: the template body's socket (same skeleton) on the same bone.
	const USkeletalMeshSocket* S = TemplateBody ? TemplateBody->FindSocket(Socket) : nullptr;
	if (!S || Arms->GetBoneIndex(S->BoneName) == INDEX_NONE)
	{
		return false;
	}
	Out = S->GetSocketLocalTransform() * Arms->GetBoneTransform(Arms->GetBoneIndex(S->BoneName), FTransform::Identity);
	return true;
}

void UMIFirstPersonRig::SetVisible(bool bGun, bool bArms)
{
	if (PackGun)
	{
		PackGun->SetVisibility(bGun && Mode == EMIFPMode::Pack, true);
		if (bGun && Mode == EMIFPMode::Pack && ReserveMag)
		{
			ReserveMag->SetVisibility(false);  // UpdateMagazines shows it when in hand
		}
	}
	for (UStaticMeshComponent* J : Jewels)
	{
		if (J) J->SetVisibility(bArms && Mode != EMIFPMode::Template);
	}
}

bool UMIFirstPersonRig::IsPackGunVisible() const
{
	return PackGun && PackGun->IsVisible();
}

void UMIFirstPersonRig::Update(double Dt, const FMIWeaponView& W, const FMIViewmodelRig& Rig, const FMIViewmodelPlayer& P, double ViewYawDeg)
{
	using namespace MIFirstPersonRigPrivate;
	UMIFPAnimInstance* AI = Arms ? Cast<UMIFPAnimInstance>(Arms->GetAnimInstance()) : nullptr;
	Clock += Dt;
	FireAge += Dt;
	JumpAge += Dt;
	LandAge += Dt;
	if (Mode == EMIFPMode::HandIK)
	{
		HandPose.Layers.Reset();
		if (UAnimSequenceBase* Idle = ArmsClip(TEXT("idle")))
		{
			HandPose.Layers.Add({Idle, static_cast<float>(FMath::Fmod(Clock, FMath::Max(0.1, (double)Idle->GetPlayLength()))), 1.f, false, 0.f});
		}
		if (UAnimSequenceBase* Fire = ArmsClip(TEXT("fire")); Fire && FireAge < Fire->GetPlayLength())
		{
			HandPose.Layers.Add({Fire, static_cast<float>(FireAge), static_cast<float>(FireWeight), true, 0.f});
		}
		return;  // the hands come in UpdateHands, after the arms are placed on the grip
	}
	if (Mode != EMIFPMode::Pack || !AI || !PackGun)
	{
		return;
	}
	FMIFPPose ArmsPose, GunPose;
	BuildPack(Dt, W, P, ViewYawDeg, ArmsPose, GunPose);
	AI->SetPose(ArmsPose);
	if (UMIFPAnimInstance* GI = Cast<UMIFPAnimInstance>(PackGun->GetAnimInstance()))
	{
		GI->SetPose(GunPose);
	}
	// The arms on the camera by the recipe, the rig's procedural motion on top; with an optic the eye moves onto
	// the optic's axis as the gun comes up (ANIMATION.md 9: minus the sight point's offset from SightRear).
	FTransform T = ArmsRest * Rig.GetLayerTransform();
	if (bOptic && W.Ads > 0.0 && PackGun->DoesSocketExist(TEXT("SightRear")))
	{
		TArray<USceneComponent*> Children;
		PackGun->GetChildrenComponents(false, Children);
		for (USceneComponent* C : Children)
		{
			const UStaticMeshComponent* S = Cast<UStaticMeshComponent>(C);
			if (S && S->DoesSocketExist(TEXT("SightEye")))
			{
				const FTransform G = PackGun->GetComponentTransform();
				FVector D = G.InverseTransformVector(S->GetSocketLocation(TEXT("SightEye")) - PackGun->GetSocketLocation(TEXT("SightRear")));
				D.Y = 0.0;  // along the bore it does not matter: across it, it does
				T.AddToTranslation(-CameraSpace(G).GetRotation().RotateVector(D) * Smooth(W.Ads));
				break;
			}
		}
	}
	Arms->SetRelativeTransform(T);
}

void UMIFirstPersonRig::BuildPack(double Dt, const FMIWeaponView& W, const FMIViewmodelPlayer& P, double ViewYawDeg, FMIFPPose& Out, FMIFPPose& Gun)
{
	using namespace MIFirstPersonRigPrivate;
	const auto Len = [](const UAnimSequenceBase* C) { return C ? static_cast<double>(C->GetPlayLength()) : 0.0; };
	const auto Loop = [&Len](const UAnimSequenceBase* C, double T) { const double L = Len(C); return L > 0.0 ? FMath::Fmod(T, L) : 0.0; };

	// --- locomotion: idle, crouch, walk by direction, sprint, airborne
	const double Speed = P.Speed;
	Walk = Damp(Walk, P.bOnGround ? FMath::Clamp(Speed / WalkSpeed, 0.0, 1.0) : 0.0, 10.0, Dt);
	Crouch = Damp(Crouch, P.bCrouching ? 1.0 : 0.0, 10.0, Dt);
	Air = Damp(Air, P.bOnGround ? 0.0 : 1.0, 8.0, Dt);
	LocoPhase += Dt * FMath::Max(0.75, Speed / WalkSpeed);
	const double Yaw = FMath::DegreesToRadians(ViewYawDeg);
	const FVector2D Fwd(FMath::Cos(Yaw), FMath::Sin(Yaw)), Right(-FMath::Sin(Yaw), FMath::Cos(Yaw));
	const FVector2D V(P.Velocity.X, P.Velocity.Y);
	const double VF = V.Dot(Fwd), VR = V.Dot(Right), VN = FMath::Max(1.0, V.Size());
	TArray<TPair<FName, double>> Group;
	const double Sprint = FMath::Clamp(W.SprintBlend, 0.0, 1.0);
	const double Moving = Walk * (1.0 - Sprint);
	Group.Add({Crouch > 0.5 && ArmsClip(TEXT("crouch")) ? FName(TEXT("crouch")) : FName(TEXT("idle")), 1.0 - Walk});
	Group.Add({TEXT("walkF"), Moving * FMath::Max(0.0, VF / VN)});
	Group.Add({TEXT("walkB"), Moving * FMath::Max(0.0, -VF / VN)});
	Group.Add({TEXT("walkR"), Moving * FMath::Max(0.0, VR / VN)});
	Group.Add({TEXT("walkL"), Moving * FMath::Max(0.0, -VR / VN)});
	Group.Add({TEXT("sprint"), Walk * Sprint});
	double Sum = 0.0;
	for (const TPair<FName, double>& G : Group)
	{
		UAnimSequenceBase* C = ArmsClip(G.Key);
		if (!C || G.Value <= 0.0) continue;
		Sum += G.Value;
		const double T = G.Key == TEXT("idle") || G.Key == TEXT("crouch") ? Loop(C, Clock) : Loop(C, LocoPhase);
		Out.Layers.Add({C, static_cast<float>(T), static_cast<float>(Out.Layers.Num() == 0 ? 1.0 : G.Value / Sum), false, 0.f});
	}
	if (UAnimSequenceBase* C = ArmsClip(TEXT("fall")); C && Air > 0.01)
	{
		Out.Layers.Add({C, static_cast<float>(Loop(C, Clock)), static_cast<float>(Air * 0.8), false, 0.f});
	}
	if (UAnimSequenceBase* C = ArmsClip(TEXT("jumpStart")); C && JumpAge < Len(C))
	{
		Out.Layers.Add({C, static_cast<float>(JumpAge), static_cast<float>(0.7 * (1.0 - JumpAge / Len(C))), false, 0.f});
	}
	if (UAnimSequenceBase* C = ArmsClip(TEXT("jumpEnd")); C && LandAge < Len(C))
	{
		Out.Layers.Add({C, static_cast<float>(LandAge), static_cast<float>(0.8 * LandWeight * (1.0 - LandAge / Len(C))), false, 0.f});
	}
	// --- aim: the aimed pose by Ads (the pack's own aim transitions are far slower than the rules' aim time)
	FName AimRole = TEXT("aim");
	if (GripVariant == TEXT("grip_vertical") && ArmsClip(TEXT("aimGripVertical"))) AimRole = TEXT("aimGripVertical");
	if (GripVariant == TEXT("grip_angled") && ArmsClip(TEXT("aimGripAngled"))) AimRole = TEXT("aimGripAngled");
	if (UAnimSequenceBase* C = ArmsClip(AimRole); C && W.Ads > 0.001)
	{
		Out.Layers.Add({C, 0.f, static_cast<float>(Smooth(W.Ads)), false, 0.f});
	}

	// --- actions: the rules' activities, then the presentation-only inspect and magazine check
	FName Now = NAME_None;
	double NowT = 0.0;
	const double K = W.ActivityLength > 0.0 ? FMath::Clamp(W.ActivityTime / W.ActivityLength, 0.0, 1.0) : 0.0;
	const FReloadMap* Map = nullptr;
	switch (W.Activity)
	{
	case EMIWeaponActivity::Reloading:
		Map = W.bReloadEmpty ? &ReloadEmpty : &ReloadTactical;
		Now = W.bReloadEmpty ? FName(TEXT("reloadEmpty")) : FName(TEXT("reloadTactical"));
		NowT = WarpReload(*Map, W.ActivityTime);
		break;
	case EMIWeaponActivity::Holstering: Now = TEXT("holster"); NowT = K * Len(ArmsClip(Now)); break;
	case EMIWeaponActivity::Drawing: Now = TEXT("draw"); NowT = K * FMath::Min(DrawRange, Len(ArmsClip(Now))); break;
	case EMIWeaponActivity::Striking: Now = TEXT("melee"); NowT = K * FMath::Min(MeleeRange, Len(ArmsClip(Now))); break;
	case EMIWeaponActivity::Selector: Now = TEXT("modeSwitch"); NowT = W.ActivityTime; break;
	default: break;
	}
	// Inspect: on the key, or as the idle flourish after inspectAfter seconds of calm (spec 02 2.14); any action,
	// aiming, sprinting or a shot ends it.
	const bool bCalm = W.Activity == EMIWeaponActivity::Ready && W.Ads < 0.05 && Sprint < 0.2 && W.SinceShot > 0.25 && Speed < 60.0;
	IdleFor = bCalm ? IdleFor + Dt : 0.0;
	if (!Presented.IsNone())
	{
		PresentedT += Dt;
		if (!bCalm && !(W.Activity == EMIWeaponActivity::Ready && W.Ads < 0.05 && W.SinceShot > 0.25)) Presented = NAME_None;
		else if (PresentedT >= Len(ArmsClip(Presented))) Presented = NAME_None;
	}
	else if (InspectAfter > 0.0 && IdleFor > InspectAfter && ArmsClip(TEXT("inspect")))
	{
		Presented = TEXT("inspect");
		PresentedT = 0.0;
		IdleFor = -1e9;  // once per calm spell
	}
	if (Now.IsNone() && !Presented.IsNone())
	{
		Now = Presented;
		NowT = PresentedT;
	}
	if (!Now.IsNone() && !ArmsClip(Now))
	{
		Now = NAME_None;
	}
	if (!Now.IsNone())
	{
		ActionWeight = FMath::Min(1.0, ActionWeight + Dt / 0.08);
		LastAction = Now;
		LastActionT = NowT;
	}
	else
	{
		ActionWeight = FMath::Max(0.0, ActionWeight - Dt / 0.18);
	}
	Action = Now;
	if (!LastAction.IsNone() && ActionWeight > 0.0)
	{
		Out.Layers.Add({ArmsClip(LastAction), static_cast<float>(LastActionT), static_cast<float>(Smooth(ActionWeight)), false, 0.f});
	}
	// --- fire: the pack's own recoil motion per round, added on top
	if (UAnimSequenceBase* C = ArmsClip(bFireAimed && ArmsClip(TEXT("fireAimed")) ? FName(TEXT("fireAimed")) : FName(TEXT("fire"))); C && FireAge < Len(C))
	{
		Out.Layers.Add({C, static_cast<float>(FireAge), static_cast<float>(FireWeight * (1.0 - ActionWeight)), true, 0.f});
	}

	// --- the gun: its reference pose, the reload / inspect / check clip at the same time, the bolt per round
	if (UAnimSequenceBase* C = GunClip(TEXT("base")))
	{
		Gun.Layers.Add({C, 0.f, 1.f, false, 0.f});
	}
	if (!Now.IsNone() && GunClip(Now))
	{
		Gun.Layers.Add({GunClip(Now), static_cast<float>(NowT), 1.f, false, 0.f});
	}
	else if (UAnimSequenceBase* C = GunClip(TEXT("fire")); C && FireAge * FireRate < Len(C) && W.Activity == EMIWeaponActivity::Ready)
	{
		Gun.Layers.Add({C, static_cast<float>(FireAge * FireRate), 1.f, false, 0.f});
	}
	UpdateMagazines(W, NowT, Map);
}

void UMIFirstPersonRig::UpdateMagazines(const FMIWeaponView& W, double ClipT, const FReloadMap* Map)
{
	UStaticMeshComponent* Seated = SeatedMag.Get();
	const bool bReloading = W.Activity == EMIWeaponActivity::Reloading && Map;
	// The old magazine's bone velocity (camera space), for the one that drops.
	if (Seated)
	{
		const FVector Now = CameraSpace(Seated->GetComponentTransform()).GetLocation();
		MagVel = (Now - MagPrev) / FMath::Max(1e-3, GetWorld() ? GetWorld()->GetDeltaSeconds() : 1.0 / 60.0);
		MagPrev = Now;
	}
	if (!bReloading)
	{
		// Outside a reload (or when it ends or is cancelled) the magazine on the seat is the one in the gun.
		if (Seated && PackGun && PackGun->IsVisible()) Seated->SetVisibility(true);
		if (ReserveMag) ReserveMag->SetVisibility(false);
		bWasReloading = false;
		bDropped = false;
		return;
	}
	if (!bWasReloading)
	{
		bWasReloading = true;
		bDropped = false;
	}
	const bool bOldShown = Map->bDrop ? ClipT < Map->Out : true;
	if (Map->bDrop && !bOldShown && !bDropped)
	{
		bDropped = true;
		DropMagazine(Map->bDropFull);
	}
	if (Seated) Seated->SetVisibility(bOldShown);
	if (ReserveMag) ReserveMag->SetVisibility(ClipT >= Map->Reserve);
}

void UMIFirstPersonRig::DropMagazine(bool bFull)
{
	UStaticMeshComponent* Seated = SeatedMag.Get();
	UWorld* World = GetWorld();
	UStaticMesh* Mesh = MagFull.Get();
	if (bFull && Seated && Seated->GetStaticMesh())
	{
		Mesh = Seated->GetStaticMesh();
	}
	else if (!bFull && MagEmpty)
	{
		Mesh = MagEmpty.Get();
	}
	if (!World || !Seated || !Mesh || !Weapon || !Camera)
	{
		return;
	}
	// Where the magazine appears on screen, as a world body (the first-person view is drawn with its own field of view).
	const FTransform CS = CameraSpace(Seated->GetComponentTransform());
	const FVector Pos = Weapon->FirstPersonToWorld(CS.GetLocation());
	const FQuat Rot = Camera->GetComponentQuat() * CS.GetRotation();
	const FVector Vel = Camera->GetComponentQuat().RotateVector(MagVel) + FVector(0, 0, -60.0);
	UMIEffects::SpawnBody(this, Mesh, FTransform(Rot, Pos), Vel, FVector(FMath::FRandRange(-200.0, 200.0), FMath::FRandRange(-300.0, 300.0), 0.0), 8.0);
}

void UMIFirstPersonRig::UpdateHands(const USkinnedMeshComponent* Gun)
{
	if (Mode != EMIFPMode::HandIK || !Arms || !Gun)
	{
		return;
	}
	UMIFPAnimInstance* AI = Cast<UMIFPAnimInstance>(Arms->GetAnimInstance());
	if (!AI)
	{
		return;
	}
	HandPose.Hands.Reset();
	const FTransform ArmsWorld = Arms->GetComponentTransform();
	const auto Pull = [&](FName Socket, const TCHAR* U, const TCHAR* L, const TCHAR* H, const TCHAR* Palm)
	{
		if (Socket.IsNone() || !Gun->DoesSocketExist(Socket))
		{
			return;
		}
		FMIFPHandIK& IK = HandPose.Hands.AddDefaulted_GetRef();
		IK.Upper = U;
		IK.Lower = L;
		IK.Hand = H;
		IK.Palm = Palm;
		IK.Target = Gun->GetSocketTransform(Socket).GetRelativeTransform(ArmsWorld);
		IK.Weight = 1.f;
		IK.bRotation = false;  // the template clip's hand shape and wrist stay; only the palm moves onto the gun
	};
	Pull(LeftSocket, TEXT("upperarm_l"), TEXT("lowerarm_l"), TEXT("hand_l"), TEXT("middle_metacarpal_l"));
	Pull(RightSocket, TEXT("upperarm_r"), TEXT("lowerarm_r"), TEXT("hand_r"), TEXT("middle_metacarpal_r"));
	AI->SetPose(HandPose);
}
