// LOADOUT.md 8.2: the attachment effects, resolved on the gun's JSON before parsing.

#include "Core/Data/MIDataSubsystem.h"
#include "Core/Data/MILoadoutData.h"
#include "Core/MIMath.h"
#include "Misc/AutomationTest.h"
#include "Weapons/MILoadoutResolver.h"
#include "Weapons/MIWeaponRules.h"
#include <limits>

#if WITH_AUTOMATION_TESTS

namespace MIAttachmentsPrivate
{
	constexpr EAutomationTestFlags Flags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter;

	struct FWorld
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
		FMILoadoutResolver Resolver() const { return FMILoadoutResolver(Data, Config, Presentation); }

		/** The first roster gun whose compatibility row takes the part (mounts ignored). */
		FName GunFor(FName Part) const
		{
			const FMIAttachmentDef* P = Data.FindPart(Part);
			for (const FName G : Data.Roster)
			{
				const FMICompatSlot* C = P ? Data.FindGun(G)->FindCompat(P->Slot) : nullptr;
				if (C && C->Options.Contains(Part)) return G;
			}
			return NAME_None;
		}
	};

	/** A target path's value in the parsed gun, in the parsed unit, or false when the parser has no such field. */
	bool Parsed(const FMIResolvedGun& G, const FString& Path, double& Out, double& Scale)
	{
		const FMIWeaponDef& D = G.Def;
		const double Deg = 180.0 / UE_DOUBLE_PI;
		struct FRow { const TCHAR* Path; double Value; double Scale; };
		const FRow Rows[] = {
			{TEXT("rules.adsTime"), D.AdsTime, 1.0},
			{TEXT("extra.adsFov"), D.AdsFov, 1.0},
			{TEXT("extra.adsLook"), D.AdsLook, 1.0},
			{TEXT("rules.spread.hip"), D.Spread.Hip, Deg},
			{TEXT("rules.spread.moveHip"), D.Spread.MoveHip, Deg},
			{TEXT("rules.spread.ads"), D.Spread.Ads, Deg},
			{TEXT("rules.spread.moveAds"), D.Spread.MoveAds, Deg},
			{TEXT("rules.recoil.pitch"), D.Recoil.Pitch, Deg},
			{TEXT("rules.recoil.shake"), D.Recoil.Shake, 1.0},
			{TEXT("rules.recoil.yaw"), D.Recoil.Yaw, Deg},
			{TEXT("rules.recoil.yawEarly"), D.Recoil.YawEarly, Deg},
			{TEXT("rules.recoil.weaveAmp"), D.Recoil.WeaveAmp, Deg},
			{TEXT("rules.recoil.weaveRandom"), D.Recoil.WeaveRandom, Deg},
			{TEXT("rules.kick.rise"), G.View.KickRise, 1.0},
			{TEXT("rules.kick.back"), G.View.KickBack, 1.0},
			{TEXT("rules.kick.yaw"), G.View.KickYaw, 1.0},
			{TEXT("rules.kick.roll"), G.View.KickRoll, 1.0},
			{TEXT("extra.holster"), D.Holster, 1.0},
			{TEXT("extra.draw"), D.Draw, 1.0},
			{TEXT("extra.noise"), D.NoiseRadius, 100.0},
			{TEXT("rules.flash.scale"), D.FlashScale, 1.0},
			{TEXT("rules.flash.light"), D.FlashLight, 1.0},
			{TEXT("extra.falloff.start"), D.FalloffStart, 100.0},
			{TEXT("extra.falloff.end"), D.FalloffEnd, 100.0},
			{TEXT("extra.falloff.min"), D.FalloffMin, 1.0},
			{TEXT("rules.wallPull[0]"), D.WallStart, 100.0},
			{TEXT("rules.wallPull[1]"), D.WallFull, 100.0},
			{TEXT("rules.swayMax"), G.View.SwayMax, 1.0},
			{TEXT("rules.magSize"), static_cast<double>(D.MagSize), 1.0},
		};
		for (const FRow& R : Rows)
		{
			if (Path == R.Path) { Out = R.Value; Scale = R.Scale; return true; }
		}
		return false;
	}

	bool Close(double A, double B, double Rel)
	{
		if (A == B) return true;
		return FMath::Abs(A - B) <= Rel * FMath::Max(FMath::Abs(A), FMath::Abs(B));
	}
}

/** Attachments.<part>.<stat>: one case per effect of every part, plus one per baseline part (no change). */
IMPLEMENT_COMPLEX_AUTOMATION_TEST(FMIAttachmentsEffectTest, "MurderInc.Attachments", MIAttachmentsPrivate::Flags)

void FMIAttachmentsEffectTest::GetTests(TArray<FString>& OutBeautifiedNames, TArray<FString>& OutTestCommands) const
	{
		MIAttachmentsPrivate::FWorld W;
		FString Error;
		if (!FMILoadoutData::Load(W.Data, Error))
		{
			return;
		}
		TArray<FName> Parts;
		W.Data.Attachments.GetKeys(Parts);
		Parts.Sort(FNameLexicalLess());
		for (const FName Id : Parts)
		{
			const FMIAttachmentDef& P = W.Data.Attachments[Id];
			if (P.bBaseline)
			{
				OutBeautifiedNames.Add(Id.ToString() + TEXT(".Baseline"));
				OutTestCommands.Add(Id.ToString() + TEXT(" baseline"));
				continue;
			}
			for (const FMIEffect& E : P.Effects)
			{
				OutBeautifiedNames.Add(Id.ToString() + TEXT(".") + E.Stat.ToString());
				OutTestCommands.Add(Id.ToString() + TEXT(" ") + E.Stat.ToString());
			}
		}
}

bool FMIAttachmentsEffectTest::RunTest(const FString& Parameters)
{
	{
		using namespace MIAttachmentsPrivate;
		FWorld W;
		if (!W.Load(*this))
		{
			return false;
		}
		FString PartText, StatText;
		Parameters.Split(TEXT(" "), &PartText, &StatText);
		const FName PartId(*PartText);
		const FMIAttachmentDef* Part = W.Data.FindPart(PartId);
		const FName GunId = W.GunFor(PartId);
		if (!Part || GunId.IsNone())
		{
			AddError(FString::Printf(TEXT("no gun takes %s"), *PartText));
			return false;
		}
		const FMILoadoutResolver Resolver = W.Resolver();
		FMIResolvedGun Bare, Fitted;
		FMIGunBuild Build;
		Build.Parts.Add(Part->Slot, PartId);
		FString Error;
		if (!Resolver.ResolveGun(GunId, nullptr, nullptr, Bare, Error) || !Resolver.ResolveGun(GunId, &Build, nullptr, Fitted, Error))
		{
			AddError(Error);
			return false;
		}
		if (StatText == TEXT("baseline"))
		{
			TestEqual(TEXT("a baseline part leaves the rules JSON untouched"), MIJson::Print(Fitted.Rules), MIJson::Print(Bare.Rules));
			TestEqual(TEXT("and the extra JSON"), MIJson::Print(Fitted.Extra), MIJson::Print(Bare.Extra));
			return !HasAnyErrors();
		}
		const FMIStatDef* Stat = W.Data.Stats.Find(FName(*StatText));
		const FMIEffect* Effect = Part->Effects.FindByPredicate([&StatText](const FMIEffect& E) { return E.Stat == FName(*StatText); });
		if (!Stat || !Effect)
		{
			AddError(TEXT("unknown stat ") + StatText);
			return false;
		}
		int32 Checked = 0;
		const bool bMulti = Stat->Targets.Num() > 1 || Stat->Targets[0].Path.EndsWith(TEXT("*"));
		for (const FMIStatTarget& T : Stat->Targets)
		{
			if (T.Path.EndsWith(TEXT(".*")))
			{
				// Every reload number x the factor, exactly, with no clamp.
				const double F = FMath::Clamp(Effect->Value, W.Data.FactorMin, W.Data.FactorMax);
				TestTrue(TEXT("reload tactical"), Close(Fitted.Def.Reload.Tactical, Bare.Def.Reload.Tactical * F, 1e-12));
				TestTrue(TEXT("reload empty"), Close(Fitted.Def.Reload.Empty, Bare.Def.Reload.Empty * F, 1e-12));
				TestTrue(TEXT("magOut"), Close(Fitted.Def.Reload.MagOut, Bare.Def.Reload.MagOut * F, 1e-12));
				TestTrue(TEXT("magIn"), Close(Fitted.Def.Reload.MagIn, Bare.Def.Reload.MagIn * F, 1e-12));
				for (const TPair<FName, double>& M : Bare.View.ReloadMarks)
				{
					const double* Got = Fitted.View.ReloadMarks.Find(M.Key);
					TestTrue(FString::Printf(TEXT("view mark %s"), *M.Key.ToString()), Got && Close(*Got, M.Value * F, 1e-12));
				}
				++Checked;
				continue;
			}
			double BaseJson = 0.0;
			TSharedPtr<FJsonObject> BareDoc = MakeShared<FJsonObject>();
			BareDoc->SetObjectField(TEXT("rules"), Bare.Rules);
			BareDoc->SetObjectField(TEXT("extra"), Bare.Extra);
			if (!MIJson::Number(MIJson::Get(BareDoc, T.Path), BaseJson))
			{
				continue;  // a target the gun lacks is skipped
			}
			double Expected = BaseJson;
			if (bMulti)
			{
				Expected = BaseJson * FMath::Clamp(Effect->Value, W.Data.FactorMin, W.Data.FactorMax);
			}
			else if (Effect->Op == TEXT("mul")) Expected = BaseJson * Effect->Value;
			else if (Effect->Op == TEXT("set")) Expected = Effect->Value;
			else if (Effect->Op == TEXT("add")) Expected = BaseJson + Effect->Value;
			else if (Effect->Op == TEXT("min")) Expected = FMath::Min(BaseJson, Effect->Value);
			else if (Effect->Op == TEXT("max")) Expected = FMath::Max(BaseJson, Effect->Value);
			if (T.bClamp) Expected = FMath::Clamp(Expected, T.Min, T.Max);
			if (T.Path == TEXT("extra.falloff.end"))
			{
				double Start = 0.0;
				TSharedPtr<FJsonObject> FitDoc = MakeShared<FJsonObject>();
				FitDoc->SetObjectField(TEXT("extra"), Fitted.Extra);
				MIJson::Number(MIJson::Get(FitDoc, TEXT("extra.falloff.start")), Start);
				Expected = FMath::Max(Expected, Start);
			}
			double Value = 0.0, Scale = 1.0;
			if (Parsed(Fitted, T.Path, Value, Scale))
			{
				TestTrue(FString::Printf(TEXT("%s on the %s: %s = %.12g x %g"), *PartText, *GunId.ToString(), *T.Path, Expected * Scale, 1.0),
					Close(Value, Expected * Scale, 1e-12));
				if (!Close(Value, Expected * Scale, 1e-12))
				{
					AddError(FString::Printf(TEXT("%s: got %.15g, expected %.15g"), *T.Path, Value, Expected * Scale));
				}
				++Checked;
			}
			else
			{
				AddError(FString::Printf(TEXT("%s: the test has no parsed field for this target"), *T.Path));
			}
		}
		TestTrue(TEXT("at least one target checked"), Checked > 0);
		return !HasAnyErrors();
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAttachmentsBuildsTest, "MurderInc.Attachments.Builds", MIAttachmentsPrivate::Flags)

bool FMIAttachmentsBuildsTest::RunTest(const FString& Parameters)
{
	using namespace MIAttachmentsPrivate;
	FWorld W;
	if (!W.Load(*this))
	{
		return false;
	}
	const FMILoadoutResolver Resolver = W.Resolver();
	struct FCase
	{
		const TCHAR* Name;
		FName Gun;
		TArray<TPair<FName, FName>> Parts;
		double Aim, Kick, Aimed, Hip, Heard, Holster, Draw;
		double Fov = 52.0;
		double FalloffMinDamage = -1.0;  // damage past the falloff end, when any
		int32 MagSize = -1;              // rounds in the magazine, when the case says (an integer: the parser truncates)
		double Reload = -1.0, MagOut = -1.0;  // tactical reload seconds and the magazine-out mark, when the case says
	};
	const auto P = [](const TCHAR* Slot, const TCHAR* Part) { return TPair<FName, FName>(FName(Slot), FName(Part)); };
	const TArray<FCase> Cases = {
		{TEXT("STICK factory"), TEXT("stick"), {}, 0.20, 0.0051, 0.0009, 0.012, 45, 0.28, 0.32},
		{TEXT("STICK scope"), TEXT("stick"), {P(TEXT("optic"), TEXT("scope"))}, 0.27, 0.0051, 0.00063, 0.012, 45, 0.28, 0.32, 30.0},
		{TEXT("STICK close"), TEXT("stick"), {P(TEXT("stock"), TEXT("stock_folded")), P(TEXT("underbarrel"), TEXT("grip_angled")), P(TEXT("laser"), TEXT("laser")), P(TEXT("magazine"), TEXT("mag_clear"))},
			0.16524, 0.00611021, 0.0012375, 0.00912, 45, 0.243443, 0.278221},
		{TEXT("STRETCH long and quiet"), TEXT("stretch"), {P(TEXT("optic"), TEXT("scope")), P(TEXT("underbarrel"), TEXT("grip_vertical")), P(TEXT("muzzle"), TEXT("silencer"))},
			0.346421, 0.0039292, 0.000539, 0.012, 18, 0.3339, 0.38955, 30.0, 21.25},
		{TEXT("SHORTY silencer"), TEXT("shorty"), {P(TEXT("muzzle"), TEXT("silencer"))}, 0.1944, 0.00532, 0.00104, 0.012, 20, 0.2756, 0.3074, 52.0, 14.28},
		{TEXT("CHOPPER scope and silencer"), TEXT("chopper"), {P(TEXT("optic"), TEXT("scope")), P(TEXT("muzzle"), TEXT("silencer"))}, 0.26244, 0.00646, 0.00084, 0.0125, 18, 0.2968, 0.3392, 30.0, 22.1},
		// Round 4: our own parts on our own guns (docs/unreal/WEAPONS_R4_TESTS.md section 2, worked out from the data by
		// tools/data/check_guns_data.py's resolver, which first reproduced the six cases above to 5e-6).
		{TEXT("CHOPPER red dot, suppressor"), TEXT("chopper"), {P(TEXT("optic"), TEXT("red_dot")), P(TEXT("muzzle"), TEXT("suppressor"))},
			0.178848, 0.00646, 0.001296, 0.0125, 18, 0.31164, 0.35616, 52.0, 22.1},
		{TEXT("CHOPPER compensator, wooden grip"), TEXT("chopper"), {P(TEXT("muzzle"), TEXT("compensator")), P(TEXT("underbarrel"), TEXT("foregrip_vertical_wood"))},
			0.202176, 0.00526592, 0.0012, 0.0125, 51.75, 0.294, 0.336, 52.0, -1.0},
		{TEXT("SHORTY carry"), TEXT("shorty"), {P(TEXT("muzzle"), TEXT("compensator")), P(TEXT("underbarrel"), TEXT("foregrip_angled")), P(TEXT("laser"), TEXT("laser_module")), P(TEXT("magazine"), TEXT("mag_ext_rifle"))},
			0.189237, 0.00473088, 0.001144, 0.0096, 57.5, 0.269724, 0.300846, 52.0, 16.8, 45, 2.3856, 0.4256},
		{TEXT("STRETCH marksman"), TEXT("stretch"), {P(TEXT("optic"), TEXT("scope_4x")), P(TEXT("underbarrel"), TEXT("foregrip_vertical")), P(TEXT("muzzle"), TEXT("suppressor")), P(TEXT("magazine"), TEXT("mag_ext_rifle"))},
			0.360278, 0.0039292, 0.000539, 0.012, 18, 0.350595, 0.409028, 30.0, 21.25, 45, 2.3856, 0.4256},
		{TEXT("RATTLER close"), TEXT("rattler"), {P(TEXT("optic"), TEXT("red_dot")), P(TEXT("muzzle"), TEXT("compensator")), P(TEXT("magazine"), TEXT("mag_ext_smg"))},
			0.14065, 0.003608, 0.00324, 0.0094, 51.75, 0.26712, 0.30051, 52.0, 16.25, 48, 2.128, 0.3808},
		{TEXT("NINE quiet and long"), TEXT("nine"), {P(TEXT("muzzle"), TEXT("suppressor_pistol")), P(TEXT("laser"), TEXT("laser_module")), P(TEXT("magazine"), TEXT("mag_ext_pistol"))},
			0.173094, 0.00874, 0.00187, 0.0084, 18, 0.333366, 0.380989, 52.0, 28.9, 24, 1.65, 0.198},
	};
	const double Deg = 180.0 / UE_DOUBLE_PI;
	for (const FCase& C : Cases)
	{
		FMIGunBuild Build;
		for (const TPair<FName, FName>& Part : C.Parts) Build.Parts.Add(Part.Key, Part.Value);
		FMIResolvedGun G;
		FString Error;
		if (!Resolver.ResolveGun(C.Gun, &Build, nullptr, G, Error))
		{
			AddError(FString::Printf(TEXT("%s: %s"), C.Name, *Error));
			continue;
		}
		// The table of LOADOUT.md 3.3 is printed to six significant figures.
		const auto Check = [this, &C](const TCHAR* What, double Got, double Want)
		{
			if (!Close(Got, Want, 5e-6)) AddError(FString::Printf(TEXT("%s %s: %.9g, the table says %.9g"), C.Name, What, Got, Want));
		};
		Check(TEXT("aim time"), G.Def.AdsTime, C.Aim);
		Check(TEXT("kick"), G.Def.Recoil.Pitch / Deg, C.Kick);
		Check(TEXT("aimed spread"), G.Def.Spread.Ads / Deg, C.Aimed);
		Check(TEXT("hip spread"), G.Def.Spread.Hip / Deg, C.Hip);
		Check(TEXT("heard"), G.Def.NoiseRadius / 100.0, C.Heard);
		Check(TEXT("holster"), G.Def.Holster, C.Holster);
		Check(TEXT("draw"), G.Def.Draw, C.Draw);
		Check(TEXT("aimed view"), G.Def.AdsFov, C.Fov);
		if (C.FalloffMinDamage >= 0.0)
		{
			FMIShotRequest Shot;
			Shot.Damage = G.Def.Damage;
			Shot.FalloffStart = G.Def.FalloffStart;
			Shot.FalloffEnd = G.Def.FalloffEnd;
			Shot.FalloffMin = G.Def.FalloffMin;
			Check(TEXT("damage past the falloff"), Shot.DamageAt(G.Def.FalloffEnd + 100.0), C.FalloffMinDamage);
		}
		if (C.Name == FString(TEXT("STICK close")))
		{
			Check(TEXT("reload"), G.Def.Reload.Tactical, 2.0022);
			Check(TEXT("magOut"), G.Def.Reload.MagOut, 0.3572);
		}
		if (C.MagSize >= 0)
		{
			// A whole number, exactly: a fractional product would lose a round to the parser's truncation.
			TestEqual(FString(C.Name) + TEXT(" rounds in the magazine"), G.Def.MagSize, C.MagSize);
			Check(TEXT("reload"), G.Def.Reload.Tactical, C.Reload);
			Check(TEXT("magOut"), G.Def.Reload.MagOut, C.MagOut);
		}
	}
	// The factory builds of the six guns: nothing leaks into a bare gun (magazine sizes CHOPPER 30, NINE 15, SHORTY 30,
	// STICK 30, STRETCH 30, RATTLER 32).
	{
		struct FFactory { const TCHAR* Gun; int32 Mag; };
		for (const FFactory& F : {FFactory{TEXT("chopper"), 30}, FFactory{TEXT("nine"), 15}, FFactory{TEXT("shorty"), 30}, FFactory{TEXT("stick"), 30}, FFactory{TEXT("stretch"), 30}, FFactory{TEXT("rattler"), 32}})
		{
			FMIResolvedGun G;
			FString Error;
			if (Resolver.ResolveGun(F.Gun, nullptr, nullptr, G, Error))
			{
				TestEqual(FString(F.Gun) + TEXT(" factory magazine"), G.Def.MagSize, F.Mag);
				TestEqual(FString(F.Gun) + TEXT(" factory: no part fitted"), G.Parts.Num(), 0);
			}
			else
			{
				AddError(FString(F.Gun) + TEXT(": ") + Error);
			}
		}
	}
	// The CHOPPER with scope and silencer: hitscan at 20, 37.5 and 60 m gives 26, the linear 24.05 and 22.1.
	{
		FMIGunBuild Build;
		Build.Parts = {{TEXT("optic"), TEXT("scope")}, {TEXT("muzzle"), TEXT("silencer")}};
		FMIResolvedGun G;
		FString Error;
		if (Resolver.ResolveGun(TEXT("chopper"), &Build, nullptr, G, Error))
		{
			FMIShotRequest Shot;
			Shot.Damage = G.Def.Damage;
			Shot.FalloffStart = G.Def.FalloffStart;
			Shot.FalloffEnd = G.Def.FalloffEnd;
			Shot.FalloffMin = G.Def.FalloffMin;
			TestTrue(TEXT("20 m: 26"), Close(Shot.DamageAt(2000.0), 26.0, 1e-12));
			TestTrue(TEXT("37.5 m: 24.05"), Close(Shot.DamageAt(3750.0), 24.05, 1e-12));
			TestTrue(TEXT("60 m: 22.1"), Close(Shot.DamageAt(6000.0), 22.1, 1e-12));
		}
	}
	return !HasAnyErrors();
}

namespace MIAttachmentsPrivate
{
	/** A part with the given effects, in a slot, added to the data for the fixture tests. */
	void AddFixture(FMILoadoutData& D, FName Id, FName Slot, const TArray<FMIEffect>& Effects)
	{
		FMIAttachmentDef& P = D.Attachments.Add(Id);
		P.Id = Id;
		P.Slot = Slot;
		P.Effects = Effects;
	}
	FMIEffect E(const TCHAR* Stat, const TCHAR* Op, double V) { FMIEffect X; X.Stat = Stat; X.Op = Op; X.Value = V; return X; }
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAttachmentsOpsTest, "MurderInc.Attachments.Ops", MIAttachmentsPrivate::Flags)

bool FMIAttachmentsOpsTest::RunTest(const FString& Parameters)
{
	using namespace MIAttachmentsPrivate;
	FWorld W;
	if (!W.Load(*this))
	{
		return false;
	}
	const FMILoadoutResolver Resolver = W.Resolver();
	// Two sets in two slots (the later slot wins), an add, two muls (they multiply), two mins and a max on adsTime.
	AddFixture(W.Data, TEXT("fx_a"), TEXT("optic"), {E(TEXT("adsTime"), TEXT("set"), 0.30), E(TEXT("adsTime"), TEXT("mul"), 1.1), E(TEXT("adsTime"), TEXT("min"), 0.5)});
	AddFixture(W.Data, TEXT("fx_b"), TEXT("muzzle"), {E(TEXT("adsTime"), TEXT("set"), 0.25), E(TEXT("adsTime"), TEXT("add"), 0.05), E(TEXT("adsTime"), TEXT("mul"), 1.2),
		E(TEXT("adsTime"), TEXT("min"), 0.40), E(TEXT("adsTime"), TEXT("max"), 0.10)});
	TArray<const FMIAttachmentDef*> Parts = {W.Data.FindPart(TEXT("fx_a")), W.Data.FindPart(TEXT("fx_b"))};
	const FMIGunEntry* Stick = W.Data.FindGun(TEXT("stick"));
	TSharedPtr<FJsonObject> Doc = MakeShared<FJsonObject>();
	Doc->SetObjectField(TEXT("rules"), MIJson::DeepCopy(Stick->Rules));
	Doc->SetObjectField(TEXT("extra"), Resolver.FilledExtra(*Stick));
	FString Error;
	TestTrue(TEXT("ops apply"), Resolver.ApplyEffects(Parts, Doc, Error));
	// set 0.25 (later slot), + 0.05, x 1.1 x 1.2, min(0.5, 0.4), max 0.1 -> min(0.396, 0.4) = 0.396
	TestTrue(TEXT("set, add, mul, min, max in order"), Close(MIJson::NumberOr(Doc, TEXT("rules.adsTime"), -1), FMath::Min((0.25 + 0.05) * (1.1 * 1.2), 0.40), 1e-12));
	// A stat no part names is not touched at all.
	TestEqual(TEXT("untouched stat"), MIJson::NumberOr(Doc, TEXT("rules.spread.hip"), -1), MIJson::NumberOr(Stick->Rules, TEXT("spread.hip"), -2));
	// A multi-target stat takes only mul.
	AddFixture(W.Data, TEXT("fx_bad"), TEXT("laser"), {E(TEXT("recoil.pitch"), TEXT("add"), 0.1)});
	TestFalse(TEXT("add on a multi-target stat is refused"), Resolver.ApplyEffects({W.Data.FindPart(TEXT("fx_bad"))}, Doc, Error));
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAttachmentsClampsTest, "MurderInc.Attachments.Clamps", MIAttachmentsPrivate::Flags)

bool FMIAttachmentsClampsTest::RunTest(const FString& Parameters)
{
	using namespace MIAttachmentsPrivate;
	FWorld W;
	if (!W.Load(*this))
	{
		return false;
	}
	const FMILoadoutResolver Resolver = W.Resolver();
	const FMIGunEntry* Stick = W.Data.FindGun(TEXT("stick"));
	for (const double F : {10.0, 0.01})
	{
		for (const TPair<FName, FMIStatDef>& S : W.Data.Stats)
		{
			if (S.Value.Targets.Num() == 0 || S.Key == TEXT("reloadTime")) continue;
			AddFixture(W.Data, TEXT("fx_clamp"), TEXT("optic"), {E(*S.Key.ToString(), TEXT("mul"), F)});
			TSharedPtr<FJsonObject> Doc = MakeShared<FJsonObject>();
			Doc->SetObjectField(TEXT("rules"), MIJson::DeepCopy(Stick->Rules));
			TSharedPtr<FJsonObject> Extra = Resolver.FilledExtra(*Stick);
			// A finite falloff so the falloff stats have a value to move.
			Extra->SetObjectField(TEXT("falloff"), MakeShared<FJsonObject>());
			Extra->GetObjectField(TEXT("falloff"))->SetNumberField(TEXT("start"), 30);
			Extra->GetObjectField(TEXT("falloff"))->SetNumberField(TEXT("end"), 60);
			Extra->GetObjectField(TEXT("falloff"))->SetNumberField(TEXT("min"), 0.8);
			Doc->SetObjectField(TEXT("extra"), Extra);
			TSharedPtr<FJsonObject> Before = MIJson::DeepCopy(Doc);
			FString Error;
			if (!Resolver.ApplyEffects({W.Data.FindPart(TEXT("fx_clamp"))}, Doc, Error))
			{
				AddError(Error);
				continue;
			}
			const bool bMulti = S.Value.Targets.Num() > 1;
			const double Factor = bMulti ? FMath::Clamp(F, W.Data.FactorMin, W.Data.FactorMax) : F;
			for (const FMIStatTarget& T : S.Value.Targets)
			{
				double B = 0.0, A = 0.0;
				if (!MIJson::Number(MIJson::Get(Before, T.Path), B) || !MIJson::Number(MIJson::Get(Doc, T.Path), A)) continue;
				double Want = B * Factor;
				if (T.bClamp) Want = FMath::Clamp(Want, T.Min, T.Max);
				if (T.Path == TEXT("extra.falloff.end")) Want = FMath::Max(Want, MIJson::NumberOr(Doc, TEXT("extra.falloff.start"), Want));
				if (!Close(A, Want, 1e-12))
				{
					AddError(FString::Printf(TEXT("%s x %g: %s is %.12g, its clamp gives %.12g"), *S.Key.ToString(), F, *T.Path, A, Want));
				}
			}
		}
	}
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAttachmentsFalloffTest, "MurderInc.Attachments.Falloff", MIAttachmentsPrivate::Flags)

bool FMIAttachmentsFalloffTest::RunTest(const FString& Parameters)
{
	using namespace MIAttachmentsPrivate;
	FWorld W;
	if (!W.Load(*this))
	{
		return false;
	}
	const FMILoadoutResolver Resolver = W.Resolver();
	// start pushed past end: end becomes start, and the shot is a step to min at start.
	AddFixture(W.Data, TEXT("fx_step"), TEXT("muzzle"), {E(TEXT("falloff.start"), TEXT("set"), 40), E(TEXT("falloff.end"), TEXT("set"), 25), E(TEXT("falloff.min"), TEXT("set"), 0.5)});
	const FMIGunEntry* Stick = W.Data.FindGun(TEXT("stick"));
	TSharedPtr<FJsonObject> Doc = MakeShared<FJsonObject>();
	Doc->SetObjectField(TEXT("rules"), MIJson::DeepCopy(Stick->Rules));
	Doc->SetObjectField(TEXT("extra"), Resolver.FilledExtra(*Stick));
	FString Error;
	TestTrue(TEXT("applies"), Resolver.ApplyEffects({W.Data.FindPart(TEXT("fx_step"))}, Doc, Error));
	TestEqual(TEXT("end = start"), MIJson::NumberOr(Doc, TEXT("extra.falloff.end"), -1), 40.0);
	FMIWeaponDef Def;
	TestTrue(TEXT("parses"), UMIDataSubsystem::ParseGun(Doc->GetObjectField(TEXT("rules")), Doc->GetObjectField(TEXT("extra")), Def, Error));
	FMIShotRequest Shot;
	Shot.Damage = Def.Damage;
	Shot.FalloffStart = Def.FalloffStart;
	Shot.FalloffEnd = Def.FalloffEnd;
	Shot.FalloffMin = Def.FalloffMin;
	TestEqual(TEXT("full damage at the start"), Shot.DamageAt(4000.0), Def.Damage);
	TestEqual(TEXT("a step to min just past it"), Shot.DamageAt(4000.5), Def.Damage * 0.5);
	// No falloff (start = infinity): the branch is skipped, the damage is the gun's, not times a computed 1.
	Shot.FalloffStart = Shot.FalloffEnd = std::numeric_limits<double>::infinity();
	TestEqual(TEXT("no falloff"), Shot.DamageAt(1e9), Def.Damage);
	return !HasAnyErrors();
}

#endif
