// The death pass's probe (docs/unreal/PLAY.md, death lane): a development console command that kills Goons the way a
// player's round or a blast does (through IMIDamageable, the same path as the weapon) and measures what the deaths cost
// in the frames that follow. Not in the Shipping game.
//
//   MI.Goon.Kill <count> [body|head|blast] [max metres] [delay s]
//       kills the <count> nearest living Goons within the distance (0: any distance), each by one round from the
//       player's eye at its body or head point (or one blast beside it on the player's side), after the delay (default
//       1 s, 0: on the next frame), then logs, for the delay before and the 3 s after, the frame time, the game thread's time and the worst of each, the ragdoll start
//       time of each body and how many bodies were frozen at the end.

#include "CoreMinimal.h"

#if !UE_BUILD_SHIPPING

#include "Components/CapsuleComponent.h"
#include "Components/SphereComponent.h"
#include "Containers/Ticker.h"
#include "Core/MIDamageable.h"
#include "Core/MIEvents.h"
#include "Engine/World.h"
#include "Enemies/MIEnemies.h"
#include "Enemies/MIEnemyActors.h"
#include "Flow/MIGameSubsystem.h"
#include "HAL/IConsoleManager.h"
#include "Misc/App.h"
#include "MurderInc.h"
#include "Player/MIPlayerCharacter.h"
#include "RenderCore.h"
#include "Weapons/MIEffects.h"

namespace MIDeathProbePrivate
{
	struct FFrames
	{
		TArray<double> Frame, Game;
		void Add() { Frame.Add(FApp::GetDeltaTime() * 1000.0); Game.Add(FPlatformTime::ToMilliseconds(GGameThreadTime)); }
		static double Mean(const TArray<double>& A) { double S = 0; for (double V : A) S += V; return A.Num() ? S / A.Num() : 0.0; }
		static double Max(const TArray<double>& A) { double M = 0; for (double V : A) M = FMath::Max(M, V); return M; }
		FString Line() const
		{
			return FString::Printf(TEXT("%d frames, frame mean %.2f ms worst %.2f ms, game thread mean %.2f ms worst %.2f ms"),
				Frame.Num(), Mean(Frame), Max(Frame), Mean(Game), Max(Game));
		}
	};

	struct FProbe
	{
		TWeakObjectPtr<UWorld> World;
		TArray<TWeakObjectPtr<AMIGoon>> Killed;
		FFrames Before, After;
		double Clock = 0.0;
		int32 Count = 1;
		FName Part = TEXT("body");
		double MaxMetres = 0.0, Delay = 1.0;
		bool bFired = false;
		FTSTicker::FDelegateHandle Handle;
	};

	TSharedPtr<FProbe> Active;

	void Kill(FProbe& P)
	{
		UWorld* World = P.World.Get();
		UMIGameSubsystem* G = UMIGameSubsystem::Get(World);
		AMIPlayerCharacter* Me = G ? G->GetPlayer() : nullptr;
		if (!G || !Me)
		{
			return;
		}
		const FVector Eye = Me->GetPlayerRules().Eye;
		TArray<TPair<double, AMIGoon*>> Live;
		const TArray<FMIEnemy>& Slots = G->GetEnemies().GetSlots();
		for (int32 I = 0; I < Slots.Num(); ++I)
		{
			AMIGoon* Goon = Cast<AMIGoon>(G->GetEnemyActor(I));
			if (Goon && Slots[I].bAlive && Goon->IsMIDamageableAlive())
			{
				const double D = FVector::Dist(Goon->GetActorLocation(), Eye);
				if (P.MaxMetres <= 0.0 || D <= P.MaxMetres * 100.0)
				{
					Live.Add({D, Goon});
				}
			}
		}
		Live.Sort([](const TPair<double, AMIGoon*>& A, const TPair<double, AMIGoon*>& B) { return A.Key < B.Key; });
		FMIGameEvents* Events = UMIEventSubsystem::Get(World);
		for (int32 I = 0; I < Live.Num() && I < P.Count; ++I)
		{
			AMIGoon* Goon = Live[I].Value;
			FMIDamage D;
			D.Amount = 100000.0;
			D.Source = EMIDamageSource::Player;
			D.Instigator = Me;
			if (P.Part == TEXT("blast"))
			{
				const FVector Target = Goon->GetMIBlastTarget();
				const FVector Side = (Eye - Target).GetSafeNormal2D();
				const FVector Centre = Target + Side * 220.0 - FVector(0, 0, 70.0);
				D.Kind = EMIDamageKind::Blast;
				D.Source = EMIDamageSource::Blast;
				D.From = Centre;
				D.Point = Target;
				D.Direction = (Target - Centre).GetSafeNormal();
				D.Weapon = TEXT("blast");
				if (Events)
				{
					FMIExplosionEvent X;
					X.Position = Centre;
					X.Radius = 450.0;
					X.bBig = false;
					Events->Explosion.Broadcast(X);
				}
			}
			else
			{
				const bool bHead = P.Part == TEXT("head");
				const FVector Point = bHead ? Goon->GetHeadHit()->GetComponentLocation() : Goon->GetBodyHit()->GetComponentLocation();
				D.Kind = EMIDamageKind::Bullet;
				D.From = Eye;
				D.Direction = (Point - Eye).GetSafeNormal();
				D.Point = Point - D.Direction * (bHead ? Goon->GetHeadHit()->GetScaledSphereRadius() : Goon->GetBodyHit()->GetScaledCapsuleRadius());
				D.Part = bHead ? FName(TEXT("head")) : FName(TEXT("body"));
				D.Weapon = TEXT("chopper");
				if (Events)
				{
					FMIImpactEvent Hit;
					Hit.Point = D.Point;
					Hit.Normal = -D.Direction;
					Hit.Surface = TEXT("flesh");
					Hit.Direction = D.Direction;
					Hit.Actor = Goon;
					Events->Impact.Broadcast(Hit);
				}
			}
			const FVector Fwd = Goon->GetActorForwardVector();
			const double Facing = FVector::DotProduct(Fwd.GetSafeNormal2D(), D.Direction.GetSafeNormal2D());
			const FMIDamageResult R = Goon->ApplyMIDamage(D);
			UE_LOG(LogMI, Display, TEXT("MI.Goon.Kill: %s %s at %.1f m, shot %s (facing dot %.2f), killed %d"), *Goon->GetName(), *P.Part.ToString(),
				Live[I].Key / 100.0, Facing < -0.5 ? TEXT("into the front") : Facing > 0.5 ? TEXT("into the back") : TEXT("into the side"), Facing, R.bKilled ? 1 : 0);
			if (R.bKilled)
			{
				P.Killed.Add(Goon);
			}
		}
	}

	bool Tick(float)
	{
		if (!Active.IsValid())
		{
			return false;
		}
		FProbe& P = *Active;
		if (!P.World.IsValid())
		{
			Active.Reset();
			return false;
		}
		P.Clock += FApp::GetDeltaTime();
		if (!P.bFired)
		{
			P.Before.Add();
			if (P.Clock >= P.Delay)
			{
				P.bFired = true;
				P.Clock = 0.0;
				Kill(P);
			}
			return true;
		}
		P.After.Add();
		if (P.Clock < 3.0)
		{
			return true;
		}
		double Start = 0.0, Worst = 0.0;
		int32 Rag = 0, Settled = 0;
		for (const TWeakObjectPtr<AMIGoon>& W : P.Killed)
		{
			if (const AMIGoon* Goon = W.Get())
			{
				Start += Goon->GetRagdollStartCost();
				Worst = FMath::Max(Worst, Goon->GetRagdollStartCost());
				Rag += Goon->IsRagdoll() ? 1 : 0;
				Settled += Goon->IsBodySettled() ? 1 : 0;
			}
		}
		// The first three frames after the kill carry the ragdoll start and the bodies' first steps.
		FFrames First;
		for (int32 I = 0; I < 3 && I < P.After.Frame.Num(); ++I)
		{
			First.Frame.Add(P.After.Frame[I]);
			First.Game.Add(P.After.Game[I]);
		}
		const UMIEffects* Fx = UMIEffects::Get(P.World.Get());
		UE_LOG(LogMI, Display, TEXT("MI.Goon.Kill result: %d killed (%s), ragdolls %d, frozen after 3 s %d, ragdoll start %.3f ms in all (worst body %.3f ms), blood decals %d"),
			P.Killed.Num(), *P.Part.ToString(), Rag, Settled, Start * 1000.0, Worst * 1000.0, Fx ? Fx->CountBlood() : -1);
		UE_LOG(LogMI, Display, TEXT("MI.Goon.Kill before (%.1f s): %s"), P.Delay, *P.Before.Line());
		UE_LOG(LogMI, Display, TEXT("MI.Goon.Kill first 3 frames after: %s"), *First.Line());
		UE_LOG(LogMI, Display, TEXT("MI.Goon.Kill after (3 s): %s"), *P.After.Line());
		Active.Reset();
		return false;
	}

	FAutoConsoleCommandWithWorldAndArgs KillCmd(TEXT("MI.Goon.Kill"),
		TEXT("MI.Goon.Kill <count> [body|head|blast] [max metres] [delay s]: kill the nearest living Goons as a round or a blast would, and log the frames' cost"),
		FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args, UWorld* World)
		{
			if (!World || Active.IsValid())
			{
				UE_LOG(LogMI, Warning, TEXT("MI.Goon.Kill: %s"), World ? TEXT("a probe is already running") : TEXT("no world"));
				return;
			}
			Active = MakeShared<FProbe>();
			Active->World = World;
			Active->Count = Args.Num() > 0 ? FMath::Max(1, FCString::Atoi(*Args[0])) : 1;
			Active->Part = Args.Num() > 1 ? FName(*Args[1].ToLower()) : FName(TEXT("body"));
			Active->MaxMetres = Args.Num() > 2 ? FCString::Atod(*Args[2]) : 0.0;
			Active->Delay = Args.Num() > 3 ? FMath::Max(0.0, FCString::Atod(*Args[3])) : 1.0;
			Active->Handle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateStatic(&Tick));
			UE_LOG(LogMI, Display, TEXT("MI.Goon.Kill: %d %s in %.1f s"), Active->Count, *Active->Part.ToString(), Active->Delay);
		}));
}

#endif
