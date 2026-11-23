#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Containers/Ticker.h"
#include "MICloud.generated.h"

class SMICloudOverlay;
class FMICloudInput;

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
 *  - when the last viewer disconnects, a running game pauses; the next viewer gets the click card again.
 *
 * -MICloudProbe=<seconds> logs one "MICloudProbe" line per period (frame time, GPU time, process memory, the GPU
 * memory the RHI reports, the view's yaw and pitch, the game state) for the cloud budget measurements.
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
	/** Sets every [MICloud] CVars line; returns how many were set. */
	static int32 ApplyCloudProfile();

	bool IsStreamed() const { return bStreamed; }
	bool IsWaitingForClick() const { return bWaitingForClick; }
	/** The first click, key or button of a viewer: hides the card. */
	void Dismiss();

private:
	void BecomeStreamed(const TCHAR* Why);
	bool Tick(float DeltaTime);
	void EnsureOverlay();
	void OnViewerJoined();
	void OnAllViewersLeft();
	void Probe(float DeltaTime);

	bool bStreamed = false;
	bool bProfileApplied = false;
	bool bWaitingForClick = false;
	bool bConnectionLost = false;
	FTSTicker::FDelegateHandle TickHandle;
	TSharedPtr<SMICloudOverlay> Overlay;
	TSharedPtr<FMICloudInput> Input;
	TWeakObjectPtr<class UGameViewportClient> OverlayViewport;

	float ProbePeriod = 0.f;
	double ProbeNext = 0.0;
	double ProbeFrames = 0.0, ProbeTime = 0.0, ProbeWorst = 0.0;
	TArray<FDelegateHandle> StreamHandles;
};
