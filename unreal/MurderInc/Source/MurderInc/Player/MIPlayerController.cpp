#include "Player/MIPlayerController.h"

#include "Engine/LocalPlayer.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputAction.h"
#include "InputActionValue.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "MurderInc.h"
#include "Player/MIPlayerCharacter.h"

void AMIPlayerController::BuildInputAssets()
{
	if (MappingContext)
	{
		return;
	}

	const auto MakeAction = [this](const TCHAR* Name, EInputActionValueType Type)
	{
		UInputAction* Action = NewObject<UInputAction>(this, Name);
		Action->ValueType = Type;
		return Action;
	};
	MoveAction = MakeAction(TEXT("IA_Move"), EInputActionValueType::Axis2D);
	LookAction = MakeAction(TEXT("IA_Look"), EInputActionValueType::Axis2D);
	JumpAction = MakeAction(TEXT("IA_Jump"), EInputActionValueType::Boolean);
	SprintAction = MakeAction(TEXT("IA_Sprint"), EInputActionValueType::Boolean);
	CrouchAction = MakeAction(TEXT("IA_Crouch"), EInputActionValueType::Boolean);

	MappingContext = NewObject<UInputMappingContext>(this, TEXT("IMC_Player"));

	// A key gives (1, 0, 0). Swizzle moves that onto Y (forward / back); Negate flips the sign.
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

	// Move: X = right, Y = forward (keys of config.json player.keys; glyphs W A S D).
	Map(MoveAction, EKeys::W, true, false);
	Map(MoveAction, EKeys::S, true, true);
	Map(MoveAction, EKeys::D, false, false);
	Map(MoveAction, EKeys::A, false, true);
	Map(MoveAction, EKeys::Gamepad_Left2D);

	// Look: raw mouse counts, X = right, Y = up. The character turns them into degrees.
	Map(LookAction, EKeys::Mouse2D);

	Map(JumpAction, EKeys::SpaceBar);
	Map(JumpAction, EKeys::Gamepad_FaceButton_Bottom);
	Map(SprintAction, EKeys::LeftShift);
	Map(SprintAction, EKeys::RightShift);
	Map(SprintAction, EKeys::Gamepad_LeftThumbstick);
	Map(CrouchAction, EKeys::C);
	Map(CrouchAction, EKeys::Gamepad_FaceButton_Right);
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

	UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(InputComponent);
	if (!Input)
	{
		UE_LOG(LogMI, Error, TEXT("Input: %s has no Enhanced Input component (check DefaultInputComponentClass in DefaultInput.ini)"), *GetNameSafe(this));
		return;
	}
	Input->BindAction(MoveAction, ETriggerEvent::Triggered, this, &AMIPlayerController::OnMove);
	Input->BindAction(MoveAction, ETriggerEvent::Completed, this, &AMIPlayerController::OnMoveEnded);
	Input->BindAction(MoveAction, ETriggerEvent::Canceled, this, &AMIPlayerController::OnMoveEnded);
	Input->BindAction(LookAction, ETriggerEvent::Triggered, this, &AMIPlayerController::OnLook);
	Input->BindAction(JumpAction, ETriggerEvent::Started, this, &AMIPlayerController::OnJumpPressed);
	Input->BindAction(JumpAction, ETriggerEvent::Completed, this, &AMIPlayerController::OnJumpReleased);
	Input->BindAction(SprintAction, ETriggerEvent::Started, this, &AMIPlayerController::OnSprintPressed);
	Input->BindAction(SprintAction, ETriggerEvent::Completed, this, &AMIPlayerController::OnSprintReleased);
	Input->BindAction(CrouchAction, ETriggerEvent::Started, this, &AMIPlayerController::OnCrouchPressed);
	Input->BindAction(CrouchAction, ETriggerEvent::Completed, this, &AMIPlayerController::OnCrouchReleased);
}

AMIPlayerCharacter* AMIPlayerController::GetMICharacter() const
{
	return Cast<AMIPlayerCharacter>(GetPawn());
}

void AMIPlayerController::OnMove(const FInputActionValue& Value)
{
	if (AMIPlayerCharacter* Character = GetMICharacter())
	{
		Character->SetMoveInput(Value.Get<FVector2D>());
	}
}

void AMIPlayerController::OnMoveEnded(const FInputActionValue& Value)
{
	if (AMIPlayerCharacter* Character = GetMICharacter())
	{
		Character->SetMoveInput(FVector2D::ZeroVector);
	}
}

void AMIPlayerController::OnLook(const FInputActionValue& Value)
{
	if (AMIPlayerCharacter* Character = GetMICharacter())
	{
		Character->AddLookInput(Value.Get<FVector2D>());
	}
}

void AMIPlayerController::OnJumpPressed()
{
	if (AMIPlayerCharacter* Character = GetMICharacter())
	{
		Character->Jump();
	}
}

void AMIPlayerController::OnJumpReleased()
{
	if (AMIPlayerCharacter* Character = GetMICharacter())
	{
		Character->StopJumping();
	}
}

void AMIPlayerController::OnSprintPressed()
{
	if (AMIPlayerCharacter* Character = GetMICharacter())
	{
		Character->SetSprintHeld(true);
	}
}

void AMIPlayerController::OnSprintReleased()
{
	if (AMIPlayerCharacter* Character = GetMICharacter())
	{
		Character->SetSprintHeld(false);
	}
}

void AMIPlayerController::OnCrouchPressed()
{
	if (AMIPlayerCharacter* Character = GetMICharacter())
	{
		Character->SetCrouchHeld(true);
	}
}

void AMIPlayerController::OnCrouchReleased()
{
	if (AMIPlayerCharacter* Character = GetMICharacter())
	{
		Character->SetCrouchHeld(false);
	}
}
