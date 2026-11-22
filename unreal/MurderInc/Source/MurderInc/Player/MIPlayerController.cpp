#include "Player/MIPlayerController.h"

#include "Core/Data/MIDataSubsystem.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "Engine/LocalPlayer.h"
#include "InputAction.h"
#include "InputActionValue.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "MurderInc.h"
#include "Player/MIPlayerCharacter.h"

UInputAction* AMIPlayerController::MakeAction(const TCHAR* Name, bool bAxis2D)
{
	UInputAction* Action = NewObject<UInputAction>(this, Name);
	Action->ValueType = bAxis2D ? EInputActionValueType::Axis2D : EInputActionValueType::Boolean;
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

	UInputAction* Move = MakeAction(TEXT("IA_Move"), true);
	Map(Move, EKeys::W, true);
	Map(Move, EKeys::S, true, true);
	Map(Move, EKeys::D);
	Map(Move, EKeys::A, false, true);
	Map(Move, EKeys::Gamepad_Left2D);
	Map(MakeAction(TEXT("IA_Look"), true), EKeys::Mouse2D);

	const auto Button = [this, &Map](const TCHAR* Name, std::initializer_list<FKey> Keys)
	{
		UInputAction* Action = MakeAction(Name, false);
		for (const FKey& Key : Keys)
		{
			Map(Action, Key);
		}
	};
	Button(TEXT("IA_Jump"), {EKeys::SpaceBar, EKeys::Gamepad_FaceButton_Bottom});
	Button(TEXT("IA_Sprint"), {EKeys::LeftShift, EKeys::RightShift, EKeys::Gamepad_LeftThumbstick});
	Button(TEXT("IA_Crouch"), {EKeys::C, EKeys::Gamepad_FaceButton_Right, EKeys::Gamepad_LeftShoulder});
	Button(TEXT("IA_Fire"), {EKeys::LeftMouseButton, EKeys::Enter, EKeys::Gamepad_RightTrigger});
	Button(TEXT("IA_Aim"), {EKeys::RightMouseButton, EKeys::Gamepad_LeftTrigger});
	Button(TEXT("IA_Reload"), {EKeys::R, EKeys::Gamepad_FaceButton_Left});
	Button(TEXT("IA_Swap"), {EKeys::Q, EKeys::MouseScrollUp, EKeys::MouseScrollDown, EKeys::Gamepad_FaceButton_Top, EKeys::Gamepad_DPad_Up, EKeys::Gamepad_DPad_Down});
	Button(TEXT("IA_Weapon1"), {EKeys::One, EKeys::NumPadOne, EKeys::Gamepad_DPad_Left});
	Button(TEXT("IA_Weapon2"), {EKeys::Two, EKeys::NumPadTwo, EKeys::Gamepad_DPad_Right});
	Button(TEXT("IA_Melee"), {EKeys::F, EKeys::V, EKeys::MiddleMouseButton, EKeys::Gamepad_RightShoulder, EKeys::Gamepad_RightThumbstick});
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

	In->BindActionValueLambda(Actions[TEXT("IA_Move")], ETriggerEvent::Triggered, [State](const FInputActionValue& V) { if (FMIPlayerInputState* S = State()) S->Move = V.Get<FVector2D>(); });
	In->BindActionValueLambda(Actions[TEXT("IA_Move")], ETriggerEvent::Completed, [State](const FInputActionValue&) { if (FMIPlayerInputState* S = State()) S->Move = FVector2D::ZeroVector; });
	In->BindActionValueLambda(Actions[TEXT("IA_Look")], ETriggerEvent::Triggered, [this, State](const FInputActionValue& V)
	{
		if (FMIPlayerInputState* S = State())
		{
			const FVector2D Counts = V.Get<FVector2D>();
			const double K = MouseDegreesPerCount * Sensitivity;
			// Mouse up is +Y here; the rules look down for +Y.
			S->LookDegrees += FVector2D(Counts.X * K, -Counts.Y * K * (bInvertY ? -1.0 : 1.0));
		}
	});
	const auto Hold = [&In, this, State](const TCHAR* Name, bool FMIPlayerInputState::*Held, bool FMIPlayerInputState::*Pressed)
	{
		UInputAction* Action = Actions[FName(Name)];
		In->BindActionValueLambda(Action, ETriggerEvent::Started, [State, Held, Pressed](const FInputActionValue&)
		{
			if (FMIPlayerInputState* S = State())
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
	Hold(TEXT("IA_Sprint"), &FMIPlayerInputState::bSprint, nullptr);
	Hold(TEXT("IA_Crouch"), &FMIPlayerInputState::bCrouch, nullptr);
	Hold(TEXT("IA_Fire"), &FMIPlayerInputState::bFire, &FMIPlayerInputState::bFirePressed);
	Hold(TEXT("IA_Aim"), &FMIPlayerInputState::bAds, nullptr);
	Hold(TEXT("IA_Reload"), nullptr, &FMIPlayerInputState::bReloadPressed);
	Hold(TEXT("IA_Swap"), nullptr, &FMIPlayerInputState::bSwapPressed);
	Hold(TEXT("IA_Weapon1"), nullptr, &FMIPlayerInputState::bWeapon1Pressed);
	Hold(TEXT("IA_Weapon2"), nullptr, &FMIPlayerInputState::bWeapon2Pressed);
	Hold(TEXT("IA_Melee"), nullptr, &FMIPlayerInputState::bMeleePressed);
}

AMIPlayerCharacter* AMIPlayerController::GetMICharacter() const
{
	return Cast<AMIPlayerCharacter>(GetPawn());
}
