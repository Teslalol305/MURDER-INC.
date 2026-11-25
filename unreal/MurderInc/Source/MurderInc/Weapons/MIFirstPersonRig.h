#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Weapons/MIFirstPersonAnim.h"
#include "Weapons/MIWeaponRules.h"
#include "MIFirstPersonRig.generated.h"

class FJsonObject;
class FMIViewmodelRig;
class UAnimSequenceBase;
class UCameraComponent;
class UMaterialInstanceDynamic;
class UMIGunAssembly;
class UMIWeaponComponent;
class USkeletalMesh;
class USkeletalMeshComponent;
class UStaticMesh;
class UStaticMeshComponent;
struct FMIGunViewData;
struct FMIResolvedGun;
struct FMIViewmodelPlayer;

/** How a gun is held in first person. */
enum class EMIFPMode : uint8
{
	Template,  // the engine template body placed on the grip, the procedural rig poses the gun (clean checkout)
	Pack,      // the pack's clips drive the arms and the gun; the camera recipe of ANIMATION.md 9
	HandIK     // the procedural rig poses the gun; the arms play a template clip and their hands are pulled onto it
};

/**
 * The player's arms and gun as a current shooter draws them (docs/unreal/ANIMATION.md 4, 9, 9.1), stepped by
 * UMIWeaponComponent after the rules: SK_RuleArms (or the template body) with its bracelet; for guns whose
 * presentation names a "pack" anim set, the pack rifle on the arms' ik_hand_gun playing the pack's own clips (idle,
 * aimed, walk, sprint, jump, fire per round, both reloads warped onto the rules' stage times, inspect, magazine
 * check, fire-mode switch, melee, holster, draw), the arms on the camera by the recipe, the procedural rig's sway,
 * bob and recoil on top, the magazines of 9.1 (the reserve hidden until in hand, the dropped one a physics body).
 * For "ik" sets (the NINE) the template pistol clip with the hands pulled onto the gun's Palm sockets.
 * Everything here is presentation: it reads the rules' view and events and never writes rule state.
 */
UCLASS(ClassGroup = (MurderInc))
class MURDERINC_API UMIFirstPersonRig : public UActorComponent
{
	GENERATED_BODY()

public:
	UMIFirstPersonRig();

	/** The arms component (already attached to the camera) and presentation.json's root. */
	void Init(UMIWeaponComponent* InWeapon, USkeletalMeshComponent* InArms, UCameraComponent* InCamera, const TSharedPtr<FJsonObject>& Presentation);
	/** The gun in hand changed. Returns the mode it is drawn in. */
	EMIFPMode Equip(FName Gun, const FMIGunViewData* View, const FMIResolvedGun* Resolved, UMIGunAssembly* Assembly, class USkinnedMeshComponent* LegacyGun);
	EMIFPMode GetMode() const { return Mode; }
	/** Degrees the irons' front sight sat off the camera axis in the clip's aimed pose (the zeroing turn). */
	double GetIronZeroDeg() const { return IronZeroDeg; }

	/** One frame after the rules and the procedural rig. */
	void Update(double Dt, const FMIWeaponView& Weapon, const FMIViewmodelRig& Rig, const FMIViewmodelPlayer& Player, double ViewYawDeg);
	/** HandIK guns: pulls the hands onto the procedurally posed gun (call after the arms were placed). */
	void UpdateHands(const class USkinnedMeshComponent* Gun);

	void OnFire(double Ads);
	void OnJump() { JumpAge = 0.0; }
	void OnLand(double Speed) { LandAge = 0.0; LandWeight = FMath::Clamp(Speed / 900.0, 0.2, 1.0); }
	void RequestInspect(int32 Mag, int32 MagSize);

	/** The first-person (arms and gun) vertical field of view: hip blended by Ads to the irons' or the optic's. */
	double FirstPersonFovV(double Hip, double Ads) const;
	bool HasOptic() const { return bOptic; }
	double GetBobScale() const { return BobScale; }

	/** Pack guns: the gun component and its muzzle / ejection port in camera space. */
	USkeletalMeshComponent* GetPackGun() const { return PackGun; }
	bool MuzzleInCamera(FVector& OutPos, FVector& OutDir) const;
	bool EjectInCamera(FTransform& Out) const;
	UStaticMesh* GetCasingMesh() const { return CasingMesh; }
	/** Dev (editor only): each finger's gap to the gun mesh in the pose as drawn (arms skinned on the CPU from the
	 *  imported model, the gun's triangles), and the curl (FMIFPFingerCurl) that brings it to contact. Logged as
	 *  "MI-GRIP <label> <side> <finger> gap <cm> ... curl <deg> gap <cm>" lines (polish pass; MIGripProbe). */
	void ProbeGrip(const FString& Label) const;

	/** The arms' hand socket (presentation bodyHandSocket) in arms component space, read from the template body's socket
	 *  definition when the arms mesh has none. */
	bool HandSocket(FName Socket, FTransform& Out) const;
	/** HandIK guns with a solved grip: how far (camera space) the arms must slide so the clips' firing hand (before the
	 *  IK) sits on the grip's solved wrist; GunRel and ArmsRel are the gun's and the arms' transforms under the camera. */
	bool GripWristSlide(const FTransform& GunRel, const FTransform& ArmsRel, FVector& Out) const;
	/** HandIK guns with a solved grip and an anim set 'shoulders' anchor (camera space, cm; console mi.FP.Shoulders
	 *  "x y z" overrides, "off" falls back to GripWristSlide): the arms' translation under the camera that puts the
	 *  midpoint of upperarm_l / upperarm_r on the anchor, as a body would carry them. The two-bone IK then reaches both
	 *  hands onto the solved grip from there (the wrist slide carried the template clip's shoulders into the view). */
	bool GripShoulderTranslation(const FTransform& ArmsRel, FVector& Out) const;
	/** The shoulders' midpoint (upperarm_l / _r) in camera space, for calibration logs. */
	bool ShouldersInCamera(FVector& Out) const;
	/** A static part authored in the skeletal mesh's own space (origin and axes of the gun, as SM_Weapon_NineMagazine is
	 *  to SK_Nine) attached to a bone: its transform relative to that bone (the inverse of the bone's reference pose in
	 *  component space), so it sits where it was modelled and follows the bone's animation. */
	static FTransform MeshSpacePartOnBone(const USkeletalMesh* Mesh, FName Bone);
	void SetVisible(bool bGun, bool bArms);
	/** HandIK guns: the seated magazine's top round shows while there is a round in the magazine. */
	void SetTopRoundVisible(bool bVisible);
	bool IsPackGunVisible() const;
	/** HandIK guns in a reload whose anim set says magazine.inHand: the magazine stays drawn through the swap (it is in the
	 *  support hand, which holds it all the way down and back up), instead of vanishing at the bottom of its drop. */
	bool KeepsMagazineInHand() const;

private:
	struct FClipSet
	{
		TMap<FName, TObjectPtr<UAnimSequenceBase>> Arms;
		TMap<FName, TObjectPtr<UAnimSequenceBase>> Gun;
	};
	struct FReloadMap
	{
		TArray<FVector2D> Keys;  // (rule time, clip time)
		double Reserve = 0.0, Out = 0.0, Seated = 0.0;
		bool bDrop = true;
		bool bDropFull = false;
		bool bStow = false;  // the old magazine is kept (hidden at 'out', as if pouched): no body thrown away
	};

	UAnimSequenceBase* ArmsClip(FName Role) const;
	UAnimSequenceBase* GunClip(FName Role) const;
	void SetupArms();
	/** The real arms (and their jewels) for Pack / HandIK guns, the template body with its hidden bones otherwise. */
	void UseRealArms(bool bReal);
	void BuildPack(double Dt, const FMIWeaponView& W, const FMIViewmodelPlayer& P, double ViewYawDeg, FMIFPPose& Arms, FMIFPPose& Gun);
	void UpdateMagazines(const FMIWeaponView& W, double ClipT, const FReloadMap* Map);
	void DropMagazine(bool bFull);
	double WarpReload(const FReloadMap& Map, double RuleT) const;
	FTransform CameraSpace(const FTransform& World) const;

	UPROPERTY(Transient)
	TObjectPtr<UMIWeaponComponent> Weapon;
	UPROPERTY(Transient)
	TObjectPtr<USkeletalMeshComponent> Arms;
	UPROPERTY(Transient)
	TObjectPtr<UCameraComponent> Camera;
	UPROPERTY(Transient)
	TObjectPtr<USkeletalMeshComponent> PackGun;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMeshComponent> OwnMag;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMeshComponent> OwnTopRound;  // HandIK guns: the seated magazine's top round (a child of OwnMag)
	/** HandIK guns: the fitted optic's hardware material, one dynamic instance per slot; its scalar "AimFade" goes 0 to 1 as
	 *  the sight comes up (the housing fades out, the glass and the reticle stay: the aimed picture is not a dark tunnel). */
	TArray<TWeakObjectPtr<UMaterialInstanceDynamic>> OpticHardware;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMeshComponent> ReserveMag;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> Jewels;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UAnimSequenceBase>> Loaded;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> MagFull;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> MagEmpty;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> CasingMesh;
	UPROPERTY(Transient)
	TObjectPtr<UAnimSequenceBase> CurlClip;  // HandIK guns: the support fingers' wrap (anim set fingerCurl)
	FName CurlBranch;
	double CurlTime = 0.0, CurlWeight = 1.0;
	UPROPERTY(Transient)
	TObjectPtr<USkeletalMesh> TemplateBody;
	UPROPERTY(Transient)
	TObjectPtr<USkeletalMesh> RealArms;

	TWeakObjectPtr<UStaticMeshComponent> HeldMag;    // HandIK guns: the magazine the support hand holds in a reload (OwnMag or the fitted part)
	TWeakObjectPtr<UStaticMeshComponent> SeatedMag;  // the magazine on MagHinge (the assembly's part, or OwnMag)
	TWeakObjectPtr<UMIGunAssembly> GunAssembly;      // the build of the gun in hand (a fitted grip gives the support hand its place)
	TWeakObjectPtr<const USkinnedMeshComponent> HandGun;  // HandIK guns: the poseable gun the hands were last pulled onto (its Eject socket throws the brass)
	FVector EjectDirMesh = FVector::ZeroVector;      // HandIK guns: the casing's direction in the gun mesh's frame (presentation ejectDir), zero when none
	/** The optics in daylight: presentation firstPerson.opticMaterials (base material name -> scalar parameters) set on
	 *  dynamic instances of every material of the gun's child parts, for every mode (the pack's optics and our own). */
	void ApplyOpticMaterials(USceneComponent* GunRoot);
	TSharedPtr<FJsonObject> Root;        // presentation.json
	TSharedPtr<FJsonObject> Set;         // the anim set of the gun in hand
	FClipSet Clips;
	FReloadMap ReloadTactical, ReloadEmpty;
	EMIFPMode Mode = EMIFPMode::Template;
	double IronZeroDeg = 0.0;
	FQuat IronZero = FQuat::Identity;
	FVector SupportElbowDrop = FVector::ZeroVector;
	/** Per-gun finger curls (presentation of the resolved gun: fingers.hip / fingers.aim, side l / r, finger -> deg),
	 *  blended by smoothstep(Ads), let go in actions and sprint. */
	TMap<FName, float> CurlHip[2], CurlAim[2];
	FVector ShoulderAnchor = FVector::ZeroVector;  // anim set 'shoulders' (camera space, cm)
	bool bShoulderAnchor = false;
	bool bReloadingNow = false;
	double ReloadNowT = 0.0, ReloadNowLeft = 0.0;
	/** HandIK guns: where the support palm goes on the magazine in a reload, in the magazine part's own frame (cm): anim set
	 *  magazine.palm, or the middle of the magazine mesh's bottom when the set gives none. */
	FVector MagBasePad = FVector(1.5, 0.0, -15.0);
	/** HandIK guns, in a reload: the support grip carried onto the magazine is narrowed across the gun by this factor about
	 *  the magazine's middle (anim set magazine.squeeze: the solve wraps a 5 to 6 cm forend, a magazine is 2.5 to 3 cm). */
	double MagSqueeze = 1.0;
	/** HandIK guns, in a reload: the turn of the carried support grip about the palm (anim set magazine.turn, degrees about the
	 *  gun's X, Y, Z), so the handguard's grip closes round the magazine's body; and where on the magazine the palm goes
	 *  (magazine.height: that fraction up its front face; absent: under its base). */
	FQuat MagTurn = FQuat::Identity;
	double MagHeight = -1.0;
	bool bMagInHand = false;
	double ArmLogAt = -1e9;  // the development log of the support arm, every 2 s
	/** HandIK guns: seconds the support hand takes to go to the magazine and back (anim set magazine.blend). */
	double MagBlend = 0.25;
	/** HandIK guns: the support elbow pushed from the clip's own pole (anim set supportElbowOut, camera space cm: X forward,
	 *  Y right, Z up), at the hip; aimed it blends to supportElbowOutAim (the same when the set gives none). */
	FVector SupportElbowOut = FVector::ZeroVector, SupportElbowOutAim = FVector::ZeroVector;
	bool bReloadLogged = false;  // the development log of the support hand in a reload, once a reload
	double AdsNow = 0.0;  // HandIK guns: the aim weight of the last Update (the grip solves and the elbow blend by it)
	FName GunId;
	FTransform ArmsRest = FTransform::Identity;
	double FovIrons = 38.0, FovOptic = 32.0;
	double BobScale = 0.5, WalkSpeed = 380.0, SprintSpeed = 640.0, FireWeight = 0.6, FireRate = 1.0, DrawRange = 0.53, MeleeRange = 1.0;
	bool bOptic = false;
	FName GripVariant;  // underbarrel grip fitted (aim pose variant)

	// clocks
	double Clock = 0.0, LocoPhase = 0.0, FireAge = 1e9, JumpAge = 1e9, LandAge = 1e9, LandWeight = 0.0, Air = 0.0, Crouch = 0.0, Walk = 0.0;
	bool bFireAimed = false;
	FName Action;            // the clip role playing over the locomotion
	double ActionT = 0.0, ActionWeight = 0.0;
	FName LastAction;
	double LastActionT = 0.0;
	FName Presented;         // inspect / magCheck (presentation only)
	double PresentedT = 0.0, IdleFor = 0.0, InspectAfter = 24.0;
	bool bWasReloading = false, bDropped = false;
	FVector MagPrev = FVector::ZeroVector, MagVel = FVector::ZeroVector;
	FMIFPPose HandPose;
	FName LeftSocket, RightSocket;
	TMap<FName, FVector> GripPoints[2];  // HandIK guns: the solved grip's points (gun space, cm), [0] left, [1] right
	TMap<FName, FVector> GripPointsAim[2];  // the aimed solve (grip.aimPose, default "aim"); empty: the hip solve aimed too
	double GripWeight = 1.0;
	double SupportStretch = 1.0;  // HandIK guns: the support arm's largest stretch (anim set armStretch)
	double ReloadCurl = 0.0;      // HandIK guns: degrees the support fingers close on the magazine in a reload (anim set reloadCurl)
	double ForegripCurl = 0.0;    // HandIK guns: degrees the support fingers close extra on a fitted foregrip (anim set foregripCurl)
};
