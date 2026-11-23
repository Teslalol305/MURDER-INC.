#pragma once

#include "CoreMinimal.h"
#include "Audio/MIAudioData.h"
#include "Audio/MIAudioDirector.h"
#include "Audio/MIAudioEventLog.h"
#include "Audio/MIVoiceRules.h"
#include "Sound/SoundAttenuation.h"
#include "Subsystems/WorldSubsystem.h"
#include "MIAudioSubsystem.generated.h"

class AHUD;
class UAudioComponent;
class UCanvas;
class UReverbEffect;
class USoundEffectSubmixPreset;
class USoundWave;

/**
 * The game's sound in a world: binds FMIAudioDirector to the world's event bus, turns its commands into audio
 * components (assets /Game/Audio/... imported by tools/box/audio-import.sh), applies the mix every frame (category
 * gains, the muffle and pause low-passes), builds the attenuation (spec 07 distance model, air absorption, the
 * engine's occlusion trace, the reverb send), switches the engine reverb by zone (street, under the El, the shop)
 * and draws the voice subtitle on the HUD. docs/unreal/AUDIO.md section 4.
 */
UCLASS()
class MURDERINC_API UMIAudioSubsystem : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;
	virtual bool IsTickableWhenPaused() const override { return true; }

	static UMIAudioSubsystem* Get(const UObject* WorldContextObject);

	/** The options screen's hooks: master, effects, ambience, music, UI and the voice options. */
	void SetOptions(const FMIAudioOptions& Options) { Director.SetOptions(Options); }
	const FMIAudioOptions& GetOptions() const { return Director.GetOptions(); }
	/** The crew member whose voice set speaks (voice.json characters). */
	void SetCharacter(FName Character) { Director.SetCharacter(Character); }
	/** The loadout's silencer on a gun. */
	void SetSuppressed(FName Weapon, bool bOn) { Director.SetSuppressed(Weapon, bOn); }
	void SetNight(bool bOn) { Director.SetNight(bOn); }

	FMIAudioDirector& GetDirector() { return Director; }
	bool IsReady() const { return bReady; }
	int32 LiveComponents() const { return Components.Num(); }

	/** Start or stop recording the bus to a file under Saved/Audio (console: MIAudio.Record start|stop [name]). */
	void StartRecording();
	bool StopRecording(const FString& Name, FString& OutPath);

private:
	struct FPlaying
	{
		TWeakObjectPtr<UAudioComponent> Component;
		FName Category;
		double Volume = 1.0;
	};

	USoundWave* Wave(const FString& File);
	const FSoundAttenuationSettings& Attenuation(FName Category, double Ref, double Roll);
	void Execute(const FMIAudioCmd& C);
	void ApplyMix();
	void ApplyReverb();
	void Observe();
	void DrawSubtitle(AHUD* HUD, UCanvas* Canvas);

	FMIAudioData Data;
	FMIVoiceData Voice;
	FMIAudioDirector Director;
	FMIAudioEventLog Log;
	bool bReady = false;
	bool bBound = false;
	bool bRecording = false;
	double RecordClock = 0.0;
	double ObserveTimer = 0.0;
	int32 ChainRefreshes = 0;

	TMap<int32, FPlaying> Components;
	TMap<FString, TWeakObjectPtr<USoundWave>> Waves;
	TMap<FString, bool> ExistsCache;
	TMap<FString, FSoundAttenuationSettings> Attenuations;
	TSet<FString> Warned;
	FName ActiveReverb;
	FDelegateHandle HudHandle;

	UPROPERTY(Transient)
	TArray<TObjectPtr<USoundWave>> Loaded;

	UPROPERTY(Transient)
	TMap<FName, TObjectPtr<UReverbEffect>> Reverbs;

	/** The master chain on the device's master submix (FMIMasterChain); empty when not installed. */
	UPROPERTY(Transient)
	TArray<TObjectPtr<USoundEffectSubmixPreset>> MasterChain;
};
