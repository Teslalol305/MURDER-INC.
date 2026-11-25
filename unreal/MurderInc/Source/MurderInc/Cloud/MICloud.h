#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Containers/Ticker.h"
#include "GenericPlatform/GenericApplicationMessageHandler.h"
#include "InputCoreTypes.h"
#include "Cloud/MIPacing.h"
#include "Cloud/MISession.h"
#include "Cloud/MIStreamQuality.h"
#include "Player/MILookInput.h"
#include "MICloud.generated.h"

class SMICloudOverlay;
class FMICloudInput;
class AMIPlayerController;
class UMIGameSubsystem;

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
 * A gamepad's buttons as a stream reports them. A browser's player page reads the pad once a frame and sends every
 * button that is down again, marked as a repeat (a desktop pad repeats slowly or not at all). Passed on, one tap of A
 * on a set-up screen acted six times, and the Start that began a run paused it at once. So of one hold only the first
 * message goes on, whether the page marks it as a press or as a repeat: a browser shows a pad to a page only once one
 * of its buttons is pressed, the page then takes that button for held already, and its first message for it is a
 * repeat (no press is ever sent for the first press of a session: Epic's GamepadController.ts, onGamepadConnected).
 */
struct MURDERINC_API FMIPadButtons
{
	/** A button-down message. True: the first of a hold, it goes on; false: the button is down already, it is dropped. */
	bool Press(const FKey& Key)
	{
		bool bAlready = false;
		Down.Add(Key, &bAlready);
		return !bAlready;
	}
	void Release(const FKey& Key) { Down.Remove(Key); }
	void Reset() { Down.Reset(); }

	TSet<FKey> Down;
};

/**
 * The size a viewer's page asks the game to draw at (Pixel Streaming's "Resolution.Width" command: E3DS's Browser
 * Resolution "Dynamic" sends the viewer's frame size whenever it changes), fitted to what the game allows. Pixel
 * Streaming's own handler ran r.SetRes for any size of 1 or more; at 3840 x 2160 the encoder fell behind and the game
 * missed its viewer's leaving (box run d7), and a visitor can ask for any size from the browser's own tools.
 */
struct MURDERINC_API FMICloudSize
{
	static constexpr int32 MinWidth = 640, MinHeight = 360, MaxWidth = 1920, MaxHeight = 1080;
	/**
	 * False: the request is ignored (below 640 x 360: a phone held upright, a frame that is not laid out yet).
	 * True: Out is the size to draw at: the request itself, or the largest size of its shape within 1920 x 1080 (even
	 * numbers). OutShown is how many times wider the page shows the picture than the game draws it (1 unless the size
	 * was cut down): Pixel Streaming's mouse counts are counts of the drawn picture, so the mouse scale grows by it
	 * and the mouse keeps its speed.
	 */
	static bool Fit(int32 Width, int32 Height, FIntPoint& Out, double& OutShown);
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
 *  - when the last viewer disconnects, a run pauses (in its intro too) and everything that viewer held is let go
 *    (keys, buttons, sticks, triggers: no release arrives from a viewer who is gone); the next viewer gets the click
 *    card again, a guest who joins a session in progress does not (FMICloudViewers, ReleaseForLeave);
 *  - a double click is two clicks: the browser sends both presses and releases and then a "MouseDouble" message,
 *    which Unreal takes for a third press that is never released (E3DS's page sends no release after it); that
 *    message is dropped (GuardViewerInput);
 *  - mouse look takes the stream's mouse events one by one and turns the counts back into the browser's pixels:
 *    [MICloud] MouseScale (0.5: Pixel Streaming sends 2 counts per browser pixel when the game renders at the size the
 *    player shows it; launch option -MIMouseScale=<number> to tune it on the host without a rebuild), MouseTruncation
 *    (the count each event loses on the way) and the web game's pointer-lock spike filter (FMIStreamMouse,
 *    AMIPlayerController::StreamMouseEvent). On the desktop the mouse is untouched;
 *  - a viewer's console commands (the host passes -AllowPixelStreamingCommands) run only if they set one of the
 *    variables a visitor may tune (MITuning: the stream's own settings PixelStreaming2.* and PixelStreaming.*, the
 *    scalability groups, dynamic resolution, t.MaxFPS and a few more, some only within a range); anything else is
 *    refused and the first refusal of a session is logged (IsViewerCommandAllowed). The browser's size requests are
 *    a separate Pixel Streaming command: they still work, within 640 x 360 and 1920 x 1080 (FMICloudSize; the mouse
 *    scale follows a size that was cut down);
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
 *    logged every 30 s (-MICloudProbe=<seconds> changes the period, 0 turns it off);
 *  - the game looks after its own session (release 3c, Cloud/MISession.h): E3DS does not stop the game of a session
 *    that has ended, and the next session then finds the card shared with it. With no viewer for MI.Cloud.IdleAfter
 *    seconds (2) the game idles at MI.Cloud.IdleFps frames a second (2; 0 turns it off; launch options -MIIdleFps=,
 *    -MIIdleAfter=) and keeps the picture at its smallest; a joining viewer wakes it within a few milliseconds. When
 *    the last viewer has been gone for MI.Cloud.ExitAfterEmpty seconds (20: a host that keeps the game when a page is
 *    reloaded reconnects it within seconds, E3DS starts a new game for a reloaded page and wants the old one gone before
 *    that game has started, 34 s at the quickest seen; -MIExitAfterEmpty=) the game logs one line and quits (exit code
 *    0); so it does MI.Cloud.ExitIfNoViewer seconds (600;
 *    -MIExitIfNoViewer=) after its start when nobody ever came, and 5 s after the launcher that started it is gone
 *    (the launcher passes -MILauncherPid=<pid>; a game started without it is not watched). A viewer present keeps the
 *    game, a join cancels the countdown. -MIKeepAlive turns all of this off (the box's test scripts hold games with no
 *    viewer on purpose);
 *  - the encoder gets a range (release 3c, Cloud/MIStreamQuality.h): E3DS's Video Quality is a constant quantiser (Medium
 *    QP 34 for the lowest and the highest, High 16: launch options and console commands), which cannot give way to a thin
 *    connection. The two numbers are taken as the centre of a range: the lowest QP is the first minus MI.Cloud.QpBelow
 *    (10, not under MI.Cloud.QpFloor 8), the highest the second plus MI.Cloud.QpAbove (8, not over MI.Cloud.QpCeiling 48):
 *    34 gives 24 to 42, 16 gives 8 to 24. It holds for the launch options -PixelStreamingEncoderMinQP= and MaxQP= and for
 *    a viewer's PixelStreaming.Encoder.MinQP / MaxQP commands (each change is logged once); -MIQpExact turns the range
 *    off (launch options -MIQpBelow=, -MIQpAbove= set the numbers);
 *  - the round trip on the pause card and in the probe line is the median of the sender's last five measured values
 *    (FMIRoundTrip: Pixel Streaming reports a statistic only when it changes, and an unmeasured one is 0), cleared when
 *    the viewers change.
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

	/**
	 * The last viewer left: a run that is live or in its intro pauses (nobody is watching; the intro would end by
	 * itself after 2.4 s), and everything the viewer held is let go (AMIPlayerController::DropAllHeld): a key, button,
	 * stick or trigger that was down when the connection was cut gets no release, and would walk, turn or fire for the
	 * next viewer. Static, with the game's parts as arguments, for the tests; either may be null.
	 */
	static void ReleaseForLeave(UMIGameSubsystem* Game, AMIPlayerController* Controller);

	/**
	 * What this game does about its session, from the console variables and launch options as they are now (the numbers
	 * of the class comment). Static, for the tests and the probe.
	 */
	static FMISession::FOptions ReadSessionOptions(bool bStreamed);
	/** The encoder range settings as they are now (MI.Cloud.QpBelow, QpAbove, QpFloor, QpCeiling, QpExact). */
	static FMIEncoderRange::FSettings ReadEncoderSettings();

	bool IsStreamed() const { return bStreamed; }
	/** The game is idling: nobody is watching (see the class comment). */
	bool IsIdle() const { return bIdle; }
	bool IsWaitingForClick() const { return bWaitingForClick; }
	/** The first click, key or button of a viewer: hides the card. */
	void Dismiss();
	/** The stream's mouse shape now: the configured one, its scale times what the last size request was cut down by. */
	FMIStreamMouse GetMouseShape() const;
	/** One mouse event on its way through Slate. True: a spike, the event goes no further. */
	bool OnMouseEvent(const FVector2D& Delta);

	/**
	 * A key press on its way through Slate. True: it goes no further (a message for a gamepad button that is down
	 * already: FMIPadButtons).
	 */
	bool OnKeyDown(const FKey& Key, bool bRepeat);
	void OnKeyUp(const FKey& Key) { PadButtons.Release(Key); }
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
	/**
	 * Once the streamer is there, three of Pixel Streaming's handlers get ours in their place: the console command
	 * (the allowlist), the size request (FMICloudSize) and the double click (dropped).
	 */
	void GuardViewerInput();
	void OnViewerCommand(const FString& Command);
	void OnViewerSize(int32 Width, int32 Height);
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
	double StreamStat(const TCHAR* Name, double Missing = -1.0, bool bPeak = false, double MaxAge = 5.0) const;
	void MakeNumbersLine();

	/** Once, when the game becomes streamed: the session's numbers, the launcher to watch, the encoder's range. */
	void StartSession();
	/** Once a frame while streamed: idle, quit, or neither (FMISession::Decide). */
	void TickSession();
	/** The end of a frame while idle: waits until the next idle frame is due, or until a viewer arrives. */
	void SleepIdle(int32 Fps);
	void EnterIdle(const FString& Why);
	/** ReportedAgo: seconds since the stream reported the viewer's connection (a join that woke the game), or below 0. */
	void LeaveIdle(const TCHAR* Why, double ReportedAgo = -1.0);
	/** The session is over: one line, then FPlatformMisc::RequestExit(false). Once. */
	void RequestSessionExit(const FString& Why);
	/**
	 * Gives Pixel Streaming the encoder's QP range around the numbers wanted (launch options, a page's commands): sets
	 * its MaxQuality (the lowest QP) and MinQuality (the highest). Logs when the range changes.
	 */
	void ApplyEncoderRange(const TCHAR* Source);
	/** A viewer's "PixelStreaming.Encoder.MinQP 34" or MaxQP command. True: it was one. */
	bool OnEncoderCommand(const FString& Command);
	/** The lowest (bMin) or highest QP that was asked for, from Source: sets the encoder's range around it. */
	void SetWantedQp(bool bMin, int32 Qp, const TCHAR* Source);

	bool bStreamed = false;
	bool bProfileApplied = false;
	bool bWaitingForClick = false;
	bool bConnectionLost = false;
	bool bVideoChecked = false;
	bool bCommandsGuarded = false;
	bool bRefusalLogged = false;
	int32 CommandsRun = 0, CommandsRefused = 0;
	int32 DoubleClicksDropped = 0, SizeRequests = 0, SizeRequestsIgnored = 0;
	FMICloudViewers Viewers;
	FMIStreamMouse MouseShape;       // as configured ([MICloud], -MIMouseScale=)
	double MouseShown = 1.0;         // how many times wider the page shows the picture than it is drawn (FMICloudSize)
	FMIPadNav StickNav;
	FVector2D LeftStick = FVector2D::ZeroVector;
	FPlatformUserId StickUser = PLATFORMUSERID_NONE;
	FInputDeviceId StickDevice = INPUTDEVICEID_NONE;
	TArray<FName> StickKeysDown;  // pressed last frame, let go this frame
	FMIPadButtons PadButtons;     // the gamepad buttons that are down, as the stream reported them
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

	// The session (Cloud/MISession.h).
	FMISessionClock SessionClock;
	FMILauncherWatch LauncherWatch;
	uint64 LauncherStartTime = 0;
	double LauncherGoneAfter = 5.0;
	bool bSessionStarted = false;
	bool bIdle = false, bExitRequested = false;
	double IdleSince = 0.0, IdleFrameAt = 0.0;
	int32 IdleFrames = 0, ViewerEventsHandled = 0;
	FString SavedDynamicResMax;
	bool bDynamicResClamped = false;
	FMISession::EWhy LastWhy = FMISession::EWhy::Waiting;

	// The encoder's range and the round trip (Cloud/MIStreamQuality.h).
	int32 WantedMinQp = -1, WantedMaxQp = -1;   // what the launch options or the page asked for (-1: not given)
	FMIEncoderRange::FRange AppliedRange;
	bool bRangeApplied = false;
	FMIRoundTrip RoundTrip;

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
	/** The last half minute of live play in half-second steps: X the game's frames a second, Y the stream's (-1: not known). */
	TArray<FVector2f> PlayLows;
	int32 PlayLowNext = 0;
	// Peak: the largest value of the last two seconds (a viewer's audio and video report "bitrate" under one name,
	// in turn: the video's is the larger one).
	struct FStreamStat { float Value = 0.f, Peak = 0.f; double Time = 0.0, PeakTime = 0.0; };
	TMap<FName, FStreamStat> StreamStats;
};
