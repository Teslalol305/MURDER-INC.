#pragma once

#include "CoreMinimal.h"
#include "Core/MIMath.h"
#include "Weapons/MIWeaponRules.h"

class FJsonObject;

/**
 * The first-person gun as the web game poses it (src/weapon/viewmodel.js update()), in native code: the base pose
 * blend (hip, sprint, reload, wall, aim, holster), the strike keys, the additive layers (footstep bob, breathing,
 * look lag, movement inertia, jump and landing, bumps, the aim arc) and the six recoil springs about the recoil
 * pivot, all with the exact spring step (FMIExactSpring), so the feel does not depend on the frame rate. It also
 * drives the moving parts (bolt or slide, trigger, barrel, magazine) from the weapon state.
 *
 * The rig works in the web game's view space (metres, x right, y up, z toward the viewer; Euler order YXZ) so that
 * every number is the web number; GetGunTransform() converts the result to Unreal camera space (cm, X forward,
 * Y right, Z up). It reads the rules only through FMIWeaponView and the player through FMIViewmodelPlayer.
 */

/** A pose in web view space. */
struct FMIViewPose
{
	FVector Pos = FVector::ZeroVector;  // m
	FQuat Rot = FQuat::Identity;
};

/** presentation.json "guns.<id>.parts.<part>" */
struct FMIGunPartData
{
	FName Bone;
	FVector Axis = FVector(0, 0, 1);  // web gun space, unit
	double Travel = 0.0;              // m (bolt, slide) or rad (trigger turn, barrel tilt)
	double Back = 0.0;                // s
	double Forward = 0.0;             // s
	bool bLockOnEmpty = false;
	FName ReleaseAt;                  // config reload mark that closes a locked slide
	double Release = 0.0;             // s to close
	double Share = 0.0;               // barrel: share of the slide travel over which it tilts
	FVector Drop = FVector::ZeroVector;  // magazine: m in gun space when out
	FName OutMark, ShowMark, InMark;
};

struct FMIGunViewData
{
	FName Id;
	FSoftObjectPath Mesh;
	FSoftObjectPath Idle;
	FTransform MeshOffset = FTransform::Identity;  // Unreal gun space (cm) to the mesh's own space
	TMap<FName, FName> Sockets;                     // marker -> socket name on the mesh
	TMap<FName, FVector> Markers;                   // marker -> web gun space (m)
	double Relief = 0.0;
	double FlashStar = 0.0, FlashJet = 0.0;
	FMIViewPose Sprint, Reload, Wall, Holster;
	TArray<FMIViewPose> Hip;                         // config "views"
	TArray<TArray<double>> Melee;                    // [t, x, y, z, pitch, yaw, roll]
	FMIGunPartData Bolt, Barrel, Trigger, Magazine;
	TArray<FVector2D> BoltReloadTactical, BoltReloadEmpty;  // (t, share of travel)
	TMap<FName, double> ReloadMarks;                 // config "reload" (magOut, magShow, magInsert, magIn, tug, ...)
	double ReloadTactical = 0.0, ReloadEmpty = 0.0;
	bool bAuto = false;
	// config "kick", "adsSpring", "swaySpring", "swayMax"
	double KickBack = 0, KickRise = 0, KickYaw = 0, KickRoll = 0, KickUp = 0, KickSide = 0;
	double KickFirst = 1, KickSecond = 1, KickRandom = 0, KickCrouch = 1, KickAdsBack = 1, KickAdsRot = 1, KickAdsPos = 1;
	FVector2D SpringBack, SpringPitch, SpringYaw, SpringRoll, SpringPos, AdsSpring, SwaySpring;
	double SwayMax = 0.0;

	FVector Marker(FName Name) const { const FVector* M = Markers.Find(Name); return M ? *M : FVector::ZeroVector; }
};

/** presentation.json "feel" (the web FEEL table). */
struct FMIViewFeelData
{
	double BreatheHz = 0, BreatheY = 0, BreathePitch = 0, BreatheRoll = 0;
	FVector2D BobY, BobX, BobRoll, BobPitch;
	double BobAdsPos = 0, BobAdsRot = 0, BobCrouch = 0, BobRate = 0, BobWalkSpeed = 0, BobExponent = 0, BobMoving = 0;
	double LagGain = 0, LagRoll = 0, LagShift = 0, LagAds = 0;
	double InertiaRate = 0, InertiaStrafe = 0, InertiaSurge = 0, InertiaLean = 0, InertiaFall = 0, InertiaFallPitch = 0, InertiaAds = 0;
	double InertiaAccelLimit = 0, InertiaLeanSpeed = 0;
	FVector2D InertiaFallClamp;
	double Jump = 0, LandPerSpeed = 0, LandMax = 0, LandRoll = 0, LandAdsY = 0, LandPitch = 0, LandAdsPitch = 0;
	FVector2D LandSpring, BumpSpring;
	double AimArcDrop = 0, AimArcRoll = 0, TriggerRate = 0;
	double ReloadIn = 0, ReloadOut = 0, ReloadCancelRate = 0, DropTime = 0;
	double DryPitch = 0, DryY = 0, MagOutY = 0, MagOutRoll = 0, MagInsertY = 0, MagInY = 0, MagInPitch = 0, TugY = 0, TugPitch = 0;
	double MeleeEnemy = 0, MeleeWall = 0, MeleeRoll = 0;
};

struct FMIViewmodelData
{
	FSoftObjectPath Body;
	FName BodyHandSocket;
	TArray<FName> BodyHiddenBones;  // the parts of the first-person body that must not show (head, legs)
	double FirstPersonScale = 1.0;
	double ViewmodelFov = 0.0;  // vertical degrees (config player.fov.viewmodel)
	double StrideWalk = 0, StrideSprint = 0, StrideCrouch = 0;  // m per footstep (config player.stride)
	double TracerMinHit = 0, TracerLength = 0, TracerHidden = 0, TracerHiddenFrom = 0, TracerThickness = 0;  // m
	FMIViewFeelData Feel;
	TArray<FMIGunViewData> Guns;  // in the order of config weapons.common.order

	const FMIGunViewData* Find(FName Id) const { return Guns.FindByPredicate([Id](const FMIGunViewData& G) { return G.Id == Id; }); }

	/** Reads presentation.json and the gun tables of config.json. */
	static bool Load(FMIViewmodelData& Out, FString& OutError);
	static bool Parse(const TSharedPtr<FJsonObject>& Presentation, const TSharedPtr<FJsonObject>& Config, FMIViewmodelData& Out, FString& OutError);
	/** One gun's view data from its presentation object and its rules object (LOADOUT.md 3.7): views, kick, springs,
	 *  swayMax and the reload marks come from the same (possibly modified) rules the weapon rules parse. */
	static bool ParseGunView(const TSharedPtr<FJsonObject>& PresentationGun, const TSharedPtr<FJsonObject>& RulesGun, FMIGunViewData& Out, FString& OutError);
};

/** What the rig reads of the player each frame (Unreal units; the rig converts). */
struct FMIViewmodelPlayer
{
	double Speed = 0.0;               // cm/s horizontal
	FVector Velocity = FVector::ZeroVector;  // cm/s
	double Yaw = 0.0;                 // degrees, Unreal
	bool bOnGround = true;
	bool bCrouching = false;
	bool bSprinting = false;
	FVector2D LookDelta = FVector2D::ZeroVector;  // degrees this frame: X > 0 turned right, Y > 0 looked down
};

/** Where the moving parts are this frame. */
struct FMIGunParts
{
	double Bolt = 0.0;        // 0..1 of the bolt or slide travel
	double Trigger = 0.0;     // 0..1 of the trigger turn
	double Barrel = 0.0;      // 0..1 of the barrel tilt
	double Magazine = 0.0;    // 0 seated .. 1 fully out
	bool bMagazineVisible = true;
	bool bSlideLocked = false;
};

class MURDERINC_API FMIViewmodelRig
{
public:
	void Init(const FMIViewmodelData* InData);
	void Equip(FName Gun);
	FName GetGun() const { return Gun ? Gun->Id : NAME_None; }
	const FMIGunViewData* GetGunData() const { return Gun; }
	/** Replaces a marker by the mesh's own socket (web gun space, m), so real art moves the sights without code. */
	void OverrideMarker(FName Marker, const FVector& WebGunSpace);
	void Reset();

	/** One frame. Weapon: the rules' view; Player: the body; the events below arrive between frames. */
	void Update(double Dt, const FMIWeaponView& Weapon, double AdsLinear, bool bDropped, const FMIViewmodelPlayer& Player);

	// Events (spec 3.17): the rules' events, forwarded by the weapon component.
	void OnFire(int32 Burst, bool bCrouching, double Ads, bool bEmptied);
	void OnDry();
	void OnReloadPhase(FName Phase, bool bEmpty);
	void OnMeleeLand(bool bEnemy, bool bSolid);
	void OnJump();
	void OnLand(double SpeedCmPerS);

	/** The gun's pose in web view space (metres, radians). */
	const FMIViewPose& GetWebPose() const { return Pose; }
	/** The gun in Unreal camera space (cm; X forward, Y right, Z up): the transform of the gun-space origin. */
	FTransform GetGunTransform() const;
	/** A web gun-space point (m) in Unreal camera space (cm). */
	FVector GunPointInCamera(const FVector& WebGunPoint) const;
	const FMIGunParts& GetParts() const { return Parts; }
	double GetAimSpring() const { return Aim.X; }

	/** Clip-driven guns (the pack's clips play the aim, sprint, reload and strike: ANIMATION.md 4, 9): the rig then
	 *  keeps only the hip view, the wall pull, the holster and draw offsets, the additive layers (bob, breathing,
	 *  look lag, inertia, jump and landing, bumps, the aim arc) and the recoil springs. BobScale scales the footstep
	 *  bob (the pack's walk loops already carry one). Presentation only: the rules never read the rig. */
	void SetClipDriven(bool bOn, double InBobScale = 1.0) { bClipDriven = bOn; BobScale = InBobScale; }
	bool IsClipDriven() const { return bClipDriven; }
	/** Clip-driven: the rig's motion this frame as a camera-space transform (Unreal), from the hip view to the pose. */
	FTransform GetLayerTransform() const;

	static FVector WebToUE(const FVector& Web) { return FVector(-Web.Z, Web.X, Web.Y) * 100.0; }
	static FVector UEToWeb(const FVector& UE) { return FVector(UE.Y, UE.Z, -UE.X) / 100.0; }
	static FQuat WebToUE(const FQuat& Q) { return FQuat(Q.Z, -Q.X, -Q.Y, Q.W); }
	/** three.js Euler (pitch about x, yaw about y, roll about z) in the order YXZ. */
	static FQuat EulerYXZ(double Pitch, double Yaw, double Roll);

private:
	void BlendTo(const FMIViewPose& Target, double K);
	void TurnAboutPivot(const FQuat& Q);
	void UpdateParts(double Dt, const FMIWeaponView& Weapon);

	const FMIViewmodelData* Data = nullptr;
	const FMIGunViewData* Gun = nullptr;
	FMIViewPose Pose;
	FMIViewPose AdsPose;
	FMIGunParts Parts;

	double Clock = 0.0;
	double ShotAge = 1e30;
	double LastAdsLinear = 0.0;
	double ReloadWeight = 0.0;
	double LastReloadT = 0.0;
	double BobPhase = 0.0;
	double BobAmp = 0.0;
	double LandRollSign = 1.0;
	double DropT = 0.0;
	FVector2D LastVel = FVector2D::ZeroVector;
	double InertiaX = 0, InertiaZ = 0, InertiaLean = 0, InertiaFall = 0;
	FMIExactSpring Aim, SwayYaw, SwayPitch, Land, BumpY, BumpPitch, BumpRoll;
	FMIExactSpring RecBack, RecPitch, RecYaw, RecRoll, RecSide, RecUp;
	double TriggerX = 0.0;
	double BoltTime = 1e30;   // s since the last round moved the bolt
	bool bSlideLocked = false;
	double SlideCloseT = -1.0;
	bool bClipDriven = false;
	double BobScale = 1.0;
};
