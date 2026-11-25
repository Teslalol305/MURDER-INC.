#include "Cloud/MICloud.h"

#include <atomic>

#include "Async/Async.h"
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
#include "Styling/CoreStyle.h"
#include "UnrealClient.h"
#include "UObject/UObjectGlobals.h"
#include "Widgets/SCompoundWidget.h"

#include "Core/Data/MIDataSubsystem.h"
#include "Flow/MIGameSubsystem.h"
#include "Flow/MIGameRules.h"
#include "Player/MIPlayerController.h"
#include "UI/MIFrontEnd.h"
#include "UI/MIStyle.h"

#include <cstdio>
#if PLATFORM_LINUX && !WITH_EDITOR
#include <csignal>
#include <cstdlib>
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
	float GFpsDropOver = 0.70f, GFpsDropAfter = 1.f, GFpsRaiseUnder = 0.45f, GFpsRaiseAfter = 10.f;
	FAutoConsoleVariableRef CVarFpsDropOver(TEXT("MI.Cloud.FpsDropOver"), GFpsDropOver,
		TEXT("The frame-rate target drops when the GPU's time is over this share of the frame time at the smallest picture."));
	FAutoConsoleVariableRef CVarFpsDropAfter(TEXT("MI.Cloud.FpsDropAfter"), GFpsDropAfter, TEXT("... for this many seconds."));
	FAutoConsoleVariableRef CVarFpsRaiseUnder(TEXT("MI.Cloud.FpsRaiseUnder"), GFpsRaiseUnder,
		TEXT("The frame-rate target may rise (only while no run is being played) when the GPU's time is under this share of the frame time."));
	FAutoConsoleVariableRef CVarFpsRaiseAfter(TEXT("MI.Cloud.FpsRaiseAfter"), GFpsRaiseAfter, TEXT("... for this many seconds."));

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
		Line(FString::Printf(TEXT("Command line: %s"), FCommandLine::Get()));
	}
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
	Scalability::SetQualityLevels(Levels);
	MICloudPrivate::Line(FString::Printf(TEXT("Graphics quality: %s (scalability groups only; the resolution, the frame cap and the cloud profile stay)"),
		Level < 0 ? TEXT("auto") : *FString::FromInt(FMath::Min(Level, 3))));
}

void UMICloudSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	bProbeGiven = FParse::Value(FCommandLine::Get(), TEXT("MICloudProbe="), ProbePeriod);
	static bool bStarted = false;  // once per process (a game instance is made once in a packaged game)
	if (!bStarted)
	{
		bStarted = true;
		MICloudPrivate::ReportStartup();
#if PLATFORM_LINUX && !WITH_EDITOR
		FCoreDelegates::OnExit.AddStatic(&MICloudPrivate::ArmExitGuard);
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
		StreamHandles.Add(D->OnNewConnectionNative.AddLambda([OnGame](FString, FString)
			{ OnGame([](UMICloudSubsystem& S) { S.OnViewerJoined(); }); }));
		StreamHandles.Add(D->OnAllConnectionsClosedNative.AddLambda([OnGame](FString)
			{ OnGame([](UMICloudSubsystem& S) { S.OnAllViewersLeft(); }); }));
		// The sender's own statistics (frames captured, encoded and sent a second, bitrate, QP, round trip): broadcast on
		// the game thread about once a second for each viewer.
		StreamHandles.Add(D->OnStatChangedNative.AddUObject(this, &UMICloudSubsystem::OnStreamStat));
	}
#endif

	TickHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateUObject(this, &UMICloudSubsystem::Tick));
}

void UMICloudSubsystem::Deinitialize()
{
	FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
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
	if (Viewers.Join())
	{
		bWaitingForClick = !FParse::Param(FCommandLine::Get(), TEXT("MICloudNoCard"));
		MICloudPrivate::Line(FString::Printf(TEXT("Viewer joined: click to play")));
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
	LeftStick = FVector2D::ZeroVector;  // the pad went with its viewer
	StickNav.Reset();
	PadKeysDown.Reset();
	bRefusalLogged = false;  // the next session logs its own first refused command
	bConnectionLost = true;
	bWaitingForClick = false;
	if (UMIGameSubsystem* G = MICloudPrivate::Game(GetGameInstance()); G && G->GetRules().GetState() == EMIGameState::Playing)
	{
		G->Pause();
	}
	MICloudPrivate::Line(FString::Printf(TEXT("Connection lost: the game is paused until a viewer joins")));
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
		PC->SetStreamMouse(MouseShape);
	}
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
	if (Key.IsGamepadKey())
	{
		if (IsStreamPadRepeat(Key, bRepeat) || PadKeysDown.Contains(Key))
		{
			++PadRepeatsDropped;
			return true;
		}
		PadKeysDown.Add(Key);
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

void UMICloudSubsystem::GuardViewerCommands()
{
#if MI_WITH_PIXELSTREAMING2
	// Pixel Streaming 2 runs a viewer's {"ConsoleCommand": "..."} through GEngine->Exec when the host allows viewer
	// commands (RTCInputHandler.cpp PopulateDefaultCommandHandlers), and E3DS always passes
	// -AllowPixelStreamingCommands. IPixelStreaming2InputHandler::SetCommandHandler replaces a handler by name: ours
	// keeps Pixel Streaming's two conditions and adds the allowlist. The other command handlers (the browser's size,
	// the encoder and bitrate settings) are separate names and stay as they are.
	if (bCommandsGuarded || !IPixelStreaming2Module::IsAvailable())
	{
		return;
	}
	IPixelStreaming2Module& Module = IPixelStreaming2Module::Get();
	if (!Module.IsReady())
	{
		return;
	}
	TSharedPtr<IPixelStreaming2Streamer> Streamer = Module.FindStreamer(Module.GetDefaultStreamerID());
	TSharedPtr<IPixelStreaming2InputHandler> Handler = Streamer.IsValid() ? Streamer->GetInputHandler().Pin() : nullptr;
	if (!Handler.IsValid())
	{
		return;
	}
	bCommandsGuarded = true;
	TWeakObjectPtr<UMICloudSubsystem> Weak(this);
	TWeakPtr<IPixelStreaming2InputHandler> WeakHandler = Handler;
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
	MICloudPrivate::Line(FString::Printf(TEXT("Viewer console commands: only these variables can be read or set, anything else is refused: %s"), *MITuning::AllowedList()));
#endif
}

void UMICloudSubsystem::OnViewerCommand(const FString& Command)
{
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
		EnsureMouse();
		GuardViewerCommands();
		TickPacing();
	}
	if (ProbePeriod > 0.f)
	{
		Probe(DeltaTime);
	}
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
		if (Pacer->HasGivenUp() && !bPacerGaveUpLogged)
		{
			bPacerGaveUpLogged = true;
			MICloudPrivate::Line(TEXT("Pacing: the GPU did not report its finished frames three times in a row (each wait ran into MI.Cloud.GpuWaitLimitMs): the pacer no longer holds the game back"));
		}
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
	if (Pacer.IsValid())
	{
		const FMIGpuPacer::FStats S = Pacer->Take(1);
		In.bHeldBack = S.Frames > 0 && S.Held * 2 > S.Frames;
	}
	const AMIPlayerController* PC = GetGameInstance() ? Cast<AMIPlayerController>(GetGameInstance()->GetFirstLocalPlayerController()) : nullptr;
	In.bSafeMoment = !PC || !PC->IsInLivePlay();

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
	if (Now >= NumbersNext)
	{
		NumbersNext = Now + 1.0;
		MakeNumbersLine();
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
	}
}

double UMICloudSubsystem::StreamStat(const TCHAR* Name, double Missing) const
{
	const FStreamStat* S = StreamStats.Find(FName(Name));
	return S && FPlatformTime::Seconds() - S->Time < 5.0 ? (double)S->Value : Missing;
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
	FString Stream = TEXT("no viewer statistics yet");
	if (const double Tx = StreamStat(TEXT("transmitFps")); Tx >= 0.0)
	{
		Stream = FString::Printf(TEXT("stream %.0f a second, %.1f Mbit/s, QP %.0f"), Tx, FMath::Max(0.0, StreamStat(TEXT("bitrateMbits"), 0.0)), FMath::Max(0.0, StreamStat(TEXT("qp"), 0.0)));
		if (const double Rtt = StreamStat(TEXT("roundTripTime")); Rtt >= 0.0)
		{
			Stream += FString::Printf(TEXT(", round trip %.0f ms"), Rtt * 1000.0);
		}
	}
	static IConsoleVariable* Decouple = IConsoleManager::Get().FindConsoleVariable(TEXT("PixelStreaming2.DecoupleFramerate"));
	NumbersLine = FString::Printf(TEXT("%s  ·  %.0f frames a second (target %d%s)  ·  GPU %.1f ms  ·  %s  ·  %s%s  ·  build %s"),
		*GRHIAdapterName, LastFps, Governor.Target(), PinnedBy != 0 ? TEXT(", fixed") : TEXT(""), LastGpuMs, *Picture, *Stream,
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
		Out += FString::Printf(TEXT(" capFps=%.0f encFps=%.0f txFps=%.0f qp=%.0f mbps=%.2f encMs=%.1f rttMs=%.0f lost=%.0f"),
			StreamStat(TEXT("captureFps")), StreamStat(TEXT("encodeFps")), Tx, StreamStat(TEXT("qp")), StreamStat(TEXT("bitrateMbits")),
			StreamStat(TEXT("encodeTime")), StreamStat(TEXT("roundTripTime"), -0.001) * 1000.0, StreamStat(TEXT("packetsLost")));
	}
	Out += FString::Printf(TEXT(" rssMB=%llu peakRssMB=%llu texStreamMB=%llu texOtherMB=%llu poolMB=%lld yaw=%.4f pitch=%.4f state=%d click=%d bb=%lld pushed=%lld viewers=%d spikes=%d pad=%d cmdRun=%d cmdRefused=%d padRepeats=%d stickKeys=%d"),
		(unsigned long long)(M.UsedPhysical >> 20), (unsigned long long)(M.PeakUsedPhysical >> 20),
		(unsigned long long)(T.StreamingMemorySize >> 20), (unsigned long long)(T.NonStreamingMemorySize >> 20), (long long)(T.TexturePoolSize >> 20),
		R.Yaw, R.Pitch, G ? (int32)G->GetRules().GetState() : -1, bWaitingForClick ? 1 : 0,
		(long long)MICloudPrivate::BackBuffers.load(), (long long)MICloudPrivate::FramesPushed.load(),
		Viewers.Count, MIPC ? MIPC->GetMouseSpikes() : 0, MIPC && MIPC->IsPadActive() ? 1 : 0, CommandsRun, CommandsRefused,
		PadRepeatsDropped, StickKeysMade);
	MICloudPrivate::Line(Out);
	ProbeFrames = ProbeTime = ProbeWorst = 0.0;
	ProbeGameMs = ProbeRenderMs = ProbeRhiMs = 0.0;
}
