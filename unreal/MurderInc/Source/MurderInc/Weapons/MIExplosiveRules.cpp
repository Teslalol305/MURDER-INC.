#include "Weapons/MIExplosiveRules.h"

void FMIExplosiveField::Init(const FMIExplosivesData& InData, uint32 Seed, FMIGameEvents* InEvents)
{
	Data = InData;
	Events = InEvents;
	Rng = FMIRng(Seed).Fork(TEXT("explosives"));
	Items.Reset();
	BlastId = 0;
	bBlastLive = false;
}

const FMIExplosiveKindData* FMIExplosiveField::KindOf(int32 Index) const
{
	return Items.IsValidIndex(Index) ? Data.FindKind(Items[Index].Kind) : nullptr;
}

int32 FMIExplosiveField::Add(FName Kind, const FVector& Foot)
{
	const FMIExplosiveKindData* K = Data.FindKind(Kind);
	FMIExplosiveItem Item;
	Item.Kind = Kind;
	Item.Foot = Foot;
	Item.Height = K ? K->Box.Z : 0.0;
	Item.Hp = K ? K->Hp : 0.0;
	return Items.Add(Item);
}

void FMIExplosiveField::Reset()
{
	for (int32 I = 0; I < Items.Num(); ++I)
	{
		const FMIExplosiveKindData* K = KindOf(I);
		FMIExplosiveItem& Item = Items[I];
		Item.State = EMIExplosiveState::Idle;
		Item.Hp = K ? K->Hp : 0.0;
		Item.Fuse = Item.FuseTotal = 0.0;
		Item.ChainedBy = 0;
	}
	bBlastLive = false;
}

void FMIExplosiveField::Ignite(int32 Index, double Fuse, bool bStruckByRay)
{
	FMIExplosiveItem& Item = Items[Index];
	Item.State = EMIExplosiveState::Lit;
	Item.Fuse = Item.FuseTotal = Fuse;
	// Out of the bullet hole when a ray lit it this frame, else out of the valve in a random upward direction.
	Item.bJetAtHole = bStruckByRay;
	if (!bStruckByRay)
	{
		Item.JetAngle = Rng.Next() * UE_DOUBLE_TWO_PI;
	}
	if (Events)
	{
		Events->ExplosiveLit.Broadcast(Index, Item.Foot, Fuse);
	}
}

void FMIExplosiveField::Damage(int32 Index, double Amount, EMIDamageSource Source, bool bStruckByRay)
{
	if (!Items.IsValidIndex(Index))
	{
		return;
	}
	FMIExplosiveItem& Item = Items[Index];
	if (Item.State == EMIExplosiveState::Gone || !(Amount > 0.0))
	{
		return;
	}
	if (Source == EMIDamageSource::Blast)
	{
		Chain(Index);
		return;
	}
	if (Source == EMIDamageSource::Enemy)
	{
		Amount = Data.Rules.DamageFromEnemyRound;
	}
	Item.Hp = FMath::Max(0.0, Item.Hp - Amount);
	if (Item.State == EMIExplosiveState::Idle)
	{
		const FMIExplosiveKindData* K = KindOf(Index);
		Ignite(Index, K ? K->Fuse : 0.0, bStruckByRay);
	}
	if (Item.Hp <= 0.0)
	{
		Item.Fuse = FMath::Min(Item.Fuse, Data.Rules.PopFuse);
	}
}

void FMIExplosiveField::Chain(int32 Index)
{
	FMIExplosiveItem& Item = Items[Index];
	if (!bBlastLive || Index == BlastSource || Item.State == EMIExplosiveState::Gone || Item.ChainedBy == BlastId)
	{
		return;
	}
	const double Distance = FVector::Dist(Item.Centre(), BlastPos);
	if (Distance > BlastRange)
	{
		return;
	}
	Item.ChainedBy = BlastId;
	const double Fuse = Data.Rules.ChainFuse(Distance, Rng.Next());
	if (Item.State == EMIExplosiveState::Idle)
	{
		Ignite(Index, Fuse, false);
	}
	else
	{
		Item.Fuse = FMath::Min(Item.Fuse, Fuse);
	}
}

void FMIExplosiveField::OnExplosion(const FVector& Position, double Radius, int32 SourceIndex)
{
	BlastId++;
	bBlastLive = true;
	BlastPos = Position;
	BlastSource = SourceIndex;
	const FMIExplosiveKindData* Own = KindOf(SourceIndex);
	BlastRange = Data.Rules.ChainRange(Own ? Own->Size : Data.Rules.SizeFromRadius(Radius));
	// Everything in range goes, seen or not: the shock carries around corners.
	for (int32 I = 0; I < Items.Num(); ++I)
	{
		Chain(I);
	}
}

void FMIExplosiveField::Update(double Dt, TFunctionRef<void(int32)> BlowItem)
{
	EndBlast();  // a blast only chains while it is being resolved
	for (int32 I = 0; I < Items.Num(); ++I)
	{
		if (Items[I].State != EMIExplosiveState::Lit)
		{
			continue;
		}
		Items[I].Fuse -= Dt;
		if (Items[I].Fuse <= 0.0)
		{
			BlowItem(I);
		}
	}
}

FVector FMIExplosiveField::Blow(int32 Index)
{
	FMIExplosiveItem& Item = Items[Index];
	Item.State = EMIExplosiveState::Gone;
	Item.Hp = 0.0;
	Item.Fuse = 0.0;
	if (Events)
	{
		Events->ExplosiveBlast.Broadcast(Index, Item.Centre());
	}
	return Item.Centre();
}
