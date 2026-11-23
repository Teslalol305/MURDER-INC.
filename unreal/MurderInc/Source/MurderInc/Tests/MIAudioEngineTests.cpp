// MurderInc.Audio.EngineRender: the recorded fight through the engine's own audio mixer, not the offline one: the
// director's commands become audio components on the imported Sound Waves (decoding, pitch, volume, the mix gains and
// low-pass per category, as UMIAudioSubsystem applies them), and the master submix is recorded to a WAV in real time.
// Needs an audio device: the default test run (-NoSound) has none, so the test warns and passes; tools/box/
// audio-engine-render.sh runs it with an audio device on the SDL dummy driver (docs/unreal/AUDIO.md section 7).

#include "AudioMixerBlueprintLibrary.h"
#include "Audio/MIAudioData.h"
#include "Audio/MIAudioDirector.h"
#include "Audio/MIAudioEventLog.h"
#include "AudioDevice.h"
#include "Components/AudioComponent.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Core/MIEvents.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformTime.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Sound/SoundWave.h"
#include "UObject/StrongObjectPtr.h"

#if WITH_AUTOMATION_TESTS

namespace MIAudioEnginePrivate
{
	struct FRender
	{
		FMIAudioData Data;
		FMIVoiceData Voice;
		FMIAudioDirector Director;
		FMIAudioEventLog Log;
		FMIGameEvents Bus;
		TMap<int32, TStrongObjectPtr<UAudioComponent>> Live;
		TMap<int32, double> Base;
		TMap<int32, FName> Cat;
		UWorld* World = nullptr;
		double Start = 0.0, Last = 0.0, Secs = 20.0;
		int32 Started = 0, NoAsset = 0;
		bool bStopped = false;
		double StoppedAt = 0.0;
		bool bMade = false;
		FString Out;
		FAutomationTestBase* Test = nullptr;
	};

	UWorld* AudioWorld()
	{
		for (const FWorldContext& C : GEngine->GetWorldContexts())
		{
			UWorld* W = C.World();
			if (W && W->GetAudioDeviceRaw())
			{
				return W;
			}
		}
		return nullptr;
	}
}

class FMIAudioEngineRenderCommand : public IAutomationLatentCommand
{
public:
	explicit FMIAudioEngineRenderCommand(TSharedPtr<MIAudioEnginePrivate::FRender> InR) : R(InR) {}

	virtual bool Update() override
	{
		MIAudioEnginePrivate::FRender& X = *R;
		const double Now = FPlatformTime::Seconds() - X.Start;
		const double Dt = Now - X.Last;
		X.Log.ReplayRange(X.Last - (X.Last == 0.0 ? 1.0 : 0.0), Now, X.Bus, &X.Director);
		X.Last = Now;
		X.Director.Tick(Dt);
		TArray<FMIAudioCmd> Cmds;
		X.Director.TakeCommands(Cmds);
		const FMIMixState& M = X.Director.GetMix();
		for (const FMIAudioCmd& C : Cmds)
		{
			if (C.Type == EMIAudioCmd::Start)
			{
				USoundWave* W = LoadObject<USoundWave>(nullptr, *FMIAudioData::AssetPath(C.File), nullptr, LOAD_NoWarn | LOAD_Quiet);
				if (!W)
				{
					++X.NoAsset;
					continue;
				}
				UAudioComponent* A = UGameplayStatics::CreateSound2D(X.World, W, 1.f, (float)C.Pitch, 0.f, nullptr, false, false);
				if (!A)
				{
					continue;
				}
				// 2D here (the editor world has no listener to place): the distance gain of spec 07 stands in.
				double G = C.Volume;
				if (C.b3D)
				{
					G *= FMIAudioData::DistanceGain(FVector::Dist(C.Pos, X.Director.GetListener()) / 100.0, C.Ref / 100.0, C.Roll);
				}
				A->SetVolumeMultiplier((float)(G * (M.Gain.Contains(C.Category) ? M.Gain[C.Category] : 1.0)));
				A->Play();
				X.Live.Add(C.Id, TStrongObjectPtr<UAudioComponent>(A));
				X.Base.Add(C.Id, G);
				X.Cat.Add(C.Id, C.Category);
				++X.Started;
			}
			else if (TStrongObjectPtr<UAudioComponent>* A = X.Live.Find(C.Id))
			{
				if (C.Type == EMIAudioCmd::Set)
				{
					X.Base.Add(C.Id, C.Volume);
					if (C.Pitch > 0.0)
					{
						(*A)->SetPitchMultiplier((float)C.Pitch);
					}
				}
				else
				{
					(*A)->FadeOut(FMath::Max(0.01f, (float)C.Fade), 0.f);
					X.Live.Remove(C.Id);
				}
			}
		}
		// The mix, as UMIAudioSubsystem::ApplyMix does it.
		for (auto& Pair : X.Live)
		{
			const FName C = X.Cat.FindRef(Pair.Key);
			const FMIAudioCategory* Cat = X.Data.Categories.Find(C);
			Pair.Value->SetVolumeMultiplier((float)(X.Base.FindRef(Pair.Key) * (M.Gain.Contains(C) ? M.Gain[C] : 1.0)));
			const double Cut = Cat && Cat->bMuffled ? M.MuffleCutoff : (C == TEXT("music") ? M.MusicCutoff : 20000.0);
			Pair.Value->SetLowPassFilterEnabled(Cut < 19990.0);
			Pair.Value->SetLowPassFilterFrequency((float)Cut);
		}
		if (Now < X.Secs)
		{
			return false;
		}
		if (!X.bStopped)
		{
			// The WAV export is written on a background task: wait for the file below.
			X.bMade = UAudioMixerBlueprintLibrary::StopRecordingOutputToAnyPath(X.World, EAudioRecordingExportType::WavFile, TEXT("engine_render"), FPaths::GetPath(X.Out)) != nullptr;
			for (auto& Pair : X.Live)
			{
				Pair.Value->Stop();
			}
			X.Director.Unbind();
			X.bStopped = true;
			X.StoppedAt = Now;
			return false;
		}
		const bool bFile = FPaths::FileExists(X.Out) && IFileManager::Get().FileSize(*X.Out) > 44;
		if (!bFile && Now - X.StoppedAt < 15.0)
		{
			return false;
		}
		X.Test->AddInfo(FString::Printf(TEXT("engine render: %.1f s, %d components started, %d without an asset, wav %s (%lld bytes) -> %s"),
			X.StoppedAt, X.Started, X.NoAsset, bFile ? TEXT("written") : TEXT("missing"), bFile ? IFileManager::Get().FileSize(*X.Out) : 0LL, *X.Out));
		X.Test->TestTrue(TEXT("components started on the imported assets"), X.Started > 50);
		X.Test->TestTrue(TEXT("the engine wrote the recording"), bFile);
		return true;
	}

private:
	TSharedPtr<MIAudioEnginePrivate::FRender> R;
};

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIAudioEngineRenderTest, "MurderInc.Audio.EngineRender",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::ClientContext | EAutomationTestFlags::ProductFilter)

bool FMIAudioEngineRenderTest::RunTest(const FString& Parameters)
{
	using namespace MIAudioEnginePrivate;
	UWorld* World = AudioWorld();
	if (!World)
	{
		AddWarning(TEXT("no audio device in this process (-NoSound): run tools/box/audio-engine-render.sh for the engine's own render"));
		return true;
	}
	if (!FPackageName::DoesPackageExist(TEXT("/Game/Audio/Web/chopper_shot_01")))
	{
		AddWarning(TEXT("audio assets not imported: run tools/box/audio-import.sh first"));
		return true;
	}
	TSharedPtr<FRender> R = MakeShared<FRender>();
	FString Error;
	if (!FMIAudioData::Load(R->Data, Error) || !FMIVoiceData::Load(R->Voice, Error)
		|| !R->Log.Load(FPaths::Combine(UMIDataSubsystem::GetDataDir(), TEXT("audio_fight.json")), Error))
	{
		AddError(Error);
		return false;
	}
	R->World = World;
	R->Test = this;
	R->Secs = FCString::Atod(*Parameters) > 0.0 ? FCString::Atod(*Parameters) : FMath::Min(R->Log.Duration() + 3.0, 56.0);
	R->Out = FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Audio"), TEXT("engine_render.wav")));
	R->Director.Exists = [](const FString& F)
	{
		FString P = FMIAudioData::AssetPath(F);
		P.Split(TEXT("."), &P, nullptr);
		return FPackageName::DoesPackageExist(P);
	};
	R->Director.FileSecs = [](const FString& F)
	{
		const USoundWave* W = LoadObject<USoundWave>(nullptr, *FMIAudioData::AssetPath(F), nullptr, LOAD_NoWarn | LOAD_Quiet);
		return W ? (double)W->Duration : 0.0;
	};
	R->Director.Init(&R->Data, &R->Voice, 11);
	R->Director.Bind(R->Bus);
	UAudioMixerBlueprintLibrary::StartRecordingOutput(World, (float)R->Secs + 2.f);
	R->Start = FPlatformTime::Seconds();
	ADD_LATENT_AUTOMATION_COMMAND(FMIAudioEngineRenderCommand(R));
	return true;
}

#endif
