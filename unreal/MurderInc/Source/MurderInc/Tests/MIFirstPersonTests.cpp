// The first-person presentation's data path (docs/unreal/ANIMATION.md 9, GAMEPLAY.md 15): the real art in place of the
// templates only when it exists, the rules untouched either way, and the clips the rig plays.

#include "Animation/AnimSequenceBase.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Core/Data/MILoadoutData.h"
#include "Engine/SkeletalMesh.h"
#include "Misc/AutomationTest.h"
#include "Weapons/MILoadoutResolver.h"

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
		TestEqual(L + TEXT("CHOPPER anim set"), MIJson::StringOr(Chopper.Presentation, TEXT("animSet")), bArt ? FString(TEXT("rifle")) : FString());
		TestEqual(L + TEXT("CHOPPER grip socket"), MIJson::StringOr(Chopper.Presentation, TEXT("sockets.grip")), bArt ? FString(TEXT("Palm_R")) : FString(TEXT("GripPoint")));
		TestEqual(L + TEXT("CHOPPER finish"), MIJson::Get(Chopper.Presentation, TEXT("materials")).IsValid(), bArt);
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
	// ANIMATION.md 8.1 / 8.7: an optic over standing irons would block it, so the base mesh is the irons-folded twin.
	for (const TCHAR* Gun : {TEXT("shorty"), TEXT("stick"), TEXT("stretch")})
	{
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
	USkeletalMesh* Rifle = Cast<USkeletalMesh>(FSoftObjectPath(MIJson::StringOr(F.Presentation, TEXT("guns.chopper.realMesh"))).TryLoad());
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

#endif
