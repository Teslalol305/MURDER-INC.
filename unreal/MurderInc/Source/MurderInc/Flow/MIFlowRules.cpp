#include "Flow/MIFlowRules.h"

#include "Core/Data/MIDataSubsystem.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Enemies/MIEnemyLogic.h"

// ------------------------------------------------------------------------------------------------- formulas

namespace
{
	/** Recursive descent over the arithmetic the config's arrow functions use: + - * / ( ) Math.min/max/floor/round/abs. */
	struct FExpr
	{
		const FString& S;
		int32 I = 0;
		double Arg = 0;
		bool bOk = true;

		void Skip()
		{
			while (I < S.Len() && FChar::IsWhitespace(S[I]))
			{
				++I;
			}
		}
		bool Eat(TCHAR C)
		{
			Skip();
			if (I < S.Len() && S[I] == C)
			{
				++I;
				return true;
			}
			return false;
		}
		double Primary()
		{
			Skip();
			if (Eat(TEXT('(')))
			{
				const double V = Sum();
				bOk &= Eat(TEXT(')'));
				return V;
			}
			if (Eat(TEXT('-')))
			{
				return -Primary();
			}
			if (I < S.Len() && (FChar::IsDigit(S[I]) || S[I] == TEXT('.')))
			{
				const int32 Start = I;
				while (I < S.Len() && (FChar::IsDigit(S[I]) || S[I] == TEXT('.') || S[I] == TEXT('e')))
				{
					++I;
				}
				return FCString::Atod(*S.Mid(Start, I - Start));
			}
			const int32 Start = I;
			while (I < S.Len() && (FChar::IsAlnum(S[I]) || S[I] == TEXT('.') || S[I] == TEXT('_')))
			{
				++I;
			}
			const FString Name = S.Mid(Start, I - Start);
			if (Name.StartsWith(TEXT("Math.")))
			{
				TArray<double> Args;
				bOk &= Eat(TEXT('('));
				if (!Eat(TEXT(')')))
				{
					do
					{
						Args.Add(Sum());
					} while (Eat(TEXT(',')));
					bOk &= Eat(TEXT(')'));
				}
				const FString F = Name.Mid(5);
				if (Args.Num() == 0)
				{
					bOk = false;
					return 0;
				}
				if (F == TEXT("min")) { double V = Args[0]; for (double A : Args) V = FMath::Min(V, A); return V; }
				if (F == TEXT("max")) { double V = Args[0]; for (double A : Args) V = FMath::Max(V, A); return V; }
				if (F == TEXT("floor")) return FMath::FloorToDouble(Args[0]);
				if (F == TEXT("round")) return FMath::FloorToDouble(Args[0] + 0.5);
				if (F == TEXT("abs")) return FMath::Abs(Args[0]);
				bOk = false;
				return 0;
			}
			if (Name.IsEmpty())
			{
				bOk = false;
				return 0;
			}
			return Arg;  // the one parameter
		}
		double Product()
		{
			double V = Primary();
			for (;;)
			{
				if (Eat(TEXT('*'))) V *= Primary();
				else if (Eat(TEXT('/'))) V /= Primary();
				else return V;
			}
		}
		double Sum()
		{
			double V = Product();
			for (;;)
			{
				if (Eat(TEXT('+'))) V += Product();
				else if (Eat(TEXT('-'))) V -= Product();
				else return V;
			}
		}
	};
}

double FMIFormula::Eval(double Arg) const
{
	const int32 Arrow = Source.Find(TEXT("=>"));
	const FString Body = Arrow >= 0 ? Source.Mid(Arrow + 2) : Source;
	FExpr E{Body};
	E.Arg = Arg;
	const double V = E.Sum();
	return E.bOk ? V : 0.0;
}

FMIFormula FMIFormula::From(const TSharedPtr<FJsonValue>& V)
{
	FMIFormula F;
	const TSharedPtr<FJsonObject>* O;
	const TSharedPtr<FJsonObject>* Fn;
	if (V.IsValid() && V->TryGetObject(O) && (*O)->TryGetObjectField(TEXT("$function"), Fn))
	{
		F.Source = (*Fn)->GetStringField(TEXT("source"));
	}
	else if (V.IsValid() && V->Type == EJson::Number)
	{
		F.Source = FString::SanitizeFloat(V->AsNumber());
	}
	return F;
}

// --------------------------------------------------------------------------------------------------- tables

namespace
{
	struct FReader
	{
		TSharedPtr<FJsonObject> Root;
		FString Missing;
		TSharedPtr<FJsonValue> Find(const FString& Path)
		{
			TArray<FString> Parts;
			Path.ParseIntoArray(Parts, TEXT("."));
			TSharedPtr<FJsonValue> V = MakeShared<FJsonValueObject>(Root);
			for (const FString& P : Parts)
			{
				if (!V.IsValid())
				{
					break;
				}
				if (V->Type == EJson::Array)
				{
					const TArray<TSharedPtr<FJsonValue>>& A = V->AsArray();
					const int32 K = FCString::Atoi(*P);
					V = A.IsValidIndex(K) ? A[K] : nullptr;
				}
				else if (V->Type == EJson::Object)
				{
					V = V->AsObject()->TryGetField(P);
				}
				else
				{
					V = nullptr;
				}
			}
			if (!V.IsValid() && Missing.IsEmpty())
			{
				Missing = Path;
			}
			return V;
		}
		double N(const FString& Path) { TSharedPtr<FJsonValue> V = Find(Path); return V.IsValid() ? V->AsNumber() : 0.0; }
		int32 I(const FString& Path) { return static_cast<int32>(N(Path)); }
	};
}

const FMIFlowDifficulty& FMIFlowTune::Difficulty(FName Name) const
{
	const FMIFlowDifficulty* D = Difficulties.Find(Name);
	return D ? *D : Difficulties.FindChecked(DefaultDifficulty);
}

bool FMIFlowTune::Parse(const TSharedPtr<FJsonObject>& Config, FMIFlowTune& O, FString& OutError)
{
	FReader R{Config};
	O.Intro = R.N(TEXT("flow.timing.intro"));
	O.IntroQuick = R.N(TEXT("flow.timing.introQuick"));
	O.IntroFadeA = R.N(TEXT("flow.timing.introFade.0"));
	O.IntroFadeB = R.N(TEXT("flow.timing.introFade.1"));
	O.LocationCardAt = R.N(TEXT("flow.timing.locationCardAt"));
	O.IntroRadioAt = R.N(TEXT("flow.timing.introRadioAt"));
	O.PauseDebounce = R.N(TEXT("flow.timing.pauseDebounce"));
	O.DeathCard = R.N(TEXT("flow.timing.deathCard"));
	O.DebriefCard = R.N(TEXT("flow.timing.debriefCard"));
	O.DeadSat = R.N(TEXT("flow.post.dead.saturation.0"));
	O.DeadSatRate = R.N(TEXT("flow.post.dead.saturation.1"));
	O.DeadFade = R.N(TEXT("flow.post.dead.fade.0"));
	O.DeadFadeRate = R.N(TEXT("flow.post.dead.fade.1"));
	O.DoneSat = R.N(TEXT("flow.post.complete.saturation.0"));
	O.DoneSatRate = R.N(TEXT("flow.post.complete.saturation.1"));
	O.DoneFade = R.N(TEXT("flow.post.complete.fade.0"));
	O.DoneFadeRate = R.N(TEXT("flow.post.complete.fade.1"));
	O.InteractRange = R.N(TEXT("flow.interact.range"));
	O.InteractVertical = R.N(TEXT("flow.interact.vertical"));
	O.FacingDot = R.N(TEXT("flow.interact.facingDot"));
	O.FreeRange = R.N(TEXT("flow.interact.freeRange"));
	O.Hold = R.N(TEXT("flow.interact.hold"));
	O.Decay = R.N(TEXT("flow.interact.decay"));
	O.InteractShake = R.N(TEXT("flow.interact.shake"));
	O.ExtractVertical = R.N(TEXT("flow.extraction.vertical"));
	O.RefuseSecs = R.N(TEXT("flow.extraction.refuseSecs"));
	O.RefuseEvery = R.N(TEXT("flow.extraction.refuseEvery"));
	O.FirstDelay = R.N(TEXT("flow.spawn.firstDelay"));
	O.Stagger = R.N(TEXT("flow.spawn.stagger"));
	O.Far = R.N(TEXT("flow.spawn.far"));
	O.PatrolMinDistance = R.N(TEXT("flow.spawn.patrolMinDistance"));
	O.ScoreRandom = R.N(TEXT("flow.spawn.score.random"));
	O.ScoreFar = R.N(TEXT("flow.spawn.score.far"));
	O.ScoreFarExtra = R.N(TEXT("flow.spawn.score.farExtra"));
	O.ScoreFarExtraOver = R.N(TEXT("flow.spawn.score.farExtraOver"));
	O.ScoreNearDivisor = R.N(TEXT("flow.spawn.score.nearDivisor"));
	O.ScoreHidden = R.N(TEXT("flow.spawn.score.hidden"));
	O.ScoreRecent = R.N(TEXT("flow.spawn.score.recent"));
	O.ScoreRecentSecs = R.N(TEXT("flow.spawn.score.recentSecs"));
	O.Jitter = R.N(TEXT("flow.spawn.jitter"));
	O.AirMinHeight = R.N(TEXT("flow.spawn.airMinHeight"));
	O.AirLiftA = R.N(TEXT("flow.spawn.airLift.0"));
	O.AirLiftB = R.N(TEXT("flow.spawn.airLift.1"));
	O.EyeHeight = R.N(TEXT("flow.spawn.eyeHeight"));
	O.ProbeHeight = R.N(TEXT("flow.spawn.probeHeight"));
	O.TooClose = R.N(TEXT("flow.spawn.tooClose"));
	O.CapRetry = R.N(TEXT("flow.spawn.capRetry"));
	O.PoolRetry = R.N(TEXT("flow.spawn.poolRetry"));
	O.PoolTries = R.I(TEXT("flow.spawn.poolTries"));
	O.AlertRadius = R.N(TEXT("flow.spawn.alertRadius"));
	O.FallbackRing = R.N(TEXT("flow.spawn.fallbackRing"));
	O.BannerSecs = R.N(TEXT("flow.spawn.bannerSecs"));
	O.PursuitFirstDelay = R.N(TEXT("flow.pursuit.firstDelay"));
	O.PursuitMinAlive = R.I(TEXT("flow.pursuit.minAlive"));
	O.PursuitSpawnDelay = R.N(TEXT("flow.pursuit.spawnDelay"));
	O.PursuitBuzzardShare = R.N(TEXT("flow.pursuit.buzzardShare"));
	O.PursuitRealertEvery = R.N(TEXT("flow.pursuit.realertEvery"));
	O.PursuitRealertRadius = R.N(TEXT("flow.pursuit.realertRadius"));
	O.HoldFirstDelay = R.N(TEXT("flow.holdout.firstDelay"));
	O.Breather = R.N(TEXT("flow.holdout.breather"));
	O.CountdownFrom = R.I(TEXT("flow.holdout.countdownFrom"));
	O.FirstSpawn = R.N(TEXT("flow.holdout.firstSpawn"));
	O.HoldBannerSecs = R.N(TEXT("flow.holdout.bannerSecs"));
	O.HoldRealertEvery = R.N(TEXT("flow.holdout.realertEvery"));
	O.HoldRealertRadius = R.N(TEXT("flow.holdout.realertRadius"));
	O.Total = FMIFormula::From(R.Find(TEXT("flow.holdout.total")));
	O.BuzzardShare = FMIFormula::From(R.Find(TEXT("flow.holdout.buzzardShare")));
	O.StaggerOf = FMIFormula::From(R.Find(TEXT("flow.holdout.stagger")));
	O.HpScale = FMIFormula::From(R.Find(TEXT("flow.holdout.hpScale")));
	O.DamageScale = FMIFormula::From(R.Find(TEXT("flow.holdout.damageScale")));
	O.CooldownScale = FMIFormula::From(R.Find(TEXT("flow.holdout.cooldownScale")));
	O.ExtraAlive = FMIFormula::From(R.Find(TEXT("flow.holdout.extraAlive")));
	O.KillScale = FMIFormula::From(R.Find(TEXT("flow.holdout.score.killScale")));
	O.WaveClear = FMIFormula::From(R.Find(TEXT("flow.holdout.score.waveClear")));
	O.KillGoon = R.N(TEXT("flow.holdout.score.goon"));
	O.KillBuzzard = R.N(TEXT("flow.holdout.score.buzzard"));
	O.ResupplyReserve = R.N(TEXT("flow.holdout.resupply.reserve"));
	O.ResupplyReserveCap = R.N(TEXT("flow.holdout.resupply.reserveCap"));
	O.ResupplyHeal = R.N(TEXT("flow.holdout.resupply.heal"));
	O.ExplosivesEvery = R.I(TEXT("flow.holdout.resupply.explosivesEvery"));
	for (const FString Table : {FString(TEXT("time")), FString(TEXT("accuracy"))})
	{
		if (TSharedPtr<FJsonValue> V = R.Find(TEXT("flow.rating.") + Table))
		{
			for (const TSharedPtr<FJsonValue>& Row : V->AsArray())
			{
				(Table == TEXT("time") ? O.RatingTime : O.RatingAccuracy).Add({Row->AsArray()[0]->AsNumber(), static_cast<int32>(Row->AsArray()[1]->AsNumber())});
			}
		}
	}
	O.RatingNoRetries = R.I(TEXT("flow.rating.noRetries"));
	O.MusicCalm = R.N(TEXT("flow.music.calm"));
	O.MusicAlert = R.N(TEXT("flow.music.alert"));
	O.MusicHot = R.N(TEXT("flow.music.hot"));
	O.AlertHold = R.N(TEXT("flow.music.alertHold"));
	O.HitHold = R.N(TEXT("flow.music.hitHold"));
	O.NearDistance = R.N(TEXT("flow.music.nearDistance"));
	O.WaveHot = R.N(TEXT("flow.music.waveHot"));
	O.WaveMinOut = R.N(TEXT("flow.music.waveMinOut"));
	O.RadioCharsPerSec = R.N(TEXT("flow.pacing.radioCharsPerSec"));
	O.CountdownSecs = R.N(TEXT("flow.pacing.countdownSecs"));
	O.RadioGap = R.N(TEXT("flow.pacing.radioGap"));
	O.LowWarning = R.N(TEXT("player.health.lowWarning"));
	if (TSharedPtr<FJsonValue> V = R.Find(TEXT("flow.defaultDifficulty")))
	{
		O.DefaultDifficulty = FName(V->AsString());
	}
	if (TSharedPtr<FJsonValue> V = R.Find(TEXT("flow.difficulty")))
	{
		for (const auto& Pair : V->AsObject()->Values)
		{
			const FString Key(*Pair.Key);
			FMIFlowDifficulty D;
			const FString P = TEXT("flow.difficulty.") + Key;
			D.RegenDelay = R.N(P + TEXT(".regen.delay"));
			D.RegenRate = R.N(P + TEXT(".regen.rate"));
			D.PatrolBuzzard = R.I(P + TEXT(".patrol.buzzard"));
			D.PatrolGoon = R.I(P + TEXT(".patrol.goon"));
			for (const TSharedPtr<FJsonValue>& W : R.Find(P + TEXT(".waves"))->AsArray())
			{
				D.Waves.Add({static_cast<int32>(W->AsObject()->GetNumberField(TEXT("buzzard"))), static_cast<int32>(W->AsObject()->GetNumberField(TEXT("goon")))});
			}
			D.MaxAlive = R.I(P + TEXT(".maxAlive"));
			D.PursuitEvery = R.N(P + TEXT(".pursuitEvery"));
			D.PursuitBudget = R.I(P + TEXT(".pursuitBudget"));
			O.Difficulties.Add(FName(Key), D);
		}
	}
	if (!R.Missing.IsEmpty() || !O.Difficulties.Contains(O.DefaultDifficulty) || O.Total.Source.IsEmpty())
	{
		OutError = FString::Printf(TEXT("config.json flow: %s is missing"), R.Missing.IsEmpty() ? TEXT("a difficulty or the holdout formulas") : *R.Missing);
		return false;
	}
	return true;
}

// ----------------------------------------------------------------------------------------------------- text

bool FMIText::Load(FMIText& Out, FString& OutError)
{
	TSharedPtr<FJsonObject> Root;
	if (!UMIDataSubsystem::LoadJsonFile(TEXT("text.json"), Root, OutError))
	{
		return false;
	}
	const TSharedPtr<FJsonObject>* Text;
	if (!Root->TryGetObjectField(TEXT("text"), Text))
	{
		OutError = TEXT("text.json has no `text` deck");
		return false;
	}
	Out.Root = *Text;
	return true;
}

FString FMIText::Get(const FString& Path) const
{
	FReader R{Root};
	TSharedPtr<FJsonValue> V = R.Find(Path);
	return V.IsValid() && V->Type == EJson::String ? V->AsString() : FString();
}

double FMIText::Secs(const FString& Path) const
{
	FReader R{Root};
	TSharedPtr<FJsonValue> V = R.Find(Path);
	return V.IsValid() && V->Type == EJson::Number ? V->AsNumber() : 0.0;
}

int32 FMIText::Count(const FString& Path) const
{
	FReader R{Root};
	TSharedPtr<FJsonValue> V = R.Find(Path);
	return V.IsValid() && V->Type == EJson::Array ? V->AsArray().Num() : 0;
}

FString FMIText::Format(const FString& Path, const TMap<FString, FString>& Args) const
{
	FReader R{Root};
	TSharedPtr<FJsonValue> V = R.Find(Path + TEXT(".$template.template"));
	FString Out = V.IsValid() ? V->AsString() : Get(Path);
	for (const auto& A : Args)
	{
		Out.ReplaceInline(*FString::Printf(TEXT("{%s}"), *A.Key), *A.Value, ESearchCase::CaseSensitive);
	}
	return Out;
}

FString FMIText::Grouped(double X)
{
	const int64 N = static_cast<int64>(FMath::FloorToDouble(X + 0.5));
	FString Digits = FString::Printf(TEXT("%lld"), N < 0 ? -N : N);
	for (int32 I = Digits.Len() - 3; I > 0; I -= 3)
	{
		Digits.InsertAt(I, TEXT(','));
	}
	return N < 0 ? TEXT("-") + Digits : Digits;
}

// ---------------------------------------------------------------------------------------------------- rules

namespace MIFlow
{
	int32 CompassSector(double Dx, double Dz)
	{
		// Math.round: half up.
		const int32 Sector = static_cast<int32>(FMath::FloorToDouble(FMath::Atan2(Dx, 0.0 - Dz) / (UE_DOUBLE_PI / 4.0) + 0.5));
		return ((Sector % 8) + 8) % 8;
	}

	double SpawnScore(const FMISpawnCandidate& C, const FMIFlowTune& T, double MinDistance)
	{
		double Score = C.Random * T.ScoreRandom;
		if (C.Distance >= MinDistance)
		{
			const double Over = FMath::Min(1.0, (C.Distance - MinDistance) / T.ScoreFarExtraOver);
			Score += T.ScoreFar + T.ScoreFarExtra * Over;
		}
		else
		{
			Score -= (MinDistance - C.Distance) / T.ScoreNearDivisor;
		}
		if (C.bHidden)
		{
			Score += T.ScoreHidden;
		}
		if (C.UsedAgo < T.ScoreRecentSecs)
		{
			Score += T.ScoreRecent;
		}
		return Score;
	}

	TArray<FName> MissionOrder(int32 B, int32 G)
	{
		B = FMath::Max(0, B);
		G = FMath::Max(0, G);
		TArray<FName> Order;
		while (B > 0 || G > 0)
		{
			if (B > 0)
			{
				Order.Add(TEXT("buzzard"));
				--B;
			}
			if (G > 0)
			{
				Order.Add(TEXT("goon"));
				--G;
			}
		}
		return Order;
	}

	TArray<FName> HoldoutOrder(int32 Total, int32 Buzzards)
	{
		const int32 N = FMath::Max(0, Total);
		const int32 B = FMath::Min(N, FMath::Max(0, Buzzards));
		TArray<FName> Order;
		Order.Init(TEXT("goon"), N);
		for (int32 I = 0; I < B; ++I)
		{
			int32 Slot = FMath::Min(N - 1, 1 + static_cast<int32>(FMath::FloorToDouble(static_cast<double>(I) * N / B)));
			while (Order[Slot] == FName(TEXT("buzzard")))
			{
				Slot = (Slot + 1) % N;
			}
			Order[Slot] = TEXT("buzzard");
		}
		return Order;
	}

	FHoldoutWave HoldoutWave(int32 N, const FMIFlowTune& T)
	{
		FHoldoutWave W;
		W.Wave = FMath::Max(1, N);
		W.Total = static_cast<int32>(T.Total.Eval(W.Wave));
		W.Buzzards = FMath::Min(W.Total, static_cast<int32>(FMath::FloorToDouble(W.Total * T.BuzzardShare.Eval(W.Wave) + 0.5)));
		W.Goons = W.Total - W.Buzzards;
		W.Order = HoldoutOrder(W.Total, W.Buzzards);
		W.Stagger = T.StaggerOf.Eval(W.Wave);
		W.Hp = T.HpScale.Eval(W.Wave);
		W.Damage = T.DamageScale.Eval(W.Wave);
		W.Cooldown = T.CooldownScale.Eval(W.Wave);
		W.ExtraAlive = static_cast<int32>(T.ExtraAlive.Eval(W.Wave));
		return W;
	}

	int32 KillScore(bool bGoon, int32 Wave, const FMIFlowTune& T)
	{
		return static_cast<int32>(FMath::FloorToDouble((bGoon ? T.KillGoon : T.KillBuzzard) * T.KillScale.Eval(FMath::Max(1, Wave)) + 0.5));
	}

	int32 RatingPoints(double Time, int32 Shots, int32 Hits, int32 Retries, const FMIFlowTune& T)
	{
		int32 Points = 0;
		for (const auto& Row : T.RatingTime)
		{
			if (Time < Row.Key)
			{
				Points += Row.Value;
				break;
			}
		}
		const double Acc = Shots > 0 ? static_cast<double>(Hits) / Shots : 0.0;
		for (const auto& Row : T.RatingAccuracy)
		{
			if (Acc >= Row.Key)
			{
				Points += Row.Value;
				break;
			}
		}
		if (!Retries)
		{
			Points += T.RatingNoRetries;
		}
		return Points;
	}

	double MusicIntensity(const FMusicState& S, const FMIFlowTune& T)
	{
		if (S.bAllDone || S.Queued > 0 || (S.WaveAge < T.WaveHot && S.Alive > 0))
		{
			return T.MusicHot;
		}
		if (S.SinceAlert < T.AlertHold || S.SinceHit < T.HitHold || S.Nearest < T.NearDistance)
		{
			return T.MusicAlert;
		}
		return T.MusicCalm;
	}
}

// ---------------------------------------------------------------------------------------------------- radio

void FMIRadio::Say(const FString& Text, double Secs)
{
	if (Text.IsEmpty())
	{
		return;
	}
	Queue.Add({Text, Secs > 0 ? Secs : 0.0});
}

void FMIRadio::Clear()
{
	Queue.Reset();
	Busy = 0;
	Current.Reset();
}

void FMIRadio::Update(double Dt)
{
	CurrentAge += Dt;
	if (Busy > 0)
	{
		Busy -= Dt;
		if (Busy > 0)
		{
			return;
		}
	}
	if (Queue.Num() == 0)
	{
		Busy = 0;
		Current.Reset();
		return;
	}
	const FLine Line = Queue[0];
	Queue.RemoveAt(0);
	Busy = Line.Text.Len() / CharsPerSec + Line.Secs + Gap;
	Current = Line.Text;
	CurrentSecs = Line.Secs;
	CurrentAge = 0;
	if (OnLine)
	{
		OnLine(Line.Text, Line.Secs);
	}
}
