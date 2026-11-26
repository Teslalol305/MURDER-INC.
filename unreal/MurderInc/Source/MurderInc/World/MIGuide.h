#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "World/MIBoxWorld.h"
#include "MIGuide.generated.h"

class FJsonObject;
class FMIGameRules;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UStaticMesh;
class UStaticMeshComponent;
struct FMILevelData;

/**
 * Story guidance (docs/unreal/PLAY.md, guide lane): the next step of the mission (Reel 1, Reel 2, Reel 3, then the IPX
 * truck), a hint line after a while without progress, and a path of chevrons on the ground from the player to that step
 * along the nav grid the Goons path on. Presentation only: it reads the flow and the enemies and never writes to them;
 * its path searches run on a private copy of the box world, so not even the search buffers of the simulation are touched.
 * Tuning and the hint lines: Content/Data/guide.json.
 */
struct MURDERINC_API FMIGuideTune
{
	// path
	double Repath = 1.0, MinRepath = 0.25, Stray = 2.5, Keep = 0.95;
	double Spacing = 1.5, Ahead = 1.4, Reach = 30.0, StopShort = 1.2, FadeIn = 2.5, Elevated = 1.0, StepUp = 0.45;
	int32 MaxChevrons = 24;
	// look
	FString Mesh = TEXT("/Engine/BasicShapes/Plane.Plane");
	FString Material = TEXT("/Game/FX/M_FX_Tracer.M_FX_Tracer");
	double ArmLength = 0.5, ArmWidth = 0.11, ArmAngle = 52.0, Lift = 0.035;
	FLinearColor Color = FLinearColor(1.f, 0.62f, 0.22f);
	double Intensity = 2600.0, Shade = 0.3, Combat = 0.35, CombatFade = 0.6;
	// a dark strip under each arm (look.underlay), so the chevron reads as a lit line on black in full sun, not as one
	// more pale stripe of road paint: an empty material draws none
	FString UnderMaterial;
	FLinearColor UnderColor = FLinearColor(0.02f, 0.018f, 0.016f);
	double UnderWidth = 2.4, UnderLonger = 0.1, UnderDrop = 0.012;
	int32 Phases = 4;
	double Chase = 0.9, Low = 0.4;
	// marker
	double MarkerFar = 10.0, MarkerNear = 2.5, MarkerEdge = 56.0;
	// hints
	double HintAfter = 45.0, Progress = 3.0;
	TMap<FName, FString> Hints;  // objective id or "extraction" -> line
	struct FWayDown
	{
		FString Name;
		FVector Top = FVector::ZeroVector;   // web
		FVector Foot = FVector::ZeroVector;  // web
	};
	TArray<FWayDown> WaysDown;

	/** guide.json for the level levels.json names as its default; false (and the defaults above) when it is missing. */
	static bool Load(FMIGuideTune& Out, FString& OutError);
	static bool Parse(const TSharedPtr<FJsonObject>& Root, FName Level, FMIGuideTune& Out, FString& OutError);
};

/** One chevron: its tip on the ground (web), the direction it points (web, flat, unit), its size 0..1 and its slot (the
 *  count of spacings back from the goal: stable while the route stays the same). */
struct FMIGuideChevron
{
	FVector Tip = FVector::ZeroVector;
	FVector Dir = FVector(1, 0, 0);
	double Scale = 1.0;
	int32 Slot = 0;
	bool bShade = false;
};

/** What the plan reads each frame (filled by AMIGuide from the game; tests fill it themselves). */
struct FMIGuideInput
{
	bool bStory = false;   // a mission run in its intro or in play
	bool bClock = false;   // in play: the no-progress clock may run
	bool bCombat = false;  // an enemy is engaging
	FVector Feet = FVector::ZeroVector;  // web
	TArray<bool> Secured;  // per objective
};

/** The guidance's decisions, without the engine (testable). */
class MURDERINC_API FMIGuidePlan
{
public:
	static constexpr int32 NoStep = INDEX_NONE;
	static constexpr int32 ExtractionStep = 1000;

	/** The step the story asks for next: the first objective not taken, in the level's order, then the extraction. */
	static int32 NextStep(const TArray<bool>& Secured);
	static int32 NextStep(const FMIGameRules& Rules, const FMILevelData& Level);

	void Init(const FMIGuideTune& InTune, const FMILevelData* InLevel);
	void Reset();
	/** One frame. Nav: the box world the routes are searched on (AMIGuide's private copy). True when the chevrons
	 *  changed. */
	bool Update(double Dt, const FMIGuideInput& In, FMIBoxWorld& Nav);

	int32 GetStep() const { return Step; }
	bool IsActive() const { return Step != NoStep; }
	FVector GetGoal() const { return Goal; }                // web, the objective or the extraction point
	FName GetStepId() const;
	const TArray<FVector>& GetPath() const { return Path; }  // web, from where the player stood at the search
	bool HasRoute() const { return Path.Num() >= 2; }
	/** Metres left along the route from the player (straight-line distance when there is no route). */
	double GetRemaining() const { return Remaining; }
	/** Metres from the player to the drawn route. */
	double GetOffRoute() const { return OffRoute; }
	double GetNoProgress() const { return NoProgress; }
	bool ShowsHint() const { return bHint; }
	const FString& GetHint() const { return Hint; }
	const TArray<FMIGuideChevron>& GetChevrons() const { return Chevrons; }
	/** 0 calm, 1 an enemy is engaging (eased). */
	double GetCombat() const { return Combat; }
	int32 GetSearches() const { return Searches; }
	int32 GetFailedSearches() const { return FailedSearches; }
	const FMIGuideTune& GetTune() const { return Tune; }
	/** Dev (console MIGuide.HintAfter, pictures): the seconds without progress before the hint. */
	void SetHintAfter(double Seconds) { Tune.HintAfter = Seconds; }

private:
	bool Search(const FVector& Feet, FMIBoxWorld& Nav, TArray<FVector>& Out) const;
	/** Arc length of the projection of P on the path (x, z) and the distance to it. */
	void Project(const FVector& P, double& OutS, double& OutDist) const;
	double FloorAt(FMIBoxWorld& Nav, const FVector& At, double Below) const;
	void Lay(FMIBoxWorld& Nav, double S0);
	FVector GoalOf(int32 InStep) const;

	/** What a slot of the current route looks like (computed once per route: floor and roof rays are not free). */
	struct FSlot
	{
		bool bValid = false;
		bool bShade = false;
		FVector Tip = FVector::ZeroVector;
		FVector Dir = FVector(1, 0, 0);
	};

	FMIGuideTune Tune;
	const FMILevelData* Level = nullptr;
	int32 Step = NoStep;
	FVector Goal = FVector::ZeroVector;
	TArray<FVector> Path;
	TArray<double> Cum;
	TArray<FMIGuideChevron> Chevrons;
	TArray<FSlot> SlotCache;
	mutable TArray<FVector> SearchBuf;  // reused: no allocation per search once grown
	TArray<FVector> NewBuf;
	double SinceSearch = 1e9;
	double Remaining = 0.0, OffRoute = 0.0, Best = 1e9, NoProgress = 0.0, LaidAt = -1e9, Combat = 0.0;
	bool bHint = false;
	FString Hint;
	int32 Searches = 0, FailedSearches = 0;
};

/** What the guidance has cost on the game thread (AMIGuide::GetCost, console MIGuide.Stats). */
struct FMIGuideCost
{
	int32 Frames = 0, Searches = 0, Moves = 0;
	double TotalMs = 0.0, WorstMs = 0.0, SearchMs = 0.0, WorstSearchMs = 0.0;
};

/**
 * The guidance in the world: runs FMIGuidePlan every frame after the player has moved and draws the chevrons with a
 * pool of flat strips (two per chevron) in the tracer material, one material instance per light phase and shade, so
 * a frame only sets a few scalar parameters; strips move only when the route or the player's end of it changes.
 * Spawned by the HUD (AMIHUD::BeginPlay): tests and the simulation run without it. The HUD draws the step line, the hint
 * and the marker from GetPlan(). Settings "Ground path" off hides the path; the objectives keep their plain markers.
 *
 * Console: MIGuide.Stats (the cost so far: average and worst milliseconds a frame, searches, the state), MIGuide.Reset
 * (zero the cost), MIGuide.HintAfter <s> and MIGuide.Show 0|1 (pictures: the hint sooner, the Settings row).
 */
UCLASS(NotPlaceable, Transient)
class MURDERINC_API AMIGuide : public AActor
{
	GENERATED_BODY()

public:
	AMIGuide();

	/** The guide of this world (the first one), or null. */
	static AMIGuide* Find(const UWorld* World);
	/** The guide of this world, spawned when there is none (only in a world whose game has booted). */
	static AMIGuide* Ensure(UWorld* World);

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	/** One frame of guidance (Tick calls it; tests may too). */
	void Step(double Dt);

	const FMIGuidePlan& GetPlan() const { return Plan; }
	const FMIGuideTune& GetTune() const { return Tune; }
	/** Dev (console MIGuide.HintAfter): the seconds without progress before the hint line. */
	void SetHintAfter(double Seconds) { Tune.HintAfter = Seconds; Plan.SetHintAfter(Seconds); }
	/** The ground path wanted: on in Settings and a step to show. */
	bool IsShown() const { return bShown; }
	/** Strips drawn right now (for tests and pictures). */
	int32 VisibleStrips() const;
	/** The strip pool (for tests and pictures). */
	const TArray<TObjectPtr<UStaticMeshComponent>>& GetStrips() const { return Strips; }

	using FCost = FMIGuideCost;
	const FCost& GetCost() const { return Cost; }
	void ResetCost() { Cost = FCost(); }

private:
	void Build();
	void Place();
	void Animate();
	void HideAll();
	bool SyncNav(const FMIBoxWorld& Source);

	FMIGuideTune Tune;
	FMIGuidePlan Plan;
	FMIBoxWorld Nav;  // private copy of the game's box world (refreshed when its revision changes)
	uint32 NavRevision = MAX_uint32;
	const FMIBoxWorld* NavSource = nullptr;
	bool bHaveNav = false;
	bool bBuilt = false;
	bool bShown = false;
	bool bDrawn = false;
	double Clock = 0.0;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> Strips;  // two per pool entry: entry p shows the chevron of slot k with k % pool == p

	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> Unders;  // the dark strip under Strips[i] (empty without look.underlay)

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> Mats;  // [phase + Phases * shade]

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> UnderMat;

	FMIGuideInput Input;        // reused every frame
	TArray<bool> PoolUsed;
	TArray<int32> StripMat;     // the material each strip has now (index into Mats)
	TArray<FTransform> StripAt; // the transform each strip has now
	TArray<bool> StripOn;
	FMIGuideCost Cost;
};
