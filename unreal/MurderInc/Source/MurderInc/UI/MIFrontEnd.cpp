#include "UI/MIFrontEnd.h"

#include "Camera/CameraActor.h"
#include "Camera/PlayerCameraManager.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Flow/MIGameSubsystem.h"
#include "Flow/MIRunSetupSubsystem.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/PlayerController.h"
#include "MurderInc.h"
#include "Player/MIPlayerCharacter.h"
#include "UI/MIShowroom.h"
#include "UI/SMIFrontEnd.h"
#include "Weapons/MIWeaponComponent.h"
#include "Widgets/SWeakWidget.h"

namespace MIFrontEndObjPrivate
{
	FVector StageOrigin(const TSharedPtr<FJsonObject>& Frontend)
	{
		const TSharedPtr<FJsonValue> V = MIJson::Get(Frontend, TEXT("stage.origin"));
		if (V.IsValid() && V->Type == EJson::Array && V->AsArray().Num() == 3)
		{
			return FVector(V->AsArray()[0]->AsNumber(), V->AsArray()[1]->AsNumber(), V->AsArray()[2]->AsNumber());
		}
		return FVector(0, 0, 100000);
	}
}

bool UMIFrontEnd::Init(UMIGameSubsystem* InGame)
{
	Game = InGame;
	UMIRunSetupSubsystem* Setup = UMIRunSetupSubsystem::Get(InGame);
	const FMILoadoutData* Data = Setup ? Setup->GetData() : nullptr;
	FString Error;
	if (!Setup)
	{
		OwnData = MakeUnique<FMILoadoutData>();
		Data = FMILoadoutData::Load(*OwnData, Error) ? OwnData.Get() : nullptr;
	}
	if (!Data || !FMILoadoutResolver::LoadRoots(ConfigRoot, PresentationRoot, Error) || !UMIDataSubsystem::LoadJsonFile(TEXT("text.json"), TextRoot, Error))
	{
		UE_LOG(LogMI, Error, TEXT("Front end: no loadout data (%s): the canvas title stays"), *Error);
		return false;
	}
	Resolver = MakeUnique<FMILoadoutResolver>(*Data, ConfigRoot, PresentationRoot);
	Rules.TextJson = TextRoot;
	Rules.ConfigJson = ConfigRoot;
	const FMISettings& S = InGame->GetSettings();
	FMIRunSetup Saved = Setup && Setup->HasSetup() ? Setup->GetSetup() : Data->ParitySetup(S.Mode, S.Difficulty, S.Time);
	Saved.Mode = S.Mode;
	Saved.Difficulty = S.Difficulty;
	Saved.Time = S.Time;
	FMIReadiness Ready;
	if (Setup)
	{
		Ready = Setup->MakeReadiness();
	}
	else
	{
		Ready.Data = Data;
		Ready.AssetExists = FMIReadiness::PackageExists();
	}
	Rules.Init(Data, Ready, Resolver.Get(), Saved);
	ViewData = MakeUnique<FMIViewmodelData>();
	FMIViewmodelData::Load(*ViewData, Error);

	UWorld* World = InGame->GetWorld();
	if (World)
	{
		FActorSpawnParameters P;
		P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		P.ObjectFlags |= RF_Transient;
		Showroom = World->SpawnActor<AMIShowroom>(MIFrontEndObjPrivate::StageOrigin(Data->FrontendJson), FRotator::ZeroRotator, P);
		if (Showroom)
		{
			Showroom->Setup(Data->FrontendJson, ViewData.Get());
		}
	}
	Widget = SNew(SMIFrontEnd).Owner(this);
	return true;
}

void UMIFrontEnd::Show()
{
	if (bShown)
	{
		return;
	}
	bShown = true;
	UWorld* World = Game.IsValid() ? Game->GetWorld() : nullptr;
	if (UGameViewportClient* Viewport = World ? World->GetGameViewport() : nullptr; Viewport && Widget)
	{
		Viewport->AddViewportWidgetContent(Widget.ToSharedRef(), 10);
	}
	bInputMode = false;
	ViewTargetFor = -1;
	Focus = 0;
	Changed();
	SyncStage(true);
}

void UMIFrontEnd::Hide()
{
	if (!bShown)
	{
		return;
	}
	bShown = false;
	UWorld* World = Game.IsValid() ? Game->GetWorld() : nullptr;
	if (UGameViewportClient* Viewport = World ? World->GetGameViewport() : nullptr; Viewport && Widget)
	{
		Viewport->RemoveViewportWidgetContent(Widget.ToSharedRef());
	}
	if (APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr)
	{
		PC->SetInputMode(FInputModeGameOnly());
	}
}

void UMIFrontEnd::OpenBriefing()
{
	Rules.OpenBriefing();
	AfterScreenChange();
}

void UMIFrontEnd::OpenHome()
{
	Rules.OpenHome();
	AfterScreenChange();
}

int32 UMIFrontEnd::NumFocusable() const
{
	switch (Rules.GetScreen())
	{
	case EMIFrontScreen::Home: return 8;  // Hit the block, Gear up, Mode, Difficulty, Time, the summary's Crew, Guns, Where
	case EMIFrontScreen::Crew: return Rules.OfferedCrew().Num();
	case EMIFrontScreen::Loadout: return Pane == 0 ? Rules.Rack(RackFilter).Num() : Rules.GetData().CarryMax;
	case EMIFrontScreen::Workbench: return Rules.BenchOptions(Rules.GetBenchSlot()).Num();
	case EMIFrontScreen::Where: return 4;     // level, time, mode, difficulty
	case EMIFrontScreen::Briefing: return 5;  // crew, carrying, block, style, Hit the block
	}
	return 0;
}

void UMIFrontEnd::AfterScreenChange()
{
	// Every screen opens with the saved choice selected and focused.
	const FMIRunSetup& S = Rules.GetSetup();
	Focus = 0;
	Pane = 0;
	switch (Rules.GetScreen())
	{
	case EMIFrontScreen::Crew: Focus = FMath::Max(0, Rules.OfferedCrew().IndexOfByKey(S.Crew)); break;
	case EMIFrontScreen::Loadout: Focus = FMath::Max(0, Rules.Rack(RackFilter).IndexOfByKey(Rules.GetFocusGun())); break;
	case EMIFrontScreen::Workbench: Focus = FMath::Max(0, Rules.BenchOptions(Rules.GetBenchSlot()).IndexOfByKey(Rules.FittedIn(Rules.GetBenchSlot()))); break;
	case EMIFrontScreen::Briefing: Focus = 4; break;
	default: break;
	}
	if (Rules.ConsumeRemember())
	{
		Remember();
	}
	Changed();
	SyncStage(true);
}

void UMIFrontEnd::Remember()
{
	if (UMIRunSetupSubsystem* S = UMIRunSetupSubsystem::Get(Game.Get()))
	{
		S->SetSetup(Rules.GetSetup());
	}
	if (Game.IsValid())
	{
		Game->SaveSettings();
	}
}

void UMIFrontEnd::WriteSetting(FName Which, FName Value)
{
	if (!Game.IsValid())
	{
		return;
	}
	FMISettings& S = Game->GetSettings();
	bool bChanged = false;
	if (Which == TEXT("mode")) { Rules.SetMode(Value); bChanged = S.SetMode(Rules.GetSetup().Mode); }
	else if (Which == TEXT("difficulty")) { Rules.SetDifficulty(Value); Game->SetDifficulty(Value); }
	else if (Which == TEXT("time")) { Rules.SetTime(Value); bChanged = S.SetTime(Value); }
	if (bChanged)
	{
		Game->SaveSettings();
	}
	Changed();
}

void UMIFrontEnd::StartRun()
{
	Remember();
	if (Game.IsValid())
	{
		const FMIRunSetup S = Rules.GetSetup();
		Hide();
		Game->BeginWithSetup(S);
	}
}

bool UMIFrontEnd::ResolveShown(FName Gun, const FMIGunBuild* Build, FMIResolvedGun& Out) const
{
	FString Error;
	return Resolver && Resolver->ResolveGun(Gun, Build, &Rules.GetReadiness(), Out, Error);
}

// ---------------------------------------------------------------------------------------------------- actions

bool UMIFrontEnd::Act(const FString& Action, const FString& Arg)
{
	const FString A = Action.ToLower();
	const FName N(*Arg);
	const EMIFrontScreen Before = Rules.GetScreen();
	bool bOk = true;
	if (A == TEXT("hit") || A == TEXT("start"))
	{
		if (Rules.GetScreen() == EMIFrontScreen::Home ? Rules.HitTheBlock() == EMIFrontRequest::StartRun : Rules.Next() == EMIFrontRequest::StartRun)
		{
			StartRun();
			return true;
		}
	}
	else if (A == TEXT("gearup")) Rules.GearUp();
	else if (A == TEXT("next") || A == TEXT("done"))
	{
		if (Rules.Next() == EMIFrontRequest::StartRun)
		{
			StartRun();
			return true;
		}
	}
	else if (A == TEXT("back")) Rules.Back();
	else if (A == TEXT("briefing")) bOk = Rules.ToBriefing();
	else if (A == TEXT("step")) bOk = Rules.GoToStep(FCString::Atoi(*Arg));
	else if (A == TEXT("edit"))
	{
		EMIFrontScreen S;
		bOk = FMIFrontEndRules::ParseScreen(Arg, S);
		if (bOk) Rules.Edit(S);
	}
	else if (A == TEXT("crew")) Rules.ChooseCrew(N);
	else if (A == TEXT("filter")) RackFilter = N;
	else if (A == TEXT("carry")) bOk = Rules.Carry(N);
	else if (A == TEXT("slot"))
	{
		FString SlotText, Gun;
		bOk = Arg.Split(TEXT(" "), &SlotText, &Gun) && Rules.PutInSlot(FName(*Gun), FCString::Atoi(*SlotText) - 1);
	}
	else if (A == TEXT("swap"))
	{
		FString X, Y;
		if (Arg.Split(TEXT(" "), &X, &Y)) Rules.SwapSlots(FCString::Atoi(*X) - 1, FCString::Atoi(*Y) - 1);
	}
	else if (A == TEXT("empty")) Rules.EmptySlot(FCString::Atoi(*Arg) - 1);
	else if (A == TEXT("selectslot")) Rules.SelectSlot(FCString::Atoi(*Arg) - 1);
	else if (A == TEXT("focusgun")) Rules.FocusGun(N);
	else if (A == TEXT("bench")) Rules.OpenWorkbench(N.IsNone() ? Rules.GetFocusGun() : N);
	else if (A == TEXT("benchslot")) Rules.ChooseBenchSlot(N);
	else if (A == TEXT("benchnext")) Rules.BenchNextGun(Arg.IsEmpty() ? 1 : FCString::Atoi(*Arg));
	else if (A == TEXT("preview")) Rules.PreviewPart(Arg == TEXT("factory") ? NAME_None : N);
	else if (A == TEXT("fit")) Rules.Fit(Arg == TEXT("factory") ? NAME_None : N);
	else if (A == TEXT("reset")) { bool bDone = false; for (int32 I = 0; I < 120 && !bDone; ++I) bDone = Rules.HoldReset(1.0 / 60.0, true); }
	else if (A == TEXT("level")) Rules.SetLevel(N);
	else if (A == TEXT("time") || A == TEXT("mode") || A == TEXT("difficulty")) WriteSetting(FName(*A), N);
	else if (A == TEXT("home")) Rules.OpenHome();
	else if (A == TEXT("unready")) Rules.SetShowUnready(Arg != TEXT("0"));
	else if (A == TEXT("showbriefing")) Rules.OpenBriefing();
	else bOk = false;
	if (Rules.GetScreen() != Before || Rules.ConsumeRemember())
	{
		if (Rules.GetScreen() == Before) Remember();
		else AfterScreenChange();
	}
	Changed();
	SyncStage(false);
	return bOk;
}

void UMIFrontEnd::Move(int32 Dx, int32 Dy)
{
	const EMIFrontScreen S = Rules.GetScreen();
	const int32 Count = FMath::Max(1, NumFocusable());
	switch (S)
	{
	case EMIFrontScreen::Home:
	{
		if (Dy != 0) Focus = (Focus + Dy + Count) % Count;
		// The pickers: left / right change them at once, as on the web title.
		const FMISettings::FRules& R = Game->GetSettings().Rules;
		const FMIRunSetup& Set = Rules.GetSetup();
		if (Dx != 0 && Focus == 2) WriteSetting(TEXT("mode"), FMISettings::Next(Set.Mode, R.Modes, Dx));
		if (Dx != 0 && Focus == 3) WriteSetting(TEXT("difficulty"), FMISettings::Next(Set.Difficulty, R.Difficulties, Dx));
		if (Dx != 0 && Focus == 4) WriteSetting(TEXT("time"), FMISettings::Next(Set.Time, R.Times, Dx));
		break;
	}
	case EMIFrontScreen::Crew:
	{
		// Focus selects.
		const TArray<FName> C = Rules.OfferedCrew();
		Focus = (Focus + Dx + Count) % Count;
		if (C.IsValidIndex(Focus)) Rules.ChooseCrew(C[Focus]);
		break;
	}
	case EMIFrontScreen::Loadout:
		if (Pane == 0)
		{
			const int32 Next = Focus + Dx + Dy * 3;  // three cards wide
			Focus = FMath::Clamp(Next, 0, Count - 1);
			const TArray<FName> Rack = Rules.Rack(RackFilter);
			if (Rack.IsValidIndex(Focus)) Rules.FocusGun(Rack[Focus]);
		}
		else
		{
			Focus = FMath::Clamp(Focus + Dy, 0, Count - 1);
			Rules.SelectSlot(Focus);
		}
		break;
	case EMIFrontScreen::Workbench:
	{
		if (Dx != 0)
		{
			const TArray<FName> Slots = Rules.BenchSlots();
			const int32 At = Slots.IndexOfByKey(Rules.GetBenchSlot());
			if (Slots.Num() > 0)
			{
				Rules.ChooseBenchSlot(Slots[((At + Dx) % Slots.Num() + Slots.Num()) % Slots.Num()]);
				Focus = FMath::Max(0, Rules.BenchOptions(Rules.GetBenchSlot()).IndexOfByKey(Rules.FittedIn(Rules.GetBenchSlot())));
			}
		}
		if (Dy != 0)
		{
			const TArray<FName> Options = Rules.BenchOptions(Rules.GetBenchSlot());
			Focus = FMath::Clamp(Focus + Dy, 0, FMath::Max(0, Options.Num() - 1));
			if (Options.IsValidIndex(Focus)) Rules.PreviewPart(Options[Focus]);  // focus previews, it does not fit
		}
		break;
	}
	case EMIFrontScreen::Where:
	{
		if (Dy != 0) Focus = (Focus + Dy + 4) % 4;
		if (Dx != 0)
		{
			const FMIRunSetup& Set = Rules.GetSetup();
			const FMISettings::FRules& R = Game->GetSettings().Rules;
			if (Focus == 0)
			{
				const TArray<FName> L = Rules.Levels();
				Rules.SetLevel(L[((L.IndexOfByKey(Set.Level) + Dx) % L.Num() + L.Num()) % L.Num()]);
			}
			else if (Focus == 1) WriteSetting(TEXT("time"), FMISettings::Next(Set.Time, R.Times, Dx));
			else if (Focus == 2)
			{
				const TArray<FName> M = Rules.Modes();
				if (M.Num() > 0) WriteSetting(TEXT("mode"), M[((M.IndexOfByKey(Set.Mode) + Dx) % M.Num() + M.Num()) % M.Num()]);
			}
			else WriteSetting(TEXT("difficulty"), FMISettings::Next(Set.Difficulty, R.Difficulties, Dx));
		}
		break;
	}
	case EMIFrontScreen::Briefing:
		if (Dy != 0) Focus = (Focus + Dy + 5) % 5;
		break;
	}
	Changed();
	SyncStage(false);
}

void UMIFrontEnd::Activate()
{
	switch (Rules.GetScreen())
	{
	case EMIFrontScreen::Home:
	{
		static const TCHAR* Actions[] = {TEXT("hit"), TEXT("gearup"), nullptr, nullptr, nullptr};
		if (Focus <= 1) Act(Actions[Focus]);
		else if (Focus <= 4) Move(1, 0);
		else Act(TEXT("edit"), Focus == 5 ? TEXT("crew") : Focus == 6 ? TEXT("loadout") : TEXT("where"));
		break;
	}
	case EMIFrontScreen::Loadout:
		if (Pane == 0)
		{
			const TArray<FName> Rack = Rules.Rack(RackFilter);
			if (Rack.IsValidIndex(Focus)) Act(TEXT("carry"), Rack[Focus].ToString());
		}
		else
		{
			Rules.SelectSlot(Focus);  // A on a slot, then A on a card puts the card there
			Pane = 0;
			Changed();
		}
		break;
	case EMIFrontScreen::Workbench:
	{
		const TArray<FName> Options = Rules.BenchOptions(Rules.GetBenchSlot());
		if (Options.IsValidIndex(Focus)) Act(TEXT("fit"), Options[Focus].IsNone() ? TEXT("factory") : Options[Focus].ToString());
		break;
	}
	case EMIFrontScreen::Briefing:
	{
		static const TCHAR* Screens[] = {TEXT("crew"), TEXT("loadout"), TEXT("where"), TEXT("where")};
		if (Focus < 4) Act(TEXT("edit"), Screens[Focus]);
		else Act(TEXT("hit"));
		break;
	}
	default:
		Act(TEXT("next"));  // in a single-choice row moving the focus selects, so A there means Next
		break;
	}
}

bool UMIFrontEnd::Key(const FKey& K, bool bDown, bool bRepeat, bool bCtrl, bool bShift)
{
	const EMIFrontScreen S = Rules.GetScreen();
	// Reset build is a 0.6 s hold (R, gamepad Y), never a tap.
	if (S == EMIFrontScreen::Workbench && (K == EKeys::R || K == EKeys::Gamepad_FaceButton_Top))
	{
		bResetDown = bDown;
		return true;
	}
	if (!bDown)
	{
		return false;
	}
	const bool bEnter = K == EKeys::Enter || K == EKeys::SpaceBar || K == EKeys::Gamepad_FaceButton_Bottom;
	const bool bStart = K == EKeys::Gamepad_Special_Right;
	if ((K == EKeys::Enter && bCtrl) || (bStart && S != EMIFrontScreen::Home && S != EMIFrontScreen::Briefing))
	{
		if (Act(TEXT("briefing"))) return true;
		if (bStart) { Act(TEXT("next")); return true; }
	}
	if (bStart)
	{
		Act(TEXT("hit"));
		return true;
	}
	if (K == EKeys::Escape || K == EKeys::Gamepad_FaceButton_Right)
	{
		if (S == EMIFrontScreen::Home) return false;
		Act(TEXT("back"));
		return true;
	}
	if (K == EKeys::Up || K == EKeys::Gamepad_DPad_Up || K == EKeys::Gamepad_LeftStick_Up)
	{
		if (S == EMIFrontScreen::Loadout && Pane == 1 && bShift) { Act(TEXT("swap"), FString::Printf(TEXT("%d %d"), Focus + 1, Focus)); Focus = FMath::Max(0, Focus - 1); return true; }
		Move(0, -1);
		return true;
	}
	if (K == EKeys::Down || K == EKeys::Gamepad_DPad_Down || K == EKeys::Gamepad_LeftStick_Down)
	{
		if (S == EMIFrontScreen::Loadout && Pane == 1 && bShift) { Act(TEXT("swap"), FString::Printf(TEXT("%d %d"), Focus + 1, Focus + 2)); Focus = FMath::Min(Focus + 1, Rules.GetSetup().Guns.Num() - 1); return true; }
		Move(0, 1);
		return true;
	}
	if (K == EKeys::Left || K == EKeys::Gamepad_DPad_Left || K == EKeys::Gamepad_LeftStick_Left) { Move(-1, 0); return true; }
	if (K == EKeys::Right || K == EKeys::Gamepad_DPad_Right || K == EKeys::Gamepad_LeftStick_Right) { Move(1, 0); return true; }
	if (S == EMIFrontScreen::Loadout)
	{
		const TArray<FName> Rack = Rules.Rack(RackFilter);
		const FName Card = Rack.IsValidIndex(Focus) ? Rack[Focus] : NAME_None;
		if (K == EKeys::Tab) { Pane = 1 - Pane; Focus = 0; Changed(); return true; }
		if (Pane == 0 && !Card.IsNone())
		{
			if (K == EKeys::One || K == EKeys::Two || K == EKeys::Three || K == EKeys::Four)
			{
				const int32 Slot = K == EKeys::One ? 1 : K == EKeys::Two ? 2 : K == EKeys::Three ? 3 : 4;
				Act(TEXT("slot"), FString::Printf(TEXT("%d %s"), Slot, *Card.ToString()));
				return true;
			}
			if (K == EKeys::E || K == EKeys::Gamepad_FaceButton_Top) { Act(TEXT("bench"), Card.ToString()); return true; }
		}
		if (Pane == 1)
		{
			if (K == EKeys::Delete || K == EKeys::Gamepad_FaceButton_Left) { Act(TEXT("empty"), FString::FromInt(Focus + 1)); return true; }
			if (K == EKeys::Gamepad_LeftShoulder) { Act(TEXT("swap"), FString::Printf(TEXT("%d %d"), Focus + 1, Focus)); return true; }
			if (K == EKeys::Gamepad_RightShoulder) { Act(TEXT("swap"), FString::Printf(TEXT("%d %d"), Focus + 1, Focus + 2)); return true; }
			if ((K == EKeys::E || K == EKeys::Gamepad_FaceButton_Top) && Rules.GetSetup().Guns.IsValidIndex(Focus)) { Act(TEXT("bench"), Rules.GetSetup().Guns[Focus].ToString()); return true; }
		}
		if (K == EKeys::Gamepad_LeftShoulder || K == EKeys::Gamepad_RightShoulder)
		{
			Pane = 1 - Pane;  // D-pad across switches panes on a pad
			Focus = 0;
			Changed();
			return true;
		}
	}
	if (S == EMIFrontScreen::Workbench)
	{
		if (K == EKeys::BackSpace || K == EKeys::Gamepad_FaceButton_Left) { Act(TEXT("fit"), TEXT("factory")); return true; }
		if (K == EKeys::LeftBracket || K == EKeys::Gamepad_LeftShoulder) { Act(TEXT("benchnext"), TEXT("-1")); return true; }
		if (K == EKeys::RightBracket || K == EKeys::Gamepad_RightShoulder) { Act(TEXT("benchnext"), TEXT("1")); return true; }
	}
	if (bEnter)
	{
		if (K == EKeys::Enter && S == EMIFrontScreen::Home && Focus > 1 && Focus < 5)
		{
			Act(TEXT("hit"));  // Enter with no other control focused starts, as on the web title
			return true;
		}
		Activate();
		return true;
	}
	return false;
}

// ---------------------------------------------------------------------------------------------------- frame

void UMIFrontEnd::Tick(double Dt)
{
	if (!bShown)
	{
		return;
	}
	if (!bInputMode && Game.IsValid() && Game->GetWorld())
	{
		// The player controller may join after the boot: the screens take the keyboard, mouse and pad once it does.
		if (APlayerController* PC = Game->GetWorld()->GetFirstPlayerController())
		{
			FInputModeUIOnly Mode;
			Mode.SetWidgetToFocus(Widget);
			Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
			PC->SetInputMode(Mode);
			PC->bShowMouseCursor = true;
			bInputMode = true;
		}
	}
	if (Rules.GetScreen() == EMIFrontScreen::Workbench)
	{
		const double Before = Rules.GetResetHold();
		if (Rules.HoldReset(Dt, bResetDown))
		{
			bResetDown = false;
			Remember();
			Changed();
		}
		else if (Before != Rules.GetResetHold())
		{
			Changed();
		}
	}
	SyncViewTarget();
	SyncStage(false);
	// The Briefing's first-person view: the arms hold the first carried gun, as the intro starts from this view.
	if (Rules.GetScreen() == EMIFrontScreen::Briefing && Game.IsValid())
	{
		if (AMIPlayerCharacter* P = Game->GetPlayer())
		{
			if (P->GetWeapon())
			{
				P->GetWeapon()->Step(Dt, FMIWeaponInput(), FVector2D::ZeroVector);
			}
		}
	}
}

void UMIFrontEnd::SyncViewTarget()
{
	UWorld* World = Game.IsValid() ? Game->GetWorld() : nullptr;
	APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	if (!PC)
	{
		return;
	}
	const EMIFrontScreen S = Rules.GetScreen();
	const int32 Want = (S == EMIFrontScreen::Home || S == EMIFrontScreen::Where) ? 0 : S == EMIFrontScreen::Briefing ? 2 : 1;
	if (Want == ViewTargetFor)
	{
		return;
	}
	const bool bFirst = ViewTargetFor < 0;
	ViewTargetFor = Want;
	AActor* Target = nullptr;
	AMIPlayerCharacter* P = Game->GetPlayer();
	if (Want == 0) Target = Game->GetTitleCamera();
	else if (Want == 1) Target = Showroom;
	else Target = P;
	if (P)
	{
		P->SetViewmodelVisible(Want == 2);
		if (Want == 2)
		{
			Game->PreviewSetup(Rules.GetSetup());  // the chosen arms and guns in the player's own hands
		}
	}
	if (Target)
	{
		PC->SetViewTarget(Target);
	}
	// View-target changes fade through black (0.3 s), never two renders.
	if (!bFirst && PC->PlayerCameraManager)
	{
		PC->PlayerCameraManager->StartCameraFade(1.f, 0.f, 0.3f, FLinearColor::Black, false, false);
	}
}

void UMIFrontEnd::SyncStage(bool bForce)
{
	if (!Showroom)
	{
		return;
	}
	const EMIFrontScreen S = Rules.GetScreen();
	const FMIRunSetup& Set = Rules.GetSetup();
	FName Gun;
	FMIGunBuild Build;
	FString Key = FMIFrontEndRules::ScreenName(S);
	if (S == EMIFrontScreen::Workbench)
	{
		Gun = Rules.GetBenchGun();
		Build = Rules.ShownBuild();
		Key += Gun.ToString() + Rules.GetBenchSlot().ToString();
	}
	else if (S == EMIFrontScreen::Loadout)
	{
		Gun = Rules.GetFocusGun().IsNone() && Set.Guns.Num() > 0 ? Set.Guns[0] : Rules.GetFocusGun();
		if (const FMIGunBuild* B = Set.BuildOf(Gun)) Build = *B;
	}
	else if (S == EMIFrontScreen::Crew)
	{
		Gun = Set.Guns.Num() > 0 ? Set.Guns[0] : NAME_None;
		if (const FMIGunBuild* B = Set.BuildOf(Gun)) Build = *B;
		Key += Set.Crew.ToString();
	}
	else
	{
		StageKey = Key;
		return;
	}
	for (const TPair<FName, FName>& P : Build.Parts) Key += P.Key.ToString() + P.Value.ToString();
	Key += Gun.ToString();
	if (!bForce && Key == StageKey)
	{
		return;
	}
	StageKey = Key;
	FMIResolvedGun G;
	if (Gun.IsNone() || !ResolveShown(Gun, &Build, G))
	{
		return;
	}
	if (S == EMIFrontScreen::Crew)
	{
		Showroom->UseShot(AMIShowroom::EShot::Arms);
		Showroom->ShowArms(Rules.GetData().FindCrew(Set.Crew), G);
	}
	else
	{
		Showroom->UseShot(AMIShowroom::EShot::Turntable);
		Showroom->ShowGun(G);
		Showroom->FocusSlot(S == EMIFrontScreen::Workbench ? Rules.GetBenchSlot() : NAME_None);
	}
}
