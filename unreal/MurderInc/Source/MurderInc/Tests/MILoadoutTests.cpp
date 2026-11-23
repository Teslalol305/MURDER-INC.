// LOADOUT.md 8: the loadout data, the resolver's parity and the attachments.

#include "Core/Data/MIDataSubsystem.h"
#include "Core/Data/MILoadoutData.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Misc/AutomationTest.h"
#include "Misc/Paths.h"
#include "World/MILevelData.h"
#include "Weapons/MILoadoutResolver.h"
#include "Weapons/MIViewmodel.h"

#if WITH_AUTOMATION_TESTS

namespace MILoadoutTestsPrivate
{
	constexpr EAutomationTestFlags Flags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter;

	/** Field-by-field, doubles exactly (the parity guard of LOADOUT.md 8.1). */
	void SameGun(FAutomationTestBase& T, const FString& L, const FMIWeaponDef& A, const FMIWeaponDef& B)
	{
#define MI_SAME(F) T.TestTrue(L + TEXT(" ") TEXT(#F), A.F == B.F)
		MI_SAME(Id); MI_SAME(Name); MI_SAME(bAuto); MI_SAME(Damage); MI_SAME(Rpm); MI_SAME(MagSize); MI_SAME(Reserve); MI_SAME(Range);
		MI_SAME(AdsTime); MI_SAME(FireBuffer); MI_SAME(DryCooldown); MI_SAME(DryReloadDelay);
		MI_SAME(Reload.Tactical); MI_SAME(Reload.Empty); MI_SAME(Reload.MagOut); MI_SAME(Reload.MagIn); MI_SAME(Reload.BoltTactical); MI_SAME(Reload.BoltEmpty);
		MI_SAME(Spread.Hip); MI_SAME(Spread.Ads); MI_SAME(Spread.MoveHip); MI_SAME(Spread.MoveAds); MI_SAME(Spread.BloomHip); MI_SAME(Spread.BloomAds);
		MI_SAME(Spread.Air); MI_SAME(Spread.Crouch); MI_SAME(Spread.Shot); MI_SAME(Spread.Decay);
		MI_SAME(Recoil.Pitch); MI_SAME(Recoil.PitchRandomMin); MI_SAME(Recoil.PitchRandomMax); MI_SAME(Recoil.bWeave); MI_SAME(Recoil.LateFrom); MI_SAME(Recoil.LateScale);
		MI_SAME(Recoil.YawEarly); MI_SAME(Recoil.WeaveFrom); MI_SAME(Recoil.WeaveAmp); MI_SAME(Recoil.WeaveFreq); MI_SAME(Recoil.WeaveRandom); MI_SAME(Recoil.Yaw); MI_SAME(Recoil.Shake);
		MI_SAME(WallStart); MI_SAME(WallFull); MI_SAME(FlashScale); MI_SAME(FlashLight); MI_SAME(FlashColor); MI_SAME(FlashRange); MI_SAME(FlashTtl);
		MI_SAME(RumbleStrong); MI_SAME(RumbleWeak); MI_SAME(RumbleMs);
		MI_SAME(Holster); MI_SAME(Draw); MI_SAME(AdsFov); MI_SAME(AdsLook); MI_SAME(NoiseRadius); MI_SAME(FalloffStart); MI_SAME(FalloffEnd); MI_SAME(FalloffMin);
		MI_SAME(SemiFireBuffer); MI_SAME(ModeSwitch); MI_SAME(InspectAfter); MI_SAME(Pool); MI_SAME(bSuppressed);
#undef MI_SAME
	}

	void SameView(FAutomationTestBase& T, const FString& L, const FMIGunViewData& A, const FMIGunViewData& B)
	{
#define MI_SAME(F) T.TestTrue(L + TEXT(" view ") TEXT(#F), A.F == B.F)
		MI_SAME(Id); MI_SAME(Mesh); MI_SAME(Idle); MI_SAME(Relief); MI_SAME(FlashStar); MI_SAME(FlashJet); MI_SAME(ReloadTactical); MI_SAME(ReloadEmpty); MI_SAME(bAuto);
		MI_SAME(KickBack); MI_SAME(KickRise); MI_SAME(KickYaw); MI_SAME(KickRoll); MI_SAME(KickUp); MI_SAME(KickSide); MI_SAME(KickFirst); MI_SAME(KickSecond);
		MI_SAME(KickRandom); MI_SAME(KickCrouch); MI_SAME(KickAdsBack); MI_SAME(KickAdsRot); MI_SAME(KickAdsPos);
		MI_SAME(SpringBack); MI_SAME(SpringPitch); MI_SAME(SpringYaw); MI_SAME(SpringRoll); MI_SAME(SpringPos); MI_SAME(AdsSpring); MI_SAME(SwaySpring); MI_SAME(SwayMax);
		MI_SAME(Hip.Num()); MI_SAME(Melee); MI_SAME(BoltReloadTactical); MI_SAME(BoltReloadEmpty); MI_SAME(Bolt.Travel); MI_SAME(Magazine.Drop);
#undef MI_SAME
		T.TestTrue(L + TEXT(" view mesh offset"), A.MeshOffset.Equals(B.MeshOffset, 0.0));
		T.TestTrue(L + TEXT(" view markers"), A.Markers.OrderIndependentCompareEqual(B.Markers));
		T.TestTrue(L + TEXT(" view sockets"), A.Sockets.OrderIndependentCompareEqual(B.Sockets));
		T.TestTrue(L + TEXT(" view reload marks"), A.ReloadMarks.OrderIndependentCompareEqual(B.ReloadMarks));
		for (int32 I = 0; I < FMath::Min(A.Hip.Num(), B.Hip.Num()); ++I)
		{
			T.TestTrue(L + TEXT(" view hip pose"), A.Hip[I].Pos == B.Hip[I].Pos && A.Hip[I].Rot == B.Hip[I].Rot);
		}
	}

	bool LoadData(FAutomationTestBase& Test, FMILoadoutData& Out)
	{
		FString Error;
		if (!FMILoadoutData::Load(Out, Error))
		{
			Test.AddError(FString::Printf(TEXT("loadout data: %s"), *Error));
			return false;
		}
		return true;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMILoadoutDataLoadsTest, "MurderInc.Loadout.DataLoads", MILoadoutTestsPrivate::Flags)

bool FMILoadoutDataLoadsTest::RunTest(const FString& Parameters)
{
	FMILoadoutData D;
	if (!MILoadoutTestsPrivate::LoadData(*this, D))
	{
		return false;
	}
	TArray<FString> Problems;
	D.ValidateData(Problems);
	for (const FString& P : Problems)
	{
		AddError(P);
	}
	TestEqual(TEXT("roster"), D.Roster.Num(), 6);
	TestEqual(TEXT("parts"), D.Attachments.Num(), 10);
	TestEqual(TEXT("slots"), D.Slots.Num(), 6);
	TestEqual(TEXT("crew"), D.CrewOrder.Num(), 4);
	TestEqual(TEXT("parity guns"), D.ParityGuns, TArray<FName>{TEXT("chopper"), TEXT("nine")});
	// The CHOPPER's rules are the very config.json object (one source of truth).
	FMIConfigData Config;
	FString Error;
	TSharedPtr<FJsonObject> ConfigRoot;
	if (UMIDataSubsystem::LoadJsonFile(TEXT("config.json"), ConfigRoot, Error))
	{
		const TSharedPtr<FJsonValue> Chopper = MIJson::Get(ConfigRoot, TEXT("weapons.chopper"));
		TestTrue(TEXT("chopper rules = config.json weapons.chopper"), Chopper.IsValid() && MIJson::Print(Chopper->AsObject()) == MIJson::Print(D.FindGun(TEXT("chopper"))->Rules));
		double Holster = 0.0, Common = 0.0;
		TestTrue(TEXT("extraDefaults.holster is a number"), MIJson::Number(D.ExtraDefaults->TryGetField(TEXT("holster")), Holster));
		MIJson::Number(MIJson::Get(ConfigRoot, TEXT("weapons.common.holster")), Common);
		TestEqual(TEXT("extraDefaults.holster = weapons.common.holster"), Holster, Common);
	}

	// levels.json provides against the level file (the block: 3 reels, 29 / 17 spawns, 21 explosives, 14 title keys).
	const FMILevelData* Level = FMILevelData::Get();
	const FMILevelEntry* Block = D.Levels.Find(TEXT("block"));
	if (TestNotNull(TEXT("level.json"), Level) && TestNotNull(TEXT("levels.json block"), Block))
	{
		int32 Ground = 0, Air = 0;
		for (const FMILevelPoint& S : Level->Spawns)
		{
			(S.Type == TEXT("air") ? Air : Ground)++;
		}
		const FMILevelProvides& P = Block->Provides;
		TestEqual(TEXT("objectives"), P.Objectives, Level->Objectives.Num());
		TestEqual(TEXT("ground spawns"), P.Ground, Ground);
		TestEqual(TEXT("air spawns"), P.Air, Air);
		TestEqual(TEXT("explosives"), P.bExplosives, Level->Explosives.Num() > 0);
		TestEqual(TEXT("title path"), P.bTitlePath, Level->CinematicPos.Num() >= 2);
		TestEqual(TEXT("21 explosives"), Level->Explosives.Num(), 21);
		TestEqual(TEXT("14 title keys"), Level->CinematicPos.Num(), 14);
		TestEqual(TEXT("3 reels"), Level->Objectives.Num(), 3);
	}
	return Problems.Num() == 0;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMILoadoutParityResolveTest, "MurderInc.Loadout.ParityResolve", MILoadoutTestsPrivate::Flags)

bool FMILoadoutParityResolveTest::RunTest(const FString& Parameters)
{
	using namespace MILoadoutTestsPrivate;
	FMILoadoutData D;
	FMIConfigData Config;
	FMIViewmodelData View;
	TSharedPtr<FJsonObject> ConfigRoot, PresentationRoot;
	FString Error;
	if (!LoadData(*this, D) || !UMIDataSubsystem::LoadConfig(Config, Error) || !FMIViewmodelData::Load(View, Error)
		|| !FMILoadoutResolver::LoadRoots(ConfigRoot, PresentationRoot, Error))
	{
		AddError(Error);
		return false;
	}
	const FMILoadoutResolver Resolver(D, ConfigRoot, PresentationRoot);
	const FMIRunSetup Setup = D.ParitySetup(TEXT("mission"), TEXT("boss"), TEXT("day"));
	FMIResolvedRun Run;
	if (!Resolver.Resolve(Setup, nullptr, Run, Error))
	{
		AddError(Error);
		return false;
	}
	TestEqual(TEXT("two guns"), Run.Weapons.Guns.Num(), Config.Weapons.Guns.Num());
	for (int32 I = 0; I < FMath::Min(Run.Guns.Num(), Config.Weapons.Guns.Num()); ++I)
	{
		const FMIResolvedGun& G = Run.Guns[I];
		const FString L = G.Id.ToString();
		// The JSON: byte-equal to config.json's object (no part fitted: no effect applied).
		const TSharedPtr<FJsonValue> Source = MIJson::Get(ConfigRoot, TEXT("weapons.") + L);
		TestTrue(L + TEXT(" rules JSON = config.json"), Source.IsValid() && MIJson::Print(G.Rules) == MIJson::Print(Source->AsObject()));
		const TSharedPtr<FJsonValue> PSource = MIJson::Get(PresentationRoot, TEXT("guns.") + L);
		TestTrue(L + TEXT(" presentation JSON = presentation.json"), PSource.IsValid() && MIJson::Print(G.Presentation) == MIJson::Print(PSource->AsObject()));
		// The filled defaults are the refs' values.
		for (const auto& Pair : D.ExtraDefaults->Values)
		{
			const FString Key(*Pair.Key);
			if (!D.FindGun(G.Id)->Extra->HasField(Key))
			{
				const TSharedPtr<FJsonValue> Have = G.Extra->TryGetField(Key);
				double X = 0.0, Y = 0.0;
				const bool bNumbers = MIJson::Number(Have, X) && MIJson::Number(Pair.Value, Y);
				TestTrue(L + TEXT(" extra.") + Key + TEXT(" is the default"), Have.IsValid() && (!bNumbers || X == Y));
			}
		}
		SameGun(*this, L, G.Def, Config.Weapons.Guns[I]);
		TestEqual(L + TEXT(" starts in fireModes[0]"), G.Def.FireModes.Num() > 0 ? G.Def.FireModes[0] : NAME_None, Config.Weapons.Guns[I].FireModes[0]);
		TestEqual(L + TEXT(" slot"), G.Def.Slot, Config.Weapons.Guns[I].Slot);
		if (const FMIGunViewData* V = View.Find(G.Id))
		{
			SameView(*this, L, Run.View.Guns[I], *V);
		}
	}
	TestTrue(TEXT("CHOPPER fire modes auto, semi"), Run.Weapons.Guns.Num() > 0 && Run.Weapons.Guns[0].FireModes == TArray<FName>{TEXT("auto"), TEXT("semi")});
	TestTrue(TEXT("NINE fire modes semi"), Run.Weapons.Guns.Num() > 1 && Run.Weapons.Guns[1].FireModes == TArray<FName>{TEXT("semi")});
	// Common and melee: the same parser on the same document.
	const FMIWeaponCommonData& A = Run.Weapons.Common;
	const FMIWeaponCommonData& B = Config.Weapons.Common;
	TestTrue(TEXT("common"), A.Holster == B.Holster && A.Draw == B.Draw && A.HeadMultiplier == B.HeadMultiplier && A.SpreadRate == B.SpreadRate
		&& A.LowAmmoFraction == B.LowAmmoFraction && A.TracerSpeed == B.TracerSpeed && A.AimRange == B.AimRange);
	TestTrue(TEXT("melee"), Run.Weapons.Melee.Damage == Config.Weapons.Melee.Damage && Run.Weapons.Melee.Reach == Config.Weapons.Melee.Reach);
	TestTrue(TEXT("viewmodel fov"), Run.View.ViewmodelFov == View.ViewmodelFov && Run.View.FirstPersonScale == View.FirstPersonScale);
	return !HasAnyErrors();
}

// LOADOUT.md 8.6: every mount and variant the data marks `exists` has its mesh and its sockets on the imported pack
// meshes. A clean checkout has no pack meshes (licence, 6.7): then there is nothing to check and the test says so.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMILoadoutMountsExistTest, "MurderInc.Loadout.MountsExist", MILoadoutTestsPrivate::Flags)

bool FMILoadoutMountsExistTest::RunTest(const FString& Parameters)
{
	using namespace MILoadoutTestsPrivate;
	FMILoadoutData D;
	if (!LoadData(*this, D))
	{
		return false;
	}
	const FMIAssetExists Exists = FMIReadiness::PackageExists();
	int32 Meshes = 0, Sockets = 0, Absent = 0;
	const auto HasSocket = [](const UObject* Mesh, FName Socket)
	{
		if (const USkeletalMesh* S = Cast<USkeletalMesh>(Mesh)) return S->FindSocket(Socket) != nullptr || S->GetRefSkeleton().FindBoneIndex(Socket) != INDEX_NONE;
		if (const UStaticMesh* S = Cast<UStaticMesh>(Mesh)) return S->FindSocket(Socket) != nullptr;
		return false;
	};
	for (const TPair<FName, FMIGunEntry>& Pair : D.Guns)
	{
		const FMIGunEntry& G = Pair.Value;
		for (const TPair<FName, FMIGunVariant>& V : G.Variants)
		{
			if (V.Value.Status != TEXT("exists") || V.Value.Mesh.IsEmpty())
			{
				continue;
			}
			// The variant's mesh and its irons-folded twin (used whenever an optic is fitted).
			TArray<FString> Paths = {V.Value.Mesh};
			const FString Optic = MIJson::StringOr(D.GunsJson, FString::Printf(TEXT("guns.%s.variants.%s.opticMesh"), *G.Id.ToString(), *V.Key.ToString()));
			if (!Optic.IsEmpty()) Paths.Add(Optic);
			for (const FString& Path : Paths)
			{
				if (!Exists(Path))
				{
					++Absent;
					continue;
				}
				const UObject* Mesh = FSoftObjectPath(Path).TryLoad();
				const FString L = FString::Printf(TEXT("%s %s (%s)"), *G.Id.ToString(), *V.Key.ToString(), *FPaths::GetBaseFilename(Path));
				if (!TestNotNull(L + TEXT(": the mesh loads"), Mesh))
				{
					continue;
				}
				++Meshes;
				for (const TPair<FName, FMIGunMount>& M : G.Mounts)
				{
					if (M.Value.Status == TEXT("exists"))
					{
						TestTrue(FString::Printf(TEXT("%s: mount %s has socket %s"), *L, *M.Key.ToString(), *M.Value.Socket.ToString()), HasSocket(Mesh, M.Value.Socket));
						++Sockets;
					}
				}
				// The viewmodel sockets every variant carries (presentation.sockets).
				if (const TSharedPtr<FJsonValue> S = MIJson::Get(G.Presentation, TEXT("sockets")); S.IsValid() && S->Type == EJson::Object)
				{
					for (const auto& Socket : S->AsObject()->Values)
					{
						if (Socket.Value->Type == EJson::String && FString(*Socket.Key) != TEXT("note"))
						{
							TestTrue(FString::Printf(TEXT("%s: socket %s"), *L, *Socket.Value->AsString()), HasSocket(Mesh, FName(*Socket.Value->AsString())));
							++Sockets;
						}
					}
				}
			}
		}
	}
	// The parts: their meshes and the sockets their presentation names.
	for (const TPair<FName, FMIAttachmentDef>& Pair : D.Attachments)
	{
		const FMIAttachmentDef& A = Pair.Value;
		if (A.ArtStatus != TEXT("exists") || A.Mesh.IsEmpty())
		{
			continue;
		}
		if (!Exists(A.Mesh))
		{
			++Absent;
			continue;
		}
		const UObject* Mesh = FSoftObjectPath(A.Mesh).TryLoad();
		if (!TestNotNull(A.Id.ToString() + TEXT(": the part's mesh loads"), Mesh))
		{
			continue;
		}
		++Meshes;
		for (const TPair<FName, FName>& S : A.Sockets)
		{
			TestTrue(FString::Printf(TEXT("%s: socket %s"), *A.Id.ToString(), *S.Value.ToString()), HasSocket(Mesh, S.Value));
			++Sockets;
		}
	}
	if (Meshes == 0)
	{
		AddInfo(FString::Printf(TEXT("The pack is not installed here (%d meshes the data names are absent): nothing to check (LOADOUT.md 6.7)."), Absent));
	}
	else
	{
		AddInfo(FString::Printf(TEXT("%d pack meshes, %d sockets checked; %d named meshes absent"), Meshes, Sockets, Absent));
	}
	return !HasAnyErrors();
}

#endif
