#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "MIDemoDirector.generated.h"

class AMIPlayerCharacter;
class UMIGameSubsystem;

/**
 * Dev only (not in shipping builds): the demo capture (tools/box/demo/). Plays a script of timed actions through the
 * game's own input and console commands, frame by frame on game time, and can hand every frame of the game viewport
 * (the set-up screens, the HUD and the world, as MIShot reads them) to a pipe as raw BGRA.
 *
 *   MIDemo.Run <script file>     start the script (one action per line, docs in tools/box/demo/demo.txt)
 *   MIDemo.Stop                  stop the script and any capture
 *   MIDemo.Capture <path> | off  write every frame from now on (a FIFO that ffmpeg reads, or a .raw file)
 *
 * Run it with a fixed frame time (-benchmark -fps=60 -deterministic) so each engine frame is one video frame and the
 * run is the same every time. The player's view is moved by a damped spring toward what the script looks at, never
 * set in one step, so the picture has no jumps.
 */
UCLASS()
class MURDERINC_API UMIDemoDirector : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(UMIDemoDirector, STATGROUP_Tickables); }
	virtual bool IsTickableWhenPaused() const override { return true; }

	bool RunScript(const FString& Path);
	void Stop();
	bool StartCapture(const FString& Path);
	void StopCapture();

private:
	struct FAction
	{
		FString Verb;
		TArray<FString> Args;
		FString Raw;
		int32 Line = 0;
	};

	AMIPlayerCharacter* Player() const;
	UMIGameSubsystem* Game() const;
	void Console(const FString& Command);
	/** Starts the action at Index; returns true when it finished at once. */
	bool Begin(const FAction& A);
	/** One frame of the running action; returns true when it is done. */
	bool Step(float Dt);
	void SteerView(float Dt);
	void Move(float Dt);
	/** One frame of fighting; returns false when there is no target. */
	bool Fight(float Dt);
	int32 PickTarget() const;
	FVector AimPoint(int32 Slot, bool bHead) const;
	bool Sees(int32 Slot, bool bHead) const;
	void ReleaseTrigger();
	void OnEndFrame();
	void Log(const FString& Text) const;
	double Arg(const FAction& A, int32 I, double Default) const;

	TArray<FAction> Script;
	int32 Index = INDEX_NONE;
	bool bRunning = false;
	double Clock = 0.0;       // game seconds since the script started
	int64 Frame = 0;          // frames since the script started
	double ActionTime = 0.0;  // seconds in the current action
	double ActionLimit = 0.0;

	// The view: a damped spring toward a wanted direction.
	bool bHasView = false;
	double WantYaw = 0.0, WantPitch = 0.0;
	double YawRate = 0.0, PitchRate = 0.0;
	double SpringHz = 1.6;     // natural frequency (Hz)
	double MaxRate = 210.0;    // degrees per second
	bool bLookAtPoint = false;
	FVector LookPoint = FVector::ZeroVector;

	// Walking.
	bool bWalking = false;
	FVector2D WalkTo = FVector2D::ZeroVector;
	/** A route (pure pursuit): the walk heads for a point Ahead cm further along the polyline. */
	TArray<FVector2D> Route;
	int32 RouteSeg = 0;
	double Ahead = 220.0;
	FVector2D RoutePoint(double Further) const;
	void AdvanceRoute(const FVector2D& Feet);
	bool bSprint = false;
	double WalkPitch = -2.0;
	/** The view follows the walk's direction (face path). */
	bool bWalkFacesPath = true;
	double Arrive = 60.0;
	/** Walk on while fighting (otherwise the walk waits for the fight). */
	bool bAuto = false;

	// Fighting.
	bool bFighting = false;
	bool bHead = true;
	int32 Target = INDEX_NONE;
	double TargetTime = 0.0;   // seconds on this target
	double OnTarget = 0.0;     // seconds with the aim inside the tolerance
	double Calm = 0.0;         // seconds since a target was in sight
	double CalmEnd = 2.5;
	double AfterKill = 0.0;
	int32 KillsAtStart = 0;
	int32 KillsWanted = 0;
	bool bTriggerDown = false;
	bool bFightLook = false;
	FVector FightPoint = FVector::ZeroVector;
	double FightHz = 2.2;
	int32 LastKills = 0;
	int32 FireFrames = 0;
	double MaxRange = 3200.0;
	double Burst = 0.0;        // seconds of trigger in this burst
	double BurstRest = 0.0;

	// Blowing an explosive / grabbing a reel.
	TWeakObjectPtr<AActor> Blow;
	int32 ReelsAtStart = 0;

	bool bGod = false;

	// Capture.
	FILE* Pipe = nullptr;
	FString PipePath;
	int64 Captured = 0;
	FIntPoint CaptureSize = FIntPoint::ZeroValue;
	FDelegateHandle EndFrameHandle;
};
