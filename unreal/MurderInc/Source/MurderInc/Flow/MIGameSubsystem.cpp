#include "Flow/MIGameSubsystem.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

#include "AudioDevice.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Audio/MIAudioSubsystem.h"
#include "Cloud/MICloud.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Flow/MIRunSetupSubsystem.h"
#include "UI/MIFrontEnd.h"
#include "Weapons/MILoadoutResolver.h"
#include "Core/MIEvents.h"
#include "Dom/JsonObject.h"
#include "Enemies/MIEnemyActors.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/GameUserSettings.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "MurderInc.h"
#include "Player/MIPlayerCharacter.h"
#include "Player/MILookInput.h"
#include "Player/MIPlayerController.h"
#include "Weapons/MICombatSubsystem.h"
#include "Weapons/MIWeaponComponent.h"
#include "World/MIBlockGeometry.h"
#include "World/MIExplosive.h"
#include "World/MILevelData.h"
#include "Weapons/MIEffects.h"
#include "World/MIObjectiveActors.h"

namespace MIGameSubsystemPrivate
{
	inline FVector DirToUnreal(const FVector& D) { return FVector(D.X, D.Z, D.Y); }
	inline FVector DirFromUnreal(const FVector& D) { return FVector(D.X, D.Z, D.Y); }

	FName ArtTag()
	{
		TSharedPtr<FJsonObject> P;
		FString Error, Tag = TEXT("MIBlock");
		const TSharedPtr<FJsonObject>* Block = nullptr;
		if (UMIDataSubsystem::LoadJsonFile(TEXT("presentation.json"), P, Error) && P->TryGetObjectField(TEXT("block"), Block))
		{
			(*Block)->TryGetStringField(TEXT("artTag"), Tag);
		}
		return FName(Tag);
	}

	/** presentation.json block.startPitch: the view's pitch (degrees, up positive) when a run puts the player on the
	 *  start. The start pose itself is the web game's; at pitch 0 the open trash can 1.1 m ahead (prop 270) filled
	 *  the bottom of every run's first frame, a few degrees up the frame looks down the avenue under the El. */
	double StartPitch()
	{
		TSharedPtr<FJsonObject> P;
		FString Error;
		double Pitch = 0.0;
		const TSharedPtr<FJsonObject>* Block = nullptr;
		if (UMIDataSubsystem::LoadJsonFile(TEXT("presentation.json"), P, Error) && P->TryGetObjectField(TEXT("block"), Block))
		{
			(*Block)->TryGetNumberField(TEXT("startPitch"), Pitch);
		}
		return Pitch;
	}
}

void FMIGameFrameTick::ExecuteTick(float DeltaTime, ELevelTick TickType, ENamedThreads::Type CurrentThread, const FGraphEventRef& MyCompletionGraphEvent)
{
	if (Target)
	{
		if (bEnemies)
		{
			Target->EnemyFrame(DeltaTime);
		}
		else
		{
			Target->FlowFrame(DeltaTime);
		}
	}
}

UMIGameSubsystem* UMIGameSubsystem::Get(const UObject* WorldContextObject)
{
	const UWorld* World = WorldContextObject ? WorldContextObject->GetWorld() : nullptr;
	return World ? World->GetSubsystem<UMIGameSubsystem>() : nullptr;
}

bool UMIGameSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
	const UWorld* World = Cast<UWorld>(Outer);
	return World && (World->WorldType == EWorldType::Game || World->WorldType == EWorldType::PIE);
}

void UMIGameSubsystem::Deinitialize()
{
	FlowTick.UnRegisterTickFunction();
	EnemyTick.UnRegisterTickFunction();
	Super::Deinitialize();
}

AMIPlayerCharacter* UMIGameSubsystem::GetPlayer() const
{
	if (!Player.IsValid() && GetWorld())
	{
		if (TActorIterator<AMIPlayerCharacter> It(GetWorld()); It)
		{
			Player = *It;
		}
	}
	return Player.Get();
}

AActor* UMIGameSubsystem::GetEnemyActor(int32 Slot) const
{
	return EnemyActors.IsValidIndex(Slot) ? EnemyActors[Slot].Get() : nullptr;
}

AMIReelCase* UMIGameSubsystem::GetCase(int32 Index) const
{
	return Cases.IsValidIndex(Index) ? Cases[Index].Get() : nullptr;
}

// ============================================================================================================ boot

bool UMIGameSubsystem::Boot(const FMIBootOptions& Options)
{
	using namespace MI::Web;
	UWorld* World = GetWorld();
	if (bBooted || !World)
	{
		return bBooted;
	}
	Boots = Options;
	FString Error;
	Level = FMILevelData::Get();
	TSharedPtr<FJsonObject> Config, TextJson, RulesJson;
	FMIEnemyLook Look;
	if (!Level || !UMIDataSubsystem::LoadJsonFile(TEXT("config.json"), Config, Error) || !FMIFlowTune::Parse(Config, FlowTune, Error) || !FMIText::Load(Copy, Error)
		|| !UMIDataSubsystem::LoadJsonFile(TEXT("text.json"), TextJson, Error) || !FMISettings::LoadDefaults(Settings, Error) || !FMIEnemyLook::Load(Look, Error)
		|| !UMIDataSubsystem::LoadJsonFile(TEXT("rules.json"), RulesJson, Error))
	{
		UE_LOG(LogMI, Error, TEXT("Game: cannot boot: %s"), Level ? *Error : TEXT("level.json did not load"));
		return false;
	}
	const TSharedPtr<FJsonObject>* Interface = nullptr;
	if (TextJson->TryGetObjectField(TEXT("interface"), Interface))
	{
		Ui.Root = *Interface;
	}
	const TSharedPtr<FJsonObject>* Input = nullptr;
	if (TextJson->TryGetObjectField(TEXT("input"), Input))
	{
		Keys.Root = *Input;
	}
	for (const FName D : Settings.Rules.Difficulties)
	{
		FMIEnemyTune& T = Tunes.Add(D);
		if (!FMIEnemyTune::Load(D, T, Error))
		{
			UE_LOG(LogMI, Error, TEXT("Game: enemy table %s: %s"), *D.ToString(), *Error);
			return false;
		}
	}
	const TSharedPtr<FJsonObject>* RP = nullptr;
	const TSharedPtr<FJsonObject>* Target = nullptr;
	if (RulesJson->TryGetObjectField(TEXT("player"), RP) && (*RP)->TryGetObjectField(TEXT("shotTarget"), Target))
	{
		(*Target)->TryGetNumberField(TEXT("radius"), ShotTargetRadius);
		(*Target)->TryGetNumberField(TEXT("standing"), ShotTargetStand);
		(*Target)->TryGetNumberField(TEXT("crouching"), ShotTargetCrouch);
	}
	const TSharedPtr<FJsonObject>* Flow = nullptr;
	const TSharedPtr<FJsonObject>* TitleCam = nullptr;
	if (Config->TryGetObjectField(TEXT("flow"), Flow) && (*Flow)->TryGetObjectField(TEXT("titleCamera"), TitleCam))
	{
		(*TitleCam)->TryGetNumberField(TEXT("speed"), TitleSpeed);
		(*TitleCam)->TryGetNumberField(TEXT("fadeIn"), TitleFadeIn);
	}
	// Times of day: only those the default level offers (levels.json levels.<default>.times). Night has no lighting
	// rig yet, so the block offers day only; a saved "night" is then refused by SetTime and the run plays by day.
	{
		TSharedPtr<FJsonObject> LevelsJson;
		FString LevelsError;
		const TSharedPtr<FJsonObject>* Levels = nullptr;
		const TSharedPtr<FJsonObject>* Lv = nullptr;
		FString DefaultLevel;
		if (UMIDataSubsystem::LoadJsonFile(TEXT("levels.json"), LevelsJson, LevelsError) && LevelsJson->TryGetStringField(TEXT("default"), DefaultLevel)
			&& LevelsJson->TryGetObjectField(TEXT("levels"), Levels) && (*Levels)->TryGetObjectField(DefaultLevel, Lv))
		{
			const TArray<TSharedPtr<FJsonValue>>* Offered = nullptr;
			if ((*Lv)->TryGetArrayField(TEXT("times"), Offered) && Offered->Num() > 0)
			{
				TArray<FName> Keep;
				for (const TSharedPtr<FJsonValue>& V : *Offered)
				{
					const FName T(V->AsString());
					if (Settings.Rules.Times.Contains(T)) Keep.Add(T);
				}
				if (Keep.Num() > 0)
				{
					Settings.Rules.Times = Keep;
					if (!Keep.Contains(Settings.Time)) Settings.Time = Keep[0];
				}
			}
		}
	}
	const UMISaveGame* Save = Options.bPersist ? Cast<UMISaveGame>(UGameplayStatics::LoadGameFromSlot(Settings.Rules.Slot, 0)) : nullptr;
	if (Save)
	{
		Settings.FromSave(*Save);
	}
	if (!Options.Mode.IsNone())
	{
		Settings.SetMode(Options.Mode);
	}
	if (!Options.Difficulty.IsNone())
	{
		Settings.SetDifficulty(Options.Difficulty);
	}
	uint32 Seed = 1994;
	double SeedValue = 0;
	const TSharedPtr<FJsonObject>* Meta = nullptr;
	if (Config->TryGetObjectField(TEXT("meta"), Meta) && (*Meta)->TryGetNumberField(TEXT("seed"), SeedValue))
	{
		Seed = static_cast<uint32>(SeedValue);
	}
	const FMIRng Root(Seed);

	// The block: the box world the rules run on and the same boxes as engine collision.
	Level->FillWorld(Box, Root);
	const FName Tag = MIGameSubsystemPrivate::ArtTag();
	bArt = AMIBlockGeometry::WorldHasArt(World, Tag);
	if (bArt)
	{
		const int32 Off = AMIBlockGeometry::DisableArtCollision(World, Tag);
		UE_LOG(LogMI, Log, TEXT("Game: art map: %d art collision primitives switched off, the data's boxes decide"), Off);
	}
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	Params.ObjectFlags |= RF_Transient;
	Geometry = World->SpawnActor<AMIBlockGeometry>(FVector::ZeroVector, FRotator::ZeroRotator, Params);
	Geometry->Build(*Level, Options.bDrawGrey.Get(!bArt));

	// The explosives in level order: item i of the combat field is level explosive i (the box world's owner index).
	for (const FMILevelExplosive& X : Level->Explosives)
	{
		const FTransform At(FRotator(0, YawToUnreal(X.Yaw), 0), ToUnreal(X.Pos));
		AMIExplosive* E = World->SpawnActorDeferred<AMIExplosive>(AMIExplosive::StaticClass(), At, nullptr, nullptr, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
		E->Kind = X.Type;
		E->FinishSpawning(At);
		if (E->GetIndex() != X.Index)
		{
			UE_LOG(LogMI, Warning, TEXT("Game: explosive %d took combat item %d (another explosive is in the map)"), X.Index, E->GetIndex());
		}
		Explosives.Add(E);
	}

	// Both pools, pre-spawned and hidden: slot i of the field is actor i.
	const FMIEnemyTune& Tune = Tunes.FindChecked(Settings.Difficulty);
	Field.Init(Tune, Level, &Box, this);
	for (int32 Slot = 0; Slot < Field.GetSlots().Num(); ++Slot)
	{
		const FVector Away(0, 0, -100000.0);
		if (Field.GetSlots()[Slot].IsGoon())
		{
			AMIGoon* G = World->SpawnActor<AMIGoon>(Away, FRotator::ZeroRotator, Params);
			G->Setup(Slot, Look, Tune.Goon);
			EnemyActors.Add(G);
		}
		else
		{
			AMIBuzzard* B = World->SpawnActor<AMIBuzzard>(Away, FRotator::ZeroRotator, Params);
			B->Setup(Slot, Look, Tune.Buzzard, Field.Model);
			EnemyActors.Add(B);
		}
	}

	for (int32 I = 0; I < Level->Objectives.Num(); ++I)
	{
		const FMILevelObjective& O = Level->Objectives[I];
		AMIReelCase* C = World->SpawnActor<AMIReelCase>(ToUnreal(O.Pos), FRotator(0, YawToUnreal(O.Yaw), 0), Params);
		C->Setup(I, O.Id);
		Cases.Add(C);
	}
	Truck = World->SpawnActor<AMITruck>(ToUnreal(Level->TruckPos), FRotator(0, YawToUnreal(Level->TruckYaw), 0), Params);
	Truck->Setup(!bArt);
	TitleCamera = World->SpawnActor<ACameraActor>(FVector::ZeroVector, FRotator::ZeroRotator, Params);
	if (TitleCamera && TitleCamera->GetCameraComponent())
	{
		TitleCamera->GetCameraComponent()->SetConstraintAspectRatio(false);  // fills 21:9 and wider, no pillarbox
	}

	Rules.Init(FlowTune, Copy, Level, &Box, &Field, this, Root);
	Rules.SetDifficulty(Settings.Difficulty);
	BindEvents();

	FlowTick.Target = this;
	FlowTick.bEnemies = false;
	FlowTick.TickGroup = TG_PrePhysics;
	FlowTick.bCanEverTick = true;
	FlowTick.bTickEvenWhenPaused = true;
	FlowTick.RegisterTickFunction(World->PersistentLevel);
	EnemyTick.Target = this;
	EnemyTick.bEnemies = true;
	EnemyTick.TickGroup = TG_PostUpdateWork;
	EnemyTick.bCanEverTick = true;
	EnemyTick.RegisterTickFunction(World->PersistentLevel);

	bBooted = true;
	// The remembered set-up (LOADOUT.md 7), validated against what is offered now, and the set-up flow.
	if (UMIRunSetupSubsystem* RunSetup = UMIRunSetupSubsystem::Get(this))
	{
		RunSetup->Load(Save, Settings);
	}
	FString RootsError;
	FMILoadoutResolver::LoadRoots(ResolverConfig, ResolverPresentation, RootsError);
	if (Copy.Root.IsValid())
	{
		const UMIDataSubsystem* Data = UMIDataSubsystem::Get(this);
		if (Data && Data->IsLoadoutLoaded())
		{
			for (const TPair<FString, FString>& R : Data->GetLoadout().CrewReplaces)
			{
				OriginalLines.Add(R.Key, MIJson::StringOr(Copy.Root, R.Key.Mid(5)));
			}
		}
	}
	if (Options.bTitle)
	{
		FrontEnd = NewObject<UMIFrontEnd>(this);
		if (!FrontEnd->Init(this))
		{
			FrontEnd = nullptr;
		}
	}
	ApplySettings();
	ResetPlayer(Level->PlayerStart.Pos, Level->PlayerStart.Yaw);
	if (!Options.bTitle)
	{
		StartRun(Settings.Mode, Options.bSkipIntro);
	}
	ApplyState();
	UE_LOG(LogMI, Log, TEXT("Game: booted (%s map, %d boxes, %d explosives, %d enemy slots, %d reels)"), bArt ? TEXT("art") : TEXT("grey-box"), Geometry->NumBoxes(), Explosives.Num(), EnemyActors.Num(), Cases.Num());
	return true;
}

void UMIGameSubsystem::BindEvents()
{
	using namespace MI::Web;
	FMIGameEvents* Events = UMIEventSubsystem::Get(this);
	if (!Events)
	{
		return;
	}
	Events->WeaponFire.AddWeakLambda(this, [this](const FMIShotFiredEvent& E)
	{
		RunStats.Shots++;
		// The gun's noise radius (a silencer shrinks it); the default radius takes the web's own call.
		if (E.NoiseRadius > 0.0 && E.NoiseRadius != Field.GetTune().Ai.HearGunfire * 100.0)
		{
			Field.Gunfire(FromUnreal(E.Muzzle), E.NoiseRadius / 100.0);
		}
		else
		{
			Field.Gunfire(FromUnreal(E.Muzzle));
		}
	});
	Events->PlayerHitEnemy.AddWeakLambda(this, [this](const FMIHitEnemyEvent& E)
	{
		if (E.Weapon != TEXT("melee") && E.Weapon != TEXT("blast"))
		{
			RunStats.Hits++;
		}
	});
	Events->Explosion.AddWeakLambda(this, [this](const FMIExplosionEvent& E)
	{
		Field.Explosion(FromUnreal(E.Position), Field.GetTune().Ai.HearExplosion);
	});
	Events->ExplosiveBlast.AddWeakLambda(this, [this](int32 Index, const FVector& Centre)
	{
		// The collider goes before the blast resolves (explosives.js blow), so it shields nothing; the block hears it.
		Box.RemoveOwner(Index);
		RemovedOwners.Add(Index);
		Field.Alert(FromUnreal(Centre), Field.GetTune().Ai.HearExplosive);
	});
	Events->PlayerHit.AddWeakLambda(this, [this](const FMIPlayerHitEvent&) { Rules.OnPlayerHit(); });
	Events->PlayerDead.AddWeakLambda(this, [this](const TOptional<FVector>&)
	{
		Rules.OnPlayerDead();
		ForwardFlow();
	});
}

// ======================================================================================================== commands

void UMIGameSubsystem::StartRun(FName Mode, bool bSkipIntro)
{
	if (!bBooted)
	{
		return;
	}
	Settings.SetMode(Mode.IsNone() ? Settings.Mode : Mode);
	Rules.SetDifficulty(Settings.Difficulty);
	Rules.Start(Settings.Mode, bSkipIntro);
	ForwardFlow();
	ApplyState();
}

void UMIGameSubsystem::StartRunWithSetup(FName Mode, bool bSkipIntro)
{
	// The same resolver as the set-up screens: a run started from the console draws the real arms and guns too.
	const UMIRunSetupSubsystem* RunSetup = UMIRunSetupSubsystem::Get(this);
	FMIRunSetup S = RunSetup && RunSetup->HasSetup() ? RunSetup->GetSetup() : FMIRunSetup();
	if (!ApplySetup(S))
	{
		UE_LOG(LogMI, Warning, TEXT("MIStart: the set-up did not resolve: the run keeps the guns it had"));
	}
	StartRun(Mode, bSkipIntro);
}

void UMIGameSubsystem::Pause()
{
	Rules.Pause();
	ForwardFlow();
	ApplyState();
}

void UMIGameSubsystem::Resume()
{
	Rules.Resume();
	ForwardFlow();
	ApplyState();
}

void UMIGameSubsystem::PauseKey()
{
	const EMIGameState S = Rules.GetState();
	if (S == EMIGameState::Playing || S == EMIGameState::Intro)
	{
		Pause();
	}
	else if (S == EMIGameState::Paused)
	{
		if (Menu.Screen == EMIMenuScreen::Settings)
		{
			MenuBack();
		}
		else if (Rules.GetStateTime() >= FlowTune.PauseDebounce)
		{
			Resume();
		}
	}
	else if (Menu.Screen == EMIMenuScreen::Settings)
	{
		MenuBack();
	}
}

void UMIGameSubsystem::Restart()
{
	Rules.Restart();
	ForwardFlow();
	ApplyState();
}

void UMIGameSubsystem::Retry()
{
	Rules.Retry();
	ForwardFlow();
	ApplyState();
}

void UMIGameSubsystem::Redeploy()
{
	Rules.Redeploy();
	ForwardFlow();
	ApplyState();
}

void UMIGameSubsystem::ToTitle()
{
	Rules.ToTitle();
	ForwardFlow();
	ApplyState();
}

void UMIGameSubsystem::SetDifficulty(FName Difficulty)
{
	if (Settings.SetDifficulty(Difficulty))
	{
		SaveSettings();
	}
	Rules.SetDifficulty(Settings.Difficulty);
}

// =========================================================================================================== menus

void UMIGameSubsystem::RebuildMenu()
{
	Menu.Build(Menu.Screen, Settings, Copy, Ui, Rules.Card(), Rules.GetMode());
	PatchCards();
}

void UMIGameSubsystem::PatchCards()
{
	if (!FrontEnd || Menu.IndexOf(TEXT("changesetup")) != INDEX_NONE)
	{
		return;
	}
	if (Menu.Screen == EMIMenuScreen::Pause)
	{
		// The pause card gains Change set-up and Back to title after its own rows (SMOOTH.md B4): with the set-up screens
		// a run can be left for another gun, mode or crew without dying first. The web game's card (src/menus.js
		// paused()) has neither because it has no set-up screens to go back to. MenuConfirm ends the run as the death
		// card's rows do.
		FMIMenuItem Change;
		Change.Id = TEXT("changesetup");
		Change.Label = FrontEnd->GetRules().Text(TEXT("frontend.cards.changeSetup"));
		Menu.Items.Add(Change);
		FMIMenuItem Title;
		Title.Id = TEXT("totitle");
		Title.Label = Ui.Get(TEXT("cards.toTitle"));
		Menu.Items.Add(Title);
		return;
	}
	// The death and debrief cards gain Change set-up between Run it back and Back to title (LOADOUT.md 2.9).
	if (Menu.Screen != EMIMenuScreen::Dead && Menu.Screen != EMIMenuScreen::Debrief)
	{
		return;
	}
	const int32 At = Menu.IndexOf(TEXT("totitle"));
	FMIMenuItem Item;
	Item.Id = TEXT("changesetup");
	Item.Label = FrontEnd->GetRules().Text(TEXT("frontend.cards.changeSetup"));
	Menu.Items.Insert(Item, At == INDEX_NONE ? Menu.Items.Num() : At);
}

void UMIGameSubsystem::OpenSettingsFromFrontEnd()
{
	if (FrontEnd)
	{
		FrontEnd->Hide();
	}
	Menu.Return = EMIMenuScreen::Title;
	Menu.Build(EMIMenuScreen::Settings, Settings, Copy, Ui, Rules.Card(), Rules.GetMode());
}

void UMIGameSubsystem::ApplyCrewLines(FName Crew)
{
	// Rule keeps text.json word for word; a crew member with template lines says them with his call name. The flow
	// rules share this deck's JSON, so the radio and the cards read the patched lines.
	const UMIDataSubsystem* Data = UMIDataSubsystem::Get(this);
	if (!Data || !Data->IsLoadoutLoaded() || !Copy.Root.IsValid())
	{
		return;
	}
	const FMILoadoutData& L = Data->GetLoadout();
	const FMICrewEntry* C = L.FindCrew(Crew);
	for (const TPair<FString, FString>& R : L.CrewReplaces)
	{
		const FString* Original = OriginalLines.Find(R.Key);
		const FString Line = C && !C->bOriginalLines ? L.Format(R.Value, {{TEXT("name"), C->CallName}}) : (Original ? *Original : FString());
		if (!Line.IsEmpty())
		{
			MIJson::Set(Copy.Root, R.Key.Mid(5), MakeShared<FJsonValueString>(Line));
		}
	}
}

bool UMIGameSubsystem::ApplySetup(const FMIRunSetup& Setup)
{
	UMIRunSetupSubsystem* RunSetup = UMIRunSetupSubsystem::Get(this);
	const FMILoadoutData* Data = RunSetup ? RunSetup->GetData() : (FrontEnd ? &FrontEnd->GetRules().GetData() : nullptr);
	AMIPlayerCharacter* P = GetPlayer();
	if (!Data || !P || !P->GetWeapon() || !ResolverConfig.IsValid())
	{
		return false;
	}
	const FMIReadiness Ready = RunSetup ? RunSetup->MakeReadiness() : FrontEnd->GetReadiness();
	FMIRunSetup S = Setup;
	Ready.Validate(S);
	FMIResolvedRun Run;
	FString Error;
	bool bResolved = false;
	{
		TRACE_CPUPROFILER_EVENT_SCOPE_STR("MI/ApplySetup Resolve");
		bResolved = FMILoadoutResolver(*Data, ResolverConfig, ResolverPresentation).Resolve(S, &Ready, Run, Error);
	}
	if (!bResolved)
	{
		UE_LOG(LogMI, Error, TEXT("Set-up: %s (the run keeps the guns it had)"), *Error);
		return false;
	}
	{
		TRACE_CPUPROFILER_EVENT_SCOPE_STR("MI/ApplySetup ApplyRun");
		P->GetWeapon()->ApplyRun(Run);
	}
	{
		TRACE_CPUPROFILER_EVENT_SCOPE_STR("MI/ApplySetup ApplyCrewLook");
		P->ApplyCrewLook(Data->FindCrew(S.Crew));
	}
	{
		TRACE_CPUPROFILER_EVENT_SCOPE_STR("MI/ApplySetup ApplyCrewLines");
		ApplyCrewLines(S.Crew);
	}
	// The audio agent's hooks (docs/unreal/AUDIO.md 1): the crew member's voice set and the silencers.
	if (UMIAudioSubsystem* Audio = UMIAudioSubsystem::Get(this))
	{
		Audio->SetCharacter(S.Crew);
		for (const FMIWeaponDef& G : Run.Weapons.Guns)
		{
			Audio->SetSuppressed(G.Id, G.bSuppressed);
		}
	}
	return true;
}

void UMIGameSubsystem::PreviewSetup(const FMIRunSetup& Setup)
{
	ApplySetup(Setup);
}

void UMIGameSubsystem::BeginWithSetup(const FMIRunSetup& Setup)
{
	bool bChanged = Settings.SetMode(Setup.Mode);
	bChanged |= Settings.SetTime(Setup.Time);
	SetDifficulty(Setup.Difficulty);
	if (bChanged)
	{
		SaveSettings();
	}
	ApplySetup(Setup);
	UE_LOG(LogMI, Log, TEXT("Set-up: %s"), *Setup.ToJsonString());
	StartRun(Settings.Mode);
}

void UMIGameSubsystem::UiNote(const TCHAR* Name, const UObject* WorldContext)
{
	static uint64 LastFrame[2] = {MAX_uint64, MAX_uint64};
	static double LastClick = -1.0;
	const int32 Click = FCString::Strcmp(Name, TEXT("ui:click")) == 0 ? 1 : 0;
	const double Now = FPlatformTime::Seconds();
	if (LastFrame[Click] == GFrameCounter || (!Click && Now - LastClick < 0.15))
	{
		return;
	}
	LastFrame[Click] = GFrameCounter;
	if (Click)
	{
		LastClick = Now;
	}
	if (FMIGameEvents* Events = WorldContext ? UMIEventSubsystem::Get(WorldContext) : nullptr)
	{
		FMIFlowEvent E;
		E.Name = Name;
		Events->Flow.Broadcast(E);
	}
}

void UMIGameSubsystem::MenuMove(int32 Dy)
{
	Menu.Move(Dy);
	UiNote(TEXT("ui:hover"), this);
}

void UMIGameSubsystem::MenuAdjust(int32 Dx, int32 Mult)
{
	const FMIMenuItem* Item = Menu.Current();
	if (!Item || !Item->bAdjust || Dx == 0)
	{
		return;
	}
	UiNote(TEXT("ui:click"), this);
	const FName Id = Item->Id;
	const FMISettings::FRules& R = Settings.Rules;
	const AMIPlayerController* StepPC = Cast<AMIPlayerController>(UGameplayStatics::GetPlayerController(this, 0));
	const bool bPadStep = StepPC && StepPC->IsPadActive();
	bool bChanged = false;
	if (Id == TEXT("mode")) bChanged = Settings.SetMode(FMISettings::Next(Settings.Mode, R.Modes, Dx));
	else if (Id == TEXT("difficulty"))
	{
		bChanged = Settings.SetDifficulty(FMISettings::Next(Settings.Difficulty, R.Difficulties, Dx));
		Rules.SetDifficulty(Settings.Difficulty);
	}
	else if (Id == TEXT("time")) bChanged = Settings.SetTime(FMISettings::Next(Settings.Time, R.Times, Dx));
	else if (Id == TEXT("quality")) bChanged = Settings.SetQuality(FMISettings::Next(Settings.Quality, R.Qualities, Dx));
	else if (Id == TEXT("sens")) bChanged = Settings.SetSens(Settings.Sens + Dx * Mult * (bPadStep ? R.PadSensStep : R.SensStep));
	else if (Id == TEXT("volume")) bChanged = Settings.SetVolume(Settings.Volume + Dx * Mult * (bPadStep ? R.PadVolumeStep : R.VolumeStep));
	else if (Id == TEXT("fov")) bChanged = Settings.SetFov(Settings.Fov + Dx * Mult * (bPadStep ? R.PadFovStep : R.FovStep));
	else if (Id == TEXT("invert")) bChanged = Settings.SetInvertY(!Settings.bInvertY);
	else if (Id == TEXT("padnames")) bChanged = Settings.SetPadPlayStation(!Settings.bPadPlayStation);
	else if (Id == TEXT("guide")) bChanged = Settings.SetGuide(!Settings.bGuide);
	else if (Id == TEXT("view")) bChanged = Settings.SetView((Settings.View - R.ViewMin + Dx + (R.ViewMax - R.ViewMin + 1)) % (R.ViewMax - R.ViewMin + 1) + R.ViewMin);
	if (bChanged)
	{
		SaveSettings();
		ApplySettings();
	}
	RebuildMenu();
}

void UMIGameSubsystem::MenuConfirm()
{
	const FMIMenuItem* Item = Menu.Current();
	if (!Item)
	{
		return;
	}
	const FName Id = Item->Id;
	UiNote(TEXT("ui:click"), this);
	if (Item->bAdjust)
	{
		MenuAdjust(1);
	}
	else if (Id == TEXT("start")) StartRun(Settings.Mode);
	else if (Id == TEXT("resume")) Resume();
	else if (Id == TEXT("restart")) Restart();
	else if (Id == TEXT("retry")) Retry();
	else if (Id == TEXT("again")) Redeploy();
	else if (Id == TEXT("totitle"))
	{
		ToTitle();
		if (FrontEnd) FrontEnd->OpenHome();
	}
	else if (Id == TEXT("changesetup"))
	{
		// The run ends as Back to title does, then the Briefing opens (LOADOUT.md 2.9).
		ToTitle();
		if (FrontEnd) FrontEnd->OpenBriefing();
	}
	else if (Id == TEXT("settings"))
	{
		Menu.Return = Menu.Screen;
		Menu.Build(EMIMenuScreen::Settings, Settings, Copy, Ui, Rules.Card(), Rules.GetMode());
	}
	else if (Id == TEXT("back")) MenuBack();
}

bool UMIGameSubsystem::MenuHover(const FVector2D& Point)
{
	const FMIMenuHit Hit = Menu.HitTest(Point);
	if (Hit.Row == INDEX_NONE)
	{
		return false;
	}
	if (Menu.Selected != Hit.Row)
	{
		UiNote(TEXT("ui:hover"), this);  // the pointer came onto another row
	}
	Menu.Selected = Hit.Row;
	return true;
}

bool UMIGameSubsystem::MenuClick(const FVector2D& Point)
{
	const FMIMenuHit Hit = Menu.HitTest(Point);
	UE_LOG(LogMI, Log, TEXT("Card click at (%.0f, %.0f): row %d, side %d (rows from (%.0f, %.0f), %.0f wide, %.0f high, %.0f apart)"),
		Point.X, Point.Y, Hit.Row, Hit.Side, Menu.Layout.X, Menu.Layout.Top, Menu.Layout.Width, Menu.Layout.RowHeight, Menu.Layout.RowGap);
	if (Hit.Row == INDEX_NONE)
	{
		return false;
	}
	Menu.Selected = Hit.Row;
	if (Hit.Side != 0)
	{
		MenuAdjust(Hit.Side);
	}
	else
	{
		MenuConfirm();
	}
	return true;
}

void UMIGameSubsystem::MenuBack()
{
	if (Menu.Screen == EMIMenuScreen::Settings)
	{
		UiNote(TEXT("ui:click"), this);
		Menu.Build(Menu.Return, Settings, Copy, Ui, Rules.Card(), Rules.GetMode());
		PatchCards();  // back on the pause card: its set-up rows again
		if (FrontEnd && Rules.GetState() == EMIGameState::Title)
		{
			FrontEnd->Show();  // back to Home
		}
	}
	else if (Menu.Screen == EMIMenuScreen::Pause && Rules.GetStateTime() >= FlowTune.PauseDebounce)
	{
		Resume();
	}
}

void UMIGameSubsystem::SaveSettings()
{
	if (!Boots.bPersist)
	{
		return;
	}
	UMISaveGame* Save = Cast<UMISaveGame>(UGameplayStatics::CreateSaveGameObject(UMISaveGame::StaticClass()));
	Settings.ToSave(*Save);
	if (const UMIRunSetupSubsystem* RunSetup = UMIRunSetupSubsystem::Get(this))
	{
		RunSetup->Write(*Save);  // the remembered set-up rides in the same slot
	}
	UGameplayStatics::SaveGameToSlot(Save, Settings.Rules.Slot, 0);
}

FString UMIGameSubsystem::ControlName(const TCHAR* Action, bool bPad) const
{
	const FString Name = Keys.Root.IsValid() ? Keys.Get(FString::Printf(TEXT("glyphs.%s.%s"), bPad ? TEXT("pad") : TEXT("kbm"), Action)) : FString();
	return bPad ? PadName(Name) : Name;
}

FString UMIGameSubsystem::PadName(const FString& Name) const
{
	return MILook::PadName(Name, Settings.bPadPlayStation);
}

void UMIGameSubsystem::ApplySettings()
{
	if (AMIPlayerCharacter* P = GetPlayer())
	{
		P->GetPlayerRules().SetFov(Settings.VerticalFov());
		if (AMIPlayerController* PC = Cast<AMIPlayerController>(P->GetController()))
		{
			PC->Sensitivity = Settings.Sens;
			PC->bInvertY = Settings.bInvertY;
		}
	}
	if (!Boots.bPersist)
	{
		return;  // tests leave the machine's audio and scalability alone
	}
	if (UMIAudioSubsystem* Mix = UMIAudioSubsystem::Get(this); Mix && Mix->IsReady())
	{
		// The master volume through the audio agent's options hook (docs/unreal/AUDIO.md 1); the device stays at 1
		// so the setting is applied once.
		FMIAudioOptions Options = Mix->GetOptions();
		Options.Master = Settings.Volume;
		Mix->SetOptions(Options);
		if (FAudioDevice* Audio = GetWorld()->GetAudioDeviceRaw())
		{
			Audio->SetTransientPrimaryVolume(1.f);
		}
	}
	else if (FAudioDevice* Audio = GetWorld() ? GetWorld()->GetAudioDeviceRaw() : nullptr)
	{
		Audio->SetTransientPrimaryVolume(Settings.Volume);
	}
	const int32 Scalability = Settings.Rules.Qualities.IndexOfByKey(Settings.Quality) - 1;  // auto, low .. ultra
	const UGameInstance* GI = GetWorld() ? GetWorld()->GetGameInstance() : nullptr;
	const UMICloudSubsystem* Cloud = GI ? GI->GetSubsystem<UMICloudSubsystem>() : nullptr;
	if (Cloud && Cloud->IsStreamed())
	{
		// In a stream the setting moves the scalability groups only: UGameUserSettings::ApplySettings would also ask
		// for its own resolution and window mode, clear the 60 fps cap and render Ultra at the full output size.
		// While Settings is open the level waits (FlowFrame writes it when the card closes): every level written costs a
		// frame of 62 to 377 ms (SMOOTH.md B3), and a player steps through several on the way to the one they want.
		if (Menu.Screen == EMIMenuScreen::Settings)
		{
			bStreamedQualityPending = true;
			PendingStreamedQuality = Scalability;
		}
		else
		{
			bStreamedQualityPending = false;
			UMICloudSubsystem::ApplyStreamedQuality(Scalability);
		}
	}
	else if (UGameUserSettings* User = GEngine ? GEngine->GetGameUserSettings() : nullptr)
	{
		if (Scalability >= 0 && User->GetOverallScalabilityLevel() != Scalability)
		{
			User->SetOverallScalabilityLevel(Scalability);
			User->ApplySettings(false);
		}
	}
}

// =========================================================================================================== frame

FVector UMIGameSubsystem::PlayerFeetWeb() const
{
	const AMIPlayerCharacter* P = GetPlayer();
	return P ? MI::Web::FromUnreal(P->GetPlayerRules().Feet) : FVector::ZeroVector;
}

void UMIGameSubsystem::TeleportPlayerWeb(const FVector& Feet)
{
	if (AMIPlayerCharacter* P = GetPlayer())
	{
		P->TeleportFeet(MI::Web::ToUnreal(Feet));
	}
}

bool UMIGameSubsystem::FaceNearestEnemy(double Metres)
{
	AMIPlayerCharacter* P = GetPlayer();
	if (!P || !bBooted)
	{
		return false;
	}
	const FVector Me = PlayerFeetWeb();
	const FMIEnemy* Near = nullptr;
	for (const FMIEnemy& E : Field.GetSlots())
	{
		if (E.bAlive && (!Near || FVector::Dist(E.Pos, Me) < FVector::Dist(Near->Pos, Me)))
		{
			Near = &E;
		}
	}
	FVector Spot;
	if (!Near)
	{
		return false;
	}
	FVector Away = (Me - Near->Pos).GetSafeNormal2D();
	if (Away.IsNearlyZero()) Away = FVector(1, 0, 0);
	if (Metres > 0.0)  // Metres <= 0: only turn to look at it
	{
		// A walkable spot at the asked distance (within 0.75 m) with a clear line to the Goon's chest: bearings
		// fanned out from the line Goon -> player, nearest bearing first (the old 6 m snap could land 10 m off).
		const FVector Chest = Near->Pos + FVector(0, 1.2, 0);
		bool bFound = false;
		for (int32 Step = 0; Step <= 24 && !bFound; ++Step)
		{
			const double Deg = (Step % 2 == 1 ? 1.0 : -1.0) * 15.0 * ((Step + 1) / 2);
			const FVector Dir = Away.RotateAngleAxis(Deg, FVector(0, 1, 0));
			FVector Candidate;
			const FVector Want = Near->Pos + Dir * Metres;
			if (!Box.NearestWalkable(Want.X, Want.Z, 0.75, Candidate) || FMath::Abs(FVector::Dist2D(FVector(Candidate.X, Candidate.Z, 0), FVector(Near->Pos.X, Near->Pos.Z, 0)) - Metres) > 0.75)
			{
				continue;
			}
			const double Y = Box.GroundHeight(Candidate.X, Candidate.Z, Near->Pos.Y + 1.0);
			if (Box.LineOfSight(FVector(Candidate.X, Y + 1.6, Candidate.Z), Chest))
			{
				Spot = FVector(Candidate.X, Y, Candidate.Z);
				bFound = true;
			}
		}
		if (!bFound)
		{
			UE_LOG(LogMI, Warning, TEXT("MIFaceEnemy: no walkable spot %.0f m from the nearest Goon with a clear line"), Metres);
			return false;
		}
		TeleportPlayerWeb(Spot);
		UE_LOG(LogMI, Log, TEXT("MIFaceEnemy: %.1f m from the nearest Goon"), FVector::Dist2D(FVector(Spot.X, Spot.Z, 0), FVector(Near->Pos.X, Near->Pos.Z, 0)));
	}
	FMIPlayerRules& R = P->GetPlayerRules();
	const FVector D = MI::Web::ToUnreal(Near->Pos + FVector(0, Near->IsGoon() ? 1.2 : 0.0, 0)) - (P->GetActorLocation() + FVector(0, 0, 70.0));
	R.Yaw = FMath::RadiansToDegrees(FMath::Atan2(D.Y, D.X));
	R.Pitch = FMath::RadiansToDegrees(FMath::Atan2(D.Z, D.Size2D()));
	return true;
}

void UMIGameSubsystem::FlowFrame(double Dt)
{
	using namespace MI::Web;
	using namespace MIGameSubsystemPrivate;
	if (!bBooted)
	{
		return;
	}
	Dt = FMath::Min(Dt, 0.05);
	if (bStreamedQualityPending && Menu.Screen != EMIMenuScreen::Settings)
	{
		// Settings has closed (Back, the pause key, a resume): the Graphics quality chosen there is written now, once.
		bStreamedQualityPending = false;
		UMICloudSubsystem::ApplyStreamedQuality(PendingStreamedQuality);
	}
	if (FrontEnd && FrontEnd->IsShown())
	{
		FrontEnd->Tick(Dt);
	}
	AMIPlayerCharacter* P = GetPlayer();
	if (P && !bPrerequisite)
	{
		// The player joined (the game mode spawns him after the boot): the flow runs before his frame, he keeps
		// inside the play bounds and stands at the level's start.
		P->AddFramePrerequisite(this, FlowTick);
		const FVector Lo = ToUnreal(FVector(Level->Bounds.MinX, 0, Level->Bounds.MinZ));
		const FVector Hi = ToUnreal(FVector(Level->Bounds.MaxX, 0, Level->Bounds.MaxZ));
		P->SetPlayBounds(FBox2D(FVector2D(FMath::Min(Lo.X, Hi.X), FMath::Min(Lo.Y, Hi.Y)), FVector2D(FMath::Max(Lo.X, Hi.X), FMath::Max(Lo.Y, Hi.Y))));
		bPrerequisite = true;
		ApplySettings();
		if (Rules.GetState() == EMIGameState::Title)
		{
			ResetPlayer(Level->PlayerStart.Pos, Level->PlayerStart.Yaw);
		}
	}
	FMIFlowPlayer FP;
	if (P)
	{
		const FMIPlayerRules& R = P->GetPlayerRules();
		FP.Pos = FromUnreal(R.Feet);
		FP.Forward = DirFromUnreal(R.Forward).GetSafeNormal();
		FP.bAlive = R.bAlive;
		FP.Health = R.Health;
	}
	// The grab prompt names the control of the device in use.
	{
		const AMIPlayerController* PC = P ? Cast<AMIPlayerController>(P->GetController()) : nullptr;
		const FString Name = ControlName(TEXT("interact"), PC && PC->IsPadActive());
		Rules.InteractGlyph = Name.IsEmpty() ? FString(TEXT("E")) : Name;
	}
	Rules.Update(Dt, FP, bInteract);
	ForwardFlow();
	DrainEnemies();
	UpdateLastEnemies(Dt);
	MenuRepeat(Dt);
	ApplyState();
	SyncView(Dt);
}

void UMIGameSubsystem::MenuRepeat(double Dt)
{
	const FMIMenuItem* Item = Menu.Screen != EMIMenuScreen::None ? Menu.Current() : nullptr;
	const APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	int32 Dir = 0;
	if (Item && Item->bAdjust && PC)
	{
		const bool bLeft = PC->IsInputKeyDown(EKeys::Left) || PC->IsInputKeyDown(EKeys::Gamepad_DPad_Left) || PC->IsInputKeyDown(EKeys::Gamepad_LeftStick_Left);
		const bool bRight = PC->IsInputKeyDown(EKeys::Right) || PC->IsInputKeyDown(EKeys::Gamepad_DPad_Right) || PC->IsInputKeyDown(EKeys::Gamepad_LeftStick_Right);
		Dir = bRight && !bLeft ? 1 : (bLeft && !bRight ? -1 : 0);
	}
	if (Dir == 0 || Dir != RepeatDir)
	{
		RepeatDir = Dir;
		RepeatHeld = 0;
		RepeatIn = Settings.Rules.RepeatAfter;
		return;
	}
	RepeatHeld += Dt;
	RepeatIn -= Dt;
	while (RepeatIn <= 0.0)
	{
		RepeatIn += Settings.Rules.RepeatEvery;
		MenuAdjust(Dir, RepeatHeld >= Settings.Rules.FastAfter ? FMath::Max(1, FMath::RoundToInt32(Settings.Rules.FastMult)) : 1);
	}
}

void UMIGameSubsystem::UpdateLastEnemies(double Dt)
{
	LastEnemies.Reset();
	const bool bHold = Rules.GetMode() == TEXT("holdout") && Rules.HoldoutActive() && Rules.GetState() == EMIGameState::Playing && Rules.QueueLength() == 0;
	const int32 Alive = bHold ? Field.AliveCount() : 0;
	if (Alive <= 0 || Alive > 2)
	{
		LastStandFor = 0;
		LastStandHp = -1;
		return;
	}
	const TArray<FMIEnemy>& Slots = Field.GetSlots();
	double Hp = 0;
	bool bAllAir = true;
	for (const int32 I : Field.GetList())
	{
		const FMIEnemy& E = Slots[I];
		if (!E.bAlive)
		{
			continue;
		}
		LastEnemies.Add(E.Id);
		Hp += E.Hp;
		bAllAir &= !E.IsGoon();
	}
	// A wave that can never end: only Buzzards left, none hurt for 20 s (the owner, DECISIONS.md 2026-11-27: "Drones come to
	// the player"). They fly straight at the player so the fight ends; the marker on the last enemies stays. Off in tests and
	// replays (no save slot), so the web game's rules and the golden runs are untouched.
	if (Hp != LastStandHp)
	{
		LastStandHp = Hp;
		LastStandFor = 0;
	}
	LastStandFor += Dt;
	if ((Boots.bPersist || Boots.bLastDrones) && bAllAir && LastStandFor > LastStandLimit)
	{
		for (const int32 Id : LastEnemies)
		{
			FMIEnemy* E = Field.Find(Id);
			if (E && !E->bCharge)
			{
				UE_LOG(LogMI, Log, TEXT("Hold: Buzzard %d unhurt for %.0f s as the wave's last enemy: it flies at the player"), Id, LastStandFor);
				E->bCharge = true;
				E->Mode = EMIEnemyMode::Engage;
				E->SinceSeen = 0;
			}
		}
	}
}

void UMIGameSubsystem::EnemyFrame(double Dt)
{
	using namespace MI::Web;
	using namespace MIGameSubsystemPrivate;
	if (!bBooted)
	{
		return;
	}
	Dt = FMath::Min(Dt, 0.05);
	// Once the run is complete the enemy field stands still (review 2026-11-24: the pursuers spawned after the last
	// reel kept shooting, and a tracer crossed the debrief card). The rules stop at Complete in every test and replay.
	if (bSimLive && Rules.GetState() != EMIGameState::Complete)
	{
		FMIEnemyPlayer EP;
		if (const AMIPlayerCharacter* P = GetPlayer())
		{
			const FMIPlayerRules& R = P->GetPlayerRules();
			EP.Pos = FromUnreal(R.Feet);
			EP.Eye = FromUnreal(R.Eye);
			EP.Vel = DirFromUnreal(R.Velocity) * 0.01;
			EP.bAlive = R.bAlive;
			EP.bCrouching = R.bCrouching;
		}
		Field.Update(Dt, EP);
		DrainEnemies();
	}
	SyncActors(Dt);
}

void UMIGameSubsystem::DrainEnemies()
{
	TArray<FMIEnemyEvent> Out;
	Rules.DrainEnemies(Out);
	FMIGameEvents* Events = UMIEventSubsystem::Get(this);
	for (const FMIEnemyEvent& Ev : Out)
	{
		if (Ev.Kind == FMIEnemyEvent::EKind::Killed && Ev.bByPlayer)
		{
			RunStats.Kills++;
			if (Ev.Part == TEXT("head"))
			{
				RunStats.Headshots++;
			}
		}
		const int32 Slot = SlotOf(Ev.Id);
		if (AMIGoon* G = Cast<AMIGoon>(GetEnemyActor(Slot)))
		{
			G->OnRuleEvent(Ev);
		}
		else if (AMIBuzzard* B = Cast<AMIBuzzard>(GetEnemyActor(Slot)))
		{
			B->OnRuleEvent(Ev);
		}
		if (Events)
		{
			Events->Enemy.Broadcast(Ev);
		}
	}
	ForwardFlow();
}

void UMIGameSubsystem::ForwardFlow()
{
	TArray<FMIFlowEvent>& Pending = Rules.Events();
	if (Pending.Num() == 0)
	{
		return;
	}
	TArray<FMIFlowEvent> Batch = MoveTemp(Pending);
	Pending.Reset();
	if (FMIGameEvents* Events = UMIEventSubsystem::Get(this))
	{
		for (const FMIFlowEvent& E : Batch)
		{
			Events->Flow.Broadcast(E);
		}
	}
}

int32 UMIGameSubsystem::SlotOf(int32 EnemyId) const
{
	const TArray<FMIEnemy>& Slots = Field.GetSlots();
	for (int32 I = 0; I < Slots.Num(); ++I)
	{
		if (Slots[I].Id == EnemyId)
		{
			return I;
		}
	}
	return INDEX_NONE;
}

void UMIGameSubsystem::ApplyState()
{
	const EMIGameState S = Rules.GetState();
	const bool bRun = S == EMIGameState::Intro || S == EMIGameState::Playing;
	bSimLive = S != EMIGameState::Title && S != EMIGameState::Paused;
	AMIPlayerCharacter* P = GetPlayer();
	if (P)
	{
		P->SetSimulationLive(bSimLive);
		P->SetGameplayInput(bRun);
		P->SetViewmodelVisible(bRun || (FrontEnd && FrontEnd->WantsViewmodel()));
		P->GetPlayerRules().bEnabled = S != EMIGameState::Title && S != EMIGameState::Complete;
	}
	// The card a state shows: the menus follow the flow.
	EMIMenuScreen Want = Menu.Screen;
	switch (S)
	{
	case EMIGameState::Title: Want = Menu.Screen == EMIMenuScreen::Settings ? EMIMenuScreen::Settings : EMIMenuScreen::Title; break;
	case EMIGameState::Paused: Want = Menu.Screen == EMIMenuScreen::Settings ? EMIMenuScreen::Settings : EMIMenuScreen::Pause; break;
	case EMIGameState::Dead: Want = Rules.Card().IsSet() ? EMIMenuScreen::Dead : EMIMenuScreen::None; break;
	case EMIGameState::Complete: Want = Rules.Card().IsSet() ? EMIMenuScreen::Debrief : EMIMenuScreen::None; break;
	default: Want = EMIMenuScreen::None; break;
	}
	if (Want != Menu.Screen || (bStateApplied && S != AppliedState))
	{
		if (Want == EMIMenuScreen::Settings)
		{
			Menu.Return = S == EMIGameState::Title ? EMIMenuScreen::Title : EMIMenuScreen::Pause;
		}
		Menu.Build(Want, Settings, Copy, Ui, Rules.Card(), Rules.GetMode());
		PatchCards();
	}
	if (FrontEnd)
	{
		if (S == EMIGameState::Title && Menu.Screen != EMIMenuScreen::Settings) FrontEnd->Show();
		else if (S != EMIGameState::Title) FrontEnd->Hide();
	}
	if (bStateApplied && S == AppliedState)
	{
		return;
	}
	const EMIGameState Prev = AppliedState;
	AppliedState = S;
	bStateApplied = true;
	UWorld* World = GetWorld();
	if (S == EMIGameState::Complete && World)
	{
		if (UMIEffects* Fx = World->GetSubsystem<UMIEffects>())
		{
			Fx->ClearShots();  // no tracer or flash still flying over the debrief
		}
	}
	APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	if ((S == EMIGameState::Paused) != (Prev == EMIGameState::Paused) && World && World->GetAuthGameMode())
	{
		UGameplayStatics::SetGamePaused(World, S == EMIGameState::Paused);
	}
	if (PC)
	{
		PC->bShowMouseCursor = !bRun;
		if (S == EMIGameState::Title && TitleCamera)
		{
			TitleT = 0;
			if (!FrontEnd)
			{
				PC->SetViewTarget(TitleCamera);  // the front end picks the view per screen
				if (PC->PlayerCameraManager) PC->PlayerCameraManager->SetGameCameraCutThisFrame();
			}
		}
		else if (P && PC->GetViewTarget() != P)
		{
			PC->SetViewTarget(P);
			if (PC->PlayerCameraManager) PC->PlayerCameraManager->SetGameCameraCutThisFrame();  // no history from the stage
		}
	}
}

void UMIGameSubsystem::SyncView(double Dt)
{
	using namespace MI::Web;
	const FMIFlowView& V = Rules.View();
	UWorld* World = GetWorld();
	APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	if (PC && PC->PlayerCameraManager)
	{
		// On the title the fly-through fades itself in at the start of each pass (flow.titleCamera.fadeIn).
		const double Fade = Rules.GetState() == EMIGameState::Title ? 1.0 - FMath::Clamp(TitleT / FMath::Max(1e-3, TitleFadeIn * TitleSpeed), 0.0, 1.0) : V.Fade;
		PC->PlayerCameraManager->SetManualCameraFade(Fade, FLinearColor::Black, false);
	}
	if (AMIPlayerCharacter* P = GetPlayer())
	{
		if (UCameraComponent* Cam = P->GetFirstPersonCamera())
		{
			Cam->PostProcessSettings.bOverride_ColorSaturation = true;
			Cam->PostProcessSettings.ColorSaturation = FVector4(V.Saturation, V.Saturation, V.Saturation, 1.0);
		}
	}
	if (FMIGameEvents* Events = UMIEventSubsystem::Get(this))
	{
		Events->MusicIntensity.Broadcast(V.Music);
	}
	for (int32 I = 0; I < Cases.Num(); ++I)
	{
		if (Cases[I])
		{
			Cases[I]->Sync(Rules.IsSecured(I), Rules.GrabbingObjective() == I ? Rules.Progress() : 0.0);
		}
	}
	if (Truck)
	{
		Truck->Sync(Rules.AllSecured(), Dt);
	}
	// The title fly-through: along the level's cinematic keys at the title camera's speed, then round again.
	if (Rules.GetState() == EMIGameState::Title && TitleCamera && Level && Level->CinematicPos.Num() >= 2)
	{
		TitleT += Dt * TitleSpeed;
		double Left = TitleT;
		int32 K = 0;
		for (; K + 1 < Level->CinematicPos.Num(); ++K)
		{
			const double L = FVector::Dist(Level->CinematicPos[K], Level->CinematicPos[K + 1]);
			if (Left <= L)
			{
				break;
			}
			Left -= L;
		}
		if (K + 1 >= Level->CinematicPos.Num())
		{
			TitleT = 0;
			K = 0;
			Left = 0;
		}
		const double L = FMath::Max(1e-6, FVector::Dist(Level->CinematicPos[K], Level->CinematicPos[K + 1]));
		const double A = FMath::Clamp(Left / L, 0.0, 1.0);
		const FVector Pos = ToUnreal(FMath::Lerp(Level->CinematicPos[K], Level->CinematicPos[K + 1], A));
		const int32 LK = FMath::Min(K, Level->CinematicLook.Num() - 2);
		const FVector Look = LK >= 0 ? ToUnreal(FMath::Lerp(Level->CinematicLook[LK], Level->CinematicLook[LK + 1], A)) : Pos + FVector(100, 0, 0);
		TitleCamera->SetActorLocationAndRotation(Pos, (Look - Pos).Rotation());
	}
}

void UMIGameSubsystem::SyncActors(double Dt)
{
	const TArray<FMIEnemy>& Slots = Field.GetSlots();
	for (int32 I = 0; I < Slots.Num() && I < EnemyActors.Num(); ++I)
	{
		if (AMIGoon* G = Cast<AMIGoon>(EnemyActors[I].Get()))
		{
			G->Sync(Slots[I], Field.GoonHead(Slots[I]), Dt);
		}
		else if (AMIBuzzard* B = Cast<AMIBuzzard>(EnemyActors[I].Get()))
		{
			B->Sync(Slots[I], Dt);
		}
	}
}

// ========================================================================================================== damage

FMIDamageResult UMIGameSubsystem::DamageEnemy(int32 Slot, const FMIDamage& Damage)
{
	using namespace MIGameSubsystemPrivate;
	FMIDamageResult Result;
	if (!bBooted || !Field.GetSlots().IsValidIndex(Slot))
	{
		return Result;
	}
	FMIEnemy* E = Field.Find(Field.GetSlots()[Slot].Id);
	if (!E || !E->bAlive || !(Damage.Amount > 0.0))
	{
		return Result;
	}
	// Every blast is the player's (spec 03 3.10); enemy rounds never hurt enemies.
	if (Damage.Source == EMIDamageSource::Enemy)
	{
		return Result;
	}
	const bool bByPlayer = Damage.Source == EMIDamageSource::Player || Damage.Source == EMIDamageSource::Blast;
	const FName Part = Damage.Kind == EMIDamageKind::Bullet ? Damage.Part : FName(TEXT("body"));
	const double Before = E->Hp;
	TOptional<FVector> Dir;
	if (!Damage.Direction.IsNearlyZero())
	{
		Dir = DirFromUnreal(Damage.Direction).GetSafeNormal();
	}
	Result.bKilled = Field.Damage(*E, Damage.Amount, Part, Dir, bByPlayer, Damage.Weapon);
	Result.bAccepted = true;
	Result.Dealt = Before - FMath::Max(0.0, E->Hp);
	DrainEnemies();
	return Result;
}

// ===================================================================================================== IMIGameHost

void UMIGameSubsystem::ResetPlayer(const FVector& Pos, double Yaw)
{
	if (AMIPlayerCharacter* P = GetPlayer())
	{
		P->ResetAt(MI::Web::ToUnreal(Pos), MI::Web::YawToUnreal(Yaw));
		FMIPlayerRules& R = P->GetPlayerRules();
		R.Pitch = MIGameSubsystemPrivate::StartPitch();
		R.RegenDelay = RegenDelay;
		R.RegenRate = RegenRate;
		R.SetFov(Settings.VerticalFov());
	}
}

void UMIGameSubsystem::HealPlayer(double Amount)
{
	if (AMIPlayerCharacter* P = GetPlayer())
	{
		P->GetPlayerRules().Heal(Amount);
	}
}

void UMIGameSubsystem::AddReserve(double Amount, double Cap)
{
	if (AMIPlayerCharacter* P = GetPlayer(); P && P->GetWeapon())
	{
		P->GetWeapon()->AddReserve(Amount, Cap);
	}
}

void UMIGameSubsystem::ResetExplosives()
{
	if (UMICombatSubsystem* Combat = UMICombatSubsystem::Get(this))
	{
		Combat->ResetExplosives();
	}
	if (Level)
	{
		for (const int32 Owner : RemovedOwners)
		{
			for (const FMIBox& B : Level->Colliders)
			{
				if (B.Owner == Owner)
				{
					Box.AddBox(B);
				}
			}
		}
	}
	RemovedOwners.Reset();
}

void UMIGameSubsystem::ResetCombat()
{
	RunStats = FMIRunStats();
}

void UMIGameSubsystem::SetRegen(double Delay, double Rate)
{
	RegenDelay = Delay;
	RegenRate = Rate;
	if (AMIPlayerCharacter* P = GetPlayer())
	{
		P->GetPlayerRules().RegenDelay = Delay;
		P->GetPlayerRules().RegenRate = Rate;
	}
}

void UMIGameSubsystem::SetInvulnerable(bool bOn)
{
	if (AMIPlayerCharacter* P = GetPlayer())
	{
		P->GetPlayerRules().bInvulnerable = bOn;
	}
}

void UMIGameSubsystem::AddShake(double Amount)
{
	if (AMIPlayerCharacter* P = GetPlayer())
	{
		P->GetPlayerRules().AddShake(Amount);
	}
}

void UMIGameSubsystem::Stats(int32& Kills, int32& Shots, int32& Hits, int32& Headshots) const
{
	Kills = RunStats.Kills;
	Shots = RunStats.Shots;
	Hits = RunStats.Hits;
	Headshots = RunStats.Headshots;
}

bool UMIGameSubsystem::SetBest(int32 Score)
{
	const bool bNew = Settings.SetBest(Score);
	if (bNew)
	{
		SaveSettings();
	}
	return bNew;
}

// ==================================================================================================== IMIEnemyHost

double UMIGameSubsystem::RayPlayer(const FVector& Origin, const FVector& D, double MaxDist) const
{
	// src/combat.js rayPlayer: the upright cylinder enemy rounds test (web units).
	const AMIPlayerCharacter* P = GetPlayer();
	if (!P || !P->GetPlayerRules().bAlive)
	{
		return MIEnemy::Inf;
	}
	const FVector Pos = MI::Web::FromUnreal(P->GetPlayerRules().Feet);
	const double Height = P->GetPlayerRules().bCrouching ? ShotTargetCrouch : ShotTargetStand;
	const double Ox = Origin.X - Pos.X, Oz = Origin.Z - Pos.Z, Oy = Origin.Y - Pos.Y;
	const double R2 = ShotTargetRadius * ShotTargetRadius;
	if (Ox * Ox + Oz * Oz <= R2 && Oy >= 0 && Oy <= Height)
	{
		return 0;
	}
	double TIn = 0, TOut = MaxDist;
	const double A = D.X * D.X + D.Z * D.Z;
	if (A > 1e-12)
	{
		const double B = Ox * D.X + Oz * D.Z;
		const double Disc = B * B - A * (Ox * Ox + Oz * Oz - R2);
		if (Disc < 0)
		{
			return MIEnemy::Inf;
		}
		const double Root = FMath::Sqrt(Disc);
		TIn = FMath::Max(TIn, (-B - Root) / A);
		TOut = FMath::Min(TOut, (-B + Root) / A);
	}
	else if (Ox * Ox + Oz * Oz > R2)
	{
		return MIEnemy::Inf;
	}
	if (FMath::Abs(D.Y) > 1e-12)
	{
		const double T0 = -Oy / D.Y, T1 = (Height - Oy) / D.Y;
		TIn = FMath::Max(TIn, FMath::Min(T0, T1));
		TOut = FMath::Min(TOut, FMath::Max(T0, T1));
	}
	else if (Oy < 0 || Oy > Height)
	{
		return MIEnemy::Inf;
	}
	return TIn > TOut ? MIEnemy::Inf : TIn;
}

FVector UMIGameSubsystem::Hitscan(int32 EnemyId, const FVector& Origin, const FVector& Dir, double Range, double Damage)
{
	using namespace MI::Web;
	using namespace MIGameSubsystemPrivate;
	UWorld* World = GetWorld();
	const FVector O = ToUnreal(Origin);
	const FVector D = DirToUnreal(Dir).GetSafeNormal();
	FCollisionQueryParams Params(SCENE_QUERY_STAT(MIEnemyRound), false);
	for (const TObjectPtr<AActor>& A : EnemyActors)
	{
		Params.AddIgnoredActor(A.Get());
	}
	if (AMIPlayerCharacter* P = GetPlayer())
	{
		Params.AddIgnoredActor(P);
	}
	FHitResult Hit;
	const bool bWorld = World && World->LineTraceSingleByChannel(Hit, O, O + D * Range * 100.0, MIBulletChannel, Params);
	const double Limit = bWorld ? Hit.Distance * 0.01 : Range;
	const double TP = RayPlayer(Origin, Dir, Limit);
	if (TP <= Limit)
	{
		if (AMIPlayerCharacter* P = GetPlayer())
		{
			FMIDamage Dm;
			Dm.Amount = Damage;
			Dm.Kind = EMIDamageKind::Bullet;
			Dm.Source = EMIDamageSource::Enemy;
			Dm.From = O;
			Dm.Point = O + D * TP * 100.0;
			Dm.Direction = D;
			Dm.Weapon = TEXT("smg");
			P->ApplyMIDamage(Dm);
		}
		return Origin + Dir * TP;
	}
	if (!bWorld)
	{
		return Origin + Dir * Range;
	}
	IMIDamageable* Target = Cast<IMIDamageable>(Hit.GetActor());
	if (Target && Target->IsMIDamageableAlive() && Target->GetMIDamageableKind() == TEXT("explosive"))
	{
		FMIDamage Dm;
		Dm.Amount = Damage;
		Dm.Kind = EMIDamageKind::Bullet;
		Dm.Source = EMIDamageSource::Enemy;
		Dm.From = O;
		Dm.Point = Hit.ImpactPoint;
		Dm.Direction = D;
		Target->ApplyMIDamage(Dm);
	}
	if (FMIGameEvents* Events = UMIEventSubsystem::Get(this))
	{
		FMIImpactEvent Impact;
		Impact.Point = Hit.ImpactPoint;
		Impact.Normal = Hit.ImpactNormal;
		Impact.Direction = D;
		Impact.From = EMIDamageSource::Enemy;
		Impact.Actor = Hit.GetActor();
		Events->Impact.Broadcast(Impact);
	}
	return FromUnreal(Hit.ImpactPoint);
}

void UMIGameSubsystem::DamagePlayer(double Amount, const FVector& From, FName Kind)
{
	AMIPlayerCharacter* P = GetPlayer();
	if (!P)
	{
		return;
	}
	FMIDamage Dm;
	Dm.Amount = Amount;
	Dm.Kind = Kind == TEXT("melee") ? EMIDamageKind::Melee : Kind == TEXT("bolt") ? EMIDamageKind::Bolt : Kind == TEXT("blast") ? EMIDamageKind::Blast : EMIDamageKind::Bullet;
	Dm.Source = EMIDamageSource::Enemy;
	Dm.From = MI::Web::ToUnreal(From);
	Dm.Weapon = Kind;
	P->ApplyMIDamage(Dm);
}

void UMIGameSubsystem::Explode(int32 EnemyId, const FVector& Pos, double Radius, double Damage, double PlayerScale)
{
	if (UMICombatSubsystem* Combat = UMICombatSubsystem::Get(this))
	{
		// combat.js: explosions at least 5 m wide are announced as big.
		Combat->Explode(MI::Web::ToUnreal(Pos), Radius * 100.0, Damage, INDEX_NONE, Radius >= 5.0, GetEnemyActor(SlotOf(EnemyId)), PlayerScale);
	}
}

void UMIGameSubsystem::HitExplosive(int32 Item, double Amount)
{
	if (UMICombatSubsystem* Combat = UMICombatSubsystem::Get(this); Combat && Combat->GetExplosives().GetItems().IsValidIndex(Item))
	{
		Combat->GetExplosives().Damage(Item, Amount, EMIDamageSource::Enemy, true);
	}
}
