#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "MISettings.generated.h"

/** One gun's build in the save: slot -> part (LOADOUT.md 7). */
USTRUCT()
struct FMIGunBuildSave
{
	GENERATED_BODY()
	UPROPERTY() TMap<FName, FName> Parts;
};

/** The remembered set-up (LOADOUT.md 7, frontend.json save). Mode, difficulty and time stay the settings keys. */
USTRUCT()
struct FMISetupSave
{
	GENERATED_BODY()
	UPROPERTY() int32 Version = 1;
	UPROPERTY() FName Crew;
	UPROPERTY() TArray<FName> Guns;                   // up to 4, slot order
	UPROPERTY() TMap<FName, FMIGunBuildSave> Builds;  // every gun ever built
	UPROPERTY() FName Level;
	UPROPERTY() TArray<FName> Seen;                   // ids looked at (the NEW badges)
	UPROPERTY() bool bPlayed = false;                 // false: Hit the block on Home opens Crew
};

/** The stored record: one save-game slot holds the settings, the best Hold the Block score (spec 04 2.16) and the
 *  remembered set-up (LOADOUT.md 7). */
UCLASS()
class MURDERINC_API UMISaveGame : public USaveGame
{
	GENERATED_BODY()

public:
	UPROPERTY() int32 Version = 1;
	UPROPERTY() FString Mode;
	UPROPERTY() FString Difficulty;
	UPROPERTY() FString Time;
	UPROPERTY() FString Quality;
	UPROPERTY() double Sens = 1.0;
	UPROPERTY() bool bInvertY = false;
	UPROPERTY() bool bPadPlayStation = false;
	/** Story guidance: the ground path and the objective markers (docs/unreal/PLAY.md, guide lane). On by default. */
	UPROPERTY() bool bGuide = true;
	/** Aim assist (DECISIONS.md 2026-11-27 ~22:20): on by default; the strength is a data id (low, normal, high). */
	UPROPERTY() bool bAimAssist = true;
	UPROPERTY() FString AimAssistStrength = TEXT("normal");
	UPROPERTY() double Volume = 0.8;
	UPROPERTY() double Fov = 74.0;               // the old vertical field (v5 and earlier saves): not read any more
	/** The field of view the Settings slider shows: horizontal degrees at 16:9 (the owner, DECISIONS.md 2026-11-26: default 90). */
	UPROPERTY() double FovWide = 90.0;
	UPROPERTY() int32 View = 1;
	UPROPERTY() int32 Best = 0;
	UPROPERTY() FMISetupSave Setup;
};

/**
 * src/core/settings.js: the user's settings with the web game's validation. Defaults from config.json
 * settings.defaults, accepted values and ranges from rules.json settings. Every setter validates on its own and
 * returns true only when the stored value changed (an unusable value changes nothing).
 */
struct MURDERINC_API FMISettings
{
	FName Mode, Difficulty, Time, Quality;
	/** Fov is HORIZONTAL degrees at 16:9 (default 90); the rules take its vertical equivalent (VerticalFov). */
	double Sens = 1.0, Volume = 0.8, Fov = 90.0;
	bool bInvertY = false;
	/**
	 * What a controller's buttons are called on screen: Xbox names (the web game's), or the PlayStation names for the
	 * same buttons. The Unreal build's own setting: a streamed game cannot tell which pad the player holds.
	 */
	bool bPadPlayStation = false;
	/** The Unreal build's own setting: the story's ground path and objective markers (on by default). */
	bool bGuide = true;
	/** The Unreal build's own settings: the aim assist (docs/unreal/DECISIONS.md 2026-11-27 ~22:20), on by default, and how strong. */
	bool bAimAssist = true;
	FName AimAssistStrength = TEXT("normal");
	int32 View = 1;
	int32 Best = 0;       // stored best
	int32 SessionBest = 0;

	struct FRules
	{
		FString Slot = TEXT("murderinc.settings.v1");
		double SensMin = 0.2, SensMax = 3.0, SensStep = 0.05, FovMin = 70, FovMax = 120, FovStep = 1, VolumeMin = 0, VolumeMax = 1, VolumeStep = 0.01;
		/** A pad press steps further than a key (POLISH.md 4; the stream drops a held pad button's repeats), and a held Left/Right repeats. */
		double PadSensStep = 0.1, PadFovStep = 5, PadVolumeStep = 0.05;
		double RepeatAfter = 0.38, RepeatEvery = 0.17, FastAfter = 1.2, FastMult = 5;
		int32 ViewMin = 1, ViewMax = 3;
		TArray<FName> Qualities, Modes, Difficulties, Times;
		TArray<FName> AssistStrengths;  // config.json player.input.assist.strengths, in cycling order
	} Rules;

	/** Defaults (config.json) and the validation table (rules.json). */
	static bool LoadDefaults(FMISettings& Out, FString& OutError);

	bool SetMode(FName V) { return SetName(Mode, V, Rules.Modes); }
	bool SetDifficulty(FName V) { return SetName(Difficulty, V, Rules.Difficulties); }
	bool SetTime(FName V) { return SetName(Time, V, Rules.Times); }
	bool SetQuality(FName V) { return SetName(Quality, V, Rules.Qualities); }
	bool SetSens(double V);
	bool SetVolume(double V);
	/** Clamped and rounded to a whole degree (horizontal field of view at 16:9). */
	bool SetFov(double V);
	/** The vertical field the rules use for a horizontal one at 16:9 (90 gives 58.7). */
	static double VerticalFromWide(double WideDegrees);
	double VerticalFov() const { return VerticalFromWide(Fov); }
	bool SetView(int32 V);
	bool SetInvertY(bool V);
	bool SetPadPlayStation(bool V);
	bool SetGuide(bool V);
	bool SetAimAssist(bool V);
	/** One of Rules.AssistStrengths; anything else changes nothing. */
	bool SetAimAssistStrength(FName V) { return SetName(AimAssistStrength, V, Rules.AssistStrengths); }
	/** Cycles a named setting through its accepted values. */
	static FName Next(FName Current, const TArray<FName>& Values, int32 Step);

	/** settings.best(): the larger of the stored value and this session's. */
	int32 GetBest() const { return FMath::Max(Best, SessionBest); }
	/** settings.setBest(n): rounds, stores only a new record, returns true for one. */
	bool SetBest(double Score);

	void ToSave(UMISaveGame& Save) const;
	/** Every field validated on its own; an unusable one keeps the default. */
	void FromSave(const UMISaveGame& Save);

private:
	static bool SetName(FName& Field, FName V, const TArray<FName>& Allowed);
};
