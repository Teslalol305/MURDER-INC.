#pragma once

#include "CoreMinimal.h"

/**
 * The encoder's quantiser as the game gives it to Pixel Streaming (release 3c). Pure logic: UMICloudSubsystem reads the
 * numbers (launch options, a viewer's console commands) and sets the plugin's variables.
 *
 * The problem. E3DS's "Video Quality" is not a bitrate but a constant quantiser: Medium starts the game with
 * -PixelStreamingEncoderMinQP=34 -PixelStreamingEncoderMaxQP=34, High with 16 and 16, and its page sends the same two
 * numbers as console commands (PixelStreaming.Encoder.MinQP 34, PixelStreaming.Encoder.MaxQP 34) at the start of every
 * session (measured: docs/unreal/DECISIONS.md, 2026-11-25). With the minimum equal to the maximum the encoder cannot
 * trade quality for bits: at QP 16 a fast turn needs up to 14.5 Mbit/s whatever the connection carries, the extra bits
 * queue in the sender, and the picture of a thin connection stalls.
 *
 * What the game does about it. The two numbers are taken as the CENTRE of a range: the lowest QP the encoder may use is
 * the first number minus MI.Cloud.QpBelow (10; never under 8), the highest is the second plus MI.Cloud.QpAbove (8; never
 * over 48). Medium (34) gives 24 to 42, High (16) gives 8 to 24. The encoder's rate control then picks, frame by frame,
 * the quality the connection carries (the sender's congestion control gives it a bitrate; Pixel Streaming runs the
 * encoder in constant bit rate mode, which holds the QP inside the range). -MIQpExact turns the range off.
 *
 * How Pixel Streaming 2 of Unreal 5.9 takes the numbers (read in its source, Engine/Plugins/Media/PixelStreaming2):
 *  - the launch options -PixelStreamingEncoderMinQP= and -PixelStreamingEncoderMaxQP= are turned into the plugin's
 *    quality variables PixelStreaming2.Encoder.MaxQuality and MinQuality when it starts (a LOW QP is a HIGH quality):
 *    quality = 100 * (1 - QP / 51), cut to an integer;
 *  - the encoder (NVENC, AVCodecs) turns them back: QP = (1 - quality / 100) * 51, cut to an integer, and with the
 *    rate control in CBR mode holds the QP inside [minQP, maxQP];
 *  - a viewer's console command "PixelStreaming.Encoder.MinQP 34" matches no console variable or command of the plugin
 *    (it registers PixelStreaming2.* only): it does nothing by itself. The plugin's own "Encoder.MinQP" message (a
 *    Command message, not a console command) does set the quality, rounded.
 */
struct MURDERINC_API FMIEncoderRange
{
	static constexpr int32 TopQp = 51;

	/** The quality (0 to 100) whose QP the encoder works out as exactly Qp. */
	static int32 QualityForQp(int32 Qp);
	/** What the encoder makes of a quality: the arithmetic of its configuration (float, cut). */
	static int32 QpForQuality(int32 Quality);

	struct FSettings
	{
		/** The lowest QP is the first number minus this. */
		int32 Below = 10;
		/** The highest QP is the second number plus this. */
		int32 Above = 8;
		/** The lowest QP the range reaches down to (a request below it is kept as it is). */
		int32 Floor = 8;
		/** The highest QP the range reaches up to (a request above it is kept as it is). */
		int32 Ceiling = 48;
		/** -MIQpExact: no range, the numbers as they come. */
		bool bExact = false;
	};

	struct FRange
	{
		int32 MinQp = 0, MaxQp = TopQp;
		bool operator==(const FRange& O) const { return MinQp == O.MinQp && MaxQp == O.MaxQp; }
	};

	/** The range around the numbers a page or a launch option gives (the lowest QP it wants, the highest it accepts). */
	static FRange Widen(int32 WantedMin, int32 WantedMax, const FSettings& Settings);

	enum class ECommand : uint8
	{
		None,
		MinQp,
		MaxQp,
	};
	/**
	 * A viewer's console command that sets the encoder's lowest or highest QP: "PixelStreaming.Encoder.MinQP 34",
	 * "PixelStreaming.Encoder.MaxQP=34" and the same under PixelStreaming2 (any case). OutQp is the number, 0 to 51.
	 */
	static ECommand ParseCommand(const FString& Command, int32& OutQp);

	/**
	 * The two launch options on a command line, as Pixel Streaming reads them (the first of each; E3DS puts a second
	 * -PixelStreamingEncoderMaxQP at the end of its list, which counts for nothing). -1: not given.
	 */
	static void ReadLaunchOptions(const TCHAR* CommandLine, int32& OutMinQp, int32& OutMaxQp);
};

/**
 * The round trip of the stream as the sender reports it. Pixel Streaming sends a statistic only when its value
 * changes, under one name for the video track and the audio track, and an unmeasured round trip is a plain 0: so
 * "nothing arrived for 5 s" means "steady", not "unknown" (a steady link is the one most likely to be quiet), and a
 * 0 means "not measured yet", never "no delay". This keeps the last few measured values (above zero, under a minute),
 * answers with their median, and forgets them when the viewers change (the next viewer is another connection).
 */
struct MURDERINC_API FMIRoundTrip
{
	static constexpr int32 Kept = 5;

	void Reset();
	/** One report, in seconds. Not finite, 0, negative or over a minute: not a measurement, ignored (and counted). */
	void Add(double Seconds, double Now);

	bool IsKnown() const { return Count > 0; }
	/** The median of the kept values, in ms (0 when none is known). */
	double Ms() const;
	/** Seconds since the newest value arrived (a large number when none did). */
	double AgeSeconds(double Now) const;
	/** Measured values and ignored reports since the last Reset (for the probe line). */
	int32 GetAccepted() const { return Accepted; }
	int32 GetIgnored() const { return Ignored; }

private:
	float Values[Kept] = {};
	int32 Count = 0, Next = 0, Accepted = 0, Ignored = 0;
	double Newest = -1e9;
};
