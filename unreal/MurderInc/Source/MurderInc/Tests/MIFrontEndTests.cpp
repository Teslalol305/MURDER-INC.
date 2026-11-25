// LOADOUT.md 8.5 and 8.6: a scripted walk through the whole set-up flow (rules only) and the saved set-up.

#include "Core/Data/MIDataSubsystem.h"
#include "Flow/MIFrontEndRules.h"
#include "Flow/MIRunSetupSubsystem.h"
#include "Flow/MISettings.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Misc/Paths.h"
#include "UI/MIFrontEnd.h"
#include "UI/MIStyle.h"
#include "UI/SMIMark.h"
#include "Weapons/MILoadoutResolver.h"
#include "Weapons/MIWeaponRules.h"

#if WITH_AUTOMATION_TESTS

namespace MIFrontEndTestsPrivate
{
	constexpr EAutomationTestFlags Flags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter;

	/** The data with every pack rifle ready, their mounts and variants built and their parts imported (test data:
	 *  the pack is not in a clean checkout). The parity guns' mounts stay as the data says (round 4: the CHOPPER's and
	 *  NINE's mounts exist now, with their own parts); the crew's looks stay missing. */
	struct FFixture
	{
		FMILoadoutData Data;
		TSharedPtr<FJsonObject> Config, Presentation, Text;
		FMIReadiness Ready;

		bool Load(FAutomationTestBase& T)
		{
			FString Error;
			if (!FMILoadoutData::Load(Data, Error) || !FMILoadoutResolver::LoadRoots(Config, Presentation, Error) || !UMIDataSubsystem::LoadJsonFile(TEXT("text.json"), Text, Error))
			{
				T.AddError(Error);
				return false;
			}
			for (TPair<FName, FMIGunEntry>& G : Data.Guns)
			{
				if (G.Value.bParity) continue;
				for (TPair<FName, FMIGunVariant>& V : G.Value.Variants)
				{
					V.Value.Status = TEXT("exists");
					if (V.Value.Mesh.IsEmpty()) V.Value.Mesh = FString::Printf(TEXT("/Game/Test/SK_%s_%s.SK_%s_%s"), *G.Key.ToString(), *V.Key.ToString(), *G.Key.ToString(), *V.Key.ToString());
				}
				for (TPair<FName, FMIGunMount>& M : G.Value.Mounts) M.Value.Status = TEXT("exists");
			}
			for (TPair<FName, FMIAttachmentDef>& P : Data.Attachments)
			{
				if (P.Value.Mesh.IsEmpty()) P.Value.Mesh = FString::Printf(TEXT("/Game/Test/SM_%s.SM_%s"), *P.Key.ToString(), *P.Key.ToString());
			}
			Ready.Data = &Data;
			Ready.AssetExists = [](const FString& Path) { return !Path.Contains(TEXT("/Characters/Crew/")); };
			return true;
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIFrontendWalkTest, "MurderInc.Frontend.Walk", MIFrontEndTestsPrivate::Flags)

bool FMIFrontendWalkTest::RunTest(const FString& Parameters)
{
	using namespace MIFrontEndTestsPrivate;
	FFixture F;
	if (!F.Load(*this))
	{
		return false;
	}
	const FMILoadoutResolver Resolver(F.Data, F.Config, F.Presentation);
	FMIFrontEndRules R;
	R.TextJson = F.Text;
	R.ConfigJson = F.Config;
	R.Init(&F.Data, F.Ready, &Resolver, F.Data.ParitySetup(TEXT("mission"), TEXT("boss"), TEXT("day")));

	// 1. Boot: Home; played is false, so Hit the block opens Crew, not a run.
	TestEqual(TEXT("boot on Home"), R.GetScreen(), EMIFrontScreen::Home);
	TestEqual(TEXT("first Hit the block: no run"), R.HitTheBlock(), EMIFrontRequest::None);
	TestEqual(TEXT("first Hit the block opens Crew"), R.GetScreen(), EMIFrontScreen::Crew);

	// 2. Crew: only Rule without the phase-1 materials. Next: Loadout with the CHOPPER and the NINE.
	TestEqual(TEXT("one crew card"), R.OfferedCrew(), TArray<FName>{TEXT("rule")});
	R.Next();
	TestEqual(TEXT("Loadout"), R.GetScreen(), EMIFrontScreen::Loadout);
	TestEqual(TEXT("parity guns"), R.GetSetup().Guns, TArray<FName>{TEXT("chopper"), TEXT("nine")});
	TestTrue(TEXT("the rack offers the pack rifles with the test data"), R.Rack().Contains(TEXT("stick")) && R.Rack().Contains(TEXT("stretch")) && R.Rack().Contains(TEXT("shorty")));
	// Round 4: the RATTLER has its mesh (and the template plays its Idle), so the rack offers it; without its mesh it is
	// hidden again (the box before the weapons import, a clean checkout).
	TestTrue(TEXT("the RATTLER is offered with its mesh"), R.Rack().Contains(TEXT("rattler")));
	{
		FMIReadiness NoRattler = F.Ready;
		NoRattler.AssetExists = [](const FString& Path) { return !Path.Contains(TEXT("/Game/Weapons/Rattler/")) && !Path.Contains(TEXT("/Characters/Crew/")); };
		TestFalse(TEXT("the RATTLER is hidden without its mesh"), NoRattler.IsGunOffered(TEXT("rattler")));
		TestTrue(TEXT("the others stay offered without it"), NoRattler.IsGunOffered(TEXT("shorty")) && NoRattler.IsGunOffered(TEXT("stretch")) && NoRattler.IsGunOffered(TEXT("stick")));
	}

	// 3. Carry the STICK and the STRETCH (slots 3, 4); a fifth carry asks for a slot.
	TestTrue(TEXT("carry STICK"), R.Carry(TEXT("stick")));
	TestTrue(TEXT("carry STRETCH"), R.Carry(TEXT("stretch")));
	TestEqual(TEXT("slots"), R.GetSetup().Guns, TArray<FName>{TEXT("chopper"), TEXT("nine"), TEXT("stick"), TEXT("stretch")});
	TestFalse(TEXT("a fifth carry is refused"), R.Carry(TEXT("shorty")));
	TestEqual(TEXT("it asks for a slot"), R.LastMessage, F.Data.Text(TEXT("frontend.loadout.full")));
	// Move slot 4 to 1 (they swap); empty slot 2 (the rest close up); right-click off a slot does nothing.
	R.SwapSlots(3, 0);
	TestEqual(TEXT("slot 4 to 1"), R.GetSetup().Guns[0], FName(TEXT("stretch")));
	R.EmptySlot(1);
	TestEqual(TEXT("slot 2 emptied, closed up"), R.GetSetup().Guns, TArray<FName>{TEXT("stretch"), TEXT("stick"), TEXT("chopper")});
	R.EmptySlot(7);
	TestEqual(TEXT("off a slot: nothing"), R.GetSetup().Guns.Num(), 3);

	// 4. Workbench on the STICK: scope, silencer, folded stock (the base mesh swaps).
	R.OpenWorkbench(TEXT("stick"));
	TestEqual(TEXT("Workbench"), R.GetScreen(), EMIFrontScreen::Workbench);
	TestTrue(TEXT("six slots on the STICK"), R.BenchSlots().Num() == 6);
	R.ChooseBenchSlot(TEXT("optic"));
	TestFalse(TEXT("optic required: no Factory"), R.BenchOptions(TEXT("optic")).Contains(NAME_None));
	R.Fit(TEXT("scope"));
	R.ChooseBenchSlot(TEXT("muzzle"));
	TestTrue(TEXT("muzzle has Factory"), R.BenchOptions(TEXT("muzzle")).Contains(NAME_None));
	R.Fit(TEXT("silencer"));
	R.ChooseBenchSlot(TEXT("stock"));
	const FString OpenMesh = F.Ready.BaseMesh(TEXT("stick"), R.GetSetup().BuildOf(TEXT("stick")));
	R.Fit(TEXT("stock_folded"));
	const FString FoldedMesh = F.Ready.BaseMesh(TEXT("stick"), R.GetSetup().BuildOf(TEXT("stick")));
	TestTrue(TEXT("the folded stock swaps the base mesh"), OpenMesh != FoldedMesh && FoldedMesh == F.Data.FindGun(TEXT("stick"))->Variants[TEXT("folded")].Mesh);
	// The effect lines carry their mark, and they come from the resolver.
	const TArray<FMIEffectLine> Lines = R.EffectLines(TEXT("stick"), TEXT("scope"));
	TestTrue(TEXT("scope effect lines"), Lines.Num() >= 4);
	for (const FMIEffectLine& L : Lines)
	{
		TestTrue(TEXT("line starts with a mark: ") + L.Text, L.Text.StartsWith(TEXT("▲")) || L.Text.StartsWith(TEXT("▼")) || L.Text.StartsWith(TEXT("•")));
	}
	TestTrue(TEXT("scope: aimed view line"), Lines.ContainsByPredicate([](const FMIEffectLine& L) { return L.Text.Contains(TEXT("30° (from 52°)")); }));
	TestTrue(TEXT("scope: -30% aimed spread"), Lines.ContainsByPredicate([](const FMIEffectLine& L) { return L.Sign > 0 && L.Text.Contains(TEXT("30% aimed spread")); }));
	{
		const FMIGunBuild* B = R.GetSetup().BuildOf(TEXT("stick"));
		FMIResolvedGun G;
		FString Error;
		Resolver.ResolveGun(TEXT("stick"), B, &F.Ready, G, Error);
		const FMIGunBars A = R.Bars(TEXT("stick"), B);
		const FMIGunBars Want = FMIGunBars::Of(G, 110.0);
		TestTrue(TEXT("bars equal the resolver's"), A.Aimed == Want.Aimed && A.Handling == Want.Handling && A.Control == Want.Control && A.Kill == Want.Kill);
	}
	// A tap of R does nothing; a 0.6 s hold resets.
	R.HoldReset(0.1, true);
	R.HoldReset(0.0, false);
	TestEqual(TEXT("a tap keeps the build"), R.GetSetup().PartIn(TEXT("stick"), TEXT("optic")), FName(TEXT("scope")));
	bool bReset = false;
	for (int32 I = 0; I < 36 && !bReset; ++I) bReset = R.HoldReset(1.0 / 60.0, true);
	TestTrue(TEXT("a 0.6 s hold resets"), bReset);
	TestEqual(TEXT("reset: the irons back"), R.GetSetup().PartIn(TEXT("stick"), TEXT("optic")), FName(TEXT("irons")));
	TestEqual(TEXT("reset: no silencer"), R.GetSetup().PartIn(TEXT("stick"), TEXT("muzzle")), NAME_None);
	R.ChooseBenchSlot(TEXT("optic"));
	R.Fit(TEXT("scope"));
	// [ / ] to the CHOPPER: its mounts exist since round 4 (SK_Chopper carries Optic, MuzzleMount and Underbarrel).
	R.BenchNextGun(1);
	TestEqual(TEXT("] reaches the CHOPPER"), R.GetBenchGun(), FName(TEXT("chopper")));
	TestEqual(TEXT("CHOPPER: optic, muzzle, underbarrel"), R.BenchSlots(), TArray<FName>{TEXT("optic"), TEXT("muzzle"), TEXT("underbarrel")});
	R.BenchNextGun(1);
	TestEqual(TEXT("] wraps to the STRETCH"), R.GetBenchGun(), FName(TEXT("stretch")));
	// The STRETCH is our own marksman rifle: no laser slot, no stock slot, and its own parts.
	TestEqual(TEXT("STRETCH: optic, muzzle, underbarrel, magazine"), R.BenchSlots(), TArray<FName>{TEXT("optic"), TEXT("muzzle"), TEXT("underbarrel"), TEXT("magazine")});
	TestEqual(TEXT("STRETCH optics"), F.Ready.OfferedParts(TEXT("stretch"), TEXT("optic")), TArray<FName>{TEXT("scope_4x"), TEXT("red_dot")});
	TestEqual(TEXT("STRETCH muzzle devices"), F.Ready.OfferedParts(TEXT("stretch"), TEXT("muzzle")), TArray<FName>{TEXT("suppressor")});
	TestEqual(TEXT("STRETCH grips"), F.Ready.OfferedParts(TEXT("stretch"), TEXT("underbarrel")), TArray<FName>{TEXT("foregrip_vertical"), TEXT("foregrip_angled")});
	TestEqual(TEXT("STRETCH magazines"), F.Ready.OfferedParts(TEXT("stretch"), TEXT("magazine")), TArray<FName>{TEXT("mag_ext_rifle")});
	R.ChooseBenchSlot(TEXT("optic"));
	R.Fit(TEXT("scope_4x"));
	R.Next();  // Done
	TestEqual(TEXT("Done: back on the rack"), R.GetScreen(), EMIFrontScreen::Loadout);

	// 5. Block & Style: night, Hold the Block, Kingpin. Next: the Briefing.
	R.Next();
	TestEqual(TEXT("Block & Style"), R.GetScreen(), EMIFrontScreen::Where);
	R.SetTime(TEXT("night"));
	R.SetMode(TEXT("holdout"));
	R.SetDifficulty(TEXT("kingpin"));
	R.Next();
	TestEqual(TEXT("Briefing"), R.GetScreen(), EMIFrontScreen::Briefing);
	TestTrue(TEXT("remembered on Next"), R.ConsumeRemember());

	// 6. Change on Carrying: Loadout in edit mode; Done returns to the Briefing. Ctrl+Enter from Crew: the Briefing.
	R.Edit(EMIFrontScreen::Loadout);
	TestTrue(TEXT("edit mode"), R.IsEditMode());
	R.Next();
	TestEqual(TEXT("Done: the Briefing"), R.GetScreen(), EMIFrontScreen::Briefing);
	R.GoToStep(1);
	TestEqual(TEXT("step bullet: Crew"), R.GetScreen(), EMIFrontScreen::Crew);
	TestTrue(TEXT("Ctrl+Enter"), R.ToBriefing());
	TestEqual(TEXT("Ctrl+Enter: the Briefing"), R.GetScreen(), EMIFrontScreen::Briefing);

	// 7. Hit the block: slot 1 is the STRETCH, four... three slots and one bag of 150, the STRETCH aims at 30 degrees.
	TestEqual(TEXT("Hit the block starts"), R.Next(), EMIFrontRequest::StartRun);
	FMIResolvedRun Run;
	FString Error;
	TestTrue(TEXT("the set-up resolves"), Resolver.Resolve(R.GetSetup(), &F.Ready, Run, Error));
	if (Run.Guns.Num() == 3)
	{
		TestEqual(TEXT("slot 1 is the STRETCH"), Run.Guns[0].Id, FName(TEXT("stretch")));
		TestEqual(TEXT("STRETCH aimed view 30"), Run.Weapons.Guns[0].AdsFov, 30.0);
		FMIWeaponRules Rules;
		Rules.Init(Run.Weapons, 1, nullptr);
		TestEqual(TEXT("one bag of 150"), Rules.GetBag(), 150.0);
		TestEqual(TEXT("three slots"), Rules.NumGuns(), 3);
		TestFalse(TEXT("every gun starts in fireModes[0] (auto)"), Rules.IsSemi(0) || Rules.IsSemi(1) || Rules.IsSemi(2));
	}

	// 8. After a death: Change set-up opens the Briefing; Back to title: Home with Night in the summary; Hit the
	//    block (now played) starts at once with the identical set-up.
	const FMIRunSetup Before = R.GetSetup();
	R.OpenBriefing();
	TestEqual(TEXT("Change set-up: the Briefing"), R.GetScreen(), EMIFrontScreen::Briefing);
	R.OpenHome();
	TestTrue(TEXT("summary with Night"), R.Summary().Contains(TEXT("Night")));
	TestEqual(TEXT("played: Hit the block starts at once"), R.HitTheBlock(), EMIFrontRequest::StartRun);
	TestTrue(TEXT("identical set-up"), R.GetSetup().SameLoadout(Before));
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMISaveSetupRoundTripTest, "MurderInc.Save.SetupRoundTrip", MIFrontEndTestsPrivate::Flags)

bool FMISaveSetupRoundTripTest::RunTest(const FString& Parameters)
{
	FMIRunSetup S;
	S.Crew = TEXT("rule");
	S.Guns = {TEXT("stretch"), TEXT("stick"), TEXT("chopper")};
	S.Builds.Add(TEXT("stick")).Parts = {{TEXT("optic"), TEXT("scope")}, {TEXT("stock"), TEXT("stock_folded")}};
	S.Builds.Add(TEXT("shorty")).Parts = {{TEXT("muzzle"), TEXT("silencer")}};
	S.Level = TEXT("block");
	S.Seen = {TEXT("stick"), TEXT("scope")};
	S.bPlayed = true;
	UMISaveGame* Save = Cast<UMISaveGame>(UGameplayStatics::CreateSaveGameObject(UMISaveGame::StaticClass()));
	UMIRunSetupSubsystem::ToSave(S, Save->Setup);
	const FString Slot = TEXT("MurderIncTest");
	TestTrue(TEXT("written"), UGameplayStatics::SaveGameToSlot(Save, Slot, 0));
	const UMISaveGame* Back = Cast<UMISaveGame>(UGameplayStatics::LoadGameFromSlot(Slot, 0));
	if (!TestNotNull(TEXT("read back"), Back))
	{
		return false;
	}
	FMIRunSetup R;
	UMIRunSetupSubsystem::FromSave(Back->Setup, R);
	R.Mode = S.Mode;
	R.Difficulty = S.Difficulty;
	R.Time = S.Time;
	TestTrue(TEXT("same loadout"), R.SameLoadout(S));
	TestEqual(TEXT("builds kept for every gun ever built"), R.Builds.Num(), 2);
	TestEqual(TEXT("seen"), R.Seen, S.Seen);
	TestTrue(TEXT("played"), R.bPlayed);
	UGameplayStatics::DeleteGameInSlot(Slot, 0);
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMISaveSetupValidationTest, "MurderInc.Save.SetupValidation", MIFrontEndTestsPrivate::Flags)

bool FMISaveSetupValidationTest::RunTest(const FString& Parameters)
{
	using namespace MIFrontEndTestsPrivate;
	FFixture F;
	if (!F.Load(*this))
	{
		return false;
	}
	// 1. An unknown or unoffered crew member -> rule; an unknown level -> block.
	FMIRunSetup S = F.Data.ParitySetup(TEXT("mission"), TEXT("boss"), TEXT("day"));
	S.Crew = TEXT("deuce");  // its phase-1 materials do not exist
	S.Level = TEXT("moon");
	F.Ready.Validate(S);
	TestEqual(TEXT("unoffered crew -> rule"), S.Crew, FName(TEXT("rule")));
	TestEqual(TEXT("unknown level -> block"), S.Level, FName(TEXT("block")));
	// 2. Unknown or unoffered guns dropped; none left -> the parity guns.
	S.Guns = {TEXT("bazooka")};
	F.Ready.Validate(S);
	TestEqual(TEXT("none left: the parity guns"), S.Guns, F.Data.ParityGuns);
	{
		// The RATTLER is offered once its mesh exists (round 4); a saved RATTLER whose mesh is gone degrades the same way.
		FMIReadiness NoRattler = F.Ready;
		NoRattler.AssetExists = [](const FString& Path) { return !Path.Contains(TEXT("/Game/Weapons/Rattler/")) && !Path.Contains(TEXT("/Characters/Crew/")); };
		FMIRunSetup G = F.Data.ParitySetup(TEXT("mission"), TEXT("boss"), TEXT("day"));
		G.Guns = {TEXT("rattler")};
		NoRattler.Validate(G);
		TestEqual(TEXT("a RATTLER without its mesh: the parity guns"), G.Guns, F.Data.ParityGuns);
		G.Guns = {TEXT("rattler")};
		F.Ready.Validate(G);
		TestEqual(TEXT("a RATTLER with its mesh is kept"), G.Guns, TArray<FName>{TEXT("rattler")});
	}
	// 3. Parts not in the gun's options or not offered are dropped; a required slot takes its default.
	S.Guns = {TEXT("nine"), TEXT("stick")};
	S.Builds.Add(TEXT("nine")).Parts = {{TEXT("muzzle"), TEXT("silencer")}, {TEXT("laser"), TEXT("laser")}};
	S.Builds.Add(TEXT("stick")).Parts = {{TEXT("optic"), TEXT("silencer")}};
	F.Ready.Validate(S);
	TestEqual(TEXT("a part that does not fit is dropped"), S.PartIn(TEXT("nine"), TEXT("muzzle")), NAME_None);
	TestEqual(TEXT("a pack part the NINE does not take is dropped"), S.PartIn(TEXT("nine"), TEXT("laser")), NAME_None);
	TestEqual(TEXT("a required slot takes its default"), S.PartIn(TEXT("stick"), TEXT("optic")), FName(TEXT("irons")));
	// The NINE's own parts (round 4): kept while the mount and the part's mesh exist, dropped when either is gone.
	{
		FMIRunSetup N = F.Data.ParitySetup(TEXT("mission"), TEXT("boss"), TEXT("day"));
		N.Builds.Add(TEXT("nine")).Parts = {{TEXT("muzzle"), TEXT("suppressor_pistol")}, {TEXT("laser"), TEXT("laser_module")}};
		F.Ready.Validate(N);
		TestEqual(TEXT("the NINE's pistol suppressor is kept"), N.PartIn(TEXT("nine"), TEXT("muzzle")), FName(TEXT("suppressor_pistol")));
		TestEqual(TEXT("the NINE's laser module is kept"), N.PartIn(TEXT("nine"), TEXT("laser")), FName(TEXT("laser_module")));
		FMIReadiness NoParts = F.Ready;
		NoParts.AssetExists = [](const FString& Path) { return !Path.Contains(TEXT("/Game/Weapons/Parts/")) && !Path.Contains(TEXT("/Characters/Crew/")); };
		N.Builds.Add(TEXT("nine")).Parts = {{TEXT("muzzle"), TEXT("suppressor_pistol")}};
		NoParts.Validate(N);
		TestEqual(TEXT("a part whose mesh is missing is dropped"), N.PartIn(TEXT("nine"), TEXT("muzzle")), NAME_None);
		// A mount that is missing: the part is dropped for that reason alone.
		FMIGunEntry* Nine = F.Data.Guns.Find(TEXT("nine"));
		FMIGunMount* LaserMount = Nine ? Nine->Mounts.Find(TEXT("laser")) : nullptr;
		if (TestNotNull(TEXT("the NINE has a laser mount"), LaserMount))
		{
			const FName Was = LaserMount->Status;
			LaserMount->Status = TEXT("missing");
			N.Builds.Add(TEXT("nine")).Parts = {{TEXT("laser"), TEXT("laser_module")}};
			F.Ready.Validate(N);
			TestEqual(TEXT("a part whose mount is missing is dropped"), N.PartIn(TEXT("nine"), TEXT("laser")), NAME_None);
			LaserMount->Status = Was;
		}
	}
	// 4. Duplicates and gaps removed, cut to four.
	S.Guns = {TEXT("stick"), NAME_None, TEXT("stick"), TEXT("chopper"), TEXT("nine"), TEXT("shorty"), TEXT("stretch")};
	F.Ready.Validate(S);
	TestEqual(TEXT("no duplicates or gaps, at most four"), S.Guns, TArray<FName>{TEXT("stick"), TEXT("chopper"), TEXT("nine"), TEXT("shorty")});
	// 5. A mode the level does not provide -> its first mode.
	S.Mode = TEXT("racing");
	F.Ready.Validate(S);
	TestEqual(TEXT("unknown mode -> the level's first"), S.Mode, FName(TEXT("mission")));
	// In a clean checkout (no pack on disk) the pack rifles are not offered: a saved STICK degrades to the parity guns.
	FMIReadiness Clean;
	Clean.Data = &F.Data;
	Clean.AssetExists = [](const FString&) { return false; };
	FMIRunSetup C = F.Data.ParitySetup(TEXT("mission"), TEXT("boss"), TEXT("day"));
	C.Guns = {TEXT("stick")};
	Clean.Validate(C);
	TestEqual(TEXT("clean checkout: the parity guns"), C.Guns, F.Data.ParityGuns);
	return !HasAnyErrors();
}

// LOADOUT.md 2.6 and 2.11: every character the set-up screens draw from frontend_text.json and text.json is in a face in
// use or in the symbol face behind it (an empty box otherwise), read from the fonts' own character maps.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIFrontendGlyphsTest, "MurderInc.Frontend.Glyphs", MIFrontEndTestsPrivate::Flags)

bool FMIFrontendGlyphsTest::RunTest(const FString& Parameters)
{
	for (const FString& File : MIStyle::FaceFiles())
	{
		TestTrue(TEXT("the character map of ") + FPaths::GetCleanFilename(File) + TEXT(" reads"), MIStyle::FontHasGlyphs(File));
	}
	TestTrue(TEXT("the symbol face reads: ") + FPaths::GetCleanFilename(MIStyle::SymbolFontFile()), MIStyle::FontHasGlyphs(MIStyle::SymbolFontFile()));
	TArray<FString> Drawn;
	for (const TCHAR* Name : {TEXT("frontend_text.json"), TEXT("text.json")})
	{
		TSharedPtr<FJsonObject> Root;
		FString Error;
		if (TestTrue(FString::Printf(TEXT("%s loads"), Name), UMIDataSubsystem::LoadJsonFile(Name, Root, Error)))
		{
			UMIFrontEnd::CollectDrawnText(Root, Drawn);
		}
	}
	TestTrue(TEXT("strings to draw"), Drawn.Num() > 100);
	const FString Missing = MIStyle::MissingGlyphs(FString::Join(Drawn, TEXT("")));
	FString Codes;
	for (const TCHAR C : Missing) Codes += FString::Printf(TEXT(" U+%04X"), static_cast<int32>(C));
	TestTrue(TEXT("every drawn character has a glyph; missing:") + Codes, Missing.IsEmpty());
	// The marks the rules put on effect lines (better, worse, neutral) are drawn as shapes, never as characters.
	TestEqual(TEXT("a mark is a shape"), static_cast<int32>(SMIMark::ForSign(1)), static_cast<int32>(SMIMark::EKind::Up));
	return !HasAnyErrors();
}

#endif
