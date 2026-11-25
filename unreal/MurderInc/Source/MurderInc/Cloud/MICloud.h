#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Containers/Ticker.h"
#include "GenericPlatform/GenericApplicationMessageHandler.h"
#include "InputCoreTypes.h"
#include "Cloud/MIPacing.h"
#include "Player/MILookInput.h"
#include "MICloud.generated.h"

class SMICloudOverlay;
class FMICloudInput;

/**
 * Who is watching the stream, as far as the click card needs it: the card shows for the first viewer and again for
 * the first one after everybody has left (the game paused meanwhile), never for a guest who joins a session that is
 * being played (E3DS's Share button hands out a link to the running session).
 */
struct MURDERINC_API FMICloudViewers
{
	/** Joins since the stream was last empty. */
	int32 Count = 0;

	/** A viewer joined. True: nobody was watching, the click card shows. */
	bool Join() { return Count++ == 0; }
	/** The last viewer left. */
	void AllLeft() { Count = 0; }
};

/**
 * The game played in a browser through Pixel Streaming 2 (docs/LAUNCH.md, tools/box/cloud/).
 *
 * Streamed means: the command line carries a Pixel Streaming connection (-PixelStreamingURL=,
 * -PixelStreamingConnectionURL=), or -MICloud, or the Pixel Streaming 2 plugin reports a signalling connection.
 * Then, and only then:
 *  - the 'Cloud' scalability profile is applied: every +CVars= line of [MICloud] in DefaultGame.ini, set with
 *    device-profile priority so the scalability groups of the settings menu cannot undo it (budgets for an 8 GB
 *    card at 1080p 60: texture pool, Lumen, virtual shadow map and Nanite pools);
 *  - a "click to play" card covers the screen until the first click, key or gamepad button (the browser needs that
 *    click to lock the pointer for mouse look and to start the sound); the click is eaten so it presses nothing;
 *  - the second pause key is shown (the browser keeps Esc to free the pointer: P pauses);
 *  - a software cursor is drawn wherever the game shows the mouse (menus): the stream carries no OS cursor;
 *  - when the last viewer disconnects, a running game pauses; the next viewer gets the click card again, a guest
 *    who joins a session in progress does not (FMICloudViewers);
 *  - mouse look takes the stream's mouse events one by one and turns the counts back into the browser's pixels:
 *    [MICloud] MouseScale (0.5: Pixel Streaming sends 2 counts per browser pixel when the game renders at the size the
 *    player shows it; launch option -MIMouseScale=<number> to tune it on the host without a rebuild), MouseTruncation
 *    (the count each event loses on the way) and the web game's pointer-lock spike filter (FMIStreamMouse,
 *    AMIPlayerController::StreamMouseEvent). On the desktop the mouse is untouched;
 *  - a viewer's console commands (the host passes -AllowPixelStreamingCommands) run only if they set one of the
 *    variables a visitor may tune (MITuning: the stream's own settings PixelStreaming2.* and PixelStreaming.*, the
 *    scalability groups, dynamic resolution, t.MaxFPS and a few more, some only within a range); anything else is
 *    refused and the first refusal of a session is logged (IsViewerCommandAllowed). The browser's size requests are
 *    a separate Pixel Streaming command and still work;
 *  - Graphics quality on the Settings card changes the scalability groups only: not the output resolution, the frame
 *    cap or the cloud profile (ApplyStreamedQuality);
 *  - the game never runs ahead of the GPU and keeps it head-room (Cloud/MIPacing.h): dynamic resolution (the cloud
 *    profile turns it on), a frame-rate target of 60, 45 or 30 that t.MaxFPS, the stream's frame rate and dynamic
 *    resolution's frame time follow (launch option -MIFps=60|45|30 or MI.Cloud.FpsTarget fixes it; so does a t.MaxFPS
 *    set by hand), and a pacer that does not start a frame while the GPU still owes more than
 *    MI.Cloud.GpuFramesInFlight frames;
 *  - the launch option -MICVars=name=value,name=value sets console variables of the same list after the cloud
 *    profile, with command-line priority, each one printed in the log: tuning on the host without a new build;
 *  - the pause card carries one small line of the game's own numbers (GPU, frame rate and target, GPU time, the
 *    picture's drawn and sent size, the stream as its sender measures it, the build), and one "MICloudProbe" line is
 *    logged every 30 s (-MICloudProbe=<seconds> changes the period, 0 turns it off).
 *
 * At start (every run, streamed or not): one block of lines with the build (BUILD.txt at the package root), the GPU,
 * driver, RHI, shader platform, ray tracing, Nanite, Lumen and video memory; if hardware ray tracing is missing,
 * software Lumen traces the meshes' distance fields. In Shipping (no engine log) every line is also printed to stdout,
 * which the launcher writes to MurderInc/Saved/Logs (tools/box/cloud/MurderInc.sh). On Linux game builds an exit guard
 * ends the process when main() returns, before the engine's codec registry crashes in its static destructor, and
 * reports a stop asked for by SIGINT/SIGTERM/SIGHUP as exit code 0. Not in the Shipping game: -MICrashTest=<seconds>
 * crashes on purpose, -MICloudLog=<file> copies every line to a file (a viewer can add launch options to a link).
 *
 * -MICloudProbe=<seconds> logs one "MICloudProbe" line per period (frame rate, worst frame, GPU time, the frame-rate
 * target, dynamic resolution's share, what the pacer did, the worst game, render and RHI thread times, the stream's
 * sender statistics, process memory, the GPU memory the RHI reports, the view's yaw and pitch, the game state, mouse
 * spikes dropped, the device in use) for the cloud budget measurements and the lag tests (tools/box/cloud/lag-test.sh).
 */
UCLASS()
class MURDERINC_API UMICloudSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	/** True when the command line says the game is streamed (see the class comment). */
	static bool IsStreamedByCommandLine();
	/**
	 * Sets every [MICloud] CVars line; returns how many were set. The StreamCVars lines (Pixel Streaming 2's own
	 * settings: the plugin is only in the game target) are set as well where the plugin is compiled in, and are not
	 * counted.
	 */
	static int32 ApplyCloudProfile();
	/**
	 * The launch option -MICVars=name=value,name=value on CommandLine: sets the variables MITuning allows, with
	 * command-line priority (above the cloud profile), and logs each one and each refusal. Returns how many were set.
	 */
	static int32 ApplyTuningOption(const TCHAR* CommandLine);

	/**
	 * The stream's mouse shape: [MICloud] MouseScale and MouseTruncation of DefaultGame.ini, the scale overridden by
	 * -MIMouseScale=<number> and the truncation by -MIMouseTruncation=<number> on CommandLine; Glitch is the caller's
	 * (config.json player.input.mouseGlitch). Values out of range fall back to the defaults (0.5 and 1).
	 */
	static FMIStreamMouse ReadMouseShape(const TCHAR* CommandLine, double Glitch);

	/**
	 * True for a viewer's console command that may run: it reads or sets one variable MITuning allows ("name",
	 * "name value" or "name=value"; see the class comment). OutCommand, when given, is the command to run: "name value".
	 */
	static bool IsViewerCommandAllowed(const FString& Command, FString* OutCommand = nullptr);

	/**
	 * Graphics quality from the Settings card while streamed. Level 0..3 (low .. ultra) sets the scalability groups
	 * (view distance, shadows, global illumination, reflections, post-processing, textures, effects, shading ...);
	 * below 0 (auto) puts back the levels the game started with. The render resolution, the output resolution, the
	 * frame cap and the cloud profile are left alone: UGameUserSettings::ApplySettings, which the desktop uses, asks
	 * for its own stored resolution and window mode, clears t.MaxFPS and sets r.ScreenPercentage with the level.
	 */
	static void ApplyStreamedQuality(int32 Level);

	bool IsStreamed() const { return bStreamed; }
	bool IsWaitingForClick() const { return bWaitingForClick; }
	/** The first click, key or button of a viewer: hides the card. */
	void Dismiss();
	const FMIStreamMouse& GetMouseShape() const { return MouseShape; }
	/** One mouse event on its way through Slate. True: a spike, the event goes no further. */
	bool OnMouseEvent(const FVector2D& Delta);

	/**
	 * A browser sends a held gamepad button again on every frame, marked as a repeat (Pixel Streaming's player reads
	 * the pad once a frame and sends every button that is down; a desktop pad repeats slowly or not at all). Passed
	 * on, one tap of A on a set-up screen acted six times, and the Start that began a run paused it at once, because
	 * the game sees a repeat of a key it never saw go down as a press. So in a stream a gamepad's repeats go nowhere.
	 */
	static bool IsStreamPadRepeat(const FKey& Key, bool bRepeat) { return bRepeat && Key.IsGamepadKey(); }
	/**
	 * A key press on its way through Slate. True: it goes no further (a gamepad button's repeat, or a second press of
	 * a gamepad button that never went up: a player page that does not mark its repeats).
	 */
	bool OnKeyDown(const FKey& Key, bool bRepeat);
	void OnKeyUp(const FKey& Key) { PadKeysDown.Remove(Key); }
	/** An axis on its way through Slate: the left stick is kept for the menus. */
	void OnAnalog(const FKey& Key, float Value, FPlatformUserId User, FInputDeviceId Device);
	/**
	 * Once a frame: while a card or a set-up screen is up, the left stick presses the keys a desktop pad's stick
	 * presses (Gamepad_LeftStick_Up and the like, which the cards and the set-up screens already answer to). Pixel
	 * Streaming hands over a stick's axes only, so through a stream the stick did nothing in a menu.
	 */
	void TickStickMenu(float DeltaTime);

	/** The frame-rate target now (60, 45 or 30). */
	int32 GetFrameRateTarget() const { return Governor.Target(); }
	/** The pause card's line of numbers (made once a second while streamed). */
	const FString& GetNumbersLine() const { return NumbersLine; }

private:
	void BecomeStreamed(const TCHAR* Why);
	bool Tick(float DeltaTime);
	void EnsureOverlay();
	void EnsureVideoProducer();
	/** Gives the player controller the stream's mouse shape (again after a map load made a new controller). */
	void EnsureMouse();
	/** Puts the allowlist in place of Pixel Streaming's console-command handler, once the streamer is there. */
	void GuardViewerCommands();
	void OnViewerCommand(const FString& Command);
	void OnViewerJoined();
	void OnAllViewersLeft();
	void Probe(float DeltaTime);
	/** The pacer, the frame-rate target and the default probe period, once, when the game becomes streamed. */
	void StartPacing();
	/** Once a frame while streamed: the GPU's time, twice a second the frame-rate target's decision. */
	void TickPacing();
	/** t.MaxFPS, the stream's frame rate and dynamic resolution's frame time for the target (cloud-profile priority). */
	void ApplyFrameRateTarget();
	void OnStreamStat(FString Player, FName Stat, float Value);
	/** A sender statistic of the stream by name (bPeak: its largest value of the last two seconds); Missing when none arrived in the last 5 s. */
	double StreamStat(const TCHAR* Name, double Missing = -1.0, bool bPeak = false) const;
	void MakeNumbersLine();

	bool bStreamed = false;
	bool bProfileApplied = false;
	bool bWaitingForClick = false;
	bool bConnectionLost = false;
	bool bVideoChecked = false;
	bool bCommandsGuarded = false;
	bool bRefusalLogged = false;
	int32 CommandsRun = 0, CommandsRefused = 0;
	FMICloudViewers Viewers;
	FMIStreamMouse MouseShape;
	FMIPadNav StickNav;
	FVector2D LeftStick = FVector2D::ZeroVector;
	FPlatformUserId StickUser = PLATFORMUSERID_NONE;
	FInputDeviceId StickDevice = INPUTDEVICEID_NONE;
	TArray<FName> StickKeysDown;  // pressed last frame, let go this frame
	TSet<FKey> PadKeysDown;       // the gamepad buttons that are down, as the stream reported them
	bool bMakingStickKeys = false, bPlatformStickKeys = false;
	int32 PadRepeatsDropped = 0, StickKeysMade = 0;
	FTSTicker::FDelegateHandle TickHandle;
	TSharedPtr<SMICloudOverlay> Overlay;
	TSharedPtr<FMICloudInput> Input;
	TWeakObjectPtr<class UGameViewportClient> OverlayViewport;

	double CrashTestAt = 0.0;
	float ProbePeriod = 0.f;
	bool bProbeGiven = false;
	double ProbeNext = 0.0;
	double ProbeFrames = 0.0, ProbeTime = 0.0, ProbeWorst = 0.0;
	double ProbeGameMs = 0.0, ProbeRenderMs = 0.0, ProbeRhiMs = 0.0;  // the worst of each thread in the window
	TArray<FDelegateHandle> StreamHandles;

	// Pacing (Cloud/MIPacing.h).
	TSharedPtr<FMIGpuPacer, ESPMode::ThreadSafe> Pacer;
	FMIFrameRateGovernor Governor;
	bool bPacingStarted = false;
	int32 PacerPausesLogged = 0;
	int32 PinnedBy = 0;                      // 0 not pinned, 1 MI.Cloud.FpsTarget / -MIFps, 2 t.MaxFPS set by hand
	double GovLast = 0.0, GovGpuSum = 0.0;   // since the governor's last step
	int32 GovFrames = 0;
	double LastGpuMs = 0.0, LastFps = 0.0;   // the last half second, for the pause card
	float PictureShare = -1.f;               // dynamic resolution's share of the output size (-1: off)
	double NumbersNext = 0.0;
	FString NumbersLine;
	// Peak: the largest value of the last two seconds (a viewer's audio and video report "bitrate" under one name,
	// in turn: the video's is the larger one).
	struct FStreamStat { float Value = 0.f, Peak = 0.f; double Time = 0.0, PeakTime = 0.0; };
	TMap<FName, FStreamStat> StreamStats;
};
