#pragma once

#include "CoreMinimal.h"
#include "Audio/MIAudioData.h"
#include "Audio/MIVoiceRules.h"
#include "Audio/MIVoiceTriggers.h"
#include "Math/RandomStream.h"

struct FMIGameEvents;
struct FMIShotFiredEvent;
struct FMIReloadEvent;
struct FMISwitchEvent;
struct FMIImpactEvent;
struct FMIHitEnemyEvent;
struct FMIExplosionEvent;
struct FMIPlayerStepEvent;
struct FMIPlayerLandEvent;
struct FMIPlayerHitEvent;
struct FMIEnemyEvent;
struct FMIFlowEvent;

/**
 * The sound of the game as decisions: the event bus in, play / set / stop commands and a mix state out
 * (docs/unreal/AUDIO.md section 3). Plain C++ with a seeded random stream: the engine host (UMIAudioSubsystem) turns
 * the commands into audio components, the offline mixer (FMIOfflineMix) into a WAV file, and the tests read them.
 * Positions are Unreal units (cm); the enemy and flow payloads (web units) are converted here.
 */

enum class EMIAudioCmd : uint8
{
	Start,
	Set,
	Stop
};

struct FMIAudioCmd
{
	EMIAudioCmd Type = EMIAudioCmd::Start;
	int32 Id = 0;
	double Time = 0.0;      // director clock, seconds
	FName Sound;            // the definition this voice belongs to
	FString File;           // relative to Content/Audio/
	FName Category;
	double Volume = 1.0;    // before the category gain of the mix
	double Pitch = 1.0;
	bool b3D = false;
	FVector Pos = FVector::ZeroVector;   // cm
	double Ref = 300.0;     // cm
	double Roll = 1.0;
	bool bLoop = false;
	int32 Priority = 5;     // the sound's own priority (audio_sounds.json prio, 1 to 10)
	/**
	 * What the engine ranks this voice by when it has more of them than channels (it keeps the highest loudness x this):
	 * Priority times the category's scale (audio.json categories.<c>.priority), 0 to 100. The player's guns, with or
	 * without a silencer, carry the highest; a footstep the lowest.
	 */
	double VoicePriority = 5.0;
	bool bAlwaysPlay = false;   // keeps its voice whatever it competes with and however quiet it is (the player's guns)
	bool bKeepVoice = false;    // a loop that keeps its voice and its place in time at no volume (the music's stems, the beds)
	double Secs = 0.0;      // the file's length (as data says)
	double Fade = 0.0;      // Stop: fade-out seconds
	FString Subtitle;       // voice lines
	FString Speaker;
};

struct FMIAudioOptions
{
	double Master = 0.8;
	double Effects = 1.0;
	double Ambience = 1.0;
	double Music = 1.0;
	double UI = 1.0;
	FMIVoiceOptions Voice;
};

/** The mix this frame: what the host applies to every live voice. */
struct FMIMixState
{
	TMap<FName, double> Gain;        // category -> linear gain (bus, option, master, ducks, states)
	double MuffleCutoff = 20000.0;   // Hz, on the muffled categories
	double MusicCutoff = 20000.0;
	double AmbienceCutoff = 20000.0; // Hz, the ambience low-pass by interior: 20000 * 0.08^i (spec 07 3.19)
	double Interior = 0.0;           // 0 street .. 1 inside
	FName Reverb;                    // the reverb preset of the strongest zone
	double Muffle = 0.0;
	double VoiceDuck = 1.0;
	bool bPaused = false;
};

struct FMISubtitle
{
	FString Speaker;
	FString Text;
	double Until = -1.0;
	bool bPlaceholder = true;
};

class MURDERINC_API FMIAudioDirector
{
public:
	/** Does a file exist (asset or WAV)? Missing replacement layers are skipped; missing web files stay silent. */
	TFunction<bool(const FString& File)> Exists;
	/** Seconds of a file (the host asks its assets; default: the data's numbers, or 1.5 s). */
	TFunction<double(const FString& File)> FileSecs;
	/** Does the world block the line (near-miss whizz)? Default: never. */
	TFunction<bool(const FVector& From, const FVector& To)> Blocked;

	bool Init(const FMIAudioData* InData, const FMIVoiceData* InVoice, int32 Seed = 7);
	void Bind(FMIGameEvents& Bus);
	void Unbind();

	void SetOptions(const FMIAudioOptions& InOptions);
	const FMIAudioOptions& GetOptions() const { return Options; }
	void SetCharacter(FName Character) { Voice.SetCharacter(Character); }
	/** The loadout's silencer: the gun's shots use <weapon>_shot_silenced (LOADOUT.md 6.6). */
	void SetSuppressed(FName Weapon, bool bOn);
	void SetNight(bool bOn) { bNight = bOn; }

	// What the host observes each frame (public state only).
	void SetListener(const FVector& Pos, const FVector& Forward);
	void SetPlayer(double HealthFraction, bool bAlive);
	void SetEnemy(int32 Id, bool bBuzzard, const FVector& Pos, bool bAlive);

	/** Advance the clock (real seconds; the world's pause is read from the flow state). */
	void Tick(double Dt);
	void TakeCommands(TArray<FMIAudioCmd>& Out);
	const FMIMixState& GetMix() const { return Mix; }
	const FMISubtitle& GetSubtitle() const { return Subtitle; }
	double Now() const { return Clock; }
	const FVector& GetListener() const { return Listener; }
	const FVector& GetListenerForward() const { return ListenerForward; }
	FMIVoiceRules& GetVoice() { return Voice; }
	FMIVoiceTriggers& GetTriggers() { return Triggers; }

	// The bus (public so a replay can call them in order).
	void OnWeaponFire(const FMIShotFiredEvent& E);
	void OnWeaponDry(FName Weapon);
	void OnWeaponReload(const FMIReloadEvent& E);
	void OnWeaponSwitch(const FMISwitchEvent& E);
	void OnWeaponSwing(FName Weapon);
	/** The fire selector flipped (LOADOUT.md 4.4): a small mechanical click. */
	void OnWeaponMode(FName Weapon, bool bSemi);
	void OnWeaponMelee(bool bHit);
	void OnImpact(const FMIImpactEvent& E);
	void OnHitEnemy(const FMIHitEnemyEvent& E);
	void OnExplosion(const FMIExplosionEvent& E);
	void OnExplosiveLit(int32 Index, const FVector& Pos, double Fuse);
	void OnExplosiveBlast(int32 Index, const FVector& Centre);
	void OnPlayerStep(const FMIPlayerStepEvent& E);
	void OnPlayerJump();
	void OnPlayerLand(const FMIPlayerLandEvent& E);
	void OnPlayerHit(const FMIPlayerHitEvent& E);
	void OnPlayerDead(const TOptional<FVector>& From);
	void OnEnemy(const FMIEnemyEvent& E);
	void OnFlow(const FMIFlowEvent& E);
	void OnMusicIntensity(double Intensity);

	/** Every event key the bus can produce (the coverage test of the event table). */
	static TArray<FName> BusEventKeys();
	/**
	 * Every FMIGameEvents delegate the director listens to, with the event keys it maps to (key patterns: a '*' is
	 * any variant). The coverage test reads Core/MIEvents.h and fails on a delegate missing here, so a new bus event
	 * (the loadout's silencer, an attachment) cannot stay silent by accident.
	 */
	static TArray<TPair<FName, FString>> BusDelegates();
	/** The key one event maps to. */
	static FName EnemyKey(const FMIEnemyEvent& E);

	// Counters for tests.
	int32 Started() const { return StartedCount; }
	int32 Refused() const { return RefusedCount; }
	/** Sound ids something asked to play that the data does not have, since the last call (the host warns once each). */
	TArray<FName> TakeUnknown();
	/** All of them since Init. */
	const TSet<FName>& Unknown() const { return UnknownEver; }
	/**
	 * The gun whose sounds a gun fires with: its own when the data has <gun>_shot, else the one audio.json weaponSounds
	 * names (the web game has two guns, the loadout six: a rifle without recorded material sounds as the CHOPPER).
	 */
	FName SoundFamily(FName Weapon) const;

private:
	struct FInstance
	{
		TArray<int32> Ids;
		TArray<double> Base;
	};
	struct FLive
	{
		FName Sound;
		double Start = 0.0;
		double End = 0.0;
		int32 Priority = 5;
		FName Category;
		int32 PlayId = 0;   // the Play() this voice belongs to: a play is the web sound and its replacement layers together
	};
	struct FDuck
	{
		double Depth = 1.0;
		double Until = 0.0;
		double Release = 0.1;
		bool bMusic = false;
	};
	struct FPlayArgs
	{
		double Volume = 1.0;
		double Pitch = 1.0;
		double Delay = 0.0;
		bool b3D = false;
		FVector Pos = FVector::ZeroVector;
		bool bLoop = false;
		bool bNoJitter = false;
		/** A category and a distance law of this play's own, where the sound's are not what the web game plays it with (a Goon's step: the world bus, 3 m, 1.2). */
		FName Category;
		double Ref = -1.0;     // metres; <= 0: the sound's own
		double Roll = -1.0;
		int32 Priority = 0;    // <= 0: the sound's own
	};

	TSet<FName> UnknownEver;
	TArray<FName> UnknownNew;

	FInstance Play(FName Sound, const FPlayArgs& Args);
	int32 StartFile(const FMISoundDef& Def, const FString& File, double Secs, double Volume, const FPlayArgs& Args, double Pitch);
	void SetInstance(const FInstance& I, double Volume, double Delay = 0.0, double Pitch = -1.0, const FVector* Pos = nullptr);
	void StopInstance(const FInstance& I, double Fade, double Delay = 0.0);
	void PlayEntry(const TSharedPtr<FJsonObject>& Entry, FName Variant, const FVector* At, const TMap<FString, FString>& Vars);
	FString Fill(const FString& Pattern, const TMap<FString, FString>& Vars) const;
	void Duck(const TCHAR* Name, FName Weapon = NAME_None);
	void MuffleTo(double M, double Floor = -1.0);
	void Meter(double Add, double AtLeast = 0.0);
	TSharedPtr<FJsonObject> Surface(FName Name) const;
	FVector Web(const FVector& W) const;
	double InteriorAt(const FVector& Pos) const;
	void UpdateMix(double Dt);
	void UpdateLoops(double Dt);
	void UpdateMusic(double Dt);
	void UpdateAmbience(double Dt);
	void StartBeds();
	void Queue(const FMIAudioCmd& C);
	void StopAllLoops(bool bMusicToo);

	const FMIAudioData* Data = nullptr;
	const FMIVoiceData* VoiceData = nullptr;
	FMIAudioOptions Options;
	FRandomStream Rng;
	FMIVoiceRules Voice;
	FMIVoiceTriggers Triggers;
	TArray<FDelegateHandle> Handles;
	FMIGameEvents* BoundBus = nullptr;

	double Clock = 0.0;
	double GameClock = 0.0;   // stops while paused (the voice and the ambience schedule run on it)
	int32 NextId = 1;
	int32 NextPlayId = 1;
	int32 CurrentPlayId = 0;  // set while Play() starts the voices of one play
	TArray<FMIAudioCmd> Pending;  // scheduled for later
	TArray<FMIAudioCmd> Ready;
	TMap<int32, FLive> Live;
	TMap<FName, double> LastStartOf;
	TMap<FName, int32> NextVariant;
	TMap<FString, int32> LastLayerFile;
	double LastImpact = -1e9;
	int32 StartedCount = 0;
	int32 RefusedCount = 0;

	FVector Listener = FVector::ZeroVector;
	FVector ListenerForward = FVector::ForwardVector;
	double Health = 1.0;
	bool bAlive = true;
	bool bNight = false;
	TSet<FName> Suppressed;
	FName State;

	// Gun tails (spec 07 3.20).
	double LastShot = -1e9;
	FInstance TailOut, TailIn;
	double TailK = 1.0;
	int32 ShotSerial = 0;
	FName PlayerSurface = TEXT("asphalt");
	struct FRaise
	{
		int32 Serial = 0;
		double At = 0.0;
		FInstance TailOut, TailIn;
	double TailK = 1.0;
		double Out = 0.0, In = 0.0;
	};
	TArray<FRaise> Raises;

	// Mix state (spec 07 3.19).
	TArray<FDuck> Ducks;
	double AmbDuck = 1.0, MusDuck = 1.0;
	double MusicDip = 1.0;
	double Muffle = 0.0, MuffleFloor = 0.0;
	double Interior = 0.0;
	double AmbState = 0.6, AmbStateNow = 0.6;
	double VoiceAmt = 0.0;
	double DuckRelease = 0.1;
	double LowHealthK = 0.0;
	FMIMixState Mix;
	FMISubtitle Subtitle;
	FInstance VoiceLine;

	// Loops.
	struct FTracked
	{
		FInstance Loop;
		FVector Pos = FVector::ZeroVector;
		bool bBuzzard = false;
		bool bAlive = true;
		double Tune = 1.0;
		double Stride = 0.0;
		FVector LastPos = FVector::ZeroVector;
		bool bAudible = false;
		bool bHasPos = false;
	};
	TMap<int32, FTracked> Enemies;
	double RankTimer = 0.0;
	TMap<int32, FInstance> Fuses;
	TMap<int32, double> FuseStart, FuseLength;
	FInstance Grab;
	double GrabSeen = -1e9;
	FInstance Heartbeat;
	TArray<TPair<int32, double>> PendingGrunts;  // enemy id, time
	TSet<int32> KilledNow;

	// Music (spec 07 3.24, without the riser).
	TArray<FInstance> Stems;
	bool bStemsStarted = false;
	double MusicTarget = 0.15, MusicMeter = 0.15, MusicI = 0.15;
	FName MusicMode = TEXT("title");
	TArray<double> StemGain;
	double StemBus = 1.0, StemBusTarget = 1.0, StemBusUntil = 0.0;

	// Ambience.
	bool bBedsStarted = false;
	FInstance BedDay, BedNight, Wind;
	double DayMix = 1.0, Gust = 0.5, GustTarget = 0.5, GustTimer = 0.0;
	TMap<FName, double> FarTimers;
	double TrainTimer = 20.0, TrainT = -1.0;
	int32 TrainTrack = 0;
	FInstance TrainRumble, TrainClack;
	bool bSquealDone = false;
	double SquealAt = -1.0;
	double TrainDuck = 1.0;
};
