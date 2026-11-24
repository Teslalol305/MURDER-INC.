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
#include "Misc/App.h"
#include "Misc/CoreDelegates.h"
#include "Misc/Paths.h"
#include "RHIStats.h"
#include "RHIStrings.h"
#include "RenderUtils.h"
#include "Scalability.h"
#include "Styling/CoreStyle.h"
#include "UObject/UObjectGlobals.h"
#include "Widgets/SCompoundWidget.h"

#include "Core/Data/MIDataSubsystem.h"
#include "Flow/MIGameSubsystem.h"
#include "Flow/MIGameRules.h"
#include "Player/MIPlayerController.h"
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

		if (State == EMIGameState::Paused)
		{
			// The pause card says nothing about keys; in a browser Esc may never reach the game, so name P.
			Text(Out, Layer, Geo, TEXT("P to resume  ·  Esc gives the mouse back to the browser; click the game to take it again"),
				MIStyle::Body(18 * S, true), MIStyle::Ink(), Size.Y - 64 * S);
		}

		// The stream has no operating-system cursor: draw one wherever the game shows the mouse.
		const APlayerController* PC = O->GetGameInstance() ? O->GetGameInstance()->GetFirstLocalPlayerController() : nullptr;
		if (PC && PC->ShouldShowMouseCursor() && FSlateApplication::IsInitialized())
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

	virtual void Tick(const float, FSlateApplication&, TSharedRef<ICursor>) override {}
	virtual const TCHAR* GetDebugName() const override { return TEXT("MICloudClickToPlay"); }

	virtual bool HandleKeyDownEvent(FSlateApplication&, const FKeyEvent&) override { return Eat(); }
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
	MICloudPrivate::Line(FString::Printf(TEXT("Cloud profile applied: %d of %d settings"), N, Lines.Num()));
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

bool UMICloudSubsystem::IsViewerCommandAllowed(const FString& Command)
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
	return C.StartsWith(TEXT("PixelStreaming2."), ESearchCase::IgnoreCase) || C.StartsWith(TEXT("PixelStreaming."), ESearchCase::IgnoreCase);
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
	FParse::Value(FCommandLine::Get(), TEXT("MICloudProbe="), ProbePeriod);
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
	}
#endif

	TickHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateUObject(this, &UMICloudSubsystem::Tick));
}

void UMICloudSubsystem::Deinitialize()
{
	FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
#if MI_WITH_PIXELSTREAMING2
	if (UPixelStreaming2Delegates* D = UPixelStreaming2Delegates::Get(); D && StreamHandles.Num() == 3)
	{
		D->OnConnectedToSignallingServerNative.Remove(StreamHandles[0]);
		D->OnNewConnectionNative.Remove(StreamHandles[1]);
		D->OnAllConnectionsClosedNative.Remove(StreamHandles[2]);
	}
#endif
	StreamHandles.Reset();
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
		}
		else if (UMIDataSubsystem::LoadConfig(Config, Error))
		{
			Glitch = Config.Player.Look.MouseGlitch;
		}
		MouseShape = ReadMouseShape(FCommandLine::Get(), Glitch);
		MICloudPrivate::Line(FString::Printf(TEXT("Mouse look: %.4f browser pixels per count ([MICloud] MouseScale; launch option -MIMouseScale=<number>), %.2f count(s) put back per event and axis (MouseTruncation), events beyond %.0f pixels dropped as pointer-lock spikes"),
			MouseShape.Scale, MouseShape.Truncation, MouseShape.Glitch));
	}
	if (!bProfileApplied)
	{
		bProfileApplied = true;
		ApplyCloudProfile();
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
	MICloudPrivate::Line(TEXT("Viewer console commands: only PixelStreaming2.* and PixelStreaming.* run; anything else is refused"));
#endif
}

void UMICloudSubsystem::OnViewerCommand(const FString& Command)
{
	if (IsViewerCommandAllowed(Command))
	{
		++CommandsRun;
		if (GEngine)
		{
			GEngine->Exec(GetGameInstance() ? GetGameInstance()->GetWorld() : nullptr, *Command.TrimStartAndEnd());
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
		MICloudPrivate::Line(FString::Printf(TEXT("Viewer console command refused: \"%s\" (only PixelStreaming2.* and PixelStreaming.* run; further refusals of this session are counted, not logged)"), *Shown));
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
	}
	if (ProbePeriod > 0.f)
	{
		Probe(DeltaTime);
	}
	return true;
}

void UMICloudSubsystem::Probe(float DeltaTime)
{
	ProbeFrames += 1.0;
	ProbeTime += DeltaTime;
	ProbeWorst = FMath::Max(ProbeWorst, (double)DeltaTime);
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
	MICloudPrivate::Line(FString::Printf(TEXT("MICloudProbe fps=%.1f worstMs=%.1f gpuMs=%.2f rssMB=%llu peakRssMB=%llu texStreamMB=%llu texOtherMB=%llu poolMB=%lld yaw=%.4f pitch=%.4f state=%d click=%d bb=%lld pushed=%lld viewers=%d spikes=%d pad=%d cmdRun=%d cmdRefused=%d"),
		ProbeTime > 0 ? ProbeFrames / ProbeTime : 0.0, ProbeWorst * 1000.0, GpuMs,
		(unsigned long long)(M.UsedPhysical >> 20), (unsigned long long)(M.PeakUsedPhysical >> 20),
		(unsigned long long)(T.StreamingMemorySize >> 20), (unsigned long long)(T.NonStreamingMemorySize >> 20), (long long)(T.TexturePoolSize >> 20),
		R.Yaw, R.Pitch, G ? (int32)G->GetRules().GetState() : -1, bWaitingForClick ? 1 : 0,
		(long long)MICloudPrivate::BackBuffers.load(), (long long)MICloudPrivate::FramesPushed.load(),
		Viewers.Count, MIPC ? MIPC->GetMouseSpikes() : 0, MIPC && MIPC->IsPadActive() ? 1 : 0, CommandsRun, CommandsRefused));
	ProbeFrames = ProbeTime = ProbeWorst = 0.0;
}
