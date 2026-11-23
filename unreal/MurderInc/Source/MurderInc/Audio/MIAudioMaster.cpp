#include "Audio/MIAudioMaster.h"

#include "Audio/MIAudioData.h"
#include "AudioDevice.h"
#include "AudioMixerBlueprintLibrary.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Sound/AudioSettings.h"
#include "Sound/SoundSubmix.h"
#include "SubmixEffects/AudioMixerSubmixEffectDynamicsProcessor.h"
#include "UObject/Package.h"

namespace MIAudioMasterPrivate
{
	/** The device's main submix asset (project audio settings), loaded. */
	USoundSubmix* MainSubmix()
	{
		const UAudioSettings* S = GetDefault<UAudioSettings>();
		return S ? Cast<USoundSubmix>(S->MasterSubmix.TryLoad()) : nullptr;
	}
	/** The main submix's own chain before ours went on (restored by Uninstall). */
	TArray<TObjectPtr<USoundEffectSubmixPreset>> SavedChain;
	bool bSaved = false;

	/** The two processors' settings from the chain's numbers. */
	void Settings(const FMIMasterChain& Ch, FSubmixEffectDynamicsProcessorSettings& S, FSubmixEffectDynamicsProcessorSettings& C)
	{
		S.DynamicsProcessorType = ESubmixEffectDynamicsProcessorType::Compressor;
		S.PeakMode = ESubmixEffectDynamicsPeakMode::Peak;
		S.LinkMode = ESubmixEffectDynamicsChannelLinkMode::Peak;
		S.ThresholdDb = (float)Ch.ThresholdDb;
		S.Ratio = (float)Ch.Ratio;
		S.KneeBandwidthDb = (float)Ch.KneeDb;
		S.AttackTimeMsec = (float)Ch.AttackMs;
		S.ReleaseTimeMsec = (float)Ch.ReleaseMs;
		S.LookAheadMsec = 0.f;
		S.InputGainDb = 0.f;
		S.OutputGainDb = (float)(20.0 * FMath::LogX(10.0, FMath::Max(1e-6, Ch.Makeup)));
		C = S;
		C.DynamicsProcessorType = ESubmixEffectDynamicsProcessorType::Limiter;
		C.ThresholdDb = (float)Ch.ClipThresholdDb;
		C.KneeBandwidthDb = (float)Ch.ClipKneeDb;
		C.Ratio = 20.f;
		C.AttackTimeMsec = (float)Ch.ClipAttackMs;
		C.ReleaseTimeMsec = (float)Ch.ClipReleaseMs;
		C.LookAheadMsec = (float)Ch.ClipLookAheadMs;
		C.OutputGainDb = 0.f;
	}
}

FMIMasterChain FMIMasterChain::FromData(const FMIAudioData& Data)
{
	using namespace MIAudioJson;
	FMIMasterChain C;
	const TSharedPtr<FJsonObject> M = Data.Table(TEXT("master"));
	if (!M.IsValid())
	{
		return C;
	}
	C.bEnabled = Flag(M, TEXT("enabled"), true);
	const TSharedPtr<FJsonObject> K = Obj(M, TEXT("compressor"));
	C.ThresholdDb = Num(K, TEXT("thresholdDb"), C.ThresholdDb);
	C.KneeDb = Num(K, TEXT("kneeDb"), C.KneeDb);
	C.Ratio = FMath::Max(1.0, Num(K, TEXT("ratio"), C.Ratio));
	C.AttackMs = Num(K, TEXT("attackMs"), C.AttackMs);
	C.ReleaseMs = Num(K, TEXT("releaseMs"), C.ReleaseMs);
	C.Makeup = Num(M, TEXT("makeup"), C.Makeup);
	const TSharedPtr<FJsonObject> L = Obj(M, TEXT("clip"));
	C.ClipThresholdDb = Num(L, TEXT("engineThresholdDb"), C.ClipThresholdDb);
	C.ClipKneeDb = Num(L, TEXT("engineKneeDb"), C.ClipKneeDb);
	C.ClipAttackMs = Num(L, TEXT("engineAttackMs"), C.ClipAttackMs);
	C.ClipReleaseMs = Num(L, TEXT("engineReleaseMs"), C.ClipReleaseMs);
	C.ClipLookAheadMs = Num(L, TEXT("engineLookAheadMs"), C.ClipLookAheadMs);
	return C;
}

bool FMIMasterChain::Install(UObject* WorldContext, TArray<TObjectPtr<USoundEffectSubmixPreset>>& OutKeep) const
{
	UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	if (!World || !World->GetAudioDeviceRaw() || !bEnabled)
	{
		return false;
	}
	UAudioMixerBlueprintLibrary::ClearMasterSubmixEffects(World);
	OutKeep.Reset();

	USubmixEffectDynamicsProcessorPreset* Comp = NewObject<USubmixEffectDynamicsProcessorPreset>(GetTransientPackage());
	USubmixEffectDynamicsProcessorPreset* Clip = NewObject<USubmixEffectDynamicsProcessorPreset>(GetTransientPackage());
	FSubmixEffectDynamicsProcessorSettings S, C;
	MIAudioMasterPrivate::Settings(*this, S, C);
	Comp->SetSettings(S);
	Clip->SetSettings(C);

	OutKeep.Add(Comp);
	OutKeep.Add(Clip);
	// The chain goes on the main submix asset itself and the submix is re-initialised from it: the path an
	// authored chain takes, so it survives any later re-initialisation (effects added with AddMasterSubmixEffect
	// alone did not act on the recorded output in the box's engine render).
	using namespace MIAudioMasterPrivate;
	USoundSubmix* Main = MainSubmix();
	FAudioDevice* Device = World->GetAudioDeviceRaw();
	if (Main && Device)
	{
		if (!bSaved)
		{
			SavedChain = Main->SubmixEffectChain;
			bSaved = true;
		}
		Main->SubmixEffectChain = {Comp, Clip};
		Device->RegisterSoundSubmix(Main, true);
		return true;
	}
	UAudioMixerBlueprintLibrary::AddMasterSubmixEffect(World, Comp);
	UAudioMixerBlueprintLibrary::AddMasterSubmixEffect(World, Clip);
	return true;
}

void FMIMasterChain::Uninstall(UObject* WorldContext)
{
	using namespace MIAudioMasterPrivate;
	UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	if (World && World->GetAudioDeviceRaw())
	{
		UAudioMixerBlueprintLibrary::ClearMasterSubmixEffects(World);
		if (USoundSubmix* Main = bSaved ? MainSubmix() : nullptr)
		{
			Main->SubmixEffectChain = SavedChain;
			World->GetAudioDeviceRaw()->RegisterSoundSubmix(Main, true);
			bSaved = false;
		}
	}
}

void FMIMasterChain::Refresh(const TArray<TObjectPtr<USoundEffectSubmixPreset>>& Presets) const
{
	FSubmixEffectDynamicsProcessorSettings S, C;
	MIAudioMasterPrivate::Settings(*this, S, C);
	for (int32 I = 0; I < Presets.Num(); ++I)
	{
		if (USubmixEffectDynamicsProcessorPreset* D = Cast<USubmixEffectDynamicsProcessorPreset>(Presets[I].Get()))
		{
			D->SetSettings(I == 0 ? S : C);
		}
	}
}

// ------------------------------------------------------------------------------------------- offline compressor

float FMIMasterCompressor::SoftClip(float X)
{
	const float A = FMath::Abs(X);
	if (A <= 0.6f)
	{
		return X;
	}
	return FMath::Sign(X) * (0.6f + 0.4f * FMath::Tanh((A - 0.6f) / 0.4f));
}

void FMIMasterCompressor::Init(const FMIMasterChain& InChain, int32 Rate)
{
	Chain = InChain;
	AttackK = FMath::Exp(-1.0 / (FMath::Max(0.1, Chain.AttackMs) * 0.001 * Rate));
	ReleaseK = FMath::Exp(-1.0 / (FMath::Max(0.1, Chain.ReleaseMs) * 0.001 * Rate));
	Env = 0.0;
	MaxReduction = 0.0;
}

double FMIMasterCompressor::CurveDb(double X) const
{
	// A soft-knee compressor's static curve (the knee centred on the threshold).
	const double T = Chain.ThresholdDb, W = Chain.KneeDb, R = Chain.Ratio;
	double Y = X;
	if (2.0 * (X - T) <= -W)
	{
		Y = X;
	}
	else if (W > 0.0 && 2.0 * FMath::Abs(X - T) < W)
	{
		const double D = X - T + W * 0.5;
		Y = X + (1.0 / R - 1.0) * D * D / (2.0 * W);
	}
	else
	{
		Y = T + (X - T) / R;
	}
	return FMath::Min(0.0, Y - X);
}

void FMIMasterCompressor::Process(float& L, float& R)
{
	if (!Chain.bEnabled)
	{
		L = SoftClip(L);
		R = SoftClip(R);
		return;
	}
	const double Level = FMath::Max(FMath::Abs((double)L), FMath::Abs((double)R));
	const double Target = CurveDb(20.0 * FMath::LogX(10.0, FMath::Max(1e-9, Level)));
	// The reduction deepens with the attack time and recovers with the release time.
	const double K = Target < Env ? AttackK : ReleaseK;
	Env = K * Env + (1.0 - K) * Target;
	MaxReduction = FMath::Min(MaxReduction, Env);
	const double G = FMath::Pow(10.0, Env / 20.0) * Chain.Makeup;
	L = SoftClip(float(L * G));
	R = SoftClip(float(R * G));
}
