#include "Audio/MIAudioEventLog.h"

#include "Audio/MIAudioDirector.h"
#include "Core/Data/MIDataSubsystem.h"
#include "Core/MIEvents.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Enemies/MIEnemies.h"
#include "Flow/MIGameRules.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

namespace MIEventLogPrivate
{
	TSharedPtr<FJsonValue> V3(const FVector& V)
	{
		TArray<TSharedPtr<FJsonValue>> A;
		A.Add(MakeShared<FJsonValueNumber>(FMath::RoundToDouble(V.X * 100.0) / 100.0));
		A.Add(MakeShared<FJsonValueNumber>(FMath::RoundToDouble(V.Y * 100.0) / 100.0));
		A.Add(MakeShared<FJsonValueNumber>(FMath::RoundToDouble(V.Z * 100.0) / 100.0));
		return MakeShared<FJsonValueArray>(A);
	}

	FVector GetV3(const TSharedPtr<FJsonObject>& J, const TCHAR* Key)
	{
		const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
		if (J->TryGetArrayField(Key, A) && A->Num() == 3)
		{
			return FVector((*A)[0]->AsNumber(), (*A)[1]->AsNumber(), (*A)[2]->AsNumber());
		}
		return FVector::ZeroVector;
	}

	TSharedPtr<FJsonObject> Make(const TCHAR* Type)
	{
		TSharedPtr<FJsonObject> J = MakeShared<FJsonObject>();
		J->SetStringField(TEXT("type"), Type);
		return J;
	}

	double Num(const TSharedPtr<FJsonObject>& J, const TCHAR* K) { double V = 0; J->TryGetNumberField(K, V); return V; }
	bool Bool(const TSharedPtr<FJsonObject>& J, const TCHAR* K) { bool V = false; J->TryGetBoolField(K, V); return V; }
	FName Name(const TSharedPtr<FJsonObject>& J, const TCHAR* K) { FString V; J->TryGetStringField(K, V); return V.IsEmpty() ? NAME_None : FName(V); }
}

void FMIAudioEventLog::Add(const TSharedPtr<FJsonObject>& J)
{
	const double T = Now ? Now() : 0.0;
	J->SetNumberField(TEXT("t"), FMath::RoundToDouble(T * 10000.0) / 10000.0);
	Entries.Add({T, J});
}

void FMIAudioEventLog::Record(FMIGameEvents& InBus, TFunction<double()> InNow)
{
	using namespace MIEventLogPrivate;
	StopRecording();
	Bus = &InBus;
	Now = MoveTemp(InNow);
	Entries.Reset();
	Handles.Add(InBus.WeaponFire.AddLambda([this](const FMIShotFiredEvent& E)
	{
		auto J = Make(TEXT("fire"));
		J->SetStringField(TEXT("weapon"), E.Weapon.ToString());
		J->SetField(TEXT("muzzle"), V3(E.Muzzle));
		J->SetField(TEXT("dir"), V3(E.Direction));
		J->SetNumberField(TEXT("ads"), E.Ads);
		J->SetNumberField(TEXT("burst"), E.Burst);
		J->SetNumberField(TEXT("magLeft"), E.MagLeft);
		Add(J);
	}));
	Handles.Add(InBus.WeaponDry.AddLambda([this](FName W) { auto J = Make(TEXT("dry")); J->SetStringField(TEXT("weapon"), W.ToString()); Add(J); }));
	Handles.Add(InBus.WeaponReload.AddLambda([this](const FMIReloadEvent& E)
	{
		auto J = Make(TEXT("reload"));
		J->SetStringField(TEXT("weapon"), E.Weapon.ToString());
		J->SetStringField(TEXT("phase"), E.Phase.ToString());
		J->SetBoolField(TEXT("empty"), E.bEmpty);
		Add(J);
	}));
	Handles.Add(InBus.WeaponSwitch.AddLambda([this](const FMISwitchEvent& E)
	{
		auto J = Make(TEXT("switch"));
		J->SetStringField(TEXT("from"), E.From.ToString());
		J->SetStringField(TEXT("to"), E.To.ToString());
		J->SetStringField(TEXT("phase"), E.Phase.ToString());
		Add(J);
	}));
	Handles.Add(InBus.WeaponSwing.AddLambda([this](FName W) { auto J = Make(TEXT("swing")); J->SetStringField(TEXT("weapon"), W.ToString()); Add(J); }));
	Handles.Add(InBus.WeaponMelee.AddLambda([this](bool bHit) { auto J = Make(TEXT("melee")); J->SetBoolField(TEXT("hit"), bHit); Add(J); }));
	Handles.Add(InBus.Impact.AddLambda([this](const FMIImpactEvent& E)
	{
		auto J = Make(TEXT("impact"));
		J->SetField(TEXT("point"), V3(E.Point));
		J->SetField(TEXT("normal"), V3(E.Normal));
		J->SetField(TEXT("dir"), V3(E.Direction));
		J->SetStringField(TEXT("surface"), E.Surface.ToString());
		J->SetNumberField(TEXT("from"), (int32)E.From);
		Add(J);
	}));
	Handles.Add(InBus.PlayerHitEnemy.AddLambda([this](const FMIHitEnemyEvent& E)
	{
		auto J = Make(TEXT("hitEnemy"));
		J->SetStringField(TEXT("part"), E.Part.ToString());
		J->SetBoolField(TEXT("killed"), E.bKilled);
		J->SetNumberField(TEXT("damage"), E.Damage);
		J->SetStringField(TEXT("weapon"), E.Weapon.ToString());
		Add(J);
	}));
	Handles.Add(InBus.Explosion.AddLambda([this](const FMIExplosionEvent& E)
	{
		auto J = Make(TEXT("explosion"));
		J->SetField(TEXT("pos"), V3(E.Position));
		J->SetNumberField(TEXT("radius"), E.Radius);
		J->SetBoolField(TEXT("big"), E.bBig);
		Add(J);
	}));
	Handles.Add(InBus.ExplosiveLit.AddLambda([this](int32 I, const FVector& P, double Fuse)
	{
		auto J = Make(TEXT("lit"));
		J->SetNumberField(TEXT("index"), I);
		J->SetField(TEXT("pos"), V3(P));
		J->SetNumberField(TEXT("fuse"), Fuse);
		Add(J);
	}));
	Handles.Add(InBus.ExplosiveBlast.AddLambda([this](int32 I, const FVector& P)
	{
		auto J = Make(TEXT("blast"));
		J->SetNumberField(TEXT("index"), I);
		J->SetField(TEXT("pos"), V3(P));
		Add(J);
	}));
	Handles.Add(InBus.PlayerStep.AddLambda([this](const FMIPlayerStepEvent& E)
	{
		auto J = Make(TEXT("step"));
		J->SetField(TEXT("pos"), V3(E.Position));
		J->SetStringField(TEXT("surface"), E.Surface.ToString());
		J->SetBoolField(TEXT("sprint"), E.bSprint);
		Add(J);
	}));
	Handles.Add(InBus.PlayerJump.AddLambda([this]() { Add(Make(TEXT("jump"))); }));
	Handles.Add(InBus.PlayerLand.AddLambda([this](const FMIPlayerLandEvent& E)
	{
		auto J = Make(TEXT("land"));
		J->SetNumberField(TEXT("speed"), E.Speed);
		J->SetStringField(TEXT("surface"), E.Surface.ToString());
		Add(J);
	}));
	Handles.Add(InBus.PlayerHit.AddLambda([this](const FMIPlayerHitEvent& E)
	{
		auto J = Make(TEXT("playerHit"));
		J->SetNumberField(TEXT("amount"), E.Amount);
		J->SetNumberField(TEXT("health"), E.Health);
		J->SetNumberField(TEXT("kind"), (int32)E.Kind);
		if (E.From.IsSet())
		{
			J->SetField(TEXT("from"), V3(E.From.GetValue()));
		}
		Add(J);
	}));
	Handles.Add(InBus.PlayerDead.AddLambda([this](const TOptional<FVector>& From)
	{
		auto J = Make(TEXT("dead"));
		if (From.IsSet())
		{
			J->SetField(TEXT("from"), V3(From.GetValue()));
		}
		Add(J);
	}));
	Handles.Add(InBus.Enemy.AddLambda([this](const FMIEnemyEvent& E)
	{
		auto J = Make(TEXT("enemy"));
		J->SetNumberField(TEXT("kind"), (int32)E.Kind);
		J->SetNumberField(TEXT("id"), E.Id);
		J->SetNumberField(TEXT("etype"), (int32)E.Type);
		J->SetField(TEXT("pos"), V3(E.Pos));
		J->SetField(TEXT("dir"), V3(E.Dir));
		J->SetStringField(TEXT("phase"), E.Phase.ToString());
		J->SetStringField(TEXT("part"), E.Part.ToString());
		J->SetNumberField(TEXT("damage"), E.Damage);
		J->SetNumberField(TEXT("duration"), E.Duration);
		J->SetBoolField(TEXT("byPlayer"), E.bByPlayer);
		J->SetStringField(TEXT("weapon"), E.Weapon.ToString());
		Add(J);
	}));
	Handles.Add(InBus.Flow.AddLambda([this](const FMIFlowEvent& E)
	{
		auto J = Make(TEXT("flow"));
		J->SetStringField(TEXT("name"), E.Name.ToString());
		J->SetStringField(TEXT("text"), E.Text);
		J->SetNumberField(TEXT("a"), E.A);
		J->SetNumberField(TEXT("b"), E.B);
		J->SetNumberField(TEXT("c"), E.C);
		Add(J);
	}));
	Handles.Add(InBus.MusicIntensity.AddLambda([this](double I)
	{
		// Every frame on the bus: keep a change of more than 0.01 only.
		static double Last = -1.0;
		if (FMath::Abs(I - Last) > 0.01)
		{
			Last = I;
			auto J = Make(TEXT("music"));
			J->SetNumberField(TEXT("i"), I);
			Add(J);
		}
	}));
}

void FMIAudioEventLog::StopRecording()
{
	if (!Bus)
	{
		return;
	}
	FMIGameEvents& B = *Bus;
	int32 I = 0;
	auto Next = [this, &I]() { return Handles.IsValidIndex(I) ? Handles[I++] : FDelegateHandle(); };
	B.WeaponFire.Remove(Next());
	B.WeaponDry.Remove(Next());
	B.WeaponReload.Remove(Next());
	B.WeaponSwitch.Remove(Next());
	B.WeaponSwing.Remove(Next());
	B.WeaponMelee.Remove(Next());
	B.Impact.Remove(Next());
	B.PlayerHitEnemy.Remove(Next());
	B.Explosion.Remove(Next());
	B.ExplosiveLit.Remove(Next());
	B.ExplosiveBlast.Remove(Next());
	B.PlayerStep.Remove(Next());
	B.PlayerJump.Remove(Next());
	B.PlayerLand.Remove(Next());
	B.PlayerHit.Remove(Next());
	B.PlayerDead.Remove(Next());
	B.Enemy.Remove(Next());
	B.Flow.Remove(Next());
	B.MusicIntensity.Remove(Next());
	Handles.Reset();
	Bus = nullptr;
}

void FMIAudioEventLog::Observe(double Time, const FVector& Listener, const FVector& Forward, double Health, bool bAlive)
{
	using namespace MIEventLogPrivate;
	auto J = Make(TEXT("observe"));
	J->SetField(TEXT("listener"), V3(Listener));
	J->SetField(TEXT("forward"), V3(Forward));
	J->SetNumberField(TEXT("health"), Health);
	J->SetBoolField(TEXT("alive"), bAlive);
	J->SetNumberField(TEXT("t"), Time);
	Entries.Add({Time, J});
}

bool FMIAudioEventLog::Save(const FString& Path) const
{
	TSharedPtr<FJsonObject> Root = MakeShared<FJsonObject>();
	Root->SetStringField(TEXT("about"), TEXT("A recorded bus event stream (docs/unreal/AUDIO.md section 7): t in seconds; positions in Unreal units except the enemy and flow payloads (web units), as on the bus."));
	TArray<TSharedPtr<FJsonValue>> A;
	for (const FEntry& E : Entries)
	{
		A.Add(MakeShared<FJsonValueObject>(E.Json));
	}
	Root->SetArrayField(TEXT("events"), A);
	FString Text;
	const TSharedRef<TJsonWriter<>> W = TJsonWriterFactory<>::Create(&Text);
	FJsonSerializer::Serialize(Root.ToSharedRef(), W);
	return FFileHelper::SaveStringToFile(Text, *Path);
}

bool FMIAudioEventLog::Parse(const TSharedPtr<FJsonObject>& Root, FString& OutError)
{
	Entries.Reset();
	const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
	if (!Root.IsValid() || !Root->TryGetArrayField(TEXT("events"), A))
	{
		OutError = TEXT("no events array");
		return false;
	}
	for (const TSharedPtr<FJsonValue>& V : *A)
	{
		const TSharedPtr<FJsonObject> J = V->AsObject();
		if (J.IsValid())
		{
			Entries.Add({J->GetNumberField(TEXT("t")), J});
		}
	}
	Entries.StableSort([](const FEntry& X, const FEntry& Y) { return X.Time < Y.Time; });
	return true;
}

bool FMIAudioEventLog::Load(const FString& Path, FString& OutError)
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *Path))
	{
		OutError = TEXT("cannot read ") + Path;
		return false;
	}
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> R = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(R, Root))
	{
		OutError = TEXT("not JSON: ") + Path;
		return false;
	}
	return Parse(Root, OutError);
}

double FMIAudioEventLog::Duration() const
{
	return Entries.Num() ? Entries.Last().Time : 0.0;
}

int32 FMIAudioEventLog::ReplayRange(double From, double To, FMIGameEvents& B, FMIAudioDirector* Director) const
{
	using namespace MIEventLogPrivate;
	int32 Count = 0;
	for (const FEntry& E : Entries)
	{
		if (E.Time <= From || E.Time > To)
		{
			continue;
		}
		++Count;
		const TSharedPtr<FJsonObject>& J = E.Json;
		const FString Type = J->GetStringField(TEXT("type"));
		if (Type == TEXT("fire"))
		{
			FMIShotFiredEvent S;
			S.Weapon = Name(J, TEXT("weapon"));
			S.Muzzle = GetV3(J, TEXT("muzzle"));
			S.Direction = GetV3(J, TEXT("dir"));
			S.Ads = Num(J, TEXT("ads"));
			S.Burst = (int32)Num(J, TEXT("burst"));
			S.MagLeft = (int32)Num(J, TEXT("magLeft"));
			B.WeaponFire.Broadcast(S);
		}
		else if (Type == TEXT("dry")) { B.WeaponDry.Broadcast(Name(J, TEXT("weapon"))); }
		else if (Type == TEXT("reload"))
		{
			FMIReloadEvent R;
			R.Weapon = Name(J, TEXT("weapon"));
			R.Phase = Name(J, TEXT("phase"));
			R.bEmpty = Bool(J, TEXT("empty"));
			B.WeaponReload.Broadcast(R);
		}
		else if (Type == TEXT("switch"))
		{
			FMISwitchEvent S;
			S.From = Name(J, TEXT("from"));
			S.To = Name(J, TEXT("to"));
			S.Phase = Name(J, TEXT("phase"));
			B.WeaponSwitch.Broadcast(S);
		}
		else if (Type == TEXT("swing")) { B.WeaponSwing.Broadcast(Name(J, TEXT("weapon"))); }
		else if (Type == TEXT("melee")) { B.WeaponMelee.Broadcast(Bool(J, TEXT("hit"))); }
		else if (Type == TEXT("impact"))
		{
			FMIImpactEvent I;
			I.Point = GetV3(J, TEXT("point"));
			I.Normal = GetV3(J, TEXT("normal"));
			I.Direction = GetV3(J, TEXT("dir"));
			I.Surface = Name(J, TEXT("surface"));
			I.From = (EMIDamageSource)(int32)Num(J, TEXT("from"));
			B.Impact.Broadcast(I);
		}
		else if (Type == TEXT("hitEnemy"))
		{
			FMIHitEnemyEvent H;
			H.Part = Name(J, TEXT("part"));
			H.bKilled = Bool(J, TEXT("killed"));
			H.Damage = Num(J, TEXT("damage"));
			H.Weapon = Name(J, TEXT("weapon"));
			B.PlayerHitEnemy.Broadcast(H);
		}
		else if (Type == TEXT("explosion"))
		{
			FMIExplosionEvent X;
			X.Position = GetV3(J, TEXT("pos"));
			X.Radius = Num(J, TEXT("radius"));
			X.bBig = Bool(J, TEXT("big"));
			B.Explosion.Broadcast(X);
		}
		else if (Type == TEXT("lit")) { B.ExplosiveLit.Broadcast((int32)Num(J, TEXT("index")), GetV3(J, TEXT("pos")), Num(J, TEXT("fuse"))); }
		else if (Type == TEXT("blast")) { B.ExplosiveBlast.Broadcast((int32)Num(J, TEXT("index")), GetV3(J, TEXT("pos"))); }
		else if (Type == TEXT("step"))
		{
			FMIPlayerStepEvent S;
			S.Position = GetV3(J, TEXT("pos"));
			S.Surface = Name(J, TEXT("surface"));
			S.bSprint = Bool(J, TEXT("sprint"));
			B.PlayerStep.Broadcast(S);
		}
		else if (Type == TEXT("jump")) { B.PlayerJump.Broadcast(); }
		else if (Type == TEXT("land"))
		{
			FMIPlayerLandEvent L;
			L.Speed = Num(J, TEXT("speed"));
			L.Surface = Name(J, TEXT("surface"));
			B.PlayerLand.Broadcast(L);
		}
		else if (Type == TEXT("playerHit"))
		{
			FMIPlayerHitEvent H;
			H.Amount = Num(J, TEXT("amount"));
			H.Health = Num(J, TEXT("health"));
			H.Kind = (EMIDamageKind)(int32)Num(J, TEXT("kind"));
			if (J->HasField(TEXT("from")))
			{
				H.From = GetV3(J, TEXT("from"));
			}
			B.PlayerHit.Broadcast(H);
		}
		else if (Type == TEXT("dead"))
		{
			TOptional<FVector> From;
			if (J->HasField(TEXT("from")))
			{
				From = GetV3(J, TEXT("from"));
			}
			B.PlayerDead.Broadcast(From);
		}
		else if (Type == TEXT("enemy"))
		{
			FMIEnemyEvent Ev;
			Ev.Kind = (FMIEnemyEvent::EKind)(int32)Num(J, TEXT("kind"));
			Ev.Id = (int32)Num(J, TEXT("id"));
			Ev.Type = (MIEnemy::EType)(int32)Num(J, TEXT("etype"));
			Ev.Pos = GetV3(J, TEXT("pos"));
			Ev.Dir = GetV3(J, TEXT("dir"));
			Ev.Phase = Name(J, TEXT("phase"));
			Ev.Part = Name(J, TEXT("part"));
			Ev.Damage = Num(J, TEXT("damage"));
			Ev.Duration = Num(J, TEXT("duration"));
			Ev.bByPlayer = Bool(J, TEXT("byPlayer"));
			Ev.Weapon = Name(J, TEXT("weapon"));
			B.Enemy.Broadcast(Ev);
		}
		else if (Type == TEXT("flow"))
		{
			FMIFlowEvent F;
			F.Name = Name(J, TEXT("name"));
			J->TryGetStringField(TEXT("text"), F.Text);
			F.A = Num(J, TEXT("a"));
			F.B = Num(J, TEXT("b"));
			F.C = Num(J, TEXT("c"));
			B.Flow.Broadcast(F);
		}
		else if (Type == TEXT("music")) { B.MusicIntensity.Broadcast(Num(J, TEXT("i"))); }
		else if (Type == TEXT("observe") && Director)
		{
			Director->SetListener(GetV3(J, TEXT("listener")), GetV3(J, TEXT("forward")));
			Director->SetPlayer(Num(J, TEXT("health")), Bool(J, TEXT("alive")));
		}
	}
	return Count;
}
