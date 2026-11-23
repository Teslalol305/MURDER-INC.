#include "Flow/MIDemoDirector.h"

#include "Components/CapsuleComponent.h"
#include "Components/SphereComponent.h"
#include "Core/MIEvents.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Enemies/MIEnemies.h"
#include "Enemies/MIEnemyActors.h"
#include "Flow/MIGameRules.h"
#include "Flow/MIGameSubsystem.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CoreDelegates.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "MurderInc.h"
#include "Player/MIPlayerCharacter.h"
#include "Weapons/MICombatSubsystem.h"
#include "Weapons/MIWeaponComponent.h"
#include "Widgets/SViewport.h"
#include "World/MIBoxWorld.h"
#include "World/MIExplosive.h"
#include "World/MILevelData.h"
#include "World/MIObjectiveActors.h"
#include <cstdio>

namespace MIDemoPrivate
{
	double Wrap(double Deg)
	{
		return FRotator::NormalizeAxis(Deg);
	}

	void YawPitchTo(const FVector& From, const FVector& To, double& OutYaw, double& OutPitch)
	{
		const FVector D = To - From;
		OutYaw = FMath::RadiansToDegrees(FMath::Atan2(D.Y, D.X));
		OutPitch = FMath::RadiansToDegrees(FMath::Atan2(D.Z, D.Size2D()));
	}

	UMIDemoDirector* Director(UWorld* World)
	{
		return World ? World->GetSubsystem<UMIDemoDirector>() : nullptr;
	}

#if !UE_BUILD_SHIPPING
	FAutoConsoleCommandWithWorldAndArgs RunCmd(TEXT("MIDemo.Run"),
		TEXT("MIDemo.Run <script>: play a demo script (tools/box/demo/demo.txt) on game time"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			if (UMIDemoDirector* D = Director(World); D && Args.Num() > 0)
			{
				D->RunScript(Args[0]);
			}
		}));
	FAutoConsoleCommandWithWorldAndArgs StopCmd(TEXT("MIDemo.Stop"), TEXT("MIDemo.Stop: stop the script and the capture"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>&, UWorld* World)
		{
			if (UMIDemoDirector* D = Director(World))
			{
				D->Stop();
			}
		}));
	FAutoConsoleCommandWithWorldAndArgs CaptureCmd(TEXT("MIDemo.Capture"),
		TEXT("MIDemo.Capture <fifo or file> | off: every frame of the game viewport as raw BGRA"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			if (UMIDemoDirector* D = Director(World); D && Args.Num() > 0)
			{
				Args[0] == TEXT("off") ? D->StopCapture() : (void)D->StartCapture(Args[0]);
			}
		}));
#endif
}

bool UMIDemoDirector::ShouldCreateSubsystem(UObject* Outer) const
{
#if UE_BUILD_SHIPPING
	return false;
#else
	const UWorld* World = Cast<UWorld>(Outer);
	return World && (World->WorldType == EWorldType::Game || World->WorldType == EWorldType::PIE);
#endif
}

void UMIDemoDirector::Deinitialize()
{
	StopCapture();
	Super::Deinitialize();
}

void UMIDemoDirector::Log(const FString& Text) const
{
	UE_LOG(LogMI, Display, TEXT("MIDemo: frame %lld t %.3f: %s"), Frame, Clock, *Text);
}

AMIPlayerCharacter* UMIDemoDirector::Player() const
{
	UMIGameSubsystem* G = Game();
	return G ? G->GetPlayer() : nullptr;
}

UMIGameSubsystem* UMIDemoDirector::Game() const
{
	return UMIGameSubsystem::Get(GetWorld());
}

void UMIDemoDirector::Console(const FString& Command)
{
	UWorld* World = GetWorld();
	APlayerController* PC = World ? World->GetFirstPlayerController() : nullptr;
	if (PC)
	{
		PC->ConsoleCommand(Command, false);
	}
	else if (GEngine)
	{
		GEngine->Exec(World, *Command);
	}
}

double UMIDemoDirector::Arg(const FAction& A, int32 I, double Default) const
{
	return A.Args.IsValidIndex(I) ? FCString::Atod(*A.Args[I]) : Default;
}

bool UMIDemoDirector::RunScript(const FString& Path)
{
	TArray<FString> Lines;
	if (!FFileHelper::LoadFileToStringArray(Lines, *Path))
	{
		UE_LOG(LogMI, Error, TEXT("MIDemo: cannot read %s"), *Path);
		return false;
	}
	Script.Reset();
	for (int32 I = 0; I < Lines.Num(); ++I)
	{
		FString L = Lines[I];
		int32 Hash;
		if (L.FindChar(TEXT('#'), Hash))
		{
			L.LeftInline(Hash);
		}
		L.TrimStartAndEndInline();
		if (L.IsEmpty())
		{
			continue;
		}
		FAction A;
		A.Line = I + 1;
		A.Raw = L;
		L.ParseIntoArrayWS(A.Args);
		A.Verb = A.Args[0].ToLower();
		A.Args.RemoveAt(0);
		Script.Add(A);
	}
	Index = INDEX_NONE;
	Clock = 0.0;
	Frame = 0;
	bRunning = true;
	bHasView = bWalking = bFighting = bAuto = bLookAtPoint = false;
	YawRate = PitchRate = 0.0;
	if (FMIGameEvents* Bus = UMIEventSubsystem::Get(GetWorld()))
	{
		// Key moments on the frame clock, to line the sound and the voice lines up with the picture.
		Bus->Enemy.AddWeakLambda(this, [this](const FMIEnemyEvent& E)
		{
			if (bRunning && E.Kind == FMIEnemyEvent::EKind::Killed)
			{
				Log(FString::Printf(TEXT("event killed id %d part %s weapon %s by player %d"), E.Id, *E.Part.ToString(), *E.Weapon.ToString(), E.bByPlayer ? 1 : 0));
			}
		});
		Bus->Flow.AddWeakLambda(this, [this](const FMIFlowEvent& E)
		{
			const FString N = E.Name.ToString();
			if (bRunning && !N.StartsWith(TEXT("hud:")))
			{
				Log(FString::Printf(TEXT("event %s %s %.0f %.0f"), *N, *E.Text, E.A, E.B));
			}
		});
		Bus->WeaponReload.AddWeakLambda(this, [this](const FMIReloadEvent& E) { if (bRunning) Log(FString::Printf(TEXT("event reload %s %s"), *E.Weapon.ToString(), *E.Phase.ToString())); });
		Bus->WeaponSwitch.AddWeakLambda(this, [this](const FMISwitchEvent& E) { if (bRunning) Log(FString::Printf(TEXT("event switch %s -> %s %s"), *E.From.ToString(), *E.To.ToString(), *E.Phase.ToString())); });
		Bus->Explosion.AddWeakLambda(this, [this](const FMIExplosionEvent&) { if (bRunning) Log(TEXT("event explosion")); });
	}
	UE_LOG(LogMI, Display, TEXT("MIDemo: %d actions from %s"), Script.Num(), *Path);
	return true;
}

void UMIDemoDirector::Stop()
{
	bRunning = false;
	ReleaseTrigger();
	StopCapture();
	if (AMIPlayerCharacter* P = Player())
	{
		P->GetInput().Move = FVector2D::ZeroVector;
	}
	Log(TEXT("stopped"));
}

bool UMIDemoDirector::StartCapture(const FString& Path)
{
	StopCapture();
	Pipe = fopen(TCHAR_TO_UTF8(*Path), "wb");
	if (!Pipe)
	{
		UE_LOG(LogMI, Error, TEXT("MIDemo: cannot open %s for the capture"), *Path);
		return false;
	}
	PipePath = Path;
	Captured = 0;
	CaptureSize = FIntPoint::ZeroValue;
	EndFrameHandle = FCoreDelegates::OnEndFrame.AddUObject(this, &UMIDemoDirector::OnEndFrame);
	Log(FString::Printf(TEXT("capture to %s"), *Path));
	return true;
}

void UMIDemoDirector::StopCapture()
{
	if (EndFrameHandle.IsValid())
	{
		FCoreDelegates::OnEndFrame.Remove(EndFrameHandle);
		EndFrameHandle.Reset();
	}
	if (Pipe)
	{
		fclose(Pipe);
		Pipe = nullptr;
		UE_LOG(LogMI, Display, TEXT("MIDemo: capture closed, %lld frames of %d x %d to %s"), Captured, CaptureSize.X, CaptureSize.Y, *PipePath);
	}
}

void UMIDemoDirector::OnEndFrame()
{
	UWorld* World = GetWorld();
	UGameViewportClient* Client = World ? World->GetGameViewport() : nullptr;
	TSharedPtr<SViewport> Widget = Client ? Client->GetGameViewportWidget() : nullptr;
	if (!Pipe || !Widget.IsValid() || !FSlateApplication::IsInitialized())
	{
		return;
	}
	TArray<FColor> Pixels;
	FIntVector Size;
	if (!FSlateApplication::Get().TakeScreenshot(Widget.ToSharedRef(), Pixels, Size) || Pixels.Num() == 0)
	{
		UE_LOG(LogMI, Warning, TEXT("MIDemo: frame %lld not read back"), Captured);
		return;
	}
	if (CaptureSize == FIntPoint::ZeroValue)
	{
		CaptureSize = FIntPoint(Size.X, Size.Y);
		UE_LOG(LogMI, Display, TEXT("MIDemo: capture size %d x %d"), Size.X, Size.Y);
	}
	if (Size.X != CaptureSize.X || Size.Y != CaptureSize.Y)
	{
		UE_LOG(LogMI, Warning, TEXT("MIDemo: frame %lld is %d x %d, not %d x %d: skipped"), Captured, Size.X, Size.Y, CaptureSize.X, CaptureSize.Y);
		return;
	}
	fwrite(Pixels.GetData(), sizeof(FColor), Pixels.Num(), Pipe);
	++Captured;
	if (Captured % 600 == 0)
	{
		Log(FString::Printf(TEXT("captured %lld frames"), Captured));
	}
}

void UMIDemoDirector::ReleaseTrigger()
{
	if (AMIPlayerCharacter* P = Player())
	{
		P->GetInput().bFire = false;
	}
	bTriggerDown = false;
	Burst = 0.0;
}

void UMIDemoDirector::Tick(float DeltaTime)
{
	if (!bRunning)
	{
		return;
	}
	const float Dt = DeltaTime;
	Clock += Dt;
	++Frame;
	AMIPlayerCharacter* P = Player();
	if (bGod && P)
	{
		P->GetPlayerRules().bInvulnerable = true;
		P->GetPlayerRules().Health = P->GetPlayerRules().MaxHealth;
	}
	bool bNext = Index == INDEX_NONE ? true : Step(Dt);
	for (int32 Guard = 0; bNext && Guard < 256; ++Guard)
	{
		++Index;
		ActionTime = 0.0;
		if (Index >= Script.Num())
		{
			Log(TEXT("script done"));
			bRunning = false;
			ReleaseTrigger();
			if (P)
			{
				P->GetInput().Move = FVector2D::ZeroVector;
			}
			return;
		}
		Log(FString::Printf(TEXT("line %d: %s"), Script[Index].Line, *Script[Index].Raw));
		bNext = Begin(Script[Index]);
	}
	if (!P)
	{
		return;
	}
	const bool bFightNow = bFighting || bAuto;
	const bool bEngaged = bFightNow && Fight(Dt);
	if (!bEngaged && bFightNow)
	{
		P->GetInput().bAds = false;
	}
	if (bHunting && !bEngaged)
	{
		Hunt(Dt);
	}
	if (bWalking && !bEngaged)
	{
		Move(Dt);
	}
	else
	{
		P->GetInput().Move = FVector2D::ZeroVector;
		P->GetInput().bSprint = false;
	}
	SteerView(Dt);
}

bool UMIDemoDirector::Begin(const FAction& A)
{
	using namespace MIDemoPrivate;
	const FString& V = A.Verb;
	AMIPlayerCharacter* P = Player();
	UMIGameSubsystem* G = Game();
	ActionLimit = 0.0;
	if (V == TEXT("con"))
	{
		FString Cmd = A.Raw.Mid(3).TrimStart();
		Console(Cmd);
		return true;
	}
	if (V == TEXT("wait"))
	{
		ActionLimit = Arg(A, 0, 1.0);
		return false;
	}
	if (V == TEXT("capture"))
	{
		if (A.Args.Num() > 0 && A.Args[0] != TEXT("off"))
		{
			StartCapture(A.Args[0]);
		}
		else
		{
			StopCapture();
		}
		return true;
	}
	if (V == TEXT("god"))
	{
		bGod = Arg(A, 0, 1.0) != 0.0;
		return true;
	}
	if (V == TEXT("spring"))
	{
		SpringHz = Arg(A, 0, SpringHz);
		MaxRate = Arg(A, 1, MaxRate);
		return true;
	}
	if (V == TEXT("auto"))
	{
		bAuto = Arg(A, 0, 1.0) != 0.0;
		bHead = Arg(A, 1, 1.0) != 0.0;
		CalmEnd = 2.5;
		if (!bAuto)
		{
			ReleaseTrigger();
		}
		return true;
	}
	if (V == TEXT("face"))
	{
		// face path [pitch] | face angles <yaw> <pitch> | face point <x> <y> <z>
		const FString M = A.Args.Num() > 0 ? A.Args[0].ToLower() : TEXT("path");
		bHasView = true;
		bLookAtPoint = false;
		if (M == TEXT("angles"))
		{
			WantYaw = Arg(A, 1, 0.0);
			WantPitch = Arg(A, 2, 0.0);
			WalkPitch = WantPitch;
			bWalkFacesPath = false;
		}
		else if (M == TEXT("point"))
		{
			bLookAtPoint = true;
			LookPoint = FVector(Arg(A, 1, 0.0), Arg(A, 2, 0.0), Arg(A, 3, 160.0));
			bWalkFacesPath = false;
		}
		else
		{
			WalkPitch = Arg(A, 1, WalkPitch);
			bWalkFacesPath = true;
			if (P)
			{
				WantYaw = P->GetPlayerRules().Yaw;
				WantPitch = WalkPitch;
			}
		}
		return true;
	}
	if (V == TEXT("look") || V == TEXT("lookat"))
	{
		bHasView = true;
		bWalkFacesPath = false;
		if (V == TEXT("look"))
		{
			bLookAtPoint = false;
			WantYaw = Arg(A, 0, 0.0);
			WantPitch = Arg(A, 1, 0.0);
			ActionLimit = Arg(A, 2, 3.0);
		}
		else
		{
			bLookAtPoint = true;
			LookPoint = FVector(Arg(A, 0, 0.0), Arg(A, 1, 0.0), Arg(A, 2, 160.0));
			ActionLimit = Arg(A, 3, 3.0);
		}
		return false;
	}
	if (V == TEXT("walk"))
	{
		// walk <x> <y> [sprint 0|1] [arrive cm] [limit s]
		WalkTo = FVector2D(Arg(A, 0, 0.0), Arg(A, 1, 0.0));
		bSprint = Arg(A, 2, 0.0) != 0.0;
		Arrive = Arg(A, 3, 60.0);
		ActionLimit = Arg(A, 4, 40.0);
		bWalking = true;
		return false;
	}
	if (V == TEXT("route"))
	{
		// route <sprint 0|1> <x1> <y1> <x2> <y2> ...: one smooth walk along the polyline (from where the player is)
		bSprint = Arg(A, 0, 0.0) != 0.0;
		Route.Reset();
		if (P)
		{
			Route.Add(FVector2D(P->GetActorLocation().X, P->GetActorLocation().Y));
		}
		for (int32 I = 1; I + 1 < A.Args.Num(); I += 2)
		{
			Route.Add(FVector2D(Arg(A, I, 0.0), Arg(A, I + 1, 0.0)));
		}
		RouteSeg = 0;
		WalkTo = Route.Last();
		Arrive = 70.0;
		ActionLimit = 60.0;
		bWalking = Route.Num() >= 2;
		return !bWalking;
	}
	if (V == TEXT("stopwalk"))
	{
		bWalking = false;
		return true;
	}
	if (V == TEXT("fight"))
	{
		// fight <limit s> [kills N] [head 0|1] [calm s]
		ActionLimit = Arg(A, 0, 20.0);
		KillsWanted = (int32)Arg(A, 1, 0.0);
		bHead = Arg(A, 2, 1.0) != 0.0;
		CalmEnd = Arg(A, 3, 2.5);
		KillsAtStart = G ? G->GetStats().Kills : 0;
		Calm = 0.0;
		bFighting = true;
		return false;
	}
	if (V == TEXT("hunt"))
	{
		// hunt <limit s> [kills] [head 0|1]: fight what is in sight; with nothing in sight walk the nav path toward
		// the nearest living enemy (replanned every 1.5 s)
		ActionLimit = Arg(A, 0, 20.0);
		KillsWanted = (int32)Arg(A, 1, 1.0);
		bHead = Arg(A, 2, 1.0) != 0.0;
		CalmEnd = 1e9;
		KillsAtStart = G ? G->GetStats().Kills : 0;
		bFighting = true;
		bHunting = true;
		ReplanIn = 0.0;
		return false;
	}
	if (V == TEXT("goto"))
	{
		// goto <x> <y> [sprint 0|1]: one route along the nav path from where the player stands
		bSprint = Arg(A, 2, 0.0) != 0.0;
		Route.Reset();
		TArray<FVector> Path;
		const FVector Goal = MI::Web::FromUnreal(FVector(Arg(A, 0, 0.0), Arg(A, 1, 0.0), 0.0));
		if (P && G && G->GetBoxWorld().FindPath(G->PlayerFeetWeb(), Goal, Path) && Path.Num() >= 1)
		{
			Route.Add(FVector2D(P->GetActorLocation().X, P->GetActorLocation().Y));
			for (int32 I = 1; I < Path.Num(); ++I)
			{
				const FVector U = MI::Web::ToUnreal(Path[I]);
				Route.Add(FVector2D(U.X, U.Y));
			}
			Route.Add(FVector2D(Arg(A, 0, 0.0), Arg(A, 1, 0.0)));
		}
		Log(FString::Printf(TEXT("goto: %d points"), Route.Num()));
		RouteSeg = 0;
		WalkTo = Route.Num() ? Route.Last() : FVector2D::ZeroVector;
		Arrive = 70.0;
		ActionLimit = 40.0;
		bWalking = Route.Num() >= 2;
		bWalkFacesPath = true;
		return !bWalking;
	}
	if (V == TEXT("alert"))
	{
		// alert <radius m>: every enemy within the radius comes to look (the rules' own alert)
		if (G)
		{
			G->GetEnemies().Alert(G->PlayerFeetWeb(), Arg(A, 0, 40.0));
		}
		return true;
	}
	if (V == TEXT("hide"))
	{
		// hide <label part> ...: hides in game every actor whose editor label (or name) contains one of the parts
		// (a part "a*b" needs every piece)
		int32 N = 0;
		for (TActorIterator<AActor> It(GetWorld()); It; ++It)
		{
#if WITH_EDITOR
			const FString Label = It->GetActorLabel();
#else
			const FString Label = It->GetName();
#endif
			for (const FString& Part : A.Args)
			{
				// "a*b": the label holds every piece
				TArray<FString> Pieces;
				Part.ParseIntoArray(Pieces, TEXT("*"));
				bool bAll = Pieces.Num() > 0;
				for (const FString& Piece : Pieces)
				{
					bAll &= Label.Contains(Piece);
				}
				if (bAll)
				{
					It->SetActorHiddenInGame(true);
					++N;
					break;
				}
			}
		}
		Log(FString::Printf(TEXT("hid %d actors"), N));
		return true;
	}
	if (V == TEXT("blow"))
	{
		// blow [limit s]: the nearest live explosive in front, shot until it goes
		ActionLimit = Arg(A, 0, 6.0);
		Blow.Reset();
		double Best = 1e30;
		if (P)
		{
			for (TActorIterator<AMIExplosive> It(GetWorld()); It; ++It)
			{
				const FVector To = It->GetActorLocation() - P->GetPlayerRules().Eye;
				const double Front = FVector::DotProduct(To.GetSafeNormal2D(), P->GetPlayerRules().Forward.GetSafeNormal2D());
				if (It->IsMIDamageableAlive() && Front > 0.5 && To.Size() < 3000.0 && To.Size() < Best)
				{
					Blow = *It;
					Best = To.Size();
				}
			}
		}
		Log(Blow.IsValid() ? FString::Printf(TEXT("blow %s at %.1f m"), *Blow->GetName(), Best / 100.0) : FString(TEXT("blow: no explosive in front")));
		return !Blow.IsValid();
	}
	if (V == TEXT("grab"))
	{
		ActionLimit = Arg(A, 0, 6.0);
		ReelsAtStart = G ? G->GetRules().GetRun().Reels : 0;
		if (G)
		{
			G->SetInteractHeld(true);
		}
		return false;
	}
	if (V == TEXT("secure"))
	{
		if (G)
		{
			G->GetRules().DevSecureQuietly((int32)Arg(A, 0, 0.0));
		}
		return true;
	}
	if (V == TEXT("waitstate"))
	{
		ActionLimit = Arg(A, 1, 60.0);
		return false;
	}
	if (V == TEXT("quit"))
	{
		Stop();
		Console(TEXT("quit"));
		return true;
	}
	UE_LOG(LogMI, Warning, TEXT("MIDemo: line %d: unknown action '%s'"), A.Line, *V);
	return true;
}

bool UMIDemoDirector::Step(float Dt)
{
	using namespace MIDemoPrivate;
	ActionTime += Dt;
	const FAction& A = Script[Index];
	const FString& V = A.Verb;
	AMIPlayerCharacter* P = Player();
	UMIGameSubsystem* G = Game();
	const bool bTimedOut = ActionLimit > 0.0 && ActionTime >= ActionLimit;
	if (V == TEXT("wait"))
	{
		return bTimedOut;
	}
	if (V == TEXT("look") || V == TEXT("lookat"))
	{
		if (!P)
		{
			return true;
		}
		double Yaw = WantYaw, Pitch = WantPitch;
		if (bLookAtPoint)
		{
			YawPitchTo(P->GetPlayerRules().Eye, LookPoint, Yaw, Pitch);
		}
		const double Err = FMath::Abs(Wrap(Yaw - P->GetPlayerRules().Yaw)) + FMath::Abs(Pitch - P->GetPlayerRules().Pitch);
		return bTimedOut || (Err < 0.5 && FMath::Abs(YawRate) < 5.0);
	}
	if (V == TEXT("walk") || V == TEXT("route") || V == TEXT("goto"))
	{
		if (!P)
		{
			return true;
		}
		const FVector2D Feet(P->GetActorLocation().X, P->GetActorLocation().Y);
		const bool bThere = FVector2D::Distance(Feet, WalkTo) < Arrive;
		if (bThere || bTimedOut)
		{
			if (bTimedOut && !bThere)
			{
				Log(FString::Printf(TEXT("walk timed out %.0f cm short"), FVector2D::Distance(Feet, WalkTo)));
			}
			bWalking = false;
			Route.Reset();
			P->GetInput().Move = FVector2D::ZeroVector;
			P->GetInput().bSprint = false;
			return true;
		}
		return false;
	}
	if (V == TEXT("hunt"))
	{
		const int32 Kills = G ? G->GetStats().Kills - KillsAtStart : 0;
		const bool bAlive = G && G->GetEnemies().AliveCount() > 0;
		const bool bDone = bTimedOut || (Kills >= KillsWanted && AfterKill <= -0.2) || (!bAlive && AfterKill <= -0.2);
		if (bDone)
		{
			Log(FString::Printf(TEXT("hunt done: %d kills, %s"), Kills, bTimedOut ? TEXT("time") : TEXT("kills")));
			bFighting = bHunting = bWalking = false;
			Route.Reset();
			Target = INDEX_NONE;
			ReleaseTrigger();
			if (P)
			{
				P->GetInput().bAds = false;
				P->GetInput().Move = FVector2D::ZeroVector;
			}
		}
		return bDone;
	}
	if (V == TEXT("fight"))
	{
		const int32 Kills = G ? G->GetStats().Kills - KillsAtStart : 0;
		const bool bDone = bTimedOut || (KillsWanted > 0 && Kills >= KillsWanted && AfterKill <= 0.0) || (Calm >= CalmEnd && ActionTime > 0.5);
		if (bDone)
		{
			Log(FString::Printf(TEXT("fight done: %d kills, %s"), Kills, bTimedOut ? TEXT("time") : Calm >= CalmEnd ? TEXT("calm") : TEXT("kills")));
			bFighting = false;
			Target = INDEX_NONE;
			ReleaseTrigger();
			if (P)
			{
				P->GetInput().bAds = false;
			}
		}
		return bDone;
	}
	if (V == TEXT("blow"))
	{
		AActor* X = Blow.Get();
		const bool bGone = !X || !Cast<AMIExplosive>(X)->IsMIDamageableAlive();
		if (P && X && !bGone)
		{
			bHasView = true;
			bLookAtPoint = true;
			LookPoint = X->GetActorLocation() + FVector(0, 0, 45.0);
			double Yaw, Pitch;
			YawPitchTo(P->GetPlayerRules().Eye, LookPoint, Yaw, Pitch);
			const double Err = FMath::Abs(Wrap(Yaw - P->GetPlayerRules().Yaw)) + FMath::Abs(Pitch - P->GetPlayerRules().Pitch);
			P->GetInput().bAds = Err < 25.0;
			// On target: one round, and the tank takes it as lethal (MIBlowNearest): a hit that only lights the
			// tank was not needed here, and the take's first try crashed on the frame after one.
			const bool bShoot = Err < 1.5 && P->GetPlayerRules().Ads > 0.6 && ActionTime > 0.5;
			P->GetInput().bFire = bShoot;
			if (bShoot)
			{
				P->GetInput().bFirePressed = true;
				Console(TEXT("MIBlowNearest"));
			}
		}
		if (bGone || bTimedOut)
		{
			Log(bGone ? TEXT("blow: it went") : TEXT("blow timed out"));
			ReleaseTrigger();
			if (P)
			{
				P->GetInput().bAds = false;
			}
			return true;
		}
		return false;
	}
	if (V == TEXT("grab"))
	{
		const bool bGot = G && G->GetRules().GetRun().Reels > ReelsAtStart;
		if (bGot || bTimedOut)
		{
			if (G)
			{
				G->SetInteractHeld(false);
			}
			Log(bGot ? TEXT("grab: reel taken") : TEXT("grab timed out"));
			return true;
		}
		return false;
	}
	if (V == TEXT("waitstate"))
	{
		static const TCHAR* Names[] = {TEXT("title"), TEXT("intro"), TEXT("playing"), TEXT("paused"), TEXT("dead"), TEXT("complete")};
		const int32 S = G ? (int32)G->GetRules().GetState() : 0;
		return bTimedOut || (A.Args.Num() > 0 && S < 6 && A.Args[0].ToLower() == Names[S]);
	}
	return true;
}

void UMIDemoDirector::SteerView(float Dt)
{
	using namespace MIDemoPrivate;
	AMIPlayerCharacter* P = Player();
	if (!P || !bHasView)
	{
		return;
	}
	FMIPlayerRules& R = P->GetPlayerRules();
	double Yaw = WantYaw, Pitch = WantPitch;
	if (bLookAtPoint || bFightLook)
	{
		YawPitchTo(R.Eye, bFightLook ? FightPoint : LookPoint, Yaw, Pitch);
	}
	const double Hz = bFightLook ? FightHz : SpringHz;
	const double W = 2.0 * UE_DOUBLE_PI * Hz;
	const double EY = Wrap(Yaw - R.Yaw);
	const double EP = Pitch - R.Pitch;
	YawRate += (W * W * EY - 2.0 * W * YawRate) * Dt;
	PitchRate += (W * W * EP - 2.0 * W * PitchRate) * Dt;
	YawRate = FMath::Clamp(YawRate, -MaxRate, MaxRate);
	PitchRate = FMath::Clamp(PitchRate, -MaxRate, MaxRate);
	R.Yaw = Wrap(R.Yaw + YawRate * Dt);
	R.Pitch = FMath::Clamp(R.Pitch + PitchRate * Dt, -80.0, 80.0);
}

void UMIDemoDirector::Move(float Dt)
{
	using namespace MIDemoPrivate;
	AMIPlayerCharacter* P = Player();
	if (!P)
	{
		return;
	}
	FMIPlayerRules& R = P->GetPlayerRules();
	const FVector2D Feet(P->GetActorLocation().X, P->GetActorLocation().Y);
	FVector2D Goal = WalkTo, Sight = WalkTo;
	if (Route.Num() >= 2)
	{
		AdvanceRoute(Feet);
		Goal = RoutePoint(Ahead);
		Sight = RoutePoint(Ahead * 2.2);
	}
	const FVector2D D = Goal - Feet;
	const double Dist = FVector2D::Distance(WalkTo, Feet);
	const FVector2D DS = Sight - Feet;
	const double PathYaw = FMath::RadiansToDegrees(FMath::Atan2(D.Y, D.X));
	const double SightYaw = DS.Size() > 30.0 ? FMath::RadiansToDegrees(FMath::Atan2(DS.Y, DS.X)) : PathYaw;
	if (bWalkFacesPath && !bFightLook)
	{
		bHasView = true;
		bLookAtPoint = false;
		WantYaw = SightYaw;
		WantPitch = WalkPitch;
	}
	const double Rel = FMath::DegreesToRadians(Wrap(PathYaw - R.Yaw));
	const double Mag = FMath::Clamp(Dist / 160.0, 0.3, 1.0);
	FMIPlayerInputState& In = P->GetInput();
	In.Move = FVector2D(FMath::Sin(Rel), FMath::Cos(Rel)) * Mag;
	In.bSprint = bSprint && FMath::Cos(Rel) > 0.85 && Dist > 250.0;
}

void UMIDemoDirector::Hunt(float Dt)
{
	UMIGameSubsystem* G = Game();
	AMIPlayerCharacter* P = Player();
	ReplanIn -= Dt;
	if (!G || !P || ReplanIn > 0.0)
	{
		return;
	}
	ReplanIn = 1.5;
	const FVector Me = G->PlayerFeetWeb();
	const TArray<FMIEnemy>& Slots = G->GetEnemies().GetSlots();
	const FMIEnemy* Near = nullptr;
	for (const FMIEnemy& E : Slots)
	{
		if (E.bAlive && E.Type == MIEnemy::EType::Goon && (!Near || FVector::Dist(E.Pos, Me) < FVector::Dist(Near->Pos, Me)))
		{
			Near = &E;
		}
	}
	TArray<FVector> Path;
	if (!Near || FVector::Dist2D(FVector(Near->Pos.X, Near->Pos.Z, 0), FVector(Me.X, Me.Z, 0)) < 6.0
		|| !G->GetBoxWorld().FindPath(Me, Near->Pos, Path) || Path.Num() < 2)
	{
		bWalking = false;
		Route.Reset();
		return;
	}
	Route.Reset();
	Route.Add(FVector2D(P->GetActorLocation().X, P->GetActorLocation().Y));
	for (int32 I = 1; I < Path.Num(); ++I)
	{
		const FVector U = MI::Web::ToUnreal(Path[I]);
		Route.Add(FVector2D(U.X, U.Y));
	}
	// Stop about 7 m short of the enemy: walk the route, not into him.
	double Keep = 700.0;
	while (Route.Num() >= 2 && Keep > 0.0)
	{
		const double L = FVector2D::Distance(Route.Last(), Route[Route.Num() - 2]);
		if (L > Keep)
		{
			Route.Last() = Route.Last() + (Route[Route.Num() - 2] - Route.Last()) * (Keep / L);
			break;
		}
		Keep -= L;
		Route.Pop();
	}
	if (Route.Num() < 2)
	{
		bWalking = false;
		Route.Reset();
		return;
	}
	RouteSeg = 0;
	WalkTo = Route.Last();
	bSprint = false;
	bWalking = true;
	bWalkFacesPath = true;
}

void UMIDemoDirector::AdvanceRoute(const FVector2D& Feet)
{
	// Move on to the next segment once the feet are past the end of this one (or nearer the next).
	while (RouteSeg + 1 < Route.Num() - 1)
	{
		const FVector2D A = Route[RouteSeg], B = Route[RouteSeg + 1];
		const FVector2D AB = B - A;
		const double T = FVector2D::DotProduct(Feet - A, AB) / FMath::Max(1.0, AB.SizeSquared());
		if (T >= 1.0 || FVector2D::Distance(Feet, B) < Ahead * 0.5)
		{
			++RouteSeg;
		}
		else
		{
			break;
		}
	}
}

FVector2D UMIDemoDirector::RoutePoint(double Further) const
{
	// The point Further cm along the route from the feet's projection on the current segment.
	const FVector2D A = Route[RouteSeg], B = Route[RouteSeg + 1];
	const FVector2D AB = B - A;
	const double Len = FMath::Max(1.0, AB.Size());
	double T = 0.0;
	if (const AMIPlayerCharacter* P = Player())
	{
		const FVector2D Feet(P->GetActorLocation().X, P->GetActorLocation().Y);
		T = FMath::Clamp(FVector2D::DotProduct(Feet - A, AB) / (Len * Len), 0.0, 1.0);
	}
	double Left = Further + (1.0 - T) * 0.0;
	FVector2D At = A + AB * T;
	int32 Seg = RouteSeg;
	while (true)
	{
		const FVector2D End = Route[Seg + 1];
		const double D = FVector2D::Distance(At, End);
		if (D >= Left || Seg + 2 >= Route.Num())
		{
			return D >= Left ? At + (End - At) / FMath::Max(D, 1e-3) * Left : End;
		}
		Left -= D;
		At = End;
		++Seg;
	}
}

FVector UMIDemoDirector::AimPoint(int32 Slot, bool bHeadShot) const
{
	UMIGameSubsystem* G = Game();
	AActor* A = G ? G->GetEnemyActor(Slot) : nullptr;
	if (const AMIGoon* Goon = Cast<AMIGoon>(A))
	{
		return bHeadShot ? Goon->GetHeadHit()->GetComponentLocation() : Goon->GetBodyHit()->GetComponentLocation() + FVector(0, 0, 20.0);
	}
	return A ? A->GetActorLocation() : FVector::ZeroVector;
}

bool UMIDemoDirector::Sees(int32 Slot, bool bHeadShot) const
{
	UMIGameSubsystem* G = Game();
	AMIPlayerCharacter* P = Player();
	AActor* A = G ? G->GetEnemyActor(Slot) : nullptr;
	if (!A || !P)
	{
		return false;
	}
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(MIDemoSight), false, P);
	return GetWorld()->LineTraceSingleByChannel(Hit, P->GetPlayerRules().Eye, AimPoint(Slot, bHeadShot), MIBulletChannel, Params) && Hit.GetActor() == A;
}

int32 UMIDemoDirector::PickTarget() const
{
	using namespace MIDemoPrivate;
	UMIGameSubsystem* G = Game();
	AMIPlayerCharacter* P = Player();
	if (!G || !P)
	{
		return INDEX_NONE;
	}
	const TArray<FMIEnemy>& Slots = G->GetEnemies().GetSlots();
	const FMIPlayerRules& R = P->GetPlayerRules();
	int32 Best = INDEX_NONE;
	double BestScore = 1e30;
	for (int32 I = 0; I < Slots.Num(); ++I)
	{
		if (!Slots[I].bAlive || !G->GetEnemyActor(I) || !Sees(I, false))
		{
			continue;
		}
		const FVector At = AimPoint(I, false);
		const double D = FVector::Dist(R.Eye, At);
		if (D > MaxRange)
		{
			continue;
		}
		double Yaw, Pitch;
		YawPitchTo(R.Eye, At, Yaw, Pitch);
		const double Off = FMath::Abs(Wrap(Yaw - R.Yaw));
		const double Score = D + Off * 25.0;
		if (Score < BestScore)
		{
			Best = I;
			BestScore = Score;
		}
	}
	return Best;
}

bool UMIDemoDirector::Fight(float Dt)
{
	using namespace MIDemoPrivate;
	UMIGameSubsystem* G = Game();
	AMIPlayerCharacter* P = Player();
	if (!G || !P || G->GetRules().GetState() != EMIGameState::Playing)
	{
		bFightLook = false;
		return false;
	}
	const TArray<FMIEnemy>& Slots = G->GetEnemies().GetSlots();
	const int32 Kills = G->GetStats().Kills;
	if (Kills != LastKills)
	{
		LastKills = Kills;
		AfterKill = 0.45;
		Target = INDEX_NONE;
		ReleaseTrigger();
	}
	AfterKill -= Dt;
	if (Target != INDEX_NONE && (!Slots.IsValidIndex(Target) || !Slots[Target].bAlive || !Sees(Target, false)))
	{
		Target = INDEX_NONE;
	}
	if (Target == INDEX_NONE && AfterKill <= 0.0)
	{
		Target = PickTarget();
		TargetTime = 0.0;
		Burst = BurstRest = 0.0;
		if (Target != INDEX_NONE)
		{
			Log(FString::Printf(TEXT("target slot %d at %.1f m"), Target, FVector::Dist(P->GetPlayerRules().Eye, AimPoint(Target, false)) / 100.0));
		}
	}
	FMIPlayerInputState& In = P->GetInput();
	if (Target == INDEX_NONE)
	{
		ReleaseTrigger();
		Calm += Dt;
		// Hold the last aim a moment after a kill, then hand the view back.
		if (AfterKill <= -0.4)
		{
			bFightLook = false;
		}
		return AfterKill > -0.4 && bFightLook;
	}
	Calm = 0.0;
	TargetTime += Dt;
	const bool bHeadShot = bHead && TargetTime < 2.2 && Sees(Target, true);
	FightPoint = AimPoint(Target, bHeadShot);
	bFightLook = true;
	bHasView = true;
	const FMIPlayerRules& R = P->GetPlayerRules();
	double Yaw, Pitch;
	YawPitchTo(R.Eye, FightPoint, Yaw, Pitch);
	const double Err = FMath::Sqrt(FMath::Square(Wrap(Yaw - R.Yaw)) + FMath::Square(Pitch - R.Pitch));
	In.bAds = Err < 25.0;
	const UMIWeaponComponent* Weapon = P->GetWeapon();
	if (Weapon && Weapon->GetRules().GetMag() == 0)
	{
		ReleaseTrigger();
		if (Weapon->GetRules().GetReserve() > 0.0)
		{
			In.bReloadPressed = true;
		}
		return true;
	}
	const double Dist = FMath::Max(100.0, FVector::Dist(R.Eye, FightPoint));
	const double Tol = FMath::RadiansToDegrees(FMath::Atan((bHeadShot ? 9.0 : 18.0) / Dist));
	const bool bOn = Err < FMath::Max(Tol, 0.25) && R.Ads > 0.75;
	if (BurstRest > 0.0)
	{
		BurstRest -= Dt;
		In.bFire = false;
		bTriggerDown = false;
		return true;
	}
	if (bOn)
	{
		if (!bTriggerDown || (FireFrames % 9) == 0)
		{
			In.bFirePressed = true;
		}
		++FireFrames;
		In.bFire = true;
		bTriggerDown = true;
		Burst += Dt;
		if (Burst > 0.3)
		{
			Burst = 0.0;
			BurstRest = 0.22;
		}
	}
	else
	{
		In.bFire = false;
		bTriggerDown = false;
	}
	return true;
}
