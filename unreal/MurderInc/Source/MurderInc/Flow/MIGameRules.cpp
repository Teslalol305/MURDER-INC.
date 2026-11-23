#include "Flow/MIGameRules.h"

// src/game.js, function by function (the comments explaining each rule are there). The browser-only parts (pointer
// lock, look-mode hints, the title fly-through camera, the DOM listeners) are the host's business.

using MI::Web::Hypot;

namespace
{
	const FName NMission(TEXT("mission"));
	const FName NHoldout(TEXT("holdout"));
	const FName NBuzzard(TEXT("buzzard"));
	const FName NGoon(TEXT("goon"));

	const TCHAR* StateName(EMIGameState S)
	{
		switch (S)
		{
		case EMIGameState::Title: return TEXT("title");
		case EMIGameState::Intro: return TEXT("intro");
		case EMIGameState::Playing: return TEXT("playing");
		case EMIGameState::Paused: return TEXT("paused");
		case EMIGameState::Dead: return TEXT("dead");
		default: return TEXT("complete");
		}
	}

	double SmoothStep(double E0, double E1, double X)
	{
		const double T = MI::Clamp01((X - E0) / (E1 - E0));
		return T * T * (3.0 - 2.0 * T);
	}
}

void FMIGameRules::Init(const FMIFlowTune& InTune, const FMIText& InText, const FMILevelData* InLevel, FMIBoxWorld* InWorld, FMIEnemyField* InEnemies, IMIGameHost* InHost, const FMIRng& Root)
{
	Tune = InTune;
	Text = InText;
	Level = InLevel;
	World = InWorld;
	Enemies = InEnemies;
	Host = InHost;
	Rng = Root.Fork(TEXT("game"));
	Difficulty = Tune.DefaultDifficulty;
	Radio.CharsPerSec = Tune.RadioCharsPerSec;
	Radio.Gap = Tune.RadioGap;
	Radio.OnLine = [this](const FString& Line, double Secs) { Note(TEXT("hud:radio"), Line, Secs); };
	ApplyDifficulty();
	ViewState.Fade = 1;
	SetState(EMIGameState::Title);
}

void FMIGameRules::Note(FName Name, const FString& InText, double A, double B, double C)
{
	FMIFlowEvent& E = PendingEvents.AddDefaulted_GetRef();
	E.Name = Name;
	E.Text = InText;
	E.A = A;
	E.B = B;
	E.C = C;
}

void FMIGameRules::Message(const FString& Line, double Secs)
{
	ViewState.Message = Line;
	ViewState.MessageLeft = Secs;
	Note(TEXT("hud:message"), Line, Secs);
}

void FMIGameRules::Warn(const FString& Line, double Secs)
{
	ViewState.Warn = Line;
	ViewState.WarnLeft = Secs;
	Note(TEXT("hud:warn"), Line, Secs);
}

void FMIGameRules::Say(const FString& Path, const TMap<FString, FString>* Args)
{
	const FString Line = Args ? Text.Format(Path + TEXT(".text"), *Args) : Text.Get(Path + TEXT(".text"));
	Radio.Say(Line, Text.Secs(Path + TEXT(".secs")));
}

void FMIGameRules::Hush()
{
	Radio.Clear();
}

// ---------------------------------------------------------------------------------------------- state machine

void FMIGameRules::SetState(EMIGameState Next)
{
	State = Next;
	StateTime = 0;
	bCardShown = false;
	const bool bActive = Next == EMIGameState::Playing || Next == EMIGameState::Intro;
	if (Next != EMIGameState::Dead && Next != EMIGameState::Complete)
	{
		CardShown.Reset();
	}
	if (!bActive)
	{
		ShowPrompt(nullptr, 0);
	}
	Note(TEXT("game:state"), StateName(Next));
}

void FMIGameRules::ApplyWaveScale()
{
	if (Mode == NHoldout && Run.Wave > 0)
	{
		const MIFlow::FHoldoutWave W = MIFlow::HoldoutWave(Run.Wave, Tune);
		Enemies->SetScale(W.Hp, W.Damage, W.Cooldown);
		MaxAlive = Diff.MaxAlive + W.ExtraAlive;
	}
	else
	{
		Enemies->SetScale(1, 1, 1);
		MaxAlive = Diff.MaxAlive;
	}
}

void FMIGameRules::ApplyDifficulty()
{
	if (!Tune.Difficulties.Contains(Difficulty))
	{
		Difficulty = Tune.DefaultDifficulty;
	}
	Diff = Tune.Difficulty(Difficulty);
	if (const FMIEnemyTune* T = Host ? Host->EnemyTune(Difficulty) : nullptr)
	{
		Enemies->SetTune(*T);
	}
	ApplyWaveScale();
	if (Host)
	{
		Host->SetRegen(Diff.RegenDelay, Diff.RegenRate);
	}
}

void FMIGameRules::SetDifficulty(FName Name)
{
	Difficulty = Tune.Difficulties.Contains(Name) ? Name : Tune.DefaultDifficulty;
	ApplyDifficulty();
}

void FMIGameRules::Reset()
{
	const bool bStory = Mode == NMission;
	Queue.Reset();
	LastUsed.Reset();
	Secured.Reset();
	Clock = 0;
	GrabTarget = INDEX_NONE;
	GrabProgress = 0;
	RefusedAt = -MIEnemy::Inf;
	bSaidContact = bSaidLow = false;
	PursuitLeft = 0;
	PursuitTimer = 0;
	WaveAge = SinceAlert = SinceHit = MIEnemy::Inf;
	bHoldoutActive = false;
	BreakLeft = Tune.HoldFirstDelay;
	Countdown = 0;
	Cleared = 0;
	RealertIn = 0;
	const int32 Retries = Run.Retries;
	Run = FRun();
	Run.Retries = Retries;
	Run.Total = Level ? Level->Objectives.Num() : 3;

	Hush();
	Enemies->Clear();
	ApplyDifficulty();
	if (Host)
	{
		Host->ResetCombat();
		Host->ResetExplosives();
		Note(TEXT("explosives:reset"));
		Host->ResetPlayer(Level ? Level->PlayerStart.Pos : FVector::ZeroVector, Level ? Level->PlayerStart.Yaw : 0.0);
	}
	if (Level)
	{
		Player.Pos = Level->PlayerStart.Pos;
	}
	Player.bAlive = true;
	Player.Health = 100;
	Note(TEXT("player:reset"));
	bPromptOn = false;
	const double Music = ViewState.Music;
	ViewState = FMIFlowView();
	ViewState.Music = Music;
	ViewState.ReelsTotal = Run.Total;
	ViewState.Saturation = 1;
	if (bStory)
	{
		ViewState.Reels = 0;
		Note(TEXT("hud:reels"), FString(), 0, Run.Total);
		SpawnPatrol();
	}
	else
	{
		ViewState.Tally = Text.Get(TEXT("objectives.tally.standby"));
		Note(TEXT("hud:tally"), ViewState.Tally);
	}
	RefreshObjective();
}

void FMIGameRules::Begin(FName InMode, bool bSkipIntro, bool bQuick)
{
	if (InMode == NMission || InMode == NHoldout)
	{
		Mode = InMode;
	}
	Reset();
	if (bSkipIntro)
	{
		ViewState.Fade = 0;
		SetState(EMIGameState::Playing);
		return;
	}
	IntroLength = bQuick ? Tune.IntroQuick : Tune.Intro;
	bFullIntro = !bQuick;
	bIntroCard = bIntroRadio = false;
	ViewState.Fade = 1;
	SetState(EMIGameState::Intro);
}

void FMIGameRules::Start(FName InMode, bool bSkipIntro)
{
	Run.Retries = 0;
	Begin(InMode, bSkipIntro, false);
}

void FMIGameRules::Restart()
{
	Run.Retries++;
	Begin(Mode, false, true);
}

void FMIGameRules::Redeploy()
{
	Run.Retries = 0;
	Begin(Mode, false, true);
}

void FMIGameRules::Pause()
{
	if (State != EMIGameState::Playing && State != EMIGameState::Intro)
	{
		return;
	}
	if (State == EMIGameState::Intro)
	{
		FinishIntro();
	}
	SetState(EMIGameState::Paused);
}

void FMIGameRules::Resume()
{
	if (State != EMIGameState::Paused)
	{
		return;
	}
	SetState(EMIGameState::Playing);
}

void FMIGameRules::ToTitle()
{
	Queue.Reset();
	if (Host && Level)
	{
		Host->ResetPlayer(Level->PlayerStart.Pos, Level->PlayerStart.Yaw);
	}
	Hush();
	Enemies->Clear();
	ViewState.Markers.Reset();
	ViewState.Saturation = 1;
	ViewState.Fade = 1;
	ViewState.bLocationCard = false;
	SetState(EMIGameState::Title);
}

void FMIGameRules::FinishIntro()
{
	ViewState.bLocationCard = false;
	ViewState.Fade = 0;
	SetState(EMIGameState::Playing);
}

// ------------------------------------------------------------------------------------------------- HUD lines

void FMIGameRules::RefreshObjective()
{
	if (Mode == NMission)
	{
		const int32 N = Text.Count(TEXT("objectives.mission"));
		ViewState.Objective = Text.Get(FString::Printf(TEXT("objectives.mission.%d"), FMath::Min(Run.Reels, N - 1)));
		Note(TEXT("hud:objective"), ViewState.Objective);
		ViewState.Markers.Reset();
		if (Level)
		{
			for (int32 I = 0; I < Level->Objectives.Num(); ++I)
			{
				if (!Secured.Contains(I))
				{
					const FMILevelObjective& O = Level->Objectives[I];
					ViewState.Markers.Add({O.Id, O.Code, O.Label, O.Pos, false});
				}
			}
			if (AllSecured())
			{
				const FMILevelObjective& X = Level->Extraction;
				ViewState.Markers.Add({TEXT("extraction"), X.Code, X.Label, X.Pos, true});
			}
		}
	}
	else
	{
		ViewState.Objective = Text.Get(bHoldoutActive ? TEXT("objectives.holdout.hold") : (Run.Wave == 0 ? TEXT("objectives.holdout.inbound") : TEXT("objectives.holdout.breather")));
		Note(TEXT("hud:objective"), ViewState.Objective);
		ViewState.Markers.Reset();
		RefreshTally();
	}
}

void FMIGameRules::RefreshTally()
{
	if (Run.Wave > 0)
	{
		ViewState.Tally = Text.Format(TEXT("objectives.tally.wave"), {{TEXT("n"), FString::FromInt(Run.Wave)}, {TEXT("score"), FMIText::Grouped(Run.Score)}});
	}
	else
	{
		ViewState.Tally = Text.Get(TEXT("objectives.tally.standby"));
	}
	Note(TEXT("hud:tally"), ViewState.Tally);
}

void FMIGameRules::ShowPrompt(const FString* Line, double Progress)
{
	if (!Line && !bPromptOn)
	{
		return;
	}
	bPromptOn = Line != nullptr;
	ViewState.Prompt = Line ? *Line : FString();
	ViewState.PromptProgress = Progress;
	Note(TEXT("hud:prompt"), ViewState.Prompt, Line ? Progress : -1.0);
}

// -------------------------------------------------------------------------------------------------- spawning

bool FMIGameRules::ChoosePosition(FName Type, double MinDistance, bool bStrict, FVector& Out)
{
	const bool bAir = Type == NBuzzard;
	const FName Wanted = bAir ? FName(TEXT("air")) : FName(TEXT("ground"));
	const FVector P = Player.Pos;
	const FVector Eye(P.X, P.Y + Tune.EyeHeight, P.Z);
	const FMILevelPoint* Best = nullptr;
	double BestScore = -MIEnemy::Inf;
	bool bBestFar = false;
	if (Level)
	{
		for (const FMILevelPoint& Point : Level->Spawns)
		{
			if (Point.Type != Wanted)
			{
				continue;
			}
			const double Distance = Hypot(Point.Pos.X - P.X, Point.Pos.Z - P.Z);
			const bool bFar = Distance >= MinDistance;
			if (bStrict && bBestFar && !bFar)
			{
				continue;
			}
			FMISpawnCandidate C;
			C.Distance = Distance;
			FVector Probe = Point.Pos;
			if (Point.Type == FName(TEXT("ground")))
			{
				Probe.Y += Tune.ProbeHeight;
			}
			C.bHidden = !World->LineOfSight(Eye, Probe);
			const double* Used = LastUsed.Find(Point.Index);
			C.UsedAgo = Used ? Clock - *Used : MIEnemy::Inf;
			C.Random = Rng.Next();
			const double Score = MIFlow::SpawnScore(C, Tune, MinDistance);
			if (Score > BestScore || (bStrict && bFar && !bBestFar))
			{
				Best = &Point;
				BestScore = Score;
				bBestFar = bFar;
			}
		}
	}
	if (Best)
	{
		LastUsed.Add(Best->Index, Clock);
		Out = Best->Pos;
	}
	else
	{
		const double A = Rng.Range(0, UE_DOUBLE_PI * 2.0);
		const FMIBounds& B = World->GetBounds();
		Out = FVector(FMath::Min(B.MaxX - 2, FMath::Max(B.MinX + 2, P.X + FMath::Cos(A) * Tune.FallbackRing)), 0,
			FMath::Min(B.MaxZ - 2, FMath::Max(B.MinZ + 2, P.Z + FMath::Sin(A) * Tune.FallbackRing)));
		if (!bAir)
		{
			FVector Near;
			if (!World->NearestWalkable(Out.X, Out.Z, 6.0, Near))
			{
				return false;
			}
			Out = FVector(Near.X, World->GroundHeight(Near.X, Near.Z, 1), Near.Z);
		}
	}
	const double Jx = Rng.Range(-Tune.Jitter, Tune.Jitter);
	const double Jz = Rng.Range(-Tune.Jitter, Tune.Jitter);
	if (bAir)
	{
		Out.X += Jx;
		Out.Z += Jz;
		if (Out.Y < Tune.AirMinHeight)
		{
			Out.Y = Rng.Range(Tune.AirLiftA, Tune.AirLiftB);
		}
	}
	else if (World->IsWalkable(Out.X + Jx, Out.Z + Jz))
	{
		const double Y = World->GroundHeight(Out.X + Jx, Out.Z + Jz, Out.Y + 0.6);
		if (FMath::Abs(Y - Out.Y) < 0.3)
		{
			Out = FVector(Out.X + Jx, Y, Out.Z + Jz);
		}
	}
	return true;
}

void FMIGameRules::SpawnPatrol()
{
	for (const FName Type : {NBuzzard, NGoon})
	{
		const int32 N = Type == NBuzzard ? Diff.PatrolBuzzard : Diff.PatrolGoon;
		for (int32 I = 0; I < N; ++I)
		{
			FVector At;
			if (ChoosePosition(Type, Tune.PatrolMinDistance, true, At))
			{
				Enemies->SetLivePlayerPos(Player.Pos);
				Enemies->Spawn(Type == NBuzzard ? MIEnemy::EType::Buzzard : MIEnemy::EType::Goon, At);
				ForwardEnemyEvents();
			}
		}
	}
}

bool FMIGameRules::QueueWave(const TArray<FName>& Order, double FirstDelay, double Stagger, FString& OutFrom)
{
	const FVector P = Player.Pos;
	double Sx = 0, Sz = 0;
	int32 Queued = 0;
	for (int32 I = 0; I < Order.Num(); ++I)
	{
		FVector Pos;
		if (!ChoosePosition(Order[I], Tune.Far, false, Pos))
		{
			continue;
		}
		Sx += Pos.X - P.X;
		Sz += Pos.Z - P.Z;
		Queue.Add({Order[I], Clock + FirstDelay + I * Stagger, Pos, 0});
		++Queued;
	}
	if (Queued == 0)
	{
		return false;
	}
	WaveAge = 0;
	OutFrom = Text.Get(FString::Printf(TEXT("compass.%d"), MIFlow::CompassSector(Sx, Sz)));
	return true;
}

void FMIGameRules::PumpQueue()
{
	int32 Index = INDEX_NONE;
	for (int32 I = 0; I < Queue.Num(); ++I)
	{
		if (Queue[I].At <= Clock)
		{
			Index = I;
			break;
		}
	}
	if (Index == INDEX_NONE)
	{
		return;
	}
	FArrival& Next = Queue[Index];
	if (Enemies->AliveCount() >= MaxAlive)
	{
		Next.At = Clock + Tune.CapRetry;
		return;
	}
	const FVector P = Player.Pos;
	if (Next.Type != NBuzzard && Hypot(Next.Pos.X - P.X, Next.Pos.Z - P.Z) < Tune.TooClose)
	{
		ChoosePosition(Next.Type, Tune.Far, false, Next.Pos);
	}
	FMIEnemySpawnOptions O;
	O.bAlerted = true;
	O.Target = P;
	Enemies->SetLivePlayerPos(P);
	if (Enemies->Spawn(Next.Type == NBuzzard ? MIEnemy::EType::Buzzard : MIEnemy::EType::Goon, Next.Pos, O))
	{
		Queue.RemoveAt(Index);
		ForwardEnemyEvents();
		Enemies->Alert(P, Tune.AlertRadius);
		ForwardEnemyEvents();
	}
	else if (++Next.Tries >= Tune.PoolTries)
	{
		Queue.RemoveAt(Index);
	}
	else
	{
		Next.At = Clock + Tune.PoolRetry;
	}
}

// ----------------------------------------------------------------------------------------------------- story

int32 FMIGameRules::ReelInReach() const
{
	if (!Level)
	{
		return INDEX_NONE;
	}
	const double Fx = Player.Forward.X, Fz = Player.Forward.Z;
	const double FlatRaw = Hypot(Fx, Fz);
	const double Flat = FlatRaw != 0 ? FlatRaw : 1.0;
	int32 Best = INDEX_NONE;
	double BestD = MIEnemy::Inf;
	for (int32 I = 0; I < Level->Objectives.Num(); ++I)
	{
		if (Secured.Contains(I))
		{
			continue;
		}
		const FVector& O = Level->Objectives[I].Pos;
		const double Dx = O.X - Player.Pos.X, Dz = O.Z - Player.Pos.Z;
		const double D = Hypot(Dx, Dz);
		if (D > Tune.InteractRange || D >= BestD || FMath::Abs(O.Y - Player.Pos.Y) > Tune.InteractVertical)
		{
			continue;
		}
		if (D > Tune.FreeRange && (Dx * Fx + Dz * Fz) / (D * Flat) < Tune.FacingDot)
		{
			continue;
		}
		Best = I;
		BestD = D;
	}
	return Best;
}

void FMIGameRules::UpdateInteraction(double Dt, bool bHeld)
{
	const int32 Target = Player.bAlive ? ReelInReach() : INDEX_NONE;
	const bool bHolding = Target != INDEX_NONE && bHeld;
	if (bHolding)
	{
		if (GrabTarget != Target)
		{
			GrabTarget = Target;
			GrabProgress = 0;
		}
		GrabProgress = FMath::Min(1.0, GrabProgress + Dt / Tune.Hold);
	}
	else if (GrabTarget != INDEX_NONE)
	{
		GrabProgress = FMath::Max(0.0, GrabProgress - Tune.Decay * Dt);
		if (GrabProgress == 0)
		{
			GrabTarget = INDEX_NONE;
		}
	}
	if (Target != INDEX_NONE)
	{
		const FString Line = Text.Format(TEXT("prompts.grab"), {{TEXT("glyph"), TEXT("E")}, {TEXT("code"), Level->Objectives[Target].Code}});
		ShowPrompt(&Line, Target == GrabTarget ? MI::Clamp01(GrabProgress) : 0.0);
	}
	else
	{
		ShowPrompt(nullptr, 0);
	}
	if (bHolding && GrabProgress >= 1)
	{
		Secure(Target);
	}
}

void FMIGameRules::Secure(int32 O)
{
	Secured.Add(O);
	Run.Reels = Secured.Num();
	if (GrabTarget == O)
	{
		GrabTarget = INDEX_NONE;
	}
	GrabProgress = 0;
	ShowPrompt(nullptr, 0);
	ViewState.Reels = Run.Reels;
	Note(TEXT("hud:reels"), FString(), Run.Reels, Run.Total);
	if (Host)
	{
		Host->AddShake(Tune.InteractShake);
	}
	RefreshObjective();
	Note(TEXT("objective:done"), Level->Objectives[O].Id.ToString(), Run.Reels, Run.Total);

	const bool bAll = Run.Reels >= Run.Total;
	const TPair<int32, int32>& Wave = Diff.Waves[FMath::Min(Run.Reels, Diff.Waves.Num()) - 1];
	FString From;
	if (QueueWave(MIFlow::MissionOrder(Wave.Key, Wave.Value), Tune.FirstDelay, Tune.Stagger, From))
	{
		Warn(Text.Format(TEXT("banners.contact"), {{TEXT("dir"), From}}), Tune.BannerSecs);
	}
	const int32 Lines = Text.Count(TEXT("radio.reel"));
	Say(FString::Printf(TEXT("radio.reel.%d"), bAll ? Lines - 1 : FMath::Min(Run.Reels, Lines - 1) - 1));
	Note(TEXT("audio:sting"), bAll ? TEXT("all") : TEXT("reel"));
	if (bAll)
	{
		PursuitLeft = Diff.PursuitBudget;
		PursuitTimer = Tune.PursuitFirstDelay;
		Note(TEXT("objective:all"));
	}
}

void FMIGameRules::DevSecureQuietly(int32 O)
{
#if !UE_BUILD_SHIPPING
	if (!Level || !Level->Objectives.IsValidIndex(O) || Secured.Contains(O))
	{
		return;
	}
	Secured.Add(O);
	Run.Reels = Secured.Num();
	ViewState.Reels = Run.Reels;
	Note(TEXT("hud:reels"), FString(), Run.Reels, Run.Total);
	RefreshObjective();
#endif
}

void FMIGameRules::UpdatePursuit(double Dt)
{
	PursuitTimer -= Dt;
	if (PursuitTimer <= 0)
	{
		if (PursuitLeft > 0 && Queue.Num() == 0 && Enemies->AliveCount() < Tune.PursuitMinAlive)
		{
			PursuitLeft--;
			FString From;
			QueueWave({MIFlow::PursuitType(Rng.Next(), Tune.PursuitBuzzardShare)}, Tune.PursuitSpawnDelay, 0, From);
			PursuitTimer = Diff.PursuitEvery;
		}
		else
		{
			PursuitTimer = Tune.PursuitRealertEvery;
			Enemies->Alert(Player.Pos, Tune.PursuitRealertRadius);
			ForwardEnemyEvents();
		}
	}
}

void FMIGameRules::UpdateExtraction()
{
	const FMILevelObjective& X = Level->Extraction;
	if (Hypot(X.Pos.X - Player.Pos.X, X.Pos.Z - Player.Pos.Z) > Level->ExtractionRadius || FMath::Abs(X.Pos.Y - Player.Pos.Y) > Tune.ExtractVertical)
	{
		return;
	}
	if (AllSecured())
	{
		if (Player.bAlive)
		{
			Complete();
		}
	}
	else if (Clock - RefusedAt > Tune.RefuseEvery)
	{
		RefusedAt = Clock;
		Message(Text.Get(TEXT("prompts.refuse")), Tune.RefuseSecs);
	}
}

void FMIGameRules::Complete()
{
	SyncStats();
	if (Host)
	{
		Host->SetInvulnerable(true);
	}
	Note(TEXT("extraction:reached"));
	Note(TEXT("audio:sting"), TEXT("complete"));
	SetState(EMIGameState::Complete);
	Hush();
	Say(TEXT("radio.done"));
}

// ---------------------------------------------------------------------------------------------- hold the block

void FMIGameRules::StartWave()
{
	const int32 N = ++Run.Wave;
	bHoldoutActive = true;
	RealertIn = Tune.HoldRealertEvery;
	ApplyDifficulty();
	const MIFlow::FHoldoutWave Wave = MIFlow::HoldoutWave(N, Tune);
	FString From;
	if (QueueWave(Wave.Order, Tune.FirstSpawn, Wave.Stagger, From))
	{
		Warn(Text.Format(TEXT("banners.wave"), {{TEXT("n"), FString::FromInt(N)}, {TEXT("dir"), From}}), Tune.HoldBannerSecs);
	}
	RefreshObjective();
	Note(TEXT("holdout:wave"), FString(), N, Wave.Total);
}

void FMIGameRules::ClearWave()
{
	const int32 N = Run.Wave;
	bHoldoutActive = false;
	Cleared = N;
	BreakLeft = Tune.Breather;
	Countdown = Tune.CountdownFrom;
	Run.Score += Tune.WaveClear.Eval(N);
	if (Host)
	{
		Host->AddReserve(Tune.ResupplyReserve, Tune.ResupplyReserveCap);
		Host->HealPlayer(Tune.ResupplyHeal);
	}
	Note(TEXT("weapon:reserve"), FString(), Tune.ResupplyReserve, Tune.ResupplyReserveCap);
	Note(TEXT("player:heal"), FString(), Tune.ResupplyHeal);
	if (N % Tune.ExplosivesEvery == 0)
	{
		if (Host)
		{
			Host->ResetExplosives();
		}
		Note(TEXT("explosives:reset"));
	}
	const TMap<FString, FString> Args = {{TEXT("n"), FString::FromInt(N)}};
	Say(TEXT("radio.waveClear"), &Args);
	RefreshObjective();
	Note(TEXT("objective:done"), TEXT("wave"), N, N);
	Note(TEXT("audio:sting"), TEXT("reel"));
}

void FMIGameRules::UpdateHoldout(double Dt)
{
	if (bHoldoutActive)
	{
		if (Queue.Num() > 0)
		{
			return;
		}
		if (Enemies->AliveCount() == 0)
		{
			ClearWave();
			return;
		}
		RealertIn -= Dt;
		if (RealertIn <= 0)
		{
			RealertIn = Tune.HoldRealertEvery;
			Enemies->Alert(Player.Pos, Tune.HoldRealertRadius);
			ForwardEnemyEvents();
		}
		return;
	}
	BreakLeft -= Dt;
	if (Run.Wave > 0 && Countdown > 0 && BreakLeft <= Countdown)
	{
		Message(Text.Format(TEXT("banners.countdown"), {{TEXT("n"), FString::FromInt(Run.Wave + 1)}, {TEXT("secs"), FString::FromInt(Countdown)}}), Tune.CountdownSecs);
		Countdown--;
	}
	if (BreakLeft <= 0)
	{
		StartWave();
	}
}

// ----------------------------------------------------------------------------------------------------- cards

void FMIGameRules::SyncStats()
{
	if (Host)
	{
		int32 Headshots;
		Host->Stats(Run.Kills, Run.Shots, Run.Hits, Headshots);
	}
}

void FMIGameRules::ShowCard(FName Screen)
{
	SyncStats();
	Run.Score = FMath::FloorToDouble(Run.Score + 0.5);
	int32 Kills = 0, Shots = 0, Hits = 0, Headshots = 0;
	if (Host)
	{
		Host->Stats(Kills, Shots, Hits, Headshots);
	}
	FMIRunCard C;
	C.Screen = Screen;
	C.Mode = Mode;
	C.Difficulty = Difficulty;
	C.Time = Run.Time;
	C.Reels = Run.Reels;
	C.Total = Run.Total;
	C.Wave = Cleared;
	C.Kills = Run.Kills;
	C.Headshots = Headshots;
	C.Shots = Run.Shots;
	C.Hits = Run.Hits;
	C.Score = static_cast<int32>(Run.Score);
	if (Mode == NHoldout && Host)
	{
		C.bNewBest = Host->SetBest(C.Score);
		C.Best = Host->Best();
	}
	C.Accuracy = MIFlow::Accuracy(Run.Shots, Run.Hits);
	C.Retries = Run.Retries;
	C.Rating = MIFlow::RatingPoints(Run.Time, Run.Shots, Run.Hits, Run.Retries, Tune);
	C.RatingName = Text.Get(FString::Printf(TEXT("ratings.%d"), C.Rating));
	if (C.RatingName.IsEmpty())
	{
		C.RatingName = Text.Get(TEXT("ratings.0"));
	}
	CardShown = C;
	Note(TEXT("menus:card"), Screen.ToString(), C.Rating, C.Score, C.Time);
}

void FMIGameRules::EasePost(double Sat, double SatRate, double FadeTo, double FadeRate, double Dt)
{
	ViewState.Saturation = MI::Damp(ViewState.Saturation, Sat, SatRate, Dt);
	ViewState.Fade = MI::Damp(ViewState.Fade, FadeTo, FadeRate, Dt);
}

void FMIGameRules::UpdateMusic(double Dt)
{
	WaveAge += Dt;
	SinceAlert += Dt;
	SinceHit += Dt;
	MIFlow::FMusicState S;
	S.bAllDone = AllSecured();
	S.Queued = Queue.Num();
	S.Alive = Enemies->AliveCount();
	S.WaveAge = WaveAge;
	S.SinceAlert = SinceAlert;
	S.SinceHit = SinceHit;
	S.Nearest = Enemies->NearestDistance(Player.Pos);
	if (MIFlow::WaveIsOver(S, Tune))
	{
		S.WaveAge = WaveAge = MIEnemy::Inf;
	}
	ViewState.Music = MIFlow::MusicIntensity(S, Tune);
}

// ---------------------------------------------------------------------------------------------------- update

bool FMIGameRules::Update(double Dt, const FMIFlowPlayer& InPlayer, bool bInteractHeld)
{
	Player = InPlayer;
	StateTime += Dt;
	ViewState.MessageLeft = FMath::Max(0.0, ViewState.MessageLeft - Dt);
	ViewState.WarnLeft = FMath::Max(0.0, ViewState.WarnLeft - Dt);
	switch (State)
	{
	case EMIGameState::Title:
		ViewState.Saturation = 1;
		return false;
	case EMIGameState::Paused:
		return false;
	case EMIGameState::Dead:
		EasePost(Tune.DeadSat, Tune.DeadSatRate, Tune.DeadFade, Tune.DeadFadeRate, Dt);
		if (!bCardShown && StateTime >= Tune.DeathCard)
		{
			bCardShown = true;
			ShowCard(TEXT("dead"));
		}
		return true;
	case EMIGameState::Complete:
		EasePost(Tune.DoneSat, Tune.DoneSatRate, Tune.DoneFade, Tune.DoneFadeRate, Dt);
		Radio.Update(Dt);
		if (!bCardShown && StateTime >= Tune.DebriefCard)
		{
			bCardShown = true;
			ShowCard(TEXT("complete"));
		}
		return true;
	default:
		break;
	}
	Clock += Dt;
	if (State == EMIGameState::Intro)
	{
		ViewState.Fade = 1.0 - SmoothStep(Tune.IntroFadeA, FMath::Min(IntroLength, Tune.IntroFadeB), StateTime);
		if (bFullIntro && !bIntroCard && StateTime >= Tune.LocationCardAt)
		{
			bIntroCard = true;
			ViewState.bLocationCard = true;
		}
		if (bFullIntro && !bIntroRadio && StateTime >= Tune.IntroRadioAt)
		{
			bIntroRadio = true;
			Say(Mode == NMission ? TEXT("radio.intro") : TEXT("radio.introHoldout"));
		}
		if (StateTime >= IntroLength)
		{
			FinishIntro();
		}
	}
	else
	{
		Run.Time += Dt;
	}
	SyncStats();
	PumpQueue();
	if (Mode == NMission)
	{
		UpdateInteraction(Dt, bInteractHeld);
		if (AllSecured())
		{
			UpdatePursuit(Dt);
		}
		UpdateExtraction();
		if (State == EMIGameState::Complete)
		{
			return true;
		}
	}
	else
	{
		UpdateHoldout(Dt);
	}
	if (!bSaidLow && Player.bAlive && Player.Health < Tune.LowWarning)
	{
		bSaidLow = true;
		Say(TEXT("radio.lowHealth"));
	}
	Radio.Update(Dt);
	UpdateMusic(Dt);
	return true;
}

// ---------------------------------------------------------------------------------------------------- events

void FMIGameRules::OnPlayerDead()
{
	if (State != EMIGameState::Playing && State != EMIGameState::Intro && State != EMIGameState::Paused)
	{
		return;
	}
	SyncStats();
	GrabTarget = INDEX_NONE;
	GrabProgress = 0;
	ViewState.bLocationCard = false;
	Note(TEXT("audio:sting"), TEXT("dead"));
	SetState(EMIGameState::Dead);
	Hush();
}

void FMIGameRules::OnEnemyEvent(const FMIEnemyEvent& Ev)
{
	switch (Ev.Kind)
	{
	case FMIEnemyEvent::EKind::Spawn:
		Note(TEXT("enemy:spawn"), Ev.Type == MIEnemy::EType::Goon ? TEXT("goon") : TEXT("buzzard"), Ev.Id, 0, 0);
		break;
	case FMIEnemyEvent::EKind::Alert:
		SinceAlert = 0;
		if (!bSaidContact && State == EMIGameState::Playing)
		{
			bSaidContact = true;
			Say(TEXT("radio.contact"));
		}
		break;
	case FMIEnemyEvent::EKind::Killed:
		Note(TEXT("enemy:killed"), Ev.Type == MIEnemy::EType::Goon ? TEXT("goon") : TEXT("buzzard"), Ev.Id);
		if (Mode == NHoldout && State == EMIGameState::Playing)
		{
			Run.Score += MIFlow::KillScore(Ev.Type == MIEnemy::EType::Goon, Run.Wave, Tune);
			RefreshTally();
		}
		break;
	default:
		break;
	}
}

void FMIGameRules::ForwardEnemyEvents()
{
	TArray<FMIEnemyEvent>& Events = Enemies->Events();
	for (int32 I = 0; I < Events.Num(); ++I)
	{
		if (I >= Handled)
		{
			OnEnemyEvent(Events[I]);
		}
	}
	Handled = Events.Num();
}

void FMIGameRules::DrainEnemies(TArray<FMIEnemyEvent>& Out)
{
	ForwardEnemyEvents();
	Out.Append(Enemies->Events());
	Enemies->Events().Reset();
	Handled = 0;
}
