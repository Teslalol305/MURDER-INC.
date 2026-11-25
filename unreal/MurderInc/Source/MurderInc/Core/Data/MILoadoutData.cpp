#include "Core/Data/MILoadoutData.h"

#include "Core/Data/MIDataSubsystem.h"
#include "Misc/PackageName.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include <limits>

// ================================================================================================== JSON helpers

namespace MIJson
{
	TSharedPtr<FJsonValue> DeepCopy(const TSharedPtr<FJsonValue>& Value)
	{
		if (!Value.IsValid())
		{
			return Value;
		}
		switch (Value->Type)
		{
		case EJson::Object:
			return MakeShared<FJsonValueObject>(DeepCopy(Value->AsObject()));
		case EJson::Array:
		{
			TArray<TSharedPtr<FJsonValue>> Items;
			for (const TSharedPtr<FJsonValue>& V : Value->AsArray())
			{
				Items.Add(DeepCopy(V));
			}
			return MakeShared<FJsonValueArray>(Items);
		}
		default:
			return Value;  // numbers, strings, booleans and null are immutable
		}
	}

	TSharedPtr<FJsonObject> DeepCopy(const TSharedPtr<FJsonObject>& Object)
	{
		if (!Object.IsValid())
		{
			return Object;
		}
		TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
		for (const auto& Pair : Object->Values)
		{
			Out->SetField(FString(*Pair.Key), DeepCopy(Pair.Value));
		}
		return Out;
	}

	/** "a.b[1].c" -> ("a", -1), ("b", 1), ("c", -1) */
	static void Split(const FString& Path, TArray<TPair<FString, int32>>& Out)
	{
		TArray<FString> Parts;
		Path.ParseIntoArray(Parts, TEXT("."));
		for (const FString& Part : Parts)
		{
			int32 Open = INDEX_NONE;
			if (Part.FindChar(TEXT('['), Open) && Part.EndsWith(TEXT("]")))
			{
				Out.Add({Part.Left(Open), FCString::Atoi(*Part.Mid(Open + 1, Part.Len() - Open - 2))});
			}
			else
			{
				Out.Add({Part, INDEX_NONE});
			}
		}
	}

	TSharedPtr<FJsonValue> Get(const TSharedPtr<FJsonObject>& Root, const FString& Path)
	{
		TArray<TPair<FString, int32>> Keys;
		Split(Path, Keys);
		TSharedPtr<FJsonValue> V;
		if (Root.IsValid()) V = MakeShared<FJsonValueObject>(Root);
		for (const TPair<FString, int32>& K : Keys)
		{
			if (!V.IsValid() || V->Type != EJson::Object)
			{
				return nullptr;
			}
			V = V->AsObject()->TryGetField(K.Key);
			if (K.Value != INDEX_NONE)
			{
				if (!V.IsValid() || V->Type != EJson::Array || !V->AsArray().IsValidIndex(K.Value))
				{
					return nullptr;
				}
				V = V->AsArray()[K.Value];
			}
		}
		return V;
	}

	bool Set(const TSharedPtr<FJsonObject>& Root, const FString& Path, const TSharedPtr<FJsonValue>& Value)
	{
		TArray<TPair<FString, int32>> Keys;
		Split(Path, Keys);
		if (Keys.Num() == 0 || !Root.IsValid())
		{
			return false;
		}
		TSharedPtr<FJsonObject> O = Root;
		for (int32 I = 0; I < Keys.Num() - 1; ++I)
		{
			const TSharedPtr<FJsonValue> V = O->TryGetField(Keys[I].Key);
			TSharedPtr<FJsonValue> Child = V;
			if (Keys[I].Value != INDEX_NONE)
			{
				if (!V.IsValid() || V->Type != EJson::Array || !V->AsArray().IsValidIndex(Keys[I].Value)) return false;
				Child = V->AsArray()[Keys[I].Value];
			}
			if (!Child.IsValid() || Child->Type != EJson::Object) return false;
			O = Child->AsObject();
		}
		const TPair<FString, int32>& Leaf = Keys.Last();
		if (Leaf.Value == INDEX_NONE)
		{
			O->SetField(Leaf.Key, Value);
			return true;
		}
		const TSharedPtr<FJsonValue> V = O->TryGetField(Leaf.Key);
		if (!V.IsValid() || V->Type != EJson::Array || !V->AsArray().IsValidIndex(Leaf.Value))
		{
			return false;
		}
		TArray<TSharedPtr<FJsonValue>> Items = V->AsArray();
		Items[Leaf.Value] = Value;
		O->SetArrayField(Leaf.Key, Items);
		return true;
	}

	bool Number(const TSharedPtr<FJsonValue>& Value, double& Out)
	{
		if (!Value.IsValid())
		{
			return false;
		}
		if (Value->Type == EJson::Number)
		{
			Out = Value->AsNumber();
			return true;
		}
		if (Value->Type == EJson::String)
		{
			const FString S = Value->AsString();
			if (S == TEXT("Infinity")) { Out = std::numeric_limits<double>::infinity(); return true; }
			if (S == TEXT("-Infinity")) { Out = -std::numeric_limits<double>::infinity(); return true; }
		}
		return false;
	}

	double NumberOr(const TSharedPtr<FJsonObject>& Root, const FString& Path, double Fallback)
	{
		double V = 0.0;
		return Number(Get(Root, Path), V) ? V : Fallback;
	}

	FString StringOr(const TSharedPtr<FJsonObject>& Root, const FString& Path, const FString& Fallback)
	{
		const TSharedPtr<FJsonValue> V = Get(Root, Path);
		return V.IsValid() && V->Type == EJson::String ? V->AsString() : Fallback;
	}

	TArray<FName> Names(const TSharedPtr<FJsonObject>& Root, const FString& Path)
	{
		TArray<FName> Out;
		const TSharedPtr<FJsonValue> V = Get(Root, Path);
		if (V.IsValid() && V->Type == EJson::Array)
		{
			for (const TSharedPtr<FJsonValue>& E : V->AsArray())
			{
				if (E.IsValid() && E->Type == EJson::String) Out.Add(FName(*E->AsString()));
			}
		}
		return Out;
	}

	FString Print(const TSharedPtr<FJsonObject>& Object)
	{
		FString Out;
		const TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> Writer = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Out);
		if (Object.IsValid())
		{
			FJsonSerializer::Serialize(Object.ToSharedRef(), Writer);
		}
		return Out;
	}

	TSharedPtr<FJsonValue> MakeNumber(double V)
	{
		return MakeShared<FJsonValueNumber>(V);
	}
}

// ================================================================================================== set-up

bool FMIGunBuild::operator==(const FMIGunBuild& O) const
{
	if (Parts.Num() != O.Parts.Num())
	{
		return false;
	}
	for (const TPair<FName, FName>& P : Parts)
	{
		const FName* Other = O.Parts.Find(P.Key);
		if (!Other || *Other != P.Value) return false;
	}
	return true;
}

FName FMIRunSetup::PartIn(FName Gun, FName Slot) const
{
	const FMIGunBuild* B = Builds.Find(Gun);
	const FName* P = B ? B->Parts.Find(Slot) : nullptr;
	return P ? *P : NAME_None;
}

bool FMIRunSetup::SameLoadout(const FMIRunSetup& O) const
{
	if (Crew != O.Crew || Guns != O.Guns || Level != O.Level || Mode != O.Mode || Difficulty != O.Difficulty || Time != O.Time)
	{
		return false;
	}
	for (const FName G : Guns)
	{
		const FMIGunBuild* A = Builds.Find(G);
		const FMIGunBuild* B = O.Builds.Find(G);
		const FMIGunBuild Empty;
		if (!((A ? *A : Empty) == (B ? *B : Empty))) return false;
	}
	return true;
}

FString FMIRunSetup::ToJsonString() const
{
	TSharedPtr<FJsonObject> O = MakeShared<FJsonObject>();
	O->SetStringField(TEXT("crew"), Crew.ToString());
	TArray<TSharedPtr<FJsonValue>> G;
	for (const FName N : Guns) G.Add(MakeShared<FJsonValueString>(N.ToString()));
	O->SetArrayField(TEXT("guns"), G);
	TSharedPtr<FJsonObject> B = MakeShared<FJsonObject>();
	for (const TPair<FName, FMIGunBuild>& Build : Builds)
	{
		TSharedPtr<FJsonObject> Parts = MakeShared<FJsonObject>();
		for (const TPair<FName, FName>& P : Build.Value.Parts) Parts->SetStringField(P.Key.ToString(), P.Value.ToString());
		B->SetObjectField(Build.Key.ToString(), Parts);
	}
	O->SetObjectField(TEXT("builds"), B);
	O->SetStringField(TEXT("level"), Level.ToString());
	O->SetStringField(TEXT("mode"), Mode.ToString());
	O->SetStringField(TEXT("difficulty"), Difficulty.ToString());
	O->SetStringField(TEXT("time"), Time.ToString());
	O->SetBoolField(TEXT("played"), bPlayed);
	return MIJson::Print(O);
}

// ================================================================================================== loading

namespace MILoadoutPrivate
{
	using FFiles = TMap<FString, TSharedPtr<FJsonObject>>;

	/** Replaces every {"$ref": "file#path"} in V (recursively) by the value it names. */
	TSharedPtr<FJsonValue> Resolve(const TSharedPtr<FJsonValue>& V, const FFiles& Files, const FString& Owner, TArray<FString>& Unresolved, int32 Depth = 0)
	{
		if (!V.IsValid() || Depth > 16)
		{
			return V;
		}
		if (V->Type == EJson::Array)
		{
			TArray<TSharedPtr<FJsonValue>> Items;
			for (const TSharedPtr<FJsonValue>& E : V->AsArray()) Items.Add(Resolve(E, Files, Owner, Unresolved, Depth));
			return MakeShared<FJsonValueArray>(Items);
		}
		if (V->Type != EJson::Object)
		{
			return V;
		}
		const TSharedPtr<FJsonObject> O = V->AsObject();
		FString Ref;
		if (O->Values.Num() == 1 && O->TryGetStringField(TEXT("$ref"), Ref))
		{
			FString File, Path;
			const TSharedPtr<FJsonObject>* Doc = nullptr;
			if (Ref.Split(TEXT("#"), &File, &Path) && (Doc = Files.Find(File)) && Doc->IsValid())
			{
				const TSharedPtr<FJsonValue> Target = MIJson::Get(*Doc, Path);
				if (Target.IsValid())
				{
					return Resolve(Target, Files, Owner, Unresolved, Depth + 1);
				}
			}
			Unresolved.Add(FString::Printf(TEXT("%s: %s"), *Owner, *Ref));
			return MakeShared<FJsonValueNull>();
		}
		bool bChanged = false;
		TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
		for (const auto& Pair : O->Values)
		{
			const TSharedPtr<FJsonValue> R = Resolve(Pair.Value, Files, Owner, Unresolved, Depth);
			bChanged |= R != Pair.Value;
			Out->SetField(FString(*Pair.Key), R);
		}
		// Unchanged subtrees keep their identity, so a $ref target stays the very object of its file.
		if (bChanged) return MakeShared<FJsonValueObject>(Out);
		return V;
	}

	TSharedPtr<FJsonObject> Obj(const TSharedPtr<FJsonObject>& Root, const FString& Path)
	{
		const TSharedPtr<FJsonValue> V = MIJson::Get(Root, Path);
		return V.IsValid() && V->Type == EJson::Object ? V->AsObject() : nullptr;
	}

	FName NameOr(const TSharedPtr<FJsonObject>& Root, const FString& Path)
	{
		const FString S = MIJson::StringOr(Root, Path);
		return S.IsEmpty() ? NAME_None : FName(*S);
	}

	void ReadProvides(const TSharedPtr<FJsonObject>& P, FMILevelProvides& Out)
	{
		if (!P.IsValid()) return;
		bool B = false;
		Out.bPlayerStart = P->TryGetBoolField(TEXT("playerStart"), B) && B;
		Out.bExtraction = P->TryGetBoolField(TEXT("extraction"), B) && B;
		Out.bNav = P->TryGetBoolField(TEXT("nav"), B) && B;
		Out.bExplosives = P->TryGetBoolField(TEXT("explosives"), B) && B;
		Out.bTitlePath = P->TryGetBoolField(TEXT("titlePath"), B) && B;
		Out.Objectives = static_cast<int32>(MIJson::NumberOr(P, TEXT("objectives"), 0));
		Out.Ground = static_cast<int32>(MIJson::NumberOr(P, TEXT("enemySpawns.ground"), 0));
		Out.Air = static_cast<int32>(MIJson::NumberOr(P, TEXT("enemySpawns.air"), 0));
	}

	/** A string, or a {"$template"} filled by name ({n}, {gun} ...). */
	FString TextAt(const TSharedPtr<FJsonObject>& Root, const FString& Path, const TMap<FString, FString>* Args)
	{
		const TSharedPtr<FJsonValue> V = MIJson::Get(Root, Path);
		if (!V.IsValid()) return FString();
		if (V->Type == EJson::String) return V->AsString();
		if (V->Type == EJson::Object)
		{
			FString T = MIJson::StringOr(V->AsObject(), TEXT("$template.template"));
			if (Args)
			{
				for (const TPair<FString, FString>& A : *Args)
				{
					T.ReplaceInline(*FString::Printf(TEXT("{%s}"), *A.Key), *A.Value, ESearchCase::CaseSensitive);
				}
			}
			return T;
		}
		return FString();
	}
}

FString FMILoadoutData::Format(const FString& Key, const TMap<FString, FString>& Args) const
{
	using namespace MILoadoutPrivate;
	if (Key.StartsWith(TEXT("frontend.")))
	{
		return TextAt(TextJson, Key, &Args);
	}
	return FString();
}

FString FMILoadoutData::Text(const FString& Key) const
{
	using namespace MILoadoutPrivate;
	if (Key.StartsWith(TEXT("frontend.")))
	{
		return TextAt(TextJson, Key, nullptr);
	}
	return FString();
}

TArray<FString> FMILoadoutData::TextList(const FString& Key) const
{
	TArray<FString> Out;
	const TSharedPtr<FJsonValue> V = MIJson::Get(TextJson, Key);
	if (V.IsValid() && V->Type == EJson::Array)
	{
		for (const TSharedPtr<FJsonValue>& E : V->AsArray()) Out.Add(E->Type == EJson::String ? E->AsString() : FString());
	}
	return Out;
}

bool FMILoadoutData::HasText(const FString& Key) const
{
	return MIJson::Get(TextJson, Key).IsValid();
}

FMIRunSetup FMILoadoutData::ParitySetup(FName Mode, FName Difficulty, FName Time) const
{
	FMIRunSetup S;
	S.Crew = ParityCrew;
	S.Guns = ParityGuns;
	S.Level = ParityLevel;
	S.Mode = Mode;
	S.Difficulty = Difficulty;
	S.Time = Time;
	return S;
}

bool FMILoadoutData::Load(FMILoadoutData& Out, FString& OutError)
{
	static const TCHAR* Names[] = {TEXT("config.json"), TEXT("presentation.json"), TEXT("guns.json"), TEXT("attachments.json"),
		TEXT("crew.json"), TEXT("levels.json"), TEXT("frontend.json"), TEXT("frontend_text.json")};
	TMap<FString, TSharedPtr<FJsonObject>> Files;
	for (const TCHAR* Name : Names)
	{
		TSharedPtr<FJsonObject> Root;
		if (!UMIDataSubsystem::LoadJsonFile(Name, Root, OutError))
		{
			return false;
		}
		Files.Add(Name, Root);
	}
	return Parse(Files, Out, OutError);
}

bool FMILoadoutData::Parse(const TMap<FString, TSharedPtr<FJsonObject>>& Files, FMILoadoutData& Out, FString& OutError)
{
	using namespace MILoadoutPrivate;
	Out = FMILoadoutData();
	const auto Doc = [&](const TCHAR* Name) -> TSharedPtr<FJsonObject>
	{
		const TSharedPtr<FJsonObject>* D = Files.Find(Name);
		if (!D || !D->IsValid())
		{
			return nullptr;
		}
		const TSharedPtr<FJsonValue> R = Resolve(MakeShared<FJsonValueObject>(*D), Files, Name, Out.Unresolved);
		return R.IsValid() && R->Type == EJson::Object ? R->AsObject() : nullptr;
	};
	Out.GunsJson = Doc(TEXT("guns.json"));
	Out.AttachmentsJson = Doc(TEXT("attachments.json"));
	Out.CrewJson = Doc(TEXT("crew.json"));
	Out.LevelsJson = Doc(TEXT("levels.json"));
	Out.FrontendJson = Doc(TEXT("frontend.json"));
	Out.TextJson = Doc(TEXT("frontend_text.json"));
	if (!Out.GunsJson || !Out.AttachmentsJson || !Out.CrewJson || !Out.LevelsJson || !Out.FrontendJson || !Out.TextJson)
	{
		OutError = TEXT("a loadout file is missing (guns, attachments, crew, levels, frontend, frontend_text)");
		return false;
	}

	// ---- guns.json
	const TSharedPtr<FJsonObject>& G = Out.GunsJson;
	Out.Roster = MIJson::Names(G, TEXT("roster"));
	Out.CoreRoles = MIJson::Names(G, TEXT("ready.coreRoles"));
	Out.Playable = MIJson::Names(G, TEXT("ready.playable"));
	Out.DefaultPool = NameOr(G, TEXT("ammo.defaultPool"));
	Out.ExtraDefaults = MakeShared<FJsonObject>();
	if (const TSharedPtr<FJsonObject> D = Obj(G, TEXT("extraDefaults")))
	{
		for (const auto& Pair : D->Values)
		{
			if (Pair.Value->Type == EJson::Object)
			{
				if (const TSharedPtr<FJsonValue> V = Pair.Value->AsObject()->TryGetField(TEXT("value")))
				{
					Out.ExtraDefaults->SetField(FString(*Pair.Key), V);
				}
			}
		}
	}
	const TSharedPtr<FJsonObject> GunsObj = Obj(G, TEXT("guns"));
	for (const FName Id : Out.Roster)
	{
		const TSharedPtr<FJsonObject> E = GunsObj ? Obj(GunsObj, Id.ToString()) : nullptr;
		if (!E)
		{
			OutError = FString::Printf(TEXT("guns.json: roster names %s, which has no entry"), *Id.ToString());
			return false;
		}
		FMIGunEntry& Gun = Out.Guns.Add(Id);
		Gun.Id = Id;
		Gun.Class = NameOr(E, TEXT("class"));
		Gun.TextKey = MIJson::StringOr(E, TEXT("text"));
		Gun.MeleeKey = MIJson::StringOr(E, TEXT("melee"));
		bool bParity = false;
		Gun.bParity = E->TryGetBoolField(TEXT("parity"), bParity) && bParity;
		Gun.Rules = Obj(E, TEXT("rules"));
		Gun.Extra = Obj(E, TEXT("extra"));
		if (!Gun.Extra) Gun.Extra = MakeShared<FJsonObject>();
		Gun.Presentation = Obj(E, TEXT("presentation"));
		if (const TSharedPtr<FJsonObject> V = Obj(E, TEXT("variants")))
		{
			for (const auto& Pair : V->Values)
			{
				if (Pair.Value->Type != EJson::Object) continue;
				FMIGunVariant& Var = Gun.Variants.Add(FName(*FString(*Pair.Key)));
				Var.Mesh = MIJson::StringOr(Pair.Value->AsObject(), TEXT("mesh"));
				Var.OpticMesh = MIJson::StringOr(Pair.Value->AsObject(), TEXT("opticMesh"));
				Var.Status = NameOr(Pair.Value->AsObject(), TEXT("status"));
			}
		}
		if (const TSharedPtr<FJsonObject> M = Obj(E, TEXT("mounts")))
		{
			for (const auto& Pair : M->Values)
			{
				if (Pair.Value->Type != EJson::Object) continue;
				const TSharedPtr<FJsonObject> MO = Pair.Value->AsObject();
				FMIGunMount& Mount = Gun.Mounts.Add(FName(*FString(*Pair.Key)));
				Mount.Socket = NameOr(MO, TEXT("socket"));
				Mount.Status = NameOr(MO, TEXT("status"));
				Mount.Hide = MIJson::Names(MO, TEXT("hide"));
			}
		}
		Gun.MeshAsset = MIJson::StringOr(E, TEXT("art.mesh.asset"));
		Gun.MeshStatus = NameOr(E, TEXT("art.mesh.status"));
		Gun.StandIn = MIJson::StringOr(E, TEXT("art.mesh.standIn"));
		Gun.Icon = MIJson::StringOr(E, TEXT("art.icon.asset"));
		if (const TSharedPtr<FJsonObject> By = Obj(E, TEXT("clips.byStatus")))
		{
			for (const auto& Pair : By->Values)
			{
				if (Pair.Value->Type != EJson::Array) continue;
				for (const TSharedPtr<FJsonValue>& R : Pair.Value->AsArray())
				{
					// A role named twice keeps its first status; DataLoads reports the duplicate.
					if (!Gun.ClipStatus.Contains(FName(*R->AsString())))
					{
						Gun.ClipStatus.Add(FName(*R->AsString()), FName(*FString(*Pair.Key)));
					}
				}
			}
		}
	}

	// ---- attachments.json
	const TSharedPtr<FJsonObject>& A = Out.AttachmentsJson;
	if (const TSharedPtr<FJsonValue> F = MIJson::Get(A, TEXT("meta.factor")); F.IsValid() && F->Type == EJson::Array && F->AsArray().Num() == 2)
	{
		Out.FactorMin = F->AsArray()[0]->AsNumber();
		Out.FactorMax = F->AsArray()[1]->AsNumber();
	}
	if (const TSharedPtr<FJsonValue> T = MIJson::Get(A, TEXT("meta.tradeBand")); T.IsValid() && T->Type == EJson::Array && T->AsArray().Num() == 2)
	{
		Out.TradeMin = T->AsArray()[0]->AsNumber();
		Out.TradeMax = T->AsArray()[1]->AsNumber();
	}
	if (const TSharedPtr<FJsonValue> S = MIJson::Get(A, TEXT("slots")); S.IsValid() && S->Type == EJson::Array)
	{
		for (const TSharedPtr<FJsonValue>& E : S->AsArray())
		{
			const TSharedPtr<FJsonObject> O = E->AsObject();
			FMISlotDef& Slot = Out.Slots.AddDefaulted_GetRef();
			Slot.Id = NameOr(O, TEXT("id"));
			Slot.Order = static_cast<int32>(MIJson::NumberOr(O, TEXT("order"), Out.Slots.Num()));
			Slot.Text = MIJson::StringOr(O, TEXT("text"));
			Slot.Focus = NameOr(O, TEXT("focus"));
		}
		Out.Slots.Sort([](const FMISlotDef& L, const FMISlotDef& R) { return L.Order < R.Order; });
	}
	if (const TSharedPtr<FJsonObject> S = Obj(A, TEXT("stats")))
	{
		for (const auto& Pair : S->Values)
		{
			const TSharedPtr<FJsonObject> O = Pair.Value->AsObject();
			FMIStatDef& Stat = Out.Stats.Add(FName(*FString(*Pair.Key)));
			Stat.Id = FName(*FString(*Pair.Key));
			Stat.Better = NameOr(O, TEXT("better"));
			bool bTrade = false;
			Stat.bTrade = O->TryGetBoolField(TEXT("trade"), bTrade) && bTrade;
			Stat.Text = MIJson::StringOr(O, TEXT("text"));
			Stat.TextShorter = MIJson::StringOr(O, TEXT("textShorter"));
			const TArray<TSharedPtr<FJsonValue>>* Targets = nullptr;
			if (O->TryGetArrayField(TEXT("targets"), Targets))
			{
				for (const TSharedPtr<FJsonValue>& TV : *Targets)
				{
					const TSharedPtr<FJsonObject> TO = TV->AsObject();
					FMIStatTarget& T = Stat.Targets.AddDefaulted_GetRef();
					T.Path = MIJson::StringOr(TO, TEXT("path"));
					const TSharedPtr<FJsonValue> C = TO->TryGetField(TEXT("clamp"));
					if (C.IsValid() && C->Type == EJson::Array && C->AsArray().Num() == 2)
					{
						T.bClamp = MIJson::Number(C->AsArray()[0], T.Min) && MIJson::Number(C->AsArray()[1], T.Max);
					}
				}
			}
		}
	}
	if (const TSharedPtr<FJsonObject> Parts = Obj(A, TEXT("attachments")))
	{
		for (const auto& Pair : Parts->Values)
		{
			const TSharedPtr<FJsonObject> O = Pair.Value->AsObject();
			FMIAttachmentDef& P = Out.Attachments.Add(FName(*FString(*Pair.Key)));
			P.Id = FName(*FString(*Pair.Key));
			P.Slot = NameOr(O, TEXT("slot"));
			bool bBase = false;
			P.bBaseline = O->TryGetBoolField(TEXT("baseline"), bBase) && bBase;
			P.Text = MIJson::StringOr(O, TEXT("text"));
			const TArray<TSharedPtr<FJsonValue>>* Effects = nullptr;
			if (O->TryGetArrayField(TEXT("effects"), Effects))
			{
				for (const TSharedPtr<FJsonValue>& EV : *Effects)
				{
					const TSharedPtr<FJsonObject> EO = EV->AsObject();
					FMIEffect& Eff = P.Effects.AddDefaulted_GetRef();
					Eff.Stat = NameOr(EO, TEXT("stat"));
					Eff.Op = NameOr(EO, TEXT("op"));
					MIJson::Number(EO->TryGetField(TEXT("value")), Eff.Value);
				}
			}
			P.Mesh = MIJson::StringOr(O, TEXT("presentation.mesh"));
			P.Variant = NameOr(O, TEXT("presentation.variant"));
			P.Relief = MIJson::NumberOr(O, TEXT("presentation.relief"), -1.0);
			P.HandPose = NameOr(O, TEXT("presentation.handPose"));
			P.ArtStatus = NameOr(O, TEXT("art.status"));
			P.bSuppressed = MIJson::StringOr(O, TEXT("presentation.sound")) == TEXT("suppressed");
			if (const TSharedPtr<FJsonObject> Sockets = Obj(O, TEXT("presentation.sockets")))
			{
				for (const auto& S : Sockets->Values)
				{
					if (S.Value->Type == EJson::String) P.Sockets.Add(FName(*FString(*S.Key)), FName(*S.Value->AsString()));
				}
				P.bLaser = P.Sockets.Contains(TEXT("beam"));
			}
		}
	}
	if (const TSharedPtr<FJsonObject> Compat = Obj(A, TEXT("compatibility")))
	{
		for (TPair<FName, FMIGunEntry>& Gun : Out.Guns)
		{
			const TSharedPtr<FJsonObject> Row = Obj(Compat, Gun.Key.ToString());
			if (!Row) continue;
			for (const FMISlotDef& Slot : Out.Slots)
			{
				const TSharedPtr<FJsonObject> C = Obj(Row, Slot.Id.ToString());
				if (!C) continue;
				FMICompatSlot& S = Gun.Value.Compat.AddDefaulted_GetRef();
				S.Slot = Slot.Id;
				S.Options = MIJson::Names(C, TEXT("options"));
				S.Default = NameOr(C, TEXT("default"));
				bool B = false;
				S.bRequired = C->TryGetBoolField(TEXT("required"), B) && B;
				S.bVariant = C->TryGetBoolField(TEXT("variant"), B) && B;
				S.Mount = NameOr(C, TEXT("mount"));
				S.GateMaxLength = MIJson::NumberOr(C, TEXT("gate.maxLength"), -1.0);
			}
		}
	}

	// ---- crew.json
	const TSharedPtr<FJsonObject>& C = Out.CrewJson;
	Out.CrewOrder = MIJson::Names(C, TEXT("order"));
	for (const FName Id : Out.CrewOrder)
	{
		const TSharedPtr<FJsonObject> O = Obj(C, TEXT("crew.") + Id.ToString());
		if (!O)
		{
			OutError = FString::Printf(TEXT("crew.json: order names %s, which has no entry"), *Id.ToString());
			return false;
		}
		FMICrewEntry& M = Out.Crew.Add(Id);
		M.Id = Id;
		M.TextKey = MIJson::StringOr(O, TEXT("text"));
		M.CallName = MIJson::StringOr(O, TEXT("callName"));
		M.bOriginalLines = MIJson::StringOr(O, TEXT("lines")) != TEXT("template");
		bool B = false;
		M.bParity = O->TryGetBoolField(TEXT("parity"), B) && B;
		M.Arms = MIJson::StringOr(O, TEXT("look.arms"));
		M.Portrait = MIJson::StringOr(O, TEXT("portrait.asset"));
		if (const TSharedPtr<FJsonObject> Mats = Obj(O, TEXT("look.materials")))
		{
			for (const auto& P : Mats->Values)
			{
				if (P.Value->Type == EJson::String)
				{
					M.Materials.Add(FName(*FString(*P.Key)), P.Value->AsString());
					M.LookAssets.AddUnique(P.Value->AsString());
				}
			}
		}
		if (const TSharedPtr<FJsonValue> J = MIJson::Get(O, TEXT("look.jewellery")); J.IsValid() && J->Type == EJson::Array)
		{
			for (const TSharedPtr<FJsonValue>& JV : J->AsArray())
			{
				const TSharedPtr<FJsonObject> JO = JV->AsObject();
				FMICrewJewel& Jw = M.Jewellery.AddDefaulted_GetRef();
				Jw.Mesh = MIJson::StringOr(JO, TEXT("mesh"));
				Jw.Bone = NameOr(JO, TEXT("bone"));
				const TSharedPtr<FJsonValue> Off = JO->TryGetField(TEXT("offset"));
				if (Off.IsValid() && Off->Type == EJson::Array && Off->AsArray().Num() == 3)
				{
					Jw.bOffset = true;
					Jw.Offset = FVector(Off->AsArray()[0]->AsNumber(), Off->AsArray()[1]->AsNumber(), Off->AsArray()[2]->AsNumber());
				}
			}
		}
		if (const TSharedPtr<FJsonObject> Later = Obj(O, TEXT("later")))
		{
			for (const auto& P : Later->Values)
			{
				if (P.Value->Type == EJson::String) M.LaterAssets.Add(P.Value->AsString());
				else if (P.Value->Type == EJson::Array)
				{
					for (const TSharedPtr<FJsonValue>& JV : P.Value->AsArray())
					{
						if (JV->Type == EJson::Object) M.LaterAssets.Add(MIJson::StringOr(JV->AsObject(), TEXT("mesh")));
					}
				}
			}
		}
	}
	if (const TSharedPtr<FJsonObject> R = Obj(C, TEXT("lines.replaces")))
	{
		for (const auto& P : R->Values)
		{
			if (P.Value->Type == EJson::String) Out.CrewReplaces.Add(FString(*P.Key), P.Value->AsString());
		}
	}

	// ---- levels.json
	const TSharedPtr<FJsonObject>& L = Out.LevelsJson;
	Out.LevelOrder = MIJson::Names(L, TEXT("order"));
	for (const FName Id : Out.LevelOrder)
	{
		const TSharedPtr<FJsonObject> O = Obj(L, TEXT("levels.") + Id.ToString());
		if (!O)
		{
			OutError = FString::Printf(TEXT("levels.json: order names %s, which has no entry"), *Id.ToString());
			return false;
		}
		FMILevelEntry& Lv = Out.Levels.Add(Id);
		Lv.Id = Id;
		Lv.TextKey = MIJson::StringOr(O, TEXT("text"));
		Lv.Map = MIJson::StringOr(O, TEXT("map"));
		Lv.Times = MIJson::Names(O, TEXT("times"));
		if (const TSharedPtr<FJsonObject> P = Obj(O, TEXT("place")))
		{
			for (const auto& Pair : P->Values) Lv.Place.Add(FName(*FString(*Pair.Key)), Pair.Value->AsString());
		}
		ReadProvides(Obj(O, TEXT("provides")), Lv.Provides);
		Lv.Thumbnail = MIJson::StringOr(O, TEXT("preview.thumbnail.asset"));
	}
	if (const TSharedPtr<FJsonObject> Modes = Obj(L, TEXT("modes")))
	{
		for (const auto& Pair : Modes->Values)
		{
			const TSharedPtr<FJsonObject> O = Pair.Value->AsObject();
			FMIModeEntry& M = Out.Modes.Add(FName(*FString(*Pair.Key)));
			M.Id = FName(*FString(*Pair.Key));
			M.TextKey = MIJson::StringOr(O, TEXT("text"));
			M.Tagline = MIJson::StringOr(O, TEXT("tagline"));
			M.Radio = MIJson::StringOr(O, TEXT("radio"));
			M.Score = NameOr(O, TEXT("score"));
			ReadProvides(Obj(O, TEXT("needs")), M.Needs);
			Out.ModeOrder.Add(M.Id);
		}
	}
	Out.Difficulties = MIJson::Names(L, TEXT("difficulties.order"));

	// ---- frontend.json
	const TSharedPtr<FJsonObject>& F = Out.FrontendJson;
	Out.ParityCrew = NameOr(F, TEXT("parity.crew"));
	Out.ParityGuns = MIJson::Names(F, TEXT("parity.guns"));
	Out.ParityLevel = NameOr(F, TEXT("parity.level"));
	Out.CarryMax = static_cast<int32>(MIJson::NumberOr(F, TEXT("carry.max"), 4));
	Out.CarryMin = static_cast<int32>(MIJson::NumberOr(F, TEXT("carry.min"), 1));
	Out.WheelMinGuns = static_cast<int32>(MIJson::NumberOr(F, TEXT("wheel.minGuns"), 3));
	Out.WheelHold = MIJson::NumberOr(F, TEXT("wheel.hold"), 0.25);
	Out.WheelDeadzone = MIJson::NumberOr(F, TEXT("wheel.deadzone"), 0.5);
	Out.WheelMouseRadius = MIJson::NumberOr(F, TEXT("wheel.mouseRadius"), 60.0);
	Out.InspectHold = MIJson::NumberOr(F, TEXT("input.holds.inspectHold"), 0.4);
	Out.ResetHold = MIJson::NumberOr(F, TEXT("input.holds.resetHold"), 0.6);
	if (Out.ParityCrew.IsNone() || Out.ParityGuns.Num() == 0 || Out.ParityLevel.IsNone())
	{
		OutError = TEXT("frontend.json: parity set-up is incomplete");
		return false;
	}
	return true;
}

int32 FMILoadoutData::ApplyOverlay(const TSharedPtr<FJsonObject>& Overlay)
{
	int32 N = 0;
	if (!Overlay.IsValid())
	{
		return 0;
	}
	if (const TSharedPtr<FJsonValue> G = Overlay->TryGetField(TEXT("guns")); G.IsValid() && G->Type == EJson::Object)
	{
		for (const auto& Pair : G->AsObject()->Values)
		{
			FMIGunEntry* Gun = Guns.Find(FName(*FString(*Pair.Key)));
			if (!Gun || Pair.Value->Type != EJson::Object) continue;
			const TSharedPtr<FJsonObject> O = Pair.Value->AsObject();
			if (const TSharedPtr<FJsonValue> V = O->TryGetField(TEXT("variants")); V.IsValid() && V->Type == EJson::Object)
			{
				for (const auto& Var : V->AsObject()->Values)
				{
					FMIGunVariant& Target = Gun->Variants.FindOrAdd(FName(*FString(*Var.Key)));
					const TSharedPtr<FJsonObject> VO = Var.Value->AsObject();
					FString S;
					if (VO->TryGetStringField(TEXT("mesh"), S)) { Target.Mesh = S; ++N; }
					if (VO->TryGetStringField(TEXT("status"), S)) { Target.Status = FName(*S); ++N; }
				}
			}
			if (const TSharedPtr<FJsonValue> M = O->TryGetField(TEXT("mounts")); M.IsValid() && M->Type == EJson::Object)
			{
				for (const auto& Mount : M->AsObject()->Values)
				{
					if (FMIGunMount* Target = Gun->Mounts.Find(FName(*FString(*Mount.Key))))
					{
						FString S;
						if (Mount.Value->AsObject()->TryGetStringField(TEXT("status"), S)) { Target->Status = FName(*S); ++N; }
					}
				}
			}
		}
	}
	if (const TSharedPtr<FJsonValue> A = Overlay->TryGetField(TEXT("attachments")); A.IsValid() && A->Type == EJson::Object)
	{
		for (const auto& Pair : A->AsObject()->Values)
		{
			FMIAttachmentDef* Part = Attachments.Find(FName(*FString(*Pair.Key)));
			FString S;
			if (Part && Pair.Value->Type == EJson::Object && Pair.Value->AsObject()->TryGetStringField(TEXT("mesh"), S)) { Part->Mesh = S; ++N; }
		}
	}
	return N;
}

void FMILoadoutData::TradeOf(const FMIAttachmentDef& Part, double& OutBetter, double& OutWorse) const
{
	OutBetter = 0.0;
	OutWorse = 0.0;
	for (const FMIEffect& E : Part.Effects)
	{
		const FMIStatDef* S = Stats.Find(E.Stat);
		if (!S || !S->bTrade || E.Op != TEXT("mul") || !(E.Value > 0.0) || E.Value == 1.0)
		{
			continue;
		}
		const bool bLower = S->Better == TEXT("lower"), bHigher = S->Better == TEXT("higher");
		if (!bLower && !bHigher)
		{
			continue;  // "none": a trade of its own kind, neither better nor worse
		}
		const double L = FMath::Abs(FMath::Loge(E.Value));
		const bool bBetter = bLower ? E.Value < 1.0 : E.Value > 1.0;
		(bBetter ? OutBetter : OutWorse) += L;
	}
}

void FMILoadoutData::ValidateData(TArray<FString>& P) const
{
	for (const FString& U : Unresolved)
	{
		P.Add(FString::Printf(TEXT("$ref does not resolve: %s"), *U));
	}
	// extraDefaults: numbers, or the listed shapes.
	static const TCHAR* NumberDefaults[] = {TEXT("holster"), TEXT("draw"), TEXT("adsFov"), TEXT("adsLook"), TEXT("noise"), TEXT("semiFireBuffer"), TEXT("modeSwitch"), TEXT("inspectAfter")};
	for (const TCHAR* Key : NumberDefaults)
	{
		double V = 0.0;
		if (!MIJson::Number(ExtraDefaults->TryGetField(Key), V)) P.Add(FString::Printf(TEXT("guns.json extraDefaults.%s is not a number"), Key));
	}
	for (const TCHAR* Key : {TEXT("start"), TEXT("end"), TEXT("min")})
	{
		double V = 0.0;
		if (!MIJson::Number(MIJson::Get(ExtraDefaults, FString(TEXT("falloff.")) + Key), V)) P.Add(FString::Printf(TEXT("guns.json extraDefaults.falloff.%s is not a number"), Key));
	}
	if (MIJson::Names(ExtraDefaults, TEXT("fireModes")).Num() == 0) P.Add(TEXT("guns.json extraDefaults.fireModes is not a list of modes"));

	// Every clip role exactly once per gun.
	TArray<FName> Roles;
	if (const TSharedPtr<FJsonValue> R = MIJson::Get(GunsJson, TEXT("clipRoles.roles")); R.IsValid() && R->Type == EJson::Array)
	{
		for (const TSharedPtr<FJsonValue>& E : R->AsArray()) Roles.Add(FName(*MIJson::StringOr(E->AsObject(), TEXT("role"))));
	}
	for (const TPair<FName, FMIGunEntry>& Gun : Guns)
	{
		const FMIGunEntry& G = Gun.Value;
		if (!G.Rules.IsValid()) P.Add(FString::Printf(TEXT("%s: no rules"), *G.Id.ToString()));
		if (!G.Presentation.IsValid()) P.Add(FString::Printf(TEXT("%s: no presentation"), *G.Id.ToString()));
		TMap<FName, int32> Count;
		if (const TSharedPtr<FJsonValue> By = MIJson::Get(GunsJson, FString::Printf(TEXT("guns.%s.clips.byStatus"), *G.Id.ToString())); By.IsValid() && By->Type == EJson::Object)
		{
			for (const auto& Pair : By->AsObject()->Values)
			{
				for (const TSharedPtr<FJsonValue>& R : Pair.Value->AsArray()) Count.FindOrAdd(FName(*R->AsString()))++;
			}
		}
		for (const FName Role : Roles)
		{
			const int32 N = Count.FindRef(Role);
			if (N != 1) P.Add(FString::Printf(TEXT("%s: clip role %s named %d times"), *G.Id.ToString(), *Role.ToString(), N));
		}
		for (const TPair<FName, int32>& C : Count)
		{
			if (!Roles.Contains(C.Key)) P.Add(FString::Printf(TEXT("%s: unknown clip role %s"), *G.Id.ToString(), *C.Key.ToString()));
		}
		// Compatibility: known parts in their own slot; a required slot's default among its options.
		for (const FMICompatSlot& S : G.Compat)
		{
			for (const FName O : S.Options)
			{
				const FMIAttachmentDef* Part = FindPart(O);
				if (!Part) P.Add(FString::Printf(TEXT("%s.%s: unknown part %s"), *G.Id.ToString(), *S.Slot.ToString(), *O.ToString()));
				else if (Part->Slot != S.Slot) P.Add(FString::Printf(TEXT("%s.%s: %s belongs to %s"), *G.Id.ToString(), *S.Slot.ToString(), *O.ToString(), *Part->Slot.ToString()));
				if (S.bVariant && Part && !G.Variants.Contains(Part->Variant)) P.Add(FString::Printf(TEXT("%s: variant %s of %s has no entry"), *G.Id.ToString(), *Part->Variant.ToString(), *O.ToString()));
			}
			if (S.bRequired && !S.Options.Contains(S.Default)) P.Add(FString::Printf(TEXT("%s.%s: required, but its default %s is not an option"), *G.Id.ToString(), *S.Slot.ToString(), *S.Default.ToString()));
			if (!S.bVariant && !G.Mounts.Contains(S.Slot)) P.Add(FString::Printf(TEXT("%s.%s: no mount in guns.json"), *G.Id.ToString(), *S.Slot.ToString()));
		}
		// Text keys.
		if (G.TextKey.StartsWith(TEXT("frontend.")) && (!HasText(G.TextKey + TEXT(".name")) || !HasText(G.TextKey + TEXT(".blurb"))))
		{
			P.Add(FString::Printf(TEXT("%s: text %s.name / .blurb missing"), *G.Id.ToString(), *G.TextKey));
		}
		if (G.MeleeKey.StartsWith(TEXT("frontend.")) && !HasText(G.MeleeKey)) P.Add(FString::Printf(TEXT("%s: text %s missing"), *G.Id.ToString(), *G.MeleeKey));
		if (!HasText(FString::Printf(TEXT("frontend.loadout.classes.%s"), *G.Class.ToString()))) P.Add(FString::Printf(TEXT("%s: class %s has no text"), *G.Id.ToString(), *G.Class.ToString()));
	}
	// Attachments: known stats and ops; a multi-target stat takes only mul; text keys.
	for (const TPair<FName, FMIAttachmentDef>& Part : Attachments)
	{
		const FMIAttachmentDef& A = Part.Value;
		if (!FindSlot(A.Slot)) P.Add(FString::Printf(TEXT("%s: unknown slot %s"), *A.Id.ToString(), *A.Slot.ToString()));
		if (!HasText(A.Text + TEXT(".name")) || !HasText(A.Text + TEXT(".blurb"))) P.Add(FString::Printf(TEXT("%s: text %s missing"), *A.Id.ToString(), *A.Text));
		if (A.bBaseline && A.Effects.Num() > 0) P.Add(FString::Printf(TEXT("%s: a baseline part has effects"), *A.Id.ToString()));
		for (const FMIEffect& E : A.Effects)
		{
			const FMIStatDef* S = Stats.Find(E.Stat);
			if (!S) { P.Add(FString::Printf(TEXT("%s: unknown stat %s"), *A.Id.ToString(), *E.Stat.ToString())); continue; }
			static const FName Ops[] = {TEXT("set"), TEXT("add"), TEXT("mul"), TEXT("min"), TEXT("max")};
			if (!MakeArrayView(Ops).Contains(E.Op)) P.Add(FString::Printf(TEXT("%s: unknown op %s"), *A.Id.ToString(), *E.Op.ToString()));
			if ((S->Targets.Num() > 1 || S->Targets.ContainsByPredicate([](const FMIStatTarget& T) { return T.Path.EndsWith(TEXT("*")); })) && E.Op != TEXT("mul"))
			{
				P.Add(FString::Printf(TEXT("%s: %s has several targets and takes only mul, not %s"), *A.Id.ToString(), *E.Stat.ToString(), *E.Op.ToString()));
			}
		}
	}
	// The trade check (LOADOUT.md 3.3): every part that is not a baseline makes something better and something worse,
	// and the two weigh about the same (B / W in meta.trade). The text says this is checked here; it was not until the
	// parts kit of round 4 (twelve new parts) needed it.
	for (const TPair<FName, FMIAttachmentDef>& Part : Attachments)
	{
		const FMIAttachmentDef& A = Part.Value;
		if (A.bBaseline)
		{
			continue;
		}
		double B = 0.0, W = 0.0;
		TradeOf(A, B, W);
		if (!(B > 0.0) || !(W > 0.0))
		{
			P.Add(FString::Printf(TEXT("%s: a part must make one stat better and one worse (better %.4f, worse %.4f)"), *A.Id.ToString(), B, W));
		}
		else if (B / W < TradeMin || B / W > TradeMax)
		{
			P.Add(FString::Printf(TEXT("%s: the trade is out of balance: better %.4f / worse %.4f = %.3f, outside [%.2f, %.2f]"), *A.Id.ToString(), B, W, B / W, TradeMin, TradeMax));
		}
	}
	for (const TPair<FName, FMIStatDef>& S : Stats)
	{
		if (!S.Value.Text.IsEmpty() && !HasText(S.Value.Text)) P.Add(FString::Printf(TEXT("stat %s: text %s missing"), *S.Key.ToString(), *S.Value.Text));
	}
	for (const FMISlotDef& S : Slots)
	{
		if (!HasText(S.Text)) P.Add(FString::Printf(TEXT("slot %s: text %s missing"), *S.Id.ToString(), *S.Text));
	}
	// Crew.
	if (!Crew.Contains(ParityCrew)) P.Add(TEXT("frontend.json parity.crew is not in crew.json"));
	for (const TPair<FName, FMICrewEntry>& M : Crew)
	{
		if (!HasText(M.Value.TextKey + TEXT(".name")) || !HasText(M.Value.TextKey + TEXT(".tagline"))) P.Add(FString::Printf(TEXT("crew %s: text missing"), *M.Key.ToString()));
		if (M.Value.CallName.IsEmpty()) P.Add(FString::Printf(TEXT("crew %s: no callName"), *M.Key.ToString()));
	}
	for (const TPair<FString, FString>& R : CrewReplaces)
	{
		if (!HasText(R.Value)) P.Add(FString::Printf(TEXT("crew.json lines.replaces: %s missing"), *R.Value));
	}
	// Parity guns.
	for (const FName Id : ParityGuns)
	{
		const FMIGunEntry* G = FindGun(Id);
		if (!G || !G->bParity) P.Add(FString::Printf(TEXT("frontend.json parity gun %s is not a parity gun of guns.json"), *Id.ToString()));
	}
	// Levels and modes: every mode is provided by at least one level.
	if (!Levels.Contains(ParityLevel)) P.Add(TEXT("frontend.json parity.level is not in levels.json"));
	for (const TPair<FName, FMIModeEntry>& M : Modes)
	{
		bool bAny = false;
		for (const TPair<FName, FMILevelEntry>& L : Levels)
		{
			const FMILevelProvides& H = L.Value.Provides;
			const FMILevelProvides& N = M.Value.Needs;
			bAny |= (!N.bPlayerStart || H.bPlayerStart) && (!N.bExtraction || H.bExtraction) && (!N.bNav || H.bNav)
				&& H.Objectives >= N.Objectives && H.Ground >= N.Ground && H.Air >= N.Air;
		}
		if (!bAny) P.Add(FString::Printf(TEXT("mode %s is provided by no level"), *M.Key.ToString()));
	}
	for (const TPair<FName, FMILevelEntry>& L : Levels)
	{
		if (!HasText(L.Value.TextKey + TEXT(".name"))) P.Add(FString::Printf(TEXT("level %s: text missing"), *L.Key.ToString()));
	}
	// Front-end strings every screen uses.
	static const TCHAR* Keys[] = {TEXT("frontend.home.start"), TEXT("frontend.home.setup"), TEXT("frontend.home.summary"), TEXT("frontend.home.firstTime"),
		TEXT("frontend.steps.labels"), TEXT("frontend.steps.next"), TEXT("frontend.steps.back"), TEXT("frontend.steps.done"),
		TEXT("frontend.crew.kicker"), TEXT("frontend.crew.title"), TEXT("frontend.crew.note"),
		TEXT("frontend.loadout.kicker"), TEXT("frontend.loadout.title"), TEXT("frontend.loadout.carry"), TEXT("frontend.loadout.slot"),
		TEXT("frontend.loadout.empty"), TEXT("frontend.loadout.emptyHint"), TEXT("frontend.loadout.carried"), TEXT("frontend.loadout.needOne"),
		TEXT("frontend.loadout.full"), TEXT("frontend.loadout.bag"), TEXT("frontend.loadout.devTag"), TEXT("frontend.loadout.noSlots"), TEXT("frontend.loadout.slots"),
		TEXT("frontend.attachments.kicker"), TEXT("frontend.attachments.title"), TEXT("frontend.attachments.factory"), TEXT("frontend.attachments.factoryNote"),
		TEXT("frontend.attachments.fitted"), TEXT("frontend.attachments.reset"), TEXT("frontend.attachments.noPartsYet"), TEXT("frontend.attachments.noPartsYetNote"),
		TEXT("frontend.where.kicker"), TEXT("frontend.where.title"), TEXT("frontend.level.time"), TEXT("frontend.mode.difficulty"), TEXT("frontend.mode.best"),
		TEXT("frontend.briefing.kicker"), TEXT("frontend.briefing.title"), TEXT("frontend.briefing.change"), TEXT("frontend.briefing.go"),
		TEXT("frontend.cards.changeSetup"), TEXT("frontend.hud.modes.auto"), TEXT("frontend.hud.modes.semi"), TEXT("frontend.hud.wheel"), TEXT("frontend.hud.bag")};
	for (const TCHAR* Key : Keys)
	{
		if (!HasText(Key)) P.Add(FString::Printf(TEXT("frontend_text.json: %s missing"), Key));
	}
}

// ================================================================================================== readiness

FMIAssetExists FMIReadiness::PackageExists()
{
	return [](const FString& Path)
	{
		if (Path.IsEmpty()) return false;
		const FString Package = FPackageName::ObjectPathToPackageName(Path);
		return FPackageName::DoesPackageExist(Package);
	};
}

bool FMIReadiness::IsGunReady(FName Id) const
{
	const FMIGunEntry* G = Data ? Data->FindGun(Id) : nullptr;
	if (!G)
	{
		return false;
	}
	if (G->bParity)
	{
		return true;
	}
	// The mesh of its default variant exists and is not a stand-in.
	bool bMesh = false;
	if (G->Variants.Num() > 0)
	{
		FName Open = TEXT("open");
		if (const FMICompatSlot* Stock = G->FindCompat(TEXT("stock")))
		{
			if (const FMIAttachmentDef* P = Data->FindPart(Stock->Default)) Open = P->Variant;
		}
		const FMIGunVariant* V = G->Variants.Find(Open);
		bMesh = V && V->Status == TEXT("exists") && AssetExists && AssetExists(V->Mesh);
	}
	else
	{
		const FString Real = MIJson::StringOr(G->Presentation, TEXT("realMesh"), MIJson::StringOr(G->Presentation, TEXT("mesh")));
		bMesh = G->MeshStatus == TEXT("exists") && AssetExists && AssetExists(Real);
	}
	if (!bMesh)
	{
		return false;
	}
	// Each core role plays now: its clip exists (or a template or the procedural rig plays it). A role whose pack
	// clip is being imported (inProgress) is played by the procedural rig meanwhile (LOADOUT.md 3.2, 5).
	for (const FName Role : Data->CoreRoles)
	{
		const FName Status = G->ClipOf(Role);
		if (!Data->Playable.Contains(Status) && Status != TEXT("inProgress")) return false;
	}
	return true;
}

TArray<FName> FMIReadiness::OfferedSlots(FName Id) const
{
	TArray<FName> Out;
	const FMIGunEntry* G = Data ? Data->FindGun(Id) : nullptr;
	if (!G)
	{
		return Out;
	}
	for (const FMICompatSlot& S : G->Compat)
	{
		if (OfferedParts(Id, S.Slot).Num() > 0) Out.Add(S.Slot);
	}
	return Out;
}

TArray<FName> FMIReadiness::OfferedParts(FName Id, FName Slot) const
{
	TArray<FName> Out;
	const FMIGunEntry* G = Data ? Data->FindGun(Id) : nullptr;
	const FMICompatSlot* S = G ? G->FindCompat(Slot) : nullptr;
	if (!S)
	{
		return Out;
	}
	if (S->bVariant)
	{
		for (const FName O : S->Options)
		{
			const FMIAttachmentDef* P = Data->FindPart(O);
			const FMIGunVariant* V = P ? G->Variants.Find(P->Variant) : nullptr;
			if (V && V->Status == TEXT("exists") && AssetExists && AssetExists(V->Mesh)) Out.Add(O);
		}
		// A variant slot with only its default offered is no choice: the slot shows once a second variant exists.
		return Out.Num() >= 2 ? Out : TArray<FName>();
	}
	const FMIGunMount* M = G->Mounts.Find(Slot);
	if (!M || M->Status != TEXT("exists"))
	{
		return Out;
	}
	for (const FName O : S->Options)
	{
		const FMIAttachmentDef* P = Data->FindPart(O);
		// A part is offered when its mesh can be shown, or when it is the factory baseline of the gun.
		if (P && (P->bBaseline || (!P->Mesh.IsEmpty() && AssetExists && AssetExists(P->Mesh)))) Out.Add(O);
	}
	if (S->bRequired && !Out.Contains(S->Default))
	{
		Out.Reset();  // a required slot is offered only with its default
	}
	return Out.Num() > (S->bRequired ? 1 : 0) ? Out : TArray<FName>();
}

bool FMIReadiness::IsCrewOffered(FName Id) const
{
	const FMICrewEntry* C = Data ? Data->FindCrew(Id) : nullptr;
	if (!C)
	{
		return false;
	}
	if (C->bParity)
	{
		return true;
	}
	if (C->LookAssets.Num() == 0 || !AssetExists)
	{
		return false;
	}
	for (const FString& A : C->LookAssets)
	{
		if (!AssetExists(A)) return false;
	}
	return true;
}

bool FMIReadiness::HasLater(FName Id) const
{
	const FMICrewEntry* C = Data ? Data->FindCrew(Id) : nullptr;
	if (!C || C->LaterAssets.Num() == 0 || !AssetExists)
	{
		return false;
	}
	for (const FString& A : C->LaterAssets)
	{
		if (!AssetExists(A)) return false;
	}
	return true;
}

FString FMIReadiness::BaseMesh(FName Id, const FMIGunBuild* Build) const
{
	const FMIGunEntry* G = Data ? Data->FindGun(Id) : nullptr;
	if (!G)
	{
		return FString();
	}
	if (G->Variants.Num() > 0)
	{
		FName Part = NAME_None;
		if (const FMICompatSlot* Stock = G->FindCompat(TEXT("stock")))
		{
			Part = Stock->Default;
			if (Build && Build->Parts.Contains(TEXT("stock"))) Part = Build->Parts[TEXT("stock")];
		}
		const FMIAttachmentDef* P = Data->FindPart(Part);
		const FMIGunVariant* V = G->Variants.Find(P ? P->Variant : FName(TEXT("open")));
		if (V && !V->Mesh.IsEmpty() && AssetExists && AssetExists(V->Mesh))
		{
			// An optic over standing irons would block it: the irons-folded twin (ANIMATION.md 8.1, 8.7).
			const FName* Optic = Build ? Build->Parts.Find(TEXT("optic")) : nullptr;
			if (Optic && !Optic->IsNone() && *Optic != TEXT("irons") && !V->OpticMesh.IsEmpty() && AssetExists(V->OpticMesh))
			{
				return V->OpticMesh;
			}
			return V->Mesh;
		}
	}
	const FString Real = MIJson::StringOr(G->Presentation, TEXT("realMesh"));
	if (!Real.IsEmpty() && AssetExists && AssetExists(Real))
	{
		return Real;
	}
	const FString Mesh = MIJson::StringOr(G->Presentation, TEXT("mesh"));
	return Mesh.IsEmpty() ? MIJson::StringOr(G->Presentation, TEXT("fallbackMesh")) : Mesh;
}

FMIGunBuild FMIReadiness::DefaultBuild(FName Id) const
{
	FMIGunBuild B;
	if (const FMIGunEntry* G = Data ? Data->FindGun(Id) : nullptr)
	{
		for (const FMICompatSlot& S : G->Compat)
		{
			if (S.bRequired && !S.Default.IsNone()) B.Parts.Add(S.Slot, S.Default);
		}
	}
	return B;
}

TArray<FName> FMIReadiness::ModesOf(FName LevelId) const
{
	TArray<FName> Out;
	const FMILevelEntry* L = Data ? Data->Levels.Find(LevelId) : nullptr;
	if (!L)
	{
		return Out;
	}
	for (const FName M : Data->ModeOrder)
	{
		const FMILevelProvides& H = L->Provides;
		const FMILevelProvides& N = Data->Modes[M].Needs;
		if ((!N.bPlayerStart || H.bPlayerStart) && (!N.bExtraction || H.bExtraction) && (!N.bNav || H.bNav)
			&& H.Objectives >= N.Objectives && H.Ground >= N.Ground && H.Air >= N.Air)
		{
			Out.Add(M);
		}
	}
	return Out;
}

int32 FMIReadiness::Validate(FMIRunSetup& S) const
{
	if (!Data)
	{
		return 0;
	}
	int32 Fixes = 0;
	// 1. Crew and level.
	if (!IsCrewOffered(S.Crew)) { S.Crew = Data->ParityCrew; ++Fixes; }
	if (!Data->Levels.Contains(S.Level)) { S.Level = Data->ParityLevel; ++Fixes; }
	// 2. and 4. Guns: known, offered, no duplicates, no gaps, at most four; none left -> the parity guns.
	TArray<FName> Guns;
	for (const FName G : S.Guns)
	{
		if (!G.IsNone() && IsGunOffered(G) && !Guns.Contains(G) && Guns.Num() < Data->CarryMax) Guns.Add(G);
	}
	if (Guns.Num() == 0) Guns = Data->ParityGuns;
	if (Guns != S.Guns) { S.Guns = Guns; ++Fixes; }
	// 3. Parts: in the gun's options and offered, else dropped; a required slot without a valid choice -> its default.
	for (TPair<FName, FMIGunBuild>& B : S.Builds)
	{
		const FMIGunEntry* G = Data->FindGun(B.Key);
		if (!G) continue;
		TMap<FName, FName> Kept;
		for (const TPair<FName, FName>& P : B.Value.Parts)
		{
			const FMICompatSlot* C = G->FindCompat(P.Key);
			if (C && C->Options.Contains(P.Value) && OfferedParts(B.Key, P.Key).Contains(P.Value)) Kept.Add(P.Key, P.Value);
			else ++Fixes;
		}
		for (const FMICompatSlot& C : G->Compat)
		{
			if (C.bRequired && !Kept.Contains(C.Slot) && !C.Default.IsNone()) Kept.Add(C.Slot, C.Default);
		}
		B.Value.Parts = Kept;
	}
	// 5. A mode the level does not provide -> its first mode.
	const TArray<FName> Modes = ModesOf(S.Level);
	if (Modes.Num() > 0 && !Modes.Contains(S.Mode)) { S.Mode = Modes[0]; ++Fixes; }
	return Fixes;
}
