#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "MIEffects.generated.h"

class AActor;
class UDecalComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class UPointLightComponent;
class UStaticMesh;
class UStaticMeshComponent;
struct FMIExplosionEvent;
struct FMIImpactEvent;

/**
 * The game's effects at the event-bus hooks (docs/unreal/GAMEPLAY.md 3, 8), restrained and short-lived: muzzle flash
 * cards with a brief light (none with a silencer), brass from the ejection port, tracers for enemy fire, bullet
 * strikes with a mark and dust in the surface's colour, blood on the Goons, and explosions with a flash, a fireball,
 * smoke, debris and a scorch. Built in code on pooled components over the materials tools/box/fp/mi_fp_import.py
 * makes (/Game/FX: M_FX_Flash, M_FX_Smoke, M_FX_Tracer, MD_FX_Mark, M_FX_Brass, M_FX_Debris); tuning in
 * presentation.json "fx". Without those materials (a clean checkout) nothing is drawn. Never touches rule state.
 */
UCLASS()
class MURDERINC_API UMIEffects : public UTickableWorldSubsystem
{
	GENERATED_BODY()

public:
	static UMIEffects* Get(const UObject* WorldContext);

	/** A physics body that falls out of the world's way (a dropped magazine, a casing, debris), gone after Life s.
	 *  Hidden for its first HiddenFor s when HiddenFor > 0 (the world half of a first-person hand-off). */
	static AActor* SpawnBody(const UObject* WorldContext, UStaticMesh* Mesh, const FTransform& At, const FVector& Velocity, const FVector& SpinDeg, double Life, UMaterialInterface* Material = nullptr, double HiddenFor = 0.0);
	/** Something thrown from the gun (a casing, a dropped magazine) seen from the eye: a body at the first-person depth and
	 *  size (ViewAt, ViewVelocity) for ViewLife s, so it leaves the gun on screen, then the same thing at its true size
	 *  where it really is (WorldAt, WorldVelocity: thrown at the same moment, shown when the first-person one goes) for
	 *  the rest of Life (fix pass: the first-person body stayed for its whole life, a casing the size of the rear sight
	 *  over the screen and then a miniature on the ground). */
	static void SpawnViewBody(const UObject* WorldContext, UStaticMesh* Mesh, const FTransform& ViewAt, const FVector& ViewVelocity,
		const FTransform& WorldAt, const FVector& WorldVelocity, const FVector& SpinDeg, double ViewLife, double Life, UMaterialInterface* Material = nullptr);

	/** A muzzle flash seen in the world (an enemy's): cards along and across the bore and a short light. */
	void WorldFlash(const FVector& Muzzle, const FVector& Dir, double Scale, bool bLight);
	/** The player's own flash, seen from the eye behind the gun (polish pass): the star faces the eye, the jets run
	 *  along the bore turned to face it, and all three are pulled toward the eye along their sight lines (fx.flash.view
	 *  pull: the fraction of the distance kept, sizes scaled alike) so they draw over the gun's front end, which hides
	 *  the muzzle itself from the eye at the hip. Same pixels, same apparent size. Aimed (Ads) the pull eases to
	 *  flash.view.pullAimed (1: none): pulled in, the cards fell behind the rear sight, the nearest thing to the eye;
	 *  on the muzzle their upper half shows through the aperture round the front post.
	 *  With fx.materials.flashView (M_FX_FlashView: the flash material with depth testing off) the player's flash has its
	 *  own cards in that material: they sit on the muzzle's true first-person point and draw over the gun's front end
	 *  without being pulled in (fx.flash.view.pullOverlay, 1 = none), and enemy flashes never recycle them (fix pass). */
	void ViewFlash(const FVector& Muzzle, const FVector& Dir, const FVector& Eye, double Scale, double Ads = 0.0);
	/** The player's own flash light (dimmer and shorter than an enemy's, placed ahead of the gun by the caller). */
	void FlashLight(const FVector& At, double Scale);
	/** How far ahead of the muzzle, along the bore, the player's flash light sits (fx.flash.player.ahead, cm). */
	double PlayerFlashAhead() const;
	/** A tracer streak from a muzzle to where the round ends. */
	void Tracer(const FVector& From, const FVector& To, double SpeedCmPerS);
	/** The player's tracer: from the muzzle as drawn (the first-person point) to where the round ends, drawn from its first
	 *  frame, its tail held fx.tracer.player.start cm past the muzzle (so it leaves the gun on screen as a converging
	 *  streak instead of a dot at the crosshair), fx.tracer.player length and radius. */
	void PlayerTracer(const FVector& From, const FVector& To, double SpeedCmPerS);
	/** An enemy round: flash at the muzzle, the tracer to the first thing it meets (presentation trace). */
	void EnemyShot(const AActor* Shooter, const FVector& Muzzle, const FVector& Dir);
	bool CanDrawTracers() const { return bReady && Streaks.Num() > 0; }
	/** Ends every tracer, flash card and flash light still showing (the run is complete: nothing flies over the debrief). */
	void ClearShots();
	/** A brass casing out of the ejection port: seen at the first-person depth and size (ViewAt, ViewVelocity) for
	 *  fx.casing.viewLife s, then at its true size from its true place (WorldAt, WorldVelocity) for fx.casing.life. */
	void Casing(UStaticMesh* Mesh, const FTransform& ViewAt, const FVector& ViewVelocity, const FTransform& WorldAt, const FVector& WorldVelocity);

	/** The killing hit on a Goon (death pass): a dark burst out of the wound along the shot (fx.blood.kill; heavier and
	 *  more forward for a head shot, low and wide for a blast) and a spatter on the nearest surface behind the hit and on
	 *  the ground beside it. Victim is left out of the traces. Presentation only. */
	void BloodKill(const FVector& Point, const FVector& Dir, bool bHead, bool bBlast, const AActor* Victim);
	/** A pool spreading under a body that has come to rest (fx.blood.pool): returns a handle for EndBloodPool, or 0. */
	int32 BloodPool(const FVector& Point, const FVector& Normal);
	/** The body is gone: its pool fades out over Seconds (a pool that was already recycled is left alone). */
	void EndBloodPool(int32 Handle, double Seconds);
	/** Number of blood decals showing (tests and the cost probe). */
	int32 CountBlood() const;

	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Deinitialize() override;
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override { RETURN_QUICK_DECLARE_CYCLE_STAT(UMIEffects, STATGROUP_Tickables); }
	virtual bool IsTickable() const override { return bReady; }

private:
	struct FPuff
	{
		TObjectPtr<UStaticMeshComponent> Mesh;
		TObjectPtr<UMaterialInstanceDynamic> Mat;
		FVector Pos, Vel;
		double Age = 1e9, Life = 1.0, Size0 = 10.0, Size1 = 50.0, Opacity = 0.5, Fire = 0.0, Drag = 2.0, Rise = 0.0, Spin = 0.0, Roll = 0.0;
	};
	struct FCard
	{
		TObjectPtr<UStaticMeshComponent> Mesh;
		TObjectPtr<UMaterialInstanceDynamic> Mat;
		double Age = 1e9, Life = 0.05, Intensity = 1.0;
	};
	struct FLight
	{
		TObjectPtr<UPointLightComponent> Light;
		double Age = 1e9, Life = 0.06, Peak = 0.0;
	};
	struct FMark
	{
		TObjectPtr<UDecalComponent> Decal;
		TObjectPtr<UMaterialInstanceDynamic> Mat;
		double Age = 1e9, Life = 20.0;
	};
	/** A blood decal (spatter or pool) in its own pool, so bullet marks never recycle a body's pool. */
	struct FBlood
	{
		TObjectPtr<UDecalComponent> Decal;
		TObjectPtr<UMaterialInstanceDynamic> Mat;
		double Age = 1e9, Life = 40.0, Size0 = 40.0, Size1 = 40.0, Grow = 0.0, FadeOut = 3.0;
		int32 Serial = 0;
		bool bPool = false;  // a pool under a body: never taken by a later spatter while it lasts
	};
	struct FStreak
	{
		TObjectPtr<UStaticMeshComponent> Mesh;
		FVector From, To;
		double Age = 1e9, Life = 0.1, Length = 300.0, MinTail = 0.0;
	};

	void Bind();
	void OnImpact(const FMIImpactEvent& E);
	void OnExplosion(const FMIExplosionEvent& E);
	void Puff(const FVector& Pos, const FVector& Vel, double Life, double Size0, double Size1, double Opacity, const FLinearColor& Color, double Fire = 0.0, double Drag = 2.0, double Rise = 0.0);
	void Mark(const FVector& Point, const FVector& Normal, double Size, double Kind, const FLinearColor& Tint, double Life);
	void Light(const FVector& At, double Candela, double Radius, double Life, const FLinearColor& Color);
	/** One blood decal: Kind 1 a spatter, 1.25 a pool (MD_FX_Mark; an older material draws 1.25 as a spatter). */
	int32 Blood(const FVector& Point, const FVector& Normal, double Size0, double Size1, double Grow, double Kind, double Life, double Depth);
	FLinearColor SurfaceColor(FName Surface, bool& bSparks) const;

	UPROPERTY(Transient)
	TObjectPtr<AActor> Host;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> FlashMat;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> FlashViewMat;  // optional: depth test off, the player's own flash only
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> SmokeMat;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> TracerMat;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> MarkMat;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> DebrisMat;
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> BrassMat;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> Plane;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> Cylinder;
	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> Cube;

	TArray<FPuff> Puffs;
	TArray<FCard> Cards;
	TArray<FCard> ViewCards;  // the player's flash in FlashViewMat (empty without it: ViewFlash uses Cards)
	TArray<FLight> Lights;
	TArray<FMark> Marks;
	TArray<FStreak> Streaks;
	TArray<FBlood> Bloods;
	int32 NextPuff = 0, NextCard = 0, NextViewCard = 0, NextLight = 0, NextMark = 0, NextStreak = 0, NextBlood = 0, BloodSerial = 0;
	TArray<FDelegateHandle> Handles;
	TSharedPtr<class FJsonObject> Fx;
	bool bReady = false;
};
