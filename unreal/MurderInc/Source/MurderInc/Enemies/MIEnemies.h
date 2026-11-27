#pragma once

#include "CoreMinimal.h"
#include "Enemies/MIEnemyLogic.h"
#include "Enemies/MIEnemyTune.h"

/**
 * The Vultures as rules: src/enemies.js (pools, the mode machine, sight and hearing, the accuracy ramp, tokens,
 * damage, bodies, budgets), src/enemies/goon.js, buzzard.js and bolts.js, ported line for line onto the box world.
 * No actor, no mesh: UMIEnemySubsystem hosts it and AMIGoon / AMIBuzzard draw what it decides.
 * Web units and axes (metres, radians, yaw 0 = north -Z, + = left); MurderInc.Golden.Enemies replays six fights of
 * the web game's own module frame by frame.
 */

enum class EMIEnemyMode : uint8 { Patrol, Investigate, Search, Engage, Dying, Dead, Idle };
enum class EMIGoonSub : uint8 { Move, Aim, Cool, Telegraph, Burst, Windup, Lunge, Recover };

/** What the field tells its host (and the event bus): enemy:* events, in the order they happened. */
struct FMIEnemyEvent
{
	enum class EKind : uint8 { Spawn, Alert, Telegraph, Fire, Melee, Hit, Killed };
	EKind Kind = EKind::Spawn;
	int32 Id = 0;
	MIEnemy::EType Type = MIEnemy::EType::Goon;
	FVector Pos = FVector::ZeroVector;
	FVector Dir = FVector::ZeroVector;
	FName Phase;   // melee: windup / strike
	FName Part;    // hit / killed: head / body
	double Damage = 0.0;
	double Duration = 0.0;
	bool bByPlayer = false;
	FName Weapon;
};

/** The player as the enemies read him each frame. */
struct FMIEnemyPlayer
{
	FVector Pos = FVector::ZeroVector;
	FVector Eye = FVector::ZeroVector;
	FVector Vel = FVector::ZeroVector;
	bool bAlive = true;
	bool bCrouching = false;
};

/** What the rules ask the world for, beyond the box world: answered by the engine in the game, recorded in tests. */
class IMIEnemyHost
{
public:
	virtual ~IMIEnemyHost() = default;
	/** A Goon round: one ray on the shot channel; returns where it ended (the tracer's end). */
	virtual FVector Hitscan(int32 EnemyId, const FVector& Origin, const FVector& Dir, double Range, double Damage) = 0;
	virtual void DamagePlayer(double Amount, const FVector& From, FName Kind) = 0;
	/** A Buzzard's crash burst (combat.explode). */
	virtual void Explode(int32 EnemyId, const FVector& Pos, double Radius, double Damage, double PlayerScale) = 0;
	/** A bolt hit a box that belongs to an explosive item (bolts.js explosiveBehind). */
	virtual void HitExplosive(int32 Item, double Amount) {}
};

/** One Goon or Buzzard slot (the web record: shared fields, then the type's own). */
struct FMIEnemy
{
	// ---- shared ----
	int32 Id = 0;
	MIEnemy::EType Type = MIEnemy::EType::Goon;
	int32 Slot = 0;
	bool bActive = false;
	bool bAlive = false;
	bool bPassive = false;
	double Hp = 0, MaxHp = 0;
	FVector Pos = FVector::ZeroVector;
	FVector Vel = FVector::ZeroVector;
	double Yaw = 0;
	EMIEnemyMode Mode = EMIEnemyMode::Idle;
	double ModeTime = 0, Seen = 0, SinceSeen = 0, SenseIn = 0, Exposure = 0;
	bool bSees = false;
	FVector LastKnown = FVector::ZeroVector;
	FVector Home = FVector::ZeroVector;
	double Cooldown = 0, Telegraph = 0;
	bool bHasToken = false;
	double LastActive = 0, DeadTime = 0;
	int32 BurstLeft = 0;
	double BurstTimer = 0;
	double LampWant = 0;

	// ---- Goon ----
	EMIGoonSub Sub = EMIGoonSub::Move;
	double SubT = 0;
	TArray<FVector> Path;
	int32 PathIndex = 0;
	bool bHasPath = false, bNeedPath = false, bHasGoal = false, bArrived = false;
	int32 PathFails = 0;
	double GoalX = 0, GoalZ = 0, ReplanIn = 0, WantSpeed = 0, FaceYaw = 0;
	bool bFacing = false;
	double TurnScale = 1, MoveSpeed = 0, Stuck = 0;
	int32 StuckCount = 0;
	double Travel = 0, Wait = 0;
	bool bOnGround = true;
	FName Surface;
	bool bHasFirePos = false, bWantPick = false, bPickAway = false, bAtCover = false;
	double GoalFireX = 0, GoalFireZ = 0, PickX = 0, PickZ = 0;
	bool bWantStand = false, bHasStand = false, bStandSight = false;
	double StandX = 0, StandZ = 0, StandForX = 0, StandForY = 0, StandForZ = 0;
	int32 Bursts = 0, BurstsToMove = 1;
	double NoSight = 0, Waited = 0, TooClose = 0, RushCooldown = 0;
	bool bRushHit = false;
	double AimYaw = 0, Sweep = 0, SweepBase = 0, Scan = 0;
	bool bDusted = false;
	double BodyAge = 0;
	bool bFading = false;
	double Fade = 0;
	int32 Variant = 0;
	// what the pose reads
	double Speed = 0, YawRate = 0, WantCrouch = 0, WantAim = 0, AimYawRel = 0, AimPitch = 0, LookYawRel = 0, LookPitch = 0;
	int32 RushPhase = 0;
	double RushK = 0;
	// the slice of goon-anim.js the rules depend on
	double HeadYaw = 0, HeadPitch = 0;
	int32 Swing = -1;
	double DeathT = 0;
	FVector DeathDir = FVector::ZeroVector;  // model-space direction of the killing shot (x, z)
	FVector FlinchDir = FVector::ZeroVector;
	double FlinchStrength = 0;
	double FlinchAge = 0;

	// ---- Buzzard ----
	/** Hold the Block's last-drone rule (DECISIONS.md 2026-11-27): after 20 s unhurt as the wave's last enemies the Buzzard flies straight at the player. */
	bool bCharge = false;
	double Altitude = 6, OrbitRadius = 18, OrbitAngle = 0, OrbitDir = 1, PatrolRadius = 6, RethinkIn = 5, FlipIn = 0;
	FVector Push = FVector::ZeroVector;
	double StuckX = 0, StuckY = 0, StuckZ = 0, StuckT = 0, DetourIn = 0, DetourX = 0, DetourY = 0, DetourZ = 0;
	double Ceiling = MIEnemy::Inf, CeilingAge = 0;
	int32 Feeler = 0;
	double Pitch = 0, Roll = 0, KickPitch = 0, KickRoll = 0, Wobble = 0, Lead = 0.5;
	double SmokeIn = 0, SparkIn = 0, Spin = 0, Strobe = 0;
	double RotorWant = 1, EyeYawWant = 0, EyePitchWant = 0;
	// buzzard-model.js anim
	double RotorSpeed = 1, RotorAngle = 0, EyeYaw = 0, EyePitch = 0, Lamp = 0, Flash = 0;
	int32 LostRotor = -1;
	FVector Eye = FVector::ZeroVector;
	FVector Gun = FVector::ZeroVector;

	bool IsGoon() const { return Type == MIEnemy::EType::Goon; }
};

struct FMIBolt
{
	FVector P = FVector::ZeroVector;
	FVector D = FVector::ZeroVector;
	FVector O = FVector::ZeroVector;
	double Life = 0, Flown = 0, Damage = 0;
	int32 Owner = 0;
};

/** The presentation constants of the Buzzard the rules read (buzzard-model.js / buzzard.js; rules.json buzzardModel). */
struct FMIBuzzardModel
{
	FVector GimbalPivot = FVector(0, -0.085, -0.17);
	FVector Eye = FVector(0, -0.015, -0.085);
	FVector Muzzle = FVector(0.062, -0.045, -0.2);
	double TiltPerAccel = 0.034;
	double MaxTilt = 0.5;
	double StrobePeriod = 1.3;
	double PoleStep = 2.0;
	double RoomMargin = 1.5;
	double BladeRate = 41.0;
	TArray<FVector> Rotors;
};

struct FMIEnemySpawnOptions
{
	TOptional<double> Yaw;
	bool bPassive = false;
	bool bAlerted = false;
	TOptional<FVector> Target;
	int32 Variant = -1;
};

class MURDERINC_API FMIEnemyField
{
public:
	/** Level: cover points, the El deck, interiors and doorways. World: the box world everything moves in. */
	void Init(const FMIEnemyTune& InTune, const FMILevelData* InLevel, FMIBoxWorld* InWorld, IMIEnemyHost* InHost);
	/** setDifficulty: the next resolved table (hit points are fixed when a unit spawns). */
	void SetTune(const FMIEnemyTune& InTune) { Tune = InTune; }
	/** Holdout wave multipliers: hp for units spawned from now on, damage and cooldown at once. */
	void SetScale(double Hp, double Damage, double CooldownScale);

	/** A unit in a free slot (or the oldest body's, or a falling one's); null when all are alive. */
	FMIEnemy* Spawn(MIEnemy::EType Type, const FVector& Pos, const FMIEnemySpawnOptions& Opts = FMIEnemySpawnOptions());
	void Clear();
	void Update(double Dt, const FMIEnemyPlayer& Player);
	/** Where the player stands right now (an alerted spawn without a target heads there, as G.player.pos). */
	void SetLivePlayerPos(const FVector& Pos) { LivePlayerPos = Pos; }

	/** Returns true when the hit killed. Info: part (head/body), direction of the shot (web, unit), source. */
	bool Damage(FMIEnemy& E, double Amount, FName Part, const TOptional<FVector>& Dir, bool bByPlayer, FName Weapon);
	/** Everyone within Radius of Pos who is not fighting goes to look. */
	void Alert(const FVector& Pos, double Radius);
	/** Only units still unaware go to look. */
	void Hear(const FVector& Pos, double Radius);
	/** The player's gun went off (weapon:fire): alerts at most every gunfireEvery seconds. */
	void Gunfire(const FVector& Pos);
	/** A round heard RadiusM metres out (LOADOUT.md 4.5: a silencer shrinks it). The throttle stays, except that a
	 *  round heard further than the last alert in the window still alerts (never when every radius is equal). */
	void Gunfire(const FVector& Pos, double RadiusM);
	void Explosion(const FVector& Pos, double Radius) { Alert(Pos, Radius); }

	int32 AliveCount() const;
	int32 CountByType(MIEnemy::EType Type) const;
	double NearestDistance(const FVector& From) const;
	/** Living and dying units, in spawn order of the web list. */
	const TArray<int32>& GetList() const { return List; }
	const TArray<int32>& GetBodies() const { return Bodies; }
	const TArray<FMIEnemy>& GetSlots() const { return Slots; }
	FMIEnemy* Find(int32 Id);
	const FMIEnemy* Find(int32 Id) const;
	int32 LiveBolts() const;
	const TArray<FMIBolt>& GetBolts() const { return BoltSlots; }
	int32 TokensHeld() const { return Tokens.Held; }
	const FMIEnemyTune& GetTune() const { return Tune; }
	double Clock() const { return Now; }

	/** Events since the last call (the host forwards them to the event bus). */
	TArray<FMIEnemyEvent>& Events() { return PendingEvents; }

	/** goon-anim.js points (head, chest) for hit volumes: from the rule state, not the drawn pose. */
	FVector GoonHead(const FMIEnemy& E) const;

	FMIBuzzardModel Model;

private:
	// ---- shared (enemies.js) ----
	bool RequestToken(FMIEnemy& E);
	void ReleaseToken(FMIEnemy& E);
	void CancelAttack(FMIEnemy& E);
	void SetMode(FMIEnemy& E, EMIEnemyMode Mode);
	void Rally(FMIEnemy& E, double Radius, const FVector& At);
	void Engage(FMIEnemy& E);
	void Investigate(FMIEnemy& E, const FVector& At, double Seconds, bool bAnnounce);
	void ToPatrol(FMIEnemy& E);
	void Sense(FMIEnemy& E, double Dt);
	void Think(FMIEnemy& E, double Dt);
	void Retire(FMIEnemy& E);
	void SpendBudgets();
	void Emit(FMIEnemyEvent::EKind Kind, const FMIEnemy& E, const FVector& Pos, const FVector& Dir = FVector::ZeroVector);
	double Random() { return Rng.Next(); }
	double Range(const FMIRange& R) { return R.A + (R.B - R.A) * Rng.Next(); }
	void OnLeaveEngage(FMIEnemy& E);
	void OnEngage(FMIEnemy& E);
	void OnInvestigate(FMIEnemy& E);
	void OnPatrol(FMIEnemy& E);

	// ---- Goon ----
	void GoonSpawn(FMIEnemy& E, const FVector& At, const FMIEnemySpawnOptions& Opts);
	void SetGoal(FMIEnemy& E, double X, double Z);
	void ClearGoal(FMIEnemy& E);
	void Plan(FMIEnemy& E);
	bool Locomote(FMIEnemy& E, double Dt);
	int32 CollectOthers(const FMIEnemy& E);
	int32 AddCandidate(int32 N, double X, double Z, MIEnemy::ECandidate Kind, bool bCover, const FMIEnemy& E, const FVector& TargetPos, const FVector& TargetEye, bool bStand);
	bool PickFirePosition(FMIEnemy& E);
	void PickStand(FMIEnemy& E);
	void Pick(FMIEnemy& E);
	void ToAim(FMIEnemy& E);
	void Relocate(FMIEnemy& E);
	void Fire(FMIEnemy& E);
	void StartRush(FMIEnemy& E);
	void SwingPipe(FMIEnemy& E);
	void GoonPatrol(FMIEnemy& E, double Dt);
	void GoonInvestigate(FMIEnemy& E, double Dt);
	bool RushClear(const FMIEnemy& E) const;
	void GoonEngage(FMIEnemy& E, double Dt);
	void GoonUpdate(FMIEnemy& E, double Dt);
	void GoonKilled(FMIEnemy& E, const TOptional<FVector>& Dir);
	bool GoonDying(FMIEnemy& E, double Dt);
	bool GoonBody(FMIEnemy& E, double Dt);

	// ---- Buzzard ----
	void BuzzardSpawn(FMIEnemy& E, const FVector& At, const FMIEnemySpawnOptions& Opts);
	void BuzzardPlace(FMIEnemy& E);
	void BuzzardPose(FMIEnemy& E, double Dt);
	double Target(FMIEnemy& E, double Dt);
	void Feel(FMIEnemy& E, double Speed);
	bool Slide(FMIEnemy& E, int32 Axis, double Dt, double Clear, double Bounce, MIEnemy::FSolid const** HitPole);
	void Detour(FMIEnemy& E, double Dt);
	void Fly(FMIEnemy& E, double Dt);
	void FireBolt(FMIEnemy& E);
	void Attack(FMIEnemy& E, double Dt, double Bearing, double Dist);
	void BuzzardUpdate(FMIEnemy& E, double Dt);
	void BuzzardHit(FMIEnemy& E, double Amount, const TOptional<FVector>& Dir);
	void BuzzardKilled(FMIEnemy& E, const TOptional<FVector>& Dir);
	bool BuzzardDying(FMIEnemy& E, double Dt);
	void Burst(FMIEnemy& E);

	// ---- bolts ----
	void SpawnBolt(const FVector& From, const FVector& Dir, double Amount, int32 Owner);
	void UpdateBolts(double Dt);

	FMIEnemyTune Tune;
	const FMILevelData* Level = nullptr;
	FMIBoxWorld* World = nullptr;
	IMIEnemyHost* Host = nullptr;
	FMIRng Rng;
	MIEnemy::FTokens Tokens;
	MIEnemy::FSolids Solids;
	double ScaleHp = 1, ScaleDamage = 1, ScaleCooldown = 1;
	TArray<FMIEnemy> Slots;  // goons first (PoolGoon), then buzzards
	TArray<int32> List;      // slot indices, living and dying
	TArray<int32> Bodies;    // slot indices, oldest first
	TArray<FMIBolt> BoltSlots;
	int32 NextBolt = 0;
	int32 LiveBoltCount = 0;
	TArray<FMIEnemyEvent> PendingEvents;
	FMIEnemyPlayer Player;
	FVector LivePlayerPos = FVector::ZeroVector;
	double PlayerSpeed = 0;
	double Now = 0;
	int32 Alive = 0;
	int32 NextId = 1;
	double SinceGunfire = MIEnemy::Inf;
	double LastGunfireRadius = 0.0;
	int32 BudgetPaths = 0, BudgetPicks = 0;
	int32 PathCursor = 0, PickCursor = 0, StandCursor = 0;
	TArray<MIEnemy::FCandidate> Candidates;
	TArray<MIEnemy::FOther> Others;
	// Buzzard scratch (buzzard.js `want`, `hit`).
	FVector Want = FVector::ZeroVector;
	double Cap = 0;
	FMIRayHit LastHit;
	int32 ClimbHitSolid = INDEX_NONE;
};
