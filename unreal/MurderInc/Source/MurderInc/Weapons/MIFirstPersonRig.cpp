#include "Weapons/MIFirstPersonRig.h"

#include "HAL/IConsoleManager.h"

#include "Animation/AnimSequenceBase.h"
#include "AnimationRuntime.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Core/Data/MIDataSubsystem.h"
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
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/Material.h"
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

FTransform UMIFirstPersonRig::MeshSpacePartOnBone(const USkeletalMesh* Mesh, FName Bone)
{
	const int32 Index = Mesh ? Mesh->GetRefSkeleton().FindBoneIndex(Bone) : INDEX_NONE;
	if (Index == INDEX_NONE)
	{
		return FTransform::Identity;
	}
	const FTransform BoneCS = FAnimationRuntime::GetComponentSpaceTransformRefPose(Mesh->GetRefSkeleton(), Index);
	return FTransform::Identity.GetRelativeTransform(BoneCS);
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
	IronZero = FQuat::Identity;
	IronZeroDeg = 0.0;
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
	// The gun's own finger corrections (polish pass: solved in play with MIGripProbe so the fingers touch this gun).
	for (int32 CurlSide = 0; CurlSide < 2; ++CurlSide)
	{
		CurlHip[CurlSide].Reset();
		CurlAim[CurlSide].Reset();
		for (int32 CurlPose = 0; CurlPose < 2; ++CurlPose)
		{
			const TSharedPtr<FJsonObject> CurlObj = Obj(P, FString::Printf(TEXT("fingers.%s.%s"), CurlPose == 0 ? TEXT("hip") : TEXT("aim"), CurlSide == 0 ? TEXT("l") : TEXT("r")));
			if (!CurlObj.IsValid()) continue;
			for (const auto& CurlKV : CurlObj->Values)
			{
				double CurlDeg = 0.0;
				if (CurlKV.Value.IsValid() && CurlKV.Value->TryGetNumber(CurlDeg)) (CurlPose == 0 ? CurlHip[CurlSide] : CurlAim[CurlSide]).Add(FName(FString(*CurlKV.Key)), static_cast<float>(CurlDeg));
			}
		}
	}
	SupportElbowDrop = FVector::ZeroVector;
	if (const TSharedPtr<FJsonValue> E = MIJson::Get(Set, TEXT("supportElbowDrop")); E.IsValid() && E->Type == EJson::Array && E->AsArray().Num() == 3)
	{
		SupportElbowDrop = FVector(E->AsArray()[0]->AsNumber(), E->AsArray()[1]->AsNumber(), E->AsArray()[2]->AsNumber());
	}
	bShoulderAnchor = false;
	if (const TSharedPtr<FJsonValue> E = MIJson::Get(Set, TEXT("shoulders")); E.IsValid() && E->Type == EJson::Array && E->AsArray().Num() == 3)
	{
		ShoulderAnchor = FVector(E->AsArray()[0]->AsNumber(), E->AsArray()[1]->AsNumber(), E->AsArray()[2]->AsNumber());
		bShoulderAnchor = true;
	}
	DrawRange = Num(Set, TEXT("drawRange"), 0.53);
	MeleeRange = Num(Set, TEXT("meleeRange"), 1.0);
	InspectAfter = Resolved ? Resolved->Def.InspectAfter : 24.0;
	CasingMesh = LoadAs<UStaticMesh>(MIJson::StringOr(Set, TEXT("casing")));

	CurlClip = nullptr;
	if (Kind == TEXT("ik"))
	{
		// Optional finger curl (another clip on the same skeleton; absent in a clean checkout: no curl, no fallback).
		if (UAnimSequenceBase* C = LoadAs<UAnimSequenceBase>(MIJson::StringOr(Set, TEXT("fingerCurl.clip"))); C && C->GetSkeleton() == ArmsMesh->GetSkeleton())
		{
			CurlClip = C;
			CurlBranch = FName(*MIJson::StringOr(Set, TEXT("fingerCurl.branch"), TEXT("hand_l")));
			CurlTime = MIJson::NumberOr(Set, TEXT("fingerCurl.time"), 0.0);
			CurlWeight = MIJson::NumberOr(Set, TEXT("fingerCurl.weight"), 1.0);
			Loaded.Add(C);
		}
		LeftSocket = FName(*MIJson::StringOr(Set, TEXT("ik.left")));
		RightSocket = FName(*MIJson::StringOr(Set, TEXT("ik.right")));
		// The solved grip (Content/Data/grips.json, written by art/blender/assets/_rule_grips.py): both hands' joint
		// points in the gun's space. Hands-and-tattoos second pass: the template pistol idle alone rested the NINE on a
		// flat support hand with the firing fingers straight under the frame.
		GripPoints[0].Reset();
		GripPoints[1].Reset();
		GripWeight = MIJson::NumberOr(Set, TEXT("grip.weight"), 1.0);
		const FString GripKey = MIJson::StringOr(Set, TEXT("grip.gun"));
		TSharedPtr<FJsonObject> Grips;
		FString GripError;
		if (!GripKey.IsEmpty() && UMIDataSubsystem::LoadJsonFile(TEXT("grips.json"), Grips, GripError))
		{
			const FString Pose = MIJson::StringOr(Set, TEXT("grip.pose"), TEXT("hip"));
			for (int32 S = 0; S < 2; ++S)
			{
				const TSharedPtr<FJsonObject> Pts = Obj(Grips, FString::Printf(TEXT("guns.%s.%s.%s"), *GripKey, *Pose, S == 0 ? TEXT("l") : TEXT("r")));
				if (!Pts)
				{
					continue;
				}
				const TCHAR* Side = S == 0 ? TEXT("_l") : TEXT("_r");
				TArray<FString> Names = {FString(TEXT("hand")) + Side};
				for (const TCHAR* F : {TEXT("thumb"), TEXT("index"), TEXT("middle"), TEXT("ring"), TEXT("pinky")})
				{
					Names.Add(FString::Printf(TEXT("%s_metacarpal%s"), F, Side));
					for (int32 K = 1; K <= 3; ++K)
					{
						Names.Add(FString::Printf(TEXT("%s_%02d%s"), F, K, Side));
					}
					Names.Add(FString::Printf(TEXT("%s_tip%s"), F, Side));
				}
				for (const FString& N : Names)
				{
					const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
					if (Pts->TryGetArrayField(N, A) && A->Num() == 3)
					{
						GripPoints[S].Add(FName(*N), FVector((*A)[0]->AsNumber(), (*A)[1]->AsNumber(), (*A)[2]->AsNumber()));
					}
				}
			}
			UE_LOG(LogTemp, Log, TEXT("First person: grip %s/%s, %d + %d points"), *GripKey, *Pose, GripPoints[0].Num(), GripPoints[1].Num());
		}
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
			// The magazine is modelled in the pistol's own space (origin = pistol origin), not the bone's: undo the
			// bone's reference pose so it sits in the grip and rides the bone's drop.
			OwnMag->SetRelativeTransform(MeshSpacePartOnBone(Cast<USkeletalMesh>(LegacyGun->GetSkinnedAsset()), MagBone));
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
	// The optics in daylight (review 2026-11-23: no reticle visible at 32 degrees, the glass tinted dark grey):
	// presentation firstPerson.opticMaterials, base material name -> scalar parameters, set on dynamic instances.
	if (const TSharedPtr<FJsonObject> OM = Obj(Root, TEXT("firstPerson.opticMaterials")))
	{
		TArray<USceneComponent*> Parts;
		PackGun->GetChildrenComponents(true, Parts);
		for (USceneComponent* SC : Parts)
		{
			UPrimitiveComponent* PC = Cast<UPrimitiveComponent>(SC);
			for (int32 I = 0; PC && I < PC->GetNumMaterials(); ++I)
			{
				UMaterialInterface* M = PC->GetMaterial(I);
				const UMaterial* Base = M ? M->GetBaseMaterial() : nullptr;
				const TSharedPtr<FJsonObject> Params = Base ? Obj(OM, Base->GetName()) : nullptr;
				if (!Params.IsValid())
				{
					continue;
				}
				UMaterialInstanceDynamic* D = Cast<UMaterialInstanceDynamic>(M);
				if (!D)
				{
					D = UMaterialInstanceDynamic::Create(M, PC);
					PC->SetMaterial(I, D);
				}
				for (const auto& Pair : Params->Values)
				{
					double V = 0.0;
					if (Pair.Value->TryGetNumber(V))
					{
						D->SetScalarParameterValue(FName(FString(*Pair.Key)), static_cast<float>(V));
					}
				}
			}
		}
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
		Out.bStow = R->TryGetBoolField(TEXT("stow"), bB) && bB;
		if (Out.bStow) Out.bDrop = false;
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
	// The arms' own socket (SK_RuleArms carries HandGrip_R since its re-import), else the template body's socket
	// (same skeleton) on the same bone.
	const USkeletalMesh* ArmsAsset = Cast<USkeletalMesh>(Arms->GetSkinnedAsset());
	const USkeletalMeshSocket* S = ArmsAsset ? ArmsAsset->FindSocket(Socket) : nullptr;
	if (!S && TemplateBody)
	{
		S = TemplateBody->FindSocket(Socket);
	}
	if (!S && Arms->DoesSocketExist(Socket))
	{
		Out = Arms->GetSocketTransform(Socket, RTS_Component);
		return true;
	}
	if (!S || Arms->GetBoneIndex(S->BoneName) == INDEX_NONE)
	{
		return false;
	}
	// HandIK guns: the hand as the clips posed it, before the IK and the solved grip; the posed bone would feed the
	// grip's turn of the hand back into the arms' placement every frame (second pass: the NINE's forearm swung up in
	// front of the eye)
	FTransform Bone = Arms->GetBoneTransform(Arms->GetBoneIndex(S->BoneName), FTransform::Identity);
	if (Mode == EMIFPMode::HandIK)
	{
		if (const UMIFPAnimInstance* AI = Cast<UMIFPAnimInstance>(Arms->GetAnimInstance()))
		{
			AI->GetPreIKHand(S->BoneName, Bone);
		}
	}
	Out = S->GetSocketLocalTransform() * Bone;
	return true;
}

bool UMIFirstPersonRig::GripWristSlide(const FTransform& GunRel, const FTransform& ArmsRel, FVector& Out) const
{
	const FVector* Wrist = GripPoints[1].Find(TEXT("hand_r"));
	const UMIFPAnimInstance* AI = Arms ? Cast<UMIFPAnimInstance>(Arms->GetAnimInstance()) : nullptr;
	FTransform Hand;
	if (Mode != EMIFPMode::HandIK || !Wrist || GripWeight <= 0.0 || !AI || !AI->GetPreIKHand(TEXT("hand_r"), Hand))
	{
		return false;
	}
	Out = (GunRel.TransformPosition(*Wrist) - ArmsRel.TransformPosition(Hand.GetLocation())) * GripWeight;
	return true;
}

namespace MIFirstPersonRigPrivate
{
	static TAutoConsoleVariable<FString> CVarShoulders(TEXT("mi.FP.Shoulders"), TEXT(""),
		TEXT("HandIK guns with a solved grip: the arms' shoulders (midpoint of upperarm_l / _r) in camera space, \"x y z\" cm; ")
		TEXT("empty or \"data\": the anim set's 'shoulders'; 'off': the wrist slide"));
}

bool UMIFirstPersonRig::GripShoulderTranslation(const FTransform& ArmsRel, FVector& Out) const
{
	if (Mode != EMIFPMode::HandIK || GripPoints[1].IsEmpty() || GripWeight <= 0.0 || !Arms || !Arms->GetSkinnedAsset())
	{
		return false;
	}
	const FString C = MIFirstPersonRigPrivate::CVarShoulders.GetValueOnGameThread().TrimStartAndEnd();
	FVector Anchor = ShoulderAnchor;
	if (C == TEXT("off") || ((C.IsEmpty() || C == TEXT("data")) && !bShoulderAnchor))
	{
		return false;
	}
	if (!C.IsEmpty() && C != TEXT("data"))
	{
		TArray<FString> P;
		C.ParseIntoArrayWS(P);
		if (P.Num() != 3)
		{
			return false;
		}
		Anchor = FVector(FCString::Atod(*P[0]), FCString::Atod(*P[1]), FCString::Atod(*P[2]));
	}
	if (Arms->GetBoneIndex(TEXT("upperarm_l")) == INDEX_NONE || Arms->GetBoneIndex(TEXT("upperarm_r")) == INDEX_NONE)
	{
		return false;
	}
	const FVector Mid = (Arms->GetBoneLocation(TEXT("upperarm_l"), EBoneSpaces::ComponentSpace) + Arms->GetBoneLocation(TEXT("upperarm_r"), EBoneSpaces::ComponentSpace)) * 0.5;
	Out = FMath::Lerp(ArmsRel.GetTranslation(), Anchor - ArmsRel.TransformVector(Mid), GripWeight);
	return true;
}

bool UMIFirstPersonRig::ShouldersInCamera(FVector& Out) const
{
	if (!Arms || !Camera || !Arms->GetSkinnedAsset() || Arms->GetBoneIndex(TEXT("upperarm_l")) == INDEX_NONE)
	{
		return false;
	}
	const FVector Mid = (Arms->GetBoneLocation(TEXT("upperarm_l")) + Arms->GetBoneLocation(TEXT("upperarm_r"))) * 0.5;
	Out = Camera->GetComponentTransform().InverseTransformPosition(Mid);
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
		bReloadingNow = W.Activity == EMIWeaponActivity::Reloading;
		ReloadNowT = W.ActivityTime;
		ReloadNowLeft = FMath::Max(0.0, W.ActivityLength - W.ActivityTime);
		HandPose.Layers.Reset();
		if (UAnimSequenceBase* Idle = ArmsClip(TEXT("idle")))
		{
			HandPose.Layers.Add({Idle, static_cast<float>(FMath::Fmod(Clock, FMath::Max(0.1, (double)Idle->GetPlayLength()))), 1.f, false, 0.f});
		}
		if (UAnimSequenceBase* Fire = ArmsClip(TEXT("fire")); Fire && FireAge < Fire->GetPlayLength())
		{
			HandPose.Layers.Add({Fire, static_cast<float>(FireAge), static_cast<float>(FireWeight), true, 0.f});
		}
		// The support hand's fingers curled round the firing hand (a wrapping grip from another clip, fingers only).
		if (CurlClip)
		{
			FMIFPLayer& Curl = HandPose.Layers.AddDefaulted_GetRef();
			Curl.Clip = CurlClip;
			Curl.Time = static_cast<float>(CurlTime);
			Curl.Weight = static_cast<float>(CurlWeight);
			Curl.Branch = CurlBranch;
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
	// Irons zeroed to the aim point (review 2026-11-23: the front post sat about 1.3 degrees under the screen centre):
	// on the clip's own pose (the rig's layers taken off), the front sight's direction from the eye is turned onto
	// the camera axis about the eye, by smoothstep(Ads). Recoil, sway and the aim arc stay on top.
	// The turn is measured once the gun is fully up (Ads > 0.95) and kept per gun, so it never pops mid-blend.
	if (!bOptic && W.Ads > 0.95 && PackGun->DoesSocketExist(TEXT("SightFront")))
	{
		const FTransform GunInArms = CameraSpace(PackGun->GetComponentTransform()) * Arms->GetRelativeTransform().Inverse();
		const FVector Front = (PackGun->GetSocketTransform(TEXT("SightFront"), RTS_Component) * GunInArms * ArmsRest).GetLocation();
		const FVector D = Front.GetSafeNormal();
		const double Off = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(D.X, -1.0, 1.0)));
		if (D.X > 0.0 && Off < 4.0)
		{
			IronZeroDeg = Off;
			IronZero = FQuat::Slerp(IronZero, FQuat::FindBetweenNormals(D, FVector::ForwardVector), FMath::Min(1.0, 20.0 * Dt)).GetNormalized();
		}
	}
	const FTransform Zero(bOptic ? FQuat::Identity : FQuat::Slerp(FQuat::Identity, IronZero, Smooth(W.Ads)));
	FTransform T = ArmsRest * Zero * Rig.GetLayerTransform();
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
	// --- aimed, the support elbow drops (the hand stays on the handguard): the forearm leaves the sight picture
	// instead of lying across a quarter of the screen (review 2026-11-23; presentation animSets.rifle.supportElbowDrop)
	if (!SupportElbowDrop.IsNearlyZero() && W.Ads > 0.0)
	{
		FMIFPHandIK& IK = Out.Hands.AddDefaulted_GetRef();
		IK.Upper = TEXT("upperarm_l");
		IK.Lower = TEXT("lowerarm_l");
		IK.Hand = TEXT("hand_l");
		IK.bKeepHand = true;
		IK.PoleShift = SupportElbowDrop;
		IK.Weight = static_cast<float>(Smooth(W.Ads) * (1.0 - ActionWeight));
	}

	// --- the gun's own finger corrections (hip to aim by smoothstep(Ads)), let go in actions and the sprint
	{
		const float AimK = static_cast<float>(Smooth(W.Ads));
		const float CurlW = static_cast<float>((1.0 - ActionWeight) * (1.0 - Sprint));
		for (int32 Side = 0; Side < 2 && CurlW > 0.001f; ++Side)
		{
			TSet<FName> Names;
			for (const auto& KV : CurlHip[Side]) Names.Add(KV.Key);
			for (const auto& KV : CurlAim[Side]) Names.Add(KV.Key);
			for (const FName& Finger : Names)
			{
				const float* HipDeg = CurlHip[Side].Find(Finger);
				const float* AimDeg = CurlAim[Side].Find(Finger);
				const float Hip = HipDeg ? *HipDeg : 0.f, Aim = AimDeg ? *AimDeg : Hip;
				Out.Curls.Add({Finger, Side == 0, (Hip + (Aim - Hip) * AimK) * CurlW});
			}
		}
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
	// Dropped or stowed, the old magazine leaves the seat at 'out' (stowed: kept, so no body is thrown away).
	const bool bOldShown = Map->bDrop || Map->bStow ? ClipT < Map->Out : true;
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
	// Drawn at the first-person depth and size, so the falling magazine is seen leaving the well (review 2026-11-23).
	const FTransform At = Weapon->FirstPersonToNearWorld(CameraSpace(Seated->GetComponentTransform()));
	const FVector Pos = At.GetLocation();
	const FVector Vel = Camera->GetComponentQuat().RotateVector(MagVel) * At.GetScale3D().X + FVector(0, 0, -60.0);
	// First-person size while it leaves the hands, then the magazine at its true size where it really falls (fix pass:
	// the first-person one lay shrunken on the ground for 8 s).
	const FTransform Seat = CameraSpace(Seated->GetComponentTransform());
	const FTransform Real(Camera->GetComponentQuat() * Seat.GetRotation(), Weapon->FirstPersonToWorld(Seat.GetLocation()), Seat.GetScale3D());
	const FVector RealVel = Camera->GetComponentQuat().RotateVector(MagVel) + FVector(0, 0, -60.0);
	UMIEffects::SpawnViewBody(this, Mesh, At, Vel, Real, RealVel, FVector(FMath::FRandRange(-200.0, 200.0), FMath::FRandRange(-300.0, 300.0), 0.0), 0.45, 8.0);
	UE_LOG(LogMI, Log, TEXT("First person: magazine dropped at %s, %.0f cm/s"), *Pos.ToCompactString(), Vel.Size());
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
		// the solved grip, when there is one: the hand turned and placed as solved, each finger closed onto the gun
		const TMap<FName, FVector>& Pts = GripPoints[FCString::Strcmp(H, TEXT("hand_l")) == 0 ? 0 : 1];
		if (!Pts.IsEmpty() && GripWeight > 0.0)
		{
			const FTransform GunWorld = Gun->GetComponentTransform();
			for (const TPair<FName, FVector>& KV : Pts)
			{
				IK.Shape.Add(KV.Key, ArmsWorld.InverseTransformPosition(GunWorld.TransformPosition(KV.Value)));
			}
			IK.ShapeWeight = static_cast<float>(GripWeight);
		}
	};
	Pull(LeftSocket, TEXT("upperarm_l"), TEXT("lowerarm_l"), TEXT("hand_l"), TEXT("middle_metacarpal_l"));
	Pull(RightSocket, TEXT("upperarm_r"), TEXT("lowerarm_r"), TEXT("hand_r"), TEXT("middle_metacarpal_r"));
	// In a reload the support hand leaves the grip and works the magazine (review 2026-11-23: it stayed on the
	// rolled pistol): its palm follows the magazine's base pad on the 'magazine' bone the rig drops and seats, blended
	// in and out over the first and last 0.15 s.
	const FName MagBone = OwnMag ? OwnMag->GetAttachSocketName() : NAME_None;
	if (bReloadingNow && !MagBone.IsNone() && Gun->DoesSocketExist(MagBone) && HandPose.Hands.Num() > 0 && HandPose.Hands[0].Hand == TEXT("hand_l"))
	{
		const FTransform Base = FTransform(MagBasePad) * OwnMag->GetRelativeTransform() * Gun->GetSocketTransform(MagBone);
		FMIFPHandIK& L = HandPose.Hands[0];
		const double K = FMath::Clamp(FMath::Min(ReloadNowT, ReloadNowLeft) / 0.15, 0.0, 1.0);
		L.Target.SetLocation(FMath::Lerp(L.Target.GetLocation(), Base.GetRelativeTransform(ArmsWorld).GetLocation(), MIFirstPersonRigPrivate::Smooth(K)));
		L.ShapeWeight *= static_cast<float>(1.0 - MIFirstPersonRigPrivate::Smooth(K));  // the support grip lets go
	}
	AI->SetPose(HandPose);
}

#if WITH_EDITOR
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#endif

void UMIFirstPersonRig::ProbeGrip(const FString& Label) const
{
#if WITH_EDITOR
	USkeletalMesh* ArmsAsset = Arms ? Cast<USkeletalMesh>(Arms->GetSkinnedAsset()) : nullptr;
	USkeletalMesh* GunAsset = PackGun ? Cast<USkeletalMesh>(PackGun->GetSkinnedAsset()) : nullptr;
	if (Mode != EMIFPMode::Pack || !ArmsAsset || !GunAsset || !ArmsAsset->GetImportedModel() || !GunAsset->GetImportedModel()
		|| ArmsAsset->GetImportedModel()->LODModels.Num() == 0 || GunAsset->GetImportedModel()->LODModels.Num() == 0)
	{
		UE_LOG(LogMI, Log, TEXT("MI-GRIP %s: no pack gun with imported models in hand"), *Label);
		return;
	}
	// The gun's triangles in world space (its reference pose: the gun clip's base is the reference pose).
	const FSkeletalMeshLODModel& G = GunAsset->GetImportedModel()->LODModels[0];
	TArray<FVector> GV, GN;
	const FTransform GunT = PackGun->GetComponentTransform();
	for (const FSkelMeshSection& S : G.Sections)
	{
		if (GV.Num() < static_cast<int32>(S.BaseVertexIndex)) { GV.SetNum(S.BaseVertexIndex); GN.SetNum(S.BaseVertexIndex); }
		for (const FSoftSkinVertex& V : S.SoftVertices)
		{
			GV.Add(GunT.TransformPosition(FVector(V.Position)));
			GN.Add(GunT.TransformVectorNoScale(FVector(V.TangentZ.X, V.TangentZ.Y, V.TangentZ.Z)));
		}
	}
	TArray<FVector> Tri, TriN;   // three corners per triangle; its outward normal (the corners' normals averaged)
	for (int32 I = 0; I + 2 < G.IndexBuffer.Num(); I += 3)
	{
		const uint32 A = G.IndexBuffer[I], B = G.IndexBuffer[I + 1], C = G.IndexBuffer[I + 2];
		if (static_cast<int32>(FMath::Max3(A, B, C)) < GV.Num())
		{
			Tri.Add(GV[A]); Tri.Add(GV[B]); Tri.Add(GV[C]);
			TriN.Add((GN[A] + GN[B] + GN[C]).GetSafeNormal());
		}
	}
	// The arms' vertices skinned on the CPU (component-space bones x inverse reference), with their main bone.
	const FSkeletalMeshLODModel& M = ArmsAsset->GetImportedModel()->LODModels[0];
	const TArray<FTransform>& CSB = Arms->GetComponentSpaceTransforms();
	const TArray<FMatrix44f>& Inv = ArmsAsset->GetRefBasesInvMatrix();
	const FTransform ToWorld = Arms->GetComponentTransform();
	struct FPt { FVector P; int32 Bone; };
	TArray<FPt> Pts;
	for (const FSkelMeshSection& S : M.Sections)
	{
		for (int32 VI = 0; VI < S.SoftVertices.Num(); VI += 2)   // every second vertex: plenty on a finger
		{
			const FSoftSkinVertex& V = S.SoftVertices[VI];
			FVector Acc = FVector::ZeroVector;
			int32 Best = INDEX_NONE, BestW = -1;
			for (int32 K = 0; K < MAX_TOTAL_INFLUENCES; ++K)
			{
				const int32 W = V.InfluenceWeights[K];
				if (W == 0 || !S.BoneMap.IsValidIndex(V.InfluenceBones[K])) continue;
				const int32 Bone = S.BoneMap[V.InfluenceBones[K]];
				if (!CSB.IsValidIndex(Bone) || !Inv.IsValidIndex(Bone)) continue;
				const FMatrix Skin = FMatrix(Inv[Bone]) * CSB[Bone].ToMatrixWithScale();
				Acc += Skin.TransformPosition(FVector(V.Position)) * (W / 65535.0);
				if (W > BestW) { BestW = W; Best = Bone; }
			}
			if (Best != INDEX_NONE) Pts.Add({ToWorld.TransformPosition(Acc), Best});
		}
	}
	static const TCHAR* Fingers[4] = {TEXT("index"), TEXT("middle"), TEXT("ring"), TEXT("pinky")};
	const auto BoneAt = [this](FName N) { return Arms->GetBoneLocation(N, EBoneSpaces::WorldSpace); };
	const double Target = 0.1;   // cm: the pad on the surface
	for (int32 S = 0; S < 2; ++S)
	{
		const bool bLeft = S == 0;
		FVector Base[4], Tip[4];
		for (int32 I = 0; I < 4; ++I) { Base[I] = BoneAt(MIFingerCurl::Bone(Fingers[I], 1, bLeft)); Tip[I] = BoneAt(MIFingerCurl::Bone(Fingers[I], 3, bLeft)); }
		const FVector N = MIFingerCurl::PalmNormal(BoneAt(bLeft ? FName(TEXT("hand_l")) : FName(TEXT("hand_r"))), Base[1], Base[0], Base[3], Base, Tip);
		for (int32 I = 0; I < 4; ++I)
		{
			int32 Bi[3];
			FVector P0[3];
			for (int32 J = 0; J < 3; ++J) { Bi[J] = Arms->GetBoneIndex(MIFingerCurl::Bone(Fingers[I], J + 1, bLeft)); P0[J] = BoneAt(MIFingerCurl::Bone(Fingers[I], J + 1, bLeft)); }
			if (Bi[0] == INDEX_NONE || Bi[1] == INDEX_NONE || Bi[2] == INDEX_NONE) continue;
			TArray<TPair<FVector, int32>> Own;   // the finger's middle and end segments (the pads), joint 1 or 2
			for (const FPt& Pt : Pts) if (Pt.Bone == Bi[1] || Pt.Bone == Bi[2]) Own.Add({Pt.P, Pt.Bone == Bi[1] ? 1 : 2});
			if (Own.Num() == 0) continue;
			// the gun's triangles near this finger
			const double Reach = FVector::Dist(P0[0], P0[2]) + 6.0;
			TArray<int32> Near;
			for (int32 T = 0; T < Tri.Num(); T += 3)
			{
				const FVector C = (Tri[T] + Tri[T + 1] + Tri[T + 2]) / 3.0;
				const double R = FMath::Max3(FVector::Dist(C, Tri[T]), FVector::Dist(C, Tri[T + 1]), FVector::Dist(C, Tri[T + 2]));
				if (FVector::Dist(C, P0[0]) < Reach + R) Near.Add(T);
			}
			// (gap, depth): the nearest pad point's distance outside the gun, and how deep the deepest one is inside
			// (signed by the nearest triangle's outward normal), with the finger curled by Deg as the anim applies it
			const auto Measure = [&](float Deg, double& OutGap, double& OutDepth)
			{
				// the curl as UMIFPAnimInstance applies it: joint by joint, each about its pivot, the rest following
				FVector P[3] = {P0[0], P0[1], P0[2]};
				FQuat Acc[3];
				FVector Piv[3];
				for (int32 J = 0; J < 3; ++J)
				{
					const FQuat Q = MIFingerCurl::JointTurn(P, J, N, Deg);
					Acc[J] = Q;
					Piv[J] = P[J];
					for (int32 K = J + 1; K < 3; ++K) P[K] = Piv[J] + Q.RotateVector(P[K] - Piv[J]);
				}
				OutGap = 1e9;
				OutDepth = 0.0;
				for (int32 OI = 0; OI < Own.Num(); OI += 2)
				{
					FVector V = Own[OI].Key;
					for (int32 J = 0; J <= Own[OI].Value; ++J) V = Piv[J] + Acc[J].RotateVector(V - Piv[J]);
					double Best = 1e9, Signed = 1e9;
					for (const int32 T : Near)
					{
						const FVector Q = FMath::ClosestPointOnTriangleToPoint(V, Tri[T], Tri[T + 1], Tri[T + 2]);
						const double D = FVector::Dist(V, Q);
						if (D < Best) { Best = D; Signed = FVector::DotProduct(V - Q, TriN[T / 3]) < 0.0 ? -D : D; }
					}
					if (Signed >= 0.0) OutGap = FMath::Min(OutGap, Signed);
					else OutDepth = FMath::Max(OutDepth, -Signed);
				}
				if (OutDepth > 0.0) OutGap = 0.0;
			};
			double G0 = 0.0, D0 = 0.0;
			Measure(0.f, G0, D0);
			float Best = 0.f;
			double GB = G0, DB = D0;
			if (D0 > 0.3)
			{
				// in the gun: open until the deepest pad point is within 1.5 mm of the surface
				for (float Dg = -1.f; Dg >= -25.f; Dg -= 1.f)
				{
					Measure(Dg, GB, DB);
					Best = Dg;
					if (DB <= 0.15) break;
				}
			}
			else if (G0 > Target)
			{
				// off the gun: close until a pad touches
				for (float Dg = 1.f; Dg <= 45.f; Dg += 1.f)
				{
					Measure(Dg, GB, DB);
					Best = Dg;
					if (GB <= Target || DB > 0.0) break;
				}
				if (GB > 1.0) { Best = 0.f; GB = G0; DB = D0; }   // nothing within reach of a curl: leave it
			}
			UE_LOG(LogMI, Log, TEXT("MI-GRIP %s %s %s gap %.2f cm depth %.2f cm, %d points, %d triangles near; curl %.0f deg: gap %.2f cm depth %.2f cm"),
				*Label, bLeft ? TEXT("l") : TEXT("r"), Fingers[I], G0, D0, Own.Num(), Near.Num(), Best, GB, DB);
		}
	}
#else
	UE_LOG(LogMI, Log, TEXT("MI-GRIP %s: editor builds only"), *Label);
#endif
}
