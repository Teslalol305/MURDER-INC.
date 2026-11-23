#pragma once

#include "CoreMinimal.h"
#include "Audio/MIAudioDirector.h"
#include "Audio/MIAudioMaster.h"

/** PCM WAV files: read 16/24/32-bit integer and 32-bit float, any rate, mono or stereo; write 16-bit. */
struct MURDERINC_API FMIWav
{
	int32 Rate = 48000;
	int32 Channels = 1;
	TArray<float> Samples;  // interleaved

	int32 Frames() const { return Channels > 0 ? Samples.Num() / Channels : 0; }
	double Secs() const { return Rate > 0 ? double(Frames()) / Rate : 0.0; }
	float Peak() const;
	/** RMS over the whole file, all channels. */
	double Rms() const;

	static bool Load(const FString& Path, FMIWav& Out, FString* OutError = nullptr);
	static bool Parse(const TArray<uint8>& Bytes, FMIWav& Out, FString* OutError = nullptr);
	bool Save16(const FString& Path) const;
};

/**
 * Renders what FMIAudioDirector decides into a stereo WAV without the engine's audio device: the director's commands
 * (start, set, stop at their times), its mix state (category gains, the muffle and pause filters), the spec's
 * distance model and air absorption, equal-power panning around the listener, a small reverb on the categories'
 * sends, and the master chain of spec 07 2.11 on the sum (compressor, x 1.15, soft clip: FMIMasterCompressor). A proof of the decisions and the mix, not of the engine's
 * spatialiser (docs/unreal/AUDIO.md section 7).
 */
class MURDERINC_API FMIOfflineMix
{
public:
	int32 Rate = 48000;
	/** Where the files are: Content/Audio by default. */
	FString Root;
	/** Files that could not be read, once each. */
	TSet<FString> Missing;

	void Begin(const FMIAudioData* InData, double Secs);
	/** Commands as the director gave them (in time order). */
	void Apply(const TArray<FMIAudioCmd>& Cmds);
	/** Render up to time T (director clock) with this mix and listener. */
	void RenderTo(double T, const FMIMixState& Mix, const FVector& Listener, const FVector& Forward);
	const TArray<float>& Output() const { return Out; }
	bool Save(const FString& Path) const;
	int32 VoicesStarted() const { return Started; }
	double PeakDb() const;
	/** The deepest gain reduction of the master compressor, dB (<= 0). */
	double MasterReductionDb() const { return Master.MaxReductionDb(); }

	/** The length of a file (reads and caches it); 0 when missing. */
	double FileSecs(const FString& File);

private:
	struct FVoice
	{
		const FMIWav* Wav = nullptr;
		FName Category;
		double Pos = 0.0;      // source frame
		double Step = 1.0;     // source frames per output frame
		double Pitch = 1.0;
		double Volume = 1.0;
		double Gain = 0.0;     // last applied (for ramps)
		bool b3D = false;
		FVector Where = FVector::ZeroVector;
		double Ref = 300.0, Roll = 1.0;
		bool bLoop = false;
		int64 StartFrame = 0;  // output frame where it begins
		int64 StopFrame = -1;
		double FadeFrames = 0.0;
		float LpL = 0.f, LpR = 0.f;
	};
	struct FTimed
	{
		FMIAudioCmd Cmd;
	};

	const FMIWav* Get(const FString& File);
	void Execute(const FMIAudioCmd& C);

	const FMIAudioData* Data = nullptr;
	TMap<FString, TSharedPtr<FMIWav>> Cache;
	TMap<int32, FVoice> Voices;
	TArray<FMIAudioCmd> Queue;
	TArray<float> Out;
	int64 Frame = 0;
	int32 Started = 0;
	FMIMasterCompressor Master;

	// A small Schroeder reverb (four combs, two all-passes per channel).
	struct FComb
	{
		TArray<float> Buf;
		int32 I = 0;
		float Store = 0.f;
	};
	FComb Combs[2][4];
	FComb Alls[2][2];
	bool bReverbReady = false;
	float RevLp[2] = {0.f, 0.f};
	void InitReverb();
	float Reverb(int32 Ch, float In, float Decay);
};
