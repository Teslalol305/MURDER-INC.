// MurderInc.Audio.EngineRender: the recorded fight through the engine's own audio mixer, not the offline one: the
// director's commands become audio components on the imported Sound Waves (decoding, pitch, volume, the mix gains and
// low-pass per category, as UMIAudioSubsystem applies them), and the master submix is recorded to a WAV in real time.
// The master chain (compressor, make-up, soft-knee limiter) sits on the master submix as in the game.
// Needs an audio device: the default test run (-NoSound) has none, so the test warns and passes; tools/box/
// audio-engine-render.sh runs it with an audio device on the SDL dummy driver (docs/unreal/AUDIO.md section 7).
// With a device it fails when the recording is shorter than the stream it rendered or quieter than -40 dBFS.

#include "AudioMixerBlueprintLibrary.h"
#include "Audio/MIAudioData.h"
#include "Audio/MIAudioDirector.h"
#include "Audio/MIAudioEventLog.h"
#include "Audio/MIAudioMaster.h"
#include "Audio/MIOfflineMix.h"
#include "AudioDevice.h"
#include "Components/AudioComponent.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Core/MIEvents.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "HAL/FileManager.h"
#include "Serialization/Archive.h"
#include "HAL/PlatformTime.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/AutomationTest.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Sound/SoundEffectSubmix.h"
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
		TArray<FString> Said;
		double ClockStart = 0.0, ClockSpan = 0.0;  // the audio device's own clock (its rendered time)
		TArray<TObjectPtr<USoundEffectSubmixPreset>> Master;
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
		if (Now < 2.0)
		{
			FMIMasterChain::FromData(X.Data).Refresh(X.Master);  // the device made the chain's instances on its thread: give them their settings
		}
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
				if (C.Category == TEXT("voice") && C.File.StartsWith(TEXT("Voice/")))
				{
					// On the device's clock, so the time matches the recording (the dummy driver's clock drifts from the wall clock).
					const double At = X.World->GetAudioDeviceRaw() ? X.World->GetAudioDeviceRaw()->GetAudioClock() - X.ClockStart : Now;
					X.Said.Add(FString::Printf(TEXT("%.2f:%s"), At, *FPaths::GetBaseFilename(C.File)));
				}
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
			double Cut = Cat && Cat->bMuffled ? M.MuffleCutoff : (C == TEXT("music") ? M.MusicCutoff : 20000.0);
			if (C == TEXT("ambience"))
			{
				Cut = FMath::Min(Cut, M.AmbienceCutoff);
			}
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
			X.ClockSpan = X.World->GetAudioDeviceRaw() ? X.World->GetAudioDeviceRaw()->GetAudioClock() - X.ClockStart : Now;
			X.bMade = UAudioMixerBlueprintLibrary::StopRecordingOutputToAnyPath(X.World, EAudioRecordingExportType::WavFile, TEXT("engine_render"), FPaths::GetPath(X.Out)) != nullptr;
			for (auto& Pair : X.Live)
			{
				Pair.Value->Stop();
			}
			X.Director.Unbind();
			FMIMasterChain::Uninstall(X.World);
			for (const TObjectPtr<USoundEffectSubmixPreset>& P : X.Master)
			{
				P->RemoveFromRoot();
			}
			X.bStopped = true;
			X.StoppedAt = Now;
			return false;
		}
		// Done when the file has the size its header announces (the writer fills it in chunks).
		bool bFile = false;
		const int64 Size = IFileManager::Get().FileSize(*X.Out);
		if (Size > 44)
		{
			TArray<uint8> Head;
			if (TUniquePtr<FArchive> Ar = TUniquePtr<FArchive>(IFileManager::Get().CreateFileReader(*X.Out)))
			{
				Head.SetNumZeroed(44);
				Ar->Serialize(Head.GetData(), 44);
				const int64 Riff = Head[4] | (Head[5] << 8) | (Head[6] << 16) | ((int64)Head[7] << 24);
				bFile = Size >= Riff + 8;
			}
		}
		if (!bFile && Now - X.StoppedAt < 90.0)
		{
			return false;
		}
		X.Test->AddInfo(FString::Printf(TEXT("engine render: %.1f s, %d components started, %d without an asset, wav %s (%lld bytes) -> %s"),
			X.StoppedAt, X.Started, X.NoAsset, bFile ? TEXT("written") : TEXT("missing"), bFile ? IFileManager::Get().FileSize(*X.Out) : 0LL, *X.Out));
		X.Test->AddInfo(TEXT("engine render voice lines (for tools/audio/render_report.py --voice): ") + FString::Join(X.Said, TEXT(",")));
		X.Test->TestTrue(TEXT("components started on the imported assets"), X.Started > 50);
		X.Test->TestTrue(TEXT("the engine wrote the recording"), bFile);
		// What the device produced: as long as the stream it rendered, and not silent.
		FMIWav Wav;
		FString Error;
		if (!bFile || !FMIWav::Load(X.Out, Wav, &Error))
		{
			X.Test->AddError(TEXT("the recording cannot be read: ") + Error);
			return true;
		}
		const double PeakDb = 20.0 * FMath::LogX(10.0, FMath::Max(1e-12, (double)Wav.Peak()));
		const double RmsDb = 20.0 * FMath::LogX(10.0, FMath::Max(1e-12, Wav.Rms()));
		X.Test->AddInfo(FString::Printf(TEXT("recording: %.2f s, %d channels at %d Hz, peak %.1f dBFS, RMS %.1f dBFS (stream %.1f s of wall clock, %.2f s of the device's clock)"),
			Wav.Secs(), Wav.Channels, Wav.Rate, PeakDb, RmsDb, X.StoppedAt, X.ClockSpan));
		// The whole stream: everything the device rendered between start and stop (its own clock), and never far
		// from the wall clock (a device that stalls renders less).
		X.Test->TestTrue(FString::Printf(TEXT("the recording (%.2f s) holds what the device rendered (%.2f s)"), Wav.Secs(), X.ClockSpan), Wav.Secs() >= X.ClockSpan - 0.5);
		X.Test->TestTrue(FString::Printf(TEXT("the recording (%.2f s) is at least 90 %% of the stream (%.1f s)"), Wav.Secs(), X.StoppedAt), Wav.Secs() >= 0.9 * X.StoppedAt);
		X.Test->TestTrue(FString::Printf(TEXT("the recording is not silent (peak %.1f dBFS, want above -40)"), PeakDb), PeakDb > -40.0);
		X.Test->TestTrue(TEXT("the voice spoke in the render"), X.Said.Num() >= 3);
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
	// A complete file from an earlier run would pass the wait below at once: this run's recording must replace it.
	IFileManager::Get().Delete(*R->Out, false, true, true);
	if (IFileManager::Get().FileExists(*R->Out))
	{
		AddError(TEXT("cannot remove the previous recording ") + R->Out);
		return false;
	}
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
	if (FMIMasterChain::FromData(R->Data).Install(World, R->Master))
	{
		for (const TObjectPtr<USoundEffectSubmixPreset>& P : R->Master)
		{
			P->AddToRoot();
		}
	}
	else
	{
		AddWarning(TEXT("the master chain could not be installed"));
	}
	UAudioMixerBlueprintLibrary::StartRecordingOutput(World, (float)R->Secs + 2.f);
	R->ClockStart = World->GetAudioDeviceRaw()->GetAudioClock();
	R->Start = FPlatformTime::Seconds();
	ADD_LATENT_AUTOMATION_COMMAND(FMIAudioEngineRenderCommand(R));
	return true;
}

#endif
