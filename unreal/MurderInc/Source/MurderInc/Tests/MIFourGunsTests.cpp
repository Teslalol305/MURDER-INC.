// LOADOUT.md 8.3: four guns in the rules (switching, retarget, per-gun timing, the bag, the selector, semi mode).

#include "Core/Data/MILoadoutData.h"
#include "Misc/AutomationTest.h"
#include "Weapons/MILoadoutResolver.h"
#include "Weapons/MIWeaponRules.h"

#if WITH_AUTOMATION_TESTS

namespace MIFourGunsPrivate
{
	constexpr EAutomationTestFlags Flags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter;
	constexpr double Dt = 1.0 / 60.0;

	struct FHost : public IMIWeaponHost
	{
		FMIWeaponPlayerState Player;
		int32 Rounds = 0;
		double AimFov = 0.0;
		virtual FMIWeaponPlayerState GetPlayerState() const override { return Player; }
		virtual void SetPlayerAds(double) override {}
		virtual void SetPlayerAimView(double Fov, double) override { AimFov = Fov; }
		virtual void AddRecoil(double, double) override {}
		virtual void AddShake(double) override {}
		virtual FMIShotResult Hitscan(const FMIShotRequest& Shot) override { ++Rounds; FMIShotResult R; R.bHit = true; R.Distance = 1000; return R; }
		virtual EMIStrikeResult Melee(const FMIStrikeRequest&) override { return EMIStrikeResult::None; }
		virtual double ProbeWall(const FVector&, const FVector&, double) override { return -1.0; }
		virtual bool AimTarget(const FVector&, const FVector&, double) override { return false; }
	};

	struct FRig
	{
		FMILoadoutData Data;
		TSharedPtr<FJsonObject> Config, Presentation;
		FMIGameEvents Events;
		FMIWeaponRules Rules;
		FHost Host;
		TArray<FMISwitchEvent> Switches;
		TArray<TPair<FName, bool>> Modes;

		bool Init(FAutomationTestBase& T, const TArray<FName>& Guns)
		{
			FString Error;
			FMIResolvedRun Run;
			FMIRunSetup Setup;
			Setup.Guns = Guns;
			if (!FMILoadoutData::Load(Data, Error) || !FMILoadoutResolver::LoadRoots(Config, Presentation, Error)
				|| !FMILoadoutResolver(Data, Config, Presentation).Resolve(Setup, nullptr, Run, Error))
			{
				T.AddError(Error);
				return false;
			}
			Events.WeaponSwitch.AddLambda([this](const FMISwitchEvent& E) { Switches.Add(E); });
			Events.WeaponMode.AddLambda([this](FName W, bool bSemi) { Modes.Add({W, bSemi}); });
			Rules.Init(Run.Weapons, 1994, &Events);
			return true;
		}

		void Step(const FMIWeaponInput& In = FMIWeaponInput()) { Rules.Update(Dt, In, Host); }
		void Settle() { for (int32 I = 0; I < 240 && Rules.GetActivity() != EMIWeaponActivity::Ready; ++I) Step(); }
		void Press(bool FMIWeaponInput::*Flag) { FMIWeaponInput In; In.*Flag = true; Step(In); }
		void Select(int32 Slot)
		{
			static bool FMIWeaponInput::*Flags[] = {&FMIWeaponInput::bWeapon1Pressed, &FMIWeaponInput::bWeapon2Pressed, &FMIWeaponInput::bWeapon3Pressed, &FMIWeaponInput::bWeapon4Pressed};
			Press(Flags[Slot]);
			Settle();
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIFourGunsTest, "MurderInc.Weapons.FourGuns", MIFourGunsPrivate::Flags)

bool FMIFourGunsTest::RunTest(const FString& Parameters)
{
	using namespace MIFourGunsPrivate;
	FRig R;
	// 0 CHOPPER, 1 STICK, 2 RATTLER, 3 NINE
	if (!R.Init(*this, {TEXT("chopper"), TEXT("stick"), TEXT("rattler"), TEXT("nine")}))
	{
		return false;
	}
	FMIWeaponRules& W = R.Rules;
	TestEqual(TEXT("starts on slot 1"), W.GetCurrentIndex(), 0);
	TestEqual(TEXT("last used starts at slot 2"), W.GetLastUsed(), 1);

	// 1-4 select; Q goes back to the last gun used.
	R.Select(2);
	TestEqual(TEXT("3 selects the RATTLER"), W.GetCurrentId(), FName(TEXT("rattler")));
	R.Select(3);
	TestEqual(TEXT("4 selects the NINE"), W.GetCurrentId(), FName(TEXT("nine")));
	R.Press(&FMIWeaponInput::bSwapPressed);
	R.Settle();
	TestEqual(TEXT("Q goes back to the RATTLER"), W.GetCurrentId(), FName(TEXT("rattler")));
	R.Press(&FMIWeaponInput::bSwapPressed);
	R.Settle();
	TestEqual(TEXT("Q again: the NINE"), W.GetCurrentId(), FName(TEXT("nine")));

	// Next and previous cycle and wrap (N = 4).
	R.Press(&FMIWeaponInput::bNextPressed);
	R.Settle();
	TestEqual(TEXT("next from slot 4 wraps to slot 1"), W.GetCurrentIndex(), 0);
	R.Press(&FMIWeaponInput::bPreviousPressed);
	R.Settle();
	TestEqual(TEXT("previous from slot 1 wraps to slot 4"), W.GetCurrentIndex(), 3);
	R.Press(&FMIWeaponInput::bPreviousPressed);
	R.Settle();
	TestEqual(TEXT("previous: slot 3"), W.GetCurrentIndex(), 2);

	// A third gun requested mid-holster retargets and says holster(Current, newTo).
	R.Select(0);
	R.Switches.Reset();
	R.Press(&FMIWeaponInput::bWeapon2Pressed);
	for (int32 I = 0; I < 5; ++I) R.Step();
	R.Press(&FMIWeaponInput::bWeapon3Pressed);
	TestTrue(TEXT("retarget event"), R.Switches.Num() == 2 && R.Switches[1].From == TEXT("chopper") && R.Switches[1].To == TEXT("rattler") && R.Switches[1].Phase == TEXT("holster"));
	TestEqual(TEXT("still holstering"), W.GetActivity(), EMIWeaponActivity::Holstering);
	R.Settle();
	TestEqual(TEXT("the retargeted gun is drawn"), W.GetCurrentId(), FName(TEXT("rattler")));

	// Mixed timing: RATTLER -> STICK reversed mid-holster gives T = Draw(RATTLER) x (1 - T / Holster(RATTLER)).
	R.Press(&FMIWeaponInput::bWeapon2Pressed);  // T = dt after this frame
	for (int32 I = 0; I < 6; ++I) R.Step();
	const double T0 = W.GetActivityTime();
	R.Press(&FMIWeaponInput::bWeapon3Pressed);  // the gun in hand: comes back up
	TestEqual(TEXT("reversal draws"), W.GetActivity(), EMIWeaponActivity::Drawing);
	TestTrue(TEXT("RATTLER draw 0.27, holster 0.24"), W.DrawOf(2) == 0.27 && W.HolsterOf(2) == 0.24);
	TestNearlyEqual(TEXT("reversal T"), W.GetActivityTime(), 0.27 * (1.0 - T0 / 0.24) + Dt, 1e-12);
	R.Settle();
	// A re-holster mid-draw of the STICK: T = Holster(STICK) x (1 - T / Draw(STICK)).
	R.Press(&FMIWeaponInput::bWeapon2Pressed);
	for (int32 I = 0; I < 40 && W.GetActivity() != EMIWeaponActivity::Drawing; ++I) R.Step();
	for (int32 I = 0; I < 4; ++I) R.Step();
	TestEqual(TEXT("drawing the STICK"), W.GetCurrentId(), FName(TEXT("stick")));
	const double D0 = W.GetActivityTime();
	R.Press(&FMIWeaponInput::bWeapon3Pressed);
	TestEqual(TEXT("re-holster"), W.GetActivity(), EMIWeaponActivity::Holstering);
	TestNearlyEqual(TEXT("re-holster T"), W.GetActivityTime(), W.HolsterOf(1) * (1.0 - D0 / W.DrawOf(1)) + Dt, 1e-12);
	R.Settle();

	// The bag: the CHOPPER and the STICK share it; the NINE is untouched.
	TestEqual(TEXT("bag starts at 150"), W.GetBag(), 150.0);
	R.Select(1);
	{
		FMIWeaponInput Fire;
		Fire.bFireDown = Fire.bFirePressed = true;
		for (int32 I = 0; I < 30; ++I) { R.Step(Fire); Fire.bFirePressed = false; }
	}
	R.Step();
	const int32 Spent = 30 - W.GetMag();
	TestTrue(TEXT("the STICK fired"), Spent > 0);
	R.Press(&FMIWeaponInput::bReloadPressed);
	R.Settle();
	TestEqual(TEXT("the reload drew from the bag"), W.GetBag(), 150.0 - Spent);
	TestEqual(TEXT("the CHOPPER sees the same bag"), W.GetReserveOf(0), 150.0 - Spent);
	TestFalse(TEXT("the NINE stays infinite"), FMath::IsFinite(W.GetReserveOf(3)));
	W.AddReserve(90, 240);
	TestEqual(TEXT("AddReserve(90, 240) adds 90 once"), W.GetBag(), FMath::Min(240.0, 150.0 - Spent + 90.0));

	// The selector: blocks fire for ModeSwitch, then flips; GetState is selector meanwhile.
	R.Modes.Reset();
	R.Press(&FMIWeaponInput::bFireModePressed);
	TestEqual(TEXT("state selector"), W.GetState(), FName(TEXT("selector")));
	{
		FMIWeaponInput Fire;
		Fire.bFireDown = Fire.bFirePressed = true;
		const int32 Before = R.Host.Rounds;
		R.Step(Fire);
		TestEqual(TEXT("no round during the selector"), R.Host.Rounds, Before);
	}
	R.Settle();
	TestTrue(TEXT("flipped to semi"), W.IsSemi(1) && R.Modes.Num() == 1 && R.Modes[0].Value);
	// Semi buffering on the STICK: a held trigger fires one round.
	{
		R.Press(&FMIWeaponInput::bReloadPressed);
		R.Settle();
		const int32 Before = R.Host.Rounds;
		FMIWeaponInput Fire;
		Fire.bFireDown = Fire.bFirePressed = true;
		for (int32 I = 0; I < 60; ++I) { R.Step(Fire); Fire.bFirePressed = false; }
		TestEqual(TEXT("semi: one round per press"), R.Host.Rounds - Before, 1);
		R.Step();
		Fire.bFirePressed = true;
		R.Step(Fire);
		TestEqual(TEXT("semi: the next press fires"), R.Host.Rounds - Before, 2);
	}
	// A swap cancels the selector without flipping.
	R.Step();
	R.Press(&FMIWeaponInput::bFireModePressed);
	R.Press(&FMIWeaponInput::bWeapon1Pressed);
	R.Settle();
	TestTrue(TEXT("a swap cancels the selector"), W.IsSemi(1) && R.Modes.Num() == 1);
	TestEqual(TEXT("on the CHOPPER"), W.GetCurrentIndex(), 0);
	// A dry fire, then a selector press within the dry reload delay: the reload runs when the selector ends.
	{
		FMIWeaponInput Fire;
		Fire.bFireDown = Fire.bFirePressed = true;
		for (int32 I = 0; I < 200 && W.GetMag() > 0; ++I) { R.Step(Fire); Fire.bFirePressed = false; }
		for (int32 I = 0; I < 8; ++I) R.Step(Fire);  // the cooldown runs out, then one dry fire (latched)
		R.Step();
		R.Press(&FMIWeaponInput::bFireModePressed);
		TestEqual(TEXT("selector after a dry fire"), W.GetState(), FName(TEXT("selector")));
		for (int32 I = 0; I < 60 && W.GetActivity() == EMIWeaponActivity::Selector; ++I) R.Step();
		TestEqual(TEXT("the held auto reload runs after the selector"), W.GetActivity(), EMIWeaponActivity::Reloading);
		TestTrue(TEXT("the CHOPPER is on semi now"), W.IsSemi(0));
	}
	R.Settle();

	// Reset: every gun starts in fireModes[0].
	W.Reset();
	TestFalse(TEXT("reset: CHOPPER auto"), W.IsSemi(0));
	TestFalse(TEXT("reset: STICK auto"), W.IsSemi(1));
	TestTrue(TEXT("reset: NINE semi"), W.IsSemi(3));

	// N = 3: next and previous wrap.
	FRig Three;
	if (Three.Init(*this, {TEXT("chopper"), TEXT("stick"), TEXT("nine")}))
	{
		Three.Press(&FMIWeaponInput::bPreviousPressed);
		Three.Settle();
		TestEqual(TEXT("N=3 previous wraps"), Three.Rules.GetCurrentIndex(), 2);
		Three.Press(&FMIWeaponInput::bNextPressed);
		Three.Settle();
		TestEqual(TEXT("N=3 next wraps"), Three.Rules.GetCurrentIndex(), 0);
		Three.Press(&FMIWeaponInput::bWeapon4Pressed);
		Three.Settle();
		TestEqual(TEXT("N=3 slot 4 is empty"), Three.Rules.GetCurrentIndex(), 0);
	}
	// One gun ignores every switch input.
	FRig One;
	if (One.Init(*this, {TEXT("stick")}))
	{
		for (bool FMIWeaponInput::*F : {&FMIWeaponInput::bSwapPressed, &FMIWeaponInput::bNextPressed, &FMIWeaponInput::bPreviousPressed, &FMIWeaponInput::bWeapon2Pressed})
		{
			One.Press(F);
		}
		TestTrue(TEXT("one gun: no switch"), One.Switches.Num() == 0 && One.Rules.GetActivity() == EMIWeaponActivity::Ready);
	}
	return !HasAnyErrors();
}

#endif
