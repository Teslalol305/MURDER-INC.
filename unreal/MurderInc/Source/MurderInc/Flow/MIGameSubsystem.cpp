#include "Flow/MIGameSubsystem.h"

#include "AudioDevice.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Core/Data/MIDataSubsystem.h"
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
#include "Player/MIPlayerController.h"
#include "Weapons/MICombatSubsystem.h"
#include "Weapons/MIWeaponComponent.h"
#include "World/MIBlockGeometry.h"
#include "World/MIExplosive.h"
#include "World/MILevelData.h"
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
		for (TActorIterator<AMIPlayerCharacter> It(GetWorld()); It; ++It)
		{
			Player = *It;
			break;
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
	}
	if (Options.bPersist)
	{
		if (const UMISaveGame* Save = Cast<UMISaveGame>(UGameplayStatics::LoadGameFromSlot(Settings.Rules.Slot, 0)))
		{
			Settings.FromSave(*Save);
		}
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
		Field.Gunfire(FromUnreal(E.Muzzle));
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
}

void UMIGameSubsystem::MenuMove(int32 Dy)
{
	Menu.Move(Dy);
}

void UMIGameSubsystem::MenuAdjust(int32 Dx)
{
	const FMIMenuItem* Item = Menu.Current();
	if (!Item || !Item->bAdjust || Dx == 0)
	{
		return;
	}
	const FName Id = Item->Id;
	const FMISettings::FRules& R = Settings.Rules;
	bool bChanged = false;
	if (Id == TEXT("mode")) bChanged = Settings.SetMode(FMISettings::Next(Settings.Mode, R.Modes, Dx));
	else if (Id == TEXT("difficulty"))
	{
		bChanged = Settings.SetDifficulty(FMISettings::Next(Settings.Difficulty, R.Difficulties, Dx));
		Rules.SetDifficulty(Settings.Difficulty);
	}
	else if (Id == TEXT("time")) bChanged = Settings.SetTime(FMISettings::Next(Settings.Time, R.Times, Dx));
	else if (Id == TEXT("quality")) bChanged = Settings.SetQuality(FMISettings::Next(Settings.Quality, R.Qualities, Dx));
	else if (Id == TEXT("sens")) bChanged = Settings.SetSens(Settings.Sens + Dx * R.SensStep);
	else if (Id == TEXT("volume")) bChanged = Settings.SetVolume(Settings.Volume + Dx * R.VolumeStep);
	else if (Id == TEXT("fov")) bChanged = Settings.SetFov(Settings.Fov + Dx * R.FovStep);
	else if (Id == TEXT("invert")) bChanged = Settings.SetInvertY(!Settings.bInvertY);
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
	if (Item->bAdjust)
	{
		MenuAdjust(1);
	}
	else if (Id == TEXT("start")) StartRun(Settings.Mode);
	else if (Id == TEXT("resume")) Resume();
	else if (Id == TEXT("restart")) Restart();
	else if (Id == TEXT("retry")) Retry();
	else if (Id == TEXT("again")) Redeploy();
	else if (Id == TEXT("totitle")) ToTitle();
	else if (Id == TEXT("settings"))
	{
		Menu.Return = Menu.Screen;
		Menu.Build(EMIMenuScreen::Settings, Settings, Copy, Ui, Rules.Card(), Rules.GetMode());
	}
	else if (Id == TEXT("back")) MenuBack();
}

void UMIGameSubsystem::MenuBack()
{
	if (Menu.Screen == EMIMenuScreen::Settings)
	{
		Menu.Build(Menu.Return, Settings, Copy, Ui, Rules.Card(), Rules.GetMode());
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
	UGameplayStatics::SaveGameToSlot(Save, Settings.Rules.Slot, 0);
}

void UMIGameSubsystem::ApplySettings()
{
	if (AMIPlayerCharacter* P = GetPlayer())
	{
		P->GetPlayerRules().SetFov(Settings.Fov);
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
	if (FAudioDevice* Audio = GetWorld() ? GetWorld()->GetAudioDeviceRaw() : nullptr)
	{
		Audio->SetTransientPrimaryVolume(Settings.Volume);
	}
	if (UGameUserSettings* User = GEngine ? GEngine->GetGameUserSettings() : nullptr)
	{
		const int32 Scalability = Settings.Rules.Qualities.IndexOfByKey(Settings.Quality) - 1;  // auto, low .. ultra
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

void UMIGameSubsystem::FlowFrame(double Dt)
{
	using namespace MI::Web;
	using namespace MIGameSubsystemPrivate;
	if (!bBooted)
	{
		return;
	}
	Dt = FMath::Min(Dt, 0.05);
	AMIPlayerCharacter* P = GetPlayer();
	if (P && !bPrerequisite)
	{
		P->AddFramePrerequisite(this, FlowTick);
		bPrerequisite = true;
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
	Rules.Update(Dt, FP, bInteract);
	ForwardFlow();
	DrainEnemies();
	ApplyState();
	SyncView(Dt);
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
	if (bSimLive)
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
		P->SetViewmodelVisible(bRun);
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
	}
	if (bStateApplied && S == AppliedState)
	{
		return;
	}
	const EMIGameState Prev = AppliedState;
	AppliedState = S;
	bStateApplied = true;
	UWorld* World = GetWorld();
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
			PC->SetViewTarget(TitleCamera);
		}
		else if (P && PC->GetViewTarget() != P)
		{
			PC->SetViewTarget(P);
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
		PC->PlayerCameraManager->SetManualCameraFade(V.Fade, FLinearColor::Black, false);
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
		R.RegenDelay = RegenDelay;
		R.RegenRate = RegenRate;
		R.SetFov(Settings.Fov);
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
