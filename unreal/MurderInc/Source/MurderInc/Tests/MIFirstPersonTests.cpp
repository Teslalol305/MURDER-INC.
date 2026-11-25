// The first-person presentation's data path (docs/unreal/ANIMATION.md 9, GAMEPLAY.md 15): the real art in place of the
// templates only when it exists, the rules untouched either way, and the clips the rig plays.

#include "Animation/AnimSequenceBase.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Core/Data/MILoadoutData.h"
#include "Engine/SkeletalMesh.h"
#include "Misc/AutomationTest.h"
#include "Weapons/MILoadoutResolver.h"
#include "Weapons/MIFirstPersonRig.h"
#include "Engine/StaticMesh.h"
#include "AnimationRuntime.h"

#if WITH_AUTOMATION_TESTS

namespace MIFirstPersonTestsPrivate
{
	constexpr EAutomationTestFlags Flags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter;

	struct FFixture
	{
		FMILoadoutData Data;
		TSharedPtr<FJsonObject> Config, Presentation;
		bool Load(FAutomationTestBase& T)
		{
			FString Error;
			if (!FMILoadoutData::Load(Data, Error) || !FMILoadoutResolver::LoadRoots(Config, Presentation, Error))
			{
				T.AddError(Error);
				return false;
			}
			return true;
		}
		bool Resolve(FName Gun, const FMIGunBuild* Build, bool bArtExists, FMIResolvedGun& Out, FAutomationTestBase& T) const
		{
			FMIReadiness Ready;
			Ready.Data = &Data;
			Ready.AssetExists = [bArtExists](const FString&) { return bArtExists; };
			FString Error;
			const FMILoadoutResolver Resolver(Data, Config, Presentation);
			if (!Resolver.ResolveGun(Gun, Build, &Ready, Out, Error))
			{
				T.AddError(Error);
				return false;
			}
			return true;
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIFirstPersonRealArtTest, "MurderInc.FirstPerson.RealArt", MIFirstPersonTestsPrivate::Flags)

bool FMIFirstPersonRealArtTest::RunTest(const FString& Parameters)
{
	using namespace MIFirstPersonTestsPrivate;
	FFixture F;
	if (!F.Load(*this))
	{
		return false;
	}
	for (const bool bArt : {false, true})
	{
		const FString L = bArt ? TEXT("art present: ") : TEXT("clean checkout: ");
		FMIResolvedGun Chopper, Nine;
		if (!F.Resolve(TEXT("chopper"), nullptr, bArt, Chopper, *this) || !F.Resolve(TEXT("nine"), nullptr, bArt, Nine, *this))
		{
			return false;
		}
		const FString ChopperReal = MIJson::StringOr(F.Presentation, TEXT("guns.chopper.realMesh"));
		const FString ChopperTemplate = MIJson::StringOr(F.Presentation, TEXT("guns.chopper.mesh"));
		TestEqual(L + TEXT("CHOPPER base mesh"), Chopper.BaseMesh, bArt ? ChopperReal : ChopperTemplate);
		// Round 4 (DECISIONS.md 2026-11-25): SK_Chopper is the CHOPPER's own mesh again, held with the hand-IK set of our own
		// guns; the pack rifle's dark-earth finish and finger measures are gone from its block, with the art or without.
		TestEqual(L + TEXT("CHOPPER anim set"), MIJson::StringOr(Chopper.Presentation, TEXT("animSet")), bArt ? FString(TEXT("chopper_ik")) : FString());
		TestEqual(L + TEXT("CHOPPER grip socket"), MIJson::StringOr(Chopper.Presentation, TEXT("sockets.grip")), bArt ? FString(TEXT("Palm_R")) : FString(TEXT("GripPoint")));
		TestFalse(L + TEXT("CHOPPER has no pack finish"), MIJson::Get(Chopper.Presentation, TEXT("materials")).IsValid());
		TestFalse(L + TEXT("CHOPPER has no pack finger measures"), MIJson::Get(Chopper.Presentation, TEXT("fingers")).IsValid());
		if (bArt)
		{
			// SK_Chopper faces +X as SK_Nine does (origin on the bore, muzzle +X): no quarter turn, no offset.
			for (const TCHAR* Key : {TEXT("meshOffset.rot"), TEXT("meshOffset.pos")})
			{
				const TSharedPtr<FJsonValue> V = MIJson::Get(Chopper.Presentation, Key);
				const bool bOk = V.IsValid() && V->Type == EJson::Array && V->AsArray().Num() == 3;
				TestTrue(L + TEXT("CHOPPER ") + Key + TEXT(" is [0, 0, 0]"), bOk && V->AsArray()[0]->AsNumber() == 0.0 && V->AsArray()[1]->AsNumber() == 0.0 && V->AsArray()[2]->AsNumber() == 0.0);
			}
		}
		TestEqual(L + TEXT("NINE anim set"), MIJson::StringOr(Nine.Presentation, TEXT("animSet")), bArt ? FString(TEXT("pistol")) : FString());
		TestEqual(L + TEXT("NINE base mesh"), Nine.BaseMesh, MIJson::StringOr(F.Presentation, bArt ? TEXT("guns.nine.realMesh") : TEXT("guns.nine.mesh")));
		// The rules never change with the art (DECISIONS.md: only the CHOPPER's presentation changes).
		const TSharedPtr<FJsonValue> Rules = MIJson::Get(F.Config, TEXT("weapons.chopper"));
		TestTrue(L + TEXT("CHOPPER rules = config.json"), Rules.IsValid() && MIJson::Print(Chopper.Rules) == MIJson::Print(Rules->AsObject()));
		TestEqual(L + TEXT("CHOPPER reload stage times"), Chopper.View.ReloadTactical, 2.24);
		TestEqual(L + TEXT("CHOPPER empty reload"), Chopper.View.ReloadEmpty, 2.72);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIFirstPersonOpticTwinTest, "MurderInc.FirstPerson.OpticTwin", MIFirstPersonTestsPrivate::Flags)

bool FMIFirstPersonOpticTwinTest::RunTest(const FString& Parameters)
{
	using namespace MIFirstPersonTestsPrivate;
	FFixture F;
	if (!F.Load(*this))
	{
		return false;
	}
	// The STICK is the pack's rifle: an optic over its standing irons would block it, so the base mesh is the irons-folded
	// twin (ANIMATION.md 8.1 / 8.7) and it is drawn with the pack's clips.
	{
		const TCHAR* Gun = TEXT("stick");
		FMIGunBuild Irons, Scope;
		Irons.Parts.Add(TEXT("optic"), TEXT("irons"));
		Scope.Parts.Add(TEXT("optic"), TEXT("scope"));
		FMIResolvedGun A, B;
		if (!F.Resolve(Gun, &Irons, true, A, *this) || !F.Resolve(Gun, &Scope, true, B, *this))
		{
			return false;
		}
		const FString Open = MIJson::StringOr(F.Data.GunsJson, FString::Printf(TEXT("guns.%s.variants.open.mesh"), Gun));
		const FString Folded = MIJson::StringOr(F.Data.GunsJson, FString::Printf(TEXT("guns.%s.variants.open.opticMesh"), Gun));
		TestEqual(FString(Gun) + TEXT(" with irons: the standing irons"), A.BaseMesh, Open);
		TestEqual(FString(Gun) + TEXT(" with the scope: the folded twin"), B.BaseMesh, Folded);
		TestEqual(FString(Gun) + TEXT(" is drawn with the pack's clips"), MIJson::StringOr(B.Presentation, TEXT("animSet")), FString(TEXT("rifle")));
	}
	// Our own guns (round 4): the irons are bones of the one mesh and a fitted optic hides them (mounts.optic.hide), so there
	// is no twin mesh: the base is the same whatever optic is fitted, drawn with the gun's own hand-IK set, and the optic
	// part really carries the irons to hide.
	struct FOwn { const TCHAR* Gun; const TCHAR* Set; const TCHAR* Optics[2]; };
	const FOwn Own[] = {{TEXT("shorty"), TEXT("shorty_ik"), {TEXT("red_dot"), TEXT("scope_4x")}},
		{TEXT("stretch"), TEXT("stretch_ik"), {TEXT("red_dot"), TEXT("scope_4x")}},
		{TEXT("rattler"), TEXT("rattler_ik"), {TEXT("red_dot"), TEXT("red_dot")}}};
	for (const FOwn& G : Own)
	{
		const FString Name = G.Gun;
		const FString Open = Name == TEXT("rattler") ? MIJson::StringOr(F.Data.GunsJson, TEXT("guns.rattler.presentation.realMesh"))
			: MIJson::StringOr(F.Data.GunsJson, FString::Printf(TEXT("guns.%s.variants.open.mesh"), G.Gun));
		TestTrue(Name + TEXT(" has a mesh path"), !Open.IsEmpty());
		TestTrue(Name + TEXT(" has no optic twin"), MIJson::StringOr(F.Data.GunsJson, FString::Printf(TEXT("guns.%s.variants.open.opticMesh"), G.Gun)).IsEmpty());
		for (const TCHAR* Optic : G.Optics)
		{
			FMIGunBuild Build;
			Build.Parts.Add(TEXT("optic"), Optic);
			FMIResolvedGun R;
			if (!F.Resolve(G.Gun, &Build, true, R, *this))
			{
				return false;
			}
			const FString L = Name + TEXT(" with ") + Optic;
			TestEqual(L + TEXT(": the same base mesh"), R.BaseMesh, Open);
			TestEqual(L + TEXT(": its hand-IK set"), MIJson::StringOr(R.Presentation, TEXT("animSet")), FString(G.Set));
			const FMIResolvedPart* P = R.Parts.FindByPredicate([](const FMIResolvedPart& X) { return X.Slot == TEXT("optic"); });
			if (TestNotNull(L + TEXT(": the optic is a fitted part"), P))
			{
				TestTrue(L + TEXT(": it hides the irons"), P->Hide.Num() > 0);
				TestTrue(L + TEXT(": it brings its own sight"), P->Markers.Contains(TEXT("sightRear")));
			}
		}
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIFirstPersonClipsTest, "MurderInc.FirstPerson.Clips", MIFirstPersonTestsPrivate::Flags)

bool FMIFirstPersonClipsTest::RunTest(const FString& Parameters)
{
	using namespace MIFirstPersonTestsPrivate;
	FFixture F;
	if (!F.Load(*this))
	{
		return false;
	}
	// On the box: every clip an anim set names loads, the arms' clips on the arms' skeleton and the rifle's on the
	// rifle's; the reload marks rise. Without the art (a clean checkout) the template way is used: says so, passes.
	USkeletalMesh* Arms = Cast<USkeletalMesh>(FSoftObjectPath(MIJson::StringOr(F.Presentation, TEXT("firstPerson.arms"))).TryLoad());
	// The pack rifle is the STICK's (the CHOPPER is our own SK_Chopper again, held with the hand-IK set of our own guns).
	USkeletalMesh* Rifle = Cast<USkeletalMesh>(FSoftObjectPath(MIJson::StringOr(F.Data.GunsJson, TEXT("guns.stick.variants.open.mesh"))).TryLoad());
	if (!Arms)
	{
		AddInfo(TEXT("SK_RuleArms is not in this project (clean checkout): the template body stays; nothing to check"));
		return true;
	}
	int32 Checked = 0;
	const TSharedPtr<FJsonValue> Sets = MIJson::Get(F.Presentation, TEXT("firstPerson.animSets"));
	for (const auto& S : Sets->AsObject()->Values)
	{
		const TSharedPtr<FJsonObject> Set = S.Value->AsObject();
		const bool bPack = MIJson::StringOr(Set, TEXT("mode")) == TEXT("pack");
		if (bPack && !Rifle)
		{
			AddInfo(TEXT("the pack rifle is not in this project: its set is skipped"));
			continue;
		}
		for (const TCHAR* Part : {TEXT("arms"), TEXT("gun")})
		{
			const TSharedPtr<FJsonValue> Roles = MIJson::Get(Set, Part);
			if (!Roles.IsValid())
			{
				continue;
			}
			const USkeleton* Want = FString(Part) == TEXT("arms") ? Arms->GetSkeleton() : Rifle->GetSkeleton();
			for (const auto& R : Roles->AsObject()->Values)
			{
				const UAnimSequenceBase* Clip = Cast<UAnimSequenceBase>(FSoftObjectPath(R.Value->AsString()).TryLoad());
				const FString L = FString::Printf(TEXT("%s.%s.%s"), *FString(*S.Key), Part, *FString(*R.Key));
				if (TestNotNull(L + TEXT(" loads"), Clip))
				{
					TestTrue(L + TEXT(" is on the right skeleton"), Clip->GetSkeleton() == Want);
					++Checked;
				}
			}
		}
		if (const TSharedPtr<FJsonValue> Reloads = MIJson::Get(Set, TEXT("reloads")); Reloads.IsValid())
		{
			for (const auto& R : Reloads->AsObject()->Values)
			{
				double Last = 0.0;
				for (const TSharedPtr<FJsonValue>& M : R.Value->AsObject()->GetArrayField(TEXT("marks")))
				{
					const double T = M->AsArray()[1]->AsNumber();
					TestTrue(FString(*R.Key) + TEXT(" marks rise"), T > Last);
					Last = T;
				}
			}
		}
	}
	AddInfo(FString::Printf(TEXT("%d clips checked"), Checked));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIFirstPersonNineMagazineTest, "MurderInc.FirstPerson.NineMagazine", MIFirstPersonTestsPrivate::Flags)

// The NINE's magazine is modelled in the pistol's space; attached to the 'magazine' bone it must sit inside the grip
// (review 2026-11-23: snapped to the bone's frame it floated 10 to 20 cm beside the gun, turned 90 degrees).
bool FMIFirstPersonNineMagazineTest::RunTest(const FString& Parameters)
{
	using namespace MIFirstPersonTestsPrivate;
	FFixture F;
	if (!F.Load(*this))
	{
		return false;
	}
	USkeletalMesh* Nine = Cast<USkeletalMesh>(FSoftObjectPath(MIJson::StringOr(F.Presentation, TEXT("guns.nine.realMesh"))).TryLoad());
	const TSharedPtr<FJsonObject> Set = MIJson::Get(F.Presentation, TEXT("firstPerson.animSets.pistol")).IsValid()
		? MIJson::Get(F.Presentation, TEXT("firstPerson.animSets.pistol"))->AsObject() : nullptr;
	UStaticMesh* Mag = Cast<UStaticMesh>(FSoftObjectPath(MIJson::StringOr(Set, TEXT("magazine.full"))).TryLoad());
	if (!Nine || !Mag)
	{
		AddInfo(TEXT("SK_Nine or its magazine is not in this project (a clean checkout): nothing to place"));
		return true;
	}
	const FName Bone(*MIJson::StringOr(Set, TEXT("magazine.socket")));
	const int32 Index = Nine->GetRefSkeleton().FindBoneIndex(Bone);
	if (!TestTrue(TEXT("SK_Nine has the magazine bone"), Index != INDEX_NONE))
	{
		return false;
	}
	const FTransform BoneCS = FAnimationRuntime::GetComponentSpaceTransformRefPose(Nine->GetRefSkeleton(), Index);
	const FTransform MagInGun = UMIFirstPersonRig::MeshSpacePartOnBone(Nine, Bone) * BoneCS;
	const FBox MagBox = Mag->GetBoundingBox().TransformBy(MagInGun);
	const FBox GunBox = Nine->GetImportedBounds().GetBox();
	AddInfo(FString::Printf(TEXT("magazine %s, gun %s (cm)"), *MagBox.ToString(), *GunBox.ToString()));
	// Inside the gun's box (1 cm slack: the base pad is the gun's lowest point) and below the bore, in the grip.
	TestTrue(TEXT("magazine inside SK_Nine's bounds"), GunBox.ExpandBy(1.0).IsInside(MagBox));
	TestTrue(TEXT("magazine below the bore"), MagBox.Max.Z < 0.5);
	TestTrue(TEXT("magazine in the grip, not beside it"), FMath::Abs(MagBox.GetCenter().Y) < 1.5 && MagBox.GetCenter().X < 6.0);
	TestTrue(TEXT("magazine upright (taller than long)"), MagBox.GetSize().Z > MagBox.GetSize().X);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIFirstPersonOwnGunSetsTest, "MurderInc.FirstPerson.OwnGunSets", MIFirstPersonTestsPrivate::Flags)

// Round 4: the five own guns are held with a hand-IK set of their own. On the box, for each: the set is an 'ik' set, both
// palms are sockets of the gun's mesh, the magazine it seats is a static mesh that sits in the gun (inside its bounds,
// below the bore, in the well's width) on a bone of the skeleton, and the brass it throws loads (the NINE has none).
bool FMIFirstPersonOwnGunSetsTest::RunTest(const FString& Parameters)
{
	using namespace MIFirstPersonTestsPrivate;
	FFixture F;
	if (!F.Load(*this))
	{
		return false;
	}
	int32 Checked = 0;
	for (const TCHAR* Gun : {TEXT("chopper"), TEXT("nine"), TEXT("shorty"), TEXT("stretch"), TEXT("rattler")})
	{
		FMIResolvedGun R;
		if (!F.Resolve(Gun, nullptr, true, R, *this))
		{
			return false;
		}
		const FString L = FString(Gun) + TEXT(": ");
		const FString SetName = MIJson::StringOr(R.Presentation, TEXT("animSet"));
		const TSharedPtr<FJsonValue> SetValue = MIJson::Get(F.Presentation, FString(TEXT("firstPerson.animSets.")) + SetName);
		if (!TestTrue(L + TEXT("its anim set '") + SetName + TEXT("' exists"), SetValue.IsValid() && SetValue->Type == EJson::Object))
		{
			continue;
		}
		const TSharedPtr<FJsonObject> Set = SetValue->AsObject();
		TestEqual(L + TEXT("the set is a hand-IK set"), MIJson::StringOr(Set, TEXT("mode")), FString(TEXT("ik")));
		USkeletalMesh* Mesh = Cast<USkeletalMesh>(FSoftObjectPath(R.BaseMesh).TryLoad());
		if (!Mesh)
		{
			AddInfo(L + TEXT("its mesh is not in this project (a clean checkout): the set is checked by the data tests only"));
			continue;
		}
		const auto HasBone = [Mesh](FName Name) { return Mesh->GetRefSkeleton().FindBoneIndex(Name) != INDEX_NONE || Mesh->FindSocket(Name) != nullptr; };
		for (const TCHAR* Side : {TEXT("ik.left"), TEXT("ik.right")})
		{
			TestTrue(L + Side + TEXT(" is a socket of the mesh"), HasBone(FName(*MIJson::StringOr(Set, Side))));
		}
		const FName Bone(*MIJson::StringOr(Set, TEXT("magazine.socket")));
		TestTrue(L + TEXT("the magazine's socket is a bone of the skeleton"), Mesh->GetRefSkeleton().FindBoneIndex(Bone) != INDEX_NONE);
		UStaticMesh* Mag = Cast<UStaticMesh>(FSoftObjectPath(MIJson::StringOr(Set, TEXT("magazine.full"))).TryLoad());
		if (TestNotNull(L + TEXT("the magazine loads"), Mag) && Mesh->GetRefSkeleton().FindBoneIndex(Bone) != INDEX_NONE)
		{
			const int32 Index = Mesh->GetRefSkeleton().FindBoneIndex(Bone);
			const FTransform MagInGun = UMIFirstPersonRig::MeshSpacePartOnBone(Mesh, Bone) * FAnimationRuntime::GetComponentSpaceTransformRefPose(Mesh->GetRefSkeleton(), Index);
			const FBox MagBox = Mag->GetBoundingBox().TransformBy(MagInGun);
			const FBox GunBox = Mesh->GetImportedBounds().GetBox();
			AddInfo(FString::Printf(TEXT("%smagazine %s, gun %s (cm)"), *L, *MagBox.ToString(), *GunBox.ToString()));
			TestTrue(L + TEXT("the magazine is inside the gun's bounds"), GunBox.ExpandBy(1.0).IsInside(MagBox));
			TestTrue(L + TEXT("the magazine is below the bore"), MagBox.Max.Z < 0.5);
			TestTrue(L + TEXT("the magazine is in the well, not beside it"), FMath::Abs(MagBox.GetCenter().Y) < 1.5);
		}
		if (FString(Gun) != TEXT("nine"))
		{
			TestNotNull(L + TEXT("its brass loads"), Cast<UStaticMesh>(FSoftObjectPath(MIJson::StringOr(Set, TEXT("casing"))).TryLoad()));
		}
		++Checked;
	}
	AddInfo(FString::Printf(TEXT("%d own guns checked"), Checked));
	return true;
}

#endif
