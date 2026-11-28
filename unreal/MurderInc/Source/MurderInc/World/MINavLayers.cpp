#include "World/MINavLayers.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"

int32 FMINavSpec::IndexOf(FName Id) const
{
	for (int32 I = 0; I < Layers.Num(); ++I)
	{
		if (Layers[I].Id == Id)
		{
			return I;
		}
	}
	return INDEX_NONE;
}

bool FMINavSpec::Allows(int32 PlayerLayer, int32 SpawnLayer) const
{
	const TArray<int32>* List = Reach.Find(PlayerLayer);
	return !List || List->Contains(SpawnLayer);
}

bool FMINavSpec::Parse(const TSharedPtr<FJsonObject>& Nav, FMINavSpec& Out)
{
	Out = FMINavSpec();
	const TArray<TSharedPtr<FJsonValue>>* Layers;
	if (!Nav.IsValid() || !Nav->TryGetArrayField(TEXT("layers"), Layers) || Layers->Num() < 2)
	{
		return false;
	}
	for (const TSharedPtr<FJsonValue>& V : *Layers)
	{
		const TSharedPtr<FJsonObject> O = V->AsObject();
		FMINavLayer L;
		L.Id = FName(O->GetStringField(TEXT("id")));
		L.Y = O->GetNumberField(TEXT("y"));
		L.bBoxes = O->GetStringField(TEXT("floor")) == TEXT("boxes");
		const TSharedPtr<FJsonObject>* Rect;
		if (O->TryGetObjectField(TEXT("rect"), Rect))
		{
			L.MinX = (*Rect)->GetNumberField(TEXT("minX"));
			L.MaxX = (*Rect)->GetNumberField(TEXT("maxX"));
			L.MinZ = (*Rect)->GetNumberField(TEXT("minZ"));
			L.MaxZ = (*Rect)->GetNumberField(TEXT("maxZ"));
		}
		Out.Layers.Add(L);
	}
	const TSharedPtr<FJsonObject>* Reach;
	if (Nav->TryGetObjectField(TEXT("spawnReach"), Reach))
	{
		for (const TPair<FString, TSharedPtr<FJsonValue>>& P : (*Reach)->Values)
		{
			const int32 From = Out.IndexOf(FName(P.Key));
			if (From == INDEX_NONE)
			{
				continue;
			}
			TArray<int32>& List = Out.Reach.FindOrAdd(From);
			for (const TSharedPtr<FJsonValue>& T : P.Value->AsArray())
			{
				const int32 To = Out.IndexOf(FName(T->AsString()));
				if (To != INDEX_NONE)
				{
					List.AddUnique(To);
				}
			}
		}
	}
	Nav->TryGetNumberField(TEXT("firingCellRange"), Out.FiringCellRange);
	Nav->TryGetNumberField(TEXT("strandedAfter"), Out.StrandedAfter);
	return true;
}
