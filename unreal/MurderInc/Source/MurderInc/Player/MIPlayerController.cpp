#include "Player/MIPlayerController.h"

#include "Camera/PlayerCameraManager.h"

#include "Weapons/MIFirstPersonRig.h"
#include "Weapons/MIWeaponComponent.h"

#include "Kismet/GameplayStatics.h"
#include "Core/MIDamageable.h"
#include "EngineUtils.h"
#include "World/MIBoxWorld.h"
#include "World/MIExplosive.h"
#include "Core/MIEvents.h"
#include "Enemies/MIEnemies.h"
#include "Weapons/MICombatSubsystem.h"
#include "Enemies/MIEnemyActors.h"
#include "Components/CapsuleComponent.h"
#include "Core/MIMath.h"

#include "Core/Data/MIDataSubsystem.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "Engine/LocalPlayer.h"
#include "InputAction.h"
#include "InputActionValue.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "MurderInc.h"
#include "Flow/MIGameSubsystem.h"
#include "Player/MIPlayerCharacter.h"
#include "Flow/MIRunSetupSubsystem.h"
#include "Engine/GameViewportClient.h"
#include "Framework/Application/SlateApplication.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Widgets/SViewport.h"
#include "Widgets/SWindow.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "UI/MIFrontEnd.h"
#include "Weapons/MIWeaponComponent.h"

UInputAction* AMIPlayerController::MakeAction(const TCHAR* Name, EInputActionValueType Type)
{
	UInputAction* Action = NewObject<UInputAction>(this, Name);
	Action->ValueType = Type;
	Actions.Add(FName(Name), Action);
	return Action;
}

void AMIPlayerController::BuildInputAssets()
{
	if (MappingContext)
	{
		return;
	}
	MappingContext = NewObject<UInputMappingContext>(this, TEXT("IMC_Player"));
	const auto Map = [this](const UInputAction* Action, const FKey& Key, bool bOntoY = false, bool bNegate = false)
	{
		FEnhancedActionKeyMapping& Mapping = MappingContext->MapKey(Action, Key);
		if (bOntoY)
		{
			Mapping.Modifiers.Add(NewObject<UInputModifierSwizzleAxis>(MappingContext));
		}
		if (bNegate)
		{
			Mapping.Modifiers.Add(NewObject<UInputModifierNegate>(MappingContext));
		}
	};

	UInputAction* Move = MakeAction(TEXT("IA_Move"), EInputActionValueType::Axis2D);
	Map(Move, EKeys::W, true);
	Map(Move, EKeys::S, true, true);
	Map(Move, EKeys::D);
	Map(Move, EKeys::A, false, true);
	// The sticks arrive raw: the web game's dead zone (and the right stick's curve) is applied here, not by a modifier.
	Map(MakeAction(TEXT("IA_MoveStick"), EInputActionValueType::Axis2D), EKeys::Gamepad_Left2D);
	Map(MakeAction(TEXT("IA_Look"), EInputActionValueType::Axis2D), EKeys::Mouse2D);

	const auto Button = [this, &Map](const TCHAR* Name, std::initializer_list<FKey> Keys)
	{
		UInputAction* Action = MakeAction(Name, EInputActionValueType::Boolean);
		for (const FKey& Key : Keys)
		{
			Map(Action, Key);
		}
	};
	Button(TEXT("IA_Jump"), {EKeys::SpaceBar, EKeys::Gamepad_FaceButton_Bottom});
	Button(TEXT("IA_Sprint"), {EKeys::LeftShift, EKeys::RightShift});
	Button(TEXT("IA_SprintLatch"), {EKeys::Gamepad_LeftThumbstick});  // one click holds the sprint (spec 01 3.17)
	Button(TEXT("IA_Crouch"), {EKeys::C, EKeys::Gamepad_FaceButton_Right, EKeys::Gamepad_LeftShoulder});
	Button(TEXT("IA_Fire"), {EKeys::LeftMouseButton, EKeys::Enter, EKeys::Gamepad_RightTrigger});
	Button(TEXT("IA_Aim"), {EKeys::RightMouseButton, EKeys::Gamepad_LeftTrigger});
	// The triggers' analog axes as well: a browser's gamepad comes through Pixel Streaming with its triggers as axes
	// only (Epic's player, Inputs/GamepadController.ts), never as the trigger buttons. Down beyond pad.trigger.
	Map(MakeAction(TEXT("IA_FireAxis"), EInputActionValueType::Axis1D), EKeys::Gamepad_RightTriggerAxis);
	Map(MakeAction(TEXT("IA_AimAxis"), EInputActionValueType::Axis1D), EKeys::Gamepad_LeftTriggerAxis);
	Button(TEXT("IA_Reload"), {EKeys::R});
	// The pad's X (Square) is one button with two meanings (src/input.js padDown): it reloads, unless a grab prompt
	// is showing at the moment of the press: then it grabs, for that whole hold. One action, decided when it starts.
	Button(TEXT("IA_PadX"), {EKeys::Gamepad_FaceButton_Left});
	Button(TEXT("IA_Swap"), {EKeys::Q, EKeys::Gamepad_FaceButton_Top});
	// LOADOUT.md 4.2 (frontend.json input.game): the wheel and D-pad up / down are next and previous; with two guns
	// they give the gun the web's swap gave. The mouse wheel steps at most once per player.input.wheelDebounce.
	Button(TEXT("IA_NextWheel"), {EKeys::MouseScrollDown});
	Button(TEXT("IA_PreviousWheel"), {EKeys::MouseScrollUp});
	Button(TEXT("IA_NextPad"), {EKeys::Gamepad_DPad_Up});
	Button(TEXT("IA_PreviousPad"), {EKeys::Gamepad_DPad_Down});
	Button(TEXT("IA_Weapon1"), {EKeys::One, EKeys::NumPadOne, EKeys::Gamepad_DPad_Left});
	Button(TEXT("IA_Weapon2"), {EKeys::Two, EKeys::NumPadTwo, EKeys::Gamepad_DPad_Right});
	Button(TEXT("IA_Weapon3"), {EKeys::Three, EKeys::NumPadThree});
	Button(TEXT("IA_Weapon4"), {EKeys::Four, EKeys::NumPadFour});
	Button(TEXT("IA_FireMode"), {EKeys::B});
	Button(TEXT("IA_Inspect"), {EKeys::T});
	Button(TEXT("IA_View"), {EKeys::Gamepad_Special_Left});  // a tap is the selector, a hold inspects
	Map(MakeAction(TEXT("IA_RightStick"), EInputActionValueType::Axis2D), EKeys::Gamepad_Right2D);  // the look; the wheel while it is open
	Button(TEXT("IA_Melee"), {EKeys::F, EKeys::V, EKeys::MiddleMouseButton, EKeys::Gamepad_RightShoulder, EKeys::Gamepad_RightThumbstick});
	Button(TEXT("IA_Interact"), {EKeys::E});

	// The flow and the menus: these also work while the game is paused.
	const auto MenuButton = [&Button, this](const TCHAR* Name, std::initializer_list<FKey> Keys)
	{
		Button(Name, Keys);
		Actions[FName(Name)]->bTriggerWhenPaused = true;
	};
	MenuButton(TEXT("IA_Pause"), {EKeys::Escape, EKeys::P, EKeys::Gamepad_Special_Right});
	MenuButton(TEXT("IA_MenuUp"), {EKeys::Up, EKeys::Gamepad_DPad_Up, EKeys::Gamepad_LeftStick_Up});
	MenuButton(TEXT("IA_MenuDown"), {EKeys::Down, EKeys::Gamepad_DPad_Down, EKeys::Gamepad_LeftStick_Down});
	MenuButton(TEXT("IA_MenuLeft"), {EKeys::Left, EKeys::Gamepad_DPad_Left, EKeys::Gamepad_LeftStick_Left});
	MenuButton(TEXT("IA_MenuRight"), {EKeys::Right, EKeys::Gamepad_DPad_Right, EKeys::Gamepad_LeftStick_Right});
	MenuButton(TEXT("IA_MenuConfirm"), {EKeys::Enter, EKeys::SpaceBar, EKeys::Gamepad_FaceButton_Bottom});
	MenuButton(TEXT("IA_MenuBack"), {EKeys::BackSpace, EKeys::Gamepad_FaceButton_Right});
	MenuButton(TEXT("IA_MenuClick"), {EKeys::LeftMouseButton});  // a click on a card's row (AMIHUD draws them)
}

void AMIPlayerController::BeginPlay()
{
	Super::BeginPlay();
	FMIConfigData Config;
	FString Error;
	if (const UMIDataSubsystem* Data = UMIDataSubsystem::Get(this); Data && Data->IsLoaded())
	{
		Config = Data->GetConfig();
	}
	else if (!UMIDataSubsystem::LoadConfig(Config, Error))
	{
		UE_LOG(LogMI, Error, TEXT("Input: config.json: %s"), *Error);
	}
	MouseDegreesPerCount = Config.Player.Look.MouseDegreesPerCount;
	MouseWake = Config.Player.Look.MouseWake;
	PadLook.Config = Config.Player.Look.Pad;
	Assist.Data = Config.Player.Look.Assist;
	AssistStrength = Assist.Data.ScaleOf(Assist.Data.DefaultStrength);
	WheelDebounce = Config.Player.Look.WheelDebounce;
	Switch.Config.WheelDebounce = WheelDebounce;
	if (const UMIDataSubsystem* Data = UMIDataSubsystem::Get(this); Data && Data->IsLoadoutLoaded())
	{
		const FMILoadoutData& L = Data->GetLoadout();
		Switch.Config.WheelMinGuns = L.WheelMinGuns;
		Switch.Config.WheelHold = L.WheelHold;
		Switch.Config.InspectHold = L.InspectHold;
		Switch.Config.Deadzone = L.WheelDeadzone;
		Switch.Config.MouseRadius = L.WheelMouseRadius;
	}
	Sensitivity = Config.Settings.Sensitivity;
	bInvertY = Config.Settings.bInvertY;
	// The pawn's view is the rules' camera; the legacy look scales must not stack on top.
	SetIgnoreLookInput(false);
}

void AMIPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	BuildInputAssets();
	if (IsLocalPlayerController())
	{
		if (UEnhancedInputLocalPlayerSubsystem* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer()))
		{
			Subsystem->AddMappingContext(MappingContext, 0);
		}
	}
	UEnhancedInputComponent* In = Cast<UEnhancedInputComponent>(InputComponent);
	if (!In)
	{
		UE_LOG(LogMI, Error, TEXT("Input: %s has no Enhanced Input component (check DefaultInputComponentClass in DefaultInput.ini)"), *GetNameSafe(this));
		return;
	}
	const auto State = [this]() -> FMIPlayerInputState* { AMIPlayerCharacter* C = GetMICharacter(); return C ? &C->GetInput() : nullptr; };

	// The keys and the left stick add up (the rules cut the sum back to length 1). The keys write the move as they
	// change; the stick takes part only while it is pushed (PlayerTick), so a move set by a test, a bot or the console
	// stays as set.
	In->BindActionValueLambda(Actions[TEXT("IA_Move")], ETriggerEvent::Triggered, [this, State](const FInputActionValue& V) { KeyMove = V.Get<FVector2D>(); if (FMIPlayerInputState* S = State()) S->Move = KeyMove + PadMove; });
	In->BindActionValueLambda(Actions[TEXT("IA_Move")], ETriggerEvent::Completed, [this, State](const FInputActionValue&) { KeyMove = FVector2D::ZeroVector; if (FMIPlayerInputState* S = State()) S->Move = PadMove; });
	In->BindActionValueLambda(Actions[TEXT("IA_MoveStick")], ETriggerEvent::Triggered, [this](const FInputActionValue& V) { LeftStick = V.Get<FVector2D>(); });
	In->BindActionValueLambda(Actions[TEXT("IA_MoveStick")], ETriggerEvent::Completed, [this](const FInputActionValue&) { LeftStick = FVector2D::ZeroVector; });
	In->BindActionValueLambda(Actions[TEXT("IA_Look")], ETriggerEvent::Triggered, [this](const FInputActionValue& V)
	{
		if (!bStreamMouse)  // in a stream the mouse comes event by event (StreamMouseEvent), not from this axis
		{
			MouseLook(V.Get<FVector2D>());  // the desktop: one count is one web pixel
		}
	});
	// bCarries: a hold that carries through a card (sprint and crouch, spec 01 3.16); every other press that left a
	// card is swallowed (DropMenuPresses).
	const auto Hold = [&In, this, State](const TCHAR* Name, bool FMIPlayerInputState::*Held, bool FMIPlayerInputState::*Pressed, bool bCarries = false)
	{
		UInputAction* Action = Actions[FName(Name)];
		In->BindActionValueLambda(Action, ETriggerEvent::Started, [this, State, Held, Pressed, bCarries](const FInputActionValue&)
		{
			FMIPlayerInputState* S = State();
			if (S && (bCarries || !SwallowsPresses()))
			{
				if (Held) S->*Held = true;
				if (Pressed) S->*Pressed = true;
			}
		});
		In->BindActionValueLambda(Action, ETriggerEvent::Completed, [State, Held](const FInputActionValue&)
		{
			if (FMIPlayerInputState* S = State())
			{
				if (Held) S->*Held = false;
			}
		});
	};
	Hold(TEXT("IA_Jump"), nullptr, &FMIPlayerInputState::bJumpPressed);
	Hold(TEXT("IA_Crouch"), &FMIPlayerInputState::bCrouch, nullptr, true);
	// Sprint: the keys hold it; the pad's L3 latches it (PlayerTick lets the latch go).
	In->BindActionValueLambda(Actions[TEXT("IA_Sprint")], ETriggerEvent::Started, [State](const FInputActionValue&) { if (FMIPlayerInputState* S = State()) S->bSprint = true; });
	In->BindActionValueLambda(Actions[TEXT("IA_Sprint")], ETriggerEvent::Completed, [this, State](const FInputActionValue&) { if (FMIPlayerInputState* S = State()) S->bSprint = bSprintLatch; });
	In->BindActionValueLambda(Actions[TEXT("IA_SprintLatch")], ETriggerEvent::Started, [this](const FInputActionValue&)
	{
		AMIPlayerCharacter* C = GetMICharacter();
		if (C && C->TakesLook())
		{
			bSprintLatch = !bSprintLatch;
			C->GetInput().bSprint = bSprintLatch;
		}
	});
	// Fire and aim: the keys and buttons, and the trigger's own axis beyond pad.trigger.
	In->BindActionValueLambda(Actions[TEXT("IA_Fire")], ETriggerEvent::Started, [this](const FInputActionValue&) { SetFire(bFireKey, true); });
	In->BindActionValueLambda(Actions[TEXT("IA_Fire")], ETriggerEvent::Completed, [this](const FInputActionValue&) { SetFire(bFireKey, false); });
	In->BindActionValueLambda(Actions[TEXT("IA_FireAxis")], ETriggerEvent::Triggered, [this](const FInputActionValue& V) { SetFire(bFireAxis, V.Get<float>() > PadLook.Config.Trigger); });
	In->BindActionValueLambda(Actions[TEXT("IA_FireAxis")], ETriggerEvent::Completed, [this](const FInputActionValue&) { SetFire(bFireAxis, false); });
	In->BindActionValueLambda(Actions[TEXT("IA_Aim")], ETriggerEvent::Started, [this](const FInputActionValue&) { SetAim(bAimKey, true); });
	In->BindActionValueLambda(Actions[TEXT("IA_Aim")], ETriggerEvent::Completed, [this](const FInputActionValue&) { SetAim(bAimKey, false); });
	In->BindActionValueLambda(Actions[TEXT("IA_AimAxis")], ETriggerEvent::Triggered, [this](const FInputActionValue& V) { SetAim(bAimAxis, V.Get<float>() > PadLook.Config.Trigger); });
	In->BindActionValueLambda(Actions[TEXT("IA_AimAxis")], ETriggerEvent::Completed, [this](const FInputActionValue&) { SetAim(bAimAxis, false); });
	Hold(TEXT("IA_Reload"), nullptr, &FMIPlayerInputState::bReloadPressed);
	Hold(TEXT("IA_Weapon1"), nullptr, &FMIPlayerInputState::bWeapon1Pressed);
	Hold(TEXT("IA_Weapon2"), nullptr, &FMIPlayerInputState::bWeapon2Pressed);
	Hold(TEXT("IA_Weapon3"), nullptr, &FMIPlayerInputState::bWeapon3Pressed);
	Hold(TEXT("IA_Weapon4"), nullptr, &FMIPlayerInputState::bWeapon4Pressed);
	Hold(TEXT("IA_Melee"), nullptr, &FMIPlayerInputState::bMeleePressed);
	const auto Edge = [&In, this](const TCHAR* Name, ETriggerEvent Event, TFunction<void(FMISwitchInput&)> Do)
	{
		In->BindActionValueLambda(Actions[FName(Name)], Event, [this, Do](const FInputActionValue&)
		{
			Do(Switch);
			FlushSwitch();
		});
	};
	Edge(TEXT("IA_Swap"), ETriggerEvent::Started, [this](FMISwitchInput& S) { S.SwapDown(Now()); });
	Edge(TEXT("IA_Swap"), ETriggerEvent::Completed, [this](FMISwitchInput& S) { S.SwapUp(Now()); });
	Edge(TEXT("IA_NextWheel"), ETriggerEvent::Started, [this](FMISwitchInput& S) { S.WheelStep(1, Now()); });
	Edge(TEXT("IA_PreviousWheel"), ETriggerEvent::Started, [this](FMISwitchInput& S) { S.WheelStep(-1, Now()); });
	Edge(TEXT("IA_NextPad"), ETriggerEvent::Started, [](FMISwitchInput& S) { S.PadStep(1); });
	Edge(TEXT("IA_PreviousPad"), ETriggerEvent::Started, [](FMISwitchInput& S) { S.PadStep(-1); });
	Edge(TEXT("IA_FireMode"), ETriggerEvent::Started, [](FMISwitchInput& S) { S.FireModeKey(); });
	Edge(TEXT("IA_Inspect"), ETriggerEvent::Started, [](FMISwitchInput& S) { S.InspectKey(); });
	Edge(TEXT("IA_View"), ETriggerEvent::Started, [this](FMISwitchInput& S) { S.ViewDown(Now()); });
	Edge(TEXT("IA_View"), ETriggerEvent::Completed, [this](FMISwitchInput& S) { S.ViewUp(Now()); });
	// The right stick: the look (PlayerTick), and the pick on the weapon wheel while that is open. The game viewport
	// hands the right stick's Y over upside down (FSceneViewport::OnAnalogValueChanged negates Gamepad_RightY, and only
	// that axis): stick up arrives as -1. Here up is +Y again, for the look and for the wheel (slot 1 at the top).
	// Found in the stream test of 2026-11-24: stick up looked down, and the wheel picked the opposite slot.
	In->BindActionValueLambda(Actions[TEXT("IA_RightStick")], ETriggerEvent::Triggered, [this](const FInputActionValue& V)
	{
		const FVector2D Raw = V.Get<FVector2D>();
		RightStick = FVector2D(Raw.X, -Raw.Y);
		Switch.Stick(RightStick);
	});
	In->BindActionValueLambda(Actions[TEXT("IA_RightStick")], ETriggerEvent::Completed, [this](const FInputActionValue&) { RightStick = FVector2D::ZeroVector; Switch.Stick(RightStick); });
	const auto Game = [this]() { return UMIGameSubsystem::Get(this); };
	// The grab is held by E or by the pad's X; the pad's X only when its press found a prompt (below).
	In->BindActionValueLambda(Actions[TEXT("IA_Interact")], ETriggerEvent::Started, [this, Game](const FInputActionValue&) { bGrabKey = true; if (UMIGameSubsystem* G = Game()) G->SetInteractHeld(true); });
	In->BindActionValueLambda(Actions[TEXT("IA_Interact")], ETriggerEvent::Completed, [this, Game](const FInputActionValue&) { bGrabKey = false; if (UMIGameSubsystem* G = Game()) G->SetInteractHeld(bGrabPad); });
	In->BindActionValueLambda(Actions[TEXT("IA_PadX")], ETriggerEvent::Started, [this, State, Game](const FInputActionValue&)
	{
		UMIGameSubsystem* G = Game();
		if (G && !G->GetRules().View().Prompt.IsEmpty())
		{
			// A reel is in reach: this hold grabs, and reloads nothing (the gun stays up under fire).
			bGrabPad = true;
			G->SetInteractHeld(true);
		}
		else if (FMIPlayerInputState* S = State(); S && !SwallowsPresses())
		{
			S->bReloadPressed = true;
		}
	});
	In->BindActionValueLambda(Actions[TEXT("IA_PadX")], ETriggerEvent::Completed, [this, Game](const FInputActionValue&)
	{
		if (bGrabPad)
		{
			bGrabPad = false;
			if (UMIGameSubsystem* G = Game()) G->SetInteractHeld(bGrabKey);
		}
	});
	In->BindActionValueLambda(Actions[TEXT("IA_Pause")], ETriggerEvent::Started, [this, Game](const FInputActionValue&)
	{
		if (UMIGameSubsystem* G = Game())
		{
			const bool bCard = G->GetMenu().Screen != EMIMenuScreen::None;
			G->PauseKey();
			if (bCard)
			{
				DropMenuPresses();
			}
		}
	});
	const auto Menu = [&In, this, Game](const TCHAR* Name, bool bActs, TFunction<void(UMIGameSubsystem&)> Do)
	{
		In->BindActionValueLambda(Actions[FName(Name)], ETriggerEvent::Started, [this, Game, bActs, Do](const FInputActionValue&)
		{
			UMIGameSubsystem* G = Game();
			if (G && G->GetMenu().Screen != EMIMenuScreen::None)
			{
				Do(*G);
				if (bActs)
				{
					DropMenuPresses();  // Enter is also fire, Space and the pad's A also jump: not on the press that left the card
				}
			}
		});
	};
	Menu(TEXT("IA_MenuUp"), false, [](UMIGameSubsystem& G) { G.MenuMove(-1); });
	Menu(TEXT("IA_MenuDown"), false, [](UMIGameSubsystem& G) { G.MenuMove(1); });
	Menu(TEXT("IA_MenuLeft"), false, [](UMIGameSubsystem& G) { G.MenuAdjust(-1); });
	Menu(TEXT("IA_MenuRight"), false, [](UMIGameSubsystem& G) { G.MenuAdjust(1); });
	Menu(TEXT("IA_MenuConfirm"), true, [](UMIGameSubsystem& G) { G.MenuConfirm(); });
	Menu(TEXT("IA_MenuBack"), true, [](UMIGameSubsystem& G) { G.MenuBack(); });
	// A click on a card: the row under the cursor (the HUD stored where it drew the rows), as the viewport reports
	// the cursor at the click.
	Menu(TEXT("IA_MenuClick"), true, [this](UMIGameSubsystem& G)
	{
		float X = 0.f, Y = 0.f;
		if (GetMousePosition(X, Y))
		{
			G.MenuClick(FVector2D(X, Y));
		}
	});
}

bool AMIPlayerController::InputKey(const FInputKeyEventArgs& Params)
{
	NoteDevice(Params.Key, Params.Event, Params.AmountDepressed);
	return Super::InputKey(Params);
}

void AMIPlayerController::NoteDevice(const FKey& Key, EInputEvent Event, float Value)
{
	const FMIPadLookData& P = PadLook.Config;
	if (Key.IsGamepadKey())
	{
		if (Key == EKeys::Gamepad_LeftTriggerAxis || Key == EKeys::Gamepad_RightTriggerAxis)
		{
			if (Value > P.Trigger) UsePad(true);
		}
		else if (Key.IsAnalog())
		{
			if (MILook::Deadzone(Value, P.Deadzone) != 0.0) UsePad(true);  // a stick beyond its dead zone
		}
		else if (Event == IE_Pressed)
		{
			UsePad(true);
		}
	}
	else if (!Key.IsAnalog() && !Key.IsTouch() && Event == IE_Pressed)
	{
		UsePad(false);  // a key or a mouse button (mouse travel: MouseLook)
	}
}

void AMIPlayerController::UsePad(bool bPad)
{
	if (bPad == bPadActive)
	{
		return;
	}
	bPadActive = bPad;
	if (!bPad)
	{
		PadLook.Reset();  // src/input.js wake(): leaving the pad clears its boost; the aim slow-down ends with bPad
	}
}

void AMIPlayerController::SetFire(bool& Source, bool bDown)
{
	const bool bWas = bFireKey || bFireAxis;
	Source = bDown;
	const bool bNow = bFireKey || bFireAxis;
	AMIPlayerCharacter* C = GetMICharacter();
	if (!C || bNow == bWas)
	{
		return;
	}
	FMIPlayerInputState& S = C->GetInput();
	if (!bNow)
	{
		S.bFire = false;
	}
	else if (!SwallowsPresses())
	{
		S.bFire = true;
		S.bFirePressed = true;
	}
}

void AMIPlayerController::SetAim(bool& Source, bool bDown)
{
	const bool bWas = bAimKey || bAimAxis;
	Source = bDown;
	const bool bNow = bAimKey || bAimAxis;
	AMIPlayerCharacter* C = GetMICharacter();
	if (C && bNow != bWas && !(bNow && SwallowsPresses()))
	{
		C->GetInput().bAds = bNow;
	}
}

void AMIPlayerController::DropMenuPresses()
{
	// The press that acted on a card is usually still down when the run goes live two frames later: Enter and the
	// left mouse button are also fire, Space and the pad's A also jump. Clear what such a press already set, and let
	// no play action start from a press for the next two frames of play; a fresh press after that counts. Movement,
	// sprint and crouch that are still held carry on (spec 01 3.16).
	SwallowTicks = 2;
	if (AMIPlayerCharacter* C = GetMICharacter())
	{
		FMIPlayerInputState& S = C->GetInput();
		S.bFire = S.bFirePressed = S.bAds = false;
		S.bJumpPressed = S.bReloadPressed = S.bSwapPressed = S.bMeleePressed = false;
		S.bWeapon1Pressed = S.bWeapon2Pressed = S.bWeapon3Pressed = S.bWeapon4Pressed = false;
		S.bNextPressed = S.bPreviousPressed = S.bFireModePressed = S.bInspectPressed = false;
		S.WheelPick = INDEX_NONE;
		S.LookDegrees = FVector2D::ZeroVector;
	}
	Switch.Reset();
	StreamPending = FVector2D::ZeroVector;
}

void AMIPlayerController::DropAllHeld()
{
	// The engine's side: every key and button up, every axis at rest. No release will come for them (their viewer is
	// gone), and a key that still read as down would start its action again when the run resumes: the player would
	// walk, turn or fire by himself. The actions that were running end with this, as on a real release.
	FlushPressedKeys();
	// The controller's own side, at once (the actions' own endings arrive with the next input tick).
	KeyMove = PadMove = LeftStick = RightStick = FVector2D::ZeroVector;
	bFireKey = bFireAxis = bAimKey = bAimAxis = false;
	bSprintLatch = false;
	bGrabKey = bGrabPad = false;
	StreamPending = FVector2D::ZeroVector;
	MouseTravel = 0.0;
	PadLook.Reset();
	Switch.Reset();
	if (UMIGameSubsystem* G = UMIGameSubsystem::Get(this))
	{
		G->SetInteractHeld(false);
	}
	if (AMIPlayerCharacter* C = GetMICharacter())
	{
		// Everything held and every edge not yet used; which device is in use stays.
		FMIPlayerInputState& S = C->GetInput();
		const bool bPad = S.bPad;
		S = FMIPlayerInputState();
		S.bPad = bPad;
	}
}

void AMIPlayerController::SetStreamMouse(const FMIStreamMouse& Shape)
{
	StreamMouse = Shape;
	bStreamMouse = true;
}

void AMIPlayerController::ClearStreamMouse()
{
	bStreamMouse = false;
	StreamPending = FVector2D::ZeroVector;
}

bool AMIPlayerController::IsInLivePlay() const
{
	const AMIPlayerCharacter* C = GetMICharacter();
	return C && C->TakesLook();
}

bool AMIPlayerController::StreamMouseEvent(const FVector2D& Counts)
{
	const AMIPlayerCharacter* C = GetMICharacter();
	if (!C || !C->TakesLook())
	{
		// Over a card or a set-up screen the cursor takes every move as it comes, and nothing gathers for the moment
		// play resumes.
		StreamPending = FVector2D::ZeroVector;
		return true;
	}
	FVector2D Pixels;
	if (!StreamMouse.Event(Counts, Pixels))
	{
		++MouseSpikes;
		return false;
	}
	StreamPending += FVector2D(Pixels.X, -Pixels.Y);  // Slate's Y grows downward; the look takes mouse up as +Y
	return true;
}

void AMIPlayerController::MouseLook(const FVector2D& Pixels)
{
	AMIPlayerCharacter* C = GetMICharacter();
	if (!C || !C->TakesLook())
	{
		return;
	}
	// A nudge of the desk does not take the device back from a pad; a few pixels in one frame do.
	MouseTravel += FMath::Abs(Pixels.X) + FMath::Abs(Pixels.Y);
	if (MouseTravel >= MouseWake)
	{
		UsePad(false);
	}
	if (Switch.BlocksLook())
	{
		Switch.MouseMove(Pixels);  // the weapon wheel takes the mouse while it is open
		return;
	}
	// Over a target the aim assist slows the mouse too (the last frame's factor: the events come before the tick).
	const double K = MouseDegreesPerCount * Sensitivity * (IsPadActive() ? 1.0 : AssistSlow);
	// Mouse up is +Y here; the rules look down for +Y.
	C->GetInput().LookDegrees += FVector2D(Pixels.X * K, -Pixels.Y * K * (bInvertY ? -1.0 : 1.0));
}

AMIPlayerCharacter* AMIPlayerController::GetMICharacter() const
{
	return Cast<AMIPlayerCharacter>(GetPawn());
}

double AMIPlayerController::Now() const
{
	return GetWorld() ? GetWorld()->GetRealTimeSeconds() : 0.0;
}

void AMIPlayerController::FlushSwitch()
{
	AMIPlayerCharacter* C = GetMICharacter();
	if (C && C->GetWeapon())
	{
		Switch.SetGuns(C->GetWeapon()->GetRules().NumGuns());
	}
	const FMISwitchFrame F = Switch.Consume();
	if (!C)
	{
		return;
	}
	FMIPlayerInputState& S = C->GetInput();
	S.bSwapPressed |= F.bSwap;
	S.bNextPressed |= F.bNext;
	S.bPreviousPressed |= F.bPrevious;
	S.bFireModePressed |= F.bFireMode;
	S.bInspectPressed |= F.bInspect;
	if (F.WheelPick != INDEX_NONE)
	{
		S.WheelPick = F.WheelPick;
	}
	if (Switch.IsWheelOpen())
	{
		S.bFire = S.bFirePressed = false;  // no fire while choosing
	}
}

void AMIPlayerController::PlayerTick(float DeltaTime)
{
	Super::PlayerTick(DeltaTime);
#if !UE_BUILD_SHIPPING
	if (FreezeIn >= 0.f && (FreezeIn -= DeltaTime) < 0.f)
	{
		UGameplayStatics::SetGlobalTimeDilation(this, 0.0001f);
		FreezeIn = -1.f;
	}
#endif
	Switch.Tick(Now());
	FlushSwitch();

	// The stream's mouse events since the last frame.
	if (bStreamMouse)
	{
		const FVector2D Pixels = StreamPending;
		StreamPending = FVector2D::ZeroVector;
		if (!Pixels.IsZero())
		{
			MouseLook(Pixels);
		}
	}
	MouseTravel = 0.0;

	AMIPlayerCharacter* C = GetMICharacter();
	const bool bLive = C && C->TakesLook();
	// The right stick turns the view, slowed over an enemy while the pad is the device in use (the weapon rules work
	// the slow-down out; it is 1 otherwise). The boost follows the stick whether or not the look is taken.
	// The assist's slow-down (pad 0.45 over a Goon) replaces the weapon's old 0.55 while the assist is on: the deeper wins.
	AssistSlow = UpdateAimAssist(DeltaTime, bLive);
	const double WeaponSlow = C && C->GetWeapon() && C->GetWeapon()->IsReady() ? C->GetWeapon()->GetRules().GetAimSlow() : 1.0;
	const double AimSlow = bAimAssist ? FMath::Min(WeaponSlow, AssistSlow) : WeaponSlow;
	const FVector2D Turn = PadLook.Step(RightStick, DeltaTime, Sensitivity, AimSlow, bInvertY);
	if (bLive && !Switch.BlocksLook())
	{
		C->GetInput().LookDegrees += Turn;
	}
	if (C)
	{
		FMIPlayerInputState& S = C->GetInput();
		// The left stick moves, on top of the keys, while it is pushed (and on the frame it lets go).
		const FVector2D Stick = MILook::Deadzone(LeftStick, PadLook.Config.Deadzone);
		if (!Stick.IsZero() || !PadMove.IsZero())
		{
			PadMove = Stick;
			S.Move = KeyMove + PadMove;
		}
		// The sprint latch lets go when the stick eases off forward or play stops.
		if (bSprintLatch && (!bLive || PadMove.Y < PadLook.Config.SprintForward))
		{
			bSprintLatch = false;
			S.bSprint = false;
		}
		S.bPad = bPadActive;
	}
	if (SwallowTicks > 0)
	{
		--SwallowTicks;
	}
}

void AMIPlayerController::SetAimAssist(bool bOn, FName Strength)
{
	bAimAssist = bOn;
	AssistStrength = Assist.Data.ScaleOf(Strength);
	if (!bOn)
	{
		Assist.Reset();
		AssistSlow = 1.0;
	}
}

double AMIPlayerController::UpdateAimAssist(double Dt, bool bLive)
{
	AMIPlayerCharacter* C = GetMICharacter();
	UWorld* World = GetWorld();
	if (!bAimAssist || !bLive || !C || !World || Switch.BlocksLook() || !C->GetPlayerRules().bAlive)
	{
		Assist.Reset();
		return 1.0;
	}
	const FMIPlayerRules& R = C->GetPlayerRules();
	const FVector Eye = R.Eye;
	// Where the crosshair points now (the view's own angles, recoil included): Forward is only set by the late half of the frame,
	// so it is a frame behind here and the turns would be worked out from where the view was.
	const double AimYaw = MI::DegToRad(R.GetAimYaw());
	const double AimPitch = MI::DegToRad(R.GetAimPitch());
	const bool bPad = bPadActive;
	const double Reach = Assist.Reach(bPad, AssistStrength);

	struct FCandidate { double Angle; FVector2D Error; const AMIGoon* Goon; FVector Point; };
	TArray<FCandidate, TInlineAllocator<8>> Near;
	for (TActorIterator<AMIGoon> It(World); It; ++It)
	{
		const AMIGoon* G = *It;
		if (!G->IsMIDamageableAlive() || !G->GetBodyHit())
		{
			continue;
		}
		const UCapsuleComponent* Body = G->GetBodyHit();
		const FVector Point = Body->GetComponentLocation() + FVector::UpVector * (Body->GetScaledCapsuleHalfHeight() * Assist.Data.ChestFraction);
		const FVector To = Point - Eye;
		const double Dist = To.Size();
		if (Dist < 1.0 || Dist > Assist.Data.Range)
		{
			continue;
		}
		const FVector Dir = To / Dist;
		const FVector2D Error(MI::WrapDegrees(MI::RadToDeg(FMath::Atan2(Dir.Y, Dir.X) - AimYaw)),
			MI::RadToDeg(FMath::Asin(FMath::Clamp(Dir.Z, -1.0, 1.0)) - AimPitch));
		const double Angle = Error.Size();
		if (Angle <= Reach)
		{
			Near.Add({Angle, Error, G, Point});
		}
	}
	// A line of sight for the nearest few in angle only: the bullets' own channel, so cover and walls stop it as they stop a round.
	Near.Sort([](const FCandidate& A, const FCandidate& B) { return A.Angle < B.Angle; });
	AssistErrors.Reset();
	FCollisionQueryParams Params(SCENE_QUERY_STAT(MIAssistSight), false, C);
	for (int32 I = 0; I < Near.Num() && I < 4; ++I)
	{
		FHitResult Hit;
		if (World->LineTraceSingleByChannel(Hit, Eye, Near[I].Point, MIBulletChannel, Params) && Hit.GetActor() == Near[I].Goon)
		{
			AssistErrors.Add(Near[I].Error);
		}
	}

	FMIAssistFrame F;
	F.bOn = true;
	F.bPad = bPad;
	F.Strength = AssistStrength;
	F.bFire = C->GetInput().bFire;
	F.bAds = C->GetInput().bAds;
	F.Dt = Dt;
	// The player's own turn this frame, as the look gathered it (X right, Y up).
	F.PlayerTurn = FVector2D(C->GetInput().LookDegrees.X, -C->GetInput().LookDegrees.Y);
	if (bPad)
	{
		F.PlayerTurn += MILook::Deadzone(RightStick, PadLook.Config.Deadzone);  // the stick's direction (the pad's turn is worked out after this)
	}
	FMIAssistResult Out = Assist.Step(F, AssistErrors);
	if (!Out.Turn.IsZero())
	{
		C->GetInput().AssistDegrees += Out.Turn;
	}
	return Out.Slow;
}

void AMIPlayerController::MIInput(const FString& Action, float Value)
{
#if !UE_BUILD_SHIPPING  // a debug command: it does nothing in the Shipping game
	AMIPlayerCharacter* C = GetMICharacter();
	if (!C)
	{
		return;
	}
	FMIPlayerInputState& S = C->GetInput();
	const bool bDown = Value != 0.f;
	const FString A = Action.ToLower();
	if (A == TEXT("fire")) { S.bFire = bDown; S.bFirePressed |= bDown; }
	else if (A == TEXT("ads")) S.bAds = bDown;
	else if (A == TEXT("sprint")) S.bSprint = bDown;
	else if (A == TEXT("crouch")) S.bCrouch = bDown;
	else if (A == TEXT("jump")) S.bJumpPressed |= bDown;
	else if (A == TEXT("reload")) S.bReloadPressed |= bDown;
	else if (A == TEXT("swap"))
	{
		// Through the switch layer, as Q: with two guns a press swaps; with three or more a tap swaps on release
		// and a hold opens the wheel.
		bDown ? Switch.SwapDown(Now()) : Switch.SwapUp(Now());
		FlushSwitch();
	}
	else if (A == TEXT("weapon3")) S.bWeapon3Pressed |= bDown;
	else if (A == TEXT("weapon4")) S.bWeapon4Pressed |= bDown;
	else if (A == TEXT("next")) S.bNextPressed |= bDown;
	else if (A == TEXT("previous")) S.bPreviousPressed |= bDown;
	else if (A == TEXT("firemode")) S.bFireModePressed |= bDown;
	else if (A == TEXT("wheelx")) Switch.Stick(FVector2D(Value, 0.0));
	else if (A == TEXT("wheely")) Switch.Stick(FVector2D(0.0, Value));
	else if (A == TEXT("melee")) S.bMeleePressed |= bDown;
	else if (A == TEXT("inspect")) S.bInspectPressed |= bDown;
	else if (A == TEXT("weapon1")) S.bWeapon1Pressed |= bDown;
	else if (A == TEXT("weapon2")) S.bWeapon2Pressed |= bDown;
	else if (A == TEXT("forward")) S.Move.Y = FMath::Clamp(Value, -1.f, 1.f);
	else if (A == TEXT("right")) S.Move.X = FMath::Clamp(Value, -1.f, 1.f);
	else UE_LOG(LogMI, Warning, TEXT("MIInput: unknown action '%s'"), *Action);
#endif
}

void AMIPlayerController::MIFreezeAfter(float Seconds)
{
#if !UE_BUILD_SHIPPING
	UGameplayStatics::SetGlobalTimeDilation(this, 1.f);
	FreezeIn = FMath::Max(0.f, Seconds);
#endif
}

void AMIPlayerController::MIFreezeOn(const FString& Event, float Delay)
{
#if !UE_BUILD_SHIPPING
	UGameplayStatics::SetGlobalTimeDilation(this, 1.f);
	FreezeEvent = FName(*Event.ToLower());
	FreezeDelay = FMath::Max(0.f, Delay);
	FMIGameEvents* Events = UMIEventSubsystem::Get(this);
	if (Events && !bFreezeBound)
	{
		bFreezeBound = true;
		const auto Arm = [this](FName Kind)
		{
			if (FreezeEvent == Kind)
			{
				FreezeIn = FreezeDelay;
				FreezeEvent = NAME_None;
				UE_LOG(LogMI, Log, TEXT("MIFreezeOn: %s, frozen in %.3f s"), *Kind.ToString(), FreezeDelay);
			}
		};
		Events->Enemy.AddWeakLambda(this, [this, Arm](const FMIEnemyEvent& E)
		{
			// Only a Goon in plain sight within 16 m (the picture is of one firing at the player): look at it.
			AMIPlayerCharacter* C = GetMICharacter();
			UWorld* World = GetWorld();
			if (E.Kind != FMIEnemyEvent::EKind::Fire || E.Type != MIEnemy::EType::Goon || !C || !World || FreezeEvent != TEXT("enemyfire"))
			{
				return;
			}
			const FVector Head = MI::Web::ToUnreal(E.Pos);  // the round's origin: the Goon's muzzle
			const FVector Eye = C->GetPlayerRules().Eye;
			FHitResult Hit;
			FCollisionQueryParams Q(SCENE_QUERY_STAT(MIFreezeSight), false, C);
			if (FVector::Dist(Head, Eye) > 1300.0 || World->LineTraceSingleByChannel(Hit, Eye, Head, ECC_Visibility, Q))
			{
				return;
			}
			const FVector D = Head - Eye;
			C->GetPlayerRules().Yaw = FMath::RadiansToDegrees(FMath::Atan2(D.Y, D.X));
			C->GetPlayerRules().Pitch = FMath::RadiansToDegrees(FMath::Atan2(D.Z, D.Size2D()));
			Arm(TEXT("enemyfire"));
		});
		Events->Explosion.AddWeakLambda(this, [Arm](const FMIExplosionEvent&) { Arm(TEXT("explosion")); });
		Events->WeaponFire.AddWeakLambda(this, [Arm](const FMIShotFiredEvent&) { Arm(TEXT("fire")); });
		Events->WeaponReload.AddWeakLambda(this, [Arm](const FMIReloadEvent& E) { if (E.Phase == TEXT("start")) Arm(TEXT("reload")); });
	}
#endif
}

void AMIPlayerController::MIPose(float X, float Y, float Z, float Yaw, float Pitch)
{
#if !UE_BUILD_SHIPPING
	if (AMIPlayerCharacter* C = GetMICharacter())
	{
		C->TeleportFeet(FVector(X, Y, Z));
		C->GetPlayerRules().Yaw = Yaw;
		C->GetPlayerRules().Pitch = Pitch;
		if (PlayerCameraManager) PlayerCameraManager->SetGameCameraCutThisFrame();  // a teleport: no history from before
	}
#endif
}

void AMIPlayerController::MIGripProbe(const FString& Label)
{
#if !UE_BUILD_SHIPPING
	if (AMIPlayerCharacter* C = GetMICharacter(); C && C->GetWeapon() && C->GetWeapon()->GetFirstPersonRig())
	{
		C->GetWeapon()->GetFirstPersonRig()->ProbeGrip(Label.IsEmpty() ? TEXT("now") : Label);
	}
#endif
}

void AMIPlayerController::MIBlowNearest()
{
#if !UE_BUILD_SHIPPING
	AMIPlayerCharacter* C = GetMICharacter();
	if (!C)
	{
		return;
	}
	AMIExplosive* Best = nullptr;
	double BestD = 1e30;
	for (TActorIterator<AMIExplosive> It(GetWorld()); It; ++It)
	{
		const FVector To = It->GetActorLocation() - C->GetActorLocation();
		if (It->IsMIDamageableAlive() && FVector::DotProduct(To.GetSafeNormal2D(), C->GetPlayerRules().Forward.GetSafeNormal2D()) > 0.8 && To.Size() < BestD)
		{
			Best = *It;
			BestD = To.Size();
		}
	}
	if (Best)
	{
		FMIDamage D;
		D.Amount = 9999.0;
		D.Kind = EMIDamageKind::Bullet;
		D.Source = EMIDamageSource::Player;
		D.From = C->GetPlayerRules().Eye;
		D.Point = Best->GetActorLocation();
		D.Direction = (Best->GetActorLocation() - C->GetPlayerRules().Eye).GetSafeNormal();
		D.Instigator = C;
		Best->ApplyMIDamage(D);
		UE_LOG(LogMI, Log, TEXT("MIBlowNearest: %s at %.0f m"), *Best->GetName(), BestD / 100.0);
	}
#endif
}

void AMIPlayerController::MIStart(const FString& Mode, const FString& Skip)
{
#if !UE_BUILD_SHIPPING  // a debug command: it does nothing in the Shipping game
	if (UMIGameSubsystem* G = UMIGameSubsystem::Get(this))
	{
		G->StartRunWithSetup(Mode.IsEmpty() ? NAME_None : FName(*Mode), Skip == TEXT("skip"));
	}
#endif
}

void AMIPlayerController::MIPauseKey()
{
#if !UE_BUILD_SHIPPING  // a debug command: it does nothing in the Shipping game
	if (UMIGameSubsystem* G = UMIGameSubsystem::Get(this))
	{
		G->PauseKey();
	}
#endif
}

void AMIPlayerController::MIMenu(const FString& Command)
{
#if !UE_BUILD_SHIPPING  // a debug command: it does nothing in the Shipping game
	UMIGameSubsystem* G = UMIGameSubsystem::Get(this);
	if (!G)
	{
		return;
	}
	const FString C = Command.ToLower();
	// The set-up flow (LOADOUT.md 8.5): MIMenu fe <action> [args], the console twin of every control.
	if (C.StartsWith(TEXT("fe ")))
	{
		FString Rest = Command.Mid(3).TrimStartAndEnd();
		FString Action, Arg;
		if (!Rest.Split(TEXT(" "), &Action, &Arg))
		{
			Action = Rest;
		}
		if (UMIFrontEnd* F = G->GetFrontEnd())
		{
			const bool bOk = F->Act(Action, Arg);
			UE_LOG(LogMI, Log, TEXT("MIMenu fe %s %s: %s, screen %s"), *Action, *Arg, bOk ? TEXT("ok") : TEXT("refused"), *FMIFrontEndRules::ScreenName(F->GetRules().GetScreen()));
		}
		return;
	}
	if (C == TEXT("up")) G->MenuMove(-1);
	else if (C == TEXT("down")) G->MenuMove(1);
	else if (C == TEXT("left")) G->MenuAdjust(-1);
	else if (C == TEXT("right")) G->MenuAdjust(1);
	else if (C == TEXT("confirm")) G->MenuConfirm();
	else if (C == TEXT("back")) G->MenuBack();
	else if (C == TEXT("changesetup") || C == TEXT("totitle"))
	{
		const int32 I = G->GetMenu().IndexOf(FName(*C));
		if (I != INDEX_NONE)
		{
			G->GetMenu().Selected = I;
			G->MenuConfirm();
		}
	}
#endif
}

void AMIPlayerController::MIShot(const FString& Path)
{
#if !UE_BUILD_SHIPPING  // a debug command: it does nothing in the Shipping game
	UGameViewportClient* Client = GetWorld() ? GetWorld()->GetGameViewport() : nullptr;
	TSharedPtr<SViewport> Widget = Client ? Client->GetGameViewportWidget() : nullptr;
	TArray<FColor> Pixels;
	FIntVector Size;
	if (!Widget.IsValid() || !FSlateApplication::IsInitialized())
	{
		UE_LOG(LogMI, Error, TEXT("MIShot: no game viewport"));
		return;
	}
	TSharedRef<SWidget> Ref = Widget.ToSharedRef();
	if (!FSlateApplication::Get().TakeScreenshot(Ref, Pixels, Size) || Pixels.Num() == 0)
	{
		UE_LOG(LogMI, Error, TEXT("MIShot: the viewport could not be read back"));
		return;
	}
	for (FColor& C : Pixels)
	{
		C.A = 255;
	}
	TArray64<uint8> Png;
	FImageUtils::PNGCompressImageArray(Size.X, Size.Y, TArrayView64<const FColor>(Pixels.GetData(), Pixels.Num()), Png);
	const bool bSaved = FFileHelper::SaveArrayToFile(Png, *Path);
	UE_LOG(LogMI, Log, TEXT("MIShot: %s %d x %d %s"), *Path, Size.X, Size.Y, bSaved ? TEXT("saved") : TEXT("NOT saved"));
#endif
}

void AMIPlayerController::MISetup(const FString& Command)
{
	// MISetup dump: the set-up as JSON, for bug reports (LOADOUT.md 7).
	// MISetup overlay <file>: dev only, patches mesh paths and statuses in memory (the pack import's future data).
	FString Verb, Arg;
	if (!Command.Split(TEXT(" "), &Verb, &Arg))
	{
		Verb = Command;
	}
	if (Verb == TEXT("overlay"))
	{
#if UE_BUILD_SHIPPING
		UE_LOG(LogMI, Warning, TEXT("MISetup overlay: dev only, not in shipping builds"));
		return;
#else
		UMIDataSubsystem* Data = GetGameInstance() ? GetGameInstance()->GetSubsystem<UMIDataSubsystem>() : nullptr;
		FString Text;
		TSharedPtr<FJsonObject> Root;
		if (Data && FFileHelper::LoadFileToString(Text, *Arg) && FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root))
		{
			const int32 N = Data->EditLoadoutForDev().ApplyOverlay(Root);
			UE_LOG(LogMI, Warning, TEXT("MISetup overlay: %d field(s) patched in memory from %s (dev only, nothing written)"), N, *Arg);
			if (UMIGameSubsystem* G = UMIGameSubsystem::Get(this); G && G->GetFrontEnd())
			{
				G->GetFrontEnd()->Changed();
			}
		}
		else
		{
			UE_LOG(LogMI, Error, TEXT("MISetup overlay: cannot read %s"), *Arg);
		}
		return;
#endif
	}
	if (const UMIRunSetupSubsystem* S = UMIRunSetupSubsystem::Get(this))
	{
		UE_LOG(LogMI, Log, TEXT("MISetup: %s"), *S->GetSetup().ToJsonString());
	}
}

void AMIPlayerController::MIKey(const FString& Command)
{
#if !UE_BUILD_SHIPPING
	TArray<FString> Parts;
	Command.ParseIntoArrayWS(Parts);
	const FKey K = Parts.Num() > 0 ? FKey(FName(*Parts[0])) : FKey();
	if (!K.IsValid() || !FSlateApplication::IsInitialized())
	{
		UE_LOG(LogMI, Error, TEXT("MIKey: unknown key '%s'"), *Command);
		return;
	}
	// Only the words after the key name: FString compares without case, so the arrow keys "Up" and "Down" read as the
	// release-only and press-only words, and "MIKey Up" sent a bare release (logged "not handled", READY.md W3).
	TArray<FString> Words = Parts;
	if (Words.Num() > 0)
	{
		Words.RemoveAt(0);
	}
	const bool bCtrl = Words.Contains(TEXT("ctrl")), bShift = Words.Contains(TEXT("shift"));
	const bool bDownOnly = Words.Contains(TEXT("down")), bUpOnly = Words.Contains(TEXT("up"));
	UMIGameSubsystem* G = UMIGameSubsystem::Get(this);
	UMIFrontEnd* F = G ? G->GetFrontEnd() : nullptr;
	bool bHandled = false;
	if (F && F->IsShown())
	{
		bHandled = bUpOnly ? F->SendKey(K, false, bCtrl, bShift) : bDownOnly ? F->SendKey(K, true, bCtrl, bShift) : F->PressKey(K, bCtrl, bShift);
		UE_LOG(LogMI, Log, TEXT("MIKey %s: %s, screen %s%s"), *Command, bHandled ? TEXT("handled") : TEXT("not handled"), *FMIFrontEndRules::ScreenName(F->GetRules().GetScreen()), F->bOnNext ? TEXT(" (Next focused)") : TEXT(""));
		return;
	}
	// The run: the game viewport takes the key, as from the keyboard or the pad.
	FSlateApplication& App = FSlateApplication::Get();
	App.SetAllUserFocusToGameViewport();
	const FModifierKeysState Mods(bShift, false, bCtrl, false, false, false, false, false, false);
	if (!bUpOnly) bHandled = App.ProcessKeyDownEvent(FKeyEvent(K, Mods, 0, false, 0, 0));
	if (!bDownOnly) App.ProcessKeyUpEvent(FKeyEvent(K, Mods, 0, false, 0, 0));
	UE_LOG(LogMI, Log, TEXT("MIKey %s: to the game viewport, %s"), *Command, bHandled ? TEXT("handled") : TEXT("not handled"));
#endif
}

void AMIPlayerController::MIViewSize(int32 Width, int32 Height)
{
#if !UE_BUILD_SHIPPING
	UGameViewportClient* Client = GetWorld() ? GetWorld()->GetGameViewport() : nullptr;
	TSharedPtr<SViewport> Widget = Client ? Client->GetGameViewportWidget() : nullptr;
	TSharedPtr<SWindow> Window = Widget.IsValid() && FSlateApplication::IsInitialized() ? FSlateApplication::Get().FindWidgetWindow(Widget.ToSharedRef()) : nullptr;
	if (!Window.IsValid() || Width < 64 || Height < 64)
	{
		UE_LOG(LogMI, Error, TEXT("MIViewSize: no window around the game viewport"));
		return;
	}
	FVector2D Now;
	Client->GetViewportSize(Now);
	const FVector2D Win = Window->GetSizeInScreen();
	Window->Resize(Win + FVector2D(Width, Height) - Now);
	UE_LOG(LogMI, Log, TEXT("MIViewSize: viewport %.0f x %.0f in a %.0f x %.0f window -> window %.0f x %.0f (asked %d x %d; call again after a redraw to settle)"),
		Now.X, Now.Y, Win.X, Win.Y, Win.X + Width - Now.X, Win.Y + Height - Now.Y, Width, Height);
#endif
}

void AMIPlayerController::MIInteract(float Value)
{
#if !UE_BUILD_SHIPPING  // a debug command: it does nothing in the Shipping game
	if (UMIGameSubsystem* G = UMIGameSubsystem::Get(this))
	{
		G->SetInteractHeld(Value != 0.f);
	}
#endif
}

void AMIPlayerController::MIFaceEnemy(float Metres)
{
#if !UE_BUILD_SHIPPING  // a debug command: it does nothing in the Shipping game
	if (UMIGameSubsystem* G = UMIGameSubsystem::Get(this))
	{
		G->FaceNearestEnemy(Metres != 0.f ? Metres : 8.0);  // negative: turn only
		// A snap turn: no history from before it (fix pass: polish-hold showed the forearm's last place as an orange
		// ghost on the pavement; a turn in play, frame to frame, is the check that the viewmodel itself does not ghost).
		if (PlayerCameraManager) PlayerCameraManager->SetGameCameraCutThisFrame();
	}
#endif
}
