#pragma once

#include "CoreMinimal.h"

struct FMIAudioData;
class USoundEffectSubmixPreset;

/**
 * The master chain of spec 07 2.11 / 4.5: SUM -> compressor (threshold -6 dB, knee 8 dB, 2.5 : 1, attack 6 ms,
 * release 140 ms) -> x 1.15 make-up -> soft clip (linear to 0.6, then 0.6 + 0.4 tanh). The numbers are audio.json
 * "master". The engine gets it as two Submix Effect Dynamics Processors on the master submix (a compressor with the
 * make-up as its output gain, then a soft-knee limiter whose knee starts at -4.4 dB, where the web curve leaves the
 * line); the offline mix runs the same compressor and the web game's exact curve (FMIMasterCompressor).
 * docs/unreal/AUDIO.md section 4.
 */
struct MURDERINC_API FMIMasterChain
{
	bool bEnabled = true;
	double ThresholdDb = -6.0;
	double KneeDb = 8.0;
	double Ratio = 2.5;
	double AttackMs = 6.0;
	double ReleaseMs = 140.0;
	double Makeup = 1.15;
	// The engine's stand-in for the soft clip.
	double ClipThresholdDb = -0.3;
	double ClipKneeDb = 8.2;
	double ClipAttackMs = 1.0;
	double ClipReleaseMs = 60.0;
	double ClipLookAheadMs = 3.0;

	/** audio.json "master" (spec values when the table or a key is missing). */
	static FMIMasterChain FromData(const FMIAudioData& Data);

	/**
	 * Put the chain on the master submix of the world's audio device (replacing its master effects). The presets
	 * are new transient objects: OutKeep must hold them for as long as the chain runs. False without a device.
	 */
	bool Install(UObject* WorldContext, TArray<TObjectPtr<USoundEffectSubmixPreset>>& OutKeep) const;
	static void Uninstall(UObject* WorldContext);
};

/** The chain sample by sample, stereo-linked (the offline mix and the tests). */
class MURDERINC_API FMIMasterCompressor
{
public:
	void Init(const FMIMasterChain& InChain, int32 Rate);
	/** One stereo frame through compressor, make-up and soft clip. */
	void Process(float& L, float& R);
	/** The static curve: gain reduction in dB (<= 0) for an input level in dBFS. */
	double CurveDb(double InDb) const;
	/** The deepest gain reduction so far, dB (<= 0). */
	double MaxReductionDb() const { return MaxReduction; }

	/** The web game's soft clip (spec 07 2.11). */
	static float SoftClip(float X);

private:
	FMIMasterChain Chain;
	double AttackK = 0.0, ReleaseK = 0.0;
	double Env = 0.0;  // smoothed gain reduction, dB
	double MaxReduction = 0.0;
};
