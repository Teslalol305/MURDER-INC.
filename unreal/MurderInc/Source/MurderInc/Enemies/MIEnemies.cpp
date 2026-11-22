#include "Enemies/MIEnemies.h"

// src/enemies.js, src/enemies/goon.js, src/enemies/buzzard.js and src/enemies/bolts.js, in that order. Every random
// draw, every branch and the order of the floating-point operations follow the web files (MurderInc.Golden.Enemies
// replays the web game frame by frame); the comments there explain the rules. Effects (tracers, flashes, smoke,
// sparks, dust, debris) are left to the host, which listens to the events.

using namespace MIEnemy;
using MI::Web::AngleDelta;
using MI::Web::Hypot;
using MI::Web::WrapAngle;

namespace
{
	constexpr double Gravity = 20.0;
	constexpr int32 MaxCandidates = 96;
	constexpr double SeparationPush = 2.2;
	constexpr double PlayerPush = 3.0;

	double Dist2(const FVector& A, const FVector& B) { return (A.X - B.X) * (A.X - B.X) + (A.Y - B.Y) * (A.Y - B.Y) + (A.Z - B.Z) * (A.Z - B.Z); }
	FVector Normalised(const FVector& V)
	{
		const double L = FMath::Sqrt(V.X * V.X + V.Y * V.Y + V.Z * V.Z);
		return L > 0.0 ? FVector(V.X / L, V.Y / L, V.Z / L) : V;
	}

	/** rig.js m3EulerA: row-major 3 x 3 of the Euler angles (x, y, z) in three.js 'XYZ' order. */
	void EulerMatrix(double X, double Y, double Z, double M[9])
	{
		const double Cx = FMath::Cos(X), Sx = FMath::Sin(X), Cy = FMath::Cos(Y), Sy = FMath::Sin(Y), Cz = FMath::Cos(Z), Sz = FMath::Sin(Z);
		M[0] = Cy * Cz + Sy * Sx * Sz;
		M[1] = Sy * Sx * Cz - Cy * Sz;
		M[2] = Sy * Cx;
		M[3] = Cx * Sz;
		M[4] = Cx * Cz;
		M[5] = -Sx;
		M[6] = Cy * Sx * Sz - Sy * Cz;
		M[7] = Sy * Sz + Cy * Sx * Cz;
		M[8] = Cy * Cx;
	}
	FVector Mul(const double M[9], const FVector& P) { return FVector(M[0] * P.X + M[1] * P.Y + M[2] * P.Z, M[3] * P.X + M[4] * P.Y + M[5] * P.Z, M[6] * P.X + M[7] * P.Y + M[8] * P.Z); }
}

// =================================================================================================== shared

void FMIEnemyField::Init(const FMIEnemyTune& InTune, const FMILevelData* InLevel, FMIBoxWorld* InWorld, IMIEnemyHost* InHost)
{
	Tune = InTune;
	Level = InLevel;
	World = InWorld;
	Host = InHost;
	Rng = FMIRng(Tune.Seed);
	Tokens.Reset();
	Solids = FSolids();
	Slots.Reset();
	for (int32 I = 0; I < Tune.PoolGoon; ++I)
	{
		FMIEnemy& E = Slots.AddDefaulted_GetRef();
		E.Type = EType::Goon;
		E.Slot = I;
	}
	for (int32 I = 0; I < Tune.PoolBuzzard; ++I)
	{
		FMIEnemy& E = Slots.AddDefaulted_GetRef();
		E.Type = EType::Buzzard;
		E.Slot = I;
	}
	List.Reset();
	Bodies.Reset();
	BoltSlots.Init(FMIBolt(), Tune.PoolBolts);
	NextBolt = LiveBoltCount = 0;
	PendingEvents.Reset();
	Now = 0;
	NextId = 1;
	SinceGunfire = Inf;
	PathCursor = PickCursor = StandCursor = 0;
	ScaleHp = ScaleDamage = ScaleCooldown = 1;
	PlayerSpeed = 0;
	Candidates.SetNum(MaxCandidates);
	if (Model.Rotors.Num() == 0)
	{
		Model.Rotors = {FVector(0.2, 0.02, -0.2), FVector(-0.2, 0.02, -0.2), FVector(0.2, 0.02, 0.2), FVector(-0.2, 0.02, 0.2)};
	}
}

void FMIEnemyField::SetScale(double Hp, double Damage, double CooldownScale)
{
	ScaleHp = Hp > 0 ? Hp : 1;
	ScaleDamage = Damage > 0 ? Damage : 1;
	ScaleCooldown = CooldownScale > 0 ? CooldownScale : 1;
}

void FMIEnemyField::Emit(FMIEnemyEvent::EKind Kind, const FMIEnemy& E, const FVector& Pos, const FVector& Dir)
{
	FMIEnemyEvent& Ev = PendingEvents.AddDefaulted_GetRef();
	Ev.Kind = Kind;
	Ev.Id = E.Id;
	Ev.Type = E.Type;
	Ev.Pos = Pos;
	Ev.Dir = Dir;
}

bool FMIEnemyField::RequestToken(FMIEnemy& E)
{
	if (E.bHasToken)
	{
		return true;
	}
	if (!Tokens.Request(E.Type, Now, Alive, Tune.Ai))
	{
		return false;
	}
	E.bHasToken = true;
	return true;
}

void FMIEnemyField::ReleaseToken(FMIEnemy& E)
{
	if (!E.bHasToken)
	{
		return;
	}
	E.bHasToken = false;
	Tokens.Release();
}

void FMIEnemyField::CancelAttack(FMIEnemy& E)
{
	E.Telegraph = 0;
	E.BurstLeft = 0;
	ReleaseToken(E);
}

void FMIEnemyField::SetMode(FMIEnemy& E, EMIEnemyMode Mode)
{
	if (E.Mode == Mode)
	{
		return;
	}
	if (E.Mode == EMIEnemyMode::Engage)
	{
		CancelAttack(E);
		OnLeaveEngage(E);
	}
	E.Mode = Mode;
}

void FMIEnemyField::Rally(FMIEnemy& E, double Radius, const FVector& At)
{
	for (int32 I = 0; I < List.Num(); ++I)
	{
		FMIEnemy& O = Slots[List[I]];
		if (&O == &E || !O.bAlive || O.bPassive || O.Mode == EMIEnemyMode::Engage)
		{
			continue;
		}
		if (Dist2(O.Pos, E.Pos) <= Radius * Radius)
		{
			Investigate(O, At, Range(Tune.Ai.NoiseTime), false);
		}
	}
}

void FMIEnemyField::Engage(FMIEnemy& E)
{
	if (!E.bAlive || E.bPassive || E.Mode == EMIEnemyMode::Engage)
	{
		return;
	}
	SetMode(E, EMIEnemyMode::Engage);
	E.SinceSeen = 0;
	OnEngage(E);
	Emit(FMIEnemyEvent::EKind::Alert, E, E.Pos);
	Rally(E, Tune.Ai.RallyOnSight, Player.Pos);
}

void FMIEnemyField::Investigate(FMIEnemy& E, const FVector& At, double Seconds, bool bAnnounce)
{
	if (!E.bAlive || E.bPassive || E.Mode == EMIEnemyMode::Engage)
	{
		return;
	}
	const bool bWasPatrol = E.Mode == EMIEnemyMode::Patrol;
	E.LastKnown = FVector(At.X, World->GroundHeight(At.X, At.Z, At.Y + 0.3), At.Z);
	SetMode(E, E.Mode == EMIEnemyMode::Search ? EMIEnemyMode::Search : EMIEnemyMode::Investigate);
	E.ModeTime = Seconds;
	OnInvestigate(E);
	if (bAnnounce && bWasPatrol)
	{
		Emit(FMIEnemyEvent::EKind::Alert, E, At);
	}
}

void FMIEnemyField::ToPatrol(FMIEnemy& E)
{
	SetMode(E, EMIEnemyMode::Patrol);
	E.Home = E.Pos;
	E.Seen = 0;
	OnPatrol(E);
}

void FMIEnemyField::Sense(FMIEnemy& E, double Dt)
{
	const FMIAiTune& Ai = Tune.Ai;
	E.SenseIn -= Dt;
	if (E.SenseIn > 0)
	{
		return;
	}
	const double Tick = Ai.SenseEvery.A + (Ai.SenseEvery.B - Ai.SenseEvery.A) * Random();
	E.SenseIn = Tick;
	bool bVisible = false;
	if (Player.bAlive)
	{
		const FVector Sensor = E.IsGoon() ? FVector(E.Pos.X, E.Pos.Y + Tune.Goon.EyeHeight, E.Pos.Z) : E.Eye;
		const double Dx = Player.Eye.X - Sensor.X, Dy = Player.Eye.Y - Sensor.Y, Dz = Player.Eye.Z - Sensor.Z;
		const double Dist = FMath::Sqrt(Dx * Dx + Dy * Dy + Dz * Dz);
		const double Facing = E.IsGoon() ? E.Yaw + E.HeadYaw : E.Yaw;
		bVisible = InSight(Dist, Dx, Dz, Facing, E.Mode == EMIEnemyMode::Engage, Ai) && World->LineOfSight(Sensor, Player.Eye);
	}
	E.bSees = bVisible;
	E.Seen = SeenStep(E.Seen, bVisible, Tick, Ai);
	if (bVisible)
	{
		E.LastKnown = Player.Pos;
		E.SinceSeen = 0;
		const double Reaction = E.IsGoon() ? Tune.Goon.Reaction : Tune.Buzzard.Reaction;
		if (E.Mode != EMIEnemyMode::Engage && E.Seen >= ReactionTime(Reaction, E.Mode == EMIEnemyMode::Patrol, Ai))
		{
			Engage(E);
		}
	}
}

void FMIEnemyField::Think(FMIEnemy& E, double Dt)
{
	const FMIAiTune& Ai = Tune.Ai;
	E.SinceSeen += Dt;
	Sense(E, Dt);
	E.Exposure = ExposureStep(E.Exposure, E.bSees, Dt, Ai);
	if (E.Mode == EMIEnemyMode::Engage)
	{
		if (!Player.bAlive || E.SinceSeen >= Ai.LoseSightAfter)
		{
			if (E.SinceSeen < Ai.LoseSightAfter)
			{
				E.LastKnown = Player.Pos;
			}
			SetMode(E, EMIEnemyMode::Search);
			E.ModeTime = Range(Ai.SearchTime);
			OnInvestigate(E);
		}
	}
	else if (E.Mode != EMIEnemyMode::Patrol)
	{
		E.ModeTime -= Dt;
		if (E.ModeTime <= 0)
		{
			ToPatrol(E);
		}
	}
}

void FMIEnemyField::Retire(FMIEnemy& E)
{
	ReleaseToken(E);
	E.bHasToken = false;
	E.bActive = false;
	E.bAlive = false;
	E.Mode = EMIEnemyMode::Idle;
	const int32 Index = &E - Slots.GetData();
	List.Remove(Index);
	Bodies.Remove(Index);
}

FMIEnemy* FMIEnemyField::Spawn(EType Type, const FVector& Pos, const FMIEnemySpawnOptions& Opts)
{
	const int32 First = Type == EType::Goon ? 0 : Tune.PoolGoon;
	const int32 Count = Type == EType::Goon ? Tune.PoolGoon : Tune.PoolBuzzard;
	int32 Pick = INDEX_NONE;
	for (int32 I = 0; I < Count && Pick == INDEX_NONE; ++I)
	{
		if (!Slots[First + I].bActive)
		{
			Pick = First + I;
		}
	}
	if (Pick == INDEX_NONE && Bodies.Num() && Type == EType::Goon)
	{
		Pick = Bodies[0];
	}
	for (int32 I = 0; I < Count && Pick == INDEX_NONE; ++I)
	{
		if (!Slots[First + I].bAlive)
		{
			Pick = First + I;
		}
	}
	if (Pick == INDEX_NONE)
	{
		return nullptr;
	}
	FMIEnemy& E = Slots[Pick];
	if (E.bActive)
	{
		Retire(E);
	}
	E.Id = NextId++;
	E.bActive = true;
	E.bAlive = true;
	E.MaxHp = E.Hp = (Type == EType::Goon ? Tune.Goon.Hp : Tune.Buzzard.Hp) * ScaleHp;
	E.bPassive = Opts.bPassive;
	E.Seen = 0;
	E.bSees = false;
	E.SinceSeen = Inf;
	E.SenseIn = Random() * Tune.Ai.SenseEvery.B;
	E.Exposure = 0;
	E.Telegraph = 0;
	E.bHasToken = false;
	E.LastActive = Now;
	E.DeadTime = 0;
	E.Mode = EMIEnemyMode::Patrol;
	E.ModeTime = 0;
	if (Type == EType::Goon)
	{
		GoonSpawn(E, Pos, Opts);
	}
	else
	{
		BuzzardSpawn(E, Pos, Opts);
	}
	E.LastKnown = E.Pos;
	List.Add(Pick);
	if (Opts.bAlerted && !E.bPassive)
	{
		const FVector At = Opts.Target.IsSet() ? Opts.Target.GetValue() : LivePlayerPos;
		Investigate(E, At, Type == EType::Goon ? Tune.Goon.SpawnAlertTime : Tune.Buzzard.SpawnAlertTime, false);
	}
	Emit(FMIEnemyEvent::EKind::Spawn, E, E.Pos);
	return &E;
}

void FMIEnemyField::Clear()
{
	for (int32 I = List.Num() - 1; I >= 0; --I)
	{
		Retire(Slots[List[I]]);
	}
	for (int32 I = Bodies.Num() - 1; I >= 0; --I)
	{
		Retire(Slots[Bodies[I]]);
	}
	Tokens.Reset();
	for (FMIBolt& B : BoltSlots)
	{
		B.Life = 0;
		B.Owner = 0;
	}
	LiveBoltCount = 0;
}

bool FMIEnemyField::Damage(FMIEnemy& E, double Amount, FName Part, const TOptional<FVector>& Dir, bool bByPlayer, FName Weapon)
{
	if (!E.bAlive || !(Amount > 0))
	{
		return false;
	}
	if (Part.IsNone())
	{
		Part = TEXT("body");
	}
	E.Hp -= Amount;
	{
		FMIEnemyEvent& Ev = PendingEvents.AddDefaulted_GetRef();
		Ev.Kind = FMIEnemyEvent::EKind::Hit;
		Ev.Id = E.Id;
		Ev.Type = E.Type;
		Ev.Pos = E.Pos;
		Ev.Part = Part;
		Ev.Damage = Amount;
	}
	if (E.IsGoon())
	{
		// goon.js onHit: a cosmetic flinch along the shot.
		const double Strength = FMath::Min(Tune.Goon.StaggerMax, Amount / 28.0) * (Part == FName(TEXT("head")) ? 1.5 : 1.0);
		E.FlinchStrength = Strength;
		E.FlinchAge = 0;
		if (Dir.IsSet())
		{
			const double C = FMath::Cos(E.Yaw), S = FMath::Sin(E.Yaw);
			E.FlinchDir = FVector(Dir->X * C - Dir->Z * S, 0, Dir->X * S + Dir->Z * C);
		}
	}
	else
	{
		BuzzardHit(E, Amount, Dir);
	}

	if (E.Hp > 0)
	{
		if (E.Mode != EMIEnemyMode::Engage && !E.bPassive && Player.bAlive)
		{
			Investigate(E, Player.Pos, Tune.Ai.ProvokedTime, true);
			E.Seen = FMath::Max(E.Seen, 1.0);
			E.SenseIn = 0;
			Rally(E, Tune.Ai.RallyOnHit, Player.Pos);
		}
		return false;
	}
	E.Hp = 0;
	E.bAlive = false;
	CancelAttack(E);
	if (E.Mode == EMIEnemyMode::Engage)
	{
		OnLeaveEngage(E);
	}
	E.Mode = EMIEnemyMode::Dying;
	E.DeadTime = 0;
	E.bSees = false;
	if (E.IsGoon())
	{
		GoonKilled(E, Dir);
	}
	else
	{
		BuzzardKilled(E, Dir);
	}
	FMIEnemyEvent& Ev = PendingEvents.AddDefaulted_GetRef();
	Ev.Kind = FMIEnemyEvent::EKind::Killed;
	Ev.Id = E.Id;
	Ev.Type = E.Type;
	Ev.Pos = E.Pos;
	Ev.Part = Part;
	Ev.bByPlayer = bByPlayer;
	Ev.Weapon = Weapon;
	return true;
}

void FMIEnemyField::Alert(const FVector& Pos, double Radius)
{
	for (int32 I = 0; I < List.Num(); ++I)
	{
		FMIEnemy& E = Slots[List[I]];
		if (!E.bAlive || E.bPassive || E.Mode == EMIEnemyMode::Engage)
		{
			continue;
		}
		if (Dist2(E.Pos, Pos) <= Radius * Radius)
		{
			Investigate(E, Pos, Range(Tune.Ai.NoiseTime), true);
		}
	}
}

void FMIEnemyField::Hear(const FVector& Pos, double Radius)
{
	for (int32 I = 0; I < List.Num(); ++I)
	{
		FMIEnemy& E = Slots[List[I]];
		if (!E.bAlive || E.bPassive || E.Mode != EMIEnemyMode::Patrol)
		{
			continue;
		}
		if (Dist2(E.Pos, Pos) <= Radius * Radius)
		{
			Investigate(E, Pos, Range(Tune.Ai.NoiseTime), true);
		}
	}
}

void FMIEnemyField::Gunfire(const FVector& Pos)
{
	if (SinceGunfire < Tune.Ai.GunfireEvery)
	{
		return;
	}
	SinceGunfire = 0;
	Alert(Pos, Tune.Ai.HearGunfire);
}

void FMIEnemyField::SpendBudgets()
{
	const int32 N = Tune.PoolGoon;
	for (int32 K = 0; K < N && BudgetPicks > 0; ++K)
	{
		FMIEnemy& E = Slots[(PickCursor + K) % N];
		if (!E.bAlive || E.Mode != EMIEnemyMode::Engage || !E.bWantPick)
		{
			continue;
		}
		if (E.Sub != EMIGoonSub::Move && E.Sub != EMIGoonSub::Aim && E.Sub != EMIGoonSub::Cool)
		{
			continue;
		}
		--BudgetPicks;
		Pick(E);
		PickCursor = (PickCursor + K + 1) % N;
	}
	for (int32 K = 0; K < N && BudgetPicks > 0; ++K)
	{
		FMIEnemy& E = Slots[(StandCursor + K) % N];
		if (!E.bAlive || E.bPassive || (E.Mode != EMIEnemyMode::Investigate && E.Mode != EMIEnemyMode::Search) || !E.bWantStand)
		{
			continue;
		}
		--BudgetPicks;
		PickStand(E);
		StandCursor = (StandCursor + K + 1) % N;
	}
	for (int32 K = 0; K < N && BudgetPaths > 0; ++K)
	{
		FMIEnemy& E = Slots[(PathCursor + K) % N];
		if (!E.bAlive || !E.bNeedPath || !E.bHasGoal)
		{
			continue;
		}
		--BudgetPaths;
		Plan(E);
		PathCursor = (PathCursor + K + 1) % N;
	}
}

void FMIEnemyField::Update(double Dt, const FMIEnemyPlayer& InPlayer)
{
	if (!(Dt > 0))
	{
		return;
	}
	Now += Dt;
	SinceGunfire += Dt;
	Player = InPlayer;
	LivePlayerPos = InPlayer.Pos;
	const double Speed = Player.bAlive ? Hypot(Player.Vel.X, Player.Vel.Z) : 0.0;
	PlayerSpeed = MI::Damp(PlayerSpeed, Speed, 6.0, Dt);
	BudgetPaths = Tune.Ai.PathsPerFrame;
	BudgetPicks = Tune.Ai.PicksPerFrame;
	Alive = AliveCount();

	for (int32 I = List.Num() - 1; I >= 0; --I)
	{
		if (I >= List.Num())
		{
			continue;
		}
		FMIEnemy& E = Slots[List[I]];
		if (E.bAlive)
		{
			if (!E.bPassive)
			{
				Think(E, Dt);
			}
			if (E.IsGoon())
			{
				GoonUpdate(E, Dt);
			}
			else
			{
				BuzzardUpdate(E, Dt);
			}
			continue;
		}
		E.DeadTime += Dt;
		if (E.IsGoon())
		{
			if (!GoonDying(E, Dt))
			{
				continue;
			}
			const int32 Index = List[I];
			List.RemoveAt(I);
			E.Mode = EMIEnemyMode::Dead;
			Bodies.Add(Index);
			if (Bodies.Num() > Tune.PoolBodies)
			{
				Slots[Bodies[0]].bFading = true;
			}
		}
		else
		{
			if (!BuzzardDying(E, Dt))
			{
				continue;
			}
			Retire(E);
			Burst(E);
		}
	}
	SpendBudgets();

	for (int32 I = Bodies.Num() - 1; I >= 0; --I)
	{
		FMIEnemy& E = Slots[Bodies[I]];
		if (Bodies.Num() - I > Tune.PoolBodies)
		{
			E.bFading = true;
		}
		if (GoonBody(E, Dt))
		{
			Retire(E);
		}
	}
	UpdateBolts(Dt);
}

int32 FMIEnemyField::AliveCount() const
{
	int32 N = 0;
	for (const int32 I : List)
	{
		N += Slots[I].bAlive ? 1 : 0;
	}
	return N;
}

int32 FMIEnemyField::CountByType(EType Type) const
{
	int32 N = 0;
	for (const int32 I : List)
	{
		N += Slots[I].bAlive && Slots[I].Type == Type ? 1 : 0;
	}
	return N;
}

double FMIEnemyField::NearestDistance(const FVector& From) const
{
	double Best = Inf;
	for (const int32 I : List)
	{
		if (Slots[I].bAlive)
		{
			Best = FMath::Min(Best, FMath::Sqrt(Dist2(Slots[I].Pos, From)));
		}
	}
	return Best;
}

FMIEnemy* FMIEnemyField::Find(int32 Id)
{
	for (FMIEnemy& E : Slots)
	{
		if (E.bActive && E.Id == Id)
		{
			return &E;
		}
	}
	return nullptr;
}

const FMIEnemy* FMIEnemyField::Find(int32 Id) const
{
	return const_cast<FMIEnemyField*>(this)->Find(Id);
}

void FMIEnemyField::OnLeaveEngage(FMIEnemy& E)
{
	if (E.IsGoon())
	{
		E.Sub = EMIGoonSub::Move;
		E.SubT = 0;
		E.bHasFirePos = false;
		E.bWantPick = false;
		E.BurstLeft = 0;
		ClearGoal(E);
	}
	else
	{
		E.BurstLeft = 0;
	}
}

void FMIEnemyField::OnEngage(FMIEnemy& E)
{
	if (E.IsGoon())
	{
		E.Sub = EMIGoonSub::Move;
		E.SubT = 0;
		E.bHasFirePos = false;
		E.bWantPick = true;
		E.Bursts = 0;
		E.AimYaw = E.Yaw;
		ClearGoal(E);
	}
	else
	{
		E.OrbitAngle = FMath::Atan2(E.Pos.Z - Player.Pos.Z, E.Pos.X - Player.Pos.X);
		E.RethinkIn = Range(Tune.Buzzard.OrbitRethink);
	}
}

void FMIEnemyField::OnInvestigate(FMIEnemy& E)
{
	if (E.IsGoon())
	{
		E.Sweep = 0;
		E.StuckCount = 0;
		E.PathFails = 0;
		if (E.Wait > 0)
		{
			E.Wait = 0;
		}
	}
	else
	{
		E.OrbitAngle = FMath::Atan2(E.Pos.Z - E.LastKnown.Z, E.Pos.X - E.LastKnown.X);
	}
}

void FMIEnemyField::OnPatrol(FMIEnemy& E)
{
	if (E.IsGoon())
	{
		ClearGoal(E);
		E.Wait = Range(Tune.Goon.PatrolWait) * 0.5;
	}
	else
	{
		E.OrbitAngle = FMath::Atan2(E.Pos.Z - E.Home.Z, E.Pos.X - E.Home.X);
		E.PatrolRadius = FMath::Max(1.5, FMath::Min(E.PatrolRadius, 9.0));
	}
}

FVector FMIEnemyField::GoonHead(const FMIEnemy& E) const
{
	const FMIGoonTune& T = Tune.Goon;
	const double H = FMath::Lerp(T.HeadHeight, T.HeadHeight - (T.Height - T.CrouchHeight), E.WantCrouch);
	return FVector(E.Pos.X, E.Pos.Y + H, E.Pos.Z);
}

// ===================================================================================================== Goon

void FMIEnemyField::GoonSpawn(FMIEnemy& E, const FVector& At, const FMIEnemySpawnOptions& Opts)
{
	const FMIGoonTune& T = Tune.Goon;
	E.Pos = At;
	if (!World->IsWalkable(At.X, At.Z))
	{
		FVector Near;
		if (World->NearestWalkable(At.X, At.Z, 4.0, Near))
		{
			E.Pos = FVector(Near.X, At.Y, Near.Z);
		}
	}
	E.Pos.Y = World->GroundHeight(E.Pos.X, E.Pos.Z, At.Y + 0.6);
	E.Vel = FVector::ZeroVector;
	E.Home = E.Pos;
	E.Yaw = Opts.Yaw.IsSet() ? Opts.Yaw.GetValue() : Random() * UE_DOUBLE_PI * 2.0;
	E.AimYaw = E.Yaw;
	E.Cooldown = Range(T.FirstCooldown);
	const int32 PickVariant = static_cast<int32>(FMath::FloorToDouble(Random() * 3.0)) % 3;
	E.Variant = Opts.Variant >= 0 && Opts.Variant < 3 ? Opts.Variant : PickVariant;
	E.HeadYaw = E.HeadPitch = 0;
	E.Swing = -1;
	E.DeathT = 0;
	E.FlinchStrength = 0;
	E.Sub = EMIGoonSub::Move;
	E.SubT = 0;
	E.bHasPath = E.bNeedPath = E.bHasGoal = E.bArrived = false;
	E.Path.Reset();
	E.PathFails = 0;
	E.ReplanIn = Range(T.Replan);
	E.WantSpeed = E.MoveSpeed = E.Speed = E.YawRate = 0;
	E.bFacing = false;
	E.TurnScale = 1;
	E.Stuck = 0;
	E.StuckCount = 0;
	E.Travel = 0;
	E.Wait = Random() * 1.5;
	E.bOnGround = true;
	E.bHasFirePos = E.bWantPick = E.bPickAway = E.bAtCover = false;
	E.bWantStand = E.bHasStand = false;
	E.Bursts = E.BurstLeft = 0;
	E.BurstsToMove = 1;
	E.BurstTimer = E.NoSight = E.Waited = E.TooClose = 0;
	E.RushCooldown = 0;
	E.bRushHit = false;
	E.Sweep = Random() * 6.0;
	E.Scan = Random() * 6.0;
	E.bDusted = false;
	E.BodyAge = 0;
	E.bFading = false;
	E.Fade = 0;
	E.WantCrouch = E.WantAim = E.AimYawRel = E.AimPitch = E.LookYawRel = E.LookPitch = 0;
	E.RushPhase = 0;
	E.RushK = E.LampWant = 0;
}

void FMIEnemyField::SetGoal(FMIEnemy& E, double X, double Z)
{
	if (E.bHasGoal && FMath::Abs(E.GoalX - X) < 0.3 && FMath::Abs(E.GoalZ - Z) < 0.3)
	{
		return;
	}
	E.GoalX = X;
	E.GoalZ = Z;
	E.bHasGoal = true;
	E.bNeedPath = true;
	E.bArrived = false;
	E.PathFails = 0;
}

void FMIEnemyField::ClearGoal(FMIEnemy& E)
{
	E.bHasGoal = E.bHasPath = E.bNeedPath = E.bArrived = false;
}

void FMIEnemyField::Plan(FMIEnemy& E)
{
	const bool bFound = World->FindPath(E.Pos, FVector(E.GoalX, 0, E.GoalZ), E.Path);
	E.bNeedPath = false;
	E.ReplanIn = Range(Tune.Goon.Replan);
	if (!bFound || E.Path.Num() < 2)
	{
		E.bHasPath = false;
		E.PathFails++;
		return;
	}
	E.bHasPath = true;
	E.PathIndex = 1;
	E.PathFails = 0;
}

bool FMIEnemyField::Locomote(FMIEnemy& E, double Dt)
{
	const FMIGoonTune& T = Tune.Goon;
	const bool bDashing = E.Sub == EMIGoonSub::Lunge && E.Mode == EMIEnemyMode::Engage;
	double TargetSpeed = 0;
	double WantYaw = E.Yaw;
	bool bTurning = E.bFacing;
	if (bTurning)
	{
		WantYaw = E.FaceYaw;
	}
	if (bDashing)
	{
		TargetSpeed = T.RushSpeed;
		WantYaw = FMath::Atan2(E.Pos.X - Player.Pos.X, E.Pos.Z - Player.Pos.Z);
		bTurning = true;
	}
	else if (E.bHasGoal && E.bHasPath && !E.bArrived && E.WantSpeed > 0)
	{
		const int32 Last = E.Path.Num() - 1;
		if (E.PathIndex > Last)
		{
			E.PathIndex = Last;
		}
		FVector Wp = E.Path[E.PathIndex];
		double Dx = Wp.X - E.Pos.X, Dz = Wp.Z - E.Pos.Z;
		double D = Hypot(Dx, Dz);
		while (E.PathIndex < Last && D < T.WaypointReach)
		{
			E.PathIndex++;
			Wp = E.Path[E.PathIndex];
			Dx = Wp.X - E.Pos.X;
			Dz = Wp.Z - E.Pos.Z;
			D = Hypot(Dx, Dz);
		}
		if (E.PathIndex == Last && D < T.GoalReach)
		{
			E.bArrived = true;
		}
		else
		{
			WantYaw = FMath::Atan2(-Dx, -Dz);
			bTurning = true;
			const double Error = FMath::Abs(AngleDelta(E.Yaw, WantYaw));
			TargetSpeed = FollowSpeed(E.WantSpeed, Error, E.PathIndex == Last ? D : D + 2.0, T);
		}
	}

	const double Before = E.Yaw;
	if (bTurning)
	{
		const double Rate = (bDashing ? T.TurnRate * 2.0 : (TargetSpeed > 0 || E.MoveSpeed > 0.3 ? T.PathTurnRate : T.TurnRate)) * E.TurnScale;
		E.Yaw = WrapAngle(E.Yaw + MI::MoveToward(0.0, AngleDelta(E.Yaw, WantYaw), Rate * Dt));
	}
	E.YawRate = Dt > 0 ? AngleDelta(Before, E.Yaw) / Dt : 0.0;

	if (bDashing)
	{
		E.MoveSpeed = TargetSpeed;
	}
	else
	{
		E.MoveSpeed = MI::MoveToward(E.MoveSpeed, TargetSpeed, (TargetSpeed > E.MoveSpeed ? T.Accel : T.Decel) * Dt);
	}
	double Vx = -FMath::Sin(E.Yaw) * E.MoveSpeed;
	double Vz = -FMath::Cos(E.Yaw) * E.MoveSpeed;

	for (int32 I = 0; I < List.Num(); ++I)
	{
		const FMIEnemy& O = Slots[List[I]];
		if (&O == &E || O.Type != EType::Goon || !O.bAlive)
		{
			continue;
		}
		const double Ox = E.Pos.X - O.Pos.X, Oz = E.Pos.Z - O.Pos.Z;
		const double D2 = Ox * Ox + Oz * Oz;
		const double Reach = T.SeparationGoon;
		if (D2 >= Reach * Reach || FMath::Abs(E.Pos.Y - O.Pos.Y) > 1.5)
		{
			continue;
		}
		const double D = FMath::Sqrt(D2);
		const double Push = (1.0 - D / Reach) * SeparationPush;
		if (D > 1e-3)
		{
			Vx += (Ox / D) * Push;
			Vz += (Oz / D) * Push;
		}
		else
		{
			Vx += FMath::Cos(E.Slot * 2.4) * Push;
			Vz += FMath::Sin(E.Slot * 2.4) * Push;
		}
	}
	if (!bDashing && Player.bAlive)
	{
		const double Ox = E.Pos.X - Player.Pos.X, Oz = E.Pos.Z - Player.Pos.Z;
		const double D = Hypot(Ox, Oz);
		if (D < T.SeparationPlayer && D > 1e-3 && FMath::Abs(E.Pos.Y - Player.Pos.Y) < 1.5)
		{
			const double Push = (1.0 - D / T.SeparationPlayer) * PlayerPush;
			Vx += (Ox / D) * Push;
			Vz += (Oz / D) * Push;
		}
	}

	E.Vel.X = Vx;
	E.Vel.Z = Vz;
	E.Vel.Y = E.bOnGround ? 0.0 : E.Vel.Y - Gravity * Dt;
	const double Px = E.Pos.X, Pz = E.Pos.Z;
	const FMIMoveResult Moved = World->MoveCapsule(E.Pos, E.Vel, Dt, T.Radius, T.Height, E.bOnGround);
	E.bOnGround = Moved.bOnGround;
	E.Surface = Moved.Surface;
	const double Step = Hypot(E.Pos.X - Px, E.Pos.Z - Pz);
	E.Speed = Dt > 0 ? Step / Dt : 0.0;

	if (E.MoveSpeed > 0.6 && Step < E.MoveSpeed * Dt * 0.3)
	{
		E.Stuck += Dt;
	}
	else
	{
		E.Stuck = FMath::Max(0.0, E.Stuck - Dt * 2.0);
	}
	E.Travel += Step;
	if (E.Travel > 0.5)
	{
		E.Travel = 0;
		E.StuckCount = 0;
		E.LastActive = Now;
	}
	if (E.bHasGoal && !E.bArrived && !bDashing)
	{
		E.ReplanIn -= Dt;
		if (E.ReplanIn <= 0)
		{
			E.ReplanIn = Range(T.Replan);
			if (!E.bHasPath || !World->ClearLine(E.Pos, E.Path[FMath::Min(E.PathIndex, E.Path.Num() - 1)]))
			{
				E.bNeedPath = true;
			}
		}
	}
	return Moved.bHitWall;
}

int32 FMIEnemyField::CollectOthers(const FMIEnemy& E)
{
	Others.Reset();
	for (int32 I = 0; I < List.Num() && Others.Num() < Tune.PoolGoon; ++I)
	{
		const FMIEnemy& O = Slots[List[I]];
		if (&O == &E || O.Type != EType::Goon || !O.bAlive || O.Mode != EMIEnemyMode::Engage)
		{
			continue;
		}
		Others.Add({O.Pos.X, O.Pos.Z, O.bHasFirePos ? O.GoalFireX : O.Pos.X, O.bHasFirePos ? O.GoalFireZ : O.Pos.Z});
	}
	return Others.Num();
}

int32 FMIEnemyField::AddCandidate(int32 N, double X, double Z, ECandidate Kind, bool bCover, const FMIEnemy& E, const FVector& TargetPos, const FVector& TargetEye, bool bStand)
{
	const FMIGoonTune& T = Tune.Goon;
	if (N >= MaxCandidates)
	{
		return N;
	}
	if (!InFireBand(Hypot(X - TargetPos.X, Z - TargetPos.Z), T) || !World->IsWalkable(X, Z))
	{
		return N;
	}
	if (E.bPickAway && Hypot(X - E.Pos.X, Z - E.Pos.Z) < T.RepickMinMove)
	{
		return N;
	}
	if (bStand && World->GroundHeight(X, Z, TargetPos.Y + 0.3) > E.Pos.Y + T.InvElevated)
	{
		return N;
	}
	FCandidate& C = Candidates[N];
	C.X = X;
	C.Z = Z;
	C.Kind = Kind;
	C.bCover = bCover;
	C.bSight = World->LineOfSight(FVector(X, E.Pos.Y + T.GunHeight, Z), TargetEye);
	return N + 1;
}

bool FMIEnemyField::PickFirePosition(FMIEnemy& E)
{
	const FMIGoonTune& T = Tune.Goon;
	int32 N = 0;
	if (Level)
	{
		for (const FMILevelPoint& Cv : Level->Cover)
		{
			if (FMath::Abs(Cv.Pos.Y - E.Pos.Y) > T.CoverMaxStep)
			{
				continue;
			}
			N = AddCandidate(N, Cv.Pos.X, Cv.Pos.Z, ECandidate::Authored, true, E, Player.Pos, Player.Eye, false);
		}
	}
	for (int32 I = 0; I < T.RepickRandomPoints; ++I)
	{
		const double Angle = Random() * UE_DOUBLE_PI * 2.0;
		const double R = T.RangeMin + (T.RangeMax - T.RangeMin) * FMath::Sqrt(Random());
		N = AddCandidate(N, Player.Pos.X + FMath::Cos(Angle) * R, Player.Pos.Z + FMath::Sin(Angle) * R, ECandidate::Random, false, E, Player.Pos, Player.Eye, false);
	}
	const double Side = FMath::Atan2(E.Pos.X - Player.Pos.X, E.Pos.Z - Player.Pos.Z);
	for (int32 I = 0; I < T.RepickArcPoints; ++I)
	{
		const double Angle = Side + T.RepickArc * ((static_cast<double>(I) / (T.RepickArcPoints - 1)) * 2.0 - 1.0) + (Random() - 0.5) * 0.3;
		const double R = Range(T.RepickArcRange);
		N = AddCandidate(N, Player.Pos.X + FMath::Sin(Angle) * R, Player.Pos.Z + FMath::Cos(Angle) * R, ECandidate::Arc, false, E, Player.Pos, Player.Eye, false);
	}
	E.bWantPick = false;
	E.bPickAway = false;
	E.PickX = Player.Pos.X;
	E.PickZ = Player.Pos.Z;
	E.Bursts = 0;
	E.BurstsToMove = Random() < T.BurstsBeforeMoveOne ? 1 : 2;
	if (N == 0)
	{
		return false;
	}
	CollectOthers(E);
	int32 Best = 0;
	double BestCost = Inf;
	for (int32 I = 0; I < N; ++I)
	{
		const double Cost = FirePositionCost(Candidates[I], E.Pos.X, E.Pos.Z, Player.Pos.X, Player.Pos.Z, Others, Random(), T);
		if (Cost < BestCost)
		{
			BestCost = Cost;
			Best = I;
		}
	}
	E.bHasFirePos = true;
	E.GoalFireX = Candidates[Best].X;
	E.GoalFireZ = Candidates[Best].Z;
	E.bAtCover = Candidates[Best].bCover && Candidates[Best].bSight;
	return true;
}

void FMIEnemyField::PickStand(FMIEnemy& E)
{
	const FMIGoonTune& T = Tune.Goon;
	const FVector Lk = E.LastKnown;
	E.bWantStand = false;
	E.bPickAway = false;
	E.StandForX = Lk.X;
	E.StandForY = Lk.Y;
	E.StandForZ = Lk.Z;
	const FVector Eye(Lk.X, Lk.Y + T.EyeHeight, Lk.Z);
	int32 N = 0;
	if (Level)
	{
		for (const FMILevelPoint& Cv : Level->Cover)
		{
			if (FMath::Abs(Cv.Pos.Y - E.Pos.Y) > T.CoverMaxStep)
			{
				continue;
			}
			N = AddCandidate(N, Cv.Pos.X, Cv.Pos.Z, ECandidate::Authored, true, E, Lk, Eye, true);
		}
	}
	for (int32 I = 0; I < T.RepickRandomPoints * 2; ++I)
	{
		const double Angle = Random() * UE_DOUBLE_PI * 2.0;
		const double R = T.RangeMin + (T.RangeMax - T.RangeMin) * FMath::Sqrt(Random());
		N = AddCandidate(N, Lk.X + FMath::Cos(Angle) * R, Lk.Z + FMath::Sin(Angle) * R, ECandidate::Random, false, E, Lk, Eye, true);
	}
	const double Side = FMath::Atan2(E.Pos.X - Lk.X, E.Pos.Z - Lk.Z);
	for (int32 I = 0; I < T.RepickArcPoints; ++I)
	{
		const double Angle = Side + T.RepickArc * ((static_cast<double>(I) / (T.RepickArcPoints - 1)) * 2.0 - 1.0) + (Random() - 0.5) * 0.3;
		const double R = Range(T.RepickArcRange);
		N = AddCandidate(N, Lk.X + FMath::Sin(Angle) * R, Lk.Z + FMath::Cos(Angle) * R, ECandidate::Arc, false, E, Lk, Eye, true);
	}
	E.bHasStand = N > 0;
	if (!E.bHasStand)
	{
		return;
	}
	CollectOthers(E);
	int32 Best = 0;
	double BestCost = Inf;
	for (int32 I = 0; I < N; ++I)
	{
		const double Cost = FirePositionCost(Candidates[I], E.Pos.X, E.Pos.Z, Lk.X, Lk.Z, Others, Random(), T);
		if (Cost < BestCost)
		{
			BestCost = Cost;
			Best = I;
		}
	}
	E.StandX = Candidates[Best].X;
	E.StandZ = Candidates[Best].Z;
	E.bStandSight = Candidates[Best].bSight;
}

void FMIEnemyField::Pick(FMIEnemy& E)
{
	const FMIGoonTune& T = Tune.Goon;
	if (!PickFirePosition(E))
	{
		const double D = Hypot(Player.Pos.X - E.Pos.X, Player.Pos.Z - E.Pos.Z);
		if (D <= T.RangeMax)
		{
			E.bHasFirePos = false;
			if (E.Sub == EMIGoonSub::Move)
			{
				ToAim(E);
			}
			return;
		}
		const double K = (D - (T.RangeMin + T.RangeMax) * 0.5) / D;
		E.GoalFireX = E.Pos.X + (Player.Pos.X - E.Pos.X) * K;
		E.GoalFireZ = E.Pos.Z + (Player.Pos.Z - E.Pos.Z) * K;
		E.bHasFirePos = true;
		E.bAtCover = false;
	}
	if (Hypot(E.GoalFireX - E.Pos.X, E.GoalFireZ - E.Pos.Z) < 0.7)
	{
		if (E.Sub == EMIGoonSub::Move)
		{
			ToAim(E);
		}
		return;
	}
	if (E.Sub == EMIGoonSub::Aim || E.Sub == EMIGoonSub::Cool || E.Sub == EMIGoonSub::Move)
	{
		E.Sub = EMIGoonSub::Move;
		E.SubT = 0;
		E.bHasGoal = false;
		SetGoal(E, E.GoalFireX, E.GoalFireZ);
	}
}

void FMIEnemyField::ToAim(FMIEnemy& E)
{
	E.Sub = EMIGoonSub::Aim;
	E.SubT = 0;
	ClearGoal(E);
	E.NoSight = E.Waited = E.TooClose = 0;
}

void FMIEnemyField::Relocate(FMIEnemy& E)
{
	E.bWantPick = true;
	E.bPickAway = true;
	E.NoSight = E.Waited = E.TooClose = 0;
}

void FMIEnemyField::Fire(FMIEnemy& E)
{
	const FMIGoonTune& T = Tune.Goon;
	const FVector From(E.Pos.X, E.Pos.Y + T.GunHeight, E.Pos.Z);
	FVector To(Player.Pos.X, Player.Pos.Y + (Player.bCrouching ? FMath::Min(0.8, T.AimHeight) : T.AimHeight), Player.Pos.Z);
	double SpreadY = 1;
	if (Player.Pos.Y > E.Pos.Y + T.InvElevated && !World->LineOfSight(From, To))
	{
		To.Y = Player.Eye.Y - T.OverCoverBelow;
		if (!World->LineOfSight(From, To))
		{
			To.Y = Player.Eye.Y;
		}
		SpreadY = T.OverCoverSpreadY;
	}
	FVector Dir = Normalised(To - From);
	const double Spread = AimSpread(T.SpreadFar, T.SpreadNear, E.Exposure, PlayerSpeed, T.SpreadPerSpeed);
	Dir.X += (Random() * 2.0 - 1.0) * Spread;
	Dir.Y += (Random() * 2.0 - 1.0) * Spread * SpreadY;
	Dir.Z += (Random() * 2.0 - 1.0) * Spread;
	Dir = Normalised(Dir);
	if (Host)
	{
		Host->Hitscan(E.Id, From, Dir, T.ShotRange, T.ShotDamage * ScaleDamage);
	}
	Emit(FMIEnemyEvent::EKind::Fire, E, From, Dir);
	E.LastActive = Now;
}

void FMIEnemyField::StartRush(FMIEnemy& E)
{
	CancelAttack(E);
	E.Sub = EMIGoonSub::Windup;
	E.SubT = 0;
	E.bRushHit = false;
	ClearGoal(E);
	Emit(FMIEnemyEvent::EKind::Melee, E, E.Pos);
	PendingEvents.Last().Phase = TEXT("windup");
	E.LastActive = Now;
}

void FMIEnemyField::SwingPipe(FMIEnemy& E)
{
	if (E.Swing >= 0)
	{
		return;
	}
	E.Swing = 0;
	Emit(FMIEnemyEvent::EKind::Melee, E, E.Pos);
	PendingEvents.Last().Phase = TEXT("strike");
}

void FMIEnemyField::GoonPatrol(FMIEnemy& E, double Dt)
{
	const FMIGoonTune& T = Tune.Goon;
	E.Scan += Dt;
	E.LookYawRel = FMath::Sin(E.Scan * 0.55) * 0.9;
	E.WantSpeed = T.PatrolSpeed;
	if (E.Wait > 0)
	{
		E.Wait -= Dt;
		E.WantSpeed = 0;
		return;
	}
	if (!E.bHasGoal)
	{
		FVector Point;
		if (World->RandomPoint(E.Home, T.PatrolRadius, Point))
		{
			SetGoal(E, Point.X, Point.Z);
		}
		else
		{
			E.Wait = 1;
		}
	}
	else if (E.bArrived || E.PathFails > 1)
	{
		ClearGoal(E);
		E.Wait = Range(T.PatrolWait);
	}
}

void FMIEnemyField::GoonInvestigate(FMIEnemy& E, double Dt)
{
	const FMIGoonTune& T = Tune.Goon;
	const FVector Lk = E.LastKnown;
	const double Dx = Lk.X - E.Pos.X, Dz = Lk.Z - E.Pos.Z;
	const double D = Hypot(Dx, Dz);
	const double Bearing = FMath::Atan2(-Dx, -Dz);
	E.LookYawRel = AngleDelta(E.Yaw, Bearing);
	double Gx = Lk.X, Gz = Lk.Z;
	double Stop = T.InvStopWithin;
	const bool bElevated = Lk.Y > E.Pos.Y + T.InvElevated;
	if (bElevated)
	{
		if (!E.bWantStand && (!E.bHasStand || FMath::Abs(Lk.X - E.StandForX) + FMath::Abs(Lk.Y - E.StandForY) + FMath::Abs(Lk.Z - E.StandForZ) > T.InvRestand))
		{
			E.bWantStand = true;
		}
		if (E.bHasStand && !E.bWantStand)
		{
			Gx = E.StandX;
			Gz = E.StandZ;
			Stop = 0.7;
		}
		else if (World->GroundHeight(E.Pos.X, E.Pos.Z, Lk.Y + 0.3) > E.Pos.Y + T.InvElevated)
		{
			Stop = Inf;
		}
		else
		{
			Stop = T.InvStandFallback;
		}
		E.LookPitch = FMath::Atan2(Lk.Y - E.Pos.Y, FMath::Max(D, 0.5));
	}
	const double Gd = Gx == Lk.X && Gz == Lk.Z ? D : Hypot(Gx - E.Pos.X, Gz - E.Pos.Z);
	if (Gd > Stop && !(E.bArrived && FMath::Abs(E.GoalX - Gx) < 0.3 && FMath::Abs(E.GoalZ - Gz) < 0.3) && E.PathFails < 2)
	{
		SetGoal(E, Gx, Gz);
		const bool bStalking = D <= T.InvStalkWithin;
		E.WantSpeed = bStalking ? T.StalkSpeed : T.RunSpeed;
		if (bStalking)
		{
			E.WantAim = 0.85;
			E.WantCrouch = 0.4;
			E.AimYaw = E.Yaw;
		}
		E.Sweep = 0;
		return;
	}
	E.WantSpeed = 0;
	if (E.Sweep == 0)
	{
		E.SweepBase = D > 0.5 ? Bearing : E.Yaw;
	}
	E.Sweep += Dt;
	if (bElevated && E.bHasStand && !E.bStandSight && !E.bWantStand && E.Sweep > T.InvRestandAfter)
	{
		E.bWantStand = true;
		E.Sweep = 0;
	}
	E.AimYaw = WrapAngle(E.SweepBase + FMath::Sin(E.Sweep * 1.3) * T.InvSweep);
	E.bFacing = true;
	E.FaceYaw = E.AimYaw;
	E.TurnScale = 0.6;
	E.LookYawRel = AngleDelta(E.Yaw, E.AimYaw);
	E.WantAim = 0.85;
}

bool FMIEnemyField::RushClear(const FMIEnemy& E) const
{
	return World->LineOfSight(FVector(E.Pos.X, E.Pos.Y + 1.0, E.Pos.Z), FVector(Player.Pos.X, Player.Pos.Y + 1.0, Player.Pos.Z), true);
}

void FMIEnemyField::GoonEngage(FMIEnemy& E, double Dt)
{
	const FMIGoonTune& T = Tune.Goon;
	const double Dx = Player.Pos.X - E.Pos.X, Dz = Player.Pos.Z - E.Pos.Z;
	const double Dist = Hypot(Dx, Dz);
	const double Bearing = FMath::Atan2(-Dx, -Dz);
	const bool bFree = E.Sub == EMIGoonSub::Move || E.Sub == EMIGoonSub::Aim || E.Sub == EMIGoonSub::Cool;
	E.LookYawRel = AngleDelta(E.Yaw, Bearing);

	if (bFree)
	{
		if (Player.bAlive && E.RushCooldown <= 0 && Dist < T.RushRange && FMath::Abs(Player.Pos.Y - E.Pos.Y) < 1.4)
		{
			if (World->LineOfSight(FVector(E.Pos.X, E.Pos.Y + 1.2, E.Pos.Z), FVector(Player.Pos.X, Player.Pos.Y + 1.0, Player.Pos.Z)) && RushClear(E))
			{
				StartRush(E);
				return;
			}
		}
		if (!E.bHasFirePos && !E.bWantPick && E.Sub == EMIGoonSub::Move)
		{
			E.bWantPick = true;
		}
		if (E.bHasFirePos && Hypot(Player.Pos.X - E.PickX, Player.Pos.Z - E.PickZ) > T.RepickPlayerMoved)
		{
			E.bWantPick = true;
		}
	}

	auto AimAtBearing = [&]()
	{
		E.WantSpeed = 0;
		E.bFacing = true;
		E.FaceYaw = Bearing;
		E.AimYaw = WrapAngle(E.AimYaw + MI::MoveToward(0.0, AngleDelta(E.AimYaw, Bearing), T.AimRate * Dt));
		E.WantAim = 1;
	};

	switch (E.Sub)
	{
	case EMIGoonSub::Move:
		E.SubT += Dt;
		E.WantSpeed = T.RunSpeed;
		E.AimYaw = E.Yaw;
		if (E.bArrived)
		{
			ToAim(E);
		}
		else if (E.SubT > T.MoveGiveUp)
		{
			ToAim(E);
		}
		else if (E.SubT > T.MoveAimEarlyAfter && E.bSees && Dist >= T.MoveAimEarlyRange.A && Dist <= T.MoveAimEarlyRange.B && Random() < T.MoveAimEarlyChance * Dt)
		{
			ToAim(E);
		}
		else if (E.bHasGoal && E.PathFails > 1)
		{
			ToAim(E);
			Relocate(E);
		}
		break;
	case EMIGoonSub::Aim:
	case EMIGoonSub::Cool:
		E.SubT += Dt;
		AimAtBearing();
		if (E.bAtCover && T.bCoverCrouchBetweenBursts && E.Cooldown > 0.4 && Hypot(E.GoalFireX - E.Pos.X, E.GoalFireZ - E.Pos.Z) < 1.2)
		{
			E.WantCrouch = 1;
			E.WantAim = 0.3;
		}
		if (E.bSees)
		{
			E.NoSight = 0;
			if (Dist < T.HoldTooClose)
			{
				E.TooClose += Dt;
				if (E.TooClose > T.HoldTooCloseTime)
				{
					Relocate(E);
					E.TooClose = 0;
				}
			}
			else
			{
				E.TooClose = 0;
			}
			if (E.Cooldown <= 0 && !E.bWantPick)
			{
				if (FMath::Abs(AngleDelta(E.AimYaw, Bearing)) < T.HoldAimTolerance && RequestToken(E))
				{
					E.Sub = EMIGoonSub::Telegraph;
					E.Telegraph = T.Telegraph;
					E.Waited = 0;
					Emit(FMIEnemyEvent::EKind::Telegraph, E, E.Pos);
					PendingEvents.Last().Duration = T.Telegraph;
				}
				else
				{
					E.Waited += Dt;
					if (E.Waited > T.HoldMaxWait)
					{
						Relocate(E);
					}
				}
			}
		}
		else
		{
			E.NoSight += Dt;
			if (E.NoSight > T.HoldNoSightTime)
			{
				Relocate(E);
				E.NoSight = 0;
			}
		}
		break;
	case EMIGoonSub::Telegraph:
	{
		AimAtBearing();
		E.Telegraph -= Dt;
		const double K = 1.0 - FMath::Max(0.0, E.Telegraph) / T.Telegraph;
		E.LampWant = 1.5 + 14.0 * K * K;
		if (E.Telegraph <= 0)
		{
			E.Sub = EMIGoonSub::Burst;
			E.BurstLeft = T.Burst;
			E.BurstTimer = 0;
		}
		break;
	}
	case EMIGoonSub::Burst:
		AimAtBearing();
		E.LampWant = 6;
		E.BurstTimer -= Dt;
		while (E.BurstLeft > 0 && E.BurstTimer <= 0)
		{
			Fire(E);
			E.BurstLeft--;
			E.BurstTimer += T.BurstGap;
		}
		if (E.BurstLeft == 0)
		{
			ReleaseToken(E);
			E.Cooldown = Range(T.Cooldown) * ScaleCooldown;
			E.Bursts++;
			E.Waited = E.NoSight = 0;
			E.Sub = EMIGoonSub::Cool;
			E.SubT = 0;
			if (E.Bursts >= E.BurstsToMove)
			{
				Relocate(E);
			}
		}
		break;
	case EMIGoonSub::Windup:
		E.SubT += Dt;
		E.WantSpeed = 0;
		E.bFacing = true;
		E.FaceYaw = Bearing;
		E.TurnScale = 3;
		E.RushPhase = 1;
		E.RushK = FMath::Min(1.0, E.SubT / T.RushWindup);
		if (E.SubT >= T.RushWindup)
		{
			E.Sub = EMIGoonSub::Lunge;
			E.SubT = 0;
			E.Yaw = Bearing;
		}
		break;
	case EMIGoonSub::Lunge:
		E.SubT += Dt;
		E.RushPhase = 2;
		E.RushK = FMath::Min(1.0, E.SubT / T.RushTime);
		if (!E.bRushHit && Player.bAlive && Dist < T.RushReach && FMath::Abs(Player.Pos.Y - E.Pos.Y) < 1.3 && RushClear(E))
		{
			E.bRushHit = true;
			SwingPipe(E);
			if (Host)
			{
				Host->DamagePlayer(T.RushDamage * ScaleDamage, FVector(E.Pos.X, E.Pos.Y + 1.3, E.Pos.Z), TEXT("melee"));
			}
			E.Sub = EMIGoonSub::Recover;
			E.SubT = 0;
		}
		else
		{
			if (E.SubT > T.RushTime * 0.6)
			{
				SwingPipe(E);
			}
			if (E.SubT >= T.RushTime || (E.SubT > 0.08 && E.Speed < T.RushSpeed * 0.3))
			{
				SwingPipe(E);
				E.Sub = EMIGoonSub::Recover;
				E.SubT = 0;
			}
		}
		E.LastActive = Now;
		break;
	case EMIGoonSub::Recover:
		E.SubT += Dt;
		E.WantSpeed = 0;
		E.MoveSpeed = MI::MoveToward(E.MoveSpeed, 0.0, 40.0 * Dt);
		E.RushPhase = 3;
		E.RushK = FMath::Min(1.0, E.SubT / T.RushRecovery);
		if (E.SubT >= T.RushRecovery)
		{
			E.RushCooldown = T.RushCooldown;
			E.Sub = EMIGoonSub::Aim;
			E.SubT = 0;
			E.AimYaw = E.Yaw;
			Relocate(E);
		}
		break;
	}
}

void FMIEnemyField::GoonUpdate(FMIEnemy& E, double Dt)
{
	const FMIGoonTune& T = Tune.Goon;
	if (E.Sub != EMIGoonSub::Telegraph && E.Sub != EMIGoonSub::Burst)
	{
		E.Cooldown -= Dt;
	}
	E.RushCooldown -= Dt;
	E.WantCrouch = 0;
	E.WantAim = 0;
	E.LampWant = 0;
	E.RushPhase = 0;
	E.WantSpeed = 0;
	E.bFacing = false;
	E.TurnScale = 1;
	E.LookPitch = 0;

	if (E.bPassive)
	{
		E.Scan += Dt;
		E.LookYawRel = FMath::Sin(E.Scan * 0.55) * 0.7;
	}
	else if (E.Mode == EMIEnemyMode::Engage)
	{
		GoonEngage(E, Dt);
	}
	else if (E.Mode == EMIEnemyMode::Patrol)
	{
		GoonPatrol(E, Dt);
	}
	else
	{
		GoonInvestigate(E, Dt);
	}

	Locomote(E, Dt);
	if (E.Stuck > T.StuckTime)
	{
		E.Stuck = 0;
		E.StuckCount++;
		if (E.Mode == EMIEnemyMode::Engage)
		{
			if (E.Sub == EMIGoonSub::Move)
			{
				Relocate(E);
			}
		}
		else if (E.Mode == EMIEnemyMode::Patrol)
		{
			ClearGoal(E);
			E.Wait = 0.5;
		}
		else if (E.StuckCount > 2)
		{
			E.bArrived = true;
		}
		else
		{
			E.bNeedPath = true;
		}
	}

	E.AimYawRel = AngleDelta(E.Yaw, E.AimYaw);
	if (E.Mode == EMIEnemyMode::Engage && Player.bAlive)
	{
		const double D = Hypot(Player.Pos.X - E.Pos.X, Player.Pos.Z - E.Pos.Z);
		E.AimPitch = FMath::Atan2(Player.Pos.Y + T.AimHeight - (E.Pos.Y + T.GunHeight), FMath::Max(D, 0.5));
		E.LookPitch = FMath::Atan2(Player.Eye.Y - (E.Pos.Y + T.EyeHeight), FMath::Max(D, 0.5));
	}
	else
	{
		E.AimPitch = 0;
	}
	// The part of goon-anim.js poseGoon that the rules read back: the head's turn (sight) and the swing latch.
	if (E.RushPhase != 2)
	{
		E.Swing = -1;
	}
	E.HeadYaw = MI::Damp(E.HeadYaw, FMath::Clamp(E.LookYawRel, -1.4, 1.4), 7.0, Dt);
	E.HeadPitch = MI::Damp(E.HeadPitch, FMath::Clamp(E.LookPitch, -0.6, 0.6), 7.0, Dt);
	E.FlinchAge += Dt;
}

void FMIEnemyField::GoonKilled(FMIEnemy& E, const TOptional<FVector>& Dir)
{
	double Dx = 0, Dz = 1;
	if (Dir.IsSet())
	{
		const double C = FMath::Cos(E.Yaw), S = FMath::Sin(E.Yaw);
		Dx = Dir->X * C - Dir->Z * S;
		Dz = Dir->X * S + Dir->Z * C;
	}
	E.DeathDir = FVector(Dx, 0, Dz);
	E.DeathT = 0;
	E.bDusted = false;
	E.MoveSpeed = E.Speed = 0;
	E.LampWant = 0;
}

bool FMIEnemyField::GoonDying(FMIEnemy& E, double Dt)
{
	E.DeathT += Dt;
	if (!E.bDusted && E.DeadTime > Tune.Goon.Collapse * 0.7)
	{
		E.bDusted = true;
	}
	return E.DeathT >= Tune.Goon.Collapse;
}

bool FMIEnemyField::GoonBody(FMIEnemy& E, double Dt)
{
	E.BodyAge += Dt;
	if (!E.bFading && E.BodyAge > Tune.Goon.BodyStay)
	{
		E.bFading = true;
	}
	if (!E.bFading)
	{
		return false;
	}
	E.Fade = FMath::Min(1.0, E.Fade + Dt / Tune.Goon.BodyFade);
	return E.Fade >= 1;
}

// ================================================================================================== Buzzard

void FMIEnemyField::BuzzardPose(FMIEnemy& E, double Dt)
{
	E.RotorSpeed = MI::Damp(E.RotorSpeed, E.RotorWant, E.RotorWant < E.RotorSpeed ? 1.6 : 6.0, Dt);
	E.RotorAngle = FMath::Fmod(E.RotorAngle + Model.BladeRate * E.RotorSpeed * Dt, UE_DOUBLE_PI * 2.0);
	E.EyeYaw = MI::Damp(E.EyeYaw, FMath::Max(-1.5, FMath::Min(1.5, E.EyeYawWant)), 14.0, Dt);
	E.EyePitch = MI::Damp(E.EyePitch, FMath::Max(-1.35, FMath::Min(0.5, E.EyePitchWant)), 14.0, Dt);
	E.Lamp = MI::Damp(E.Lamp, E.LampWant, E.LampWant > E.Lamp ? 30.0 : 10.0, Dt);
	E.Flash = FMath::Max(0.0, E.Flash - 7.0 * Dt);
}

void FMIEnemyField::BuzzardPlace(FMIEnemy& E)
{
	double Gimbal[9], Rot[9];
	EulerMatrix(E.EyePitch, E.EyeYaw, 0.0, Gimbal);
	EulerMatrix(E.Pitch, E.Yaw, E.Roll, Rot);
	const FVector EyeModel = Model.GimbalPivot + Mul(Gimbal, Model.Eye);
	const FVector GunModel = Model.GimbalPivot + Mul(Gimbal, Model.Muzzle);
	E.Eye = E.Pos + Mul(Rot, EyeModel);
	E.Gun = E.Pos + Mul(Rot, GunModel);
}

void FMIEnemyField::BuzzardSpawn(FMIEnemy& E, const FVector& At, const FMIEnemySpawnOptions& Opts)
{
	const FMIBuzzardTune& T = Tune.Buzzard;
	E.Pos = At;
	const double Ground = World->GroundHeight(At.X, At.Z, At.Y + 0.5);
	if (E.Pos.Y < Ground + T.MinHeight)
	{
		E.Pos.Y = Ground + 5.0 + Random() * 0.6;
	}
	const FMIDeck* El = Level ? &Level->Deck : nullptr;
	if (El && At.X > El->MinX && At.X < El->MaxX && At.Z > El->MinZ - 1 && At.Z < El->MaxZ + 1 && E.Pos.Y > El->Y - T.DeckUnder && E.Pos.Y < El->Y + T.DeckThickness + 1)
	{
		E.Pos.Y = El->Y - T.DeckUnder;
	}
	E.Vel = FVector::ZeroVector;
	Solids.Refresh(*World, El);
	const FMIFlightK K = Tune.Flight();
	PushOut(Solids, E.Pos, E.Vel, K, &World->GetBounds());
	E.Home = E.Pos;
	E.Yaw = Opts.Yaw.IsSet() ? Opts.Yaw.GetValue() : Random() * UE_DOUBLE_PI * 2.0;
	E.Cooldown = Range(T.FirstCooldown);
	E.Altitude = Range(T.OrbitAltitude);
	E.OrbitRadius = Range(T.OrbitRadius);
	E.OrbitAngle = Random() * UE_DOUBLE_PI * 2.0;
	E.OrbitDir = Random() < 0.5 ? -1 : 1;
	E.PatrolRadius = Range(T.PatrolRadius);
	E.RethinkIn = Range(T.OrbitRethink);
	E.FlipIn = 0;
	E.Push = FVector::ZeroVector;
	E.StuckX = E.Pos.X;
	E.StuckY = E.Pos.Y;
	E.StuckZ = E.Pos.Z;
	E.StuckT = E.DetourIn = 0;
	E.Ceiling = Inf;
	E.CeilingAge = 0;
	E.Feeler = E.Slot % 3;
	E.Pitch = E.Roll = E.KickPitch = E.KickRoll = 0;
	E.Wobble = Random() * 10.0;
	E.BurstLeft = 0;
	E.BurstTimer = 0;
	E.SmokeIn = E.SparkIn = 0;
	E.Spin = 0;
	E.Strobe = Random() * Model.StrobePeriod;
	E.RotorWant = 1;
	E.EyeYawWant = E.EyePitchWant = 0;
	E.LampWant = 0.6;
	E.RotorSpeed = 1;
	E.RotorAngle = E.Id * 1.7;
	E.EyeYaw = E.EyePitch = 0;
	E.Lamp = E.Flash = 0;
	E.LostRotor = -1;
	BuzzardPose(E, 0.0);
	BuzzardPlace(E);
}

double FMIEnemyField::Target(FMIEnemy& E, double Dt)
{
	const FMIBuzzardTune& T = Tune.Buzzard;
	if (E.Mode == EMIEnemyMode::Engage)
	{
		if (E.SinceSeen > T.OrbitLostAfter)
		{
			Want = FVector(E.LastKnown.X, E.LastKnown.Y + E.Altitude + 1.0, E.LastKnown.Z);
			return T.MaxSpeed;
		}
		const bool bSteady = E.Telegraph > 0 || E.BurstLeft > 0;
		E.OrbitAngle += (E.OrbitDir * (bSteady ? T.OrbitSpeedFiring : T.OrbitSpeed) * Dt) / E.OrbitRadius;
		E.RethinkIn -= Dt;
		if (E.RethinkIn <= 0)
		{
			E.RethinkIn = Range(T.OrbitRethink);
			if (Random() < T.OrbitReverseChance)
			{
				E.OrbitDir = -E.OrbitDir;
			}
			E.OrbitRadius = FMath::Clamp(E.OrbitRadius + (Random() * 2.0 - 1.0) * T.OrbitRadiusDrift, T.OrbitRadiusClamp.A, T.OrbitRadiusClamp.B);
		}
		Want = FVector(Player.Pos.X + FMath::Cos(E.OrbitAngle) * E.OrbitRadius, Player.Pos.Y + E.Altitude, Player.Pos.Z + FMath::Sin(E.OrbitAngle) * E.OrbitRadius);
		if (Level)
		{
			for (const FMIRoom& B : Level->Rooms)
			{
				if (!InRoom(B, Player.Pos, 0, true) || !InRoom(B, E.Pos, 0, true))
				{
					continue;
				}
				Want.X = FMath::Clamp(Want.X, B.Min.X + Model.RoomMargin, B.Max.X - Model.RoomMargin);
				Want.Z = FMath::Clamp(Want.Z, B.Min.Z + Model.RoomMargin, B.Max.Z - Model.RoomMargin);
			}
		}
		return T.MaxSpeed;
	}
	if (E.Mode == EMIEnemyMode::Patrol)
	{
		E.OrbitAngle += E.OrbitDir * T.PatrolTurn * Dt;
		Want = FVector(E.Home.X + FMath::Cos(E.OrbitAngle) * E.PatrolRadius, E.Home.Y, E.Home.Z + FMath::Sin(E.OrbitAngle) * E.PatrolRadius);
		return T.PatrolSpeed;
	}
	E.OrbitAngle += E.OrbitDir * T.InvTurn * Dt;
	Want = FVector(E.LastKnown.X + FMath::Cos(E.OrbitAngle) * T.InvRadius, E.LastKnown.Y + FMath::Min(E.Altitude, T.InvMaxHeight), E.LastKnown.Z + FMath::Sin(E.OrbitAngle) * T.InvRadius);
	return T.InvestigateSpeed;
}

void FMIEnemyField::Feel(FMIEnemy& E, double Speed)
{
	const FMIBuzzardTune& T = Tune.Buzzard;
	E.Feeler = (E.Feeler + 1) % 3;
	FMIRayHit Hit;
	if (E.Feeler == 0)
	{
		if (Speed < 0.3)
		{
			return;
		}
		const FVector Dir(E.Vel.X / Speed, E.Vel.Y / Speed, E.Vel.Z / Speed);
		const double Reach = T.FeelForward + T.FeelForwardPerSpeed * Speed;
		if (!World->Raycast(E.Pos, Dir, Reach, Hit))
		{
			return;
		}
		const double K = (1.0 - Hit.Dist / Reach) * T.Accel * 1.6;
		E.Push.X += Hit.Normal.X * K;
		E.Push.Y += Hit.Normal.Y * K + K * 0.5;
		E.Push.Z += Hit.Normal.Z * K;
		if (Hit.Dist < Reach * 0.5 && E.FlipIn <= 0)
		{
			E.OrbitDir = -E.OrbitDir;
			E.FlipIn = 1.2;
		}
	}
	else if (E.Feeler == 1)
	{
		if (World->Raycast(E.Pos, FVector(0, -1, 0), T.FeelDown, Hit))
		{
			E.Push.Y += (1.0 - Hit.Dist / T.FeelDown) * T.Accel * 1.5;
		}
	}
	else if (World->Raycast(E.Pos, FVector(0, 1, 0), T.FeelUp, Hit))
	{
		E.Ceiling = Hit.Point.Y;
		E.CeilingAge = 0;
	}
	else if (E.CeilingAge > 0.5)
	{
		E.Ceiling = Inf;
	}
}

bool FMIEnemyField::Slide(FMIEnemy& E, int32 Axis, double Dt, double Clear, double Bounce, const FSolid** HitPole)
{
	const double V = E.Vel[Axis];
	if (V == 0)
	{
		return false;
	}
	const double Sign = V > 0 ? 1.0 : -1.0;
	FVector Dir = FVector::ZeroVector;
	Dir[Axis] = Sign;
	const double TravelDist = FMath::Abs(V) * Dt;
	double Move = TravelDist;
	bool bStopped = false;
	FMIRayHit Hit;
	if (World->Raycast(E.Pos, Dir, TravelDist + Clear, Hit))
	{
		Move = FMath::Max(0.0, Hit.Dist - Clear);
		if (Move < TravelDist)
		{
			bStopped = true;
			E.Vel[Axis] = V * Bounce;
			LastHit = Hit;
		}
		else
		{
			Move = TravelDist;
		}
	}
	E.Pos[Axis] += Sign * Move;
	return bStopped;
}

void FMIEnemyField::Detour(FMIEnemy& E, double Dt)
{
	const FMIBuzzardTune& T = Tune.Buzzard;
	if (E.DetourIn > 0)
	{
		E.DetourIn -= Dt;
		Want = FVector(E.DetourX, E.DetourY, E.DetourZ);
		return;
	}
	const bool bFar = FMath::Abs(Want.X - E.Pos.X) + FMath::Abs(Want.Y - E.Pos.Y) + FMath::Abs(Want.Z - E.Pos.Z) > T.DetourFar;
	const double Dx = E.Pos.X - E.StuckX, Dy = E.Pos.Y - E.StuckY, Dz = E.Pos.Z - E.StuckZ;
	if (!bFar || Dx * Dx + Dy * Dy + Dz * Dz > T.DetourMoved * T.DetourMoved)
	{
		E.StuckX = E.Pos.X;
		E.StuckY = E.Pos.Y;
		E.StuckZ = E.Pos.Z;
		E.StuckT = 0;
		return;
	}
	E.StuckT += Dt;
	if (E.StuckT < T.DetourAfter)
	{
		return;
	}
	E.StuckT = 0;
	const double Up = FMath::Min(FMath::Min(T.MaxAltitude, E.Ceiling - T.CeilingClearance), E.Pos.Y + T.DetourUp);
	for (int32 K = 0; K < 6; ++K)
	{
		const double A = Random() * UE_DOUBLE_PI * 2.0;
		const FVector To(E.Pos.X + FMath::Cos(A) * T.DetourDistance, FMath::Max(E.Pos.Y, Up), E.Pos.Z + FMath::Sin(A) * T.DetourDistance);
		if (K < 5 && !World->LineOfSight(E.Pos, To, true))
		{
			continue;
		}
		E.DetourX = To.X;
		E.DetourY = To.Y;
		E.DetourZ = To.Z;
		E.DetourIn = T.DetourTime;
		return;
	}
}

void FMIEnemyField::Fly(FMIEnemy& E, double Dt)
{
	const FMIBuzzardTune& T = Tune.Buzzard;
	const FMIFlightK K = Tune.Flight();
	const FMIDeck* El = Level ? &Level->Deck : nullptr;
	Solids.Refresh(*World, El);
	Cap = Target(E, Dt);
	int32 Indoors = 0;
	if (Level)
	{
		for (int32 R = 0; R < Level->Rooms.Num() && !Indoors; ++R)
		{
			Indoors = RouteIndoors(E.Pos, Want, Level->Rooms[R]);
		}
	}
	const bool bDamaged = E.Hp < E.MaxHp * T.DamagedBelow;

	const double Ground = GroundUnder(Solids, E.Pos, 0.3);
	E.CeilingAge += Dt;
	const double Top = FMath::Min(T.MaxAltitude, E.Ceiling - T.CeilingClearance);
	Want.Y = FMath::Min(FMath::Max(Want.Y, Ground + T.MinHeight), Top);
	const int32 Plan = PlanAroundDeck(E.Pos, Want, El, K);
	const double Dm = T.DeckMargin;
	const bool bUnderDeck = El && E.Pos.Y < El->Y && E.Pos.X > El->MinX - Dm && E.Pos.X < El->MaxX + Dm && E.Pos.Z > El->MinZ - Dm && E.Pos.Z < El->MaxZ + Dm;
	if (!bUnderDeck && Indoors != 2)
	{
		double Height;
		ClimbOver(Solids, E.Pos, Want, K, ClimbHitSolid, Height);
		if ((Plan == 1 || Plan == 3) && El)
		{
			const double Ox = E.Pos.X < El->MinX - Dm ? El->MinX - Dm - E.Pos.X : (E.Pos.X > El->MaxX + Dm ? E.Pos.X - El->MaxX - Dm : 0.0);
			const double Oz = E.Pos.Z < El->MinZ - Dm ? El->MinZ - Dm - E.Pos.Z : (E.Pos.Z > El->MaxZ + Dm ? E.Pos.Z - El->MaxZ - Dm : 0.0);
			const double Free = El->Y - T.DeckUnder + 0.6;
			if (Ox * Ox + Oz * Oz <= (T.DeckHold + 1.0) * (T.DeckHold + 1.0) && Want.Y > Free)
			{
				if (Plan == 1)
				{
					DeckEntry(E.Pos, Want, *El, K);
					ClimbOver(Solids, E.Pos, Want, K, ClimbHitSolid, Height);
				}
				if (Want.Y > Free && ClimbHitSolid != INDEX_NONE)
				{
					DeckSlide(E.Pos, Want, Solids.List[ClimbHitSolid], K);
				}
			}
		}
		if (Want.Y > Top)
		{
			Want.Y = Top;
		}
	}
	Detour(E, Dt);

	double Ax = T.PullH.A * (Want.X - E.Pos.X) - T.PullH.B * E.Vel.X + E.Push.X;
	double Ay = T.PullV.A * (Want.Y - E.Pos.Y) - T.PullV.B * E.Vel.Y + E.Push.Y;
	double Az = T.PullH.A * (Want.Z - E.Pos.Z) - T.PullH.B * E.Vel.Z + E.Push.Z;
	if (bDamaged)
	{
		E.Wobble += Dt;
		Ax += FMath::Sin(E.Wobble * 5.3) * T.DamagedJitter;
		Ay += FMath::Sin(E.Wobble * 7.1 + 1.0) * T.DamagedJitter * 0.7;
		Az += FMath::Cos(E.Wobble * 4.7) * T.DamagedJitter;
	}
	const double A = FMath::Sqrt(Ax * Ax + Ay * Ay + Az * Az);
	if (A > T.Accel)
	{
		const double Kk = T.Accel / A;
		Ax *= Kk;
		Ay *= Kk;
		Az *= Kk;
	}
	E.Vel.X += Ax * Dt;
	E.Vel.Y += Ay * Dt;
	E.Vel.Z += Az * Dt;
	double Speed = FMath::Sqrt(E.Vel.X * E.Vel.X + E.Vel.Y * E.Vel.Y + E.Vel.Z * E.Vel.Z);
	if (Speed > Cap)
	{
		E.Vel *= Cap / Speed;
		Speed = Cap;
	}
	E.Push *= FMath::Exp(-6.0 * Dt);
	E.FlipIn -= Dt;
	Feel(E, Speed);

	const double Px = E.Pos.X, Py = E.Pos.Y, Pz = E.Pos.Z;
	Slide(E, 0, Dt, T.Radius + 0.1, T.FeelBounce, nullptr);
	Slide(E, 2, Dt, T.Radius + 0.1, T.FeelBounce, nullptr);
	if (Slide(E, 1, Dt, T.HalfHeight + 0.2, T.FeelBounce, nullptr) && E.Vel.Y >= 0 && LastHit.Box != INDEX_NONE)
	{
		const FMIBox& Q = World->GetBoxes()[LastHit.Box];
		if (IsPole(Q.Min, Q.Max))
		{
			const double Ox = E.Pos.X - (Q.Min.X + Q.Max.X) * 0.5;
			const double Oz = E.Pos.Z - (Q.Min.Z + Q.Max.Z) * 0.5;
			const double D = FMath::Sqrt(Ox * Ox + Oz * Oz);
			E.Vel.X = D > 0.01 ? (Ox / D) * Model.PoleStep : Model.PoleStep;
			E.Vel.Z = D > 0.01 ? (Oz / D) * Model.PoleStep : 0.0;
		}
	}
	if (E.Pos.Y < Ground + T.FloorClearance)
	{
		E.Pos.Y = Ground + T.FloorClearance;
		if (E.Vel.Y < 0)
		{
			E.Vel.Y = 0;
		}
	}
	else if (E.Pos.Y > T.MaxAltitude + T.Overshoot)
	{
		E.Pos.Y = T.MaxAltitude + T.Overshoot;
		if (E.Vel.Y > 0)
		{
			E.Vel.Y = 0;
		}
	}
	const FMIBounds& B = World->GetBounds();
	const double M = T.BoundsMargin;
	if (E.Pos.X < B.MinX + M)
	{
		E.Pos.X = B.MinX + M;
		if (E.Vel.X < 0) E.Vel.X = 0;
	}
	else if (E.Pos.X > B.MaxX - M)
	{
		E.Pos.X = B.MaxX - M;
		if (E.Vel.X > 0) E.Vel.X = 0;
	}
	if (E.Pos.Z < B.MinZ + M)
	{
		E.Pos.Z = B.MinZ + M;
		if (E.Vel.Z < 0) E.Vel.Z = 0;
	}
	else if (E.Pos.Z > B.MaxZ - M)
	{
		E.Pos.Z = B.MaxZ - M;
		if (E.Vel.Z > 0) E.Vel.Z = 0;
	}
	PushOut(Solids, E.Pos, E.Vel, K, &B);
	const double Mx = E.Pos.X - Px, My = E.Pos.Y - Py, Mz = E.Pos.Z - Pz;
	if (FMath::Sqrt(Mx * Mx + My * My + Mz * Mz) > 0.02)
	{
		E.LastActive = Now;
	}

	const double Sin = FMath::Sin(E.Yaw), Cos = FMath::Cos(E.Yaw);
	const double Forward = -Ax * Sin - Az * Cos;
	const double Right = Ax * Cos - Az * Sin;
	E.KickPitch = MI::Damp(E.KickPitch, 0.0, 5.0, Dt);
	E.KickRoll = MI::Damp(E.KickRoll, 0.0, 5.0, Dt);
	double Pitch = FMath::Clamp(-Forward * Model.TiltPerAccel, -Model.MaxTilt, Model.MaxTilt) + E.KickPitch;
	double Roll = FMath::Clamp(-Right * Model.TiltPerAccel, -Model.MaxTilt, Model.MaxTilt) + E.KickRoll;
	if (bDamaged)
	{
		Pitch += FMath::Sin(E.Wobble * 9.1) * 0.1;
		Roll += FMath::Cos(E.Wobble * 7.7) * 0.13;
	}
	E.Pitch = MI::Damp(E.Pitch, Pitch, 7.0, Dt);
	E.Roll = MI::Damp(E.Roll, Roll, 7.0, Dt);
	E.RotorWant = 0.75 + 0.25 * FMath::Min(1.0, A / T.Accel);
}

void FMIEnemyField::FireBolt(FMIEnemy& E)
{
	const FMIBuzzardTune& T = Tune.Buzzard;
	const double Chest = Player.bCrouching ? FMath::Min(0.75, T.AimHeight) : T.AimHeight;
	const FVector AimAt = LeadPoint(E.Gun, FVector(Player.Pos.X, Player.Pos.Y + Chest, Player.Pos.Z), Player.Vel, T.BoltSpeed, E.Lead);
	FVector Dir = Normalised(AimAt - E.Gun);
	const bool bDamaged = E.Hp < E.MaxHp * T.DamagedBelow;
	const double Spread = AimSpread(T.SpreadFar, T.SpreadNear, E.Exposure, PlayerSpeed, T.SpreadPerSpeed, bDamaged ? T.DamagedSpread : 1.0);
	Dir.X += (Random() * 2.0 - 1.0) * Spread;
	Dir.Y += (Random() * 2.0 - 1.0) * Spread;
	Dir.Z += (Random() * 2.0 - 1.0) * Spread;
	Dir = Normalised(Dir);
	SpawnBolt(FVector(E.Pos.X, E.Gun.Y, E.Pos.Z), Dir, T.BoltDamage * ScaleDamage, E.Id);
	E.Vel += Dir * -T.RecoilPush;
	E.KickPitch += 0.06;
	E.Lamp = 12;
	Emit(FMIEnemyEvent::EKind::Fire, E, E.Gun, Dir);
	E.LastActive = Now;
}

void FMIEnemyField::Attack(FMIEnemy& E, double Dt, double Bearing, double Dist)
{
	const FMIBuzzardTune& T = Tune.Buzzard;
	if (E.Telegraph > 0)
	{
		E.Telegraph -= Dt;
		const double K = 1.0 - FMath::Max(0.0, E.Telegraph) / T.Telegraph;
		E.LampWant = 2.5 + 16.0 * K * K;
		if (E.Telegraph <= 0)
		{
			E.Telegraph = 0;
			if (E.Mode == EMIEnemyMode::Engage)
			{
				E.BurstLeft = T.Burst;
				E.BurstTimer = 0;
				E.Lead = Range(T.Lead);
			}
			else
			{
				ReleaseToken(E);
			}
		}
		return;
	}
	if (E.BurstLeft > 0)
	{
		E.LampWant = 7;
		E.BurstTimer -= Dt;
		while (E.BurstLeft > 0 && E.BurstTimer <= 0)
		{
			FireBolt(E);
			E.BurstLeft--;
			E.BurstTimer += T.BurstGap;
		}
		if (E.BurstLeft == 0)
		{
			ReleaseToken(E);
			E.Cooldown = Range(T.Cooldown) * ScaleCooldown;
		}
		return;
	}
	E.Cooldown -= Dt;
	if (E.Mode == EMIEnemyMode::Engage && E.bSees && E.Cooldown <= 0 && Dist < T.FireRange && FMath::Abs(AngleDelta(E.Yaw, Bearing)) < T.AimTolerance && RequestToken(E))
	{
		E.Telegraph = T.Telegraph;
		Emit(FMIEnemyEvent::EKind::Telegraph, E, E.Pos);
		PendingEvents.Last().Duration = T.Telegraph;
	}
}

void FMIEnemyField::BuzzardUpdate(FMIEnemy& E, double Dt)
{
	const FMIBuzzardTune& T = Tune.Buzzard;
	if (!E.bPassive)
	{
		Fly(E, Dt);
	}
	double FaceX = E.Vel.X, FaceZ = E.Vel.Z;
	double LookY = E.Pos.Y - 3.0;
	if (E.Mode == EMIEnemyMode::Engage && E.SinceSeen <= T.OrbitLostAfter)
	{
		FaceX = Player.Pos.X - E.Pos.X;
		FaceZ = Player.Pos.Z - E.Pos.Z;
		LookY = Player.Pos.Y + T.AimHeight;
	}
	else if (E.Mode != EMIEnemyMode::Patrol)
	{
		FaceX = E.LastKnown.X - E.Pos.X;
		FaceZ = E.LastKnown.Z - E.Pos.Z;
		LookY = E.LastKnown.Y + 1.0;
	}
	const double Flat = FMath::Sqrt(FaceX * FaceX + FaceZ * FaceZ);
	const double Bearing = Flat > 0.3 ? FMath::Atan2(-FaceX, -FaceZ) : E.Yaw;
	E.Yaw = WrapAngle(E.Yaw + MI::MoveToward(0.0, AngleDelta(E.Yaw, Bearing), T.YawRate * Dt));
	E.EyeYawWant = AngleDelta(E.Yaw, Bearing);
	E.EyePitchWant = FMath::Atan2(LookY - E.Pos.Y, FMath::Max(Flat, 1.0)) - E.Pitch;

	E.Strobe += Dt;
	E.LampWant = E.Mode == EMIEnemyMode::Engage ? 2.5 : (E.Mode == EMIEnemyMode::Patrol ? 0.7 : 1.3 + 0.6 * FMath::Sin(E.Strobe * 6.0));
	if (!E.bPassive)
	{
		const double Px = Player.Pos.X - E.Pos.X, Py = Player.Pos.Y - E.Pos.Y, Pz = Player.Pos.Z - E.Pos.Z;
		Attack(E, Dt, FMath::Atan2(-Px, -Pz), FMath::Sqrt(Px * Px + Py * Py + Pz * Pz));
	}
	if (E.Hp < E.MaxHp * T.DamagedBelow)
	{
		E.SmokeIn -= Dt;
		if (E.SmokeIn <= 0)
		{
			E.SmokeIn = Range(T.SmokeEvery);
		}
		E.SparkIn -= Dt;
		if (E.SparkIn <= 0)
		{
			E.SparkIn = 0.5 + Random() * 1.2;
		}
	}
	BuzzardPose(E, Dt);
	BuzzardPlace(E);
}

void FMIEnemyField::BuzzardHit(FMIEnemy& E, double Amount, const TOptional<FVector>& Dir)
{
	const FMIBuzzardTune& T = Tune.Buzzard;
	if (Dir.IsSet())
	{
		E.Vel += Dir.GetValue() * FMath::Min(T.KnockbackMax, Amount * T.KnockbackPerDamage);
	}
	E.KickPitch += (Random() * 2.0 - 1.0) * T.HitKick;
	E.KickRoll += (Random() * 2.0 - 1.0) * T.HitKick;
	E.Flash = FMath::Min(1.0, E.Flash + 0.7);
}

void FMIEnemyField::BuzzardKilled(FMIEnemy& E, const TOptional<FVector>& Dir)
{
	const FMIBuzzardTune& T = Tune.Buzzard;
	E.Vel.Y += T.DeathKickUp;
	if (Dir.IsSet())
	{
		E.Vel += Dir.GetValue() * T.DeathKickAlong;
	}
	E.Spin = (Random() < 0.5 ? -1.0 : 1.0) * 3.0;
	E.LostRotor = static_cast<int32>(FMath::FloorToDouble(Random() * 4.0)) % 4;
	E.RotorWant = 0.25;
	E.LampWant = 0.4;
	E.SmokeIn = E.SparkIn = 0;
}

bool FMIEnemyField::BuzzardDying(FMIEnemy& E, double Dt)
{
	const FMIBuzzardTune& T = Tune.Buzzard;
	E.Vel.Y -= T.FallGravity * Dt;
	E.Vel.X *= FMath::Exp(-0.4 * Dt);
	E.Vel.Z *= FMath::Exp(-0.4 * Dt);
	E.Spin += FMath::Sign(E.Spin != 0 ? E.Spin : 1.0) * 9.0 * Dt;
	E.Yaw = WrapAngle(E.Yaw + E.Spin * Dt);
	E.Pitch = MI::Damp(E.Pitch, 0.5, 2.0, Dt);
	E.Roll += E.Spin * 0.25 * Dt;
	const double Speed = Hypot(E.Vel.X, E.Vel.Y, E.Vel.Z);
	const double TravelDist = Speed * Dt;
	bool bLanded = false;
	if (Speed > 1e-3)
	{
		const FVector Dir(E.Vel.X / Speed, E.Vel.Y / Speed, E.Vel.Z / Speed);
		FMIRayHit Hit;
		if (World->Raycast(E.Pos, Dir, TravelDist + 0.25, Hit))
		{
			E.Pos += Dir * FMath::Max(0.0, Hit.Dist - 0.25);
			bLanded = true;
		}
	}
	if (!bLanded)
	{
		E.Pos += E.Vel * Dt;
	}
	if (E.DeadTime > T.FallMaxTime || E.Pos.Y < -3)
	{
		bLanded = true;
	}
	E.LampWant = E.DeadTime < 0.5 ? 1.5 * FMath::Abs(FMath::Sin(E.DeadTime * 40.0)) : 0.0;
	BuzzardPose(E, Dt);
	BuzzardPlace(E);
	return bLanded;
}

void FMIEnemyField::Burst(FMIEnemy& E)
{
	const FMIBuzzardTune& T = Tune.Buzzard;
	if (Host)
	{
		Host->Explode(E.Id, E.Pos, T.BurstRadius, T.BurstDamage, T.BurstPlayerScale);
	}
}

// ==================================================================================================== bolts

void FMIEnemyField::SpawnBolt(const FVector& From, const FVector& Dir, double Amount, int32 Owner)
{
	const int32 Capacity = BoltSlots.Num();
	int32 I = -1;
	for (int32 K = 0; K < Capacity; ++K)
	{
		const int32 Slot = (NextBolt + K) % Capacity;
		if (BoltSlots[Slot].Life <= 0)
		{
			I = Slot;
			break;
		}
	}
	if (I < 0)
	{
		I = NextBolt;
	}
	else
	{
		++LiveBoltCount;
	}
	NextBolt = (I + 1) % Capacity;
	FMIBolt& B = BoltSlots[I];
	B.P = B.O = From;
	B.D = Dir;
	B.Life = Tune.Buzzard.BoltLife;
	B.Flown = 0;
	B.Damage = Amount;
	B.Owner = Owner;
}

void FMIEnemyField::UpdateBolts(double Dt)
{
	if (LiveBoltCount == 0)
	{
		return;
	}
	const FMIBuzzardTune& T = Tune.Buzzard;
	const double Step = T.BoltSpeed * Dt;
	for (FMIBolt& B : BoltSlots)
	{
		if (B.Life <= 0)
		{
			continue;
		}
		FMIRayHit Hit;
		const bool bWorld = World->Raycast(B.P, B.D, Step, Hit);
		const double Reach = bWorld ? Hit.Dist : Step;
		if (Player.bAlive)
		{
			const FVector& P = Player.Pos;
			if ((P.X - B.P.X) * (P.X - B.P.X) + (P.Z - B.P.Z) * (P.Z - B.P.Z) < (Reach + 1.0) * (Reach + 1.0))
			{
				const double Top = Player.bCrouching ? T.BoltCrouchTop : T.BoltTop;
				const double S = SegmentHitsUpright(B.P, B.P + B.D * Reach, P.X, P.Y + T.BoltBottom, P.Y + Top, P.Z, T.BoltRadius);
				if (S >= 0)
				{
					if (Host)
					{
						Host->DamagePlayer(B.Damage, B.O, TEXT("bolt"));
					}
					B.Life = 0;
					B.Owner = 0;
					--LiveBoltCount;
					continue;
				}
			}
		}
		if (bWorld)
		{
			if (Hit.Box != INDEX_NONE && Host)
			{
				const int32 Owner = World->GetBoxes()[Hit.Box].Owner;
				if (Owner != INDEX_NONE)
				{
					Host->HitExplosive(Owner, Tune.ExplosiveHitFromEnemy);
				}
			}
			B.Life = 0;
			B.Owner = 0;
			--LiveBoltCount;
			continue;
		}
		B.P += B.D * Step;
		B.Flown += Step;
		B.Life -= Dt;
		if (B.Life <= 0)
		{
			B.Life = 0;
			B.Owner = 0;
			--LiveBoltCount;
		}
	}
}

int32 FMIEnemyField::LiveBolts() const
{
	return LiveBoltCount;
}
