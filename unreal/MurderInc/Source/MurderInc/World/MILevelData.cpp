#include "World/MILevelData.h"

#include "Core/Data/MIDataSubsystem.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "MurderInc.h"

namespace
{
	FVector Vec(const TSharedPtr<FJsonObject>& O)
	{
		return FVector(O->GetNumberField(TEXT("x")), O->GetNumberField(TEXT("y")), O->GetNumberField(TEXT("z")));
	}

	const TSharedPtr<FJsonObject>& Web(const TSharedPtr<FJsonObject>& O) { return O->GetObjectField(TEXT("web")); }

	FMILevelPoint Point(const TSharedPtr<FJsonObject>& O)
	{
		FMILevelPoint P;
		P.Index = static_cast<int32>(O->GetNumberField(TEXT("index")));
		P.Pos = Vec(Web(O)->GetObjectField(TEXT("pos")));
		P.Zone = FName(O->GetStringField(TEXT("zone")));
		O->TryGetStringField(TEXT("place"), P.Place);
		O->TryGetBoolField(TEXT("interior"), P.bInterior);
		FString Layer;
		if (O->TryGetStringField(TEXT("layer"), Layer))
		{
			P.Layer = FName(Layer);
		}
		O->TryGetBoolField(TEXT("enabled"), P.bEnabled);
		const TArray<TSharedPtr<FJsonValue>>* Over;
		if (O->TryGetArrayField(TEXT("overlooks"), Over))
		{
			for (const TSharedPtr<FJsonValue>& Z : *Over)
			{
				P.Overlooks.Add(FName(Z->AsString()));
			}
		}
		FString Type;
		if (O->TryGetStringField(TEXT("type"), Type))
		{
			P.Type = FName(Type);
		}
		const TSharedPtr<FJsonObject>* Facing;
		if (Web(O)->TryGetObjectField(TEXT("facing"), Facing))
		{
			const FVector F = Vec(*Facing);
			P.Yaw = FMath::Atan2(-F.X, -F.Z);
		}
		return P;
	}

	FMILevelObjective Objective(const TSharedPtr<FJsonObject>& O)
	{
		FMILevelObjective R;
		FString Id;
		if (O->TryGetStringField(TEXT("id"), Id))
		{
			R.Id = FName(Id);
		}
		O->TryGetStringField(TEXT("code"), R.Code);
		O->TryGetStringField(TEXT("label"), R.Label);
		O->TryGetStringField(TEXT("place"), R.Place);
		R.Zone = FName(O->GetStringField(TEXT("zone")));
		const TSharedPtr<FJsonObject>& W = Web(O);
		R.Pos = Vec(W->GetObjectField(TEXT("pos")));
		W->TryGetNumberField(TEXT("rotationY"), R.Yaw);
		return R;
	}
}

const FMILevelZone* FMILevelData::ZoneAt(double X, double Z) const
{
	for (const FMILevelZone& Zn : Zones)
	{
		if (X >= Zn.MinX && X <= Zn.MaxX && Z >= Zn.MinZ && Z <= Zn.MaxZ)
		{
			return &Zn;
		}
	}
	return nullptr;
}

void FMILevelData::FillWorld(FMIBoxWorld& World, const FMIRng& Root) const
{
	World.Reset(Bounds, Root);
	for (const FMIBox& B : Colliders)
	{
		if (bTruckAfterAll && TruckColliders.Contains(B.Id))
		{
			continue;  // the truck rolls in after the last reel (SyncTruckColliders)
		}
		World.AddBox(B);
	}
}

int32 FMILevelData::RoomAt(const FVector& P) const
{
	for (int32 I = 0; I < Rooms.Num(); ++I)
	{
		const FMIRoom& R = Rooms[I];
		if (P.X > R.Min.X && P.X < R.Max.X && P.Z > R.Min.Z && P.Z < R.Max.Z && P.Y > R.Min.Y - 0.1 && P.Y < R.Max.Y + 0.1)
		{
			return I;
		}
	}
	return INDEX_NONE;
}

bool FMILevelData::Load(FMILevelData& Out, FString& OutError, const FString& File)
{
	TSharedPtr<FJsonObject> Root;
	if (!UMIDataSubsystem::LoadJsonFile(File, Root, OutError))
	{
		return false;
	}
	const TSharedPtr<FJsonObject>& B = Web(Root->GetObjectField(TEXT("bounds")));
	Out.Bounds.MinX = B->GetNumberField(TEXT("minX"));
	Out.Bounds.MaxX = B->GetNumberField(TEXT("maxX"));
	Out.Bounds.MinZ = B->GetNumberField(TEXT("minZ"));
	Out.Bounds.MaxZ = B->GetNumberField(TEXT("maxZ"));

	for (const TSharedPtr<FJsonValue>& V : Root->GetObjectField(TEXT("colliders"))->GetArrayField(TEXT("boxes")))
	{
		const TSharedPtr<FJsonObject>& C = V->AsObject();
		FMIBox Box;
		Box.Min = Vec(Web(C)->GetObjectField(TEXT("min")));
		Box.Max = Vec(Web(C)->GetObjectField(TEXT("max")));
		Box.Tag = FName(C->GetStringField(TEXT("tag")));
		Box.Surface = FName(C->GetStringField(TEXT("surface")));
		const TSharedPtr<FJsonObject>& F = C->GetObjectField(TEXT("flags"));
		Box.bBulletOnly = F->GetBoolField(TEXT("bulletOnly"));
		Box.bPlayerOnly = F->GetBoolField(TEXT("playerOnly"));
		Box.bNoNav = F->GetBoolField(TEXT("noNav"));
		Box.Id = static_cast<int32>(C->GetNumberField(TEXT("index")));
		const TSharedPtr<FJsonObject>& Owner = C->GetObjectField(TEXT("owner"));
		double Item;
		if (Owner->GetStringField(TEXT("kind")) == TEXT("explosive") && Owner->TryGetNumberField(TEXT("explosive"), Item))
		{
			Box.Owner = static_cast<int32>(Item);
		}
		Out.Colliders.Add(Box);
	}
	for (const TSharedPtr<FJsonValue>& V : Root->GetObjectField(TEXT("enemySpawns"))->GetArrayField(TEXT("points")))
	{
		Out.Spawns.Add(Point(V->AsObject()));
	}
	for (const TSharedPtr<FJsonValue>& V : Root->GetObjectField(TEXT("coverPoints"))->GetArrayField(TEXT("points")))
	{
		Out.Cover.Add(Point(V->AsObject()));
	}
	for (const TSharedPtr<FJsonValue>& V : Root->GetArrayField(TEXT("objectives")))
	{
		Out.Objectives.Add(Objective(V->AsObject()));
	}
	const TSharedPtr<FJsonObject>& X = Root->GetObjectField(TEXT("extraction"));
	Out.Extraction = Objective(X);
	Web(X)->TryGetNumberField(TEXT("radius"), Out.ExtractionRadius);
	const TSharedPtr<FJsonObject>& Truck = Web(X->GetObjectField(TEXT("truck")));
	Out.TruckPos = Vec(Truck->GetObjectField(TEXT("pos")));
	Truck->TryGetNumberField(TEXT("rotationY"), Out.TruckYaw);

	const TSharedPtr<FJsonObject>& Start = Web(Root->GetObjectField(TEXT("playerStart")));
	Out.PlayerStart.Pos = Vec(Start->GetObjectField(TEXT("pos")));
	Out.PlayerStart.Yaw = Start->GetNumberField(TEXT("yaw"));

	for (const TSharedPtr<FJsonValue>& V : Root->GetArrayField(TEXT("zones")))
	{
		const TSharedPtr<FJsonObject>& Z = V->AsObject();
		FMILevelZone Zn;
		Zn.Id = FName(Z->GetStringField(TEXT("id")));
		Zn.Name = Z->GetStringField(TEXT("name"));
		Zn.MinX = Web(Z)->GetNumberField(TEXT("minX"));
		Zn.MaxX = Web(Z)->GetNumberField(TEXT("maxX"));
		Zn.MinZ = Web(Z)->GetNumberField(TEXT("minZ"));
		Zn.MaxZ = Web(Z)->GetNumberField(TEXT("maxZ"));
		Out.Zones.Add(Zn);
	}
	const TSharedPtr<FJsonObject>* El = nullptr;
	if (Root->TryGetObjectField(TEXT("el"), El))
	{
		const TSharedPtr<FJsonObject>& Deck = Web((*El)->GetObjectField(TEXT("deck")));
		Out.Deck.Y = Deck->GetNumberField(TEXT("underside"));
		Out.Deck.MinX = Deck->GetNumberField(TEXT("minX"));
		Out.Deck.MaxX = Deck->GetNumberField(TEXT("maxX"));
		Out.Deck.MinZ = Deck->GetNumberField(TEXT("minZ"));
		Out.Deck.MaxZ = Deck->GetNumberField(TEXT("maxZ"));
	}
	else
	{
		// No elevated train on this level (E2): a deck 250 m outside the bounds, which every point-in-rectangle test passes over.
		Out.bHasDeck = false;
		Out.Deck.Y = 6.5;
		Out.Deck.MinX = Out.Bounds.MaxX + 250.0;
		Out.Deck.MaxX = Out.Deck.MinX + 1.0;
		Out.Deck.MinZ = Out.Bounds.MaxZ + 250.0;
		Out.Deck.MaxZ = Out.Deck.MinZ + 1.0;
	}

	const TSharedPtr<FJsonObject>& Interior = Root->GetObjectField(TEXT("interior"));
	for (const TSharedPtr<FJsonValue>& V : Interior->GetArrayField(TEXT("boxes")))
	{
		FMIRoom Room;
		Room.Min = Vec(Web(V->AsObject())->GetObjectField(TEXT("min")));
		Room.Max = Vec(Web(V->AsObject())->GetObjectField(TEXT("max")));
		Out.Rooms.Add(Room);
	}
	// The doorways belong to the room whose wall they cross (the web AI finds them per room).
	const TArray<TSharedPtr<FJsonValue>>* Doorways = nullptr;
	Interior->TryGetArrayField(TEXT("doorways"), Doorways);
	for (const TSharedPtr<FJsonValue>& V : Doorways ? *Doorways : TArray<TSharedPtr<FJsonValue>>())
	{
		const TSharedPtr<FJsonObject>& W = Web(V->AsObject());
		const FVector O = Vec(W->GetObjectField(TEXT("outside")));
		const FVector I = Vec(W->GetObjectField(TEXT("inside")));
		for (FMIRoom& Room : Out.Rooms)
		{
			if (I.X > Room.Min.X && I.X < Room.Max.X && I.Z > Room.Min.Z && I.Z < Room.Max.Z)
			{
				Room.Doorways.Add({O.X, O.Z, I.X, I.Z, O.Y});
				break;
			}
		}
	}
	for (const TSharedPtr<FJsonValue>& V : Root->GetObjectField(TEXT("explosives"))->GetArrayField(TEXT("items")))
	{
		const TSharedPtr<FJsonObject>& E = V->AsObject();
		FMILevelExplosive Item;
		Item.Index = static_cast<int32>(E->GetNumberField(TEXT("index")));
		Item.Type = FName(E->GetStringField(TEXT("type")));
		Item.Pos = Vec(Web(E)->GetObjectField(TEXT("pos")));
		Web(E)->TryGetNumberField(TEXT("rotationY"), Item.Yaw);
		double Collider;
		if (E->TryGetNumberField(TEXT("collider"), Collider))
		{
			Item.Collider = static_cast<int32>(Collider);
		}
		Out.Explosives.Add(Item);
	}
	for (const TSharedPtr<FJsonValue>& V : Root->GetObjectField(TEXT("cinematicPath"))->GetArrayField(TEXT("points")))
	{
		Out.CinematicPos.Add(Vec(Web(V->AsObject())->GetObjectField(TEXT("pos"))));
		Out.CinematicLook.Add(Vec(Web(V->AsObject())->GetObjectField(TEXT("look"))));
	}
	FString LevelName;
	if (const TSharedPtr<FJsonObject>* Meta; Root->TryGetObjectField(TEXT("meta"), Meta) && (*Meta)->TryGetStringField(TEXT("level"), LevelName))
	{
		Out.Id = FName(LevelName);
	}
	if (FString Arrival; X->TryGetStringField(TEXT("arrival"), Arrival) && Arrival == TEXT("afterAll"))
	{
		Out.bTruckAfterAll = true;
	}
	if (const TSharedPtr<FJsonObject>* TruckObj; X->TryGetObjectField(TEXT("truck"), TruckObj))
	{
		const TArray<TSharedPtr<FJsonValue>>* Idx;
		if ((*TruckObj)->TryGetArrayField(TEXT("colliders"), Idx))
		{
			for (const TSharedPtr<FJsonValue>& V : *Idx)
			{
				Out.TruckColliders.Add(static_cast<int32>(V->AsNumber()));
			}
		}
	}
	if (const TSharedPtr<FJsonObject>* Tune; Root->TryGetObjectField(TEXT("tuning"), Tune))
	{
		const TSharedPtr<FJsonObject>* Sub;
		double N;
		if ((*Tune)->TryGetObjectField(TEXT("difficulty"), Sub))
		{
			if ((*Sub)->TryGetNumberField(TEXT("maxAliveAdd"), N)) Out.Tuning.MaxAliveAdd = static_cast<int32>(N);
			if ((*Sub)->TryGetNumberField(TEXT("pursuitBudgetAdd"), N)) Out.Tuning.PursuitBudgetAdd = static_cast<int32>(N);
		}
		if ((*Tune)->TryGetObjectField(TEXT("spawn"), Sub))
		{
			(*Sub)->TryGetBoolField(TEXT("excludePlayerRoom"), Out.Tuning.bExcludePlayerRoom);
		}
		if ((*Tune)->TryGetObjectField(TEXT("rating"), Sub))
		{
			const TArray<TSharedPtr<FJsonValue>>* Rows;
			if ((*Sub)->TryGetArrayField(TEXT("time"), Rows))
			{
				for (const TSharedPtr<FJsonValue>& Row : *Rows)
				{
					Out.Tuning.RatingTime.Add({Row->AsArray()[0]->AsNumber(), static_cast<int32>(Row->AsArray()[1]->AsNumber())});
				}
			}
		}
		if ((*Tune)->TryGetNumberField(TEXT("startPitch"), N))
		{
			Out.Tuning.StartPitch = N;
		}
	}
	if (const TSharedPtr<FJsonObject>* Nav; Root->TryGetObjectField(TEXT("nav"), Nav) && (*Nav)->HasField(TEXT("layers")))
	{
		Out.NavJson = *Nav;
		for (const TSharedPtr<FJsonValue>& L : (*Nav)->GetArrayField(TEXT("layers")))
		{
			Out.NavLayerIds.Add(FName(L->AsObject()->GetStringField(TEXT("id"))));
		}
	}
	if (Out.Colliders.Num() == 0 || Out.Objectives.Num() == 0 || Out.Spawns.Num() == 0)
	{
		OutError = File + TEXT(" has no colliders, objectives or spawn points");
		return false;
	}
	return true;
}

const FMILevelData* FMILevelData::Get()
{
	static TUniquePtr<FMILevelData> Cached;
	static bool bTried = false;
	if (!bTried)
	{
		bTried = true;
		TUniquePtr<FMILevelData> Data = MakeUnique<FMILevelData>();
		FString Error;
		if (Load(*Data, Error))
		{
			Cached = MoveTemp(Data);
		}
		else
		{
			UE_LOG(LogMI, Error, TEXT("level.json: %s"), *Error);
		}
	}
	return Cached.Get();
}

namespace
{
	FName GActiveLevel = TEXT("block");
}

const FMILevelData* FMILevelData::ForLevel(FName Id)
{
	if (Id.IsNone() || Id == FName(TEXT("block")))
	{
		return Get();
	}
	static TMap<FName, TUniquePtr<FMILevelData>> Cache;
	if (TUniquePtr<FMILevelData>* Found = Cache.Find(Id))
	{
		return Found->Get();
	}
	TUniquePtr<FMILevelData> Data = MakeUnique<FMILevelData>();
	FString Error;
	if (!Load(*Data, Error, FString::Printf(TEXT("level_%s.json"), *Id.ToString())))
	{
		UE_LOG(LogMI, Error, TEXT("level_%s.json: %s"), *Id.ToString(), *Error);
		return nullptr;  // not cached: a later call tries again
	}
	Data->Id = Id;
	return Cache.Add(Id, MoveTemp(Data)).Get();
}

void FMILevelData::SetActive(FName Id) { GActiveLevel = Id.IsNone() ? FName(TEXT("block")) : Id; }
FName FMILevelData::ActiveId() { return GActiveLevel; }
const FMILevelData* FMILevelData::Current() { return ForLevel(GActiveLevel); }
