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
#include "RHIStats.h"
#include "Styling/CoreStyle.h"
#include "UObject/UObjectGlobals.h"
#include "Widgets/SCompoundWidget.h"

#include "Flow/MIGameSubsystem.h"
#include "Flow/MIGameRules.h"
#include "UI/MIStyle.h"

#if MI_WITH_PIXELSTREAMING2
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

	/** Every line also goes to -MICloudLog=<file> when given: Shipping builds compile the engine log out, and the
	 *  stream test (tools/box/cloud/stream_test.cjs) reads what the game saw from this file. */
	void Line(const FString& Text)
	{
		UE_LOG(LogMICloud, Display, TEXT("%s"), *Text);
		static FString File = [] { FString F; FParse::Value(FCommandLine::Get(), TEXT("MICloudLog="), F); return F; }();
		if (!File.IsEmpty())
		{
			FFileHelper::SaveStringToFile(FString::Printf(TEXT("%.3f %s\n"), FPlatformTime::Seconds(), *Text), *File,
				FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM, &IFileManager::Get(), FILEWRITE_Append);
		}
	}
}

namespace MICloudPrivate
{
	UMIGameSubsystem* Game(const UGameInstance* GI)
	{
		UWorld* World = GI ? GI->GetWorld() : nullptr;
		return World ? World->GetSubsystem<UMIGameSubsystem>() : nullptr;
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
			Text(Out, Layer + 1, Geo, TEXT("Sound starts with your click."), MIStyle::Body(18 * S), Dim, Mid + 138 * S);
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

void UMICloudSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	FParse::Value(FCommandLine::Get(), TEXT("MICloudProbe="), ProbePeriod);
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
	bWaitingForClick = true;
	MICloudPrivate::Line(FString::Printf(TEXT("Viewer joined: click to play")));
}

void UMICloudSubsystem::OnAllViewersLeft()
{
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

bool UMICloudSubsystem::Tick(float DeltaTime)
{
	if (bStreamed)
	{
		EnsureOverlay();
		EnsureVideoProducer();
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
	const FRotator R = PC ? PC->GetControlRotation() : FRotator::ZeroRotator;
	UMIGameSubsystem* G = MICloudPrivate::Game(GetGameInstance());
	MICloudPrivate::Line(FString::Printf(TEXT("MICloudProbe fps=%.1f worstMs=%.1f gpuMs=%.2f rssMB=%llu peakRssMB=%llu texStreamMB=%llu texOtherMB=%llu poolMB=%lld yaw=%.4f pitch=%.4f state=%d click=%d bb=%lld pushed=%lld"),
		ProbeTime > 0 ? ProbeFrames / ProbeTime : 0.0, ProbeWorst * 1000.0, GpuMs,
		(unsigned long long)(M.UsedPhysical >> 20), (unsigned long long)(M.PeakUsedPhysical >> 20),
		(unsigned long long)(T.StreamingMemorySize >> 20), (unsigned long long)(T.NonStreamingMemorySize >> 20), (long long)(T.TexturePoolSize >> 20),
		R.Yaw, R.Pitch, G ? (int32)G->GetRules().GetState() : -1, bWaitingForClick ? 1 : 0,
		(long long)MICloudPrivate::BackBuffers.load(), (long long)MICloudPrivate::FramesPushed.load()));
	ProbeFrames = ProbeTime = ProbeWorst = 0.0;
}
