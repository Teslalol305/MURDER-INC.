#include "Audio/MIAudioSubsystem.h"

#include "Audio/MIAudioMaster.h"
#include "Sound/SoundEffectSubmix.h"

#include "Camera/PlayerCameraManager.h"
#include "CanvasItem.h"
#include "Components/AudioComponent.h"
#include "Core/MIEvents.h"
#include "Enemies/MIEnemyActors.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/HUD.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Player/MIPlayerCharacter.h"
#include "Sound/ReverbEffect.h"
#include "Sound/SoundWave.h"

DEFINE_LOG_CATEGORY_STATIC(LogMIAudioHost, Log, All);

namespace MIAudioHostPrivate
{
	// Game thread only.
	UMIAudioSubsystem::FCounts GCounts;
	TSet<FString> GNoted;

	UMIAudioSubsystem* FirstGameAudio(UWorld* World)
	{
		return World ? World->GetSubsystem<UMIAudioSubsystem>() : nullptr;
	}

	FMIAudioOptions& Edit(UWorld* World, bool& bOk)
	{
		static FMIAudioOptions Dummy;
		UMIAudioSubsystem* A = FirstGameAudio(World);
		bOk = A != nullptr;
		if (!A)
		{
			return Dummy;
		}
		static FMIAudioOptions Copy;
		Copy = A->GetOptions();
		return Copy;
	}

	FAutoConsoleCommandWithWorldAndArgs VolumeCmd(
		TEXT("MIAudio.Volume"),
		TEXT("MIAudio.Volume <master|effects|ambience|music|ui|voice> <0..1>: an options slider"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			bool bOk = false;
			FMIAudioOptions& O = Edit(World, bOk);
			if (!bOk || Args.Num() < 2)
			{
				return;
			}
			const double V = FMath::Clamp(FCString::Atod(*Args[1]), 0.0, 1.0);
			const FString& K = Args[0];
			if (K == TEXT("master")) O.Master = V;
			else if (K == TEXT("effects")) O.Effects = V;
			else if (K == TEXT("ambience")) O.Ambience = V;
			else if (K == TEXT("music")) O.Music = V;
			else if (K == TEXT("ui")) O.UI = V;
			else if (K == TEXT("voice")) O.Voice.Volume = V;
			FirstGameAudio(World)->SetOptions(O);
		}));

	FAutoConsoleCommandWithWorldAndArgs VoiceCmd(
		TEXT("MIVoice"),
		TEXT("MIVoice frequency <off|rare|normal|often> | subtitles <0|1> | clean <0|1> | character <id>: the voice options"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			bool bOk = false;
			FMIAudioOptions& O = Edit(World, bOk);
			if (!bOk || Args.Num() < 2)
			{
				return;
			}
			if (Args[0] == TEXT("frequency")) O.Voice.Frequency = FName(Args[1]);
			else if (Args[0] == TEXT("subtitles")) O.Voice.bSubtitles = Args[1] != TEXT("0");
			else if (Args[0] == TEXT("clean")) O.Voice.bClean = Args[1] != TEXT("0");
			else if (Args[0] == TEXT("character"))
			{
				FirstGameAudio(World)->SetCharacter(FName(Args[1]));
				return;
			}
			FirstGameAudio(World)->SetOptions(O);
		}));

#if !UE_BUILD_SHIPPING  // a debug command that writes a file named by its caller: not in the Shipping game
	FAutoConsoleCommandWithWorldAndArgs RecordCmd(
		TEXT("MIAudio.Record"),
		TEXT("MIAudio.Record start | stop [name]: record the event bus to Saved/Audio/<name>.json for MurderInc.Audio.Mixdown"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			UMIAudioSubsystem* A = FirstGameAudio(World);
			if (!A || Args.Num() < 1)
			{
				return;
			}
			if (Args[0] == TEXT("start"))
			{
				A->StartRecording();
			}
			else
			{
				FString Path;
				A->StopRecording(Args.Num() > 1 ? Args[1] : TEXT("recorded"), Path);
				UE_LOG(LogMIAudioHost, Display, TEXT("MIAudio.Record: %s"), *Path);
			}
		}));
#endif
}

UMIAudioSubsystem::FCounts UMIAudioSubsystem::GetCounts()
{
	return MIAudioHostPrivate::GCounts;
}

void UMIAudioSubsystem::NoteMissing(const FString& What, const FString& Why)
{
	bool bAlready = false;
	MIAudioHostPrivate::GNoted.Add(What, &bAlready);
	if (bAlready)
	{
		return;
	}
	++MIAudioHostPrivate::GCounts.Missing;
	// A warning, once per sound: versions 1 to 3a of the cloud package had no Sound Wave at all and said nothing.
	UE_LOG(LogMIAudioHost, Warning, TEXT("sound missing: %s: %s. It will not be heard."), *What, *Why);
}

bool UMIAudioSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	const UWorld* World = Cast<UWorld>(Outer);
	return World && (World->WorldType == EWorldType::Game || World->WorldType == EWorldType::PIE);
}

TStatId UMIAudioSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UMIAudioSubsystem, STATGROUP_Tickables);
}

UMIAudioSubsystem* UMIAudioSubsystem::Get(const UObject* WorldContextObject)
{
	const UWorld* World = WorldContextObject ? WorldContextObject->GetWorld() : nullptr;
	return World ? World->GetSubsystem<UMIAudioSubsystem>() : nullptr;
}

void UMIAudioSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	Collection.InitializeDependency<UMIEventSubsystem>();
	FString Error;
	if (!FMIAudioData::Load(Data, Error))
	{
		UE_LOG(LogMIAudioHost, Error, TEXT("audio data: %s"), *Error);
		return;
	}
	const bool bVoice = FMIVoiceData::Load(Voice, Error);
	if (!bVoice)
	{
		UE_LOG(LogMIAudioHost, Error, TEXT("voice data: %s"), *Error);
	}
	else
	{
		// Once per world: how much of the voice is still the stand-in (voice.json "placeholder" per take).
		int32 Takes = 0, Placeholders = 0;
		Voice.CountTakes(Takes, Placeholders);
		UE_LOG(LogMIAudioHost, Display, TEXT("voice: %d of %d takes are placeholders (stock synthetic voice, not the character's: docs/unreal/AUDIO.md section 5)"), Placeholders, Takes);
	}
	Director.Exists = [this](const FString& File)
	{
		if (const bool* B = ExistsCache.Find(File))
		{
			return *B;
		}
		FString Package = FMIAudioData::AssetPath(File);
		Package.Split(TEXT("."), &Package, nullptr);
		const bool bExists = FPackageName::DoesPackageExist(Package);
		ExistsCache.Add(File, bExists);
		if (!bExists)
		{
			NoteMissing(File, FString::Printf(TEXT("no Sound Wave asset %s (tools/box/audio-import.sh in the clone the package is made from, then package again)"), *Package));
		}
		return bExists;
	};
	Director.FileSecs = [this](const FString& File)
	{
		const USoundWave* W = Wave(File);
		return W ? (double)W->Duration : 0.0;
	};
	Director.Blocked = [this](const FVector& From, const FVector& To)
	{
		FHitResult Hit;
		return GetWorld() && GetWorld()->LineTraceSingleByChannel(Hit, From, To, ECC_Visibility);
	};
	Director.Init(&Data, bVoice ? &Voice : nullptr);
	bReady = true;
	HudHandle = AHUD::OnHUDPostRender.AddUObject(this, &UMIAudioSubsystem::DrawSubtitle);
}

void UMIAudioSubsystem::Deinitialize()
{
	AHUD::OnHUDPostRender.Remove(HudHandle);
	Log.StopRecording();
	Director.Unbind();
	for (auto& Pair : Components)
	{
		if (UAudioComponent* C = Pair.Value.Component.Get())
		{
			C->Stop();
		}
	}
	Components.Reset();
	if (!ActiveReverb.IsNone())
	{
		UGameplayStatics::DeactivateReverbEffect(GetWorld(), ActiveReverb);
	}
	if (MasterChain.Num() > 0)
	{
		FMIMasterChain::Uninstall(GetWorld());
		MasterChain.Reset();
	}
	Super::Deinitialize();
}

void UMIAudioSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	if (FMIGameEvents* Bus = UMIEventSubsystem::Get(&InWorld); Bus && bReady && !bBound)
	{
		Director.Bind(*Bus);
		bBound = true;
	}
	if (bReady && FMIMasterChain::FromData(Data).Install(&InWorld, MasterChain))
	{
		UE_LOG(LogMIAudioHost, Display, TEXT("master chain on the master submix: compressor, make-up, soft-knee limiter (audio.json master)"));
	}
	if (bReady && InWorld.GetAudioDeviceRaw())
	{
		Preload();
	}
}

void UMIAudioSubsystem::Preload()
{
	const double T0 = FPlatformTime::Seconds();
	TSet<FString> Files;
	for (const auto& Pair : Data.Sounds)
	{
		for (const FString& F : Pair.Value.Files)
		{
			Files.Add(F);
		}
	}
	for (const auto& Pair : Data.Replace)
	{
		for (const FMIReplaceLayer& L : Pair.Value.Layers)
		{
			for (const FString& F : L.Files)
			{
				Files.Add(F);
			}
		}
	}
	for (const auto& Pair : Voice.Characters)
	{
		for (const FMIVoiceLine& L : Pair.Value.Lines)
		{
			for (const TArray<FMIVoiceTake>* Set : {&L.Takes, &L.CleanTakes})
			{
				for (const FMIVoiceTake& T : *Set)
				{
					Files.Add(FString::Printf(TEXT("Voice/%s/%s"), *Pair.Key.ToString(), *T.File));
				}
			}
		}
	}
	int32 Ready = 0;
	for (const FString& F : Files)
	{
		if (USoundWave* W = Wave(F))
		{
			W->RetainCompressedAudio(false);  // its audio is read from the pak now (in the background) and stays in memory
			++Ready;
		}
	}
	const int32 Missing = Files.Num() - Ready;
	if (Missing > 0)
	{
		UE_LOG(LogMIAudioHost, Warning, TEXT("sounds: %d of the %d Sound Waves the data names are MISSING from this build (each is named above): the game will be silent where they belong"), Missing, Files.Num());
	}
	UE_LOG(LogMIAudioHost, Display, TEXT("sounds: %d of %d Sound Waves loaded and kept in memory in %.0f ms"), Ready, Files.Num(), (FPlatformTime::Seconds() - T0) * 1000.0);
}

USoundWave* UMIAudioSubsystem::Wave(const FString& File)
{
	if (const TWeakObjectPtr<USoundWave>* W = Waves.Find(File))
	{
		return W->Get();
	}
	USoundWave* W = nullptr;
	if (Director.Exists(File))
	{
		W = LoadObject<USoundWave>(nullptr, *FMIAudioData::AssetPath(File), nullptr, LOAD_NoWarn | LOAD_Quiet);
	}
	if (W)
	{
		Loaded.Add(W);
	}
	else
	{
		NoteMissing(File, FString::Printf(TEXT("no Sound Wave asset %s (tools/box/audio-import.sh in the clone the package is made from, then package again)"), *FMIAudioData::AssetPath(File)));
	}
	Waves.Add(File, W);
	return W;
}

const FSoundAttenuationSettings& UMIAudioSubsystem::Attenuation(FName Category, double Ref, double Roll)
{
	const FString Key = FString::Printf(TEXT("%s/%.0f/%.3f"), *Category.ToString(), Ref, Roll);
	if (const FSoundAttenuationSettings* S = Attenuations.Find(Key))
	{
		return *S;
	}
	FSoundAttenuationSettings S;
	S.bAttenuate = true;
	S.bSpatialize = true;
	S.AttenuationShape = EAttenuationShape::Sphere;
	S.AttenuationShapeExtents = FVector::ZeroVector;
	const double Cull = Data.Cull * 100.0;
	S.FalloffDistance = (float)Cull;
	// Spec 07 2.11 inverse distance model, sampled densely near the source.
	S.DistanceAlgorithm = EAttenuationDistanceModel::Custom;
	FRichCurve* Curve = S.CustomAttenuationCurve.GetRichCurve();
	Curve->Reset();
	const int32 N = FMath::Max(8, Data.CurvePoints);
	for (int32 I = 0; I <= N; ++I)
	{
		const double X = FMath::Square(double(I) / N);
		Curve->AddKey((float)X, (float)FMIAudioData::DistanceGain(X * Data.Cull, Ref / 100.0, Roll));
	}
	// Air absorption: 20 kHz * exp(-d / 48 m) is a straight line in log frequency.
	S.bAttenuateWithLPF = true;
	S.bEnableLogFrequencyScaling = true;
	S.LPFRadiusMin = 0.f;
	S.LPFRadiusMax = 10000.f;
	S.LPFFrequencyAtMin = 20000.f;
	S.LPFFrequencyAtMax = (float)FMath::Max(Data.AirMin, 20000.0 * FMath::Exp(-100.0 / Data.AirScale));
	// The engine's occlusion trace.
	S.bEnableOcclusion = Data.bOcclusion;
	S.OcclusionTraceChannel = ECC_Visibility;
	S.OcclusionLowPassFilterFrequency = (float)Data.OcclusionCutoff;
	S.OcclusionVolumeAttenuation = (float)Data.OcclusionGain;
	S.OcclusionInterpolationTime = (float)Data.OcclusionInterp;
	// The reverb send of the category (spec 07 2.11).
	const FMIAudioCategory* Cat = Data.Categories.Find(Category);
	S.bEnableReverbSend = Cat && Cat->Reverb > 0.0;
	S.ReverbSendMethod = EReverbSendMethod::Manual;
	S.ManualReverbSendLevel = Cat ? (float)Cat->Reverb : 0.f;
	return Attenuations.Add(Key, S);
}

void UMIAudioSubsystem::Execute(const FMIAudioCmd& C)
{
	UWorld* World = GetWorld();
	if (C.Type == EMIAudioCmd::Start)
	{
		USoundWave* W = Wave(C.File);
		if (!W || !World)
		{
			return;
		}
		if (C.bLoop)
		{
			W->bLooping = true;
		}
		UAudioComponent* A = UGameplayStatics::CreateSound2D(World, W, 1.f, (float)C.Pitch, 0.f, nullptr, false, true);
		if (!A)
		{
			++MIAudioHostPrivate::GCounts.NoDevice;
			return;  // no audio device (headless runs)
		}
		const FMIAudioCategory* Cat = Data.Categories.Find(C.Category);
		A->bIsUISound = Cat && Cat->bUI;
		if (C.b3D)
		{
			A->bAllowSpatialization = true;
			A->bOverrideAttenuation = true;
			A->AttenuationOverrides = Attenuation(C.Category, C.Ref, C.Roll);
			A->SetWorldLocation(C.Pos);
		}
		const double G = Director.GetMix().Gain.Contains(C.Category) ? Director.GetMix().Gain[C.Category] : 1.0;
		A->SetVolumeMultiplier((float)(C.Volume * G));
		A->Play();
		Components.Add(C.Id, {A, C.Category, C.Volume});
		++MIAudioHostPrivate::GCounts.Played;
		// What played when, for the listening tests (tools/box/cloud/rtcaudio.py): -LogCmds="LogMIAudioHost Verbose".
		UE_LOG(LogMIAudioHost, Verbose, TEXT("play %s sound=%s category=%s volume=%.3f mix=%.3f pitch=%.3f%s%s"), *C.File, *C.Sound.ToString(), *C.Category.ToString(),
			C.Volume, G, C.Pitch, C.b3D ? TEXT(" 3d") : TEXT(""), C.bLoop ? TEXT(" loop") : TEXT(""));
	}
	else if (FPlaying* P = Components.Find(C.Id))
	{
		UAudioComponent* A = P->Component.Get();
		if (C.Type == EMIAudioCmd::Set)
		{
			P->Volume = C.Volume;
			if (A && C.Pitch > 0.0)
			{
				A->SetPitchMultiplier((float)C.Pitch);
			}
			if (A && C.b3D)
			{
				A->SetWorldLocation(C.Pos);
			}
		}
		else
		{
			if (A)
			{
				// A paused world does not advance fades: stop at once (a restart from the pause menu cuts the voice).
				const bool bPausedWorld = GetWorld() && GetWorld()->IsPaused();
				C.Fade > 0.0 && !bPausedWorld ? A->FadeOut((float)C.Fade, 0.f) : A->Stop();
			}
			Components.Remove(C.Id);
		}
	}
}

void UMIAudioSubsystem::ApplyMix()
{
	const FMIMixState& M = Director.GetMix();
	for (auto It = Components.CreateIterator(); It; ++It)
	{
		UAudioComponent* A = It->Value.Component.Get();
		if (!A || !A->IsPlaying())
		{
			It.RemoveCurrent();
			continue;
		}
		const double G = M.Gain.Contains(It->Value.Category) ? M.Gain[It->Value.Category] : 1.0;
		A->SetVolumeMultiplier((float)(It->Value.Volume * G));
		const FMIAudioCategory* Cat = Data.Categories.Find(It->Value.Category);
		double Cut = 20000.0;
		if (Cat && Cat->bMuffled)
		{
			Cut = M.MuffleCutoff;
		}
		else if (It->Value.Category == TEXT("music"))
		{
			Cut = M.MusicCutoff;
		}
		if (It->Value.Category == TEXT("ambience"))
		{
			Cut = FMath::Min(Cut, M.AmbienceCutoff);
		}
		A->SetLowPassFilterEnabled(Cut < 19990.0);
		A->SetLowPassFilterFrequency((float)Cut);
	}
}

void UMIAudioSubsystem::ApplyReverb()
{
	const FName Want = Director.GetMix().Reverb;
	if (Want == ActiveReverb || !GetWorld())
	{
		return;
	}
	if (!ActiveReverb.IsNone())
	{
		UGameplayStatics::DeactivateReverbEffect(GetWorld(), ActiveReverb);
	}
	ActiveReverb = Want;
	const FMIReverbPreset* P = Data.Reverbs.Find(Want);
	if (!P)
	{
		return;
	}
	TObjectPtr<UReverbEffect>& R = Reverbs.FindOrAdd(Want);
	if (!R)
	{
		R = NewObject<UReverbEffect>(this);
		R->Density = (float)P->Density;
		R->Diffusion = (float)P->Diffusion;
		R->Gain = (float)P->Gain;
		R->GainHF = (float)P->GainHF;
		R->DecayTime = (float)P->Decay;
		R->DecayHFRatio = (float)P->DecayHFRatio;
		R->ReflectionsGain = (float)P->ReflectionsGain;
		R->ReflectionsDelay = (float)P->ReflectionsDelay;
		R->LateGain = (float)P->LateGain;
		R->LateDelay = (float)P->LateDelay;
		R->AirAbsorptionGainHF = (float)P->AirAbsorptionHF;
	}
	UGameplayStatics::ActivateReverbEffect(GetWorld(), R, Want, 1.f, 1.f, 0.35f);
}

void UMIAudioSubsystem::Observe()
{
	UWorld* World = GetWorld();
	APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	if (PC && PC->PlayerCameraManager)
	{
		Director.SetListener(PC->PlayerCameraManager->GetCameraLocation(), PC->PlayerCameraManager->GetCameraRotation().Vector());
	}
	if (const AMIPlayerCharacter* P = PC ? Cast<AMIPlayerCharacter>(PC->GetPawn()) : nullptr)
	{
		// Public player state (spec 01 2.16), as the HUD reads it: the heartbeat and the low-health filter.
		const FMIPlayerRules& R = P->GetPlayerRules();
		Director.SetPlayer(R.MaxHealth > 0.0 ? R.Health / R.MaxHealth : 1.0, R.bAlive);
	}
	for (TActorIterator<AMIBuzzard> It(World); It; ++It)
	{
		Director.SetEnemy(It->GetSlot(), true, It->GetActorLocation(), It->GetView().bAlive);
	}
	for (TActorIterator<AMIGoon> It(World); It; ++It)
	{
		Director.SetEnemy(It->GetSlot(), false, It->GetActorLocation(), It->GetView().bAlive && !It->IsHidden());
	}
}

void UMIAudioSubsystem::Tick(float DeltaTime)
{
	if (!bReady || !GetWorld() || !GetWorld()->HasBegunPlay())
	{
		return;
	}
	if (!bBound)
	{
		if (FMIGameEvents* Bus = UMIEventSubsystem::Get(GetWorld()))
		{
			Director.Bind(*Bus);
			bBound = true;
		}
	}
	// Real seconds: the tick runs while the world is paused; the director knows the pause from the flow.
	const double Dt = FMath::Clamp((double)FApp::GetDeltaTime(), 0.0, 0.1);
	Observe();
	Director.Tick(Dt);
	TArray<FMIAudioCmd> Cmds;
	Director.TakeCommands(Cmds);
	for (const FMIAudioCmd& C : Cmds)
	{
		Execute(C);
	}
	for (const FName Id : Director.TakeUnknown())
	{
		NoteMissing(Id.ToString(), TEXT("the game asked for this sound id and the audio data has no such sound (audio_sounds.json, audio.json replace and weaponSounds)"));
	}
	ApplyMix();
	ApplyReverb();
	if (MasterChain.Num() > 0 && ChainRefreshes < 120)
	{
		// The first two seconds after the chain went on: its instances pick up the settings (FMIMasterChain::Refresh).
		FMIMasterChain::FromData(Data).Refresh(MasterChain);
		++ChainRefreshes;
	}
	if (bRecording)
	{
		RecordClock += Dt;
		ObserveTimer -= Dt;
		if (ObserveTimer <= 0.0)
		{
			ObserveTimer = 0.1;
			const FMIPlayerRules* R = nullptr;
			if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
			{
				if (const AMIPlayerCharacter* P = Cast<AMIPlayerCharacter>(PC->GetPawn()))
				{
					R = &P->GetPlayerRules();
				}
				if (PC->PlayerCameraManager)
				{
					Log.Observe(RecordClock, PC->PlayerCameraManager->GetCameraLocation(), PC->PlayerCameraManager->GetCameraRotation().Vector(),
						R && R->MaxHealth > 0.0 ? R->Health / R->MaxHealth : 1.0, R ? R->bAlive : true);
				}
			}
		}
	}
}

void UMIAudioSubsystem::StartRecording()
{
	if (FMIGameEvents* Bus = UMIEventSubsystem::Get(GetWorld()))
	{
		RecordClock = 0.0;
		ObserveTimer = 0.0;
		bRecording = true;
		Log.Record(*Bus, [this]() { return RecordClock; });
	}
}

bool UMIAudioSubsystem::StopRecording(const FString& Name, FString& OutPath)
{
	Log.StopRecording();
	bRecording = false;
	OutPath = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Audio"), Name + TEXT(".json"));
	return Log.Save(OutPath);
}

void UMIAudioSubsystem::DrawSubtitle(AHUD* HUD, UCanvas* Canvas)
{
	if (!HUD || !Canvas || HUD->GetWorld() != GetWorld())
	{
		return;
	}
	const FMISubtitle& S = Director.GetSubtitle();
	if (S.Text.IsEmpty())
	{
		return;
	}
	UFont* Font = GEngine ? GEngine->GetLargeFont() : nullptr;
	if (!Font)
	{
		return;
	}
	// Under the crosshair, above the weapon bar: speaker in gold (#f6c21a), the line in ink (#f4f2ec), on a plate.
	const float Scale = FMath::Max(1.f, Canvas->ClipY / 1080.f) * 1.25f;
	const FString Speaker = S.Speaker + TEXT("  ");
	float SW = 0.f, SH = 0.f, TW = 0.f, TH = 0.f;
	Canvas->TextSize(Font, Speaker, SW, SH, Scale, Scale);
	Canvas->TextSize(Font, S.Text, TW, TH, Scale, Scale);
	const float X = (Canvas->ClipX - SW - TW) * 0.5f;
	const float Y = Canvas->ClipY * 0.72f;
	FCanvasTileItem Plate(FVector2D(X - 14.f * Scale, Y - 6.f * Scale), FVector2D(SW + TW + 28.f * Scale, FMath::Max(SH, TH) + 12.f * Scale), FLinearColor(0.0048f, 0.0056f, 0.0070f, 0.72f));
	Plate.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Plate);
	Canvas->SetDrawColor(FColor(0xF6, 0xC2, 0x1A));
	Canvas->DrawText(Font, Speaker, X, Y, Scale, Scale);
	Canvas->SetDrawColor(FColor(0xF4, 0xF2, 0xEC));
	Canvas->DrawText(Font, S.Text, X + SW, Y, Scale, Scale);
#if !UE_BUILD_SHIPPING
	// A stand-in take says so (never in a shipping build): small, dim, under the line.
	if (S.bPlaceholder)
	{
		const float Small = Scale * 0.5f;
		Canvas->SetDrawColor(FColor(0xF4, 0xF2, 0xEC, 0x90));
		Canvas->DrawText(Font, TEXT("placeholder voice"), X, Y + FMath::Max(SH, TH) + 8.f * Scale, Small, Small);
	}
#endif
}
