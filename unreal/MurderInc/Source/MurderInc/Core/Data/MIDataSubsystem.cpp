#include "Core/Data/MIDataSubsystem.h"

#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "MurderInc.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonValue.h"
#include <limits>

namespace MIDataSubsystemPrivate
{
	/** Reads numbers by dotted path ("player.speed.walk") and remembers every path that was not there. */
	struct FReader
	{
		TSharedPtr<FJsonObject> Root;
		TArray<FString> Missing;

		TSharedPtr<FJsonObject> Parent(const FString& Path, FString& OutLeaf) const
		{
			TArray<FString> Parts;
			Path.ParseIntoArray(Parts, TEXT("."));
			TSharedPtr<FJsonObject> Object = Root;
			for (int32 Index = 0; Object.IsValid() && Index < Parts.Num() - 1; ++Index)
			{
				const TSharedPtr<FJsonObject>* Child = nullptr;
				if (Object->TryGetObjectField(Parts[Index], Child) && Child)
				{
					Object = *Child;
				}
				else
				{
					Object.Reset();
				}
			}
			OutLeaf = Parts.Num() > 0 ? Parts.Last() : FString();
			return Object;
		}

		double Number(const TCHAR* Path, double Scale = 1.0)
		{
			FString Leaf;
			double Value = 0.0;
			const TSharedPtr<FJsonObject> Object = Parent(Path, Leaf);
			if (!Object.IsValid() || !Object->TryGetNumberField(Leaf, Value))
			{
				Missing.Add(Path);
				return 0.0;
			}
			return Value * Scale;
		}

		/** Element Index of the number array at Path. */
		double NumberAt(const TCHAR* Path, int32 Index, double Scale = 1.0)
		{
			FString Leaf;
			const TArray<TSharedPtr<FJsonValue>>* Array = nullptr;
			const TSharedPtr<FJsonObject> Object = Parent(Path, Leaf);
			if (!Object.IsValid() || !Object->TryGetArrayField(Leaf, Array) || !Array->IsValidIndex(Index))
			{
				Missing.Add(FString::Printf(TEXT("%s[%d]"), Path, Index));
				return 0.0;
			}
			double Value = 0.0;
			if (!(*Array)[Index]->TryGetNumber(Value))
			{
				Missing.Add(FString::Printf(TEXT("%s[%d]"), Path, Index));
			}
			return Value * Scale;
		}

		/** A number that may be the string "Infinity" (JSON has none: meta.encoding.infinity). */
		double NumberOrInfinity(const TCHAR* Path, double Scale = 1.0)
		{
			FString Leaf;
			const TSharedPtr<FJsonObject> Object = Parent(Path, Leaf);
			FString Text;
			if (Object.IsValid() && Object->TryGetStringField(Leaf, Text) && Text == TEXT("Infinity"))
			{
				return std::numeric_limits<double>::infinity();
			}
			return Number(Path, Scale);
		}

		/** Optional number: Fallback when absent (not an error). */
		double Optional(const TCHAR* Path, double Fallback, double Scale = 1.0)
		{
			FString Leaf;
			double Value = 0.0;
			const TSharedPtr<FJsonObject> Object = Parent(Path, Leaf);
			return Object.IsValid() && Object->TryGetNumberField(Leaf, Value) ? Value * Scale : Fallback;
		}

		bool Bool(const TCHAR* Path)
		{
			FString Leaf;
			bool Value = false;
			const TSharedPtr<FJsonObject> Object = Parent(Path, Leaf);
			if (!Object.IsValid() || !Object->TryGetBoolField(Leaf, Value))
			{
				Missing.Add(Path);
			}
			return Value;
		}

		FColor Color(const TCHAR* Path)
		{
			const FString Hex = String(Path);
			return Hex.StartsWith(TEXT("#")) ? FColor::FromHex(Hex) : FColor::White;
		}

		TArray<FString> Strings(const TCHAR* Path)
		{
			FString Leaf;
			TArray<FString> Out;
			const TSharedPtr<FJsonObject> Object = Parent(Path, Leaf);
			if (!Object.IsValid() || !Object->TryGetStringArrayField(Leaf, Out))
			{
				Missing.Add(Path);
			}
			return Out;
		}

		TSharedPtr<FJsonObject> Object(const TCHAR* Path)
		{
			FString Leaf;
			const TSharedPtr<FJsonObject> Owner = Parent(FString(Path) + TEXT(".x"), Leaf);
			if (!Owner.IsValid())
			{
				Missing.Add(Path);
			}
			return Owner;
		}

		/**
		 * The numbers of a {"$function": {source, samples}} entry, in the order they appear in the source text,
		 * and the samples to check a re-implementation against.
		 */
		TArray<double> FunctionNumbers(const TCHAR* Path, TArray<TPair<TArray<double>, double>>& OutSamples)
		{
			TArray<double> Numbers;
			const FString Source = String(*FString::Printf(TEXT("%s.$function.source"), Path));
			// Skip the parameter list "(a, b) =>" and read every literal number after it.
			int32 Arrow = Source.Find(TEXT("=>"));
			const FString Body = Arrow == INDEX_NONE ? Source : Source.Mid(Arrow + 2);
			for (int32 I = 0; I < Body.Len();)
			{
				const bool bStart = FChar::IsDigit(Body[I]) && (I == 0 || !(FChar::IsAlnum(Body[I - 1]) || Body[I - 1] == TEXT('_')));
				if (!bStart)
				{
					++I;
					continue;
				}
				int32 J = I;
				while (J < Body.Len() && (FChar::IsDigit(Body[J]) || Body[J] == TEXT('.')))
				{
					++J;
				}
				Numbers.Add(FCString::Atod(*Body.Mid(I, J - I)));
				I = J;
			}
			FString Leaf;
			const TSharedPtr<FJsonObject> Fn = Parent(FString::Printf(TEXT("%s.$function.samples"), Path), Leaf);
			const TArray<TSharedPtr<FJsonValue>>* Samples = nullptr;
			if (Fn.IsValid() && Fn->TryGetArrayField(Leaf, Samples))
			{
				for (const TSharedPtr<FJsonValue>& Sample : *Samples)
				{
					const TSharedPtr<FJsonObject> S = Sample->AsObject();
					TPair<TArray<double>, double> Row;
					const TArray<TSharedPtr<FJsonValue>>* Args = nullptr;
					if (S.IsValid() && S->TryGetArrayField(TEXT("args"), Args) && S->TryGetNumberField(TEXT("value"), Row.Value))
					{
						for (const TSharedPtr<FJsonValue>& Arg : *Args)
						{
							Row.Key.Add(Arg->AsNumber());
						}
						OutSamples.Add(Row);
					}
				}
			}
			return Numbers;
		}

		FString String(const TCHAR* Path)
		{
			FString Leaf;
			FString Value;
			const TSharedPtr<FJsonObject> Object = Parent(Path, Leaf);
			if (!Object.IsValid() || !Object->TryGetStringField(Leaf, Value))
			{
				Missing.Add(Path);
			}
			return Value;
		}
	};

	// The file is in metres and radians (meta.units.web); the game runs in centimetres and degrees.
	constexpr double MetresToCm = 100.0;
	constexpr double RadToDeg = 180.0 / UE_DOUBLE_PI;
}

namespace MIDataSubsystemParse
{
	using MIDataSubsystemPrivate::FReader;

	void ParsePlayerRest(FReader& In, FMIPlayerData& P)
	{
		using namespace MIDataSubsystemPrivate;
		P.Body.AirStepHeight = In.Number(TEXT("player.body.airStepHeight"), MetresToCm);
		P.Body.BoundsMargin = In.Number(TEXT("player.body.boundsMargin"), MetresToCm);
		P.Body.StandClearance = In.Number(TEXT("player.body.standClearance"), MetresToCm);
		P.Body.Footprint = In.Number(TEXT("player.body.footprint"));
		P.Body.HeadClearance = In.Number(TEXT("player.body.headClearance"), MetresToCm);
		P.Speed.Moving = In.Number(TEXT("player.speed.moving"), MetresToCm);
		P.Sprint.MaxAds = In.Number(TEXT("player.sprint.maxAds"));

		P.Stride.Walk = In.Number(TEXT("player.stride.walk"), MetresToCm);
		P.Stride.Sprint = In.Number(TEXT("player.stride.sprint"), MetresToCm);
		P.Stride.Crouch = In.Number(TEXT("player.stride.crouch"), MetresToCm);
		P.Stride.SettleRate = In.Number(TEXT("player.stride.settleRate"));
		P.Stride.AfterLanding = In.Number(TEXT("player.stride.afterLanding"));

		P.Fov.RateAds = In.Number(TEXT("player.fov.rateAds"));
		P.Fov.AdsBandLow = In.NumberAt(TEXT("player.fov.adsBand"), 0);
		P.Fov.AdsBandHigh = In.NumberAt(TEXT("player.fov.adsBand"), 1);
		P.Fov.Viewmodel = In.Number(TEXT("player.fov.viewmodel"));

		P.Look.ViewPitchLimit = In.Number(TEXT("player.look.viewPitchLimit"), RadToDeg);
		P.Look.AdsScale = In.Number(TEXT("player.look.adsScale"));
		P.Look.MouseGlitch = In.Number(TEXT("player.input.mouseGlitch"));

		P.Health.Max = In.Number(TEXT("player.health.max"));
		P.Health.RegenDelay = In.Number(TEXT("player.health.regenDelay"));
		P.Health.RegenRate = In.Number(TEXT("player.health.regenRate"));
		P.Health.LowWarning = In.Number(TEXT("player.health.lowWarning"));
		P.Health.HurtBase = In.Number(TEXT("player.health.hurtPulse.base"));
		P.Health.HurtPerDamage = In.Number(TEXT("player.health.hurtPulse.perDamage"));
		P.Health.HurtDecay = In.Number(TEXT("player.health.hurtPulse.decay"));
		P.Health.LowFrom = In.Number(TEXT("player.health.lowHealth.from"));
		P.Health.LowTo = In.Number(TEXT("player.health.lowHealth.to"));
		P.Health.LowRate = In.Number(TEXT("player.health.lowHealth.rate"));

		P.Fall.LandMinAir = In.Number(TEXT("player.fall.landMinAir"));
		P.Fall.DamageFrom = In.Number(TEXT("player.fall.damageFrom"), MetresToCm);
		P.Fall.DamagePerSpeed = In.Number(TEXT("player.fall.damagePerSpeed"), 1.0 / MetresToCm);
		P.Fall.ShakeFrom = In.Number(TEXT("player.fall.shakeFrom"), MetresToCm);
		P.Fall.ShakePerSpeed = In.Number(TEXT("player.fall.shakePerSpeed"), 1.0 / MetresToCm);
		P.Fall.ShakeMax = In.Number(TEXT("player.fall.shakeMax"));
		P.Fall.DipPerSpeed = In.Number(TEXT("player.fall.dipPerSpeed"));
		P.Fall.DipMax = In.Number(TEXT("player.fall.dipMax"), MetresToCm);

		P.Bob.Rate = In.Number(TEXT("player.bob.rate"));
		P.Bob.Vertical = In.Number(TEXT("player.bob.vertical"), MetresToCm);
		P.Bob.Lateral = In.Number(TEXT("player.bob.lateral"), MetresToCm);
		P.Bob.RollFromLateral = In.Number(TEXT("player.bob.rollFromLateral"), RadToDeg / MetresToCm);
		P.Bob.SprintScale = In.Number(TEXT("player.bob.sprintScale"));
		P.Bob.CrouchScale = In.Number(TEXT("player.bob.crouchScale"));
		P.Bob.AdsScale = In.Number(TEXT("player.bob.adsScale"));
		P.Bob.StrafeRoll = In.Number(TEXT("player.bob.strafeRoll"), RadToDeg);
		P.Bob.StrafeRollRate = In.Number(TEXT("player.bob.strafeRollRate"));
		P.Bob.StrafeRollAds = In.Number(TEXT("player.bob.strafeRollAds"));
		P.Bob.SpringStiffness = In.Number(TEXT("player.bob.spring.stiffness"));
		P.Bob.SpringDamping = In.Number(TEXT("player.bob.spring.damping"));
		P.Bob.SpringMin = In.Number(TEXT("player.bob.spring.min"), MetresToCm);
		P.Bob.SpringMax = In.Number(TEXT("player.bob.spring.max"), MetresToCm);
		P.Bob.SpringPitch = In.Number(TEXT("player.bob.spring.pitch"), RadToDeg / MetresToCm);
		P.Bob.StepFrequency = In.Number(TEXT("player.bob.step.frequency"));
		P.Bob.StepMax = In.Number(TEXT("player.bob.step.max"), MetresToCm);

		P.Recoil.Keep = In.Number(TEXT("player.recoil.keep"));
		P.Recoil.MaxPitch = In.Number(TEXT("player.recoil.maxPitch"), RadToDeg);
		P.Recoil.MaxYaw = In.Number(TEXT("player.recoil.maxYaw"), RadToDeg);
		P.Recoil.Chase = In.Number(TEXT("player.recoil.chase"));
		P.Recoil.Hold = In.Number(TEXT("player.recoil.hold"));
		P.Recoil.Recover = In.Number(TEXT("player.recoil.recover"));

		P.Shake.Decay = In.Number(TEXT("player.shake.decay"));
		P.Shake.Pitch = In.Number(TEXT("player.shake.pitch"), RadToDeg);
		P.Shake.Yaw = In.Number(TEXT("player.shake.yaw"), RadToDeg);
		P.Shake.Roll = In.Number(TEXT("player.shake.roll"), RadToDeg);
		for (int32 I = 0; I < 2; ++I)
		{
			P.Shake.FreqPitch[I] = In.NumberAt(TEXT("player.shake.freq.pitch"), I);
			P.Shake.FreqYaw[I] = In.NumberAt(TEXT("player.shake.freq.yaw"), I);
			P.Shake.FreqRoll[I] = In.NumberAt(TEXT("player.shake.freq.roll"), I);
		}
		P.Shake.OnHitBase = In.Number(TEXT("player.shake.onHit.base"));
		P.Shake.OnHitPerDamage = In.Number(TEXT("player.shake.onHit.perDamage"));
		P.Shake.BlastRange = In.Number(TEXT("player.shake.onBlast.range"), MetresToCm);
		P.Shake.BlastBase = In.Number(TEXT("player.shake.onBlast.base"));
		P.Shake.BlastScale = In.Number(TEXT("player.shake.onBlast.scale"));
		P.Shake.BlastSmall = In.Number(TEXT("player.shake.onBlast.small"));
		P.Shake.SustainBelow = In.Number(TEXT("player.shake.sustain.below"));
		P.Shake.SustainMax = In.Number(TEXT("player.shake.sustain.max"));
		P.Shake.SustainRate = In.Number(TEXT("player.shake.sustain.rate"));

		P.Death.Collapse = In.Number(TEXT("player.death.collapse"));
		P.Death.Eye = In.Number(TEXT("player.death.eye"), MetresToCm);
		P.Death.EyeRate = In.Number(TEXT("player.death.eyeRate"));
		P.Death.Roll = In.Number(TEXT("player.death.roll"), RadToDeg);
		P.Death.Pitch = In.Number(TEXT("player.death.pitch"), RadToDeg);
		P.Death.PitchBounce = In.Number(TEXT("player.death.pitchBounce"), RadToDeg);
		P.Death.Slide = In.Number(TEXT("player.death.slide"));
		P.Death.CapsuleHeight = In.Number(TEXT("player.death.capsuleHeight"), MetresToCm);
	}

	/** One gun object. Prefix: "weapons.<id>." in config.json, "" for a gun object on its own (the resolver). */
	void ParseGunAt(FReader& In, const FString& Prefix, FMIWeaponDef& G)
	{
		using namespace MIDataSubsystemPrivate;
		const auto Path = [&Prefix](const TCHAR* Leaf) { return Prefix + Leaf; };
		G.Id = FName(*In.String(*Path(TEXT("id"))));
		G.Name = In.String(*Path(TEXT("name")));
		G.Slot = static_cast<int32>(In.Number(*Path(TEXT("slot"))));
		G.bAuto = In.Bool(*Path(TEXT("auto")));
		G.Damage = In.Number(*Path(TEXT("damage")));
		G.Rpm = In.Number(*Path(TEXT("rpm")));
		G.MagSize = static_cast<int32>(In.Number(*Path(TEXT("magSize"))));
		G.Reserve = In.NumberOrInfinity(*Path(TEXT("reserve")));
		G.Range = In.Number(*Path(TEXT("range")), MetresToCm);
		G.AdsTime = In.Number(*Path(TEXT("adsTime")));
		G.FireBuffer = In.Optional(*Path(TEXT("fireBuffer")), 0.0);
		G.DryCooldown = In.Optional(*Path(TEXT("dryCooldown")), 0.0);
		G.DryReloadDelay = In.Number(*Path(TEXT("dryReloadDelay")));

		G.Reload.Tactical = In.Number(*Path(TEXT("reload.tactical")));
		G.Reload.Empty = In.Number(*Path(TEXT("reload.empty")));
		G.Reload.MagOut = In.Number(*Path(TEXT("reload.magOut")));
		G.Reload.MagIn = In.Number(*Path(TEXT("reload.magIn")));
		// logic.js: tactical bolt = pressCheck[0]; empty bolt = boltBack ?? slideRelease.
		{
			FString Leaf;
			const TArray<TSharedPtr<FJsonValue>>* Press = nullptr;
			const TSharedPtr<FJsonObject> Reload = In.Parent(Path(TEXT("reload.pressCheck")), Leaf);
			G.Reload.BoltTactical = Reload.IsValid() && Reload->TryGetArrayField(Leaf, Press) && Press->Num() > 0 ? (*Press)[0]->AsNumber() : -1.0;
		}
		G.Reload.BoltEmpty = In.Optional(*Path(TEXT("reload.boltBack")), In.Optional(*Path(TEXT("reload.slideRelease")), -1.0));

		G.Spread.Hip = In.Number(*Path(TEXT("spread.hip")), RadToDeg);
		G.Spread.Ads = In.Number(*Path(TEXT("spread.ads")), RadToDeg);
		G.Spread.MoveHip = In.Number(*Path(TEXT("spread.moveHip")), RadToDeg);
		G.Spread.MoveAds = In.Number(*Path(TEXT("spread.moveAds")), RadToDeg);
		G.Spread.BloomHip = In.Number(*Path(TEXT("spread.bloomHip")), RadToDeg);
		G.Spread.BloomAds = In.Number(*Path(TEXT("spread.bloomAds")), RadToDeg);
		G.Spread.Air = In.Number(*Path(TEXT("spread.air")), RadToDeg);
		G.Spread.Crouch = In.Number(*Path(TEXT("spread.crouch")), RadToDeg);
		G.Spread.Shot = In.Number(*Path(TEXT("spread.shot")));
		G.Spread.Decay = In.Number(*Path(TEXT("spread.decay")));

		FMIWeaponRecoilData& R = G.Recoil;
		R.Pitch = In.Number(*Path(TEXT("recoil.pitch")), RadToDeg);
		R.PitchRandomMin = In.NumberAt(*Path(TEXT("recoil.pitchRandom")), 0);
		R.PitchRandomMax = In.NumberAt(*Path(TEXT("recoil.pitchRandom")), 1);
		R.Shake = In.Number(*Path(TEXT("recoil.shake")));
		R.bWeave = In.Optional(*Path(TEXT("recoil.weaveAmp")), -1.0) >= 0.0;
		if (R.bWeave)
		{
			R.LateFrom = static_cast<int32>(In.Number(*Path(TEXT("recoil.lateFrom"))));
			R.LateScale = In.Number(*Path(TEXT("recoil.lateScale")));
			R.YawEarly = In.Number(*Path(TEXT("recoil.yawEarly")), RadToDeg);
			R.WeaveFrom = static_cast<int32>(In.Number(*Path(TEXT("recoil.weaveFrom"))));
			R.WeaveAmp = In.Number(*Path(TEXT("recoil.weaveAmp")), RadToDeg);
			R.WeaveFreq = In.Number(*Path(TEXT("recoil.weaveFreq")));
			R.WeaveRandom = In.Number(*Path(TEXT("recoil.weaveRandom")), RadToDeg);
		}
		else
		{
			R.Yaw = In.Number(*Path(TEXT("recoil.yaw")), RadToDeg);
		}

		G.WallStart = In.NumberAt(*Path(TEXT("wallPull")), 0, MetresToCm);
		G.WallFull = In.NumberAt(*Path(TEXT("wallPull")), 1, MetresToCm);
		G.FlashScale = In.Number(*Path(TEXT("flash.scale")));
		G.FlashLight = In.Number(*Path(TEXT("flash.light")));
		G.FlashColor = In.Color(*Path(TEXT("flash.lightColor")));
		G.FlashRange = In.Number(*Path(TEXT("flash.lightRange")), MetresToCm);
		G.FlashTtl = In.Number(*Path(TEXT("flash.lightTtl")));
		G.RumbleStrong = In.Number(*Path(TEXT("rumble.strong")));
		G.RumbleWeak = In.Number(*Path(TEXT("rumble.weak")));
		G.RumbleMs = In.Number(*Path(TEXT("rumble.ms")));
	}

	void ParseWeaponsCommon(FReader& In, FMIWeaponsData& W);

	void ParseWeapons(FReader& In, FMIWeaponsData& W)
	{
		using namespace MIDataSubsystemPrivate;
		for (const FString& Id : In.Strings(TEXT("weapons.common.order")))
		{
			ParseGunAt(In, FString::Printf(TEXT("weapons.%s."), *Id), W.Guns.AddDefaulted_GetRef());
		}
		ParseWeaponsCommon(In, W);
		// The per-gun fields of LOADOUT.md 4.9 take the values the web code uses implicitly (guns.json extraDefaults).
		for (FMIWeaponDef& G : W.Guns)
		{
			G.Holster = W.Common.Holster;
			G.Draw = W.Common.Draw;
			G.AdsFov = In.Number(TEXT("player.fov.ads"));
			G.AdsLook = 1.0;
			G.NoiseRadius = In.Optional(TEXT("enemies.ai.hear.gunfire"), 45.0, MetresToCm);
			G.FireModes = {G.bAuto ? FName(TEXT("auto")) : FName(TEXT("semi"))};
			G.SemiFireBuffer = In.Optional(TEXT("weapons.nine.fireBuffer"), 0.0);
			G.ModeSwitch = 0.35;
			G.InspectAfter = In.Optional(*FString::Printf(TEXT("weapons.%s.inspectAfter"), *G.Id.ToString()), 24.0);
			G.Pool = FMath::IsFinite(G.Reserve) ? FName(TEXT("bag")) : NAME_None;
		}
	}

	void ParseWeaponsCommon(FReader& In, FMIWeaponsData& W)
	{
		using namespace MIDataSubsystemPrivate;
		FMIWeaponCommonData& C = W.Common;
		C.HeadMultiplier = In.Number(TEXT("weapons.common.headMultiplier"));
		C.Holster = In.Number(TEXT("weapons.common.holster"));
		C.Draw = In.Number(TEXT("weapons.common.draw"));
		C.BurstReset = In.Number(TEXT("weapons.common.burstReset"));
		C.MaxCatchUpShots = static_cast<int32>(In.Number(TEXT("weapons.common.maxCatchUpShots")));
		C.SpreadRate = In.Number(TEXT("weapons.common.spreadRate"));
		C.BloomHold = In.Number(TEXT("weapons.common.bloomHold"));
		C.SpreadSpeedRef = In.Number(TEXT("weapons.common.spreadSpeedRef"), MetresToCm);
		C.AdsRecoilScale = In.Number(TEXT("weapons.common.adsRecoilScale"));
		C.CrouchRecoilScale = In.Number(TEXT("weapons.common.crouchRecoilScale"));
		C.SprintRate = In.Number(TEXT("weapons.common.sprintRate"));
		C.SprintHurry = In.Number(TEXT("weapons.common.sprintHurry"));
		C.SprintFireGate = In.Number(TEXT("weapons.common.sprintFireGate"));
		C.SprintAdsGate = In.Number(TEXT("weapons.common.sprintAdsGate"));
		C.FiringHold = In.Number(TEXT("weapons.common.firingHold"));
		C.WallEvery = In.Number(TEXT("weapons.common.wallEvery"));
		C.WallRate = In.Number(TEXT("weapons.common.wallRate"));
		C.WallAdsScale = In.Number(TEXT("weapons.common.wallAdsScale"));
		C.HeatPerShot = In.Number(TEXT("weapons.common.heat.perShot"));
		C.HeatMax = In.Number(TEXT("weapons.common.heat.max"));
		C.HeatCool = In.Number(TEXT("weapons.common.heat.cool"));
		C.TracerColor = In.Color(TEXT("weapons.common.tracer.color"));
		C.TracerSpeed = In.Number(TEXT("weapons.common.tracer.speed"), MetresToCm);
		C.LowAmmoFraction = In.Number(TEXT("weapons.common.lowAmmoFraction"));
		C.AdsFlashScale = In.Number(TEXT("weapons.common.adsFlashScale"));
		C.ExplosiveHitFromEnemy = In.Number(TEXT("weapons.common.explosiveHitFromEnemy"));
		C.AimSlow = In.Number(TEXT("player.input.pad.aimSlow"));
		C.AimRange = In.Number(TEXT("player.input.pad.aimRange"), MetresToCm);
		C.AimEvery = In.Number(TEXT("player.input.pad.aimEvery"));
		C.AimRate = In.Number(TEXT("player.input.pad.aimRate"));

		FMIMeleeData& M = W.Melee;
		M.Duration = In.Number(TEXT("weapons.melee.duration"));
		M.HitAt = In.Number(TEXT("weapons.melee.hitAt"));
		M.Reach = In.Number(TEXT("weapons.melee.reach"), MetresToCm);
		M.Cone = In.Number(TEXT("weapons.melee.cone"), RadToDeg);
		M.Damage = In.Number(TEXT("weapons.melee.damage"));
		M.Cooldown = In.Number(TEXT("weapons.melee.cooldown"));
		M.bCancelsReload = In.Bool(TEXT("weapons.melee.cancelsReload"));
		M.bBlockedWhileSwitching = In.Bool(TEXT("weapons.melee.blockedWhileSwitching"));
		M.Shake = In.Number(TEXT("weapons.melee.shake"));
	}

	/** Reads a formula's numbers and checks them against the game's own answers. */
	bool FunctionCoefficients(FReader& In, const TCHAR* Path, int32 Count, TArray<double>& Out,
		TFunctionRef<double(const TArray<double>&, const TArray<double>&)> Evaluate, FString& OutError)
	{
		TArray<TPair<TArray<double>, double>> Samples;
		Out = In.FunctionNumbers(Path, Samples);
		if (Out.Num() != Count || Samples.Num() == 0)
		{
			OutError = FString::Printf(TEXT("config.json: %s: expected %d numbers and some samples, found %d numbers, %d samples"), Path, Count, Out.Num(), Samples.Num());
			return false;
		}
		for (const TPair<TArray<double>, double>& Sample : Samples)
		{
			const double Value = Evaluate(Out, Sample.Key);
			if (!FMath::IsNearlyEqual(Value, Sample.Value, 1e-9))
			{
				OutError = FString::Printf(TEXT("config.json: %s answers %.9f where the game answered %.9f"), Path, Value, Sample.Value);
				return false;
			}
		}
		return true;
	}

	bool ParseExplosives(FReader& In, FMIExplosivesData& E, FString& OutError)
	{
		using namespace MIDataSubsystemPrivate;
		const TSharedPtr<FJsonObject> Kinds = In.Object(TEXT("explosives.kinds"));
		if (Kinds.IsValid())
		{
			for (const auto& Pair : Kinds->Values)
			{
				const TPair<FString, TSharedPtr<FJsonValue>> Entry(FString(*Pair.Key), Pair.Value);
				const auto Path = [&Entry](const TCHAR* Leaf) { return FString::Printf(TEXT("explosives.kinds.%s.%s"), *Entry.Key, Leaf); };
				FMIExplosiveKindData& K = E.Kinds.AddDefaulted_GetRef();
				K.Id = FName(*Entry.Key);
				K.Prop = In.String(*Path(TEXT("prop")));
				K.Hp = In.Number(*Path(TEXT("hp")));
				K.Fuse = In.Number(*Path(TEXT("fuse")));
				K.Radius = In.Number(*Path(TEXT("radius")), MetresToCm);
				K.Damage = In.Number(*Path(TEXT("damage")));
				K.Size = In.Number(*Path(TEXT("size")));
				// Web box [x, y, z] (y up) -> Unreal (X, Y, Z) = (x, z, y).
				K.Box = FVector(In.NumberAt(*Path(TEXT("box")), 0), In.NumberAt(*Path(TEXT("box")), 2), In.NumberAt(*Path(TEXT("box")), 1)) * MetresToCm;
				K.Jet = In.Number(*Path(TEXT("jet")));
			}
		}
		FMIExplosiveRulesData& R = E.Rules;
		R.PopFuse = In.Number(TEXT("explosives.rules.popFuse"));
		R.PlayerDamageScale = In.Number(TEXT("explosives.rules.playerDamageScale"));
		R.DamageFromEnemyRound = In.Number(TEXT("explosives.rules.damageFromEnemyRound"));
		R.ShakeReach = In.Number(TEXT("explosives.rules.shakeReach"), MetresToCm);
		R.AlertRadius = In.Number(TEXT("explosives.rules.alertRadius"), MetresToCm);

		TArray<double> N;
		// (size) => 2.2 + 1.6 * size
		if (!FunctionCoefficients(In, TEXT("explosives.rules.chainRange"), 2, N,
				[](const TArray<double>& C, const TArray<double>& A) { return C[0] + C[1] * A[0]; }, OutError))
		{
			return false;
		}
		R.ChainBase = N[0];
		R.ChainPerSize = N[1];
		// (dist, roll) => 0.14 + roll * 0.3 + 0.03 * dist
		if (!FunctionCoefficients(In, TEXT("explosives.rules.chainFuse"), 3, N,
				[](const TArray<double>& C, const TArray<double>& A) { return C[0] + A[1] * C[1] + C[2] * A[0]; }, OutError))
		{
			return false;
		}
		R.FuseBase = N[0];
		R.FuseRoll = N[1];
		R.FusePerMetre = N[2];
		// (radius) => Math.min(2.6, Math.max(0.6, 0.47 + 0.244 * radius))
		if (!FunctionCoefficients(In, TEXT("explosives.rules.sizeFromRadius"), 4, N,
				[](const TArray<double>& C, const TArray<double>& A) { return FMath::Min(C[0], FMath::Max(C[1], C[2] + C[3] * A[0])); }, OutError))
		{
			return false;
		}
		R.SizeMax = N[0];
		R.SizeMin = N[1];
		R.SizeBase = N[2];
		R.SizePerMetre = N[3];
		return true;
	}
}


void UMIDataSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);

	FString Error;
	bLoaded = LoadJsonFile(TEXT("config.json"), ConfigJson, Error) && ParseConfig(ConfigJson, Config, Error);
	if (bLoaded)
	{
		UE_LOG(LogMI, Log, TEXT("Data: config.json loaded (%s, schema %d, seed %d) from %s"),
			*Config.Game, Config.Schema, Config.Seed, *GetDataDir());
	}
	else
	{
		ConfigJson.Reset();
		UE_LOG(LogMI, Error, TEXT("Data: %s"), *Error);
	}

	// The loadout files never fail the config load: without them the front end offers only the parity set-up.
	FString LoadoutError;
	bLoadoutLoaded = bLoaded && FMILoadoutData::Load(Loadout, LoadoutError);
	if (bLoadoutLoaded)
	{
		TArray<FString> Problems;
		Loadout.ValidateData(Problems);
		for (const FString& P : Problems)
		{
			UE_LOG(LogMI, Error, TEXT("Data: loadout: %s"), *P);
		}
		UE_LOG(LogMI, Log, TEXT("Data: loadout loaded (%d guns, %d parts, %d crew, %d levels, %d problems)"),
			Loadout.Guns.Num(), Loadout.Attachments.Num(), Loadout.Crew.Num(), Loadout.Levels.Num(), Problems.Num());
	}
	else if (bLoaded)
	{
		UE_LOG(LogMI, Error, TEXT("Data: loadout files did not load, only the parity set-up is offered: %s"), *LoadoutError);
	}
}

const UMIDataSubsystem* UMIDataSubsystem::Get(const UObject* WorldContextObject)
{
	const UGameInstance* GameInstance = WorldContextObject ? UGameplayStatics::GetGameInstance(WorldContextObject) : nullptr;
	return GameInstance ? GameInstance->GetSubsystem<UMIDataSubsystem>() : nullptr;
}

FString UMIDataSubsystem::GetDataDir()
{
	return FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Data"));
}

bool UMIDataSubsystem::LoadJsonFile(const FString& FileName, TSharedPtr<FJsonObject>& OutRoot, FString& OutError)
{
	const FString Path = FPaths::Combine(GetDataDir(), FileName);
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *Path))
	{
		OutError = FString::Printf(TEXT("cannot read %s"), *Path);
		return false;
	}
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, OutRoot) || !OutRoot.IsValid())
	{
		OutError = FString::Printf(TEXT("%s is not valid JSON: %s"), *Path, *Reader->GetErrorMessage());
		return false;
	}
	return true;
}

bool UMIDataSubsystem::ParseConfig(const TSharedPtr<FJsonObject>& Root, FMIConfigData& Out, FString& OutError)
{
	using namespace MIDataSubsystemPrivate;
	using namespace MIDataSubsystemParse;
	Out = FMIConfigData();
	if (!Root.IsValid())
	{
		OutError = TEXT("config.json: no document");
		return false;
	}
	FReader In{Root};

	Out.Game = In.String(TEXT("meta.game"));
	Out.Schema = static_cast<int32>(In.Number(TEXT("meta.schema")));
	Out.Seed = static_cast<int32>(In.Number(TEXT("meta.seed")));

	FMIPlayerData& P = Out.Player;
	P.Body.Radius = In.Number(TEXT("player.body.radius"), MetresToCm);
	P.Body.Height = In.Number(TEXT("player.body.height"), MetresToCm);
	P.Body.CrouchHeight = In.Number(TEXT("player.body.crouchHeight"), MetresToCm);
	P.Body.Eye = In.Number(TEXT("player.body.eye"), MetresToCm);
	P.Body.CrouchEye = In.Number(TEXT("player.body.crouchEye"), MetresToCm);
	P.Body.EyeRate = In.Number(TEXT("player.body.eyeRate"));
	P.Body.StepHeight = In.Number(TEXT("player.body.stepHeight"), MetresToCm);

	P.Speed.Walk = In.Number(TEXT("player.speed.walk"), MetresToCm);
	P.Speed.Sprint = In.Number(TEXT("player.speed.sprint"), MetresToCm);
	P.Speed.Crouch = In.Number(TEXT("player.speed.crouch"), MetresToCm);
	P.Speed.Ads = In.Number(TEXT("player.speed.ads"), MetresToCm);
	P.Speed.Backpedal = In.Number(TEXT("player.speed.backpedal"));

	P.Accel.Ground = In.Number(TEXT("player.accel.ground"), MetresToCm);
	P.Accel.GroundStop = In.Number(TEXT("player.accel.groundStop"), MetresToCm);
	P.Accel.Air = In.Number(TEXT("player.accel.air"), MetresToCm);
	P.Accel.AirStop = In.Number(TEXT("player.accel.airStop"), MetresToCm);

	P.Jump.Gravity = In.Number(TEXT("player.jump.gravity"), MetresToCm);
	P.Jump.Apex = In.Number(TEXT("player.jump.apex"), MetresToCm);
	P.Jump.Coyote = In.Number(TEXT("player.jump.coyote"));
	P.Jump.Buffer = In.Number(TEXT("player.jump.buffer"));
	P.Jump.Terminal = In.Number(TEXT("player.jump.terminal"), MetresToCm);

	P.Sprint.MinForward = In.Number(TEXT("player.sprint.minForward"));
	P.Sprint.MaxStrafe = In.Number(TEXT("player.sprint.maxStrafe"));
	P.Sprint.MinSpeedFrac = In.Number(TEXT("player.sprint.minSpeedFrac"));

	P.Fov.Base = In.Number(TEXT("player.fov.base"));
	P.Fov.Min = In.Number(TEXT("player.fov.min"));
	P.Fov.Max = In.Number(TEXT("player.fov.max"));
	P.Fov.SprintAdd = In.Number(TEXT("player.fov.sprintAdd"));
	P.Fov.Ads = In.Number(TEXT("player.fov.ads"));
	P.Fov.Rate = In.Number(TEXT("player.fov.rate"));

	P.Look.PitchLimit = In.Number(TEXT("player.look.pitchLimit"), RadToDeg);
	P.Look.MouseDegreesPerCount = In.Number(TEXT("player.input.mouse"), RadToDeg);
	P.Look.WheelDebounce = In.Number(TEXT("player.input.wheelDebounce"));

	ParsePlayerRest(In, P);
	ParseWeapons(In, Out.Weapons);
	if (!ParseExplosives(In, Out.Explosives, OutError))
	{
		return false;
	}

	// Difficulty: only the player's share (regeneration) for now; the enemy tables belong to their package.
	const TSharedPtr<FJsonObject> Difficulty = In.Object(TEXT("flow.difficulty"));
	if (Difficulty.IsValid())
	{
		for (const auto& Pair : Difficulty->Values)
		{
			const TPair<FString, TSharedPtr<FJsonValue>> Entry(FString(*Pair.Key), Pair.Value);
			FMIDifficultyData D;
			D.Id = FName(*Entry.Key);
			D.RegenDelay = In.Number(*FString::Printf(TEXT("flow.difficulty.%s.regen.delay"), *Entry.Key));
			D.RegenRate = In.Number(*FString::Printf(TEXT("flow.difficulty.%s.regen.rate"), *Entry.Key));
			Out.Difficulties.Add(D);
		}
	}
	Out.DefaultDifficulty = FName(*In.String(TEXT("flow.defaultDifficulty")));
	Out.Settings.Sensitivity = In.Number(TEXT("settings.defaults.sens"));
	Out.Settings.bInvertY = In.Bool(TEXT("settings.defaults.invertY"));
	Out.Settings.Fov = In.Number(TEXT("settings.defaults.fov"));

	if (In.Missing.Num() > 0)
	{
		OutError = FString::Printf(TEXT("config.json: %d field(s) missing: %s"), In.Missing.Num(), *FString::Join(In.Missing, TEXT(", ")));
		return false;
	}
	return true;
}

bool UMIDataSubsystem::LoadConfig(FMIConfigData& Out, FString& OutError)
{
	TSharedPtr<FJsonObject> Root;
	return LoadJsonFile(TEXT("config.json"), Root, OutError) && ParseConfig(Root, Out, OutError);
}

bool UMIDataSubsystem::ParseGun(const TSharedPtr<FJsonObject>& Rules, const TSharedPtr<FJsonObject>& Extra, FMIWeaponDef& Out, FString& OutError)
{
	using namespace MIDataSubsystemPrivate;
	using namespace MIDataSubsystemParse;
	Out = FMIWeaponDef();
	if (!Rules.IsValid() || !Extra.IsValid())
	{
		OutError = TEXT("ParseGun: no rules or no extra object");
		return false;
	}
	FReader In{Rules};
	ParseGunAt(In, FString(), Out);
	FReader X{Extra};
	Out.Holster = X.Number(TEXT("holster"));
	Out.Draw = X.Number(TEXT("draw"));
	Out.AdsFov = X.Number(TEXT("adsFov"));
	Out.AdsLook = X.Number(TEXT("adsLook"));
	Out.NoiseRadius = X.Number(TEXT("noise"), MetresToCm);
	Out.FalloffStart = X.NumberOrInfinity(TEXT("falloff.start"), MetresToCm);
	Out.FalloffEnd = X.NumberOrInfinity(TEXT("falloff.end"), MetresToCm);
	Out.FalloffMin = X.Number(TEXT("falloff.min"));
	Out.FireModes.Reset();
	for (const FString& M : X.Strings(TEXT("fireModes")))
	{
		Out.FireModes.Add(FName(*M));
	}
	Out.SemiFireBuffer = X.Number(TEXT("semiFireBuffer"));
	Out.ModeSwitch = X.Number(TEXT("modeSwitch"));
	Out.InspectAfter = In.Optional(TEXT("inspectAfter"), X.Number(TEXT("inspectAfter")));
	const FString Pool = X.String(TEXT("pool"));
	Out.Pool = FMath::IsFinite(Out.Reserve) && !Pool.IsEmpty() ? FName(*Pool) : NAME_None;
	TArray<FString> Missing = In.Missing;
	Missing.Append(X.Missing);
	if (Out.FireModes.Num() == 0)
	{
		Missing.Add(TEXT("extra.fireModes"));
	}
	if (Missing.Num() > 0)
	{
		OutError = FString::Printf(TEXT("gun %s: %d field(s) missing: %s"), *Out.Id.ToString(), Missing.Num(), *FString::Join(Missing, TEXT(", ")));
		return false;
	}
	return true;
}

bool UMIDataSubsystem::ParseWeaponsCommon(const TSharedPtr<FJsonObject>& ConfigRoot, FMIWeaponsData& Out, FString& OutError)
{
	using namespace MIDataSubsystemParse;
	MIDataSubsystemPrivate::FReader In{ConfigRoot};
	MIDataSubsystemParse::ParseWeaponsCommon(In, Out);
	if (In.Missing.Num() > 0)
	{
		OutError = FString::Printf(TEXT("config.json: %s"), *FString::Join(In.Missing, TEXT(", ")));
		return false;
	}
	return true;
}
