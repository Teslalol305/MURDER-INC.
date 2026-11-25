// Weapons round 4 (docs/unreal/WEAPONS_R4_TESTS.md, LOADOUT.md 3.3, 8): six guns that read apart, twelve parts of our own,
// and the checks that keep it so: every part's trade, six different meshes, the slots each gun offers, the data held to
// the art's contract (a clean checkout runs it), and every part fitted on every gun on the box (frame, sight, hides).

#include "AnimationRuntime.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Core/Data/MILoadoutData.h"
#include "Engine/Engine.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "GameFramework/Actor.h"
#include "GameFramework/WorldSettings.h"
#include "Misc/AutomationTest.h"
#include "Weapons/MIGunAssembly.h"
#include "Weapons/MILoadoutResolver.h"

#if WITH_AUTOMATION_TESTS

namespace MIWeaponsR4Private
{
	constexpr EAutomationTestFlags Flags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter;

	/** Our five own guns, in roster order (the STICK is the pack's). */
	const TCHAR* const OwnGuns[] = {TEXT("chopper"), TEXT("nine"), TEXT("shorty"), TEXT("stretch"), TEXT("rattler")};

	struct FData
	{
		FMILoadoutData D;
		TSharedPtr<FJsonObject> Config, Presentation, Contract;
		bool Load(FAutomationTestBase& T)
		{
			FString Error;
			if (!FMILoadoutData::Load(D, Error) || !FMILoadoutResolver::LoadRoots(Config, Presentation, Error))
			{
				T.AddError(Error);
				return false;
			}
			if (!UMIDataSubsystem::LoadJsonFile(TEXT("gun_contract.json"), Contract, Error))
			{
				T.AddError(TEXT("gun_contract.json: ") + Error);
				return false;
			}
			return true;
		}
		FMILoadoutResolver Resolver() const { return FMILoadoutResolver(D, Config, Presentation); }
	};

	/** Blender metres (x fore, y left, z up) -> Unreal centimetres in the mesh's frame: (x, -y, z) x 100. */
	FVector CmOf(const TSharedPtr<FJsonValue>& V)
	{
		const TArray<TSharedPtr<FJsonValue>>& A = V->AsArray();
		return FVector(A[0]->AsNumber() * 100.0, -A[1]->AsNumber() * 100.0, A[2]->AsNumber() * 100.0);
	}

	/** Blender metres -> the web game's gun space (m): (-y, z, -x). */
	FVector WebOf(const TSharedPtr<FJsonValue>& V)
	{
		const TArray<TSharedPtr<FJsonValue>>& A = V->AsArray();
		return FVector(-A[1]->AsNumber(), A[2]->AsNumber(), -A[0]->AsNumber());
	}

	FVector Vec(const TSharedPtr<FJsonValue>& V)
	{
		const TArray<TSharedPtr<FJsonValue>>& A = V->AsArray();
		return FVector(A[0]->AsNumber(), A[1]->AsNumber(), A[2]->AsNumber());
	}

	/** A bare game world and an actor to hang components on; destroyed by the destructor. */
	struct FStageWorld
	{
		UWorld* World = nullptr;
		AActor* Owner = nullptr;

		FStageWorld()
		{
			World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("MIWeaponsR4World"));
			FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
			Context.SetCurrentWorld(World);
			World->InitializeActorsForPlay(FURL());
			World->BeginPlay();
			if (!World->GetBegunPlay())
			{
				World->GetWorldSettings()->NotifyBeginPlay();
			}
			Owner = World->SpawnActor<AActor>();
		}
		~FStageWorld()
		{
			World->EndPlay(EEndPlayReason::Quit);
			GEngine->DestroyWorldContext(World);
			World->DestroyWorld(false);
		}
	};
}

// ================================================================================================ the trade

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMILoadoutTradeBandTest, "MurderInc.Loadout.TradeBand", MIWeaponsR4Private::Flags)

bool FMILoadoutTradeBandTest::RunTest(const FString& Parameters)
{
	using namespace MIWeaponsR4Private;
	FData F;
	if (!F.Load(*this))
	{
		return false;
	}
	FMILoadoutData& D = F.D;
	// Every part's trade, to the table of WEAPONS_R4_TESTS.md section 4 (B, W to 4 decimals, B / W to 3): a retuned part is a
	// visible edit here. The pack's parts are the ones LOADOUT.md 3.3 prints.
	struct FRow { const TCHAR* Part; double B, W, Ratio; };
	const FRow Table[] = {
		{TEXT("scope"), 0.3567, 0.5625, 0.634}, {TEXT("silencer"), 0.9676, 0.4111, 2.354}, {TEXT("grip_vertical"), 0.2904, 0.1258, 2.309},
		{TEXT("grip_angled"), 0.1975, 0.1133, 1.743}, {TEXT("laser"), 0.3857, 0.2115, 1.824}, {TEXT("mag_clear"), 0.0619, 0.0392, 1.578},
		{TEXT("stock_folded"), 0.3416, 0.5878, 0.581},
		{TEXT("scope_4x"), 0.3567, 0.5625, 0.634}, {TEXT("suppressor"), 0.9676, 0.4111, 2.354}, {TEXT("suppressor_pistol"), 0.9676, 0.4111, 2.354},
		{TEXT("foregrip_vertical"), 0.2904, 0.1258, 2.309}, {TEXT("foregrip_vertical_wood"), 0.2904, 0.1258, 2.309}, {TEXT("foregrip_angled"), 0.1975, 0.1133, 1.743},
		{TEXT("laser_module"), 0.3857, 0.2115, 1.824}, {TEXT("red_dot"), 0.2112, 0.1258, 1.680}, {TEXT("compensator"), 0.2332, 0.1790, 1.303},
		{TEXT("mag_ext_rifle"), 0.4055, 0.2013, 2.014}, {TEXT("mag_ext_smg"), 0.4055, 0.2204, 1.840}, {TEXT("mag_ext_pistol"), 0.4700, 0.2305, 2.039},
	};
	int32 Checked = 0;
	for (const FRow& R : Table)
	{
		const FMIAttachmentDef* P = D.FindPart(R.Part);
		if (!TestNotNull(FString(R.Part) + TEXT(" is in attachments.json"), P))
		{
			continue;
		}
		double B = 0.0, W = 0.0;
		D.TradeOf(*P, B, W);
		TestTrue(FString::Printf(TEXT("%s: better %.4f is %.4f"), R.Part, B, R.B), FMath::Abs(B - R.B) < 6e-5);
		TestTrue(FString::Printf(TEXT("%s: worse %.4f is %.4f"), R.Part, W, R.W), FMath::Abs(W - R.W) < 6e-5);
		TestTrue(FString::Printf(TEXT("%s: B / W %.4f is %.3f"), R.Part, B / W, R.Ratio), W > 0.0 && FMath::Abs(B / W - R.Ratio) < 6e-4);
		++Checked;
	}
	// Every non-baseline part is in the table (a new part brings its row), and inside the band.
	for (const TPair<FName, FMIAttachmentDef>& P : D.Attachments)
	{
		if (P.Value.bBaseline)
		{
			continue;
		}
		bool bListed = false;
		for (const FRow& R : Table) bListed |= P.Key == R.Part;
		TestTrue(P.Key.ToString() + TEXT(" has a row in the trade table (a new part must bring its numbers)"), bListed);
		double B = 0.0, W = 0.0;
		D.TradeOf(P.Value, B, W);
		TestTrue(P.Key.ToString() + TEXT(" makes something better and something worse"), B > 0.0 && W > 0.0);
		TestTrue(P.Key.ToString() + TEXT(" inside the band"), W > 0.0 && B / W >= D.TradeMin && B / W <= D.TradeMax);
	}
	// The check can fail: a part with no cost, a part that costs three times what it gains, both reported by ValidateData.
	{
		FMILoadoutData Bad = D;
		FMIAttachmentDef Free;
		Free.Id = TEXT("fx_free");
		Free.Slot = TEXT("optic");
		Free.Text = TEXT("frontend.attachments.items.redDot");
		Free.Effects.Add({TEXT("adsTime"), TEXT("mul"), 0.9});
		Bad.Attachments.Add(Free.Id, Free);
		FMIAttachmentDef Dear = Free;
		Dear.Id = TEXT("fx_dear");
		Dear.Effects = {{TEXT("adsTime"), TEXT("mul"), 0.97}, {TEXT("swapTime"), TEXT("mul"), 1.5}};
		Bad.Attachments.Add(Dear.Id, Dear);
		TArray<FString> Problems;
		Bad.ValidateData(Problems);
		TestTrue(TEXT("a part with no cost is reported"), Problems.ContainsByPredicate([](const FString& S) { return S.Contains(TEXT("fx_free")) && S.Contains(TEXT("one stat better and one worse")); }));
		TestTrue(TEXT("a part out of balance is reported"), Problems.ContainsByPredicate([](const FString& S) { return S.Contains(TEXT("fx_dear")) && S.Contains(TEXT("out of balance")); }));
		TArray<FString> Own;
		D.ValidateData(Own);
		TestEqual(TEXT("the real data has no problem"), Own.Num(), 0);
	}
	// A magazine part's factor must give a whole number of rounds on every gun that takes it (the parser truncates).
	for (const TPair<FName, FMIAttachmentDef>& P : D.Attachments)
	{
		const FMIEffect* E = P.Value.Effects.FindByPredicate([](const FMIEffect& X) { return X.Stat == TEXT("magSize"); });
		if (!E)
		{
			continue;
		}
		for (const FName GunId : D.Roster)
		{
			const FMIGunEntry* G = D.FindGun(GunId);
			const FMICompatSlot* C = G ? G->FindCompat(P.Value.Slot) : nullptr;
			if (!C || !C->Options.Contains(P.Key))
			{
				continue;
			}
			const double Base = MIJson::NumberOr(G->Rules, TEXT("magSize"), 0.0);
			const double Product = Base * E->Value;
			TestTrue(FString::Printf(TEXT("%s on the %s: %g x %g = %g is a whole number"), *P.Key.ToString(), *GunId.ToString(), Base, E->Value, Product), FMath::Abs(Product - FMath::RoundToDouble(Product)) < 1e-9);
		}
	}
	AddInfo(FString::Printf(TEXT("%d parts held to the trade table"), Checked));
	return !HasAnyErrors();
}

// ================================================================================================ six guns

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMILoadoutDistinctGunsTest, "MurderInc.Loadout.DistinctGuns", MIWeaponsR4Private::Flags)

// The owner's complaint of 2026-11-25 as a regression guard: "all the guns look the same". With the art present the six guns
// resolve to six different meshes, each own gun's the art's contract asset and the STICK's the pack's; with none, the
// CHOPPER and the NINE keep their template meshes and the other four are not offered.
bool FMILoadoutDistinctGunsTest::RunTest(const FString& Parameters)
{
	using namespace MIWeaponsR4Private;
	FData F;
	if (!F.Load(*this))
	{
		return false;
	}
	const FMILoadoutResolver Resolver = F.Resolver();
	FMIReadiness All;
	All.Data = &F.D;
	All.AssetExists = [](const FString&) { return true; };
	TSet<FString> Meshes;
	for (const FName Gun : F.D.Roster)
	{
		FMIResolvedGun G;
		FString Error;
		if (!Resolver.ResolveGun(Gun, nullptr, &All, G, Error))
		{
			AddError(Gun.ToString() + TEXT(": ") + Error);
			continue;
		}
		Meshes.Add(G.BaseMesh);
		TestTrue(Gun.ToString() + TEXT(" is offered with every asset present"), All.IsGunOffered(Gun));
		if (Gun == TEXT("stick"))
		{
			TestTrue(TEXT("the STICK is the pack's rifle"), G.BaseMesh.Contains(TEXT("/ThirdParty/InfimaTFA/")));
		}
		else
		{
			const TSharedPtr<FJsonValue> Asset = MIJson::Get(F.Contract, FString::Printf(TEXT("guns.%s.asset"), *Gun.ToString()));
			if (TestTrue(Gun.ToString() + TEXT(" has a contract asset"), Asset.IsValid()))
			{
				TestEqual(Gun.ToString() + TEXT(" draws its own mesh"), G.BaseMesh, Asset->AsString());
			}
			TestFalse(Gun.ToString() + TEXT(" draws no pack mesh"), G.BaseMesh.Contains(TEXT("/ThirdParty/")));
		}
	}
	TestEqual(TEXT("six guns, six different meshes"), Meshes.Num(), 6);
	TestEqual(TEXT("the roster is six guns"), F.D.Roster.Num(), 6);
	// No art: the parity guns on the template meshes, nothing else offered.
	FMIReadiness None;
	None.Data = &F.D;
	None.AssetExists = [](const FString&) { return false; };
	for (const FName Gun : F.D.Roster)
	{
		const bool bParity = Gun == TEXT("chopper") || Gun == TEXT("nine");
		TestEqual(Gun.ToString() + TEXT(" offered without any art"), None.IsGunOffered(Gun), bParity);
		if (bParity)
		{
			FMIResolvedGun G;
			FString Error;
			if (Resolver.ResolveGun(Gun, nullptr, &None, G, Error))
			{
				TestEqual(Gun.ToString() + TEXT(" falls back to its template mesh"), G.BaseMesh, MIJson::StringOr(F.Presentation, FString::Printf(TEXT("guns.%s.mesh"), *Gun.ToString())));
			}
		}
	}
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMILoadoutSlotCountsTest, "MurderInc.Loadout.SlotCounts", MIWeaponsR4Private::Flags)

// The slots each gun offers on the Workbench: 3 / 3 / 5 / 5 / 4 / 3 with the art, none (and only two guns) without it.
bool FMILoadoutSlotCountsTest::RunTest(const FString& Parameters)
{
	using namespace MIWeaponsR4Private;
	FData F;
	if (!F.Load(*this))
	{
		return false;
	}
	FMIReadiness All;
	All.Data = &F.D;
	All.AssetExists = [](const FString&) { return true; };
	struct FWant { const TCHAR* Gun; TArray<FName> Slots; };
	const TArray<FWant> Want = {
		{TEXT("chopper"), {TEXT("optic"), TEXT("muzzle"), TEXT("underbarrel")}},
		{TEXT("nine"), {TEXT("muzzle"), TEXT("laser"), TEXT("magazine")}},
		{TEXT("shorty"), {TEXT("optic"), TEXT("muzzle"), TEXT("underbarrel"), TEXT("laser"), TEXT("magazine")}},
		// the STICK's stock slot is hidden: its folded variant has no mesh
		{TEXT("stick"), {TEXT("optic"), TEXT("muzzle"), TEXT("underbarrel"), TEXT("laser"), TEXT("magazine")}},
		{TEXT("stretch"), {TEXT("optic"), TEXT("muzzle"), TEXT("underbarrel"), TEXT("magazine")}},
		{TEXT("rattler"), {TEXT("optic"), TEXT("muzzle"), TEXT("magazine")}},
	};
	for (const FWant& W : Want)
	{
		TestEqual(FString(W.Gun) + TEXT(" slots with the art"), All.OfferedSlots(W.Gun), W.Slots);
	}
	int32 Total = 0;
	for (const FWant& W : Want) Total += All.OfferedSlots(W.Gun).Num();
	TestEqual(TEXT("3 + 3 + 5 + 5 + 4 + 3 slots"), Total, 23);
	// No asset at all: only the CHOPPER and the NINE are offered, with no slot.
	FMIReadiness None;
	None.Data = &F.D;
	None.AssetExists = [](const FString&) { return false; };
	TestEqual(TEXT("a clean checkout offers two guns"), None.IsGunOffered(TEXT("chopper")) + None.IsGunOffered(TEXT("nine")) + None.IsGunOffered(TEXT("shorty")) + None.IsGunOffered(TEXT("stick"))
		+ None.IsGunOffered(TEXT("stretch")) + None.IsGunOffered(TEXT("rattler")), 2);
	for (const FWant& W : Want)
	{
		TestEqual(FString(W.Gun) + TEXT(" slots without any art"), None.OfferedSlots(W.Gun).Num(), 0);
	}
	return !HasAnyErrors();
}

// ================================================================================================ the contract

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMILoadoutSocketContractTest, "MurderInc.Loadout.SocketContract", MIWeaponsR4Private::Flags)

// The data held to the art's contract (Content/Data/gun_contract.json: the exported sockets and bones, the parts' mounts).
// It needs no art on disk, so a clean checkout runs it: the engine twin of tools/data/check_guns_data.py.
bool FMILoadoutSocketContractTest::RunTest(const FString& Parameters)
{
	using namespace MIWeaponsR4Private;
	FData F;
	if (!F.Load(*this))
	{
		return false;
	}
	FMIReadiness All;
	All.Data = &F.D;
	All.AssetExists = [](const FString&) { return true; };
	const FMILoadoutResolver Resolver = F.Resolver();
	int32 Checks = 0;
	for (const TCHAR* Gun : OwnGuns)
	{
		const FString G = Gun;
		const FMIGunEntry* Entry = F.D.FindGun(Gun);
		const TSharedPtr<FJsonValue> CGun = MIJson::Get(F.Contract, TEXT("guns.") + G);
		if (!TestNotNull(G + TEXT(" is in the data"), Entry) || !TestTrue(G + TEXT(" is in the contract"), CGun.IsValid()))
		{
			continue;
		}
		const TSharedPtr<FJsonObject> Sockets = MIJson::Get(CGun->AsObject(), TEXT("sockets"))->AsObject();
		const TSharedPtr<FJsonObject> Bones = MIJson::Get(CGun->AsObject(), TEXT("deformBones"))->AsObject();
		// Every mount of the gun: its socket is the contract's, at the contract's place, every hide a deform bone.
		for (const TPair<FName, FMIGunMount>& M : Entry->Mounts)
		{
			if (M.Value.Status != TEXT("exists"))
			{
				continue;
			}
			const FString L = FString::Printf(TEXT("%s mount %s"), Gun, *M.Key.ToString());
			const TSharedPtr<FJsonValue> S = Sockets->TryGetField(M.Value.Socket.ToString());
			if (!TestTrue(L + TEXT(": socket ") + M.Value.Socket.ToString() + TEXT(" is in the contract"), S.IsValid()))
			{
				continue;
			}
			const TSharedPtr<FJsonValue> At = MIJson::Get(F.D.GunsJson, FString::Printf(TEXT("guns.%s.mounts.%s.at"), Gun, *M.Key.ToString()));
			if (TestTrue(L + TEXT(" has an 'at'"), At.IsValid()))
			{
				TestTrue(L + TEXT(": 'at' is the socket"), (Vec(At) - Vec(S)).Size() < 1e-6);
			}
			for (const FName H : M.Value.Hide)
			{
				TestTrue(L + TEXT(": hides ") + H.ToString() + TEXT(", a deform bone"), Bones->HasField(H.ToString()));
			}
			if (!M.Value.RideBone.IsNone())
			{
				TestTrue(L + TEXT(": rides ") + M.Value.RideBone.ToString() + TEXT(", a deform bone"), Bones->HasField(M.Value.RideBone.ToString()));
			}
			const FMICompatSlot* C = Entry->FindCompat(M.Key);
			if (C)
			{
				TestEqual(L + TEXT(": the compatibility mount is the socket"), C->Mount, M.Value.Socket);
			}
			++Checks;
		}
		// The viewmodel's own sockets are the gun's, and the markers sit where the exported sockets put them, plus the
		// mesh offset, to 1.2 mm; the mesh faces +X, so no turn.
		FMIResolvedGun R;
		FString Error;
		if (!Resolver.ResolveGun(Gun, nullptr, &All, R, Error))
		{
			AddError(G + TEXT(": ") + Error);
			continue;
		}
		const TSharedPtr<FJsonObject> Pres = R.Presentation;
		{
			const TSharedPtr<FJsonValue> V = MIJson::Get(Pres, TEXT("meshOffset.rot"));
			TestTrue(G + TEXT(" meshOffset.rot is the identity (the mesh faces +X)"), V.IsValid() && Vec(V).IsNearlyZero(1e-9));
		}
		const TSharedPtr<FJsonValue> Pos = MIJson::Get(Pres, TEXT("meshOffset.pos"));
		const FVector Offset = Pos.IsValid() ? Vec(Pos) : FVector::ZeroVector;
		const TSharedPtr<FJsonValue> SocketNames = MIJson::Get(Pres, TEXT("sockets"));
		const TSharedPtr<FJsonValue> Markers = MIJson::Get(Pres, TEXT("markers"));
		if (SocketNames.IsValid() && Markers.IsValid())
		{
			for (const auto& Pair : SocketNames->AsObject()->Values)
			{
				const FString Marker(*Pair.Key);
				if (Pair.Value->Type != EJson::String || Marker == TEXT("note"))
				{
					continue;
				}
				const FString SocketName = Pair.Value->AsString();
				TestTrue(G + TEXT(": the socket ") + SocketName + TEXT(" is in the contract"), Sockets->HasField(SocketName) || Bones->HasField(SocketName));
				const TSharedPtr<FJsonValue> At = Markers->AsObject()->TryGetField(Marker);
				const TSharedPtr<FJsonValue> S = Sockets->TryGetField(SocketName);
				if (At.IsValid() && S.IsValid())
				{
					const double Mm = (Vec(At) - (WebOf(S) + Offset)).Size() * 1000.0;
					if (FString(Gun) == TEXT("nine"))
					{
						// The NINE's markers are the older hand-set ones (the data check, check_guns_data.py, leaves them out too):
						// at run time the exported sockets replace them. Reported, not held to 1.2 mm.
						AddInfo(FString::Printf(TEXT("nine: marker %s is %.2f mm from its socket %s (not held: the sockets replace it at run time)"), *Marker, Mm, *SocketName));
						continue;
					}
					TestTrue(FString::Printf(TEXT("%s: marker %s is %.2f mm from its socket %s (within 1.2 mm)"), Gun, *Marker, Mm, *SocketName), Mm <= 1.2);
					++Checks;
				}
			}
		}
		// The hand-IK set names sockets the gun has.
		const FString SetName = MIJson::StringOr(Pres, TEXT("animSet"));
		for (const TCHAR* Side : {TEXT("ik.left"), TEXT("ik.right")})
		{
			const FString Socket = MIJson::StringOr(F.Presentation, FString::Printf(TEXT("firstPerson.animSets.%s.%s"), *SetName, Side));
			TestTrue(FString::Printf(TEXT("%s: %s of the set %s is a socket of the gun"), Gun, Side, *SetName), Sockets->HasField(Socket));
		}
		// The gun's parts: the bones the presentation moves exist.
		for (const TCHAR* Part : {TEXT("bolt"), TEXT("trigger"), TEXT("barrel"), TEXT("magazine")})
		{
			const FString Bone = MIJson::StringOr(Pres, FString::Printf(TEXT("parts.%s.bone"), Part));
			if (!Bone.IsEmpty())
			{
				TestTrue(FString::Printf(TEXT("%s: parts.%s.bone %s is a deform bone"), Gun, Part, *Bone), Bones->HasField(Bone));
			}
		}
	}
	// The parts: each one's mesh is the contract's asset, its sockets are the contract's (the data's centimetre offsets as
	// (x, -y, z) x 100), and the guns that list it are exactly the guns the contract says it applies to.
	const TSharedPtr<FJsonObject> ContractParts = MIJson::Get(F.Contract, TEXT("parts"))->AsObject();
	for (const auto& Pair : ContractParts->Values)
	{
		const FName Id(*FString(*Pair.Key));
		const TSharedPtr<FJsonObject> CP = Pair.Value->AsObject();
		const FMIAttachmentDef* P = F.D.FindPart(Id);
		if (!TestNotNull(Id.ToString() + TEXT(" is in attachments.json"), P))
		{
			continue;
		}
		TestEqual(Id.ToString() + TEXT(" mesh is the contract's asset"), P->Mesh, CP->GetStringField(TEXT("asset")));
		TestEqual(Id.ToString() + TEXT(" slot"), P->Slot, FName(*CP->GetStringField(TEXT("slot"))));
		const TSharedPtr<FJsonObject> CSockets = CP->GetObjectField(TEXT("sockets"));
		for (const TPair<FName, FName>& S : P->Sockets)
		{
			TestTrue(Id.ToString() + TEXT(": socket ") + S.Value.ToString() + TEXT(" is in the contract"), CSockets->HasField(S.Value.ToString()));
		}
		const TSharedPtr<FJsonValue> Offsets = MIJson::Get(F.D.AttachmentsJson, FString::Printf(TEXT("attachments.%s.presentation.socketOffsetsCm"), *Id.ToString()));
		if (Offsets.IsValid())
		{
			for (const auto& O : Offsets->AsObject()->Values)
			{
				const TSharedPtr<FJsonValue> S = CSockets->TryGetField(FString(*O.Key));
				if (TestTrue(Id.ToString() + TEXT(": offset of ") + FString(*O.Key) + TEXT(" is a contract socket"), S.IsValid()))
				{
					TestTrue(Id.ToString() + TEXT(": ") + FString(*O.Key) + TEXT(" offset is (x, -y, z) x 100 of the socket"), (Vec(O.Value) - CmOf(S)).Size() < 1e-4);
				}
			}
		}
		TArray<FName> Listing;
		for (const FName GunId : F.D.Roster)
		{
			const FMIGunEntry* G = F.D.FindGun(GunId);
			const FMICompatSlot* C = G ? G->FindCompat(P->Slot) : nullptr;
			if (C && C->Options.Contains(Id))
			{
				Listing.Add(GunId);
				TestEqual(Id.ToString() + TEXT(" on the ") + GunId.ToString() + TEXT(": the compatibility mount is the contract's gun socket"), C->Mount, FName(*CP->GetStringField(TEXT("gunSocket"))));
			}
		}
		TArray<FName> Applies;
		for (const TSharedPtr<FJsonValue>& A : CP->GetArrayField(TEXT("appliesTo"))) Applies.Add(FName(*A->AsString()));
		Listing.Sort(FNameLexicalLess());
		Applies.Sort(FNameLexicalLess());
		TestEqual(Id.ToString() + TEXT(": the guns that list it are the contract's appliesTo"), Listing, Applies);
		++Checks;
	}
	AddInfo(FString::Printf(TEXT("%d contract checks"), Checks));
	return !HasAnyErrors();
}

// ================================================================================================ the box

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMILoadoutPartsOnEveryGunTest, "MurderInc.Loadout.PartsOnEveryGun", MIWeaponsR4Private::Flags)

// On the box, with the art: every part a gun's row offers, fitted alone on the gun's own mesh, on both component types the
// game uses (the stage's skeletal mesh, the first-person gun's poseable mesh). The part loads, its mount exists, its frame
// is the gun's (the exported bones carry a quarter turn of the glTF axes: the assembly turns it back), an optic's
// SightEye lands where the contract says, the gun parts it replaces are really hidden, its bounds sit where its mesh puts
// them from the mount, no material is missing, and a magazine follows the 'magazine' bone.
bool FMILoadoutPartsOnEveryGunTest::RunTest(const FString& Parameters)
{
	using namespace MIWeaponsR4Private;
	FData F;
	if (!F.Load(*this))
	{
		return false;
	}
	const FMIAssetExists Exists = FMIReadiness::PackageExists();
	const FString ShortyAsset = MIJson::StringOr(F.Contract, TEXT("guns.shorty.asset"));
	if (!Exists(ShortyAsset) || !Exists(MIJson::StringOr(F.Contract, TEXT("parts.red_dot.asset"))))
	{
		AddInfo(TEXT("The own guns and parts are not imported here (a clean checkout, or the box before tools/box/fp/import-chars.sh r4): nothing to fit"));
		return true;
	}
	FMIReadiness Ready;
	Ready.Data = &F.D;
	Ready.AssetExists = Exists;
	const FMILoadoutResolver Resolver = F.Resolver();
	FStageWorld W;
	USkeletalMeshComponent* Skeletal = NewObject<USkeletalMeshComponent>(W.Owner);
	Skeletal->RegisterComponent();
	UPoseableMeshComponent* Poseable = NewObject<UPoseableMeshComponent>(W.Owner);
	Poseable->RegisterComponent();
	UMIGunAssembly* Assembly = NewObject<UMIGunAssembly>(W.Owner);
	Assembly->RegisterComponent();
	int32 Fitted = 0;
	for (const TCHAR* Gun : OwnGuns)
	{
		const FMIGunEntry* Entry = F.D.FindGun(Gun);
		if (!Entry)
		{
			continue;
		}
		const TSharedPtr<FJsonObject> CGun = MIJson::Get(F.Contract, FString::Printf(TEXT("guns.%s"), Gun))->AsObject();
		const TSharedPtr<FJsonObject> CSockets = CGun->GetObjectField(TEXT("sockets"));
		for (const FMICompatSlot& Slot : Entry->Compat)
		{
			for (const FName PartId : Ready.OfferedParts(Gun, Slot.Slot))
			{
				const FMIAttachmentDef* Part = F.D.FindPart(PartId);
				if (!Part || Part->bBaseline || Part->Mesh.IsEmpty())
				{
					continue;
				}
				FMIGunBuild Build;
				Build.Parts.Add(Slot.Slot, PartId);
				FMIResolvedGun G;
				FString Error;
				if (!Resolver.ResolveGun(Gun, &Build, &Ready, G, Error))
				{
					AddError(Error);
					continue;
				}
				USkeletalMesh* Mesh = Cast<USkeletalMesh>(FSoftObjectPath(G.BaseMesh).TryLoad());
				if (!TestNotNull(FString(Gun) + TEXT(": the mesh loads"), Mesh))
				{
					continue;
				}
				for (const bool bPoseable : {false, true})
				{
					USkinnedMeshComponent* Base = bPoseable ? static_cast<USkinnedMeshComponent*>(Poseable) : static_cast<USkinnedMeshComponent*>(Skeletal);
					Base->SetSkinnedAssetAndUpdate(Mesh, true);
					Assembly->Assemble(Base, G, false);
					const FString L = FString::Printf(TEXT("%s + %s (%s)"), Gun, *PartId.ToString(), bPoseable ? TEXT("poseable") : TEXT("skeletal"));
					UStaticMeshComponent* Mount = Assembly->PartMesh(Slot.Slot);
					if (!TestNotNull(L + TEXT(": the part is on the gun"), Mount))
					{
						continue;
					}
					++Fitted;
					const FName Socket = Slot.Mount;
					TestTrue(L + TEXT(": the mount ") + Socket.ToString() + TEXT(" exists"), Base->DoesSocketExist(Socket));
					// The part's frame is the gun's: no quarter turn left by the bone.
					const double Turn = FMath::RadiansToDegrees(Mount->GetComponentQuat().AngularDistance(Base->GetComponentQuat()));
					TestTrue(FString::Printf(TEXT("%s: the part's frame is the gun's (%.2f degrees off)"), *L, Turn), Turn < 0.5);
					// Where its own mesh puts its bounds from the mount (rest, no slide): the mount's place plus the mesh's bounds centre.
					const TSharedPtr<FJsonValue> MountValue = CSockets->TryGetField(Socket.ToString());
					if (!TestTrue(L + TEXT(": the mount is a contract socket"), MountValue.IsValid()))
					{
						continue;
					}
					const FVector MountCm = CmOf(MountValue);
					const UStaticMesh* PartMesh = Mount->GetStaticMesh();
					const FVector Want = MountCm + PartMesh->GetBounds().Origin;
					const double Off = FVector::Dist(Mount->Bounds.Origin, Want);
					TestTrue(FString::Printf(TEXT("%s: its bounds sit %.2f cm from where the mount puts them (within 1 mm)"), *L, Off), Off < 0.1);
					TestTrue(L + TEXT(": it has a size"), Mount->Bounds.SphereRadius > 0.5);
					for (int32 I = 0; I < Mount->GetNumMaterials(); ++I)
					{
						TestNotNull(FString::Printf(TEXT("%s: material slot %d is assigned"), *L, I), Mount->GetMaterial(I));
					}
					// An optic: the sight line starts where the contract puts the eye on that gun.
					if (Slot.Slot == TEXT("optic") && Mount->DoesSocketExist(TEXT("SightEye")))
					{
						const FVector Eye = Base->GetComponentTransform().InverseTransformPosition(Mount->GetSocketLocation(TEXT("SightEye")));
						const FVector Expect = MountCm + CmOf(MIJson::Get(F.Contract, FString::Printf(TEXT("parts.%s.sockets.SightEye"), *PartId.ToString())));
						// SightEye in the contract is metres in the part's frame; CmOf mirrors Y for the Unreal frame
						TestTrue(FString::Printf(TEXT("%s: SightEye at %s, the contract says %s (within 1 mm)"), *L, *Eye.ToCompactString(), *Expect.ToCompactString()), FVector::Dist(Eye, Expect) < 0.1);
					}
					// Every gun part this part replaces is really hidden on this component type.
					if (bPoseable)
					{
						Poseable->RefreshBoneTransforms();
					}
					for (const FName Hide : G.Parts.Num() > 0 ? G.Parts[0].Hide : TArray<FName>())
					{
						if (Base->GetBoneIndex(Hide) == INDEX_NONE)
						{
							AddError(L + TEXT(": the hidden bone ") + Hide.ToString() + TEXT(" is not on the mesh"));
							continue;
						}
						const bool bHidden = bPoseable ? Poseable->GetBoneTransformByName(Hide, EBoneSpaces::ComponentSpace).GetScale3D().GetMax() < 0.01 : Skeletal->IsBoneHiddenByName(Hide);
						TestTrue(L + TEXT(": the bone ") + Hide.ToString() + TEXT(" is hidden"), bHidden);
					}
					// A magazine follows the 'magazine' bone when it drops (a reload).
					if (Slot.Slot == TEXT("magazine") && bPoseable)
					{
						const FVector Before = Mount->GetComponentLocation();
						FTransform Moved = FAnimationRuntime::GetComponentSpaceTransformRefPose(Mesh->GetRefSkeleton(), Mesh->GetRefSkeleton().FindBoneIndex(TEXT("magazine")));
						Moved.AddToTranslation(FVector(0.0, 0.0, -10.0));
						Poseable->SetBoneTransformByName(TEXT("magazine"), Moved, EBoneSpaces::ComponentSpace);
						Poseable->RefreshBoneTransforms();
						const FVector After = Mount->GetComponentLocation();
						TestTrue(FString::Printf(TEXT("%s: the magazine follows its bone down 10 cm (moved %s)"), *L, *(After - Before).ToCompactString()), FVector::Dist(After - Before, FVector(0, 0, -10)) < 0.1);
						Poseable->ResetBoneTransformByName(TEXT("magazine"));
					}
					Assembly->Clear();
				}
			}
		}
	}
	AddInfo(FString::Printf(TEXT("%d part fittings checked on both component types"), Fitted));
	TestTrue(TEXT("parts were fitted"), Fitted > 0);
	return !HasAnyErrors();
}

// ================================================================================================ the arms' reach

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIFirstPersonArmReachTest, "MurderInc.FirstPerson.ArmReach", MIWeaponsR4Private::Flags)

bool FMIFirstPersonArmReachTest::RunTest(const FString& Parameters)
{
	using namespace MIWeaponsR4Private;
	FData F;
	if (!F.Load(*this))
	{
		return false;
	}
	// The support arm of each rifle may stretch up to 10 percent (ANIMATION.md 11); the pistol's proven hands never stretch.
	static const TCHAR* const Rifles[] = {TEXT("chopper"), TEXT("shorty"), TEXT("stretch"), TEXT("rattler")};
	for (const TCHAR* Gun : Rifles)
	{
		const FString Set = FString::Printf(TEXT("firstPerson.animSets.%s_ik"), Gun);
		const double Stretch = MIJson::NumberOr(F.Presentation, Set + TEXT(".armStretch"), 0.0);
		TestTrue(FString::Printf(TEXT("%s: armStretch %.2f is between 1.0 and 1.3 (the solve's clamp)"), Gun, Stretch), Stretch >= 1.0 && Stretch <= 1.3);
		const double Curl = MIJson::NumberOr(F.Presentation, Set + TEXT(".foregripCurl"), -1.0);
		TestTrue(FString::Printf(TEXT("%s: foregripCurl %.0f degrees is between 0 and 70"), Gun, Curl), Curl >= 0.0 && Curl <= 70.0);
		const double Reload = MIJson::NumberOr(F.Presentation, Set + TEXT(".reloadCurl"), -1.0);
		TestTrue(FString::Printf(TEXT("%s: reloadCurl %.0f degrees is between 0 and 70"), Gun, Reload), Reload >= 0.0 && Reload <= 70.0);
	}
	TestEqual(TEXT("the NINE's hands are not stretched"), MIJson::NumberOr(F.Presentation, TEXT("firstPerson.animSets.pistol.armStretch"), 1.0), 1.0);
	// The console variable is a force for comparison pictures: 0 means each arm's own value.
	if (IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(TEXT("mi.FP.ArmStretch")))
	{
		TestEqual(TEXT("mi.FP.ArmStretch defaults to 0 (each arm's own)"), Var->GetFloat(), 0.f);
	}
	else
	{
		AddError(TEXT("console variable mi.FP.ArmStretch is not registered"));
	}
	return !HasAnyErrors();
}


// ================================================================================================ the support hand (HANDS_R4.md 8)

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIFirstPersonSupportHandTest, "MurderInc.FirstPerson.SupportHand", MIWeaponsR4Private::Flags)

bool FMIFirstPersonSupportHandTest::RunTest(const FString& Parameters)
{
	using namespace MIWeaponsR4Private;
	FData F;
	if (!F.Load(*this))
	{
		return false;
	}
	TSharedPtr<FJsonObject> Grips;
	FString Error;
	if (!UMIDataSubsystem::LoadJsonFile(TEXT("grips.json"), Grips, Error))
	{
		AddError(TEXT("grips.json: ") + Error);
		return false;
	}
	static const TCHAR* const Rifles[] = {TEXT("chopper"), TEXT("shorty"), TEXT("stretch"), TEXT("rattler")};
	for (const TCHAR* Gun : Rifles)
	{
		const FString Set = FString::Printf(TEXT("firstPerson.animSets.%s_ik"), Gun);
		// 8.2: the support elbow's pole, camera space cm: out to the left (Y not right) and down (Z not up), within 40 cm.
		for (const TCHAR* Key : {TEXT(".supportElbowOut"), TEXT(".supportElbowOutAim")})
		{
			const TSharedPtr<FJsonValue> V = MIJson::Get(F.Presentation, Set + Key);
			if (!V.IsValid())
			{
				continue;
			}
			const bool bThree = V->Type == EJson::Array && V->AsArray().Num() == 3;
			TestTrue(FString::Printf(TEXT("%s%s is three numbers"), Gun, Key), bThree);
			if (bThree)
			{
				const FVector E = Vec(V);
				TestTrue(FString::Printf(TEXT("%s%s %s: within 40 cm, to the left and down"), Gun, Key, *E.ToCompactString()),
					E.GetAbsMax() <= 40.0 && E.Y <= 0.0 && E.Z <= 0.0);
			}
		}
		// 8.1: the carried grip closes the hand on the magazine; a curl on top would sink the fingers into it.
		const double Squeeze = MIJson::NumberOr(F.Presentation, Set + TEXT(".magazine.squeeze"), 1.0);
		TestTrue(FString::Printf(TEXT("%s: magazine.squeeze %.2f is 0.2 to 1"), Gun, Squeeze), Squeeze >= 0.2 && Squeeze <= 1.0);
		const double Blend = MIJson::NumberOr(F.Presentation, Set + TEXT(".magazine.blend"), 0.25);
		TestTrue(FString::Printf(TEXT("%s: magazine.blend %.2f s is 0.05 to 0.6"), Gun, Blend), Blend >= 0.05 && Blend <= 0.6);
		TestEqual(FString::Printf(TEXT("%s: reloadCurl is 0 (the carried grip holds the magazine)"), Gun), MIJson::NumberOr(F.Presentation, Set + TEXT(".reloadCurl"), -1.0), 0.0);
		// 8.3: the aimed solve blended by the aim has every point of the hip solve, and the support hand moves little.
		const FString Key = MIJson::StringOr(F.Presentation, Set + TEXT(".grip.gun"));
		const FString Hip = MIJson::StringOr(F.Presentation, Set + TEXT(".grip.pose"), TEXT("hip"));
		const FString Aim = MIJson::StringOr(F.Presentation, Set + TEXT(".grip.aimPose"), TEXT("aim"));
		const TSharedPtr<FJsonValue> H = MIJson::Get(Grips, FString::Printf(TEXT("guns.%s.%s.l"), *Key, *Hip));
		const TSharedPtr<FJsonValue> A = MIJson::Get(Grips, FString::Printf(TEXT("guns.%s.%s.l"), *Key, *Aim));
		if (!TestTrue(FString::Printf(TEXT("%s: grips.json has the support hand's %s and %s solves"), Gun, *Hip, *Aim),
			H.IsValid() && A.IsValid() && H->Type == EJson::Object && A->Type == EJson::Object))
		{
			continue;
		}
		double Worst = 0.0;
		int32 Points = 0;
		for (const auto& Pair : H->AsObject()->Values)
		{
			const TSharedPtr<FJsonValue>* Other = A->AsObject()->Values.Find(Pair.Key);
			if (Pair.Value->Type != EJson::Array || Pair.Value->AsArray().Num() != 3)
			{
				continue;
			}
			++Points;
			if (!TestTrue(FString::Printf(TEXT("%s: the aimed support solve has %s"), Gun, *FString(*Pair.Key)), Other && (*Other)->Type == EJson::Array && (*Other)->AsArray().Num() == 3))
			{
				continue;
			}
			Worst = FMath::Max(Worst, FVector::Dist(Vec(Pair.Value), Vec(*Other)));
		}
		TestTrue(FString::Printf(TEXT("%s: %d support points"), Gun, Points), Points >= 20);
		TestTrue(FString::Printf(TEXT("%s: the support hand moves %.2f cm from hip to aimed (at most 4: a blend, not a new grip)"), Gun, Worst), Worst <= 4.0);
	}
	return !HasAnyErrors();
}

#endif
