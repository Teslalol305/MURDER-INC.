#include "Audio/MIAudioDirector.h"

#include "Core/MIEvents.h"
#include "Core/MIMath.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Enemies/MIEnemies.h"
#include "Flow/MIGameRules.h"
#include "World/MIBoxWorld.h"

DEFINE_LOG_CATEGORY_STATIC(LogMIAudio, Log, All);

using namespace MIAudioJson;

namespace MIAudioDirectorPrivate
{
	const TCHAR* KindName(FMIEnemyEvent::EKind K)
	{
		switch (K)
		{
		case FMIEnemyEvent::EKind::Spawn: return TEXT("spawn");
		case FMIEnemyEvent::EKind::Alert: return TEXT("alert");
		case FMIEnemyEvent::EKind::Telegraph: return TEXT("telegraph");
		case FMIEnemyEvent::EKind::Fire: return TEXT("fire");
		case FMIEnemyEvent::EKind::Melee: return TEXT("melee");
		case FMIEnemyEvent::EKind::Hit: return TEXT("hit");
		default: return TEXT("killed");
		}
	}

	/** Exponential approach with time constant Tau. */
	double Ease(double Current, double Target, double Tau, double Dt)
	{
		return Tau <= 0.0 ? Target : Current + (Target - Current) * (1.0 - FMath::Exp(-Dt / Tau));
	}

	double Smooth(double A, double B, double X)
	{
		const double T = MI::Clamp01((X - A) / (B - A));
		return T * T * (3.0 - 2.0 * T);
	}
}

// ------------------------------------------------------------------------------------------------------- setup

bool FMIAudioDirector::Init(const FMIAudioData* InData, const FMIVoiceData* InVoice, int32 Seed)
{
	Data = InData;
	VoiceData = InVoice;
	Rng.Initialize(Seed);
	if (!Data)
	{
		return false;
	}
	Options.Master = Data->OptionDefaults.FindRef(TEXT("master"));
	Options.Effects = Data->OptionDefaults.Contains(TEXT("effects")) ? Data->OptionDefaults[TEXT("effects")] : 1.0;
	Options.Ambience = Data->OptionDefaults.Contains(TEXT("ambience")) ? Data->OptionDefaults[TEXT("ambience")] : 1.0;
	Options.Music = Data->OptionDefaults.Contains(TEXT("music")) ? Data->OptionDefaults[TEXT("music")] : 1.0;
	Options.UI = Data->OptionDefaults.Contains(TEXT("ui")) ? Data->OptionDefaults[TEXT("ui")] : 1.0;
	if (Options.Master <= 0.0 && !Data->OptionDefaults.Contains(TEXT("master")))
	{
		Options.Master = 0.8;
	}
	if (VoiceData)
	{
		Options.Voice = VoiceData->Settings.Defaults;
		Voice.Init(VoiceData, VoiceData->Default, Options.Voice);
		Voice.TakeSecs = [this](FName Character, const FString& File)
		{
			const FString Path = FString::Printf(TEXT("Voice/%s/%s"), *Character.ToString(), *File);
			return FileSecs ? FileSecs(Path) : 1.5;
		};
		Triggers.Init(VoiceData->Settings);
		Triggers.OnTrigger = [this](FName T, int32 V) { Voice.Trigger(T, GameClock, V); };
		Triggers.OnRunStart = [this]() { Voice.NewRun(); };
		Triggers.OnSilence = [this]()
		{
			Voice.Silence(GameClock);
			StopInstance(VoiceLine, 0.15);
			VoiceLine = FInstance();
			Subtitle = FMISubtitle();
		};
	}
	if (const TSharedPtr<FJsonObject> Amb = Data->Table(TEXT("ambience")))
	{
		if (const TSharedPtr<FJsonObject> Sch = Obj(Amb, TEXT("schedule")))
		{
			for (const auto& Pair : Sch->Values)
			{
				const TSharedPtr<FJsonObject> E = Pair.Value->Type == EJson::Object ? Pair.Value->AsObject() : nullptr;
				if (E.IsValid())
				{
					FarTimers.Add(FName(FString(*Pair.Key)), Num(E, TEXT("first"), 10) * Rng.FRandRange(0.7, 1.3));
				}
			}
		}
		const FVector2D Every = Range(Obj(Amb, TEXT("train")), TEXT("every"), 55);
		TrainTimer = Rng.FRandRange(0.3, 0.6) * Every.X;
	}
	if (const TSharedPtr<FJsonObject> M = Data->Table(TEXT("music")))
	{
		const TArray<TSharedPtr<FJsonValue>>* S = nullptr;
		if (M->TryGetArrayField(TEXT("stems"), S))
		{
			StemGain.Init(0.0, S->Num());
		}
	}
	UpdateMix(0.0);
	return true;
}

void FMIAudioDirector::Bind(FMIGameEvents& Bus)
{
	Unbind();
	BoundBus = &Bus;
	Handles.Add(Bus.WeaponFire.AddRaw(this, &FMIAudioDirector::OnWeaponFire));
	Handles.Add(Bus.WeaponDry.AddRaw(this, &FMIAudioDirector::OnWeaponDry));
	Handles.Add(Bus.WeaponReload.AddRaw(this, &FMIAudioDirector::OnWeaponReload));
	Handles.Add(Bus.WeaponSwitch.AddRaw(this, &FMIAudioDirector::OnWeaponSwitch));
	Handles.Add(Bus.WeaponSwing.AddRaw(this, &FMIAudioDirector::OnWeaponSwing));
	Handles.Add(Bus.WeaponMode.AddRaw(this, &FMIAudioDirector::OnWeaponMode));
	Handles.Add(Bus.WeaponMelee.AddRaw(this, &FMIAudioDirector::OnWeaponMelee));
	Handles.Add(Bus.Impact.AddRaw(this, &FMIAudioDirector::OnImpact));
	Handles.Add(Bus.PlayerHitEnemy.AddRaw(this, &FMIAudioDirector::OnHitEnemy));
	Handles.Add(Bus.Explosion.AddRaw(this, &FMIAudioDirector::OnExplosion));
	Handles.Add(Bus.ExplosiveLit.AddRaw(this, &FMIAudioDirector::OnExplosiveLit));
	Handles.Add(Bus.ExplosiveBlast.AddRaw(this, &FMIAudioDirector::OnExplosiveBlast));
	Handles.Add(Bus.PlayerStep.AddRaw(this, &FMIAudioDirector::OnPlayerStep));
	Handles.Add(Bus.PlayerJump.AddRaw(this, &FMIAudioDirector::OnPlayerJump));
	Handles.Add(Bus.PlayerLand.AddRaw(this, &FMIAudioDirector::OnPlayerLand));
	Handles.Add(Bus.PlayerHit.AddRaw(this, &FMIAudioDirector::OnPlayerHit));
	Handles.Add(Bus.PlayerDead.AddRaw(this, &FMIAudioDirector::OnPlayerDead));
	Handles.Add(Bus.Enemy.AddRaw(this, &FMIAudioDirector::OnEnemy));
	Handles.Add(Bus.Flow.AddRaw(this, &FMIAudioDirector::OnFlow));
	Handles.Add(Bus.MusicIntensity.AddRaw(this, &FMIAudioDirector::OnMusicIntensity));
}

void FMIAudioDirector::Unbind()
{
	if (!BoundBus)
	{
		return;
	}
	FMIGameEvents& B = *BoundBus;
	int32 I = 0;
	auto Next = [this, &I]() { return Handles.IsValidIndex(I) ? Handles[I++] : FDelegateHandle(); };
	B.WeaponFire.Remove(Next());
	B.WeaponDry.Remove(Next());
	B.WeaponReload.Remove(Next());
	B.WeaponSwitch.Remove(Next());
	B.WeaponSwing.Remove(Next());
	B.WeaponMode.Remove(Next());
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
	BoundBus = nullptr;
}

void FMIAudioDirector::SetOptions(const FMIAudioOptions& InOptions)
{
	Options = InOptions;
	Voice.SetOptions(Options.Voice);
	if (Options.Voice.Frequency == TEXT("off") || Options.Voice.Volume <= 0.0)
	{
		Voice.Silence(GameClock);
	}
}

void FMIAudioDirector::SetSuppressed(FName Weapon, bool bOn)
{
	if (bOn)
	{
		Suppressed.Add(Weapon);
	}
	else
	{
		Suppressed.Remove(Weapon);
	}
}

void FMIAudioDirector::SetListener(const FVector& Pos, const FVector& Forward)
{
	Listener = Pos;
	ListenerForward = Forward;
}

void FMIAudioDirector::SetPlayer(double HealthFraction, bool bInAlive)
{
	Health = HealthFraction;
	bAlive = bInAlive;
}

void FMIAudioDirector::SetEnemy(int32 Id, bool bBuzzard, const FVector& Pos, bool bInAlive)
{
	FTracked& T = Enemies.FindOrAdd(Id);
	T.bBuzzard = bBuzzard;
	if (!T.bHasPos)
	{
		T.LastPos = Pos;
		T.bHasPos = true;
	}
	T.Pos = Pos;
	T.bAlive = bInAlive;
}

FVector FMIAudioDirector::Web(const FVector& W) const
{
	return MI::Web::ToUnreal(W);
}

TSharedPtr<FJsonObject> FMIAudioDirector::Surface(FName Name) const
{
	const TSharedPtr<FJsonObject> S = Data->Table(TEXT("surfaces"));
	TSharedPtr<FJsonObject> E = Obj(S, Name.IsNone() ? TEXT("default") : *Name.ToString());
	return E.IsValid() ? E : Obj(S, TEXT("default"));
}

FString FMIAudioDirector::Fill(const FString& Pattern, const TMap<FString, FString>& Vars) const
{
	FString Out = Pattern;
	for (const auto& V : Vars)
	{
		Out.ReplaceInline(*FString::Printf(TEXT("{%s}"), *V.Key), *V.Value, ESearchCase::CaseSensitive);
	}
	return Out;
}

// ------------------------------------------------------------------------------------------------------ voices

void FMIAudioDirector::Queue(const FMIAudioCmd& C)
{
	if (C.Time <= Clock + 1e-9)
	{
		Ready.Add(C);
	}
	else
	{
		Pending.Add(C);
	}
}

int32 FMIAudioDirector::StartFile(const FMISoundDef& Def, const FString& File, double Secs, double Volume, const FPlayArgs& Args, double Pitch)
{
	FMIAudioCmd C;
	C.Type = EMIAudioCmd::Start;
	C.Id = NextId++;
	C.Time = Clock + Args.Delay;
	C.Sound = Def.Name;
	C.File = File;
	C.Category = Def.Category;
	C.Volume = Volume;
	C.Pitch = Pitch;
	C.b3D = Args.b3D && (Def.Category == TEXT("world") || Def.Category == TEXT("ambience"));
	C.Pos = Args.Pos;
	C.Ref = (Def.Ref > 0.0 ? Def.Ref : Data->DefaultRef) * 100.0;
	C.Roll = Def.Ref > 0.0 ? Def.Roll : Data->DefaultRoll;
	C.bLoop = Args.bLoop || Def.bLoop;
	C.Priority = Def.Priority;
	C.Secs = FileSecs ? FileSecs(File) : Secs;
	if (C.Secs <= 0.0)
	{
		C.Secs = Secs > 0.0 ? Secs : 1.0;
	}
	Queue(C);
	FLive L;
	L.Sound = Def.Name;
	L.Start = C.Time;
	L.End = C.bLoop ? 1e18 : C.Time + C.Secs / FMath::Max(0.25, Pitch);
	L.Priority = Def.Priority;
	L.Category = Def.Category;
	Live.Add(C.Id, L);
	++StartedCount;
	return C.Id;
}

FMIAudioDirector::FInstance FMIAudioDirector::Play(FName Sound, const FPlayArgs& Args)
{
	FInstance Inst;
	const FMISoundDef* Def = Data ? Data->Find(Sound) : nullptr;
	if (!Def)
	{
		++RefusedCount;
		bool bAlready = false;
		UnknownEver.Add(Sound, &bAlready);
		if (!bAlready)
		{
			UnknownNew.Add(Sound);
		}
		return Inst;
	}
	const double T = Clock + Args.Delay;
	const FMIAudioCategory* Cat = Data->Categories.Find(Def->Category);

	// Refusals (spec 07 3.18).
	if (Mix.bPaused && Cat && Cat->bPausable && Args.Delay <= 0.0)
	{
		++RefusedCount;
		return Inst;
	}
	if (Def->Gap > 0.0 && T - (LastStartOf.Contains(Sound) ? LastStartOf[Sound] : -1e9) < Def->Gap)
	{
		++RefusedCount;
		return Inst;
	}
	if (Sound.ToString().StartsWith(TEXT("imp_")))
	{
		if (T - LastImpact < Data->ImpactGap)
		{
			++RefusedCount;
			return Inst;
		}
		LastImpact = T;
	}
	if (Args.b3D && FVector::Dist(Args.Pos, Listener) > Data->Cull * 100.0 && !Args.bLoop)
	{
		++RefusedCount;
		return Inst;
	}
	// Voices of this name at once: the oldest makes room.
	if (Def->Max > 0)
	{
		int32 Count = 0;
		int32 Oldest = 0;
		double OldestStart = 1e18;
		for (const auto& Pair : Live)
		{
			if (Pair.Value.Sound == Sound && Pair.Value.End > T)
			{
				++Count;
				if (Pair.Value.Start < OldestStart)
				{
					OldestStart = Pair.Value.Start;
					Oldest = Pair.Key;
				}
			}
		}
		if (Count >= Def->Max && Oldest)
		{
			FInstance Old;
			Old.Ids.Add(Oldest);
			Old.Base.Add(1.0);
			StopInstance(Old, 0.012, Args.Delay);
		}
	}
	LastStartOf.Add(Sound, T);

	const bool bLoop = Args.bLoop || Def->bLoop;
	const double Jitter = (bLoop || Args.bNoJitter) ? 0.0 : Def->Jitter;
	const double Pitch = FMath::Clamp(Args.Pitch * (1.0 + Rng.FRandRange(-Jitter, Jitter)), 0.25, 4.0);
	const double Volume = Def->Volume * Args.Volume * (bLoop ? 1.0 : 1.0 - Rng.FRand() * Data->LevelVariation);

	const FMIReplace* Rep = Data->Replace.Find(Sound);
	bool bAnyLayer = false;
	if (Rep)
	{
		for (const FMIReplaceLayer& Layer : Rep->Layers)
		{
			TArray<FString> Files;
			for (const FString& F : Layer.Files)
			{
				if (!Exists || Exists(F))
				{
					Files.Add(F);
				}
			}
			if (Files.Num() == 0)
			{
				continue;
			}
			const FString Key = Sound.ToString() + TEXT("/") + Layer.Name.ToString();
			int32 Pick = Rng.RandRange(0, Files.Num() - 1);
			if (Files.Num() > 1 && LastLayerFile.Contains(Key) && LastLayerFile[Key] == Pick)
			{
				Pick = (Pick + 1) % Files.Num();
			}
			LastLayerFile.Add(Key, Pick);
			bAnyLayer = true;
			Inst.Ids.Add(StartFile(*Def, Files[Pick], 0.0, Volume * Layer.Volume, Args, Pitch));
			Inst.Base.Add(Volume * Layer.Volume);
		}
	}
	if (Def->bReplaceOnly)
	{
		if (!bAnyLayer && Rep && !Rep->Fallback.IsNone())
		{
			return Play(Rep->Fallback, Args);
		}
		return Inst;
	}
	const double WebGain = Rep && bAnyLayer ? Rep->Web : 1.0;
	if (WebGain > 0.0 && Def->Files.Num() > 0)
	{
		const int32 N = Def->Files.Num();
		int32 V = NextVariant.FindRef(Sound) % N;
		if (N > 2 && Rng.FRand() < 0.3)
		{
			V = (V + 1) % N;
		}
		NextVariant.Add(Sound, V + 1);
		if (!Exists || Exists(Def->Files[V]))
		{
			Inst.Ids.Add(StartFile(*Def, Def->Files[V], Def->Secs[V], Volume * WebGain, Args, Pitch));
			Inst.Base.Add(Volume * WebGain);
		}
	}
	return Inst;
}

void FMIAudioDirector::SetInstance(const FInstance& I, double Volume, double Delay, double Pitch, const FVector* Pos)
{
	for (int32 K = 0; K < I.Ids.Num(); ++K)
	{
		if (!Live.Contains(I.Ids[K]))
		{
			continue;
		}
		FMIAudioCmd C;
		C.Type = EMIAudioCmd::Set;
		C.Id = I.Ids[K];
		C.Time = Clock + Delay;
		C.Volume = I.Base[K] * Volume;
		C.Pitch = Pitch;
		C.b3D = Pos != nullptr;
		if (Pos)
		{
			C.Pos = *Pos;
		}
		Queue(C);
	}
}

void FMIAudioDirector::StopInstance(const FInstance& I, double Fade, double Delay)
{
	for (const int32 Id : I.Ids)
	{
		if (Live.Remove(Id) == 0)
		{
			continue;
		}
		FMIAudioCmd C;
		C.Type = EMIAudioCmd::Stop;
		C.Id = Id;
		C.Time = Clock + Delay;
		C.Fade = Fade;
		Queue(C);
	}
}

TArray<FName> FMIAudioDirector::TakeUnknown()
{
	TArray<FName> Out = MoveTemp(UnknownNew);
	UnknownNew.Reset();
	return Out;
}

FName FMIAudioDirector::SoundFamily(FName Weapon) const
{
	if (!Data || Data->Find(FName(*FString::Printf(TEXT("%s_shot"), *Weapon.ToString()))))
	{
		return Weapon;
	}
	const FString Family = Str(Data->Table(TEXT("weaponSounds")), *Weapon.ToString());
	return Family.IsEmpty() ? Weapon : FName(*Family);
}

void FMIAudioDirector::TakeCommands(TArray<FMIAudioCmd>& Out)
{
	Out.Append(Ready);
	Ready.Reset();
}

void FMIAudioDirector::PlayEntry(const TSharedPtr<FJsonObject>& Entry, FName Variant, const FVector* At, const TMap<FString, FString>& Vars)
{
	const TArray<TSharedPtr<FJsonValue>>* List = nullptr;
	if (!Entry.IsValid() || !Entry->TryGetArrayField(TEXT("play"), List))
	{
		return;
	}
	for (const TSharedPtr<FJsonValue>& V : *List)
	{
		const TSharedPtr<FJsonObject> P = V->AsObject();
		if (!P.IsValid())
		{
			continue;
		}
		FPlayArgs A;
		A.Volume = PerKey(P, TEXT("vol"), Variant, 1.0);
		A.Pitch = PerKey(P, TEXT("pitch"), Variant, 1.0);
		A.Delay = Num(P, TEXT("delay"), 0.0);
		if (At && Str(P, TEXT("at")) == TEXT("event"))
		{
			A.b3D = true;
			A.Pos = *At;
		}
		if (A.Volume > 0.0)
		{
			Play(FName(Fill(Str(P, TEXT("sound")), Vars)), A);
		}
	}
	double M = 0;
	if (Entry->TryGetNumberField(TEXT("meter"), M) && Str(Entry, TEXT("rule")).IsEmpty())
	{
		Meter(0.0, M);
	}
}

// ----------------------------------------------------------------------------------------------------- the mix

void FMIAudioDirector::Duck(const TCHAR* Name, FName Weapon)
{
	const TSharedPtr<FJsonObject> D = Obj(Obj(Data->Table(TEXT("mix")), TEXT("ducks")), Name);
	if (!D.IsValid())
	{
		return;
	}
	FDuck K;
	K.Depth = PerKey(D, TEXT("depth"), NAME_None, 1.0);
	if (const TSharedPtr<FJsonObject> W = Obj(D, TEXT("weapons")))
	{
		K.Depth = Num(W, *Weapon.ToString(), K.Depth);
	}
	K.Until = Clock + Num(D, TEXT("hold"), 0.1);
	K.Release = Num(D, TEXT("release"), 0.1);
	K.bMusic = Flag(D, TEXT("music"), false);
	Ducks.Add(K);
	double Dip = 0;
	if (D->TryGetNumberField(TEXT("dip"), Dip))
	{
		MusicDip = FMath::Min(MusicDip, Dip);
	}
}

void FMIAudioDirector::MuffleTo(double M, double Floor)
{
	Muffle = FMath::Max(Muffle, M);
	if (Floor >= 0.0)
	{
		MuffleFloor = Floor;
	}
}

void FMIAudioDirector::Meter(double Add, double AtLeast)
{
	MusicMeter = FMath::Max(MusicMeter + Add, AtLeast);
}

double FMIAudioDirector::InteriorAt(const FVector& Pos) const
{
	const FVector W = MI::Web::FromUnreal(Pos);
	double Best = 0.0;
	for (const FMIAudioZone& Z : Data->Zones)
	{
		if (!Z.bInterior || !Z.Box.IsValid)
		{
			continue;
		}
		const double D = FMath::Sqrt(Z.Box.ComputeSquaredDistanceToPoint(W));
		Best = FMath::Max(Best, MI::Clamp01(1.0 - D / FMath::Max(Z.Fade, 0.01)));
	}
	return Best;
}

void FMIAudioDirector::UpdateMix(double Dt)
{
	using namespace MIAudioDirectorPrivate;
	const TSharedPtr<FJsonObject> MixT = Data->Table(TEXT("mix"));
	const TSharedPtr<FJsonObject> Sm = Obj(MixT, TEXT("smoothing"));
	const TSharedPtr<FJsonObject> Low = Obj(MixT, TEXT("lowHealth"));
	const TSharedPtr<FJsonObject> Pause = Obj(MixT, TEXT("pause"));

	Interior += (InteriorAt(Listener) - Interior) * FMath::Min(1.0, 3.0 * Dt);

	double AmbTarget = 1.0, MusTarget = 1.0;
	for (int32 I = 0; I < Ducks.Num(); ++I)
	{
		const FDuck& D = Ducks[I];
		if (Clock < D.Until)
		{
			AmbTarget = FMath::Min(AmbTarget, D.Depth);
			if (D.bMusic)
			{
				MusTarget = FMath::Min(MusTarget, D.Depth);
			}
			DuckRelease = D.Release;
		}
		else if (Clock > D.Until + 4.0 * D.Release)
		{
			Ducks.RemoveAt(I--);
		}
	}
	const double Down = Num(Sm, TEXT("duckDown"), 0.012);
	AmbDuck = Ease(AmbDuck, AmbTarget, AmbTarget < AmbDuck ? Down : FMath::Max(0.1, DuckRelease), Dt);
	MusDuck = Ease(MusDuck, MusTarget, MusTarget < MusDuck ? Down : FMath::Max(0.1, DuckRelease), Dt);
	MusicDip += (1.0 - MusicDip) * FMath::Min(1.0, 3.5 * Dt);
	Muffle += (MuffleFloor - Muffle) * FMath::Min(1.0, Dt * (MuffleFloor > 0.0 ? 3.0 : 0.9));
	AmbStateNow = Ease(AmbStateNow, AmbState, Num(Sm, TEXT("ambience"), 0.5), Dt);

	// The voice line ducks the rest (voice.json settings.duck).
	const bool bSpeaking = Voice.IsSpeaking(GameClock);
	if (VoiceData)
	{
		VoiceAmt = Ease(VoiceAmt, bSpeaking ? 1.0 : 0.0, bSpeaking ? VoiceData->Settings.DuckAttack : VoiceData->Settings.DuckRelease, Dt);
	}

	// Low health: new in this port (audio.json mix.lowHealth).
	const double Below = Num(Low, TEXT("below"), 0.35), Floor = Num(Low, TEXT("floor"), 0.1);
	const bool bPlaying = State == TEXT("playing") || State == TEXT("intro");
	const double KTarget = (bAlive && bPlaying) ? MI::Clamp01((Below - Health) / FMath::Max(0.01, Below - Floor)) : 0.0;
	LowHealthK = Ease(LowHealthK, KTarget, 0.3, Dt);

	Mix.bPaused = State == TEXT("paused");
	Mix.Interior = Interior;
	Mix.Muffle = Muffle;
	Mix.VoiceDuck = VoiceAmt;
	const double MuffleHz = 20000.0 * FMath::Pow(0.03, MI::Clamp01(Muffle));
	const double LowHz = FMath::Lerp(20000.0, Num(Low, TEXT("cutoff"), 3200.0), LowHealthK);
	Mix.MuffleCutoff = FMath::Min(MuffleHz, LowHz);
	Mix.MusicCutoff = Mix.bPaused ? Num(Pause, TEXT("musicCutoff"), 1300.0) : 20000.0;
	// The street ambience darkens indoors (the shop's walls): 20 kHz outside, 1.6 kHz fully inside.
	Mix.AmbienceCutoff = 20000.0 * FMath::Pow(Num(Obj(MixT, TEXT("ambienceLowpass")), TEXT("base"), 0.08), MI::Clamp01(Interior));

	for (const auto& Pair : Data->Categories)
	{
		const FMIAudioCategory& C = Pair.Value;
		double Opt = 1.0;
		if (C.Option == TEXT("effects")) Opt = Options.Effects;
		else if (C.Option == TEXT("ambience")) Opt = Options.Ambience;
		else if (C.Option == TEXT("music")) Opt = Options.Music;
		else if (C.Option == TEXT("ui")) Opt = Options.UI;
		else if (C.Option == TEXT("voice")) Opt = Options.Voice.Volume;
		double G = C.Volume * Opt * Options.Master;
		if (C.Name == TEXT("ambience"))
		{
			G *= AmbDuck * TrainDuck * AmbStateNow * (1.0 - 0.55 * Interior) * (Mix.bPaused ? 0.0 : 1.0);
			G *= 1.0 - (1.0 - Num(Low, TEXT("ambience"), 0.7)) * LowHealthK;
		}
		else if (C.Name == TEXT("music"))
		{
			G *= MusDuck * (0.6 + 0.4 * TrainDuck) * MusicDip * (Mix.bPaused ? Num(Pause, TEXT("musicGain"), 0.45) : 1.0);
			G *= 1.0 - (1.0 - Num(Low, TEXT("music"), 0.75)) * LowHealthK;
		}
		if (VoiceData && C.Name != TEXT("voice") && C.Name != TEXT("ui"))
		{
			const double F = VoiceData->Settings.Duck.Contains(C.Name) ? VoiceData->Settings.Duck[C.Name] : 1.0;
			G *= 1.0 - (1.0 - F) * VoiceAmt;
		}
		Mix.Gain.Add(C.Name, G);
	}

	// The reverb zone: the shop when inside, under the El within its box (with its fade), else the street.
	FName Reverb = NAME_None;
	double Best = 0.0;
	const FVector W = MI::Web::FromUnreal(Listener);
	for (const FMIAudioZone& Z : Data->Zones)
	{
		if (Z.bDefault)
		{
			if (Reverb.IsNone())
			{
				Reverb = Z.Preset;
			}
			continue;
		}
		if (!Z.Box.IsValid)
		{
			continue;
		}
		const double D = FMath::Sqrt(Z.Box.ComputeSquaredDistanceToPoint(W));
		const double K = MI::Clamp01(1.0 - D / FMath::Max(Z.Fade, 0.01)) + (Z.bInterior ? 0.01 : 0.0);
		if (K > 0.5 && K > Best)
		{
			Best = K;
			Reverb = Z.Preset;
		}
	}
	Mix.Reverb = Reverb;
}

// --------------------------------------------------------------------------------------------------- the clock

void FMIAudioDirector::Tick(double Dt)
{
	if (!Data)
	{
		return;
	}
	Clock += Dt;
	if (State != TEXT("paused"))
	{
		GameClock += Dt;
	}

	// Scheduled commands whose time has come, in time order.
	Pending.StableSort([](const FMIAudioCmd& A, const FMIAudioCmd& B) { return A.Time < B.Time; });
	int32 Due = 0;
	while (Due < Pending.Num() && Pending[Due].Time <= Clock + 1e-9)
	{
		++Due;
	}
	if (Due > 0)
	{
		Ready.Append(Pending.GetData(), Due);
		Pending.RemoveAt(0, Due);
	}
	for (auto It = Live.CreateIterator(); It; ++It)
	{
		if (It->Value.End < Clock - 0.5)
		{
			It.RemoveCurrent();
		}
	}

	// The last tail of a burst comes back up (spec 07 3.20).
	for (int32 I = 0; I < Raises.Num(); ++I)
	{
		if (Raises[I].Serial != ShotSerial)
		{
			Raises.RemoveAt(I--);
		}
		else if (Clock >= Raises[I].At)
		{
			// Only if they were not pushed down by a newer shot (the serial says so) and are still the current ones.
			SetInstance(Raises[I].TailOut, Raises[I].Out);
			SetInstance(Raises[I].TailIn, Raises[I].In);
			TailK = 1.0;
			Raises.RemoveAt(I--);
		}
	}

	// Hit grunts, unless the same hit killed (spec 07 3.25).
	for (int32 I = 0; I < PendingGrunts.Num(); ++I)
	{
		if (!KilledNow.Contains(PendingGrunts[I].Key))
		{
			FPlayArgs A;
			A.b3D = true;
			if (const FTracked* T = Enemies.Find(PendingGrunts[I].Key))
			{
				A.Pos = T->Pos;
			}
			Play(TEXT("grunt_hit"), A);
		}
	}
	PendingGrunts.Reset();
	KilledNow.Reset();

	// The voice: triggers, rules, and the lines that start now.
	if (VoiceData && State != TEXT("paused"))
	{
		Triggers.Tick(GameClock);
		TArray<FMIVoicePlay> Plays;
		Voice.Tick(GameClock, Plays);
		static FMISoundDef VoiceDef = []()
		{
			FMISoundDef D;
			D.Name = TEXT("voice");
			D.Category = TEXT("voice");
			D.Priority = 9;
			D.Jitter = 0.0;
			return D;
		}();
		for (const FMIVoicePlay& P : Plays)
		{
			if (P.bInterrupt)
			{
				StopInstance(VoiceLine, 0.08);
			}
			FPlayArgs A;
			const FString File = FString::Printf(TEXT("Voice/%s/%s"), *P.Character.ToString(), *P.File);
			VoiceLine = FInstance();
			VoiceLine.Ids.Add(StartFile(VoiceDef, File, P.Secs, P.Volume, A, 1.0));
			VoiceLine.Base.Add(P.Volume);
			if (P.bBleep)
			{
				SetInstance(VoiceLine, 0.0, P.BleepStart);
				SetInstance(VoiceLine, 1.0, P.BleepEnd);
				FPlayArgs B;
				B.Delay = P.BleepStart;
				B.Volume = 0.35 * P.Volume;
				FInstance Tone;
				Tone.Ids.Add(StartFile(VoiceDef, TEXT("Gen/bleep_1k.wav"), P.BleepEnd - P.BleepStart, B.Volume, B, 1.0));
				Tone.Base.Add(B.Volume);
				StopInstance(Tone, 0.005, P.BleepEnd);
			}
			if (Options.Voice.bSubtitles && VoiceData)
			{
				Subtitle.Speaker = P.Speaker;
				Subtitle.Text = P.Text;
				Subtitle.bPlaceholder = P.bPlaceholder;
				Subtitle.Until = Clock + FMath::Max(VoiceData->Settings.SubtitleMin, P.Secs + VoiceData->Settings.SubtitleExtra);
			}
		}
		if (Subtitle.Until >= 0.0 && Clock > Subtitle.Until)
		{
			Subtitle = FMISubtitle();
		}
	}

	UpdateLoops(Dt);
	UpdateMusic(Dt);
	UpdateAmbience(Dt);
	UpdateMix(Dt);
}

// ------------------------------------------------------------------------------------------------- the loops

void FMIAudioDirector::UpdateLoops(double Dt)
{
	const TSharedPtr<FJsonObject> RotorE = Data->Event(TEXT("enemy:spawn:buzzard"));
	const int32 Near = (int32)Num(RotorE, TEXT("near"), 6);
	const double Radius = Num(RotorE, TEXT("radius"), 90.0) * 100.0;

	// Rotors follow their Buzzards; the nearest few are heard (spec 07 3.22).
	RankTimer -= Dt;
	const bool bRank = RankTimer <= 0.0;
	if (bRank)
	{
		RankTimer = 0.25;
		TArray<TPair<double, int32>> Order;
		for (const auto& Pair : Enemies)
		{
			if (Pair.Value.bBuzzard && Pair.Value.bAlive && Pair.Value.Loop.Ids.Num() > 0)
			{
				Order.Add({FVector::Dist(Pair.Value.Pos, Listener), Pair.Key});
			}
		}
		Order.Sort([](const TPair<double, int32>& A, const TPair<double, int32>& B) { return A.Key < B.Key; });
		for (int32 I = 0; I < Order.Num(); ++I)
		{
			FTracked& T = Enemies[Order[I].Value];
			const bool bAudible = I < Near && Order[I].Key <= Radius;
			if (bAudible != T.bAudible)
			{
				T.bAudible = bAudible;
				SetInstance(T.Loop, bAudible ? 1.0 : 0.0);
			}
		}
	}

	// Goon steps (no step event on the bus: strided from the actors' movement) and rotor positions.
	const TSharedPtr<FJsonObject> GS = Data->Table(TEXT("goonSteps"));
	const double Stride = Num(GS, TEXT("stride"), 1.6) * 100.0;
	for (auto& Pair : Enemies)
	{
		FTracked& T = Pair.Value;
		const double Moved = FVector::Dist2D(T.Pos, T.LastPos);
		const double Speed = Dt > 0.0 ? Moved / Dt : 0.0;
		if (T.bBuzzard)
		{
			if (T.Loop.Ids.Num() > 0 && (Moved > 5.0 || bRank))
			{
				const double Rate = T.Tune * (0.94 + 0.3 * MI::Clamp01(Speed / 1000.0));
				SetInstance(T.Loop, T.bAudible ? 1.0 : 0.0, 0.0, Rate, &T.Pos);
			}
		}
		else if (T.bAlive && Speed > Num(GS, TEXT("minSpeed"), 1.0) * 100.0)
		{
			T.Stride += Moved;
			if (T.Stride >= Stride)
			{
				T.Stride = 0.0;
				if (FVector::Dist(T.Pos, Listener) <= Num(GS, TEXT("radius"), 45.0) * 100.0)
				{
					FPlayArgs A;
					A.b3D = true;
					A.Pos = T.Pos;
					A.Volume = Num(GS, TEXT("vol"), 0.75);
					A.Pitch = Num(GS, TEXT("pitch"), 0.88);
					const FString Fam = Str(Surface(FName(Str(GS, TEXT("surface"), TEXT("asphalt")))), TEXT("steps"), TEXT("asphalt"));
					Play(FName(FString::Printf(TEXT("step_%s_run"), *Fam)), A);
				}
			}
		}
		T.LastPos = T.Pos;
	}

	// The fuse hiss rises with the square of the burnt fraction.
	for (const auto& Pair : Fuses)
	{
		const double L = FMath::Max(0.05, FuseLength.FindRef(Pair.Key));
		const double U = MI::Clamp01((Clock - FuseStart.FindRef(Pair.Key)) / L);
		SetInstance(Pair.Value, 0.25 + 0.75 * U * U);
	}

	// The reel grab stops when its progress stops.
	if (Grab.Ids.Num() > 0 && (Clock - GrabSeen > Num(Data->Event(TEXT("hud:prompt")), TEXT("idle"), 0.3) || State != TEXT("playing")))
	{
		StopInstance(Grab, 0.08);
		Grab = FInstance();
	}

	// The heartbeat under 35 % health (spec 07 3.22).
	const TSharedPtr<FJsonObject> HB = Data->Table(TEXT("heartbeat"));
	const double Below = Num(HB, TEXT("below"), 0.35);
	const bool bBeat = bAlive && State == TEXT("playing") && Health < Below;
	if (bBeat)
	{
		const double K = MI::Clamp01((Below - Health) / Num(HB, TEXT("span"), 0.25));
		if (Heartbeat.Ids.Num() == 0)
		{
			FPlayArgs A;
			A.bLoop = true;
			Heartbeat = Play(FName(Str(HB, TEXT("sound"), TEXT("heartbeat"))), A);
		}
		SetInstance(Heartbeat, Num(HB, TEXT("vol"), 0.25) + Num(HB, TEXT("volPerK"), 0.4) * K, 0.0, Num(HB, TEXT("rate"), 1.0) + Num(HB, TEXT("ratePerK"), 0.35) * K);
	}
	else if (Heartbeat.Ids.Num() > 0)
	{
		StopInstance(Heartbeat, 0.4);
		Heartbeat = FInstance();
	}
}

void FMIAudioDirector::StopAllLoops(bool bMusicToo)
{
	for (auto& Pair : Enemies)
	{
		StopInstance(Pair.Value.Loop, 0.12);
	}
	Enemies.Reset();
	for (const auto& Pair : Fuses)
	{
		StopInstance(Pair.Value, 0.1);
	}
	Fuses.Reset();
	StopInstance(Grab, 0.08);
	Grab = FInstance();
	StopInstance(Heartbeat, 0.4);
	Heartbeat = FInstance();
	if (bMusicToo)
	{
		for (const FInstance& S : Stems)
		{
			StopInstance(S, 0.5);
		}
		Stems.Reset();
		bStemsStarted = false;
	}
}

// -------------------------------------------------------------------------------------------------- the music

void FMIAudioDirector::UpdateMusic(double Dt)
{
	using namespace MIAudioDirectorPrivate;
	const TSharedPtr<FJsonObject> M = Data->Table(TEXT("music"));
	const TArray<TSharedPtr<FJsonValue>>* Names = nullptr;
	if (!M.IsValid() || !M->TryGetArrayField(TEXT("stems"), Names))
	{
		return;
	}
	if (!bStemsStarted)
	{
		bStemsStarted = true;
		for (const TSharedPtr<FJsonValue>& N : *Names)
		{
			FPlayArgs A;
			A.bLoop = true;
			A.Volume = 1.0;
			FInstance S = Play(FName(N->AsString()), A);
			SetInstance(S, 0.0);
			Stems.Add(S);
		}
		StemGain.Init(0.0, Stems.Num());
	}

	// Intensity (spec 07 3.24): the game's target, the combat meter, easing.
	MusicMeter = FMath::Max(0.15, MusicMeter - Num(M, TEXT("meterDecay"), 0.06) * Dt);
	const double Want = MusicMode == TEXT("play") ? FMath::Max(MusicTarget, MusicMeter) : MusicMode == TEXT("title") ? 0.15 : MusicTarget;
	MusicI += (Want - MusicI) * FMath::Min(1.0, Num(M, TEXT("ease"), 2.0) * Dt);
	if (MusicMode == TEXT("dead") || MusicMode == TEXT("complete"))
	{
		MusicI = FMath::Min(MusicI, 0.2);
	}
	const double O = Smooth(0.25, 0.55, MusicI), K = Smooth(0.35, 0.60, MusicI), R = Smooth(0.75, 0.95, MusicI);
	double G[7] = {0.78 + 0.22 * O, 0.10 + 0.90 * O, 0.50 + 0.50 * O, MusicMode == TEXT("title") ? FMath::Max(K, 0.55) : K * (1.0 - 0.1 * R), R, 0.9 * R, 0.60 - 0.30 * O};
	if (MusicMode == TEXT("dead"))
	{
		for (double& X : G)
		{
			X = 0.0;
		}
		G[3] = 0.16;
		G[6] = 0.55;
	}
	// The stem bus (stings duck it).
	if (Clock >= StemBusUntil)
	{
		StemBusTarget = 1.0;
	}
	StemBus = Ease(StemBus, StemBusTarget, StemBusTarget < StemBus ? 0.06 : 0.5, Dt);
	const double Tau = MusicMode == TEXT("dead") ? Num(M, TEXT("deadGainTime"), 0.22) : Num(M, TEXT("gainTime"), 0.5);
	for (int32 I = 0; I < Stems.Num() && I < 7; ++I)
	{
		const double Next = Ease(StemGain[I], G[I], Tau, Dt);
		if (FMath::Abs(Next - StemGain[I]) > 0.002 || bStemsStarted == false)
		{
			StemGain[I] = Next;
			SetInstance(Stems[I], 0.9 * StemGain[I] * StemBus);
		}
	}
}

// ----------------------------------------------------------------------------------------------- the ambience

void FMIAudioDirector::StartBeds()
{
	const TSharedPtr<FJsonObject> Amb = Data->Table(TEXT("ambience"));
	const TSharedPtr<FJsonObject> Beds = Obj(Amb, TEXT("beds"));
	FPlayArgs A;
	A.bLoop = true;
	BedDay = Play(FName(Str(Beds, TEXT("day"), TEXT("bed_day"))), A);
	BedNight = Play(FName(Str(Beds, TEXT("night"), TEXT("bed_night"))), A);
	Wind = Play(FName(Str(Obj(Amb, TEXT("wind")), TEXT("sound"), TEXT("wind_el"))), A);
	bBedsStarted = true;
}

void FMIAudioDirector::UpdateAmbience(double Dt)
{
	using namespace MIAudioDirectorPrivate;
	const TSharedPtr<FJsonObject> Amb = Data->Table(TEXT("ambience"));
	if (!Amb.IsValid())
	{
		return;
	}
	if (!bBedsStarted)
	{
		StartBeds();
	}
	const bool bRun = State == TEXT("playing") || State == TEXT("intro");
	const FVector W = MI::Web::FromUnreal(Listener);

	// Beds and wind (spec 07 3.23).
	DayMix = MI::MoveToward(DayMix, bNight ? 0.0 : 1.0, 0.5 * Dt);
	SetInstance(BedDay, DayMix);
	SetInstance(BedNight, 1.0 - DayMix);
	const TSharedPtr<FJsonObject> WindT = Obj(Amb, TEXT("wind"));
	GustTimer -= Dt;
	if (GustTimer <= 0.0)
	{
		const FVector2D Every = Range(WindT, TEXT("gustEvery"), 6.0);
		GustTimer = Rng.FRandRange(Every.X, Every.Y);
		GustTarget = Rng.FRandRange(Num(WindT, TEXT("gustMin"), 0.15), 1.0);
	}
	Gust = MI::MoveToward(Gust, GustTarget, 0.5 * Dt);
	const double ElDist = FMath::Max(0.0, FMath::Max(FMath::Abs(W.X) - 46.0, FMath::Abs(W.Z) - 5.4));
	const double NearEl = MI::Clamp01(1.0 - ElDist / Num(WindT, TEXT("near"), 25.0));
	SetInstance(Wind, (0.35 + 0.25 * (1.0 - DayMix)) * (0.45 + 0.75 * NearEl) * (0.3 + 0.7 * Gust), 0.0, 0.9 + 0.22 * Gust);

	// Far one-shots on their timers (spec 07 2.14), only while a run is on.
	if (bRun && State != TEXT("paused"))
	{
		const TSharedPtr<FJsonObject> Sch = Obj(Amb, TEXT("schedule"));
		for (auto& Pair : FarTimers)
		{
			Pair.Value -= Dt;
			if (Pair.Value > 0.0)
			{
				continue;
			}
			const TSharedPtr<FJsonObject> E = Obj(Sch, *Pair.Key.ToString());
			Pair.Value = Rng.FRandRange(Num(E, TEXT("min"), 20), Num(E, TEXT("max"), 60));
			const FString Place = Str(E, TEXT("place"), TEXT("far"));
			const double Yaw = Rng.FRandRange(0.0, 2.0 * PI);
			FVector Off;
			if (Place == TEXT("street"))
			{
				Off = FVector((Rng.FRand() < 0.5 ? -1 : 1) * Rng.FRandRange(45, 105), 1.5, Rng.FRandRange(-12, 12));
			}
			else if (Place == TEXT("roof"))
			{
				const double R = Rng.FRandRange(9, 27);
				Off = FVector(FMath::Cos(Yaw) * R, Rng.FRandRange(7, 16), FMath::Sin(Yaw) * R);
			}
			else
			{
				const double R = Rng.FRandRange(60, 150);
				Off = FVector(FMath::Cos(Yaw) * R, Rng.FRandRange(2, 16), FMath::Sin(Yaw) * R);
			}
			FPlayArgs A;
			A.b3D = true;
			A.Pos = Listener + MI::Web::ToUnreal(Off);
			A.Volume = Rng.FRandRange(0.75, 1.0);
			A.Pitch = Pair.Key == TEXT("siren_far") && Rng.FRand() < 0.3 ? 0.92 : 1.0;
			Play(Pair.Key, A);
		}
	}

	// The El train: a pass every 40..70 s (spec 07 3.23).
	const TSharedPtr<FJsonObject> Tr = Obj(Amb, TEXT("train"));
	const double Ap = Num(Tr, TEXT("approach"), 8.8), Ov = Num(Tr, TEXT("over"), 10.4), Go = Num(Tr, TEXT("gone"), 8.8);
	double DuckTarget = 1.0;
	if (TrainT < 0.0)
	{
		if (bRun)
		{
			TrainTimer -= Dt;
		}
		if (TrainTimer <= 0.0 && bRun)
		{
			TrainT = 0.0;
			TrainTrack = Rng.FRand() < 0.5 ? 0 : 1;
			bSquealDone = Rng.FRand() >= Num(Tr, TEXT("squealChance"), 0.7);
			SquealAt = Ap + Ov * Rng.FRandRange(0.2, 0.6);
			FPlayArgs A;
			A.bLoop = true;
			A.b3D = true;
			A.Pos = Listener;
			A.Volume = 0.0;
			TrainRumble = Play(TEXT("train_rumble"), A);
			TrainClack = Play(TEXT("train_clack"), A);
		}
	}
	else
	{
		TrainT += Dt;
		const double Total = Ap + Ov + Go;
		const TArray<TSharedPtr<FJsonValue>>* Tracks = nullptr;
		double TrackZ = TrainTrack == 0 ? 2.1 : -2.1;
		if (Tr->TryGetArrayField(TEXT("tracks"), Tracks) && Tracks->IsValidIndex(TrainTrack))
		{
			TrackZ = (*Tracks)[TrainTrack]->AsNumber();
		}
		const double Sign = TrainTrack == 0 ? 1.0 : -1.0;
		const double Centre = Sign * FMath::Lerp(-130.0, 130.0, MI::Clamp01(TrainT / Total));
		const FVector P = MI::Web::ToUnreal(FVector(FMath::Clamp(W.X, Centre - 40.0, Centre + 40.0), Num(Tr, TEXT("railY"), 6.83), TrackZ));
		double Rumble, Clack;
		if (TrainT < Ap)
		{
			const double U = TrainT / Ap;
			Rumble = 0.2 + 0.8 * U;
			Clack = Rumble * U;
			DuckTarget = 1.0 - 0.2 * U;
		}
		else if (TrainT < Ap + Ov)
		{
			Rumble = Clack = 1.0;
			DuckTarget = Num(Tr, TEXT("duckOver"), 0.72);
		}
		else
		{
			const double U = MI::Clamp01((TrainT - Ap - Ov) / Go);
			Rumble = Clack = 1.0 - U;
			DuckTarget = 0.8 + 0.2 * U;
		}
		SetInstance(TrainRumble, Rumble, 0.0, -1.0, &P);
		SetInstance(TrainClack, Clack, 0.0, -1.0, &P);
		if (!bSquealDone && TrainT >= SquealAt)
		{
			bSquealDone = true;
			FPlayArgs A;
			A.b3D = true;
			A.Pos = P;
			A.Volume = 0.8;
			Play(TEXT("train_squeal"), A);
		}
		if (TrainT >= Total)
		{
			StopInstance(TrainRumble, 1.2);
			StopInstance(TrainClack, 0.8);
			TrainRumble = TrainClack = FInstance();
			TrainT = -1.0;
			const FVector2D Every = Range(Tr, TEXT("every"), 55);
			TrainTimer = Rng.FRandRange(Every.X, Every.Y);
		}
	}
	TrainDuck = MI::MoveToward(TrainDuck, DuckTarget, 1.5 * Dt);
}

// --------------------------------------------------------------------------------------------------- the bus

void FMIAudioDirector::OnWeaponFire(const FMIShotFiredEvent& E)
{
	const TSharedPtr<FJsonObject> R = Data->Event(TEXT("weapon:fire"));
	const FName W = SoundFamily(E.Weapon);  // a gun without sounds of its own fires with its family's
	const bool bSup = Suppressed.Contains(E.Weapon) || E.bSuppressed;  // the loadout's silencer, per gun or on the round
	const FName Silenced(*FString::Printf(TEXT("%s_shot_silenced"), *W.ToString()));
	FPlayArgs Shot;
	Play(bSup && Data->Find(Silenced) ? Silenced : FName(*FString::Printf(TEXT("%s_shot"), *W.ToString())), Shot);

	// The tails, split by the interior factor, with the burst rule.
	const double Since = Clock - LastShot;
	const double Gap = Num(R, TEXT("tailGap"), 0.45);
	const double Floor = Num(R, TEXT("tailFloor"), 0.4);
	const double K = Since < Gap ? Floor + (1.0 - Floor) * Since / Gap : 1.0;
	// The earlier tails are pushed down to pushDown x k of their full level (they started at their own k).
	const double Push = Num(R, TEXT("pushDown"), 0.25) * K / FMath::Max(1e-6, TailK);
	SetInstance(TailOut, Push);
	SetInstance(TailIn, Push);
	const double Sup = bSup ? 0.35 : 1.0;
	const double Out = FMath::Cos(Interior * HALF_PI) * Sup, In = FMath::Sin(Interior * HALF_PI) * Sup;
	TailOut = TailIn = FInstance();
	if (Out > 0.05)
	{
		FPlayArgs A;
		A.Volume = Out * K;
		TailOut = Play(FName(*FString::Printf(TEXT("%s_tail_out"), *W.ToString())), A);
	}
	if (In > 0.05)
	{
		FPlayArgs A;
		A.Volume = In * K;
		TailIn = Play(FName(*FString::Printf(TEXT("%s_tail_in"), *W.ToString())), A);
	}
	TailK = K;
	++ShotSerial;
	if (K < 1.0)
	{
		// 105 ms later, if no newer shot came, the burst's last tail comes up to full.
		FRaise Raise;
		Raise.Serial = ShotSerial;
		Raise.At = Clock + Num(R, TEXT("raiseAfter"), 0.105);
		Raise.TailOut = TailOut;
		Raise.TailIn = TailIn;
		Raise.Out = 1.0 / K;
		Raise.In = 1.0 / K;
		Raises.Add(Raise);
	}
	LastShot = Clock;
	Duck(TEXT("gunfire"), W);
	Meter(Num(R, TEXT("meter"), 0.012));

	// The spent case lands at the player's feet a moment later.
	const TSharedPtr<FJsonObject> Brass = Obj(R, TEXT("brass"));
	if (Brass.IsValid() && Rng.FRand() < Num(Brass, TEXT("chance"), 0.85))
	{
		const TSharedPtr<FJsonObject> S = Surface(PlayerSurface);
		const FVector2D Delay = Range(Brass, TEXT("delay"), 0.5);
		FPlayArgs A;
		A.b3D = true;
		A.Pos = Listener + FVector(ListenerForward.Y * 40.0, -ListenerForward.X * 40.0, -150.0);
		A.Delay = Rng.FRandRange(Delay.X, Delay.Y);
		const bool bNine = W == TEXT("nine");
		A.Volume = (bNine ? Num(Brass, TEXT("nineVol"), 0.8) : Num(Brass, TEXT("vol"), 0.9)) * Num(S, TEXT("brassVol"), 1.0);
		A.Pitch = (bNine ? Num(Brass, TEXT("ninePitch"), 1.22) : 1.0) * Num(S, TEXT("brassPitch"), 1.0);
		Play(FName(Str(S, TEXT("brass"), TEXT("brass_asphalt"))), A);
	}
}

void FMIAudioDirector::OnWeaponDry(FName Weapon)
{
	PlayEntry(Data->Event(TEXT("weapon:dry")), Weapon, nullptr, {});
}

void FMIAudioDirector::OnWeaponReload(const FMIReloadEvent& E)
{
	const bool bPistol = E.Weapon == TEXT("nine");
	const TMap<FString, FString> Vars = {
		{TEXT("weapon"), E.Weapon.ToString()},
		{TEXT("rifleOrPistol"), bPistol ? TEXT("pistol") : TEXT("rifle")},
		{TEXT("boltOrSlide"), bPistol ? TEXT("pistol_slide") : TEXT("rifle_bolt")}};
	PlayEntry(Data->Event(FName(*FString::Printf(TEXT("weapon:reload:%s"), *E.Phase.ToString()))), E.Weapon, nullptr, Vars);
}

void FMIAudioDirector::OnWeaponSwitch(const FMISwitchEvent& E)
{
	const bool bHolster = E.Phase == TEXT("holster");
	PlayEntry(Data->Event(bHolster ? FName(TEXT("weapon:switch:holster")) : FName(TEXT("weapon:switch:draw"))), bHolster ? E.From : E.To, nullptr, {});
}

void FMIAudioDirector::OnWeaponSwing(FName Weapon)
{
	PlayEntry(Data->Event(TEXT("weapon:swing")), Weapon, nullptr, {});
}

void FMIAudioDirector::OnWeaponMode(FName Weapon, bool bSemi)
{
	PlayEntry(Data->Event(TEXT("weapon:mode")), Weapon, nullptr, {});
}

void FMIAudioDirector::OnWeaponMelee(bool bHit)
{
	PlayEntry(Data->Event(bHit ? FName(TEXT("weapon:melee:hit")) : FName(TEXT("weapon:melee:miss"))), NAME_None, nullptr, {});
}

void FMIAudioDirector::OnImpact(const FMIImpactEvent& E)
{
	const TSharedPtr<FJsonObject> R = Data->Event(TEXT("impact"));
	const TSharedPtr<FJsonObject> S = Surface(E.Surface);
	const bool bBody = E.Surface == TEXT("flesh") || E.Surface == TEXT("drone");
	FPlayArgs A;
	A.b3D = true;
	A.Pos = E.Point;
	A.Pitch = Num(S, TEXT("pitch"), 1.0);
	A.Volume = bBody ? Num(R, TEXT("volBody"), 1.0) : (E.From == EMIDamageSource::Player ? Num(R, TEXT("volPlayer"), 0.9) : Num(R, TEXT("volEnemy"), 0.8));
	Play(FName(Str(S, TEXT("impact"), TEXT("imp_concrete"))), A);
	if (!bBody && Rng.FRand() < Num(S, TEXT("ricochet"), 0.0))
	{
		FPlayArgs Ric = A;
		Ric.Pitch = 1.0;
		Ric.Delay = Num(R, TEXT("ricochetDelay"), 0.012);
		Ric.Volume = Num(R, TEXT("ricochetVol"), 0.8);
		Play(TEXT("ricochet"), Ric);
	}
}

void FMIAudioDirector::OnHitEnemy(const FMIHitEnemyEvent& E)
{
	const TCHAR* Key = E.bKilled ? TEXT("player:hitEnemy:kill") : (E.Part == TEXT("head") ? TEXT("player:hitEnemy:head") : TEXT("player:hitEnemy:body"));
	PlayEntry(Data->Event(Key), E.Weapon, nullptr, {});
}

void FMIAudioDirector::OnExplosion(const FMIExplosionEvent& E)
{
	const TSharedPtr<FJsonObject> R = Data->Event(E.bBig ? FName(TEXT("explosion:big")) : FName(TEXT("explosion:small")));
	FPlayArgs A;
	A.b3D = true;
	A.Pos = E.Position;
	Play(FName(Str(R, TEXT("sound"), E.bBig ? TEXT("explosion_big") : TEXT("explosion_small"))), A);
	const TArray<TSharedPtr<FJsonValue>>* Layers = nullptr;
	if (R.IsValid() && R->TryGetArrayField(TEXT("layers"), Layers))
	{
		for (const TSharedPtr<FJsonValue>& L : *Layers)
		{
			Play(FName(L->AsString()), A);
		}
	}
	Duck(*Str(R, TEXT("duck"), TEXT("blastBig")));
	const TSharedPtr<FJsonObject> Mu = Obj(Data->Table(TEXT("mix")), TEXT("muffle"));
	const double D = FVector::Dist(E.Position, Listener) / 100.0;
	const double Near = Num(Mu, TEXT("blastNear"), 5.0), Far = Num(Mu, TEXT("blastFar"), 20.0);
	const double F = MI::Clamp01(1.0 - (D - Near) / FMath::Max(0.01, Far - Near));
	if (F > 0.0)
	{
		MuffleTo(Num(Mu, *Str(R, TEXT("muffle"), TEXT("blastBig")), 0.8) * F);
	}
	Meter(0.0, 0.6);
}

void FMIAudioDirector::OnExplosiveLit(int32 Index, const FVector& Pos, double Fuse)
{
	const TSharedPtr<FJsonObject> R = Data->Event(TEXT("explosive:lit"));
	FPlayArgs A;
	A.b3D = true;
	A.Pos = Pos;
	A.bLoop = true;
	A.Volume = 1.0;
	StopInstance(Fuses.FindRef(Index), 0.05);
	FInstance I = Play(FName(Str(R, TEXT("sound"), TEXT("hiss"))), A);
	SetInstance(I, Num(R, TEXT("from"), 0.25));
	Fuses.Add(Index, I);
	FuseStart.Add(Index, Clock);
	FuseLength.Add(Index, Fuse);
}

void FMIAudioDirector::OnExplosiveBlast(int32 Index, const FVector& Centre)
{
	if (const FInstance* I = Fuses.Find(Index))
	{
		StopInstance(*I, 0.03);
		Fuses.Remove(Index);
	}
}

void FMIAudioDirector::OnPlayerStep(const FMIPlayerStepEvent& E)
{
	const TSharedPtr<FJsonObject> R = Data->Event(TEXT("player:step"));
	const TSharedPtr<FJsonObject> S = Surface(E.Surface);
	PlayerSurface = E.Surface.IsNone() ? PlayerSurface : E.Surface;
	const TSharedPtr<FJsonObject> P = Obj(R, E.bSprint ? TEXT("run") : TEXT("walk"));
	FPlayArgs A;
	A.Volume = Num(P, TEXT("vol"), 0.55);
	A.Pitch = Num(P, TEXT("pitch"), 1.0);
	Play(FName(*FString::Printf(TEXT("step_%s%s"), *Str(S, TEXT("steps"), TEXT("concrete")), E.bSprint ? TEXT("_run") : TEXT(""))), A);
}

void FMIAudioDirector::OnPlayerJump()
{
	PlayEntry(Data->Event(TEXT("player:jump")), NAME_None, nullptr, {});
}

void FMIAudioDirector::OnPlayerLand(const FMIPlayerLandEvent& E)
{
	const TSharedPtr<FJsonObject> R = Data->Event(TEXT("player:land"));
	const double V = FMath::Clamp(Num(R, TEXT("base"), 0.35) + Num(R, TEXT("perSpeed"), 0.1) * E.Speed / 100.0, 0.35, 1.0);
	FPlayArgs A;
	A.Volume = V;
	Play(TEXT("land"), A);
	const TSharedPtr<FJsonObject> S = Surface(E.Surface);
	A.Volume = V * Num(R, TEXT("stepVol"), 0.6);
	A.Pitch = Num(R, TEXT("stepPitch"), 0.92);
	Play(FName(*FString::Printf(TEXT("step_%s_run"), *Str(S, TEXT("steps"), TEXT("concrete")))), A);
}

void FMIAudioDirector::OnPlayerHit(const FMIPlayerHitEvent& E)
{
	const TSharedPtr<FJsonObject> R = Data->Event(TEXT("player:hit"));
	FPlayArgs A;
	A.Volume = FMath::Clamp(0.5 + E.Amount / 40.0, 0.5, 1.0);
	A.Pitch = E.Kind == EMIDamageKind::Blast ? Num(R, TEXT("blastPitch"), 0.85) : 1.0;
	Play(TEXT("hurt"), A);
	if (E.Amount >= Num(R, TEXT("ringFrom"), 8.0))
	{
		FPlayArgs Ring;
		Ring.Volume = FMath::Clamp(E.Amount / 28.0, 0.3, 1.0);
		Play(TEXT("ear_ring"), Ring);
	}
	const TSharedPtr<FJsonObject> Mu = Obj(Data->Table(TEXT("mix")), TEXT("muffle"));
	MuffleTo(FMath::Clamp(E.Amount * Num(Mu, TEXT("hitPerDamage"), 0.025), Num(Mu, TEXT("hitMin"), 0.2), Num(Mu, TEXT("hitMax"), 0.7)));
	Meter(Num(R, TEXT("meter"), 0.15));
	if (VoiceData)
	{
		Triggers.OnPlayerHit(E, GameClock);
	}
}

void FMIAudioDirector::OnPlayerDead(const TOptional<FVector>& From)
{
	const TSharedPtr<FJsonObject> Mu = Obj(Data->Table(TEXT("mix")), TEXT("muffle"));
	MuffleTo(Num(Mu, TEXT("dead"), 1.0), Num(Mu, TEXT("deadFloor"), 0.85));
	bAlive = false;
	if (VoiceData)
	{
		Triggers.OnPlayerDead(GameClock);
	}
}

FName FMIAudioDirector::EnemyKey(const FMIEnemyEvent& E)
{
	using namespace MIAudioDirectorPrivate;
	if (E.Kind == FMIEnemyEvent::EKind::Melee)
	{
		return E.Phase == TEXT("strike") ? FName(TEXT("enemy:melee:strike")) : FName(TEXT("enemy:melee:windup"));
	}
	return FName(*FString::Printf(TEXT("enemy:%s:%s"), KindName(E.Kind), E.Type == MIEnemy::EType::Goon ? TEXT("goon") : TEXT("buzzard")));
}

void FMIAudioDirector::OnEnemy(const FMIEnemyEvent& E)
{
	if (VoiceData)
	{
		Triggers.OnEnemy(E, GameClock);
	}
	const FName Key = EnemyKey(E);
	const TSharedPtr<FJsonObject> R = Data->Event(Key);
	const FVector Pos = Web(E.Pos);
	const bool bBuzzard = E.Type == MIEnemy::EType::Buzzard;
	FTracked& T = Enemies.FindOrAdd(E.Id);
	T.bBuzzard = bBuzzard;
	if (!T.bHasPos)
	{
		T.Pos = T.LastPos = Pos;
		T.bHasPos = true;
	}

	switch (E.Kind)
	{
	case FMIEnemyEvent::EKind::Spawn:
		T.bAlive = true;
		T.Pos = T.LastPos = Pos;
		if (bBuzzard && T.Loop.Ids.Num() == 0)
		{
			const FVector2D Tune = Range(R, TEXT("tune"), 1.0);
			T.Tune = Rng.FRandRange(Tune.X, Tune.Y);
			FPlayArgs A;
			A.bLoop = true;
			A.b3D = true;
			A.Pos = Pos;
			T.Loop = Play(FName(Str(R, TEXT("sound"), TEXT("rotor"))), A);
			T.bAudible = true;
		}
		break;
	case FMIEnemyEvent::EKind::Telegraph:
		if (bBuzzard)
		{
			FPlayArgs A;
			A.b3D = true;
			A.Pos = Pos;
			A.Pitch = FMath::Clamp(0.5 / FMath::Max(0.05, E.Duration), 0.6, 2.0);
			Play(FName(Str(R, TEXT("sound"), TEXT("buzzard_charge"))), A);
			Meter(0.0, Num(R, TEXT("meter"), 0.6));
		}
		else
		{
			PlayEntry(R, NAME_None, &Pos, {});
		}
		break;
	case FMIEnemyEvent::EKind::Fire:
	{
		FPlayArgs A;
		A.b3D = true;
		A.Pos = Pos;
		Play(FName(Str(R, TEXT("sound"), bBuzzard ? TEXT("bolt_shot") : TEXT("smg_shot"))), A);
		Duck(*Str(R, TEXT("duck"), TEXT("enemyFire")));
		Meter(Num(R, TEXT("meter"), 0.04));
		// Near miss (spec 07 3.21).
		const FVector Dir = FVector(E.Dir.X, E.Dir.Z, E.Dir.Y).GetSafeNormal();
		const double Along = FVector::DotProduct(Listener - Pos, Dir);
		if (Along >= 200.0 && !Dir.IsNearlyZero())
		{
			const FVector Closest = Pos + Dir * Along;
			const double D = FVector::Dist(Closest, Listener);
			if (D <= 320.0 && D >= 25.0 && !(Blocked && Blocked(Pos, Closest)))
			{
				FPlayArgs Wz;
				Wz.b3D = true;
				Wz.Pos = Closest;
				Wz.Volume = FMath::Clamp(1.15 - D / 350.0, 0.3, 1.0);
				Wz.Delay = Flag(R, TEXT("whizzDelay"), false) ? FMath::Min(1.5, Along / (Num(R, TEXT("boltSpeed"), 70.0) * 100.0)) : 0.0;
				Play(TEXT("whizz"), Wz);
			}
		}
		break;
	}
	case FMIEnemyEvent::EKind::Hit:
		if (!bBuzzard)
		{
			PendingGrunts.Add({E.Id, Clock});
		}
		break;
	case FMIEnemyEvent::EKind::Killed:
		KilledNow.Add(E.Id);
		T.bAlive = false;
		if (bBuzzard)
		{
			StopInstance(T.Loop, 0.12);
			T.Loop = FInstance();
		}
		PlayEntry(R, NAME_None, &Pos, {});
		break;
	default:
		PlayEntry(R, NAME_None, &Pos, {});
		break;
	}
}

void FMIAudioDirector::OnFlow(const FMIFlowEvent& E)
{
	const FName N = E.Name;
	if (VoiceData)
	{
		Triggers.OnFlow(E, GameClock);
	}
	if (N == TEXT("game:state"))
	{
		const FName Prev = State;
		State = FName(E.Text);
		const TSharedPtr<FJsonObject> Amb = Obj(Data->Table(TEXT("mix")), TEXT("ambienceState"));
		AmbState = Num(Amb, *E.Text, 1.0);
		if (State == TEXT("title"))
		{
			MusicMode = TEXT("title");
			MuffleFloor = 0.0;
			Muffle = 0.0;
		}
		else if (State == TEXT("intro") || State == TEXT("playing"))
		{
			if (Prev != TEXT("paused"))
			{
				MuffleFloor = 0.0;
				Muffle = 0.0;
				MusicMode = TEXT("play");
				bAlive = true;
			}
		}
	}
	else if (N == TEXT("objective:done"))
	{
		if (E.Text != TEXT("wave"))
		{
			Play(FName(Str(Data->Event(N), TEXT("sound"), TEXT("reel_secure"))), FPlayArgs());
		}
	}
	else if (N == TEXT("audio:sting"))
	{
		const TSharedPtr<FJsonObject> R = Data->Event(N);
		const FString Sting = Str(Obj(R, TEXT("stings")), *E.Text);
		if (!Sting.IsEmpty())
		{
			Play(FName(Sting), FPlayArgs());
		}
		const FVector2D StingDuck = Range(Obj(Data->Table(TEXT("music")), TEXT("stingDuck")), *E.Text, 1.0);
		StemBusTarget = StingDuck.X;
		StemBusUntil = Clock + StingDuck.Y;
		if (E.Text == TEXT("dead"))
		{
			MusicMode = TEXT("dead");
		}
		else if (E.Text == TEXT("complete"))
		{
			MusicMode = TEXT("complete");
		}
	}
	else if (N == TEXT("explosives:reset"))
	{
		for (const auto& Pair : Fuses)
		{
			StopInstance(Pair.Value, 0.1);
		}
		Fuses.Reset();
	}
	else if (N == TEXT("player:reset"))
	{
		StopAllLoops(false);
		MuffleFloor = 0.0;
		Muffle = 0.0;
		bAlive = true;
	}
	else if (N == TEXT("hud:radio"))
	{
		const TSharedPtr<FJsonObject> R = Data->Event(N);
		Play(FName(Str(R, TEXT("in"), TEXT("radio_in"))), FPlayArgs());
		FPlayArgs Out;
		Out.Delay = FMath::Clamp(E.A, Num(R, TEXT("minHold"), 0.6), Num(R, TEXT("maxHold"), 12.0));
		Play(FName(Str(R, TEXT("out"), TEXT("radio_out"))), Out);
	}
	else if (N == TEXT("ui:click") || N == TEXT("ui:hover"))
	{
		// The menus' own sounds (the web game's ui:click on every press, ui:hover on every focus move).
		PlayEntry(Data->Event(N), NAME_None, nullptr, {});
	}
	else if (N == TEXT("hud:prompt"))
	{
		if (E.A >= 0.0 && !E.Text.IsEmpty())
		{
			const TSharedPtr<FJsonObject> R = Data->Event(N);
			if (Grab.Ids.Num() == 0)
			{
				FPlayArgs A;
				A.bLoop = true;
				A.Volume = Num(R, TEXT("vol"), 0.8);
				Grab = Play(FName(Str(R, TEXT("sound"), TEXT("reel_grab"))), A);
				for (double& B : Grab.Base) { B = 1.0; }
			}
			SetInstance(Grab, Num(R, TEXT("vol"), 0.8), 0.0, Num(R, TEXT("pitchBase"), 0.85) + Num(R, TEXT("pitchPerProgress"), 0.4) * MI::Clamp01(E.A));
			GrabSeen = Clock;
		}
	}
}

void FMIAudioDirector::OnMusicIntensity(double Intensity)
{
	MusicTarget = Intensity;
}

TArray<TPair<FName, FString>> FMIAudioDirector::BusDelegates()
{
	return {
		{TEXT("Enemy"), TEXT("enemy:*")}, {TEXT("Flow"), TEXT("<flow lines>")}, {TEXT("MusicIntensity"), TEXT("music:intensity")},
		{TEXT("WeaponFire"), TEXT("weapon:fire")}, {TEXT("WeaponDry"), TEXT("weapon:dry")}, {TEXT("WeaponReload"), TEXT("weapon:reload:*")},
		{TEXT("WeaponSwitch"), TEXT("weapon:switch:*")}, {TEXT("WeaponSwing"), TEXT("weapon:swing")}, {TEXT("WeaponMode"), TEXT("weapon:mode")},
		{TEXT("WeaponMelee"), TEXT("weapon:melee:*")},
		{TEXT("Impact"), TEXT("impact")}, {TEXT("PlayerHitEnemy"), TEXT("player:hitEnemy:*")}, {TEXT("Explosion"), TEXT("explosion:*")},
		{TEXT("ExplosiveLit"), TEXT("explosive:lit")}, {TEXT("ExplosiveBlast"), TEXT("explosive:blast")}, {TEXT("PlayerStep"), TEXT("player:step")},
		{TEXT("PlayerJump"), TEXT("player:jump")}, {TEXT("PlayerLand"), TEXT("player:land")}, {TEXT("PlayerHit"), TEXT("player:hit")},
		{TEXT("PlayerDead"), TEXT("player:dead")}};
}

TArray<FName> FMIAudioDirector::BusEventKeys()
{
	TArray<FName> K;
	for (const TCHAR* S : {
		TEXT("weapon:fire"), TEXT("weapon:dry"),
		TEXT("weapon:reload:start"), TEXT("weapon:reload:magout"), TEXT("weapon:reload:magin"), TEXT("weapon:reload:bolt"), TEXT("weapon:reload:done"), TEXT("weapon:reload:cancel"),
		TEXT("weapon:switch:holster"), TEXT("weapon:switch:draw"), TEXT("weapon:swing"), TEXT("weapon:mode"), TEXT("weapon:melee:hit"), TEXT("weapon:melee:miss"),
		TEXT("impact"), TEXT("player:hitEnemy:body"), TEXT("player:hitEnemy:head"), TEXT("player:hitEnemy:kill"),
		TEXT("explosion:big"), TEXT("explosion:small"), TEXT("explosive:lit"), TEXT("explosive:blast"),
		TEXT("player:step"), TEXT("player:jump"), TEXT("player:land"), TEXT("player:hit"), TEXT("player:dead"),
		TEXT("enemy:melee:windup"), TEXT("enemy:melee:strike"), TEXT("music:intensity")})
	{
		K.Add(S);
	}
	for (const TCHAR* Kind : {TEXT("spawn"), TEXT("alert"), TEXT("telegraph"), TEXT("fire"), TEXT("hit"), TEXT("killed")})
	{
		for (const TCHAR* Type : {TEXT("goon"), TEXT("buzzard")})
		{
			K.Add(FName(*FString::Printf(TEXT("enemy:%s:%s"), Kind, Type)));
		}
	}
	// The flow's lines as FMIGameRules emits them (the test also scans the source for new ones).
	for (const TCHAR* S : {
		TEXT("game:state"), TEXT("objective:done"), TEXT("objective:all"), TEXT("holdout:wave"), TEXT("extraction:reached"), TEXT("audio:sting"),
		TEXT("player:heal"), TEXT("weapon:reserve"), TEXT("explosives:reset"), TEXT("player:reset"), TEXT("menus:card"),
		TEXT("hud:radio"), TEXT("hud:message"), TEXT("hud:warn"), TEXT("hud:reels"), TEXT("hud:tally"), TEXT("hud:objective"), TEXT("hud:prompt"),
		TEXT("enemy:spawn"), TEXT("enemy:killed"), TEXT("score:best"), TEXT("ui:click"), TEXT("ui:hover")})
	{
		K.Add(S);
	}
	return K;
}
