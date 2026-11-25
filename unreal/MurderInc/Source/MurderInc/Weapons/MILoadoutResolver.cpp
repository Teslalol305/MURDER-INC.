#include "Weapons/MILoadoutResolver.h"

#include "Core/Data/MIDataSubsystem.h"
#include <limits>

namespace MILoadoutResolverPrivate
{
	/** Every number under Value (objects and arrays), each through Fn. */
	void ForEachNumber(const TSharedPtr<FJsonValue>& Value, TFunctionRef<TSharedPtr<FJsonValue>(const TSharedPtr<FJsonValue>&)> Fn, TSharedPtr<FJsonValue>& Out)
	{
		Out = Value;
		if (!Value.IsValid())
		{
			return;
		}
		if (Value->Type == EJson::Number)
		{
			Out = Fn(Value);
		}
		else if (Value->Type == EJson::Array)
		{
			TArray<TSharedPtr<FJsonValue>> Items;
			for (const TSharedPtr<FJsonValue>& E : Value->AsArray())
			{
				TSharedPtr<FJsonValue> R;
				ForEachNumber(E, Fn, R);
				Items.Add(R);
			}
			Out = MakeShared<FJsonValueArray>(Items);
		}
		else if (Value->Type == EJson::Object)
		{
			TSharedPtr<FJsonObject> O = MakeShared<FJsonObject>();
			for (const auto& Pair : Value->AsObject()->Values)
			{
				TSharedPtr<FJsonValue> R;
				ForEachNumber(Pair.Value, Fn, R);
				O->SetField(FString(*Pair.Key), R);
			}
			Out = MakeShared<FJsonValueObject>(O);
		}
	}

	double Clamp(const FMIStatTarget& T, double V)
	{
		return T.bClamp ? FMath::Min(T.Max, FMath::Max(T.Min, V)) : V;
	}
}

bool FMILoadoutResolver::LoadRoots(TSharedPtr<FJsonObject>& OutConfig, TSharedPtr<FJsonObject>& OutPresentation, FString& OutError)
{
	return UMIDataSubsystem::LoadJsonFile(TEXT("config.json"), OutConfig, OutError)
		&& UMIDataSubsystem::LoadJsonFile(TEXT("presentation.json"), OutPresentation, OutError);
}

TSharedPtr<FJsonObject> FMILoadoutResolver::FilledExtra(const FMIGunEntry& Gun) const
{
	TSharedPtr<FJsonObject> Extra = MIJson::DeepCopy(Gun.Extra.IsValid() ? Gun.Extra : MakeShared<FJsonObject>());
	for (const auto& Pair : Data.ExtraDefaults->Values)
	{
		const FString Key(*Pair.Key);
		const TSharedPtr<FJsonValue> Have = Extra->TryGetField(Key);
		if (!Have.IsValid() || Have->IsNull())
		{
			Extra->SetField(Key, MIJson::DeepCopy(Pair.Value));
		}
		else if (Have->Type == EJson::Object && Pair.Value->Type == EJson::Object)
		{
			// A partial object (falloff {start, end} without min) takes the missing members.
			for (const auto& Member : Pair.Value->AsObject()->Values)
			{
				if (!Have->AsObject()->HasField(FString(*Member.Key)))
				{
					Have->AsObject()->SetField(FString(*Member.Key), MIJson::DeepCopy(Member.Value));
				}
			}
		}
	}
	// Numbers everywhere a multiplication may land ("Infinity" is a number to the parser and to the ops).
	if (const TSharedPtr<FJsonValue> F = Extra->TryGetField(TEXT("falloff")); F.IsValid() && F->Type == EJson::Object)
	{
		for (const TCHAR* K : {TEXT("start"), TEXT("end"), TEXT("min")})
		{
			double V = 0.0;
			if (MIJson::Number(F->AsObject()->TryGetField(K), V)) F->AsObject()->SetField(K, MIJson::MakeNumber(V));
		}
	}
	return Extra;
}

TArray<const FMIAttachmentDef*> FMILoadoutResolver::FittedParts(FName GunId, const FMIGunBuild* Build) const
{
	TArray<const FMIAttachmentDef*> Out;
	const FMIGunEntry* Gun = Data.FindGun(GunId);
	if (!Gun || !Build)
	{
		return Out;
	}
	for (const FMISlotDef& Slot : Data.Slots)
	{
		const FName* Part = Build->Parts.Find(Slot.Id);
		if (Part && !Part->IsNone())
		{
			if (const FMIAttachmentDef* P = Data.FindPart(*Part)) Out.Add(P);
		}
	}
	return Out;
}

bool FMILoadoutResolver::ApplyEffects(const TArray<const FMIAttachmentDef*>& Parts, const TSharedPtr<FJsonObject>& Doc, FString& OutError) const
{
	using namespace MILoadoutResolverPrivate;
	// Per stat, the ops of every fitted part, in slot order (the parts come in slot order).
	struct FOps
	{
		TOptional<double> Set;
		double Add = 0.0;
		bool bAdd = false;
		double Mul = 1.0;
		bool bMul = false;
		TOptional<double> Min, Max;
	};
	TMap<FName, FOps> ByStat;
	TArray<FName> Order;  // stats in the order of attachments.json stats (deterministic)
	for (const FMIAttachmentDef* P : Parts)
	{
		for (const FMIEffect& E : P->Effects)
		{
			FOps& O = ByStat.FindOrAdd(E.Stat);
			if (E.Op == TEXT("set")) O.Set = E.Value;
			else if (E.Op == TEXT("add")) { O.Add += E.Value; O.bAdd = true; }
			else if (E.Op == TEXT("mul")) { O.Mul *= E.Value; O.bMul = true; }
			else if (E.Op == TEXT("min")) O.Min = O.Min.IsSet() ? FMath::Min(O.Min.GetValue(), E.Value) : E.Value;
			else if (E.Op == TEXT("max")) O.Max = O.Max.IsSet() ? FMath::Max(O.Max.GetValue(), E.Value) : E.Value;
			else { OutError = FString::Printf(TEXT("%s: unknown op %s"), *P->Id.ToString(), *E.Op.ToString()); return false; }
		}
	}
	for (const TPair<FName, FOps>& Pair : ByStat)
	{
		const FMIStatDef* Stat = Data.Stats.Find(Pair.Key);
		if (!Stat)
		{
			OutError = FString::Printf(TEXT("unknown stat %s"), *Pair.Key.ToString());
			return false;
		}
		const FOps& O = Pair.Value;
		const bool bMulti = Stat->Targets.Num() > 1 || (Stat->Targets.Num() == 1 && Stat->Targets[0].Path.EndsWith(TEXT("*")));
		if (bMulti)
		{
			if (O.Set.IsSet() || O.bAdd || O.Min.IsSet() || O.Max.IsSet())
			{
				OutError = FString::Printf(TEXT("%s has several targets and takes only mul"), *Pair.Key.ToString());
				return false;
			}
			const double Factor = FMath::Min(Data.FactorMax, FMath::Max(Data.FactorMin, O.Mul));
			for (const FMIStatTarget& T : Stat->Targets)
			{
				if (T.Path.EndsWith(TEXT(".*")))
				{
					// Every number under the object, no clamp: the marks stay exactly marks x factor.
					const FString Parent = T.Path.LeftChop(2);
					const TSharedPtr<FJsonValue> V = MIJson::Get(Doc, Parent);
					if (!V.IsValid()) continue;
					TSharedPtr<FJsonValue> R;
					ForEachNumber(V, [Factor](const TSharedPtr<FJsonValue>& N) { return MIJson::MakeNumber(N->AsNumber() * Factor); }, R);
					MIJson::Set(Doc, Parent, R);
					continue;
				}
				double V = 0.0;
				if (!MIJson::Number(MIJson::Get(Doc, T.Path), V)) continue;  // a target the gun lacks is skipped
				MIJson::Set(Doc, T.Path, MIJson::MakeNumber(Clamp(T, V * Factor)));
			}
			continue;
		}
		const FMIStatTarget& T = Stat->Targets[0];
		double V = 0.0;
		if (!MIJson::Number(MIJson::Get(Doc, T.Path), V))
		{
			continue;
		}
		if (O.Set.IsSet()) V = O.Set.GetValue();
		if (O.bAdd) V += O.Add;
		if (O.bMul) V *= O.Mul;
		if (O.Min.IsSet()) V = FMath::Min(V, O.Min.GetValue());
		if (O.Max.IsSet()) V = FMath::Max(V, O.Max.GetValue());
		MIJson::Set(Doc, T.Path, MIJson::MakeNumber(Clamp(T, V)));
	}
	// Falloff: end never before start (start == end is a step to min).
	double Start = 0.0, End = 0.0;
	if (MIJson::Number(MIJson::Get(Doc, TEXT("extra.falloff.start")), Start) && MIJson::Number(MIJson::Get(Doc, TEXT("extra.falloff.end")), End) && End < Start)
	{
		MIJson::Set(Doc, TEXT("extra.falloff.end"), MIJson::MakeNumber(Start));
	}
	return true;
}

bool FMILoadoutResolver::ResolveGun(FName GunId, const FMIGunBuild* Build, const FMIReadiness* Ready, FMIResolvedGun& Out, FString& OutError) const
{
	Out = FMIResolvedGun();
	const FMIGunEntry* Gun = Data.FindGun(GunId);
	if (!Gun || !Gun->Rules.IsValid() || !Gun->Presentation.IsValid())
	{
		OutError = FString::Printf(TEXT("no gun %s"), *GunId.ToString());
		return false;
	}
	Out.Id = GunId;
	// 2. Copy; 3. fill the defaults.
	Out.Rules = MIJson::DeepCopy(Gun->Rules);
	Out.Extra = FilledExtra(*Gun);
	Out.Presentation = MIJson::DeepCopy(Gun->Presentation);
	// 4. The effects, only when a part is fitted: a gun with no parts is its JSON untouched.
	const TArray<const FMIAttachmentDef*> Parts = FittedParts(GunId, Build);
	bool bAnyEffect = false;
	for (const FMIAttachmentDef* P : Parts) bAnyEffect |= P->Effects.Num() > 0;
	if (bAnyEffect)
	{
		TSharedPtr<FJsonObject> Doc = MakeShared<FJsonObject>();
		Doc->SetObjectField(TEXT("rules"), Out.Rules);
		Doc->SetObjectField(TEXT("extra"), Out.Extra);
		if (!ApplyEffects(Parts, Doc, OutError))
		{
			return false;
		}
		Out.Rules = Doc->GetObjectField(TEXT("rules"));
		Out.Extra = Doc->GetObjectField(TEXT("extra"));
	}
	// The base mesh of the build's variant; the presentation parser needs a mesh path.
	FMIReadiness Fallback;
	Fallback.Data = &Data;
	Out.BaseMesh = (Ready ? *Ready : Fallback).BaseMesh(GunId, Build);
	// The real art's own frame, sockets and parts (presentation "real", e.g. SK_Nine for the NINE, the pack rifle for
	// the CHOPPER): only when the real mesh is the one drawn, so a clean checkout keeps the template's numbers.
	const FString RealMesh = MIJson::StringOr(Out.Presentation, TEXT("realMesh"));
	const TSharedPtr<FJsonValue> Real = Out.Presentation->TryGetField(TEXT("real"));
	if (!RealMesh.IsEmpty() && RealMesh == Out.BaseMesh && Real.IsValid() && Real->Type == EJson::Object)
	{
		for (const auto& Pair : Real->AsObject()->Values)
		{
			Out.Presentation->SetField(FString(*Pair.Key), MIJson::DeepCopy(Pair.Value));
		}
	}
	if (!Out.Presentation->HasTypedField<EJson::String>(TEXT("mesh")) || MIJson::StringOr(Out.Presentation, TEXT("mesh")) != Out.BaseMesh)
	{
		Out.Presentation->SetStringField(TEXT("mesh"), Out.BaseMesh);
	}
	// The factory magazine the stage draws: the gun's own presentation.magazine {mesh, bone}, else its anim set's magazine
	// {full, socket} (the same mesh the first-person rig seats), so the Workbench shows a longer magazine as a change.
	{
		FString Mag = MIJson::StringOr(Out.Presentation, TEXT("magazine.mesh"));
		FString At = MIJson::StringOr(Out.Presentation, TEXT("magazine.bone"));
		const FString SetName = MIJson::StringOr(Out.Presentation, TEXT("animSet"));
		if (Mag.IsEmpty() && !SetName.IsEmpty() && Presentation.IsValid())
		{
			const FString Key = TEXT("firstPerson.animSets.") + SetName + TEXT(".magazine");
			Mag = MIJson::StringOr(Presentation, Key + TEXT(".full"));
			At = MIJson::StringOr(Presentation, Key + TEXT(".socket"));
		}
		Out.MagazineMesh = Mag;
		Out.MagazineAttach = At.IsEmpty() ? NAME_None : FName(*At);
	}
	// 5. Parse once: the rules and the view from the same JSON, so they agree.
	if (!UMIDataSubsystem::ParseGun(Out.Rules, Out.Extra, Out.Def, OutError) || !FMIViewmodelData::ParseGunView(Out.Presentation, Out.Rules, Out.View, OutError))
	{
		OutError = FString::Printf(TEXT("%s: %s"), *GunId.ToString(), *OutError);
		return false;
	}
	Out.View.Id = Out.Def.Id;
	for (const FMIAttachmentDef* P : Parts)
	{
		Out.Def.Fitted.Add(P->Slot, P->Id);
		Out.Def.bSuppressed |= P->bSuppressed;
		Out.bLaser |= P->bLaser;
		if (P->Variant.IsNone() && !P->bBaseline)
		{
			FMIResolvedPart& R = Out.Parts.AddDefaulted_GetRef();
			R.Slot = P->Slot;
			R.Part = P->Id;
			R.Mesh = P->Mesh;
			if (const FMIGunMount* M = Gun->Mounts.Find(P->Slot))
			{
				R.Socket = M->Socket;
				R.Hide = M->Hide;
				R.RideBone = M->RideBone;
			}
			R.Markers = P->Sockets;
		}
		if (P->Relief > 0.0 && !P->bBaseline)
		{
			Out.View.Relief = P->Relief;  // the optic's eye relief replaces the gun's
		}
	}
	return true;
}

bool FMILoadoutResolver::Resolve(const FMIRunSetup& Setup, const FMIReadiness* Ready, FMIResolvedRun& Out, FString& OutError) const
{
	Out = FMIResolvedRun();
	if (Setup.Guns.Num() == 0)
	{
		OutError = TEXT("the set-up carries no gun");
		return false;
	}
	// 6. Common, melee and the global view data from the root documents, unchanged.
	if (!UMIDataSubsystem::ParseWeaponsCommon(Config, Out.Weapons, OutError) || !FMIViewmodelData::Parse(Presentation, Config, Out.View, OutError))
	{
		return false;
	}
	Out.View.Guns.Reset();
	for (int32 I = 0; I < Setup.Guns.Num(); ++I)
	{
		FMIResolvedGun& G = Out.Guns.AddDefaulted_GetRef();
		if (!ResolveGun(Setup.Guns[I], Setup.BuildOf(Setup.Guns[I]), Ready, G, OutError))
		{
			return false;
		}
		G.Def.Slot = I + 1;
		Out.Weapons.Guns.Add(G.Def);
		Out.View.Guns.Add(G.View);
	}
	return true;
}

FMIGunBars FMIGunBars::Of(const FMIResolvedGun& Gun, double GoonHp)
{
	const auto Num = [&Gun](const TCHAR* Path) { return MIJson::NumberOr(Gun.Rules, Path, 0.0); };
	const auto Unit = [](double V) { return FMath::Clamp(V, 0.0, 1.0); };
	FMIGunBars B;
	const double Damage = Num(TEXT("damage"));
	double Draw = MIJson::NumberOr(Gun.Extra, TEXT("draw"), 0.32);
	// Body shots at 10 m: damage after the falloff at that range.
	double Start = std::numeric_limits<double>::infinity(), End = Start, Min = 1.0;
	MIJson::Number(MIJson::Get(Gun.Extra, TEXT("falloff.start")), Start);
	MIJson::Number(MIJson::Get(Gun.Extra, TEXT("falloff.end")), End);
	MIJson::Number(MIJson::Get(Gun.Extra, TEXT("falloff.min")), Min);
	double At10 = Damage;
	if (10.0 > Start)
	{
		At10 = Damage * (End <= Start ? Min : FMath::Lerp(1.0, Min, FMath::Min(1.0, (10.0 - Start) / (End - Start))));
	}
	B.Rounds = At10 > 0.0 ? FMath::CeilToInt32(GoonHp / At10 - 1e-9) : 0;
	const double Rpm = Num(TEXT("rpm"));
	B.KillTime = Rpm > 0.0 ? (B.Rounds - 1) * 60.0 / Rpm : 0.0;
	B.Damage = Unit(Damage / 40.0);
	B.Kill = Unit(1.0 - (B.KillTime - 0.2) / 0.4);
	B.Control = Unit(1.0 - (Num(TEXT("recoil.pitch")) - 0.002) / 0.008);
	B.Handling = (Unit(1.0 - (Num(TEXT("adsTime")) - 0.10) / 0.25) + Unit(1.0 - (Draw - 0.2) / 0.25)) * 0.5;
	B.Aimed = Unit(1.0 - (Num(TEXT("spread.ads")) - 0.0005) / 0.0035);
	B.Hip = Unit(1.0 - (Num(TEXT("spread.hip")) - 0.006) / 0.010);
	return B;
}
