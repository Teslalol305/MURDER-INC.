#include "Weapons/MICombatSubsystem.h"

#include "Core/Data/MIDataSubsystem.h"
#include "Engine/World.h"
#include "MurderInc.h"
#include "World/MIExplosive.h"

UMICombatSubsystem* UMICombatSubsystem::Get(const UObject* WorldContextObject)
{
	const UWorld* World = WorldContextObject ? WorldContextObject->GetWorld() : nullptr;
	return World ? World->GetSubsystem<UMICombatSubsystem>() : nullptr;
}

TStatId UMICombatSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UMICombatSubsystem, STATGROUP_Tickables);
}

bool UMICombatSubsystem::EnsureData()
{
	if (bHaveData)
	{
		return true;
	}
	FMIConfigData Config;
	if (const UMIDataSubsystem* DataSubsystem = UMIDataSubsystem::Get(this); DataSubsystem && DataSubsystem->IsLoaded())
	{
		Config = DataSubsystem->GetConfig();
	}
	else
	{
		FString Error;
		if (!UMIDataSubsystem::LoadConfig(Config, Error))
		{
			UE_LOG(LogMI, Error, TEXT("Combat: config.json: %s"), *Error);
			return false;
		}
	}
	Data = Config.Explosives;
	Field.Init(Data, static_cast<uint32>(Config.Seed), UMIEventSubsystem::Get(this));
	bHaveData = true;
	return true;
}

void UMICombatSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);
	bReady = EnsureData();
}

void UMICombatSubsystem::Register(TScriptInterface<IMIDamageable> Target)
{
	if (UObject* Object = Target.GetObject())
	{
		Targets.AddUnique(Object);
	}
}

void UMICombatSubsystem::Unregister(UObject* Target)
{
	Targets.Remove(Target);
}

int32 UMICombatSubsystem::AddExplosive(AMIExplosive* Actor, FName Kind, const FVector& Foot)
{
	if (!EnsureData() || !Data.FindKind(Kind))
	{
		UE_LOG(LogMI, Error, TEXT("Combat: unknown explosive kind '%s' on %s"), *Kind.ToString(), *GetNameSafe(Actor));
		return INDEX_NONE;
	}
	const int32 Index = Field.Add(Kind, Foot);
	ExplosiveActors.SetNum(FMath::Max(ExplosiveActors.Num(), Index + 1));
	ExplosiveActors[Index] = Actor;
	return Index;
}

bool UMICombatSubsystem::LineOfSight(const FVector& From, const FVector& To, const AActor* IgnoreA, const AActor* IgnoreB) const
{
	const UWorld* World = GetWorld();
	if (!World)
	{
		return true;
	}
	FCollisionQueryParams Params(SCENE_QUERY_STAT(MIBlastSight), false);
	if (IgnoreA) Params.AddIgnoredActor(IgnoreA);
	if (IgnoreB) Params.AddIgnoredActor(IgnoreB);
	// Hit shapes of people do not hide each other from a blast: only the world (static and dynamic geometry) does.
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	FHitResult Hit;
	return !World->LineTraceSingleByObjectType(Hit, From, To, Objects, Params);
}

void UMICombatSubsystem::Explode(const FVector& Centre, double Radius, double Damage, int32 SourceIndex, bool bBig, AActor* SourceActor)
{
	if (!EnsureData())
	{
		return;
	}
	if (FMIGameEvents* Events = UMIEventSubsystem::Get(this))
	{
		FMIExplosionEvent Event;
		Event.Position = Centre;
		Event.Radius = Radius;
		Event.bBig = bBig;
		Events->Explosion.Broadcast(Event);
	}
	Field.OnExplosion(Centre, Radius, SourceIndex);

	// Enemies first, then the player, then the explosives (combat.js explode()).
	TArray<IMIDamageable*> Ordered;
	for (int32 Pass = 0; Pass < 3; ++Pass)
	{
		for (const TWeakObjectPtr<UObject>& Weak : Targets)
		{
			IMIDamageable* Target = Cast<IMIDamageable>(Weak.Get());
			if (!Target)
			{
				continue;
			}
			const FName Kind = Target->GetMIDamageableKind();
			const int32 Rank = Kind == TEXT("player") ? 1 : Kind == TEXT("explosive") ? 2 : 0;
			if (Rank == Pass)
			{
				Ordered.Add(Target);
			}
		}
	}
	for (IMIDamageable* Target : Ordered)
	{
		AActor* Actor = Cast<AActor>(Target);
		if (!Target->IsMIDamageableAlive() || Actor == SourceActor)
		{
			continue;
		}
		const FVector Point = Target->GetMIBlastTarget();
		const double Distance = FVector::Dist(Point, Centre);
		const double Falloff = MIBlast::Falloff(Distance, Radius);
		if (Falloff <= 0.0 || !LineOfSight(Centre, Point, Actor, SourceActor))
		{
			continue;
		}
		const bool bPlayer = Target->GetMIDamageableKind() == TEXT("player");
		FMIDamage Hit;
		Hit.Amount = Damage * Falloff * (bPlayer ? Data.Rules.PlayerDamageScale : 1.0);
		Hit.Kind = EMIDamageKind::Blast;
		Hit.Source = EMIDamageSource::Blast;
		Hit.From = Centre;
		Hit.Point = Point;
		Hit.Direction = (Point - Centre).GetSafeNormal();
		Hit.Weapon = TEXT("blast");
		Target->ApplyMIDamage(Hit);
	}
}

void UMICombatSubsystem::Blow(int32 Index)
{
	const FVector Centre = Field.Blow(Index);
	AMIExplosive* Actor = ExplosiveActors.IsValidIndex(Index) ? ExplosiveActors[Index].Get() : nullptr;
	if (Actor)
	{
		Actor->OnBlown();
	}
	if (const FMIExplosiveKindData* Kind = Field.KindOf(Index))
	{
		Explode(Centre, Kind->Radius, Kind->Damage, Index, true, Actor);
	}
}

void UMICombatSubsystem::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	if (Field.GetItems().Num() == 0)
	{
		return;
	}
	Field.Update(DeltaTime, [this](int32 Index) { Blow(Index); });
	for (int32 I = 0; I < ExplosiveActors.Num(); ++I)
	{
		if (AMIExplosive* Actor = ExplosiveActors[I].Get())
		{
			Actor->SyncFromItem(Field.GetItems()[I]);
		}
	}
}
