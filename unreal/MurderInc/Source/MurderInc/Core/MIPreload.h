#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "UObject/SoftObjectPath.h"
#include "MIPreload.generated.h"

struct FStreamableHandle;
struct FStreamableManager;

/**
 * Loads, in the background and once a session, every asset the data files name (every string that starts with /Game/
 * in presentation.json, attachments.json, guns.json and crew.json: the six guns, their parts, magazines and clips, the
 * crew's arms, the enemies) and keeps it in memory, so that a set-up screen, the Workbench or a gun switch that asks for
 * one with FSoftObjectPath::TryLoad finds it loaded instead of holding the game thread while it is read.
 *
 * Measured before (docs/unreal/SMOOTH.md C2, the CPU lane's run from the box's local disk): each such load cost 7 to 18 ms
 * of game thread in its frame (gun focus on the slot screen 10.4, 7.3, 9.4 ms; the Briefing 10.4 ms; the switch to gun 2
 * 11.7 ms, to gun 3 18.2 ms), and 202 ms for the Briefing's load when the package was read from a slow volume. Nothing
 * here changes a rule or what is drawn: the same objects, loaded earlier.
 *
 * It starts once the first world has begun play (the title screen), not during the map's own load (which flushes every
 * request and would hold the first frame for them). Off in automation tests, in a dedicated server, with -NullRHI and with
 * -MINoPreload; MI.Preload 0 stops a session's preload before it starts.
 */
UCLASS()
class MURDERINC_API UMIPreloadSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	/** Every distinct string that starts with /Game/ in the given JSON texts, as asset paths, in order of first appearance. */
	static TArray<FSoftObjectPath> CollectPaths(const TArray<FString>& JsonTexts);

	/** The assets asked for, and whether the request has finished. */
	int32 NumRequested() const { return Requested; }
	bool IsDone() const { return bDone; }

private:
	bool Tick(float DeltaTime);
	void Start();

	FTSTicker::FDelegateHandle TickHandle;
	TUniquePtr<FStreamableManager> Streamable;
	TSharedPtr<FStreamableHandle> Handle;
	double StartedAt = 0.0;
	int32 Requested = 0;
	bool bStarted = false;
	bool bDone = false;
};
