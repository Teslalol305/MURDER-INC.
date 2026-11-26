#include "Cloud/MICloud.h"

#include "Audio/MIAudioSubsystem.h"

#include <atomic>

#include "Async/Async.h"
#include "Async/TaskGraphInterfaces.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Fonts/FontMeasure.h"
#include "Framework/Application/IInputProcessor.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformMemory.h"
#include "HAL/FileManager.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/FileHelper.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Rendering/DrawElements.h"
#include "Rendering/SlateRenderer.h"
#include "DynamicRHI.h"
#include "DynamicRenderScaling.h"
#include "DynamicResolutionState.h"
#include "Misc/App.h"
#include "Misc/CoreDelegates.h"
#include "Misc/Paths.h"
#include "RHIStats.h"
#include "RHIStrings.h"
#include "RenderTimer.h"
#include "RenderUtils.h"
#include "Scalability.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Styling/CoreStyle.h"
#include "UnrealClient.h"
#include "UObject/UObjectGlobals.h"
#include "Widgets/SCompoundWidget.h"

#include "Core/Data/MIDataSubsystem.h"
#include "Flow/MIGameSubsystem.h"
#include "Flow/MIGameRules.h"
#include "Player/MIPlayerCharacter.h"
#include "Player/MIPlayerController.h"
#include "UI/MIFrontEnd.h"
#include "Weapons/MIWeaponComponent.h"
#include "UI/MIStyle.h"

#include <cstdio>
#if PLATFORM_LINUX && !WITH_EDITOR
#include <csignal>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <thread>
#include <unistd.h>
#endif

#if MI_WITH_PIXELSTREAMING2
#include "IPixelStreaming2InputHandler.h"
#include "IPixelStreaming2Module.h"
#include "IPixelStreaming2Streamer.h"
#include "IPixelStreaming2VideoProducer.h"
#include "PixelStreaming2Delegates.h"
#include "PixelStreaming2VideoProducers.h"
#endif

DEFINE_LOG_CATEGORY_STATIC(LogMICloud, Log, All);

namespace MICloudPrivate
{
	/** For the probe: back buffers Slate presented, and frames the stream's video source passed on. */
	std::atomic<int64> BackBuffers{0};
	std::atomic<int64> FramesPushed{0};

	/** Every line also goes to -MICloudLog=<file> when given (not in the Shipping game, where a viewer could name any
	 *  file through a launch option on the link): the stream test (tools/box/cloud/stream_test.cjs) reads what the game
	 *  saw from this file. */
	void Line(const FString& Text)
	{
		UE_LOG(LogMICloud, Display, TEXT("%s"), *Text);
#if NO_LOGGING
		// Shipping compiles UE_LOG out (the installed engine cannot turn bUseLoggingInShipping on): print the line, so
		// the launcher's log (MurderInc.sh tees the game's stdout into MurderInc/Saved/Logs) has it.
		printf("[MICloud] %s\n", TCHAR_TO_UTF8(*Text));
		fflush(stdout);
#endif
#if !UE_BUILD_SHIPPING
		static FString File = [] { FString F; FParse::Value(FCommandLine::Get(), TEXT("MICloudLog="), F); return F; }();
		if (!File.IsEmpty())
		{
			FFileHelper::SaveStringToFile(FString::Printf(TEXT("%.3f %s\n"), FPlatformTime::Seconds(), *Text), *File,
				FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
		}
#endif
	}
}

namespace MICloudPrivate
{
	// Pacing (Cloud/MIPacing.h). Console variables, so the cloud profile ([MICloud] +CVars), the launch option -MICVars
	// and E3DS's console-commands field can all set them without a new build.
	int32 GFramesInFlight = 1;
	FAutoConsoleVariableRef CVarFramesInFlight(TEXT("MI.Cloud.GpuFramesInFlight"), GFramesInFlight,
		TEXT("While streamed: how many frames the GPU may still owe the game when it starts the next one.\n")
		TEXT(" 0: none (the lowest delay; fewer frames a second when the GPU is the limit)\n")
		TEXT(" 1: one (default: no frame rate is lost)\n")
		TEXT("-1: no limit: the frames are only counted (the engine's own behaviour off screen: they can pile up)"));
	float GGpuWaitLimitMs = 250.f;
	FAutoConsoleVariableRef CVarGpuWaitLimit(TEXT("MI.Cloud.GpuWaitLimitMs"), GGpuWaitLimitMs,
		TEXT("While streamed: the longest the start of a frame waits for the GPU, in ms (then it goes on and counts a time-out)."));
	int32 GFpsTarget = 0;
	FAutoConsoleVariableRef CVarFpsTarget(TEXT("MI.Cloud.FpsTarget"), GFpsTarget,
		TEXT("While streamed: 60, 45 or 30 fixes the frame-rate target; 0 lets the game choose it by the GPU's time (launch option -MIFps=)."));
	float GFpsDropOver = 1.0f, GFpsDropAfter = 1.f, GFpsRaiseUnder = 0.8f, GFpsRaiseAfter = 10.f;
	FAutoConsoleVariableRef CVarFpsDropOver(TEXT("MI.Cloud.FpsDropOver"), GFpsDropOver,
		TEXT("The frame-rate target drops (in live play) when the GPU's time is over this share of the frame time at the smallest picture, or when the game falls short of the rate because it waits for the GPU."));
	FAutoConsoleVariableRef CVarFpsDropAfter(TEXT("MI.Cloud.FpsDropAfter"), GFpsDropAfter, TEXT("... for this many seconds."));
	FAutoConsoleVariableRef CVarFpsRaiseUnder(TEXT("MI.Cloud.FpsRaiseUnder"), GFpsRaiseUnder,
		TEXT("The frame-rate target may rise (only while no run is being played) when the GPU's time at the smallest picture is under this share of the frame time of the next rate up."));
	FAutoConsoleVariableRef CVarFpsRaiseAfter(TEXT("MI.Cloud.FpsRaiseAfter"), GFpsRaiseAfter, TEXT("... for this many seconds."));
	// Measured on the box (RTX PRO 6000, Story run, 1080p): 6.39 ms a frame at a 75 % picture, 6.00 ms at 50 % (runs
	// rf-sp75, rf-sp50), and 29 ms at 400 %: about an eighth of the frame's GPU time follows the pixels, the rest
	// (Lumen, the shadow maps, Nanite, the 1080p output) does not.
	float GFpsPixelPart = 0.12f;
	FAutoConsoleVariableRef CVarFpsPixelPart(TEXT("MI.Cloud.FpsPixelPart"), GFpsPixelPart,
		TEXT("The share of the GPU's frame time that follows the number of pixels drawn (0 to 1): the rise is judged by the time the GPU would need at the smallest picture, worked out with it."));

	// The session (Cloud/MISession.h) and the encoder's range (Cloud/MIStreamQuality.h): console variables like the
	// pacing's, so the cloud profile, the launch options of StartSession, -MICVars and E3DS's console-commands field can
	// all set them without a new build.
	int32 GIdleFps = 2;
	FAutoConsoleVariableRef CVarIdleFps(TEXT("MI.Cloud.IdleFps"), GIdleFps,
		TEXT("While streamed and nobody watches: the frames a second the game idles at (launch option -MIIdleFps=). 0: it never idles."));
	float GIdleAfter = 2.f;
	FAutoConsoleVariableRef CVarIdleAfter(TEXT("MI.Cloud.IdleAfter"), GIdleAfter,
		TEXT("Seconds with no viewer before the game idles (launch option -MIIdleAfter=)."));
	float GExitAfterEmpty = 60.f;
	FAutoConsoleVariableRef CVarExitAfterEmpty(TEXT("MI.Cloud.ExitAfterEmpty"), GExitAfterEmpty,
		TEXT("Seconds after the last viewer left before the game quits (launch option -MIExitAfterEmpty=). Long enough for a viewer whose connection broke (a tunnel, a Wi-Fi change, a reload) to come back to the same game where the host allows it; the launcher stops a game left over at the next start, so this does not have to be short. 0: never."));
	float GExitIfNoViewer = 600.f;
	FAutoConsoleVariableRef CVarExitIfNoViewer(TEXT("MI.Cloud.ExitIfNoViewer"), GExitIfNoViewer,
		TEXT("Seconds after the game's start before it quits for want of a first viewer (launch option -MIExitIfNoViewer=). 0: never."));
	int32 GKeepAlive = 0;
	FAutoConsoleVariableRef CVarKeepAlive(TEXT("MI.Cloud.KeepAlive"), GKeepAlive,
		TEXT("1: the game does not idle and does not quit by itself when nobody watches or its launcher is gone (launch option -MIKeepAlive; the box's test scripts)."));
	int32 GQpBelow = 10, GQpAbove = 8, GQpFloor = 8, GQpCeiling = 48, GQpExact = 0;
	FAutoConsoleVariableRef CVarQpBelow(TEXT("MI.Cloud.QpBelow"), GQpBelow,
		TEXT("The encoder's lowest QP is the QP the page asks for minus this (launch option -MIQpBelow=)."));
	FAutoConsoleVariableRef CVarQpAbove(TEXT("MI.Cloud.QpAbove"), GQpAbove,
		TEXT("The encoder's highest QP is the QP the page asks for plus this (launch option -MIQpAbove=)."));
	FAutoConsoleVariableRef CVarQpFloor(TEXT("MI.Cloud.QpFloor"), GQpFloor, TEXT("The range never goes below this QP (a request below it keeps its own number)."));
	FAutoConsoleVariableRef CVarQpCeiling(TEXT("MI.Cloud.QpCeiling"), GQpCeiling, TEXT("The range never goes above this QP (a request above it keeps its own number)."));
	FAutoConsoleVariableRef CVarQpExact(TEXT("MI.Cloud.QpExact"), GQpExact,
		TEXT("1: the encoder gets exactly the QPs the page and the launch options ask for, no range (launch option -MIQpExact)."));

	// The quality ladder (Cloud/MIQuality.h): the steps themselves are data ([MICloud] QualitySteps= of DefaultGame.ini).
	// OFF by default until the release gate has run it on a package (review of release 3c: it was only ever walked by pinning
	// a step in a Development game); -MILadder or MI.Cloud.QualityLadder 1 turns it on.
	int32 GQualityLadder = 0;
	FAutoConsoleVariableRef CVarQualityLadder(TEXT("MI.Cloud.QualityLadder"), GQualityLadder,
		TEXT("1: while streamed the game gives up the steps of the quality ladder when the GPU is still the limit at the smallest picture, and takes them back after a long calm. 0: off, full quality (the default until the gate has run it; launch options -MILadder and -MINoLadder)."));
	int32 GQualitySm6 = 0;
	FAutoConsoleVariableRef CVarQualitySm6(TEXT("MI.Cloud.QualitySm6"), GQualitySm6,
		TEXT("1: the ladder also runs on SM6 shaders. The steps were measured on SM5 only (Nanite, virtual shadow maps and hardware Lumen were not measured), so on SM6 the ladder is off unless this is 1."));
	float GQualityWarmUp = 15.f;
	FAutoConsoleVariableRef CVarQualityWarmUp(TEXT("MI.Cloud.QualityWarmUp"), GQualityWarmUp,
		TEXT("The ladder counts nothing for this many seconds after live play begins (after a menu, a pause, a retry, a map, an idle spell): shaders, Lumen's surface cache and textures make long frames on any card."));
	float GFpsHoldMax = 20.f, GFpsHoldOver = 1.3f;
	FAutoConsoleVariableRef CVarFpsHoldMax(TEXT("MI.Cloud.FpsHoldMax"), GFpsHoldMax,
		TEXT("While the quality ladder has a step to give, the frame-rate target's drop waits for it, for at most this many seconds over the line (0: the drop never waits)."));
	FAutoConsoleVariableRef CVarFpsHoldOver(TEXT("MI.Cloud.FpsHoldOver"), GFpsHoldOver,
		TEXT("... and only while the GPU's time is under this share of the frame time (a heavier load drops the target at once)."));
	int32 GQualityStep = -1;
	FAutoConsoleVariableRef CVarQualityStep(TEXT("MI.Cloud.QualityStep"), GQualityStep,
		TEXT("Fixes the quality ladder's step: 0 is full quality, 1 the first step, and so on up to the last one in the table. Below 0 lets the game choose (launch option -MIQuality=<n>)."));
	float GQualityDownLoad = 0.85f, GQualityUpLoad = 0.70f, GQualityDownAfter = 3.f, GQualityUpAfter = 60.f, GQualityMinGap = 10.f;
	FAutoConsoleVariableRef CVarQualityDownLoad(TEXT("MI.Cloud.QualityDownLoad"), GQualityDownLoad,
		TEXT("The ladder goes down a step when the GPU's time at the smallest picture is over this share of the frame time of the highest frame-rate target (60) ..."));
	FAutoConsoleVariableRef CVarQualityDownAfter(TEXT("MI.Cloud.QualityDownAfter"), GQualityDownAfter, TEXT("... for this many seconds of play."));
	FAutoConsoleVariableRef CVarQualityUpLoad(TEXT("MI.Cloud.QualityUpLoad"), GQualityUpLoad,
		TEXT("The ladder goes up a step (at a card or a set-up screen, at the highest frame-rate target) when the GPU's time without the last step would be under this share of the frame time ..."));
	FAutoConsoleVariableRef CVarQualityUpAfter(TEXT("MI.Cloud.QualityUpAfter"), GQualityUpAfter, TEXT("... for this many seconds of play. A rise that does not hold doubles it; one that holds earns it back."));
	FAutoConsoleVariableRef CVarQualityMinGap(TEXT("MI.Cloud.QualityMinGap"), GQualityMinGap, TEXT("The ladder changes at most once in this many seconds."));

	/**
	 * One count for every viewer event (a join, all gone) as the stream reports it. Pixel Streaming posts the report as a
	 * task for the game thread, which is where the idle game sleeps: SleepIdle runs the waiting tasks every 10 ms, so the
	 * count moves within 10 ms of the viewer's arrival and the game wakes then, not at the end of a 500 ms frame.
	 * ViewerEventsHandled (the subsystem's) catches up when OnViewerJoined / OnAllViewersLeft has run.
	 */
	std::atomic<int32> GViewerEvents{0};

	/** The subsystem of this game (one per game instance, set in Initialize): the Settings card's Graphics quality reaches the ladder through it. */
	UMICloudSubsystem* GSelf = nullptr;

	/** Seconds since the process started: the viewer and session lines carry it, so that a log without time stamps (the Shipping game's) says how long a countdown ran. */
	double Uptime()
	{
		return FPlatformTime::Seconds() - (GStartTime > 0.0 ? GStartTime : FPlatformTime::Seconds());
	}

	/** "game time 12.3 s, 12:37:51.482 UTC": the uptime and the clock to the millisecond, for a log that has no time stamps and a box that has other clocks (the GPU's record is by the clock; a viewer's own log is laid against it). */
	FString Stamp()
	{
		return FString::Printf(TEXT("game time %.1f s, %s UTC"), Uptime(), *FDateTime::UtcNow().ToString(TEXT("%H:%M:%S.%s")));
	}

	/** A launch option "-Name=value" sets a console variable of this family (the same variable -MICVars reaches). */
	void ApplyLaunchOption(const TCHAR* CommandLine, const TCHAR* Option, const TCHAR* VariableName)
	{
		FString Text;
		if (!FParse::Value(CommandLine, Option, Text, false) || Text.IsEmpty())
		{
			return;
		}
		if (IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(VariableName))
		{
			Var->Set(*Text, ECVF_SetByCommandline);
		}
	}

	/** The commit of BUILD.txt, seven characters ("" outside a cloud package): the pause card's line. */
	FString GBuildCommit;

	/** Sets a variable the way the cloud profile does, unless something stronger (a launch option, the console) holds it. */
	bool SetAsProfile(const TCHAR* Name, const FString& Value)
	{
		IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(Name);
		if (!Var || (Var->GetFlags() & ECVF_SetByMask) > ECVF_SetByDeviceProfile)
		{
			return false;
		}
		if (Var->GetString() != Value)  // no change, no change callbacks (the stream's frame rate refreshes its bitrate)
		{
			Var->Set(*Value, ECVF_SetByDeviceProfile);
		}
		return true;
	}

	/** Dynamic resolution's share of the output size now (0.5 to 1), or -1 when it is off; OutSmallest: at its minimum. */
	float PictureShare(bool& OutSmallest)
	{
		OutSmallest = true;  // off: nothing left to take from the resolution
		if (!GEngine)
		{
			return -1.f;
		}
		FDynamicResolutionStateInfos Infos;
		GEngine->GetDynamicResolutionCurrentStateInfos(Infos);
		if (Infos.Status != EDynamicResolutionStatus::Enabled)
		{
			return -1.f;
		}
		const float Share = Infos.ResolutionFractionApproximations[GDynamicPrimaryResolutionFraction];
		static IConsoleVariable* Min = IConsoleManager::Get().FindConsoleVariable(TEXT("r.DynamicRes.MinScreenPercentage"));
		OutSmallest = Share <= (Min ? Min->GetFloat() : 50.f) / 100.f + 0.02f;
		return Share;
	}

	UMIGameSubsystem* Game(const UGameInstance* GI)
	{
		UWorld* World = GI ? GI->GetWorld() : nullptr;
		return World ? World->GetSubsystem<UMIGameSubsystem>() : nullptr;
	}

#if PLATFORM_LINUX && !WITH_EDITOR
	/** Runs at exit(), before the static destructors that were constructed before it was armed. The engine's codec
	 *  registry (AVCodecs, FNVDEC) logs from its static destructor after the log is gone: a segfault on every exit of
	 *  a build with logging (docs/unreal/PROGRESS.md, "E3DS crash fix"). Everything that matters is already shut down
	 *  and flushed when main() returns, so end the process here. A stop asked for by a signal (SIGINT, SIGTERM,
	 *  SIGHUP: the engine shuts down normally, then returns 128 + the signal) is reported as a normal quit (0), so a
	 *  host that stops an idle game does not count it as a crash. */
	void ExitGuard(int Status, void*)
	{
		const bool bAskedStop = Status == 128 + SIGINT || Status == 128 + SIGTERM || Status == 128 + SIGHUP;
		const int Code = bAskedStop ? 0 : Status;
		printf("[MICloud] Exit: engine status %d%s; exiting with %d (static destructors skipped)\n", Status,
			bAskedStop ? " (stop asked by a signal: a normal quit)" : "", Code);
		fflush(nullptr);
		_exit(Code);
	}

	/** Armed when the engine starts its exit (FCoreDelegates::OnExit): later than every static the game made. */
	void ArmExitGuard()
	{
		static bool bArmed = false;
		if (!bArmed && !FParse::Param(FCommandLine::Get(), TEXT("MINoExitGuard")))
		{
			bArmed = true;
			on_exit(&ExitGuard, nullptr);
		}
	}
#endif

#if PLATFORM_LINUX && !WITH_EDITOR
	/** The signal handler of the shutdown crash net (below): only calls that are safe in a handler. */
	void ShutdownCrashHandler(int Signal)
	{
		static const char Head[] = "[MICloud] Exit: the engine crashed during its shutdown (signal ";
		static const char Tail[] = "); it had been asked to quit, so this is a normal quit: exit code 0\n";
		const char Number[2] = {(char)('0' + (Signal / 10) % 10), (char)('0' + Signal % 10)};
		ssize_t Ignored = write(STDOUT_FILENO, Head, sizeof(Head) - 1);
		Ignored = write(STDOUT_FILENO, Number, 2);
		Ignored = write(STDOUT_FILENO, Tail, sizeof(Tail) - 1);
		(void)Ignored;
		_exit(0);
	}
#endif

	/**
	 * From the moment the engine has been asked to quit (the session is over and the game asked itself, or a host stopped
	 * it with a signal), a crash in its shutdown is not a crash of the game in play: it ends the process with exit code 0
	 * and one line in the log that names the signal, instead of a report, a crash e-mail from the host and exit code 139.
	 * One of 27 runs of version 3b's gate ended with such a crash in its stop (SEGV, exit code 139, a null read inside
	 * main()), and since release 3c every session ends with a shutdown. -MINoExitGuard leaves it out, for finding such a crash.
	 */
	void ArmShutdownCrashNet()
	{
#if PLATFORM_LINUX && !WITH_EDITOR
		static std::atomic<bool> bArmed{false};
		if (FParse::Param(FCommandLine::Get(), TEXT("MINoExitGuard")) || bArmed.exchange(true))
		{
			return;
		}
		struct sigaction Action;
		memset(&Action, 0, sizeof(Action));
		Action.sa_handler = &ShutdownCrashHandler;
		sigemptyset(&Action.sa_mask);
		for (const int Signal : {SIGSEGV, SIGBUS, SIGABRT, SIGILL, SIGFPE})
		{
			sigaction(Signal, &Action, nullptr);
		}
#endif
	}

	/** FCoreDelegates::OnPreExit: the engine is shutting down. (-MIExitCrashTest, not in the Shipping game: crashes here on purpose, to prove the net.) */
	void ArmShutdownCrashNetAtPreExit()
	{
		ArmShutdownCrashNet();
#if !UE_BUILD_SHIPPING
		if (FParse::Param(FCommandLine::Get(), TEXT("MIExitCrashTest")))
		{
			printf("[MICloud] Exit crash test: crashing in the shutdown now (null write)\n");
			fflush(nullptr);
			volatile int32* Null = nullptr;
			*Null = 1;
		}
#endif
	}

	/**
	 * After the game has asked to quit by itself (the session is over), the process has this long to finish its shutdown.
	 * A 4K game once did not stop within 30 s of SIGTERM (docs/unreal/BOX.md), and a game that is stuck in its shutdown
	 * after its session ended is the leftover this whole change is about: past the limit the process ends itself (exit
	 * code 0, its lines flushed first). A normal shutdown takes seconds, and the exit guard ends the process first.
	 */
	void ArmShutdownWatchdog(double Seconds)
	{
#if PLATFORM_LINUX && !WITH_EDITOR
		std::thread([Seconds]
		{
			std::this_thread::sleep_for(std::chrono::duration<double>(Seconds));
			printf("[MICloud] Exit: the shutdown took over %.0f s: ending the process (exit code 0)\n", Seconds);
			fflush(nullptr);
			_exit(0);
		}).detach();
#endif
	}

	/** One block of lines at start: what the server gave the game, so a crash report from a host says where it ran. */
	void ReportStartup()
	{
		FString Build;
		if (FFileHelper::LoadFileToString(Build, *(FPaths::RootDir() / TEXT("BUILD.txt"))))
		{
			Build.ReplaceInline(TEXT("\r"), TEXT(""));
			Build.ReplaceInline(TEXT("\n"), TEXT(" | "));
			Build.TrimStartAndEndInline();
		}
		Line(FString::Printf(TEXT("Build: %s"), Build.IsEmpty() ? TEXT("(no BUILD.txt: not a cloud package)") : *Build));
		if (const int32 At = Build.Find(TEXT("commit ")); At != INDEX_NONE)
		{
			GBuildCommit = Build.Mid(At + 7, 7);
		}
		FString Level;
		GetFeatureLevelName(GMaxRHIFeatureLevel, Level);
		const EShaderPlatform SP = GMaxRHIShaderPlatform;
		Line(FString::Printf(TEXT("GPU: %s | driver %s (%s) | RHI %s | feature level %s | shader platform %s"),
			*GRHIAdapterName, *GRHIAdapterUserDriverVersion, *GRHIAdapterInternalDriverVersion,
			GDynamicRHI ? GDynamicRHI->GetName() : TEXT("none"), *Level, *LexToString(SP, false)));
		FTextureMemoryStats T;
		if (GDynamicRHI)
		{
			RHIGetTextureMemoryStats(T);
		}
		const bool bRT = IsRayTracingEnabled();
		const bool bNanite = DoesPlatformSupportNanite(SP);
		const bool bLumen = DoesPlatformSupportLumenGI(SP);
		Line(FString::Printf(TEXT("Features: hardware ray tracing %s (RHI support %d) | Nanite %s | Lumen %s | video memory %lld MB, texture pool %lld MB"),
			bRT ? TEXT("on") : TEXT("off"), GRHISupportsRayTracing ? 1 : 0, bNanite ? TEXT("on") : TEXT("off"), bLumen ? TEXT("on") : TEXT("off"),
			(long long)(T.DedicatedVideoMemory >> 20), (long long)(T.TexturePoolSize >> 20)));
		if (!FApp::CanEverRender())
		{
			// -NullRHI (the automation tests): nothing is drawn, no fallback to report.
		}
		else if (!bNanite || !bLumen)
		{
			// UE 5.9's SM6 check failed on this GPU or driver (Vulkan 1.3 with VK_KHR_compute_shader_derivatives,
			// mesh shaders, descriptor buffers...): the engine fell back to the SM5 shaders the package also carries.
			Line(FString::Printf(TEXT("Fallback: this GPU or driver did not pass Unreal's SM6 check; running the SM5 shaders: %s%s"),
				bNanite ? TEXT("") : TEXT("no Nanite (simpler meshes)"), bLumen ? TEXT(", Lumen in software") : TEXT(", no Lumen (flatter light)")));
		}
		else if (!bRT)
		{
			// No hardware ray tracing (driver or GPU): Lumen traces in software; let it trace the meshes' distance
			// fields (cooked with the package) instead of the coarse global field only.
			if (IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(TEXT("r.Lumen.TraceMeshSDFs")))
			{
				Var->Set(1, ECVF_SetByDeviceProfile);
			}
			Line(TEXT("Fallback: no hardware ray tracing on this server; Lumen traces in software (mesh distance fields)"));
		}
		// With 6 task workers or fewer Unreal's Vulkan RHI starts without its interrupt and submission threads
		// (VulkanSubmission.cpp, InitializeSubmissionPipe): finished GPU work is then noticed only when the RHI thread
		// submits or the render thread waits for it. The pacer waits on the render thread for that reason; this line
		// says which kind of server a log came from.
		const int32 Workers = FTaskGraphInterface::IsRunning() ? FTaskGraphInterface::Get().GetNumWorkerThreads() : 0;
		Line(FString::Printf(TEXT("CPUs: %d cores, %d with hyper-threads, %d task workers (%s)"), FPlatformMisc::NumberOfCores(),
			FPlatformMisc::NumberOfCoresIncludingHyperthreads(), Workers,
			Workers > 6 ? TEXT("more than 6: the RHI has its interrupt and submission threads") : TEXT("6 or fewer: the RHI runs without interrupt and submission threads")));
		Line(FString::Printf(TEXT("Command line: %s"), FCommandLine::Get()));
	}

#if MI_WITH_PIXELSTREAMING2
	/** The default streamer's input handler (null until the plugin has made its streamer). */
	TSharedPtr<IPixelStreaming2InputHandler> StreamInput()
	{
		if (!IPixelStreaming2Module::IsAvailable())
		{
			return nullptr;
		}
		IPixelStreaming2Module& Module = IPixelStreaming2Module::Get();
		if (!Module.IsReady())
		{
			return nullptr;
		}
		const TSharedPtr<IPixelStreaming2Streamer> Streamer = Module.FindStreamer(Module.GetDefaultStreamerID());
		return Streamer.IsValid() ? Streamer->GetInputHandler().Pin() : nullptr;
	}
#endif
}

bool FMICloudSize::Fit(int32 Width, int32 Height, FIntPoint& Out, double& OutShown)
{
	if (Width < MinWidth || Height < MinHeight || Width > 32768 || Height > 32768)
	{
		return false;
	}
	// Even numbers: H.264's 4:2:0 colour has half the picture's size in both directions.
	Out = FIntPoint(Width & ~1, Height & ~1);
	OutShown = (double)Width / Out.X;
	const double Scale = FMath::Min((double)MaxWidth / Width, (double)MaxHeight / Height);
	if (Scale < 1.0)
	{
		// The largest size of the same shape that fits, in even numbers (a video encoder's sizes).
		Out.X = FMath::Max(2, FMath::RoundToInt32(Width * Scale) & ~1);
		Out.Y = FMath::Max(2, FMath::RoundToInt32(Height * Scale) & ~1);
		OutShown = (double)Width / Out.X;
	}
	return true;
}

bool FMICloudSize::FitStart(FIntPoint Launch, bool bAsGiven, FIntPoint& Out, double& OutShown)
{
	Out = Launch;
	OutShown = 1.0;
	if (bAsGiven || Launch.X <= 0 || Launch.Y <= 0)
	{
		return false;
	}
	FIntPoint Fitted(0, 0);
	double Shown = 1.0;
	if (!Fit(Launch.X, Launch.Y, Fitted, Shown) || Fitted == Launch)
	{
		return false;
	}
	Out = Fitted;
	OutShown = Shown;
	return true;
}

// ---- the card, the pause hint and the cursor, painted over the game viewport --------------------------------------

class SMICloudOverlay : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SMICloudOverlay) {}
	SLATE_END_ARGS()

	void Construct(const FArguments&, UMICloudSubsystem* InOwner)
	{
		Owner = InOwner;
		SetVisibility(EVisibility::HitTestInvisible);
	}

	virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D::ZeroVector; }

	virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& Geo, const FSlateRect& Cull, FSlateWindowElementList& Out,
		int32 Layer, const FWidgetStyle& Style, bool bParentEnabled) const override
	{
		const UMICloudSubsystem* O = Owner.Get();
		if (!O || !O->IsStreamed())
		{
			return Layer;
		}
		const FVector2D Size = Geo.GetLocalSize();
		const float S = FMath::Max(0.5f, (float)Size.Y / 1080.f);
		const FSlateBrush* White = FCoreStyle::Get().GetBrush("GenericWhiteBox");
		UMIGameSubsystem* G = MICloudPrivate::Game(O->GetGameInstance());
		const EMIGameState State = G ? G->GetRules().GetState() : EMIGameState::Title;

		if (O->IsWaitingForClick())
		{
			FSlateDrawElement::MakeBox(Out, Layer, Geo.ToPaintGeometry(), White, ESlateDrawEffect::None,
				MIStyle::WithAlpha(MIStyle::Bg(), 0.82f));
			const double Mid = Size.Y * 0.5;
			Text(Out, Layer + 1, Geo, TEXT("MURDER INC."), MIStyle::Display(64 * S), MIStyle::Ink(), Mid - 150 * S);
			// A plate behind the call to action, so it reads as the thing to click.
			const FString Call = TEXT("CLICK TO PLAY");
			const FSlateFontInfo CallFont = MIStyle::Display(44 * S);
			const FVector2D CallSize = Measure(Call, CallFont);
			const FVector2D Pad(36 * S, 14 * S);
			const FVector2D PlateSize = CallSize + Pad * 2;
			FSlateDrawElement::MakeBox(Out, Layer + 1,
				Geo.ToPaintGeometry(PlateSize, FSlateLayoutTransform(FVector2D((Size.X - PlateSize.X) * 0.5, Mid - 40 * S))),
				White, ESlateDrawEffect::None, MIStyle::Gold());
			Text(Out, Layer + 2, Geo, Call, CallFont, MIStyle::Bg(), Mid - 40 * S + Pad.Y);
			const FLinearColor Dim = MIStyle::InkDim();
			Text(Out, Layer + 1, Geo, TEXT("Mouse to look  ·  W A S D to move  ·  Shift sprint  ·  R reload  ·  hold E to grab"),
				MIStyle::Body(20 * S), Dim, Mid + 70 * S);
			Text(Out, Layer + 1, Geo, TEXT("P pauses  ·  Esc gives the mouse back to the browser  ·  a gamepad works too"),
				MIStyle::Body(20 * S, true), MIStyle::Ink(), Mid + 104 * S);
			// E3DS starts a stream muted when the browser refuses sound before a click on the page, and then only its
			// own speaker button (bottom right of the player) turns the sound on.
			Text(Out, Layer + 1, Geo, TEXT("No sound? Click the speaker at the bottom right."), MIStyle::Body(18 * S), Dim, Mid + 138 * S);
			return Layer + 3;
		}

		const APlayerController* PC = O->GetGameInstance() ? O->GetGameInstance()->GetFirstLocalPlayerController() : nullptr;
		const AMIPlayerController* MIPC = Cast<AMIPlayerController>(PC);
		const UMIFrontEnd* Front = G ? G->GetFrontEnd() : nullptr;
		const bool bPad = Front && Front->IsShown() ? Front->IsPad() : MIPC && MIPC->IsPadActive();
		if (State == EMIGameState::Paused)
		{
			// The pause card says nothing about keys; in a browser Esc may never reach the game, so name P. With a
			// controller in the hand, its own button.
			const FString Pause = G ? G->ControlName(TEXT("pause"), true) : FString();
			Text(Out, Layer, Geo, bPad ? (Pause.IsEmpty() ? FString(TEXT("START")) : Pause) + TEXT(" to resume")
					: FString(TEXT("P to resume  ·  Esc gives the mouse back to the browser; click the game to take it again")),
				MIStyle::Body(18 * S, true), MIStyle::Ink(), Size.Y - 64 * S);
			// The game's own numbers, small and dim: a screenshot of the pause card answers what the server's log would
			// (which GPU, how fast, how large the picture, how the stream is doing).
			if (!O->GetNumbersLine().IsEmpty())
			{
				Text(Out, Layer, Geo, O->GetNumbersLine(), MIStyle::Body(13 * S), MIStyle::InkDim(), Size.Y - 30 * S);
			}
		}

		// The stream has no operating-system cursor: draw one wherever the game shows the mouse (not for a player
		// who holds a controller: the arrow sat in a corner of every card).
		if (PC && PC->ShouldShowMouseCursor() && !bPad && FSlateApplication::IsInitialized())
		{
			const FVector2f P = FVector2f(Geo.AbsoluteToLocal(FSlateApplication::Get().GetCursorPos()));
			const float C = 22.f * S;
			TArray<FVector2f> Arrow = {P, P + FVector2f(0, C), P + FVector2f(C * 0.28f, C * 0.74f), P + FVector2f(C * 0.72f, C * 0.72f), P};
			FSlateDrawElement::MakeLines(Out, Layer + 1, Geo.ToPaintGeometry(), Arrow, ESlateDrawEffect::None, FLinearColor::Black, true, 4.f * S);
			FSlateDrawElement::MakeLines(Out, Layer + 2, Geo.ToPaintGeometry(), Arrow, ESlateDrawEffect::None, FLinearColor::White, true, 2.f * S);
			return Layer + 3;
		}
		return Layer + 1;
	}

private:
	static FVector2D Measure(const FString& S, const FSlateFontInfo& Font)
	{
		return FSlateApplication::Get().GetRenderer()->GetFontMeasureService()->Measure(S, Font);
	}

	static void Text(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo, const FString& S, const FSlateFontInfo& Font,
		const FLinearColor& Colour, double Y)
	{
		const FVector2D M = Measure(S, Font);
		FSlateDrawElement::MakeText(Out, Layer, Geo.ToPaintGeometry(M, FSlateLayoutTransform(FVector2D((Geo.GetLocalSize().X - M.X) * 0.5, Y))),
			S, Font, ESlateDrawEffect::None, Colour);
	}

	TWeakObjectPtr<UMICloudSubsystem> Owner;
};

// ---- the first click: eaten, it only hides the card ----------------------------------------------------------------

class FMICloudInput : public IInputProcessor
{
public:
	explicit FMICloudInput(UMICloudSubsystem* InOwner) : Owner(InOwner) {}

	virtual void Tick(const float DeltaTime, FSlateApplication&, TSharedRef<ICursor>) override
	{
		if (UMICloudSubsystem* O = Owner.Get())
		{
			O->TickStickMenu(DeltaTime);
		}
	}
	virtual const TCHAR* GetDebugName() const override { return TEXT("MICloudClickToPlay"); }

	virtual bool HandleKeyDownEvent(FSlateApplication&, const FKeyEvent& Event) override
	{
		UMICloudSubsystem* O = Owner.Get();
		return (O && O->OnKeyDown(Event.GetKey(), Event.IsRepeat())) || Eat();
	}
	virtual bool HandleKeyUpEvent(FSlateApplication&, const FKeyEvent& Event) override
	{
		if (UMICloudSubsystem* O = Owner.Get())
		{
			O->OnKeyUp(Event.GetKey());
		}
		return false;
	}
	virtual bool HandleAnalogInputEvent(FSlateApplication&, const FAnalogInputEvent& Event) override
	{
		if (UMICloudSubsystem* O = Owner.Get())
		{
			O->OnAnalog(Event.GetKey(), Event.GetAnalogValue(), Event.GetPlatformUserId(), Event.GetInputDeviceId());
		}
		return false;
	}
	virtual bool HandleMouseButtonDownEvent(FSlateApplication&, const FPointerEvent&) override { return Eat(); }
	/** Every mouse move of the stream, one event at a time: the look (and the spike filter, which eats the event). */
	virtual bool HandleMouseMoveEvent(FSlateApplication&, const FPointerEvent& Event) override
	{
		UMICloudSubsystem* O = Owner.Get();
		return O && O->OnMouseEvent(Event.GetCursorDelta());
	}
	virtual bool HandleMouseButtonUpEvent(FSlateApplication&, const FPointerEvent&) override
	{
		const bool bWas = bEatRelease;
		bEatRelease = false;
		return bWas;
	}

private:
	bool Eat()
	{
		UMICloudSubsystem* O = Owner.Get();
		if (!O || !O->IsWaitingForClick())
		{
			return false;
		}
		O->Dismiss();
		bEatRelease = true;
		return true;
	}

	TWeakObjectPtr<UMICloudSubsystem> Owner;
	bool bEatRelease = false;
};

// ---- the subsystem -------------------------------------------------------------------------------------------------

bool UMICloudSubsystem::IsStreamedByCommandLine()
{
	const TCHAR* Cmd = FCommandLine::Get();
	FString V;
	return FParse::Param(Cmd, TEXT("MICloud"))
		|| FParse::Value(Cmd, TEXT("PixelStreamingURL="), V)
		|| FParse::Value(Cmd, TEXT("PixelStreamingConnectionURL="), V)
		|| FParse::Value(Cmd, TEXT("PixelStreamingSignallingURL="), V);
}

int32 UMICloudSubsystem::ApplyCloudProfile()
{
	TArray<FString> Lines;
	GConfig->GetArray(TEXT("MICloud"), TEXT("CVars"), Lines, GGameIni);
	int32 N = 0;
	for (const FString& Line : Lines)
	{
		FString Name, Value;
		if (!Line.Split(TEXT("="), &Name, &Value))
		{
			continue;
		}
		Name.TrimStartAndEndInline();
		Value.TrimStartAndEndInline();
		if (IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(*Name))
		{
			Var->Set(*Value, ECVF_SetByDeviceProfile);
			++N;
		}
		else
		{
			UE_LOG(LogMICloud, Warning, TEXT("Cloud profile: no console variable %s"), *Name);
		}
	}
	// Pixel Streaming 2's own settings (the capture and the stream's pacing): the plugin is only in the game target,
	// so these lines are apart from the ones every build must know.
	TArray<FString> Stream;
	GConfig->GetArray(TEXT("MICloud"), TEXT("StreamCVars"), Stream, GGameIni);
	int32 StreamSet = 0;
	for (const FString& Line : Stream)
	{
		FString Name, Value;
		if (Line.Split(TEXT("="), &Name, &Value))
		{
			StreamSet += MICloudPrivate::SetAsProfile(*Name.TrimStartAndEnd(), Value.TrimStartAndEnd()) ? 1 : 0;
		}
	}
	MICloudPrivate::Line(FString::Printf(TEXT("Cloud profile applied: %d of %d settings, %d of %d stream settings"), N, Lines.Num(), StreamSet, Stream.Num()));
	return N;
}

int32 UMICloudSubsystem::ApplyTuningOption(const TCHAR* CommandLine)
{
	FString Text;
	if (!CommandLine || !FParse::Value(CommandLine, TEXT("MICVars="), Text, false) || Text.IsEmpty())
	{
		return 0;
	}
	TArray<TPair<FString, FString>> Allowed;
	TArray<FString> Refused;
	MITuning::ParseOption(Text, Allowed, Refused);
	int32 N = 0;
	for (const TPair<FString, FString>& Pair : Allowed)
	{
		if (IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(*Pair.Key))
		{
			Var->Set(*Pair.Value, ECVF_SetByCommandline);
			MICloudPrivate::Line(FString::Printf(TEXT("Launch option -MICVars: %s = %s (now %s)"), *Pair.Key, *Pair.Value, *Var->GetString()));
			++N;
		}
		else
		{
			MICloudPrivate::Line(FString::Printf(TEXT("Launch option -MICVars: no console variable %s"), *Pair.Key));
		}
	}
	for (const FString& Entry : Refused)
	{
		MICloudPrivate::Line(FString::Printf(TEXT("Launch option -MICVars: refused \"%s\" (write name=value,name=value; allowed: %s)"), *Entry, *MITuning::AllowedList()));
	}
	return N;
}

FMIStreamMouse UMICloudSubsystem::ReadMouseShape(const TCHAR* CommandLine, double Glitch)
{
	const double DefaultScale = 0.5, DefaultTruncation = 1.0;
	double Scale = DefaultScale, Truncation = DefaultTruncation;
	if (GConfig)
	{
		GConfig->GetDouble(TEXT("MICloud"), TEXT("MouseScale"), Scale, GGameIni);
		GConfig->GetDouble(TEXT("MICloud"), TEXT("MouseTruncation"), Truncation, GGameIni);
	}
	float Option = 0.f;
	if (CommandLine && FParse::Value(CommandLine, TEXT("MIMouseScale="), Option))
	{
		Scale = Option;
	}
	if (CommandLine && FParse::Value(CommandLine, TEXT("MIMouseTruncation="), Option))
	{
		Truncation = Option;
	}
	FMIStreamMouse Shape;
	Shape.Scale = FMath::IsFinite(Scale) && Scale >= 0.05 && Scale <= 4.0 ? Scale : DefaultScale;
	Shape.Truncation = FMath::IsFinite(Truncation) && Truncation >= 0.0 && Truncation <= 2.0 ? Truncation : DefaultTruncation;
	Shape.Glitch = FMath::Max(0.0, Glitch);
	return Shape;
}

FMISession::FOptions UMICloudSubsystem::ReadSessionOptions(bool bStreamed)
{
	FMISession::FOptions O;
	O.bStreamed = bStreamed;
	O.bKeepAlive = MICloudPrivate::GKeepAlive != 0;
	O.IdleAfter = MICloudPrivate::GIdleAfter;
	O.IdleFps = MICloudPrivate::GIdleFps;
	O.ExitAfterEmpty = MICloudPrivate::GExitAfterEmpty;
	O.ExitIfNoViewer = MICloudPrivate::GExitIfNoViewer;
	return FMISession::Sanitize(O);
}

FMIEncoderRange::FSettings UMICloudSubsystem::ReadEncoderSettings()
{
	FMIEncoderRange::FSettings S;
	S.Below = MICloudPrivate::GQpBelow;
	S.Above = MICloudPrivate::GQpAbove;
	S.Floor = MICloudPrivate::GQpFloor;
	S.Ceiling = MICloudPrivate::GQpCeiling;
	S.bExact = MICloudPrivate::GQpExact != 0;
	return S;
}

TArray<FMIQualityStep> UMICloudSubsystem::ReadQualityTable(TArray<FString>* OutErrors)
{
	TArray<FString> Lines;
	if (GConfig)
	{
		GConfig->GetArray(TEXT("MICloud"), TEXT("QualitySteps"), Lines, GGameIni);
	}
	return FMIQualityTable::Parse(Lines, OutErrors);
}

bool UMICloudSubsystem::IsViewerCommandAllowed(const FString& Command, FString* OutCommand)
{
	const FString C = Command.TrimStartAndEnd();
	if (C.IsEmpty() || C.Len() > 256)
	{
		return false;
	}
	for (const TCHAR Ch : C)
	{
		// One command only: the player's console splits a line at '|' and at line ends.
		if (Ch == TEXT('|') || Ch == TEXT('\n') || Ch == TEXT('\r') || Ch < TEXT(' '))
		{
			return false;
		}
	}
	// "name", "name value" or "name=value".
	int32 Cut = INDEX_NONE;
	for (int32 I = 0; I < C.Len(); ++I)
	{
		if (C[I] == TEXT(' ') || C[I] == TEXT('='))
		{
			Cut = I;
			break;
		}
	}
	const FString Name = Cut == INDEX_NONE ? C : C.Left(Cut);
	FString Value = Cut == INDEX_NONE ? FString() : C.Mid(Cut + 1).TrimStartAndEnd();
	if (Value.StartsWith(TEXT("=")))
	{
		Value = Value.Mid(1).TrimStartAndEnd();  // "name = value"
	}
	if (!MITuning::IsAllowed(Name, Value))
	{
		return false;
	}
	if (OutCommand)
	{
		*OutCommand = Value.IsEmpty() ? Name : Name + TEXT(" ") + Value;
	}
	return true;
}

void UMICloudSubsystem::ApplyStreamedQuality(int32 Level)
{
	// The levels the game started with are what 'auto' means here.
	static TOptional<Scalability::FQualityLevels> Startup;
	if (!Startup.IsSet())
	{
		if (Level < 0)
		{
			return;  // auto, and nothing was ever changed
		}
		Startup = Scalability::GetQualityLevels();
	}
	Scalability::FQualityLevels Levels = Startup.GetValue();
	if (Level >= 0)
	{
		Levels.SetFromSingleQualityLevel(FMath::Min(Level, 3));
	}
	// Not the resolution: SetFromSingleQualityLevel gives it 50, 71, 87 or 100 % with the level (Ultra would render the
	// full output size); it stays what it is now, and the engine sets nothing where the value does not change.
	Levels.ResolutionQuality = Scalability::GetQualityLevels().ResolutionQuality;
	// The ladder's steps sit above the scalability groups' priority: give the variables back before the player's level is
	// written, and let the ladder look at what the new level left (a step never raises what the level already lowered).
	if (MICloudPrivate::GSelf)
	{
		MICloudPrivate::GSelf->ReleaseQualityHolds();
	}
	Scalability::SetQualityLevels(Levels);
	if (MICloudPrivate::GSelf)
	{
		MICloudPrivate::GSelf->ReapplyQualityStep(TEXT("the Graphics quality was changed"));
	}
	MICloudPrivate::Line(FString::Printf(TEXT("Graphics quality: %s (scalability groups only; the resolution, the frame cap and the cloud profile stay)"),
		Level < 0 ? TEXT("auto") : *FString::FromInt(FMath::Min(Level, 3))));
}

void UMICloudSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	MICloudPrivate::GSelf = this;
	bProbeGiven = FParse::Value(FCommandLine::Get(), TEXT("MICloudProbe="), ProbePeriod);
	// The session's clock runs from the process's start (a first viewer is awaited from then, not from this subsystem).
	SessionClock.Start(GStartTime > 0.0 ? GStartTime : FPlatformTime::Seconds());
	static bool bStarted = false;  // once per process (a game instance is made once in a packaged game)
	if (!bStarted)
	{
		bStarted = true;
		MICloudPrivate::ReportStartup();
#if PLATFORM_LINUX && !WITH_EDITOR
		FCoreDelegates::OnExit.AddStatic(&MICloudPrivate::ArmExitGuard);
		FCoreDelegates::OnPreExit.AddStatic(&MICloudPrivate::ArmShutdownCrashNetAtPreExit);
#endif
	}
#if !UE_BUILD_SHIPPING
	// -MICrashTest=<seconds>: crash on purpose after that long, to prove that a crash leaves a log and a crash report
	// (tools/box/cloud/e3ds-repro.sh; the Development game, launch option -MIDev). Not in the Shipping game: a viewer
	// can add launch options to a stream link, and every crash is an email to the owner.
	float CrashIn = 0.f;
	if (FParse::Value(FCommandLine::Get(), TEXT("MICrashTest="), CrashIn) && CrashIn > 0.f)
	{
		CrashTestAt = FPlatformTime::Seconds() + CrashIn;
		MICloudPrivate::Line(FString::Printf(TEXT("Crash test: the game will crash on purpose in %.0f s"), CrashIn));
	}
#endif
	if (IsStreamedByCommandLine())
	{
		BecomeStreamed(TEXT("command line"));
	}

#if MI_WITH_PIXELSTREAMING2
	if (UPixelStreaming2Delegates* D = UPixelStreaming2Delegates::Get())
	{
		TWeakObjectPtr<UMICloudSubsystem> Weak(this);
		auto OnGame = [Weak](TFunction<void(UMICloudSubsystem&)> F)
		{
			AsyncTask(ENamedThreads::GameThread, [Weak, F]() { if (UMICloudSubsystem* S = Weak.Get()) F(*S); });
		};
		StreamHandles.Add(D->OnConnectedToSignallingServerNative.AddLambda([OnGame](FString)
			{ OnGame([](UMICloudSubsystem& S) { S.BecomeStreamed(TEXT("signalling server")); }); }));
		// A viewer event is counted here, on whatever thread the stream reports it, before the game thread has it: the idle
		// game sleeps in small steps and wakes when the count moves (SleepIdle), and does not go back to sleep until the game
		// thread has handled the event (ViewerEventsHandled).
		StreamHandles.Add(D->OnNewConnectionNative.AddLambda([OnGame](FString, FString)
			{ ++MICloudPrivate::GViewerEvents; OnGame([](UMICloudSubsystem& S) { S.OnViewerJoined(); }); }));
		StreamHandles.Add(D->OnAllConnectionsClosedNative.AddLambda([OnGame](FString)
			{ ++MICloudPrivate::GViewerEvents; OnGame([](UMICloudSubsystem& S) { S.OnAllViewersLeft(); }); }));
		// The sender's own statistics (frames captured, encoded and sent a second, bitrate, QP, round trip): broadcast on
		// the game thread about once a second for each viewer.
		StreamHandles.Add(D->OnStatChangedNative.AddUObject(this, &UMICloudSubsystem::OnStreamStat));
	}
#endif

	TickHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateUObject(this, &UMICloudSubsystem::Tick));
}

void UMICloudSubsystem::Deinitialize()
{
	if (MICloudPrivate::GSelf == this)
	{
		MICloudPrivate::GSelf = nullptr;
	}
	FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
	if (bIdle)
	{
		LeaveIdle(TEXT("the game is shutting down"));
	}
#if MI_WITH_PIXELSTREAMING2
	if (UPixelStreaming2Delegates* D = UPixelStreaming2Delegates::Get(); D && StreamHandles.Num() == 4)
	{
		D->OnConnectedToSignallingServerNative.Remove(StreamHandles[0]);
		D->OnNewConnectionNative.Remove(StreamHandles[1]);
		D->OnAllConnectionsClosedNative.Remove(StreamHandles[2]);
		D->OnStatChangedNative.Remove(StreamHandles[3]);
	}
#endif
	StreamHandles.Reset();
	if (Pacer.IsValid())
	{
		Pacer->Stop();
		Pacer.Reset();
	}
	if (Input.IsValid() && FSlateApplication::IsInitialized())
	{
		FSlateApplication::Get().UnregisterInputPreProcessor(Input);
	}
	if (UGameViewportClient* VC = OverlayViewport.Get(); VC && Overlay.IsValid())
	{
		VC->RemoveViewportWidgetContent(Overlay.ToSharedRef());
	}
	Input.Reset();
	Overlay.Reset();
	Super::Deinitialize();
}

void UMICloudSubsystem::BecomeStreamed(const TCHAR* Why)
{
	if (!bStreamed)
	{
		MICloudPrivate::Line(FString::Printf(TEXT("Streamed (%s): click to play, cloud profile"), Why));
		bStreamed = true;
		// -MICloudNoCard: no click card (the memory runs and pictures on the box, which no viewer clicks).
		bWaitingForClick = !FParse::Param(FCommandLine::Get(), TEXT("MICloudNoCard"));
		// The mouse through the data channel (FMIStreamMouse): the spike filter's size is the web game's.
		double Glitch = 0.0;
		const UMIDataSubsystem* Data = GetGameInstance() ? GetGameInstance()->GetSubsystem<UMIDataSubsystem>() : nullptr;
		FMIConfigData Config;
		FString Error;
		if (Data && Data->IsLoaded())
		{
			Glitch = Data->GetConfig().Player.Look.MouseGlitch;
			StickNav.Config = Data->GetConfig().Player.Look.Pad;
		}
		else if (UMIDataSubsystem::LoadConfig(Config, Error))
		{
			Glitch = Config.Player.Look.MouseGlitch;
			StickNav.Config = Config.Player.Look.Pad;
		}
		MouseShape = ReadMouseShape(FCommandLine::Get(), Glitch);
		MICloudPrivate::Line(FString::Printf(TEXT("Mouse look: %.4f browser pixels per count ([MICloud] MouseScale; launch option -MIMouseScale=<number>), %.2f count(s) put back per event and axis (MouseTruncation), events beyond %.0f pixels dropped as pointer-lock spikes"),
			MouseShape.Scale, MouseShape.Truncation, MouseShape.Glitch));
	}
	if (!bProfileApplied)
	{
		bProfileApplied = true;
		ApplyCloudProfile();
		ApplyTuningOption(FCommandLine::Get());
		StartPacing();
		StartQuality();
		StartSession();
	}
}

FMIStreamMouse UMICloudSubsystem::GetMouseShape() const
{
	FMIStreamMouse Shape = MouseShape;
	Shape.Scale *= MouseShown;
	return Shape;
}

void UMICloudSubsystem::ReleaseForLeave(UMIGameSubsystem* Game, AMIPlayerController* Controller)
{
	if (Game)
	{
		// In the intro as well (2.4 s after "Hit the block", 1.1 s after a retry): the run would go live by itself
		// with nobody watching, and the next viewer's mouse and sticks would turn and move the player under the click
		// card. The pause key pauses in the intro too (UMIGameSubsystem::PauseKey).
		const EMIGameState State = Game->GetRules().GetState();
		if (State == EMIGameState::Playing || State == EMIGameState::Intro)
		{
			Game->Pause();
		}
	}
	if (Controller)
	{
		Controller->DropAllHeld();
	}
}

bool UMICloudSubsystem::PauseForAway(UMIGameSubsystem* Game, AMIPlayerController* Controller)
{
	if (!Game)
	{
		return false;
	}
	const EMIGameState State = Game->GetRules().GetState();
	if (State != EMIGameState::Playing && State != EMIGameState::Intro)
	{
		return false;  // a menu, a card or a run already paused: nothing runs behind the page
	}
	ReleaseForLeave(Game, Controller);
	return true;
}

bool UMICloudSubsystem::IsAwayMessage(const TArray<uint8>& Message)
{
	const int32 Units = Message.Num() >= 2 ? (int32)(Message[0] | (Message[1] << 8)) : 0;
	if (Units <= 0 || Units > 256 || Message.Num() < 2 + 2 * Units)
	{
		return false;  // empty, cut short, or too long to be the game's short word
	}
	FString Descriptor;
	Descriptor.Reserve(Units);
	for (int32 I = 0; I < Units; ++I)
	{
		Descriptor.AppendChar((TCHAR)(Message[2 + 2 * I] | (Message[3 + 2 * I] << 8)));
	}
	TSharedPtr<FJsonObject> Json;
	FString Word;
	return Descriptor.Contains(TEXT("murderinc")) && FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Descriptor), Json)
		&& Json.IsValid() && Json->TryGetStringField(TEXT("murderinc"), Word) && Word.Equals(TEXT("away"), ESearchCase::IgnoreCase);
}

void UMICloudSubsystem::OnViewerAway(const TCHAR* Why)
{
	++AwaySignals;
	const UGameInstance* GI = GetGameInstance();
	if (PauseForAway(MICloudPrivate::Game(GI), GI ? Cast<AMIPlayerController>(GI->GetFirstLocalPlayerController()) : nullptr))
	{
		++AwayPauses;
		MICloudPrivate::Line(FString::Printf(TEXT("Viewer away (%s): the run is paused and what the viewer held is let go (%s)"), Why, *MICloudPrivate::Stamp()));
	}
}

void UMICloudSubsystem::Dismiss()
{
	if (bWaitingForClick)
	{
		bWaitingForClick = false;
		MICloudPrivate::Line(FString::Printf(TEXT("Click to play: dismissed")));
	}
}

void UMICloudSubsystem::OnViewerJoined()
{
	BecomeStreamed(TEXT("viewer"));
	bConnectionLost = false;
	// The session: every countdown stops, the game wakes at full speed in this very frame, and the round trip of the
	// viewer before is not this one's.
	SessionClock.Joined(FPlatformTime::Seconds());
	RoundTrip.Reset();
	++ViewerEventsHandled;
	if (bIdle)
	{
		LeaveIdle(TEXT("a viewer joined"));
	}
	if (Viewers.Join())
	{
		bWaitingForClick = !FParse::Param(FCommandLine::Get(), TEXT("MICloudNoCard"));
		MICloudPrivate::Line(FString::Printf(TEXT("Viewer joined: click to play (%s)"), *MICloudPrivate::Stamp()));
	}
	else
	{
		// A guest on a session that is being watched already (E3DS's Share link): the card stays as it is, so it does
		// not cover a game that somebody is playing.
		MICloudPrivate::Line(FString::Printf(TEXT("Viewer joined (%d since the stream was last empty): no click card over the session in progress"), Viewers.Count));
	}
}

void UMICloudSubsystem::OnAllViewersLeft()
{
	Viewers.AllLeft();
	// The session's countdowns start from now. The pause and the release of everything the viewer held follow in this
	// very call, seconds before the first idle frame: the idle game never has a run going.
	SessionClock.AllLeft(FPlatformTime::Seconds());
	RoundTrip.Reset();
	++ViewerEventsHandled;
	LeftStick = FVector2D::ZeroVector;  // the pad went with its viewer
	StickNav.Reset();
	PadButtons.Reset();
	bRefusalLogged = false;  // the next session logs its own first refused command
	bConnectionLost = true;
	bWaitingForClick = false;
#if MI_WITH_PIXELSTREAMING2
	// A trigger that was pulled when its viewer went: Pixel Streaming sends a trigger's last value to the game again
	// on every frame until a zero arrives (InputHandler.cpp, bKeepUnlessZero), and none comes from a viewer who is
	// gone: the fire or the aim would stay on for the rest of the process. Give every pad it knows its zeros (the
	// sticks too). The pads themselves stay known: a page that reconnects may go on using the id it was given.
	if (const TSharedPtr<IPixelStreaming2InputHandler> Handler = MICloudPrivate::StreamInput())
	{
		const FKey Axes[] = {EKeys::Gamepad_LeftTriggerAxis, EKeys::Gamepad_RightTriggerAxis, EKeys::Gamepad_LeftX, EKeys::Gamepad_LeftY, EKeys::Gamepad_RightX, EKeys::Gamepad_RightY};
		for (uint8 Pad = 0; Pad < 8; ++Pad)
		{
			for (const FKey& Axis : Axes)
			{
				Handler->OnControllerAnalog(Pad, Axis, 0.0);  // false for an id it does not know
			}
		}
	}
#endif
	const UGameInstance* GI = GetGameInstance();
	ReleaseForLeave(MICloudPrivate::Game(GI), GI ? Cast<AMIPlayerController>(GI->GetFirstLocalPlayerController()) : nullptr);
	MICloudPrivate::Line(FString::Printf(TEXT("Connection lost: the game is paused until a viewer joins, and what the viewer held is let go (%s)"), *MICloudPrivate::Stamp()));
}

void UMICloudSubsystem::EnsureOverlay()
{
	UGameViewportClient* VC = GetGameInstance() ? GetGameInstance()->GetGameViewportClient() : nullptr;
	if (!VC || !FSlateApplication::IsInitialized())
	{
		return;
	}
	if (!Input.IsValid())
	{
		Input = MakeShared<FMICloudInput>(this);
		FSlateApplication::Get().RegisterInputPreProcessor(Input, 0);
	}
	// A map load clears the viewport's widgets: put the overlay back when it has lost its parent.
	if (OverlayViewport.Get() != VC || !Overlay.IsValid() || !Overlay->GetParentWidget().IsValid())
	{
		if (!Overlay.IsValid())
		{
			Overlay = SNew(SMICloudOverlay, this);
		}
		VC->AddViewportWidgetContent(Overlay.ToSharedRef(), 10000);
		OverlayViewport = VC;
	}
}

void UMICloudSubsystem::EnsureVideoProducer()
{
#if MI_WITH_PIXELSTREAMING2
	// In a packaged game the plugin makes its default streamer before Slate is up, and the back-buffer video source
	// refuses to exist then (VideoProducerBackBuffer.cpp: "if (!FSlateApplication::IsInitialized()) return nullptr"):
	// the stream carries sound and input but no picture. Give the streamer its source once Slate is there.
	if (bVideoChecked || !IPixelStreaming2Module::IsAvailable() || !FSlateApplication::IsInitialized())
	{
		return;
	}
	IPixelStreaming2Module& Module = IPixelStreaming2Module::Get();
	if (!Module.IsReady())
	{
		return;
	}
	bVideoChecked = true;
	if (TSharedPtr<IPixelStreaming2Streamer> Streamer = Module.FindStreamer(Module.GetDefaultStreamerID()))
	{
		if (!Streamer->GetVideoProducer().IsValid())
		{
			Streamer->SetVideoProducer(UE::PixelStreaming2::CreateVideoProducerBackBuffer());
			MICloudPrivate::Line(FString::Printf(TEXT("Pixel Streaming: the default streamer had no video source; it streams the back buffer now")));
		}
		else
		{
			MICloudPrivate::Line(FString::Printf(TEXT("Pixel Streaming: the default streamer has its video source")));
		}
		if (TSharedPtr<IPixelStreaming2VideoProducer> Producer = Streamer->GetVideoProducer().Pin())
		{
			Producer->OnFramePushed.AddLambda([](const IPixelCaptureInputFrame&) { ++MICloudPrivate::FramesPushed; });
		}
		FSlateApplication::Get().GetRenderer()->OnBackBufferReadyToPresent().AddLambda([](SWindow&, ISlateViewportProvider&) { ++MICloudPrivate::BackBuffers; });
	}
#endif
}

void UMICloudSubsystem::EnsureMouse()
{
	AMIPlayerController* PC = GetGameInstance() ? Cast<AMIPlayerController>(GetGameInstance()->GetFirstLocalPlayerController()) : nullptr;
	if (PC && !PC->UsesStreamMouse())
	{
		PC->SetStreamMouse(GetMouseShape());
	}
}

void UMICloudSubsystem::EnsureStartSize()
{
	if (bStartSizeChecked)
	{
		return;
	}
	const UGameViewportClient* VC = GetGameInstance() ? GetGameInstance()->GetGameViewportClient() : nullptr;
	const FIntPoint Launch = VC && VC->Viewport ? VC->Viewport->GetSizeXY() : FIntPoint(0, 0);
	if (Launch.X <= 0 || Launch.Y <= 0)
	{
		return;  // no viewport yet: next tick
	}
	bStartSizeChecked = true;
	if (SizeRequests > 0)
	{
		return;  // a viewer's size request came first and was fitted already (OnViewerSize)
	}
	const bool bAsGiven = FParse::Param(FCommandLine::Get(), TEXT("MIStartSizeAsGiven"));
	FIntPoint Size(0, 0);
	double Shown = 1.0;
	if (!FMICloudSize::FitStart(Launch, bAsGiven, Size, Shown))
	{
		MICloudPrivate::Line(FString::Printf(TEXT("Start size %d x %d: drawn as it is%s"), Launch.X, Launch.Y,
			bAsGiven ? TEXT(" (-MIStartSizeAsGiven)") : TEXT("")));
		return;
	}
	if (GEngine)
	{
		GEngine->Exec(GetGameInstance()->GetWorld(), *FString::Printf(TEXT("r.SetRes %dx%d"), Size.X, Size.Y));
	}
	// As for a viewer's request: the page shows the picture Shown times wider than it is drawn, and the mouse keeps the
	// speed it had at the launch size.
	MouseShown = Shown;
	if (AMIPlayerController* PC = Cast<AMIPlayerController>(GetGameInstance()->GetFirstLocalPlayerController()))
	{
		PC->SetStreamMouse(GetMouseShape());
	}
	MICloudPrivate::Line(FString::Printf(TEXT("Start size %d x %d: drawn and streamed at %d x %d (the largest size of that shape the game draws; -MIStartSizeAsGiven keeps the launch size); mouse look %.4f browser pixels per count"),
		Launch.X, Launch.Y, Size.X, Size.Y, GetMouseShape().Scale));
}

bool UMICloudSubsystem::OnMouseEvent(const FVector2D& Delta)
{
	if (!bStreamed || Delta.IsZero())
	{
		return false;
	}
	AMIPlayerController* PC = GetGameInstance() ? Cast<AMIPlayerController>(GetGameInstance()->GetFirstLocalPlayerController()) : nullptr;
	if (!PC || !PC->UsesStreamMouse())
	{
		return false;
	}
	return !PC->StreamMouseEvent(Delta);  // a spike is eaten here: neither the look nor a widget sees it
}

bool UMICloudSubsystem::OnKeyDown(const FKey& Key, bool bRepeat)
{
	if (!bStreamed)
	{
		return false;
	}
	// Of one hold of a gamepad button only the first message goes on, marked as a repeat or not (FMIPadButtons).
	if (Key.IsGamepadKey() && !PadButtons.Press(Key))
	{
		++PadRepeatsDropped;
		return true;
	}
	// A pad that is attached to this machine has its stick keys made by the platform: ours would double them.
	if (!bMakingStickKeys && (Key == EKeys::Gamepad_LeftStick_Up || Key == EKeys::Gamepad_LeftStick_Down
		|| Key == EKeys::Gamepad_LeftStick_Left || Key == EKeys::Gamepad_LeftStick_Right))
	{
		bPlatformStickKeys = true;
	}
	return false;
}

void UMICloudSubsystem::OnAnalog(const FKey& Key, float Value, FPlatformUserId User, FInputDeviceId Device)
{
	if (Key == EKeys::Gamepad_LeftX || Key == EKeys::Gamepad_LeftY)
	{
		(Key == EKeys::Gamepad_LeftX ? LeftStick.X : LeftStick.Y) = FMath::IsFinite(Value) ? Value : 0.f;
		StickUser = User;
		StickDevice = Device;
	}
}

void UMICloudSubsystem::TickStickMenu(float DeltaTime)
{
	if (!FSlateApplication::IsInitialized())
	{
		return;
	}
	FSlateApplication& Slate = FSlateApplication::Get();
	TGuardValue<bool> Making(bMakingStickKeys, true);
	// Each step is one press, held for a frame.
	for (const FName& Key : StickKeysDown)
	{
		Slate.OnControllerButtonReleased(Key, StickUser, StickDevice, false);
	}
	StickKeysDown.Reset();
	const AMIPlayerController* PC = GetGameInstance() ? Cast<AMIPlayerController>(GetGameInstance()->GetFirstLocalPlayerController()) : nullptr;
	if (!bStreamed || bPlatformStickKeys || Viewers.Count == 0 || (PC && PC->IsInLivePlay()))
	{
		StickNav.Reset();  // in play the stick walks; a stick still pushed when a card opens acts on it (as in the web game)
		return;
	}
	const FIntPoint Step = StickNav.Step(LeftStick, DeltaTime);
	const auto Press = [this, &Slate](const FName& Key)
	{
		Slate.OnControllerButtonPressed(Key, StickUser, StickDevice, false);
		StickKeysDown.Add(Key);
		++StickKeysMade;
	};
	if (Step.Y != 0)
	{
		Press(Step.Y < 0 ? FGamepadKeyNames::LeftStickUp : FGamepadKeyNames::LeftStickDown);
	}
	if (Step.X != 0)
	{
		Press(Step.X < 0 ? FGamepadKeyNames::LeftStickLeft : FGamepadKeyNames::LeftStickRight);
	}
}

void UMICloudSubsystem::GuardViewerInput()
{
#if MI_WITH_PIXELSTREAMING2
	// Pixel Streaming 2 runs a viewer's {"ConsoleCommand": "..."} through GEngine->Exec when the host allows viewer
	// commands (RTCInputHandler.cpp PopulateDefaultCommandHandlers), and E3DS always passes
	// -AllowPixelStreamingCommands. IPixelStreaming2InputHandler::SetCommandHandler replaces a handler by name: ours
	// keeps Pixel Streaming's two conditions and adds the allowlist. The encoder and bitrate command handlers are
	// separate names and stay as they are.
	if (bCommandsGuarded)
	{
		return;
	}
	const TSharedPtr<IPixelStreaming2InputHandler> Handler = MICloudPrivate::StreamInput();
	if (!Handler.IsValid())
	{
		return;
	}
	bCommandsGuarded = true;
	TWeakObjectPtr<UMICloudSubsystem> Weak(this);
	TWeakPtr<IPixelStreaming2InputHandler> WeakHandler = Handler;
	// A double click. A browser sends mousedown, mouseup, mousedown, mouseup and then dblclick, and the player page
	// passes the last one on as "MouseDouble". Unreal takes that for a third press (Slate adds the button to its
	// pressed buttons; the game viewport sends IE_DoubleClick, which the player's input counts as a press), and no
	// release follows it: E3DS's page sends none (Epic's own page does since its version 0.3.0, whose change log
	// describes the stuck button). On E3DS two quick clicks therefore left the fire button held: an automatic gun kept
	// firing until the next click was let go, and that click fired nothing. Both clicks have arrived as presses and
	// releases already, so the message is dropped; with a page that does send a release after it, that release finds
	// the button up. RegisterMessageHandler replaces the plugin's handler (InputHandler.cpp: DispatchTable.Add). The
	// desktop's mouse does not come this way.
	Handler->RegisterMessageHandler(TEXT("MouseDouble"), [Weak](FString, FMemoryReader)
	{
		if (UMICloudSubsystem* S = Weak.Get())
		{
			++S->DoubleClicksDropped;
		}
	});
	// A viewer who stops looking at the run (SMOOTH.md B5). The web game pauses on blur and on a hidden tab; a stream
	// gave the game no such moment, so a player who pressed Esc or went to another window left the run going and was
	// shot meanwhile. E3DS's player (e3dsCore.min_ns_dark.js, read 2026-11-26) sends MouseLeave when the pointer leaves
	// the picture (the mouseleave of the video's parent; with the locked mouse that only happens once the lock has
	// ended) and nothing else when the lock ends but a key-up for each held key. The page around it hears of the
	// stream's focus (streamFocusLost) and of a hidden tab, and can tell the game with {cmd: 'sendToUe4', value:
	// {murderinc: 'away'}}: E3DS's player passes the value on as a UIInteraction descriptor. Both handlers stay the
	// plugin's (they run first, with the message as it came); ours only adds the pause. The MouseLeave that Pixel
	// Streaming sends itself when a connection closes has no sender id: the connection's own end pauses the run then.
	{
		const IPixelStreaming2InputHandler::MessageHandlerFn PluginLeave = Handler->FindMessageHandler(TEXT("MouseLeave"));
		Handler->RegisterMessageHandler(TEXT("MouseLeave"), [Weak, WeakHandler, PluginLeave](FString SourceId, FMemoryReader)
		{
			if (PluginLeave)
			{
				const TArray<uint8> None;
				PluginLeave(SourceId, FMemoryReader(None));
			}
			const TSharedPtr<IPixelStreaming2InputHandler> H = WeakHandler.Pin();
			UMICloudSubsystem* S = Weak.Get();
			if (S && H.IsValid() && !SourceId.IsEmpty() && H->IsElevated(SourceId))
			{
				S->OnViewerAway(TEXT("the pointer left the picture"));
			}
		});
		const IPixelStreaming2InputHandler::MessageHandlerFn PluginUi = Handler->FindMessageHandler(TEXT("UIInteraction"));
		Handler->RegisterMessageHandler(TEXT("UIInteraction"), [Weak, WeakHandler, PluginUi](FString SourceId, FMemoryReader Ar)
		{
			// The message as it came, for the plugin's handler, then the descriptor as that handler reads it
			// (RTCInputHandler.cpp HandleOnUIInteraction): a 16-bit count of UTF-16 code units, then the units.
			TArray<uint8> Bytes;
			Bytes.SetNumUninitialized((int32)FMath::Clamp<int64>(Ar.TotalSize(), 0, 1 << 20));
			if (Bytes.Num() > 0)
			{
				Ar.Serialize(Bytes.GetData(), Bytes.Num());
			}
			if (PluginUi)
			{
				PluginUi(SourceId, FMemoryReader(Bytes));
			}
			if (!IsAwayMessage(Bytes))
			{
				return;
			}
			const TSharedPtr<IPixelStreaming2InputHandler> H = WeakHandler.Pin();
			UMICloudSubsystem* S = Weak.Get();
			if (S && H.IsValid() && H->IsElevated(SourceId))
			{
				S->OnViewerAway(TEXT("the page says the player is away"));
			}
		});
	}
	// The size request (FMICloudSize). Pixel Streaming's handler asks only whether the sender may control the stream
	// (RTCInputHandler.cpp: no AllowPixelStreamingCommands there); ours asks the same.
	Handler->SetCommandHandler(TEXT("Resolution.Width"), [Weak, WeakHandler](FString SourceId, FString Descriptor, FString Width)
	{
		const TSharedPtr<IPixelStreaming2InputHandler> H = WeakHandler.Pin();
		TSharedPtr<FJsonObject> Json;
		double Height = 0.0;
		if (!H.IsValid() || !H->IsElevated(SourceId) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Descriptor), Json)
			|| !Json.IsValid() || !Json->TryGetNumberField(TEXT("Resolution.Height"), Height))
		{
			return;
		}
		if (UMICloudSubsystem* S = Weak.Get())
		{
			S->OnViewerSize(FCString::Atoi(*Width), FMath::IsFinite(Height) ? (int32)FMath::Clamp(Height, 0.0, 1e6) : 0);
		}
	});
	Handler->SetCommandHandler(TEXT("ConsoleCommand"), [Weak, WeakHandler](FString SourceId, FString Descriptor, FString Command)
	{
		static IConsoleVariable* Allow = IConsoleManager::Get().FindConsoleVariable(TEXT("PixelStreaming2.AllowPixelStreamingCommands"));
		const TSharedPtr<IPixelStreaming2InputHandler> H = WeakHandler.Pin();
		if (!Allow || !Allow->GetBool() || !H.IsValid() || !H->IsElevated(SourceId))
		{
			return;
		}
		if (UMICloudSubsystem* S = Weak.Get())
		{
			S->OnViewerCommand(Command);
		}
	});
	// The plugin's own quality commands (a Command message, not a console command: Epic's front end sends these) set its
	// quality variables from the QP, rounded; the range of FMIEncoderRange goes through ours instead, so that no path
	// leaves the encoder with the one QP the page asked for (-MIQpExact: the same numbers, no range).
	for (const bool bMin : {true, false})
	{
		Handler->SetCommandHandler(bMin ? TEXT("Encoder.MinQP") : TEXT("Encoder.MaxQP"), [Weak, WeakHandler, bMin](FString SourceId, FString Descriptor, FString Value)
		{
			const TSharedPtr<IPixelStreaming2InputHandler> H = WeakHandler.Pin();
			if (!H.IsValid() || !H->IsElevated(SourceId) || Value.IsEmpty() || !Value.IsNumeric())
			{
				return;
			}
			if (UMICloudSubsystem* S = Weak.Get())
			{
				S->SetWantedQp(bMin, FMath::Clamp(FMath::RoundToInt32(FCString::Atod(*Value)), 0, FMIEncoderRange::TopQp), TEXT("the page's Encoder command"));
			}
		});
	}
	MICloudPrivate::Line(FString::Printf(TEXT("Viewer console commands: only these variables can be read or set, anything else is refused: %s"), *MITuning::AllowedList()));
	MICloudPrivate::Line(FString::Printf(TEXT("Viewer input: a size request is taken from %d x %d up and drawn within %d x %d; a double click counts as its two clicks; the pointer leaving the picture or the page's {\"murderinc\":\"away\"} pauses a run"),
		FMICloudSize::MinWidth, FMICloudSize::MinHeight, FMICloudSize::MaxWidth, FMICloudSize::MaxHeight));
#endif
}

void UMICloudSubsystem::OnViewerSize(int32 Width, int32 Height)
{
	FIntPoint Size(0, 0);
	double Shown = 1.0;
	if (!FMICloudSize::Fit(Width, Height, Size, Shown))
	{
		if (++SizeRequestsIgnored <= 3)
		{
			MICloudPrivate::Line(FString::Printf(TEXT("Viewer's size request %d x %d ignored (below %d x %d)"), Width, Height, FMICloudSize::MinWidth, FMICloudSize::MinHeight));
		}
		return;
	}
	++SizeRequests;
	SizeWait.Request(Size, Shown, FIntPoint(Width, Height), FPlatformTime::Seconds());
}

void UMICloudSubsystem::TickViewerSize()
{
	if (!SizeWait.TakeDue(FPlatformTime::Seconds()))
	{
		return;
	}
	const FIntPoint Size = SizeWait.Size;
	const double Shown = SizeWait.Shown;
	const int32 Width = SizeWait.Asked.X, Height = SizeWait.Asked.Y;
	FIntPoint Now(0, 0);
	if (const UGameViewportClient* VC = GetGameInstance() ? GetGameInstance()->GetGameViewportClient() : nullptr; VC && VC->Viewport)
	{
		Now = VC->Viewport->GetSizeXY();
	}
	if (Size != Now && GEngine)
	{
		GEngine->Exec(GetGameInstance() ? GetGameInstance()->GetWorld() : nullptr, *FString::Printf(TEXT("r.SetRes %dx%d"), Size.X, Size.Y));
	}
	// The mouse keeps its speed: the page shows the picture Shown times wider than it is drawn, and Pixel Streaming's
	// counts are counts of the drawn picture.
	const bool bMouseChanged = !FMath::IsNearlyEqual(Shown, MouseShown, 1e-6);
	MouseShown = Shown;
	if (AMIPlayerController* PC = GetGameInstance() ? Cast<AMIPlayerController>(GetGameInstance()->GetFirstLocalPlayerController()) : nullptr; PC && bMouseChanged)
	{
		PC->SetStreamMouse(GetMouseShape());
	}
	if (SizeRequests <= 10 || bMouseChanged)
	{
		MICloudPrivate::Line(FString::Printf(TEXT("Viewer's size request %d x %d: drawn at %d x %d%s; mouse look %.4f browser pixels per count"), Width, Height, Size.X, Size.Y,
			Size.X != Width || Size.Y != Height ? TEXT(" (the largest size of that shape the game draws, in even numbers)") : TEXT(""), GetMouseShape().Scale));
	}
}

void UMICloudSubsystem::OnViewerCommand(const FString& Command)
{
	// E3DS's page sends "PixelStreaming.Encoder.MinQP 34" and MaxQP at the start of every session (and again and again):
	// they match no console variable of the plugin, so they did nothing; now they set the centre of the encoder's range.
	if (OnEncoderCommand(Command))
	{
		++CommandsRun;
		return;
	}
	FString Run;
	if (IsViewerCommandAllowed(Command, &Run))
	{
		++CommandsRun;
		if (GEngine)
		{
			GEngine->Exec(GetGameInstance() ? GetGameInstance()->GetWorld() : nullptr, *Run);
		}
		if (CommandsRun <= 20)
		{
			MICloudPrivate::Line(FString::Printf(TEXT("Viewer console command: %s"), *Run));
		}
		return;
	}
	++CommandsRefused;
	if (!bRefusalLogged)
	{
		bRefusalLogged = true;
		FString Shown = Command.Left(120);
		for (TCHAR& Ch : Shown)
		{
			if (Ch < TEXT(' ')) Ch = TEXT(' ');
		}
		MICloudPrivate::Line(FString::Printf(TEXT("Viewer console command refused: \"%s\" (not one of the variables a viewer may set, or out of its range; further refusals of this session are counted, not logged)"), *Shown));
	}
}

// ---- the session: idle, quit (Cloud/MISession.h) ---------------------------------------------------------------------

void UMICloudSubsystem::StartSession()
{
	if (bSessionStarted)
	{
		return;
	}
	bSessionStarted = true;
	SessionClock.MarkReady(FPlatformTime::Seconds());
	const TCHAR* Cmd = FCommandLine::Get();
	// The launch options reach the same console variables -MICVars= and the console reach.
	MICloudPrivate::ApplyLaunchOption(Cmd, TEXT("MIIdleFps="), TEXT("MI.Cloud.IdleFps"));
	MICloudPrivate::ApplyLaunchOption(Cmd, TEXT("MIIdleAfter="), TEXT("MI.Cloud.IdleAfter"));
	MICloudPrivate::ApplyLaunchOption(Cmd, TEXT("MIExitAfterEmpty="), TEXT("MI.Cloud.ExitAfterEmpty"));
	MICloudPrivate::ApplyLaunchOption(Cmd, TEXT("MIExitIfNoViewer="), TEXT("MI.Cloud.ExitIfNoViewer"));
	MICloudPrivate::ApplyLaunchOption(Cmd, TEXT("MIQpBelow="), TEXT("MI.Cloud.QpBelow"));
	MICloudPrivate::ApplyLaunchOption(Cmd, TEXT("MIQpAbove="), TEXT("MI.Cloud.QpAbove"));
	if (FParse::Param(Cmd, TEXT("MIKeepAlive")))
	{
		MICloudPrivate::GKeepAlive = 1;
	}
	if (FParse::Param(Cmd, TEXT("MIQpExact")))
	{
		MICloudPrivate::GQpExact = 1;
	}
	// The launcher passes its own process id: a game started by hand or by a test script has none, and nothing is watched.
	int32 Pid = 0;
	if (FParse::Value(Cmd, TEXT("MILauncherPid="), Pid) && Pid > 1)
	{
		LauncherWatch.Start(Pid, FPlatformTime::Seconds());
	}
	const FMISession::FOptions O = ReadSessionOptions(true);
	LauncherGoneAfter = O.LauncherGoneAfter;
	MICloudPrivate::Line(FString::Printf(TEXT("Session: %s"),
		O.bKeepAlive ? TEXT("-MIKeepAlive: the game keeps drawing and never quits by itself")
			: *FString::Printf(TEXT("no viewer for %.1f s: idle at %s; the last viewer gone for %s: quit; no viewer in %s after the start: quit; launcher %s (MI.Cloud.IdleAfter, IdleFps, ExitAfterEmpty, ExitIfNoViewer)"),
				O.IdleAfter, O.IdleFps > 0 ? *FString::Printf(TEXT("%d frames a second"), O.IdleFps) : TEXT("no cap (off)"),
				O.ExitAfterEmpty > 0.0 ? *FString::Printf(TEXT("%.0f s"), O.ExitAfterEmpty) : TEXT("never"),
				O.ExitIfNoViewer > 0.0 ? *FString::Printf(TEXT("%.0f s"), O.ExitIfNoViewer) : TEXT("never"),
				LauncherWatch.IsWatching() ? *FString::Printf(TEXT("pid %d watched: gone for %.0f s: quit"), LauncherWatch.GetPid(), O.LauncherGoneAfter) : TEXT("not watched (no -MILauncherPid)"))));
	// The encoder: the numbers the host started the game with are the centre of its range.
	FMIEncoderRange::ReadLaunchOptions(Cmd, WantedMinQp, WantedMaxQp);
	ApplyEncoderRange(TEXT("the launch options"));
}

void UMICloudSubsystem::TickSession()
{
	if (!bStreamed || !bSessionStarted || bExitRequested || IsEngineExitRequested())
	{
		return;
	}
	const double Now = FPlatformTime::Seconds();
	// The launcher: looked at every 2 s, and a launcher that was never seen alive is not watched (FMILauncherWatch).
	if (LauncherWatch.IsDue(Now))
	{
		const bool bWasGone = LauncherWatch.GetGoneFor(Now) >= 0.0;
		const FMILauncherWatch::EProbe Answer = MIProbeProcess(LauncherWatch.GetPid(), LauncherStartTime);
		LauncherWatch.Feed(Answer, Now);
		if (LauncherWatch.IsDisarmed())
		{
			MICloudPrivate::Line(FString::Printf(TEXT("Launcher: process %d (-MILauncherPid) is not there at the start of the game: it is not watched"), LauncherWatch.GetPid()));
		}
		else if (!bWasGone && LauncherWatch.GetGoneFor(Now) >= 0.0)
		{
			MICloudPrivate::Line(FString::Printf(TEXT("Launcher: process %d is gone; the game quits if it stays gone for %.0f s"), LauncherWatch.GetPid(), LauncherGoneAfter));
		}
	}
	const FMISession::FOptions O = ReadSessionOptions(true);
	const FMISession::FState State = SessionClock.Snapshot(Now, LauncherWatch.GetGoneFor(Now));
	FMISession::FDecision D = FMISession::Decide(O, State);
	// A viewer event that the game thread has not handled yet (a join that woke the idle game): the count is not true
	// yet, so the game neither goes back to sleep nor quits on it.
	if (MICloudPrivate::GViewerEvents.load() != ViewerEventsHandled && D.Action != FMISession::EAction::Keep)
	{
		D.Action = FMISession::EAction::Keep;
		D.Why = FMISession::EWhy::ViewerPresent;
	}
	switch (D.Action)
	{
	case FMISession::EAction::Exit:
		RequestSessionExit(FMISession::Describe(D, O, State));
		return;
	case FMISession::EAction::Idle:
		if (!bIdle)
		{
			EnterIdle(FMISession::Describe(D, O, State));
		}
		SleepIdle(O.IdleFps);
		return;
	case FMISession::EAction::Keep:
		break;
	}
	if (bIdle)
	{
		LeaveIdle(TEXT("the session is live again"));
	}
	LastWhy = D.Why;
}

void UMICloudSubsystem::EnterIdle(const FString& Why)
{
	bIdle = true;
	IdleSince = FPlatformTime::Seconds();
	IdleFrameAt = IdleSince;
	IdleFrames = 0;
	// The picture at its smallest while nobody looks at it (the cloud profile's dynamic resolution runs between
	// r.DynamicRes.MinScreenPercentage and MaxScreenPercentage; a value somebody set by hand stays).
	static IConsoleVariable* Min = IConsoleManager::Get().FindConsoleVariable(TEXT("r.DynamicRes.MinScreenPercentage"));
	static IConsoleVariable* Max = IConsoleManager::Get().FindConsoleVariable(TEXT("r.DynamicRes.MaxScreenPercentage"));
	if (Min && Max && !bDynamicResClamped)
	{
		SavedDynamicResMax = Max->GetString();
		bDynamicResClamped = MICloudPrivate::SetAsProfile(TEXT("r.DynamicRes.MaxScreenPercentage"), Min->GetString());
	}
	MICloudPrivate::Line(FString::Printf(TEXT("Nobody is watching: %s (%s)"), *Why, *MICloudPrivate::Stamp()));
}

void UMICloudSubsystem::LeaveIdle(const TCHAR* Why)
{
	if (!bIdle)
	{
		return;
	}
	bIdle = false;
	if (bDynamicResClamped)
	{
		MICloudPrivate::SetAsProfile(TEXT("r.DynamicRes.MaxScreenPercentage"), SavedDynamicResMax);
		bDynamicResClamped = false;
	}
	// The pacing's half second counts from now: the idle frames said nothing about what a frame costs.
	GovLast = FPlatformTime::Seconds();
	GovGpuSum = 0.0;
	GovFrames = 0;
	IdleFrameAt = 0.0;
	MICloudPrivate::Line(FString::Printf(TEXT("Back at full speed (%s) after %.1f s and %d idle frames (%s)"), Why, FPlatformTime::Seconds() - IdleSince, IdleFrames, *MICloudPrivate::Stamp()));
}

void UMICloudSubsystem::SleepIdle(int32 Fps)
{
	// The end of the frame (the core ticker runs after the frame's work): wait until the next idle frame is due. In steps
	// of 10 ms, at the end of each of which the game thread's waiting tasks are run: Pixel Streaming reports a viewer's
	// arrival as one of them, and without this the report would wait for the end of the idle frame (up to 500 ms at 2
	// frames a second). The same tasks run at the start of the next frame; here they run a little earlier. A viewer's
	// arrival (the count moves) or an exit request ends the wait.
	const double Interval = 1.0 / (double)FMath::Max(1, Fps);
	const int32 Seen = MICloudPrivate::GViewerEvents.load();
	const double Until = IdleFrameAt + Interval;
	for (double Now = FPlatformTime::Seconds(); Now < Until; Now = FPlatformTime::Seconds())
	{
		FTaskGraphInterface::Get().ProcessThreadUntilIdle(ENamedThreads::GameThread);
		if (IsEngineExitRequested() || MICloudPrivate::GViewerEvents.load() != Seen)
		{
			break;
		}
		FPlatformProcess::SleepNoStats((float)FMath::Min(0.01, Until - Now));
	}
	if (bIdle)  // a join handled in the loop has ended the idle already
	{
		IdleFrameAt = FPlatformTime::Seconds();
		++IdleFrames;
	}
}

void UMICloudSubsystem::RequestSessionExit(const FString& Why)
{
	if (bExitRequested)
	{
		return;
	}
	bExitRequested = true;
	if (bIdle)
	{
		LeaveIdle(TEXT("the session is over"));
	}
	MICloudPrivate::Line(FString::Printf(TEXT("Session over: %s. The game quits now (exit code 0). (%s)"), *Why, *MICloudPrivate::Stamp()));
	MICloudPrivate::ArmShutdownCrashNet();
	FPlatformMisc::RequestExit(false);
	MICloudPrivate::ArmShutdownWatchdog(30.0);
}

// ---- the encoder's range (Cloud/MIStreamQuality.h) ----------------------------------------------------------------------

void UMICloudSubsystem::SetWantedQp(bool bMin, int32 Qp, const TCHAR* Source)
{
	(bMin ? WantedMinQp : WantedMaxQp) = FMath::Clamp(Qp, 0, FMIEncoderRange::TopQp);
	ApplyEncoderRange(Source);
}

bool UMICloudSubsystem::OnEncoderCommand(const FString& Command)
{
	int32 Qp = 0;
	const FMIEncoderRange::ECommand Kind = FMIEncoderRange::ParseCommand(Command, Qp);
	if (Kind == FMIEncoderRange::ECommand::None)
	{
		return false;
	}
	SetWantedQp(Kind == FMIEncoderRange::ECommand::MinQp, Qp, TEXT("the page's console command"));
	return true;
}

void UMICloudSubsystem::ApplyEncoderRange(const TCHAR* Source)
{
	if (WantedMinQp < 0 && WantedMaxQp < 0)
	{
		return;  // nothing was asked for: the plugin's own defaults (no limit on either end) stay
	}
	// The plugin's quality variables: the LOWEST QP is its MaxQuality and the HIGHEST its MinQuality. Not there (the
	// editor and the tests have no Pixel Streaming): nothing to set.
	static IConsoleVariable* MaxQuality = IConsoleManager::Get().FindConsoleVariable(TEXT("PixelStreaming2.Encoder.MaxQuality"));
	static IConsoleVariable* MinQuality = IConsoleManager::Get().FindConsoleVariable(TEXT("PixelStreaming2.Encoder.MinQuality"));
	if (!MaxQuality || !MinQuality)
	{
		return;
	}
	const FMIEncoderRange::FSettings Settings = ReadEncoderSettings();
	// One end given so far (the page sends the lowest and the highest as two commands): the range is worked out around
	// that number alone and only its own end is set.
	const int32 A = WantedMinQp >= 0 ? WantedMinQp : WantedMaxQp;
	const int32 B = WantedMaxQp >= 0 ? WantedMaxQp : WantedMinQp;
	const FMIEncoderRange::FRange R = FMIEncoderRange::Widen(A, B, Settings);
	FMIEncoderRange::FRange Now = AppliedRange;
	if (!bRangeApplied)
	{
		Now.MinQp = FMIEncoderRange::QpForQuality(MaxQuality->GetInt());
		Now.MaxQp = FMIEncoderRange::QpForQuality(MinQuality->GetInt());
	}
	if (WantedMinQp >= 0)
	{
		Now.MinQp = R.MinQp;
	}
	if (WantedMaxQp >= 0)
	{
		Now.MaxQp = R.MaxQp;
	}
	if (bRangeApplied && Now == AppliedRange)
	{
		return;  // E3DS's page sends the same two numbers again and again: set once, logged once
	}
	// ECVF_SetByCommandline: the priority Pixel Streaming gave these variables from the launch options, so that a later
	// handler of its own (SetWithCurrentPriority) does not find ours below it.
	MaxQuality->Set(FMIEncoderRange::QualityForQp(Now.MinQp), ECVF_SetByCommandline);
	MinQuality->Set(FMIEncoderRange::QualityForQp(Now.MaxQp), ECVF_SetByCommandline);
	bRangeApplied = true;
	AppliedRange = Now;
	MICloudPrivate::Line(FString::Printf(TEXT("Encoder quality, from %s: asked for QP %s%s%s; the encoder may use QP %d to %d (PixelStreaming2.Encoder.MaxQuality %d, MinQuality %d)%s"),
		Source, WantedMinQp >= 0 ? *FString::Printf(TEXT("%d at the lowest"), WantedMinQp) : TEXT(""), WantedMinQp >= 0 && WantedMaxQp >= 0 ? TEXT(", ") : TEXT(""),
		WantedMaxQp >= 0 ? *FString::Printf(TEXT("%d at the highest"), WantedMaxQp) : TEXT(""), Now.MinQp, Now.MaxQp,
		MaxQuality->GetInt(), MinQuality->GetInt(),
		Settings.bExact ? TEXT(" (-MIQpExact: no range)") : *FString::Printf(TEXT(" (MI.Cloud.QpBelow %d, QpAbove %d, floor %d, ceiling %d)"), Settings.Below, Settings.Above, Settings.Floor, Settings.Ceiling)));
}

bool UMICloudSubsystem::Tick(float DeltaTime)
{
#if !UE_BUILD_SHIPPING
	if (CrashTestAt > 0.0 && FPlatformTime::Seconds() >= CrashTestAt)
	{
		MICloudPrivate::Line(TEXT("Crash test: crashing now (null write)"));
		volatile int32* Null = nullptr;
		*Null = 1;
	}
#endif
	if (bStreamed)
	{
		EnsureOverlay();
		EnsureVideoProducer();
		EnsureStartSize();
		TickViewerSize();
		EnsureMouse();
		GuardViewerInput();
		TickPacing();
		WatchQualityFrame(DeltaTime);
	}
	if (ProbePeriod > 0.f)
	{
		Probe(DeltaTime);
	}
	TickSession();
	return true;
}

void UMICloudSubsystem::StartPacing()
{
	if (bPacingStarted)
	{
		return;
	}
	bPacingStarted = true;
	// One probe line every 30 s unless the launch option says otherwise (-MICloudProbe=0: none): the numbers of a
	// session are in its log without anybody having asked for them beforehand.
	if (!bProbeGiven)
	{
		ProbePeriod = 30.f;
	}
	// -MIFps=60|45|30 fixes the frame-rate target (the same as MI.Cloud.FpsTarget).
	int32 Fixed = 0;
	if (FParse::Value(FCommandLine::Get(), TEXT("MIFps="), Fixed) && Fixed > 0)
	{
		MICloudPrivate::GFpsTarget = FMIFrameRateGovernor::TargetFor(Fixed);
	}
	GovLast = FPlatformTime::Seconds();
	if (FApp::CanEverRender())
	{
		Pacer = MakeShared<FMIGpuPacer, ESPMode::ThreadSafe>();
		Pacer->MaxInFlight = MICloudPrivate::GFramesInFlight;
		Pacer->WaitLimitMs = MICloudPrivate::GGpuWaitLimitMs;
		Pacer->Start();
	}
	ApplyFrameRateTarget();
	bool bSmallest = true;
	const float Share = MICloudPrivate::PictureShare(bSmallest);
	MICloudPrivate::Line(FString::Printf(TEXT("Pacing: frame-rate target %d (%s), the GPU may owe %d frame(s) at the start of a frame (MI.Cloud.GpuFramesInFlight; pacer %s), dynamic resolution %s"),
		Governor.Target(), MICloudPrivate::GFpsTarget > 0 ? TEXT("fixed") : TEXT("60, 45 or 30 by the GPU's time"),
		MICloudPrivate::GFramesInFlight, Pacer.IsValid() && Pacer->IsRunning() ? TEXT("on") : TEXT("off: no renderer"),
		Share > 0.f ? TEXT("on") : TEXT("not on yet (it starts with the first frame if the cloud profile turns it on)")));
}

void UMICloudSubsystem::ApplyFrameRateTarget()
{
	// A t.MaxFPS set by hand (a launch option, the console, E3DS's console-commands field) stays: the stream and
	// dynamic resolution follow it. 0 or less is no cap: budget for 60.
	static IConsoleVariable* MaxFps = IConsoleManager::Get().FindConsoleVariable(TEXT("t.MaxFPS"));
	MICloudPrivate::SetAsProfile(TEXT("t.MaxFPS"), FString::FromInt(Governor.Target()));
	const float Cap = MaxFps ? MaxFps->GetFloat() : (float)Governor.Target();
	const float Rate = Cap >= 1.f ? FMath::Min(Cap, 60.f) : 60.f;
	// The stream's own frame rate is kept in step, for a session that turns Pixel Streaming's decoupled capture on
	// (its capture thread runs at this rate). With the capture coupled to the game's frames (the default) the stream
	// sends what the game draws, and this value does nothing on a running stream: Pixel Streaming reads it once, when
	// a viewer's video is set up, as the most frames a second it may send (EpicRtcStreamer.cpp, _maxFrameRate).
	MICloudPrivate::SetAsProfile(TEXT("PixelStreaming2.WebRTC.Fps"), FString::FromInt(FMath::RoundToInt32(Rate)));
	MICloudPrivate::SetAsProfile(TEXT("r.DynamicRes.FrameTimeBudget"), FString::SanitizeFloat(1000.0 / Rate));
}

void UMICloudSubsystem::TickPacing()
{
	if (!bPacingStarted)
	{
		return;
	}
	if (Pacer.IsValid())
	{
		Pacer->MaxInFlight = MICloudPrivate::GFramesInFlight;
		Pacer->WaitLimitMs = MICloudPrivate::GGpuWaitLimitMs;
		if (Pacer->GetPauses() > PacerPausesLogged && PacerPausesLogged < 5)
		{
			PacerPausesLogged = Pacer->GetPauses();
			MICloudPrivate::Line(FString::Printf(TEXT("Pacing: the GPU finished no frame during three waits in a row of %.0f ms (MI.Cloud.GpuWaitLimitMs): it stands still, or its fences are not signalled; the game runs unheld for %.0f s, then the pacer tries again (pause %d of this session%s)"),
				MICloudPrivate::GGpuWaitLimitMs, Pacer->PauseSeconds, PacerPausesLogged, PacerPausesLogged >= 5 ? TEXT("; further ones are not logged") : TEXT("")));
		}
	}
	if (bIdle)
	{
		// Nobody is watching: the idle frames say nothing about what a frame of play costs.
		GovLast = FPlatformTime::Seconds();
		GovGpuSum = 0.0;
		GovFrames = 0;
		return;
	}
	GovGpuSum += FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles(0));
	++GovFrames;
	const double Now = FPlatformTime::Seconds();
	const double Step = Now - GovLast;
	if (Step < 0.5)
	{
		return;
	}
	GovLast = Now;
	FMIFrameRateGovernor::FInput In;
	In.Seconds = Step;
	In.GpuMs = GovFrames > 0 ? GovGpuSum / GovFrames : 0.0;
	LastGpuMs = In.GpuMs;
	LastFps = GovFrames / Step;
	GovGpuSum = 0.0;
	GovFrames = 0;
	PictureShare = MICloudPrivate::PictureShare(In.bSmallestPicture);
	{
		// For the rise: what the GPU would need at the smallest picture (the higher rate is held with a smaller one).
		static IConsoleVariable* MinPicture = IConsoleManager::Get().FindConsoleVariable(TEXT("r.DynamicRes.MinScreenPercentage"));
		In.GpuMsSmallest = MITuning::GpuMsAtSmallest(In.GpuMs, PictureShare, (MinPicture ? MinPicture->GetFloat() : 50.f) / 100.0, MICloudPrivate::GFpsPixelPart);
	}
	if (Pacer.IsValid())
	{
		// Held back: the game thread spent more than a fifth of the time waiting for the GPU AND made fewer frames
		// than the target asks for (more than 8 % short). The wait alone is not it: while the rate is held, a wait
		// before the input is read only takes the place of the frame cap's sleep (measured: a steady 45.0 frames
		// a second, no frame late, with a fifth of the time waited: box run h-l20x).
		const FMIGpuPacer::FStats S = Pacer->Take(1);
		In.bHeldBack = S.WaitMs > 0.2 * Step * 1000.0 && LastFps < 0.92 * Governor.Target();
	}
	const AMIPlayerController* PC = GetGameInstance() ? Cast<AMIPlayerController>(GetGameInstance()->GetFirstLocalPlayerController()) : nullptr;
	In.bSafeMoment = !PC || !PC->IsInLivePlay();
	if (!In.bSafeMoment)
	{
		// For the pause card: the lowest frame rates of the last half minute of play. A stutter is the server when the
		// game's own number fell and the connection when only the stream's did (the sender drops frames to fit a thin
		// connection: measured, 5 to 7 a second while turning at 1.7 Mbit/s with the game at 60).
		const FVector2f Sample((float)LastFps, (float)StreamStat(TEXT("transmitFps")));
		if (PlayLows.Num() < 60)
		{
			PlayLows.Add(Sample);
		}
		else
		{
			PlayLows[PlayLowNext] = Sample;
			PlayLowNext = (PlayLowNext + 1) % 60;
		}
	}

	In.bHold = QualityHoldsFrameRate();
	Governor.HoldMax = MICloudPrivate::GFpsHoldMax;
	Governor.HoldOverShare = MICloudPrivate::GFpsHoldOver;
	Governor.OverShare = MICloudPrivate::GFpsDropOver;
	Governor.DropAfter = MICloudPrivate::GFpsDropAfter;
	Governor.UnderShare = MICloudPrivate::GFpsRaiseUnder;
	Governor.RaiseAfter = MICloudPrivate::GFpsRaiseAfter;

	// Fixed from outside: MI.Cloud.FpsTarget (or -MIFps=), or a t.MaxFPS that something stronger than the cloud
	// profile holds (-MICVars, the console, E3DS's console-commands field).
	static IConsoleVariable* MaxFps = IConsoleManager::Get().FindConsoleVariable(TEXT("t.MaxFPS"));
	const bool bByHand = MaxFps && (MaxFps->GetFlags() & ECVF_SetByMask) > ECVF_SetByDeviceProfile;
	const int32 By = bByHand ? 2 : MICloudPrivate::GFpsTarget > 0 ? 1 : 0;
	const int32 Fixed = By == 2 ? FMIFrameRateGovernor::TargetFor(FMath::RoundToInt32(MaxFps->GetFloat())) : By == 1 ? FMIFrameRateGovernor::TargetFor(MICloudPrivate::GFpsTarget) : 0;
	if (By != PinnedBy || (By != 0 && Fixed != Governor.Target()))
	{
		PinnedBy = By;
		Governor.Pin(Fixed);
		ApplyFrameRateTarget();
		MICloudPrivate::Line(By == 0 ? FString(TEXT("Frame-rate target: free again (60, 45 or 30 by the GPU's time)"))
			: FString::Printf(TEXT("Frame-rate target: fixed at %d by %s"), Governor.Target(),
				By == 2 ? *FString::Printf(TEXT("t.MaxFPS = %s, set by hand (a launch option or a console command)"), *MaxFps->GetString()) : TEXT("MI.Cloud.FpsTarget (launch option -MIFps=)")));
	}
	if (Governor.Update(In))
	{
		ApplyFrameRateTarget();
		MICloudPrivate::Line(FString::Printf(TEXT("Frame-rate target: %s"), *Governor.Why()));
	}
	else if (PinnedBy == 2)
	{
		ApplyFrameRateTarget();  // the stream and dynamic resolution follow a cap that is changed by hand
	}
	TickQuality(In);
	if (Now >= NumbersNext)
	{
		NumbersNext = Now + 1.0;
		MakeNumbersLine();
	}
}

void UMICloudSubsystem::StartQuality()
{
	if (bQualityStarted)
	{
		return;
	}
	bQualityStarted = true;
	const TCHAR* Cmd = FCommandLine::Get();
	MICloudPrivate::ApplyLaunchOption(Cmd, TEXT("MIQuality="), TEXT("MI.Cloud.QualityStep"));
	if (FParse::Param(Cmd, TEXT("MILadder")))
	{
		MICloudPrivate::GQualityLadder = 1;
	}
	if (FParse::Param(Cmd, TEXT("MINoLadder")))
	{
		MICloudPrivate::GQualityLadder = 0;
	}
	TArray<FString> Errors;
	QualitySteps = ReadQualityTable(&Errors);
#if !UE_BUILD_SHIPPING
	{
		// For the box's test folders, whose pak is older than the branch (a Saved Game.ini is not read by a packaged game: box run
		// probe3): the steps from a file, the QualitySteps= lines of DefaultGame.ini. Not in the Shipping game: a visitor's launch
		// option must never be able to choose the variables the game sets.
		FString TableFile;
		if (FParse::Value(Cmd, TEXT("MIQualityTable="), TableFile) && !TableFile.IsEmpty())
		{
			TArray<FString> Lines;
			if (FFileHelper::LoadFileToStringArray(Lines, *TableFile))
			{
				for (FString& Line : Lines)
				{
					Line.TrimStartAndEndInline();
					Line.RemoveFromStart(TEXT("+QualitySteps="));
				}
				Errors.Reset();
				QualitySteps = FMIQualityTable::Parse(Lines, &Errors);
				MICloudPrivate::Line(FString::Printf(TEXT("Quality ladder: %d step(s) read from %s (-MIQualityTable=, not in the Shipping game)"), QualitySteps.Num(), *TableFile));
			}
			else
			{
				MICloudPrivate::Line(FString::Printf(TEXT("Quality ladder: cannot read %s (-MIQualityTable=)"), *TableFile));
			}
		}
	}
#endif
	for (const FString& E : Errors)
	{
		MICloudPrivate::Line(FString::Printf(TEXT("Quality ladder: a line of [MICloud] QualitySteps cannot be used: %s"), *E));
	}
	// A variable this build does not have (a Shipping build leaves some out) is taken out of its step, and a step that is left
	// with none is taken out of the ladder: it would save nothing while the ladder counted its saving.
	TArray<FString> Cuts;
	QualitySteps = FMIQualityTable::Prune(QualitySteps, [](const FString& Name) { return IConsoleManager::Get().FindConsoleVariable(*Name) != nullptr; }, &Cuts);
	for (const FString& C : Cuts)
	{
		MICloudPrivate::Line(FString::Printf(TEXT("Quality ladder: %s"), *C));
	}
	// The steps were measured with SM5's shaders (no Nanite, no virtual shadow maps, software Lumen).
	FString LevelName;
	GetFeatureLevelName(GMaxRHIFeatureLevel, LevelName);
	if (QualitySteps.Num() > 0 && GMaxRHIFeatureLevel >= ERHIFeatureLevel::SM6 && MICloudPrivate::GQualitySm6 == 0)
	{
		MICloudPrivate::Line(FString::Printf(TEXT("Quality ladder: the game runs %s; the steps were measured with SM5 only, so there is no ladder here (MI.Cloud.QualitySm6 1 turns it on)"), *LevelName));
		QualitySteps.Reset();
	}
	// Which way each variable goes when the quality goes down (the signs of the table, else its first and last value).
	for (const FString& Name : FMIQualityTable::Names(QualitySteps))
	{
		QualityDirection.Add(Name, FMIQualityTable::Direction(QualitySteps, Name));
	}
	Ladder.Configure(QualitySteps);
	FString List;
	for (int32 I = 0; I < QualitySteps.Num(); ++I)
	{
		List += FString::Printf(TEXT("%s%d %s (saves about %.0f %%%s)"), I > 0 ? TEXT(", ") : TEXT(""), I + 1, *QualitySteps[I].Name, QualitySteps[I].Saves * 100.0,
			QualitySteps[I].bCalm ? TEXT(", only at a calm moment") : TEXT(""));
	}
	MICloudPrivate::Line(QualitySteps.Num() == 0 ? FString(TEXT("Quality ladder: no steps: full quality at every load"))
		: FString::Printf(TEXT("Quality ladder: %d step(s) on %s: %s; %s (MI.Cloud.QualityLadder, MI.Cloud.QualityStep; launch options -MILadder, -MINoLadder, -MIQuality=<n>)"), QualitySteps.Num(), *LevelName, *List,
			MICloudPrivate::GQualityLadder == 0 ? TEXT("OFF (the default until the gate has run it: -MILadder turns it on)") : MICloudPrivate::GQualityStep >= 0 ? *FString::Printf(TEXT("fixed at step %d"), MICloudPrivate::GQualityStep)
				: *FString::Printf(TEXT("down after %.0f s over %.0f %% of a 60 frames a second frame at the smallest picture, up after %.0f s of play with room to spare, %.0f s of warm-up when live play begins"),
					MICloudPrivate::GQualityDownAfter, MICloudPrivate::GQualityDownLoad * 100.0, MICloudPrivate::GQualityUpAfter, MICloudPrivate::GQualityWarmUp)));
}

void UMICloudSubsystem::SetQualityTableForTest(const TArray<FMIQualityStep>& Steps, bool bReachable)
{
	ReleaseQualityHolds();
	QualitySteps = Steps;
	QualityDirection.Reset();
	for (const FString& Name : FMIQualityTable::Names(QualitySteps))
	{
		QualityDirection.Add(Name, FMIQualityTable::Direction(QualitySteps, Name));
	}
	Ladder.Configure(QualitySteps);
	QualityApplied = 0;
	bQualityStarted = true;
	if (bReachable)
	{
		MICloudPrivate::GSelf = this;
	}
	else if (MICloudPrivate::GSelf == this)
	{
		MICloudPrivate::GSelf = nullptr;
	}
}

void UMICloudSubsystem::ApplyQualityStepForTest(int32 Step)
{
	Ladder.Pin(Step);
	ApplyQualityStep(Ladder.Step(), TEXT("a test"), Step > QualityApplied);
}

bool UMICloudSubsystem::QualityHoldsFrameRate() const
{
	return bQualityStarted && QualitySteps.Num() > 0 && MICloudPrivate::GQualityLadder != 0 && MICloudPrivate::GQualityStep < 0 && MICloudPrivate::GFpsHoldMax > 0.f && Ladder.CanStepDown();
}

void UMICloudSubsystem::TickQuality(const FMIFrameRateGovernor::FInput& In)
{
	if (!bQualityStarted || QualitySteps.Num() == 0)
	{
		return;
	}
	Ladder.DownLoad = FMath::Clamp((double)MICloudPrivate::GQualityDownLoad, 0.3, 3.0);
	Ladder.UpLoad = FMath::Clamp((double)MICloudPrivate::GQualityUpLoad, 0.1, Ladder.DownLoad);
	Ladder.DownAfter = FMath::Max(0.5, (double)MICloudPrivate::GQualityDownAfter);
	Ladder.UpAfter = FMath::Max(1.0, (double)MICloudPrivate::GQualityUpAfter);
	Ladder.MinGap = FMath::Max(0.0, (double)MICloudPrivate::GQualityMinGap);
	const bool bOn = MICloudPrivate::GQualityLadder != 0;
	if (Ladder.IsEnabled() != bOn)
	{
		Ladder.SetEnabled(bOn);
		MICloudPrivate::Line(bOn ? FString(TEXT("Quality ladder: on")) : FString(TEXT("Quality ladder: off (MI.Cloud.QualityLadder 0, -MINoLadder or no -MILadder): full quality")));
	}
	const int32 Pin = bOn ? MICloudPrivate::GQualityStep : -1;
	if (Pin >= 0 && (!Ladder.IsPinned() || Ladder.Step() != FMath::Min(Pin, QualitySteps.Num())))
	{
		Ladder.Pin(Pin);
		MICloudPrivate::Line(FString::Printf(TEXT("Quality ladder: fixed at step %d of %d (MI.Cloud.QualityStep or -MIQuality=)"), Ladder.Step(), QualitySteps.Num()));
	}
	else if (Pin < 0 && Ladder.IsPinned())
	{
		Ladder.Pin(-1);
		MICloudPrivate::Line(FString::Printf(TEXT("Quality ladder: free again (step %d)"), Ladder.Step()));
	}
	// The start of live play (after a menu, a pause, a retry, a map load, a viewer's return from an idle spell: the game is paused
	// then) is full of long frames: the ladder counts nothing for a while.
	const double WarmUp = FMath::Max(0.0, (double)MICloudPrivate::GQualityWarmUp);
	if (bQualityWasSafe && !In.bSafeMoment)
	{
		if (WarmUp > 0.0 && bOn && Ladder.HoldLeft() <= 0.0)
		{
			MICloudPrivate::Line(FString::Printf(TEXT("Quality ladder: live play begins: warming up for %.0f s before it counts anything (MI.Cloud.QualityWarmUp)"), WarmUp));
		}
		Ladder.Hold(WarmUp);
	}
	bQualityWasSafe = In.bSafeMoment;
	FMIQualityLadder::FInput Q;
	Q.Seconds = In.Seconds;
	Q.GpuMs = In.GpuMs;
	Q.GpuMsSmallest = In.GpuMsSmallest;
	// The highest target's frame time, whatever the governor is on (the looks go before the frames), unless the rate is fixed by hand.
	Q.FrameMs = Governor.IsPinned() ? Governor.FrameMs() : 1000.0 / FMIFrameRateGovernor::Targets[0];
	Q.bSmallestPicture = In.bSmallestPicture;
	Q.bHeldBack = In.bHeldBack;
	Q.bSafeMoment = In.bSafeMoment;
	Q.bTargetAtTop = Governor.GetIndex() == 0;
	const FMIQualityLadder::EChange Change = Ladder.Update(Q);
	if (Change != FMIQualityLadder::EChange::None)
	{
		ApplyQualityStep(Ladder.Step(), Ladder.Why(), Change == FMIQualityLadder::EChange::Down);
	}
	else if (Ladder.Step() != QualityApplied)
	{
		ApplyQualityStep(Ladder.Step(), !bOn ? FString(TEXT("the ladder is off")) : FString(TEXT("fixed by hand")), Ladder.Step() > QualityApplied);
	}
}

void UMICloudSubsystem::ReleaseQualityHolds()
{
	// Every variable the ladder holds goes back to the value it had and to the priority it was set at, so that the scalability
	// groups (the Settings card's Graphics quality) can write it again.
	for (const FString& Name : QualityHeld)
	{
		IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(*Name);
		const FString* Base = QualityBaseline.Find(Name);
		const uint32* Was = QualitySetBy.Find(Name);
		if (!Var || !Base || !Was)
		{
			continue;
		}
		Var->ClearFlags(ECVF_SetByMask);
		Var->Set(**Base, (EConsoleVariableFlags)*Was);
	}
	QualityHeld.Reset();
	QualityBaseline.Reset();
	QualitySetBy.Reset();
}

void UMICloudSubsystem::ReapplyQualityStep(const TCHAR* Why)
{
	if (!bQualityStarted || QualitySteps.Num() == 0 || Ladder.Step() == 0)
	{
		return;
	}
	ApplyQualityStep(Ladder.Step(), FString(Why), false);
}

void UMICloudSubsystem::ApplyQualityStep(int32 Step, const FString& Why, bool bAfterDescent)
{
	const TArray<FString> Names = FMIQualityTable::Names(QualitySteps);
	// What each variable is now, before anything of this step is written: a scalability group's variable changes the others of
	// its group, and a baseline read after it would be the group's, not the player's.
	for (const FString& Name : Names)
	{
		if (!QualityHeld.Contains(Name))
		{
			if (const IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(*Name))
			{
				QualityBaseline.Add(Name, Var->GetString());
			}
		}
	}
	int32 Set = 0, Changed = 0, Held = 0, Skipped = 0, Released = 0;
	TArray<FString> SkippedNames;
	for (const FString& Name : Names)
	{
		IConsoleVariable* Var = IConsoleManager::Get().FindConsoleVariable(*Name);
		const FString* Base = QualityBaseline.Find(Name);
		if (!Var || !Base)
		{
			continue;
		}
		FString Target;
		bool bSets = FMIQualityTable::ValueAt(QualitySteps, Step, Name, Target);
		const int32* Dir = QualityDirection.Find(Name);
		if (bSets && !FMIQualityTable::Lowers(Dir ? *Dir : 0, *Base, Target))
		{
			// The player's own setting (or the cloud profile) is already as low as the step: leave it, and give back what was held.
			bSets = false;
			++Skipped;
			SkippedNames.Add(Name);
		}
		if (!bSets)
		{
			if (QualityHeld.Contains(Name))
			{
				const uint32* Was = QualitySetBy.Find(Name);
				const bool bDiffers = Var->GetString() != *Base;
				Var->ClearFlags(ECVF_SetByMask);
				Var->Set(**Base, (EConsoleVariableFlags)(Was ? *Was : (uint32)ECVF_SetByDeviceProfile));
				QualityHeld.Remove(Name);
				QualitySetBy.Remove(Name);
				++Released;
				Changed += bDiffers ? 1 : 0;
			}
			continue;
		}
		if (!QualityHeld.Contains(Name) && (Var->GetFlags() & ECVF_SetByMask) > ECVF_SetByDeviceProfile)
		{
			++Held;  // a launch option or a viewer's command holds it
			continue;
		}
		const bool bFirst = !QualityHeld.Contains(Name);
		const uint32 Was = Var->GetFlags() & ECVF_SetByMask;
		const bool bDiffers = Var->GetString() != Target;
		if (MICloudPrivate::SetAsProfile(*Name, Target))
		{
			++Set;
			Changed += bDiffers ? 1 : 0;
			if (bFirst)
			{
				QualityHeld.Add(Name);
				QualitySetBy.Add(Name, Was);
			}
		}
		else
		{
			++Held;
		}
	}
	if (Step == 0)
	{
		QualityBaseline.Reset();   // nothing is held: the next descent reads the variables as they are then
	}
	Ladder.NoteEffect(Step, Changed > 0, bAfterDescent);
	QualityApplied = Step;
	++QualityChanges;
	QualityWatchUntil = FPlatformTime::Seconds() + 2.0;
	QualityWorstAfter = 0.0;
	QualityWatchedStep = Step;
	const FString StepName = Step > 0 && Step <= QualitySteps.Num() ? QualitySteps[Step - 1].Name : FString(TEXT("full quality"));
	MICloudPrivate::Line(FString::Printf(TEXT("Quality: %s; now step %d of %d (\"%s\"), %d variable(s) set (%d changed a value)%s%s%s"), *Why, Step, QualitySteps.Num(), *StepName, Set, Changed,
		Released > 0 ? *FString::Printf(TEXT(", %d given back"), Released) : TEXT(""),
		Held > 0 ? *FString::Printf(TEXT(", %d held by a stronger setting"), Held) : TEXT(""),
		Skipped > 0 ? *FString::Printf(TEXT(", %d left alone because the setting is already as low (%s)"), Skipped, *FString::Join(SkippedNames, TEXT(", "))) : TEXT("")));
	if (Changed == 0 && Step > 0 && bAfterDescent)
	{
		MICloudPrivate::Line(FString::Printf(TEXT("Quality: step %d changed nothing (everything it sets is already there or held): it saves nothing, the ladder goes on"), Step));
	}
}

void UMICloudSubsystem::WatchQualityFrame(float DeltaTime)
{
	if (QualityWatchUntil <= 0.0)
	{
		return;
	}
	QualityWorstAfter = FMath::Max(QualityWorstAfter, (double)DeltaTime * 1000.0);
	if (FPlatformTime::Seconds() >= QualityWatchUntil)
	{
		QualityWatchUntil = 0.0;
		MICloudPrivate::Line(FString::Printf(TEXT("Quality: the longest frame in the two seconds after the change to step %d was %.1f ms"), QualityWatchedStep, QualityWorstAfter));
	}
}

void UMICloudSubsystem::OnStreamStat(FString Player, FName Stat, float Value)
{
	// "Application" carries the plugin's settings and its per-frame capture timings: not the stream to a viewer.
	if (Player != TEXT("Application"))
	{
		FStreamStat& S = StreamStats.FindOrAdd(Stat);
		S.Value = Value;
		S.Time = FPlatformTime::Seconds();
		if (Stat == FName(TEXT("roundTripTime")))
		{
			// Reported under this one name for the video track and the audio track, only when it changes, and 0 until the
			// first measurement: see FMIRoundTrip.
			RoundTrip.Add((double)Value, S.Time);
		}
		if (Value >= S.Peak || S.Time - S.PeakTime > 2.0)
		{
			S.Peak = Value;
			S.PeakTime = S.Time;
		}
	}
}

double UMICloudSubsystem::StreamStat(const TCHAR* Name, double Missing, bool bPeak, double MaxAge) const
{
	const FStreamStat* S = StreamStats.Find(FName(Name));
	return S && FPlatformTime::Seconds() - S->Time < MaxAge ? (double)(bPeak ? S->Peak : S->Value) : Missing;
}

void UMICloudSubsystem::MakeNumbersLine()
{
	FIntPoint Sent(0, 0);
	if (const UGameViewportClient* VC = GetGameInstance() ? GetGameInstance()->GetGameViewportClient() : nullptr; VC && VC->Viewport)
	{
		Sent = VC->Viewport->GetSizeXY();
	}
	FString Picture = FString::Printf(TEXT("%d x %d"), Sent.X, Sent.Y);
	if (PictureShare > 0.f)
	{
		Picture = FString::Printf(TEXT("drawn %d x %d, sent %d x %d"), FMath::RoundToInt32(Sent.X * PictureShare), FMath::RoundToInt32(Sent.Y * PictureShare), Sent.X, Sent.Y);
	}
	// The lowest of the last half minute of play, for both frame rates.
	float LowFps = -1.f, LowTx = -1.f;
	for (const FVector2f& S : PlayLows)
	{
		LowFps = LowFps < 0.f ? S.X : FMath::Min(LowFps, S.X);
		if (S.Y >= 0.f)
		{
			LowTx = LowTx < 0.f ? S.Y : FMath::Min(LowTx, S.Y);
		}
	}
	FString Stream = TEXT("no viewer statistics yet");
	if (const double Tx = StreamStat(TEXT("transmitFps")); Tx >= 0.0)
	{
		Stream = FString::Printf(TEXT("stream %.0f a second%s, %.1f Mbit/s, QP %.0f%s"), Tx, LowTx >= 0.f ? *FString::Printf(TEXT(" (lowest %.0f)"), LowTx) : TEXT(""),
			FMath::Max(0.0, StreamStat(TEXT("bitrateMbits"), 0.0, true)), FMath::Max(0.0, StreamStat(TEXT("qp"), 0.0)),
			bRangeApplied ? *FString::Printf(TEXT(" of %d to %d"), AppliedRange.MinQp, AppliedRange.MaxQp) : TEXT(""));
		// A round trip of the last few reports, and none when none was measured (a 0 is "not measured", never "no delay").
		if (RoundTrip.IsKnown())
		{
			Stream += RoundTrip.Ms() < 10.0 ? FString::Printf(TEXT(", round trip %.1f ms"), RoundTrip.Ms()) : FString::Printf(TEXT(", round trip %.0f ms"), RoundTrip.Ms());
		}
	}
	static IConsoleVariable* Decouple = IConsoleManager::Get().FindConsoleVariable(TEXT("PixelStreaming2.DecoupleFramerate"));
	// The quality ladder's step: "quality step 2 of 6" (full quality is step 0), "fixed" when pinned, "ladder off" when it is off.
	FString Quality;
	if (QualitySteps.Num() > 0)
	{
		Quality = FString::Printf(TEXT("  ·  quality step %d of %d%s"), Ladder.Step(), QualitySteps.Num(),
			!Ladder.IsEnabled() ? TEXT(", ladder off") : Ladder.IsPinned() ? TEXT(", fixed") : TEXT(""));
	}
	NumbersLine = FString::Printf(TEXT("%s  ·  %.0f frames a second (%starget %d%s)  ·  GPU %.1f ms%s  ·  %s  ·  %s%s  ·  build %s"),
		*GRHIAdapterName, LastFps, LowFps >= 0.f ? *FString::Printf(TEXT("lowest %.0f, "), LowFps) : TEXT(""), Governor.Target(), PinnedBy != 0 ? TEXT(", fixed") : TEXT(""), LastGpuMs, *Quality, *Picture, *Stream,
		Decouple && Decouple->GetBool() ? TEXT(", decoupled") : TEXT(""),
		MICloudPrivate::GBuildCommit.IsEmpty() ? TEXT("?") : *MICloudPrivate::GBuildCommit);
}

void UMICloudSubsystem::Probe(float DeltaTime)
{
	ProbeFrames += 1.0;
	ProbeTime += DeltaTime;
	ProbeWorst = FMath::Max(ProbeWorst, (double)DeltaTime);
	// The engine's own per-frame times of each thread, without its waits (what "stat unit" shows).
	ProbeGameMs = FMath::Max(ProbeGameMs, FPlatformTime::ToMilliseconds(GGameThreadTime));
	ProbeRenderMs = FMath::Max(ProbeRenderMs, FPlatformTime::ToMilliseconds(GRenderThreadTime));
	ProbeRhiMs = FMath::Max(ProbeRhiMs, FPlatformTime::ToMilliseconds(GRHIThreadTime));
	const double Now = FPlatformTime::Seconds();
	if (Now < ProbeNext)
	{
		return;
	}
	ProbeNext = Now + ProbePeriod;
	const FPlatformMemoryStats M = FPlatformMemory::GetStats();
	FTextureMemoryStats T;
	if (GDynamicRHI)
	{
		RHIGetTextureMemoryStats(T);
	}
	const double GpuMs = FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles(0));
	const APlayerController* PC = GetGameInstance() ? GetGameInstance()->GetFirstLocalPlayerController() : nullptr;
	const AMIPlayerController* MIPC = Cast<AMIPlayerController>(PC);
	const FRotator R = PC ? PC->GetControlRotation() : FRotator::ZeroRotator;
	UMIGameSubsystem* G = MICloudPrivate::Game(GetGameInstance());
	const FMIGpuPacer::FStats P = Pacer.IsValid() ? Pacer->Take(0) : FMIGpuPacer::FStats();
	bool bSmallest = true;
	const float Share = MICloudPrivate::PictureShare(bSmallest);
	// fps, worstMs and gpuMs stay first: the box tools read the line by its names (tools/box/cloud/lag_sum.py).
	FString Out = FString::Printf(TEXT("MICloudProbe fps=%.1f worstMs=%.1f gpuMs=%.2f target=%d dr=%.2f owed=%d held=%d waitMs=%.1f worstWaitMs=%.1f pacerTimeOuts=%d gameMs=%.1f renderMs=%.1f rhiMs=%.1f"),
		ProbeTime > 0 ? ProbeFrames / ProbeTime : 0.0, ProbeWorst * 1000.0, GpuMs, bPacingStarted ? Governor.Target() : 0, Share,
		P.MaxInFlight, P.Held, P.WaitMs, P.WorstWaitMs, P.TimeOuts, ProbeGameMs, ProbeRenderMs, ProbeRhiMs);
	if (const double Tx = StreamStat(TEXT("transmitFps")); Tx >= 0.0)
	{
		// The stream as its sender measures it: frames captured, encoded and sent a second, the encoder's QP, the bitrate
		// sent and the bitrate the connection is thought to carry (a low one makes WebRTC drop frames), the encode time.
		Out += FString::Printf(TEXT(" capFps=%.0f encFps=%.0f txFps=%.0f qp=%.0f mbps=%.2f availMbps=%.2f encMs=%.1f capToSendMs=%.0f rttMs=%.1f"),
			StreamStat(TEXT("captureFps")), StreamStat(TEXT("encodeFps")), Tx, StreamStat(TEXT("qp")), StreamStat(TEXT("bitrateMbits"), -1.0, true),
			StreamStat(TEXT("availableOutgoingBitrate"), -1e6, true, 120.0) / 1e6, StreamStat(TEXT("encodeTime")), StreamStat(TEXT("captureToSend")),
			RoundTrip.IsKnown() ? RoundTrip.Ms() : -1.0);
	}
	Out += FString::Printf(TEXT(" rssMB=%llu peakRssMB=%llu texStreamMB=%llu texOtherMB=%llu poolMB=%lld yaw=%.4f pitch=%.4f state=%d click=%d bb=%lld pushed=%lld viewers=%d spikes=%d pad=%d cmdRun=%d cmdRefused=%d padRepeats=%d stickKeys=%d"),
		(unsigned long long)(M.UsedPhysical >> 20), (unsigned long long)(M.PeakUsedPhysical >> 20),
		(unsigned long long)(T.StreamingMemorySize >> 20), (unsigned long long)(T.NonStreamingMemorySize >> 20), (long long)(T.TexturePoolSize >> 20),
		R.Yaw, R.Pitch, G ? (int32)G->GetRules().GetState() : -1, bWaitingForClick ? 1 : 0,
		(long long)MICloudPrivate::BackBuffers.load(), (long long)MICloudPrivate::FramesPushed.load(),
		Viewers.Count, MIPC ? MIPC->GetMouseSpikes() : 0, MIPC && MIPC->IsPadActive() ? 1 : 0, CommandsRun, CommandsRefused,
		PadRepeatsDropped, StickKeysMade);
	{
		// What the stream input checks read (tools/box/cloud/rtcinput.py): is the trigger held, how the player moves,
		// the rounds in the magazine, double clicks dropped, the size drawn (after a viewer's size request).
		AMIPlayerCharacter* C = PC ? Cast<AMIPlayerCharacter>(PC->GetPawn()) : nullptr;
		const UMIWeaponComponent* W = C ? C->GetWeapon() : nullptr;
		FIntPoint Size(0, 0);
		if (const UGameViewportClient* VC = GetGameInstance() ? GetGameInstance()->GetGameViewportClient() : nullptr; VC && VC->Viewport)
		{
			Size = VC->Viewport->GetSizeXY();
		}
		Out += FString::Printf(TEXT(" fire=%d moveX=%.2f moveY=%.2f mag=%d dbl=%d outW=%d outH=%d mouseScale=%.4f"), C && C->GetInput().bFire ? 1 : 0,
			C ? C->GetInput().Move.X : 0.0, C ? C->GetInput().Move.Y : 0.0, W && W->IsReady() ? W->GetRules().GetMag() : -1, DoubleClicksDropped, Size.X, Size.Y,
			GetMouseShape().Scale);
	}
	{
		// The sound (new fields go at the end of the line: the box tools read it by its names): sounds started on the
		// audio device since the process started, sounds asked for that have no asset or no entry in the data (a
		// package without its Sound Waves counts up here and plays nothing), starts that got no audio device.
		const UMIAudioSubsystem::FCounts Snd = UMIAudioSubsystem::GetCounts();
		Out += FString::Printf(TEXT(" sndPlayed=%d sndMissing=%d sndNoDevice=%d"), Snd.Played, Snd.Missing, Snd.NoDevice);
	}
	{
		// The session and the encoder (release 3c): idle=1 while nobody watches (idleFrames: frames drawn in the idle
		// episode so far); the QP range the plugin's quality variables give the encoder now (read from them, not from what
		// this game meant to set: -1 when the plugin is not there); how many round trips were measured, and how long ago
		// the newest was.
		static IConsoleVariable* QMax = IConsoleManager::Get().FindConsoleVariable(TEXT("PixelStreaming2.Encoder.MaxQuality"));
		static IConsoleVariable* QMin = IConsoleManager::Get().FindConsoleVariable(TEXT("PixelStreaming2.Encoder.MinQuality"));
		Out += FString::Printf(TEXT(" idle=%d idleFrames=%d qpMin=%d qpMax=%d rttN=%d rttAge=%.0f up=%.1f"), bIdle ? 1 : 0, bIdle ? IdleFrames : 0,
			QMax ? FMIEncoderRange::QpForQuality(QMax->GetInt()) : -1, QMin ? FMIEncoderRange::QpForQuality(QMin->GetInt()) : -1,
			RoundTrip.GetAccepted(), RoundTrip.IsKnown() ? FMath::Min(RoundTrip.AgeSeconds(FPlatformTime::Seconds()), 9999.0) : -1.0, MICloudPrivate::Uptime());
	}
	// The quality ladder (release 3c): the step in force, how many steps the table has, how many changes so far.
	Out += FString::Printf(TEXT(" q=%d qSteps=%d qChanges=%d"), Ladder.Step(), QualitySteps.Num(), QualityChanges);
	// The viewer's away signals (SMOOTH.md B5): received, and the runs they paused.
	Out += FString::Printf(TEXT(" away=%d awayPaused=%d"), AwaySignals, AwayPauses);
	MICloudPrivate::Line(Out);
	ProbeFrames = ProbeTime = ProbeWorst = 0.0;
	ProbeGameMs = ProbeRenderMs = ProbeRhiMs = 0.0;
}
