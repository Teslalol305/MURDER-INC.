#include "World/MIGuide.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

#include "Components/StaticMeshComponent.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Core/Data/MILoadoutData.h"
#include "Dom/JsonObject.h"
#include "Enemies/MIEnemies.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Flow/MIGameRules.h"
#include "Flow/MIGameSubsystem.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformTime.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "MurderInc.h"
#include "World/MILevelData.h"

namespace MIGuidePrivate
{
	FVector Triple(const TSharedPtr<FJsonValue>& V, const FVector& Fallback)
	{
		if (!V.IsValid() || V->Type != EJson::Array || V->AsArray().Num() < 3)
		{
			return Fallback;
		}
		const TArray<TSharedPtr<FJsonValue>>& A = V->AsArray();
		return FVector(A[0]->AsNumber(), A[1]->AsNumber(), A[2]->AsNumber());
	}

	double Flat(const FVector& A, const FVector& B) { return MI::Web::Hypot(A.X - B.X, A.Z - B.Z); }

	FAutoConsoleCommandWithWorld StatsCmd(TEXT("MIGuide.Stats"),
		TEXT("MIGuide.Stats: the guidance's cost so far (milliseconds a frame on the game thread, path searches) and its state"),
		FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
		{
			const AMIGuide* G = AMIGuide::Find(World);
			if (!G)
			{
				UE_LOG(LogMI, Display, TEXT("MIGuide: no guide in this world"));
				return;
			}
			const AMIGuide::FCost& C = G->GetCost();
			const FMIGuidePlan& P = G->GetPlan();
			UE_LOG(LogMI, Display, TEXT("MIGuide: %d frames, %.4f ms a frame on average, worst %.3f ms; %d searches, %.3f ms each on average, worst %.3f ms; %d strip moves; step %s, %.1f m left, %.1f m off the route, no progress %.1f s, hint %s, %d strips drawn, %d failed searches"),
				C.Frames, C.Frames ? C.TotalMs / C.Frames : 0.0, C.WorstMs, C.Searches, C.Searches ? C.SearchMs / C.Searches : 0.0, C.WorstSearchMs,
				C.Moves, *P.GetStepId().ToString(), P.GetRemaining(), P.GetOffRoute(), P.GetNoProgress(), P.ShowsHint() ? TEXT("shown") : TEXT("hidden"),
				G->VisibleStrips(), P.GetFailedSearches());
		}));

	FAutoConsoleCommandWithWorldAndArgs HintCmd(TEXT("MIGuide.HintAfter"),
		TEXT("MIGuide.HintAfter <seconds>: the time without progress before the hint line (guide.json hints.after; for pictures)"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			if (AMIGuide* G = AMIGuide::Find(World); G && Args.Num() > 0)
			{
				G->SetHintAfter(FCString::Atod(*Args[0]));
				UE_LOG(LogMI, Display, TEXT("MIGuide: hint after %.1f s"), FCString::Atod(*Args[0]));
			}
		}));

	FAutoConsoleCommandWithWorldAndArgs ShowCmd(TEXT("MIGuide.Show"),
		TEXT("MIGuide.Show 0|1: the Settings row Ground path (not saved; for pictures and tests)"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			if (UMIGameSubsystem* Game = UMIGameSubsystem::Get(World); Game && Args.Num() > 0)
			{
				Game->GetSettings().SetGuide(FCString::Atoi(*Args[0]) != 0);
				UE_LOG(LogMI, Display, TEXT("MIGuide: ground path %s"), Game->GetSettings().bGuide ? TEXT("on") : TEXT("off"));
			}
		}));

	FAutoConsoleCommandWithWorld ResetCmd(TEXT("MIGuide.Reset"), TEXT("MIGuide.Reset: zero the guidance's cost counters"),
		FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* World)
		{
			if (AMIGuide* G = AMIGuide::Find(World))
			{
				G->ResetCost();
			}
		}));
}

// ------------------------------------------------------------------------------------------------------- tune

bool FMIGuideTune::Load(FMIGuideTune& Out, FString& OutError)
{
	TSharedPtr<FJsonObject> Root;
	if (!UMIDataSubsystem::LoadJsonFile(TEXT("guide.json"), Root, OutError))
	{
		return false;
	}
	FName Level = TEXT("block");
	TSharedPtr<FJsonObject> Levels;
	FString LevelsError, Default;
	if (UMIDataSubsystem::LoadJsonFile(TEXT("levels.json"), Levels, LevelsError) && Levels->TryGetStringField(TEXT("default"), Default))
	{
		Level = FName(*Default);
	}
	return Parse(Root, Level, Out, OutError);
}

bool FMIGuideTune::Parse(const TSharedPtr<FJsonObject>& Root, FName Level, FMIGuideTune& Out, FString& OutError)
{
	using namespace MIGuidePrivate;
	if (!Root.IsValid())
	{
		OutError = TEXT("guide.json: no data");
		return false;
	}
	const auto N = [&Root](const TCHAR* Path, double& Field) { Field = MIJson::NumberOr(Root, Path, Field); };
	N(TEXT("path.repath"), Out.Repath);
	N(TEXT("path.minRepath"), Out.MinRepath);
	N(TEXT("path.stray"), Out.Stray);
	N(TEXT("path.keep"), Out.Keep);
	N(TEXT("path.spacing"), Out.Spacing);
	N(TEXT("path.ahead"), Out.Ahead);
	N(TEXT("path.reach"), Out.Reach);
	N(TEXT("path.stopShort"), Out.StopShort);
	N(TEXT("path.fadeIn"), Out.FadeIn);
	N(TEXT("path.elevated"), Out.Elevated);
	N(TEXT("path.stepUp"), Out.StepUp);
	double Pool = Out.MaxChevrons, Phases = Out.Phases;
	N(TEXT("path.maxChevrons"), Pool);
	N(TEXT("look.phases"), Phases);
	Out.Phases = FMath::Clamp(FMath::RoundToInt32(Phases), 1, 8);
	// The pool is a multiple of the phases (a pool entry keeps its phase) and holds every slot the reach can show.
	const int32 Need = FMath::CeilToInt32(Out.Reach / FMath::Max(Out.Spacing, 0.1)) + 2;
	Out.MaxChevrons = FMath::Max(FMath::RoundToInt32(Pool), Need);
	Out.MaxChevrons = FMath::DivideAndRoundUp(Out.MaxChevrons, Out.Phases) * Out.Phases;
	Out.Mesh = MIJson::StringOr(Root, TEXT("look.mesh"), Out.Mesh);
	Out.Material = MIJson::StringOr(Root, TEXT("look.material"), Out.Material);
	N(TEXT("look.armLength"), Out.ArmLength);
	N(TEXT("look.armWidth"), Out.ArmWidth);
	N(TEXT("look.armAngle"), Out.ArmAngle);
	N(TEXT("look.shadeReach"), Out.ShadeReach);
	N(TEXT("look.lift"), Out.Lift);
	const FVector C = Triple(MIJson::Get(Root, TEXT("look.color")), FVector(Out.Color.R, Out.Color.G, Out.Color.B));
	Out.Color = FLinearColor(C.X, C.Y, C.Z, 1.f);
	N(TEXT("look.intensity"), Out.Intensity);
	N(TEXT("look.shade"), Out.Shade);
	N(TEXT("look.combat"), Out.Combat);
	N(TEXT("look.combatFade"), Out.CombatFade);
	N(TEXT("look.chase"), Out.Chase);
	Out.UnderMaterial = MIJson::StringOr(Root, TEXT("look.underlay.material"), Out.UnderMaterial);
	const FVector UC = Triple(MIJson::Get(Root, TEXT("look.underlay.color")), FVector(Out.UnderColor.R, Out.UnderColor.G, Out.UnderColor.B));
	Out.UnderColor = FLinearColor(UC.X, UC.Y, UC.Z, 1.f);
	N(TEXT("look.underlay.width"), Out.UnderWidth);
	N(TEXT("look.underlay.longer"), Out.UnderLonger);
	N(TEXT("look.underlay.drop"), Out.UnderDrop);
	N(TEXT("look.low"), Out.Low);
	N(TEXT("marker.fadeFar"), Out.MarkerFar);
	N(TEXT("marker.fadeNear"), Out.MarkerNear);
	N(TEXT("marker.edge"), Out.MarkerEdge);
	N(TEXT("hints.after"), Out.HintAfter);
	N(TEXT("hints.progress"), Out.Progress);
	Out.Hints.Reset();
	Out.WaysDown.Reset();
	const TSharedPtr<FJsonValue> LevelValue = MIJson::Get(Root, FString::Printf(TEXT("levels.%s"), *Level.ToString()));
	if (!LevelValue.IsValid() || LevelValue->Type != EJson::Object)
	{
		OutError = FString::Printf(TEXT("guide.json has no levels.%s: no hint lines"), *Level.ToString());
		return true;  // the path and the markers work without them
	}
	const TSharedPtr<FJsonObject> L = LevelValue->AsObject();
	const TSharedPtr<FJsonObject>* Steps = nullptr;
	if (L->TryGetObjectField(TEXT("steps"), Steps))
	{
		for (const auto& Pair : (*Steps)->Values)
		{
			const TSharedPtr<FJsonObject>* S = nullptr;
			FString Line;
			if (Pair.Value.IsValid() && Pair.Value->TryGetObject(S) && (*S)->TryGetStringField(TEXT("hint"), Line))
			{
				Out.Hints.Add(FName(*FString(*Pair.Key)), Line);
			}
		}
	}
	const TArray<TSharedPtr<FJsonValue>>* Ways = nullptr;
	if (L->TryGetArrayField(TEXT("waysDown"), Ways))
	{
		for (const TSharedPtr<FJsonValue>& V : *Ways)
		{
			const TSharedPtr<FJsonObject>* W = nullptr;
			if (!V.IsValid() || !V->TryGetObject(W))
			{
				continue;
			}
			FMIGuideTune::FWayDown D;
			(*W)->TryGetStringField(TEXT("name"), D.Name);
			D.Top = Triple((*W)->TryGetField(TEXT("top")), FVector::ZeroVector);
			D.Foot = Triple((*W)->TryGetField(TEXT("foot")), FVector::ZeroVector);
			Out.WaysDown.Add(D);
		}
	}
	return true;
}

// ------------------------------------------------------------------------------------------------------- plan

int32 FMIGuidePlan::NextStep(const TArray<bool>& Secured)
{
	if (Secured.Num() == 0)
	{
		return NoStep;
	}
	for (int32 I = 0; I < Secured.Num(); ++I)
	{
		if (!Secured[I])
		{
			return I;
		}
	}
	return ExtractionStep;
}

int32 FMIGuidePlan::NextStep(const FMIGameRules& Rules, const FMILevelData& Level)
{
	for (int32 I = 0; I < Level.Objectives.Num(); ++I)
	{
		if (!Rules.IsSecured(I))
		{
			return I;
		}
	}
	return Level.Objectives.Num() > 0 ? ExtractionStep : NoStep;
}

void FMIGuidePlan::Init(const FMIGuideTune& InTune, const FMILevelData* InLevel)
{
	Tune = InTune;
	Level = InLevel;
	Reset();
}

void FMIGuidePlan::Reset()
{
	Step = NoStep;
	Goal = FVector::ZeroVector;
	Path.Reset();
	Cum.Reset();
	Chevrons.Reset();
	SlotCache.Reset();
	SinceSearch = 1e9;
	Remaining = OffRoute = NoProgress = Combat = 0.0;
	Best = 1e9;
	LaidAt = -1e9;
	bHint = false;
	Hint.Reset();
}

FName FMIGuidePlan::GetStepId() const
{
	if (Step == ExtractionStep)
	{
		return TEXT("extraction");
	}
	return Level && Level->Objectives.IsValidIndex(Step) ? Level->Objectives[Step].Id : NAME_None;
}

FVector FMIGuidePlan::GoalOf(int32 InStep) const
{
	if (!Level)
	{
		return FVector::ZeroVector;
	}
	if (InStep == ExtractionStep)
	{
		return Level->Extraction.Pos;
	}
	return Level->Objectives.IsValidIndex(InStep) ? Level->Objectives[InStep].Pos : FVector::ZeroVector;
}

double FMIGuidePlan::FloorAt(FMIBoxWorld& Nav, const FVector& At, double Below) const
{
	return Nav.GroundHeight(At.X, At.Z, Below);
}

bool FMIGuidePlan::Search(const FVector& Feet, FMIBoxWorld& Nav, TArray<FVector>& Out) const
{
	Out.Reset();
	FVector Start = Feet;
	// An upper floor (the scaffold shed's deck, the station, the chop shop's mezzanine): first down the nearest stair on
	// that floor, never straight through a parapet to the street under it.
	const double Ground = FloorAt(Nav, Feet, Tune.StepUp);
	if (Feet.Y - Ground > Tune.Elevated)
	{
		const FMIGuideTune::FWayDown* Way = nullptr;
		double BestD = TNumericLimits<double>::Max();
		for (const FMIGuideTune::FWayDown& W : Tune.WaysDown)
		{
			const double D = MIGuidePrivate::Flat(W.Top, Feet);
			if (FMath::Abs(W.Top.Y - Feet.Y) < 0.8 && D < BestD)
			{
				BestD = D;
				Way = &W;
			}
		}
		if (Way)
		{
			Out.Add(Feet);
			Out.Add(Way->Top);
			Out.Add(Way->Foot);
			Start = Way->Foot;
		}
	}
	TArray<FVector>& Pts = SearchBuf;
	if (!Nav.FindPath(FVector(Start.X, 0.0, Start.Z), FVector(Goal.X, 0.0, Goal.Z), Pts) || Pts.Num() == 0)
	{
		Out.Reset();
		return false;
	}
	for (int32 I = Out.Num() > 0 ? 1 : 0; I < Pts.Num(); ++I)
	{
		const FVector& P = Pts[I];
		Out.Add(FVector(P.X, FloorAt(Nav, P, Tune.StepUp), P.Z));
	}
	if (Out.Num() == 1)
	{
		Out.Add(FVector(Goal.X, FloorAt(Nav, Goal, Tune.StepUp), Goal.Z));
	}
	return Out.Num() >= 2;
}

void FMIGuidePlan::Project(const FVector& P, double& OutS, double& OutDist) const
{
	OutS = 0.0;
	OutDist = TNumericLimits<double>::Max();
	for (int32 I = 0; I + 1 < Path.Num(); ++I)
	{
		const FVector2D A(Path[I].X, Path[I].Z), B(Path[I + 1].X, Path[I + 1].Z), Q(P.X, P.Z);
		const FVector2D AB = B - A;
		const double L2 = AB.SizeSquared();
		const double T = L2 > 1e-12 ? FMath::Clamp(FVector2D::DotProduct(Q - A, AB) / L2, 0.0, 1.0) : 0.0;
		const double D = FVector2D::Distance(Q, A + AB * T);
		if (D < OutDist - 1e-9)
		{
			OutDist = D;
			OutS = Cum[I] + (Cum[I + 1] - Cum[I]) * T;
		}
	}
	if (OutDist == TNumericLimits<double>::Max())
	{
		OutDist = 0.0;
	}
}

void FMIGuidePlan::Lay(FMIBoxWorld& Nav, double S0)
{
	Chevrons.Reset();
	if (!HasRoute())
	{
		return;
	}
	const double Spacing = FMath::Max(Tune.Spacing, 0.2);
	const double End = Cum.Last() - Tune.StopShort;
	const int32 KMin = FMath::Max(0, FMath::CeilToInt32((End - (S0 + Tune.Reach)) / Spacing - 1e-9));
	for (int32 K = KMin; Chevrons.Num() < Tune.MaxChevrons - 1; ++K)
	{
		const double S = End - K * Spacing;
		if (S < S0 + Tune.Ahead || S < 0.0)
		{
			break;
		}
		if (SlotCache.Num() <= K)
		{
			SlotCache.SetNum(K + 1);
		}
		FSlot& C = SlotCache[K];
		if (!C.bValid)
		{
			// Where slot K lies on the route: its point, the way it points, the floor under it and a roof over it.
			int32 Seg = 0;
			while (Seg + 2 < Cum.Num() && Cum[Seg + 1] < S)
			{
				++Seg;
			}
			const double SegLen = Cum[Seg + 1] - Cum[Seg];
			const double T = SegLen > 1e-9 ? FMath::Clamp((S - Cum[Seg]) / SegLen, 0.0, 1.0) : 0.0;
			const FVector& A = Path[Seg];
			const FVector& B = Path[Seg + 1];
			FVector P = FMath::Lerp(A, B, T);
			// A segment on the ground follows kerbs and slabs; a stair or an upper floor keeps the heights it was given.
			if (A.Y < Tune.StepUp + 0.05 && B.Y < Tune.StepUp + 0.05)
			{
				P.Y = FloorAt(Nav, P, Tune.StepUp);
			}
			FVector D(B.X - A.X, 0.0, B.Z - A.Z);
			D = D.GetSafeNormal(1e-9, FVector(1, 0, 0));
			FMIRayHit Hit;
			C.Tip = P;
			C.Dir = D;
			C.bShade = Nav.Raycast(FVector(P.X, P.Y + 0.3, P.Z), FVector(0.0, 1.0, 0.0), Tune.ShadeReach, Hit);
			C.bValid = true;
		}
		FMIGuideChevron& V = Chevrons.AddDefaulted_GetRef();
		V.Tip = C.Tip;
		V.Dir = C.Dir;
		V.bShade = C.bShade;
		V.Slot = K;
		// Grown in at the player's end and at the far end of the reach, in steps of a tenth (a strip moves only when its
		// size changes by a step, not every frame of a walk).
		const double Near = (S - S0 - Tune.Ahead) / FMath::Max(Tune.FadeIn, 0.1);
		const double Far = (S0 + Tune.Reach - S) / FMath::Max(Tune.FadeIn, 0.1);
		const double Size = FMath::Clamp(0.25 + FMath::Min(Near, Far), 0.0, 1.0);
		V.Scale = FMath::RoundToDouble(Size * 10.0) / 10.0;
	}
}

bool FMIGuidePlan::Update(double Dt, const FMIGuideInput& In, FMIBoxWorld& Nav)
{
	Combat = FMath::Clamp(Combat + (In.bCombat ? Dt : -Dt) / FMath::Max(Tune.CombatFade, 1e-3), 0.0, 1.0);
	const int32 Want = In.bStory && Level ? NextStep(In.Secured) : NoStep;
	bool bChanged = false;
	if (Want != Step)
	{
		Step = Want;
		Path.Reset();
		Cum.Reset();
		SlotCache.Reset();
		SinceSearch = 1e9;
		Best = 1e9;
		NoProgress = 0.0;
		Remaining = OffRoute = 0.0;
		bHint = false;
		Hint.Reset();
		LaidAt = -1e9;
		if (Step != NoStep)
		{
			Goal = GoalOf(Step);
			if (const FString* H = Tune.Hints.Find(GetStepId()))
			{
				Hint = *H;
			}
		}
		if (Chevrons.Num() > 0)
		{
			Chevrons.Reset();
			bChanged = true;
		}
	}
	if (Step == NoStep)
	{
		return bChanged;
	}
	SinceSearch += Dt;
	double S0 = 0.0, Off = 0.0;
	if (HasRoute())
	{
		Project(In.Feet, S0, Off);
	}
	const bool bStray = HasRoute() && Off > Tune.Stray;
	const bool bDue = HasRoute() ? (SinceSearch >= Tune.Repath || (bStray && SinceSearch >= Tune.MinRepath)) : SinceSearch >= Tune.MinRepath;
	bool bNewRoute = false;
	const bool bHadRoute = HasRoute();
	if (bDue)
	{
		SinceSearch = 0.0;
		++Searches;
		TArray<FVector>& New = NewBuf;
		if (Search(In.Feet, Nav, New))
		{
			double Len = 0.0;
			for (int32 I = 0; I + 1 < New.Num(); ++I)
			{
				Len += FVector::Dist(New[I], New[I + 1]);
			}
			const double Left = HasRoute() ? FMath::Max(0.0, Cum.Last() - S0) + Off : TNumericLimits<double>::Max();
			// No flip between two routes of about the same length: the drawn one stays unless the player left it or
			// the new one is clearly shorter (an explosive opened a way, the player took a short cut).
			if (!HasRoute() || bStray || Len < Left * Tune.Keep)
			{
				Swap(Path, New);
				Cum.SetNum(Path.Num());
				Cum[0] = 0.0;
				for (int32 I = 1; I < Path.Num(); ++I)
				{
					Cum[I] = Cum[I - 1] + FVector::Dist(Path[I - 1], Path[I]);
				}
				SlotCache.Reset();
				Project(In.Feet, S0, Off);
				bNewRoute = true;
			}
		}
		else
		{
			++FailedSearches;
		}
	}
	if (bNewRoute && !bHadRoute)
	{
		Best = 1e9;  // the first route of a step: progress is measured along it from here
	}
	OffRoute = HasRoute() ? Off : 0.0;
	Remaining = HasRoute()
		? FMath::Max(0.0, Cum.Last() - S0) + Off + MIGuidePrivate::Flat(Path.Last(), Goal)
		: MIGuidePrivate::Flat(In.Feet, Goal);
	// Progress: closer along the route than ever before on this step.
	if (Remaining < Best - Tune.Progress || Best >= 1e9)
	{
		Best = Remaining;
		NoProgress = 0.0;
		bHint = false;
	}
	else if (In.bClock && !In.bCombat)
	{
		NoProgress += Dt;
	}
	if (!Hint.IsEmpty() && NoProgress >= Tune.HintAfter)
	{
		bHint = true;
	}
	if (HasRoute())
	{
		if (bNewRoute || FMath::Abs(S0 - LaidAt) > 0.25)
		{
			Lay(Nav, S0);
			LaidAt = S0;
			bChanged = true;
		}
	}
	else if (Chevrons.Num() > 0)
	{
		Chevrons.Reset();
		bChanged = true;
	}
	return bChanged;
}

// ------------------------------------------------------------------------------------------------------- actor

AMIGuide::AMIGuide()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = true;
	PrimaryActorTick.TickGroup = TG_PostUpdateWork;  // after the player and the flow have moved this frame
	SetCanBeDamaged(false);
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

AMIGuide* AMIGuide::Find(const UWorld* World)
{
	if (!World)
	{
		return nullptr;
	}
	TActorIterator<AMIGuide> It(const_cast<UWorld*>(World));
	return It ? *It : nullptr;
}

AMIGuide* AMIGuide::Ensure(UWorld* World)
{
	if (!World || !World->IsGameWorld())
	{
		return nullptr;
	}
	if (AMIGuide* G = Find(World))
	{
		return G;
	}
	FActorSpawnParameters P;
	P.ObjectFlags |= RF_Transient;
	P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	return World->SpawnActor<AMIGuide>(AMIGuide::StaticClass(), FTransform::Identity, P);
}

void AMIGuide::BeginPlay()
{
	Super::BeginPlay();
	FString Error;
	if (!FMIGuideTune::Load(Tune, Error))
	{
		UE_LOG(LogMI, Warning, TEXT("Guide: %s (built-in defaults, no hint lines)"), *Error);
	}
	else if (!Error.IsEmpty())
	{
		UE_LOG(LogMI, Log, TEXT("Guide: %s"), *Error);
	}
	Plan.Init(Tune, FMILevelData::Get());
	Build();
}

void AMIGuide::Build()
{
	// At the start of the map, never in play: the plane and the tracer material are loaded by then anyway (effects).
	UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, *Tune.Mesh);
	UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr, *Tune.Material);
	if (!Mesh || !Mat)
	{
		UE_LOG(LogMI, Log, TEXT("Guide: %s or %s is not in this project: no ground path (the markers and hints still work)"), *Tune.Mesh, *Tune.Material);
		return;
	}
	Mats.Reset();
	for (int32 Shade = 0; Shade < 2; ++Shade)
	{
		for (int32 Phase = 0; Phase < Tune.Phases; ++Phase)
		{
			UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(Mat, this);
			M->SetVectorParameterValue(TEXT("Color"), Tune.Color);
			M->SetScalarParameterValue(TEXT("Intensity"), 0.f);
			Mats.Add(M);
		}
	}
	// The dark underlay's material (an engine material in every package: the plane's own), one instance for all strips.
	UMaterialInterface* UnderBase = Tune.UnderMaterial.IsEmpty() ? nullptr : LoadObject<UMaterialInterface>(nullptr, *Tune.UnderMaterial);
	UnderMat = nullptr;
	if (UnderBase)
	{
		UnderMat = UMaterialInstanceDynamic::Create(UnderBase, this);
		UnderMat->SetVectorParameterValue(TEXT("Color"), Tune.UnderColor);
	}
	else if (!Tune.UnderMaterial.IsEmpty())
	{
		UE_LOG(LogMI, Log, TEXT("Guide: %s is not in this project: chevrons without their dark underlay"), *Tune.UnderMaterial);
	}
	const int32 N = Tune.MaxChevrons * 2;
	Strips.Reset();
	Unders.Reset();
	for (int32 I = 0; I < N * (UnderMat ? 2 : 1); ++I)
	{
		const bool bUnder = I >= N;
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this, NAME_None, RF_Transient);
		C->SetMobility(EComponentMobility::Movable);
		C->SetUsingAbsoluteLocation(true);
		C->SetUsingAbsoluteRotation(true);
		C->SetUsingAbsoluteScale(true);
		C->SetStaticMesh(Mesh);
		// Nothing but a picture: no collision (bullets, the player and the enemies never meet it), no shadow, no part in
		// distance fields, Lumen or decals, nothing for navigation.
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetCollisionResponseToAllChannels(ECR_Ignore);
		C->SetGenerateOverlapEvents(false);
		C->SetCanEverAffectNavigation(false);
		C->SetCastShadow(false);
		C->bAffectDistanceFieldLighting = false;
		C->bAffectDynamicIndirectLighting = false;
		C->bReceivesDecals = false;
		C->SetVisibleInRayTracing(false);
		C->SetTranslucentSortPriority(-1);
		C->SetMaterial(0, bUnder ? static_cast<UMaterialInterface*>(UnderMat.Get()) : static_cast<UMaterialInterface*>(Mats[0].Get()));
		C->SetVisibility(false);
		C->SetupAttachment(RootComponent);
		C->RegisterComponent();
		(bUnder ? Unders : Strips).Add(C);
	}
	StripMat.Init(0, N);
	StripAt.Init(FTransform::Identity, N);
	StripOn.Init(false, N);
	PoolUsed.Init(false, Tune.MaxChevrons);
	bBuilt = true;
}

bool AMIGuide::SyncNav(const FMIBoxWorld& Source)
{
	if (&Source == NavSource && Source.GetRevision() == NavRevision && bHaveNav)
	{
		return false;
	}
	// A copy, so a search here never touches the simulation's search buffers. Only when the box list changed (a
	// run's start, an explosive gone): about a megabyte copied, then the grid rebuilt on the next search.
	Nav = Source;
	NavSource = &Source;
	NavRevision = Source.GetRevision();
	bHaveNav = true;
	return true;
}

void AMIGuide::Tick(float DeltaSeconds)
{
	TRACE_CPUPROFILER_EVENT_SCOPE_STR("MI/AMIGuide::Tick");
	Super::Tick(DeltaSeconds);
	Step(DeltaSeconds);
}

void AMIGuide::Step(double Dt)
{
	const double T0 = FPlatformTime::Seconds();
	Clock += Dt;
	UMIGameSubsystem* Game = UMIGameSubsystem::Get(this);
	FMIGuideInput& In = Input;
	In.bStory = In.bClock = In.bCombat = false;
	bool bOn = false;
	if (Game && Game->IsBooted() && Game->GetLevel() && Game->GetPlayer())
	{
		const FMIGameRules& R = Game->GetRules();
		const EMIGameState S = R.GetState();
		In.bStory = R.GetMode() == FName(TEXT("mission")) && (S == EMIGameState::Intro || S == EMIGameState::Playing);
		In.bClock = S == EMIGameState::Playing;
		In.Feet = Game->PlayerFeetWeb();
		const int32 NumObjectives = Game->GetLevel()->Objectives.Num();
		In.Secured.SetNum(NumObjectives, EAllowShrinking::No);
		for (int32 I = 0; I < NumObjectives; ++I)
		{
			In.Secured[I] = R.IsSecured(I);
		}
		const FMIEnemyField& Field = Game->GetEnemies();
		// GetList holds slot indexes (not the units' spawn ids, which Find takes): read the slot itself.
		const TArray<FMIEnemy>& Slots = Field.GetSlots();
		for (const int32 I : Field.GetList())
		{
			const FMIEnemy* E = Slots.IsValidIndex(I) ? &Slots[I] : nullptr;
			if (E && E->bAlive && E->Mode == EMIEnemyMode::Engage)
			{
				In.bCombat = true;
				break;
			}
		}
		bOn = Game->GetSettings().bGuide;
		if (In.bStory)
		{
			SyncNav(Game->GetBoxWorld());
		}
	}
	const int32 SearchesBefore = Plan.GetSearches();
	const double U0 = FPlatformTime::Seconds();
	const bool bMoved = bHaveNav ? Plan.Update(Dt, In, Nav) : false;
	const double UpdateMs = (FPlatformTime::Seconds() - U0) * 1000.0;
	if (Plan.GetSearches() != SearchesBefore)
	{
		Cost.Searches++;
		Cost.SearchMs += UpdateMs;
		Cost.WorstSearchMs = FMath::Max(Cost.WorstSearchMs, UpdateMs);
	}
	bShown = bOn && Plan.IsActive();
	if (bShown && bBuilt)
	{
		if (bMoved || !bDrawn)
		{
			Place();
		}
		Animate();
	}
	else if (bDrawn)
	{
		HideAll();
	}
	const double Ms = (FPlatformTime::Seconds() - T0) * 1000.0;
	Cost.Frames++;
	Cost.TotalMs += Ms;
	Cost.WorstMs = FMath::Max(Cost.WorstMs, Ms);
}

void AMIGuide::Place()
{
	const int32 Pool = Tune.MaxChevrons;
	for (bool& B : PoolUsed)
	{
		B = false;
	}
	const double A = FMath::DegreesToRadians(Tune.ArmAngle);
	const auto Set = [this](int32 I, const FTransform& T, int32 Mat)
	{
		UStaticMeshComponent* C = Strips[I];
		if (!StripOn[I])
		{
			C->SetVisibility(true);
			StripOn[I] = true;
		}
		if (!StripAt[I].Equals(T, 0.1))
		{
			C->SetWorldTransform(T);
			StripAt[I] = T;
			Cost.Moves++;
			if (Unders.IsValidIndex(I))
			{
				// Wider, a little longer and just under the lit strip (its arm direction is the plane's X).
				const FVector Scale = T.GetScale3D();
				const FVector Down(0.0, 0.0, -Tune.UnderDrop * 100.0);
				Unders[I]->SetWorldTransform(FTransform(T.GetRotation(), T.GetLocation() + Down,
					FVector(Scale.X + Tune.UnderLonger, Scale.Y * Tune.UnderWidth, 1.0)));
			}
		}
		if (Unders.IsValidIndex(I) && !Unders[I]->IsVisible())
		{
			Unders[I]->SetVisibility(true);
		}
		if (StripMat[I] != Mat && Mats.IsValidIndex(Mat))
		{
			C->SetMaterial(0, Mats[Mat]);
			StripMat[I] = Mat;
		}
	};
	for (const FMIGuideChevron& V : Plan.GetChevrons())
	{
		const int32 P = V.Slot % Pool;
		if (PoolUsed[P] || V.Scale <= 0.0)
		{
			continue;
		}
		PoolUsed[P] = true;
		const FVector Tip = MI::Web::ToUnreal(V.Tip) + FVector(0.0, 0.0, Tune.Lift * 100.0);
		const FVector Dir = MI::Web::ToUnreal(V.Dir).GetSafeNormal2D();
		const FVector Side(-Dir.Y, Dir.X, 0.0);
		const double Len = Tune.ArmLength * V.Scale;
		const int32 Mat = (V.Slot % Tune.Phases) + (V.bShade ? Tune.Phases : 0);
		for (int32 S = 0; S < 2; ++S)
		{
			const double Sign = S == 0 ? -1.0 : 1.0;
			const FVector Back = -Dir * FMath::Cos(A) + Side * (Sign * FMath::Sin(A));
			// The engine plane is 1 m square about its centre: an arm from the tip back along Back.
			const FVector Centre = Tip + Back * (Len * 50.0);
			const FRotator Rot(0.0, FMath::RadiansToDegrees(FMath::Atan2(Back.Y, Back.X)), 0.0);
			Set(P * 2 + S, FTransform(Rot, Centre, FVector(Len, Tune.ArmWidth * V.Scale, 1.0)), Mat);
		}
	}
	for (int32 P = 0; P < Pool; ++P)
	{
		if (PoolUsed[P])
		{
			continue;
		}
		for (int32 S = 0; S < 2; ++S)
		{
			const int32 I = P * 2 + S;
			if (StripOn[I])
			{
				Strips[I]->SetVisibility(false);
				StripOn[I] = false;
				if (Unders.IsValidIndex(I))
				{
					Unders[I]->SetVisibility(false);
				}
			}
		}
	}
	bDrawn = true;
}

void AMIGuide::Animate()
{
	// A light that runs toward the goal: phase group g peaks when Clock * chase + g / phases is a whole number, so the
	// peak moves to lower slots (nearer the goal) as time goes on. Calmer while an enemy is engaging.
	const double Strength = FMath::Lerp(1.0, Tune.Combat, Plan.GetCombat());
	for (int32 G = 0; G < Tune.Phases; ++G)
	{
		const double Pulse = 0.5 + 0.5 * FMath::Cos(2.0 * UE_DOUBLE_PI * (Clock * Tune.Chase + static_cast<double>(G) / Tune.Phases));
		const double K = (Tune.Low + (1.0 - Tune.Low) * Pulse) * Strength * Tune.Intensity;
		if (Mats.IsValidIndex(G + Tune.Phases))
		{
			Mats[G]->SetScalarParameterValue(TEXT("Intensity"), static_cast<float>(K));
			Mats[G + Tune.Phases]->SetScalarParameterValue(TEXT("Intensity"), static_cast<float>(K * Tune.Shade));
		}
	}
}

void AMIGuide::HideAll()
{
	for (int32 I = 0; I < Strips.Num(); ++I)
	{
		if (StripOn[I])
		{
			Strips[I]->SetVisibility(false);
			StripOn[I] = false;
			if (Unders.IsValidIndex(I))
			{
				Unders[I]->SetVisibility(false);
			}
		}
	}
	bDrawn = false;
}

int32 AMIGuide::VisibleStrips() const
{
	int32 N = 0;
	for (const bool B : StripOn)
	{
		N += B ? 1 : 0;
	}
	return N;
}
