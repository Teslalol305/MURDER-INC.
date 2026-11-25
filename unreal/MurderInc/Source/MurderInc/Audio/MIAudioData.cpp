#include "Audio/MIAudioData.h"

#include "Core/Data/MIDataSubsystem.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Misc/Paths.h"

namespace MIAudioJson
{
	double Num(const TSharedPtr<FJsonObject>& O, const TCHAR* Key, double Default)
	{
		double V = Default;
		return O.IsValid() && O->TryGetNumberField(Key, V) ? V : Default;
	}

	bool Flag(const TSharedPtr<FJsonObject>& O, const TCHAR* Key, bool Default)
	{
		bool V = Default;
		return O.IsValid() && O->TryGetBoolField(Key, V) ? V : Default;
	}

	FString Str(const TSharedPtr<FJsonObject>& O, const TCHAR* Key, const FString& Default)
	{
		FString V;
		return O.IsValid() && O->TryGetStringField(Key, V) ? V : Default;
	}

	TSharedPtr<FJsonObject> Obj(const TSharedPtr<FJsonObject>& O, const TCHAR* Key)
	{
		const TSharedPtr<FJsonObject>* V = nullptr;
		return O.IsValid() && O->TryGetObjectField(Key, V) && V ? *V : nullptr;
	}

	double PerKey(const TSharedPtr<FJsonObject>& O, const TCHAR* Key, FName Variant, double Default)
	{
		if (!O.IsValid() || !O->HasField(Key))
		{
			return Default;
		}
		double V = Default;
		if (O->TryGetNumberField(Key, V))
		{
			return V;
		}
		const TSharedPtr<FJsonObject> P = Obj(O, Key);
		if (!P.IsValid())
		{
			return Default;
		}
		if (!Variant.IsNone() && P->TryGetNumberField(*Variant.ToString(), V))
		{
			return V;
		}
		return Num(P, TEXT("default"), Default);
	}

	FVector2D Range(const TSharedPtr<FJsonObject>& O, const TCHAR* Key, double Default)
	{
		const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
		if (O.IsValid() && O->TryGetArrayField(Key, A) && A->Num() >= 2)
		{
			return FVector2D((*A)[0]->AsNumber(), (*A)[1]->AsNumber());
		}
		const double V = Num(O, Key, Default);
		return FVector2D(V, V);
	}
}

TSharedPtr<FJsonObject> FMIAudioData::Event(FName Key) const
{
	const TSharedPtr<FJsonObject>* E = Events.Find(Key);
	return E ? *E : nullptr;
}

TSharedPtr<FJsonObject> FMIAudioData::Table(const TCHAR* Key) const
{
	return MIAudioJson::Obj(Root, Key);
}

double FMIAudioData::DistanceGain(double D, double Ref, double Roll)
{
	Ref = FMath::Max(Ref, 0.01);
	return Ref / (Ref + Roll * (FMath::Max(D, Ref) - Ref));
}

FString FMIAudioData::AudioDir()
{
	return FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Audio"));
}

FString FMIAudioData::AssetPath(const FString& File)
{
	FString Path = FPaths::ChangeExtension(File, TEXT(""));
	Path.ReplaceInline(TEXT("\\"), TEXT("/"));
	return FString::Printf(TEXT("/Game/Audio/%s.%s"), *Path, *FPaths::GetBaseFilename(File));
}

bool FMIAudioData::Parse(const TSharedPtr<FJsonObject>& SoundsRoot, const TSharedPtr<FJsonObject>& AudioRoot, FMIAudioData& Out, FString& OutError)
{
	using namespace MIAudioJson;
	Out = FMIAudioData();
	Out.Root = AudioRoot;
	if (!SoundsRoot.IsValid() || !AudioRoot.IsValid())
	{
		OutError = TEXT("audio_sounds.json or audio.json missing");
		return false;
	}

	// Categories and the bus map.
	const TSharedPtr<FJsonObject> Cats = Obj(AudioRoot, TEXT("categories"));
	if (!Cats.IsValid())
	{
		OutError = TEXT("audio.json: categories missing");
		return false;
	}
	for (const auto& Pair : Cats->Values)
	{
		const TSharedPtr<FJsonObject> C = Pair.Value->Type == EJson::Object ? Pair.Value->AsObject() : nullptr;
		if (!C.IsValid())
		{
			continue;
		}
		FMIAudioCategory Cat;
		Cat.Name = FName(FString(*Pair.Key));
		Cat.Volume = Num(C, TEXT("volume"), 1);
		Cat.Option = FName(Str(C, TEXT("option"), TEXT("effects")));
		Cat.bMuffled = Flag(C, TEXT("muffled"), false);
		Cat.bPausable = Flag(C, TEXT("pausable"), true);
		Cat.bUI = Flag(C, TEXT("ui"), false);
		Cat.Reverb = Num(C, TEXT("reverb"), 0);
		Cat.Voices = (int32)Num(C, TEXT("voices"), 8);
		Cat.Priority = FMath::Max(0.0, Num(C, TEXT("priority"), 1.0));
		Cat.bAlwaysPlay = Flag(C, TEXT("alwaysPlay"), false);
		Cat.bKeepLoops = Flag(C, TEXT("keepLoops"), false);
		Out.Categories.Add(Cat.Name, Cat);
	}
	TMap<FName, FName> BusMap;
	if (const TSharedPtr<FJsonObject> B = Obj(AudioRoot, TEXT("busToCategory")))
	{
		for (const auto& Pair : B->Values)
		{
			BusMap.Add(FName(FString(*Pair.Key)), FName(Pair.Value->AsString()));
		}
	}
	if (const TSharedPtr<FJsonObject> O = Obj(AudioRoot, TEXT("options")))
	{
		for (const auto& Pair : O->Values)
		{
			double V = 0;
			if (Pair.Value->TryGetNumber(V))
			{
				Out.OptionDefaults.Add(FName(FString(*Pair.Key)), V);
			}
		}
	}
	if (const TSharedPtr<FJsonObject> P = Obj(AudioRoot, TEXT("play")))
	{
		Out.Jitter = Num(P, TEXT("jitter"), Out.Jitter);
		Out.LevelVariation = Num(P, TEXT("levelVariation"), Out.LevelVariation);
		Out.Cull = Num(P, TEXT("cull"), Out.Cull);
		Out.ImpactGap = Num(P, TEXT("impactGap"), Out.ImpactGap);
	}
	if (const TSharedPtr<FJsonObject> D = Obj(AudioRoot, TEXT("distance")))
	{
		Out.DefaultRef = Num(D, TEXT("defaultRef"), Out.DefaultRef);
		Out.DefaultRoll = Num(D, TEXT("defaultRoll"), Out.DefaultRoll);
		Out.AirScale = Num(D, TEXT("airScale"), Out.AirScale);
		Out.AirMin = Num(D, TEXT("airMin"), Out.AirMin);
		Out.bOcclusion = Flag(D, TEXT("occlusion"), true);
		Out.OcclusionGain = Num(D, TEXT("occlusionGain"), Out.OcclusionGain);
		Out.OcclusionCutoff = Num(D, TEXT("occlusionCutoff"), Out.OcclusionCutoff);
		Out.OcclusionInterp = Num(D, TEXT("occlusionInterp"), Out.OcclusionInterp);
		Out.CurvePoints = (int32)Num(D, TEXT("curvePoints"), Out.CurvePoints);
	}

	// The web sounds.
	const TSharedPtr<FJsonObject> S = Obj(SoundsRoot, TEXT("sounds"));
	if (!S.IsValid())
	{
		OutError = TEXT("audio_sounds.json: sounds missing (node tools/ue-export/audio.mjs)");
		return false;
	}
	for (const auto& Pair : S->Values)
	{
		const TSharedPtr<FJsonObject> D = Pair.Value->AsObject();
		const FString Bus = Str(D, TEXT("bus"));
		if (!D.IsValid() || Bus == TEXT("ir"))
		{
			continue;
		}
		FMISoundDef Def;
		Def.Name = FName(FString(*Pair.Key));
		const FName* Cat = BusMap.Find(FName(Bus));
		Def.Category = Cat ? *Cat : FName(Bus);
		const int32 N = (int32)Num(D, TEXT("variants"), 1);
		const TArray<TSharedPtr<FJsonValue>>* Secs = nullptr;
		D->TryGetArrayField(TEXT("secs"), Secs);
		for (int32 I = 0; I < N; ++I)
		{
			Def.Files.Add(FString::Printf(TEXT("Web/%s_%02d.wav"), *Def.Name.ToString(), I + 1));
			Def.Secs.Add(Secs && Secs->IsValidIndex(I) ? (*Secs)[I]->AsNumber() : 1.0);
		}
		Def.Volume = Num(D, TEXT("vol"), 1);
		double J = 0;
		Def.Jitter = D->TryGetNumberField(TEXT("jitter"), J) ? J : Out.Jitter;
		Def.Priority = (int32)Num(D, TEXT("prio"), 5);
		Def.Max = (int32)Num(D, TEXT("max"), 0);
		Def.Gap = Num(D, TEXT("gap"), 0);
		double Ref = 0;
		if (D->TryGetNumberField(TEXT("ref"), Ref))
		{
			Def.Ref = Ref;
			Def.Roll = Num(D, TEXT("roll"), 1);
		}
		Def.bLoop = Flag(D, TEXT("loop"), false);
		Def.bStereo = Flag(D, TEXT("stereo"), false);
		if (!Out.Categories.Contains(Def.Category))
		{
			OutError = FString::Printf(TEXT("sound %s: bus %s maps to no category"), *Def.Name.ToString(), *Bus);
			return false;
		}
		Out.Sounds.Add(Def.Name, MoveTemp(Def));
	}

	// Replacement layers (and names that exist only as layers).
	if (const TSharedPtr<FJsonObject> R = Obj(AudioRoot, TEXT("replace")))
	{
		for (const auto& Pair : R->Values)
		{
			const TSharedPtr<FJsonObject> E = Pair.Value->Type == EJson::Object ? Pair.Value->AsObject() : nullptr;
			if (!E.IsValid())
			{
				continue;
			}
			const FName Name(FString(*Pair.Key));
			FMIReplace Rep;
			Rep.Web = Num(E, TEXT("web"), 0);
			Rep.Fallback = FName(Str(E, TEXT("fallback")));
			const TArray<TSharedPtr<FJsonValue>>* Layers = nullptr;
			if (E->TryGetArrayField(TEXT("layers"), Layers))
			{
				for (const TSharedPtr<FJsonValue>& LV : *Layers)
				{
					const TSharedPtr<FJsonObject> L = LV->AsObject();
					FMIReplaceLayer Layer;
					Layer.Name = FName(Str(L, TEXT("name"), TEXT("layer")));
					Layer.Volume = Num(L, TEXT("vol"), 1);
					Layer.bPlaceholder = Flag(L, TEXT("placeholder"), false);
					const TArray<TSharedPtr<FJsonValue>>* Files = nullptr;
					if (L.IsValid() && L->TryGetArrayField(TEXT("files"), Files))
					{
						for (const TSharedPtr<FJsonValue>& F : *Files)
						{
							Layer.Files.Add(F->AsString());
						}
					}
					Rep.Layers.Add(MoveTemp(Layer));
				}
			}
			if (!Out.Sounds.Contains(Name))
			{
				FMISoundDef Def;
				Def.Name = Name;
				Def.bReplaceOnly = true;
				Def.Category = FName(Str(E, TEXT("category"), TEXT("world")));
				double Ref = 0;
				if (E->TryGetNumberField(TEXT("ref"), Ref))
				{
					Def.Ref = Ref;
					Def.Roll = Num(E, TEXT("roll"), 1);
				}
				else if (const FMISoundDef* Fb = Out.Sounds.Find(Rep.Fallback))
				{
					Def.Ref = Fb->Ref;
					Def.Roll = Fb->Roll;
				}
				Def.Priority = (int32)Num(E, TEXT("prio"), 6);
				Def.Jitter = Num(E, TEXT("jitter"), Out.Jitter);
				if (!Out.Categories.Contains(Def.Category))
				{
					OutError = FString::Printf(TEXT("replace %s: unknown category %s"), *Name.ToString(), *Def.Category.ToString());
					return false;
				}
				Out.Sounds.Add(Name, MoveTemp(Def));
			}
			Out.Replace.Add(Name, MoveTemp(Rep));
		}
	}

	// Zones and reverb presets.
	if (const TSharedPtr<FJsonObject> Z = Obj(AudioRoot, TEXT("zones")))
	{
		for (const auto& Pair : Z->Values)
		{
			const TSharedPtr<FJsonObject> E = Pair.Value->Type == EJson::Object ? Pair.Value->AsObject() : nullptr;
			if (!E.IsValid())
			{
				continue;
			}
			FMIAudioZone Zone;
			Zone.Name = FName(FString(*Pair.Key));
			Zone.Preset = FName(Str(E, TEXT("preset"), Zone.Name.ToString()));
			Zone.bDefault = Flag(E, TEXT("default"), false);
			Zone.bInterior = Flag(E, TEXT("interior"), false);
			Zone.Fade = Num(E, TEXT("fade"), 1);
			const TArray<TSharedPtr<FJsonValue>>* Box = nullptr;
			if (E->TryGetArrayField(TEXT("box"), Box) && Box->Num() == 2)
			{
				const TArray<TSharedPtr<FJsonValue>>& A = (*Box)[0]->AsArray();
				const TArray<TSharedPtr<FJsonValue>>& B = (*Box)[1]->AsArray();
				if (A.Num() == 3 && B.Num() == 3)
				{
					Zone.Box = FBox(FVector(A[0]->AsNumber(), A[1]->AsNumber(), A[2]->AsNumber()), FVector(B[0]->AsNumber(), B[1]->AsNumber(), B[2]->AsNumber()));
				}
			}
			Out.Zones.Add(Zone);
		}
	}
	if (const TSharedPtr<FJsonObject> RP = Obj(AudioRoot, TEXT("reverbPresets")))
	{
		for (const auto& Pair : RP->Values)
		{
			const TSharedPtr<FJsonObject> E = Pair.Value->Type == EJson::Object ? Pair.Value->AsObject() : nullptr;
			if (!E.IsValid())
			{
				continue;
			}
			FMIReverbPreset P;
			P.Decay = Num(E, TEXT("decay"), P.Decay);
			P.Density = Num(E, TEXT("density"), P.Density);
			P.Diffusion = Num(E, TEXT("diffusion"), P.Diffusion);
			P.Gain = Num(E, TEXT("gain"), P.Gain);
			P.GainHF = Num(E, TEXT("gainHF"), P.GainHF);
			P.DecayHFRatio = Num(E, TEXT("decayHFRatio"), P.DecayHFRatio);
			P.ReflectionsGain = Num(E, TEXT("reflectionsGain"), P.ReflectionsGain);
			P.ReflectionsDelay = Num(E, TEXT("reflectionsDelay"), P.ReflectionsDelay);
			P.LateGain = Num(E, TEXT("lateGain"), P.LateGain);
			P.LateDelay = Num(E, TEXT("lateDelay"), P.LateDelay);
			P.AirAbsorptionHF = Num(E, TEXT("airAbsorptionHF"), P.AirAbsorptionHF);
			Out.Reverbs.Add(FName(FString(*Pair.Key)), P);
		}
	}

	// The event table.
	const TSharedPtr<FJsonObject> Ev = Obj(AudioRoot, TEXT("events"));
	if (!Ev.IsValid())
	{
		OutError = TEXT("audio.json: events missing");
		return false;
	}
	for (const auto& Pair : Ev->Values)
	{
		if (Pair.Value->Type == EJson::Object)
		{
			Out.Events.Add(FName(FString(*Pair.Key)), Pair.Value->AsObject());
		}
	}
	return true;
}

bool FMIAudioData::Load(FMIAudioData& Out, FString& OutError)
{
	TSharedPtr<FJsonObject> Sounds, Audio;
	return UMIDataSubsystem::LoadJsonFile(TEXT("audio_sounds.json"), Sounds, OutError)
		&& UMIDataSubsystem::LoadJsonFile(TEXT("audio.json"), Audio, OutError)
		&& Parse(Sounds, Audio, Out, OutError);
}
