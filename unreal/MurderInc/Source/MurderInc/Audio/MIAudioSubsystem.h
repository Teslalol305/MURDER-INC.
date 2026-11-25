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

	/**
	 * Counts since the process started, for the stream's probe line (Cloud/MICloud.cpp: a Shipping game has no log):
	 * sounds started on the audio device; sound files or ids the game asked for that have no asset (each counted
	 * once, each logged once as a warning); starts the engine gave no audio component for (no audio device).
	 */
	struct FCounts
	{
		int32 Played = 0;
		int32 Missing = 0;
		int32 NoDevice = 0;
	};
	static FCounts GetCounts();
	/** A sound the game asked for cannot be heard (no asset, or an id the data does not have): once per sound. */
	static void NoteMissing(const FString& What, const FString& Why);

	/**
	 * How the engine ranks and keeps the voice a Start command makes: its priority (past its channel limit the engine
	 * keeps the highest loudness x priority), always-play for the player's guns and for the loops that keep time,
	 * play-when-silent for those loops. Static and device-free, so a test can check a component and a wave it makes up
	 * itself (MurderInc.Audio.VoicePolicy).
	 */
	static void ApplyVoicePolicy(UAudioComponent& Component, USoundWave& Wave, const FMIAudioCmd& C);

	/**
	 * The audio device's clock against the wall clock since this was last called: seconds of sound rendered per second
	 * that went by. The dummy device a server gives the game (no sound card) waits whole milliseconds for every buffer
	 * of 21.33 ms: a little fast on a free machine, slower when the machine is busy, and below 1.0 the stream's sound
	 * has holes. Negative when there is no device or this is the first call. The stream's probe line carries it
	 * (sndPace, and sndClock with sndWall: the clock and the wall clock themselves, so a longer stretch can be worked out
	 * from two lines), so the log of one E3DS session says which side that machine is on. The clock moves in steps of one buffer (21.33 ms): over a
	 * second the pace is good to 2 %, over half a minute to 0.1 %.
	 */
	static double TakeDevicePace(double* OutClock = nullptr, double* OutWall = nullptr);

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
	/**
	 * Every Sound Wave the data can ask for, loaded and its compressed audio kept in memory before anything plays.
	 * Unreal loads a wave's audio from the pak the first time it plays: measured through a stream, the first round of
	 * each gun sample reached the viewer 140 to 150 ms after the game started it, every later one after 27 to 50 ms.
	 * The web game decodes every sound when it loads. Only with an audio device (never in the tests' worlds).
	 */
	void Preload();
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
