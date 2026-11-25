#pragma once

#include "CoreMinimal.h"
#include "Core/Data/MIData.h"
#include "Core/Data/MILoadoutData.h"
#include "Weapons/MIViewmodel.h"

/**
 * FMILoadoutResolver (docs/unreal/LOADOUT.md 3.7): from the loadout data, a set-up, config.json and presentation.json,
 * the run's FMIWeaponsData and FMIViewmodelData. All attachment effects are applied to copies of the guns' JSON in web
 * units, then every gun is parsed once by the same parsers config.json goes through, so a gun with no parts is its
 * JSON untouched and the parity set-up is the web game by construction. Pure: no world, no UObject.
 */

/** A fitted add-on part as the gun assembly mounts it. */
struct FMIResolvedPart
{
	FName Slot;
	FName Part;
	FString Mesh;          // the part's mesh (empty until the pack import fills attachments.json)
	FString TopRoundMesh;  // a magazine part's visible top round (a piece of its own, the part's frame)
	FName Socket;          // the gun's mount socket
	TArray<FName> Hide;    // gun parts the part replaces (the CHOPPER's Booster)
	FName RideBone;        // the gun bone the part follows once placed on its socket (a magazine rides 'magazine')
	TMap<FName, FName> Markers;  // viewmodel marker -> socket on the part mesh
};

struct FMIResolvedGun
{
	FName Id;
	TSharedPtr<FJsonObject> Rules, Extra, Presentation;  // after the effects, web units
	FMIWeaponDef Def;
	FMIGunViewData View;
	FString BaseMesh;       // the build's variant (the stock slot picks it)
	FString MagazineMesh;   // the factory magazine the stage draws in the well (the anim set's magazine, or presentation.magazine)
	FString MagazineTopRound;  // its top round, a piece of its own in the same frame
	FName MagazineAttach;   // the bone it rides (our guns: 'magazine', authored in the gun's space) or the socket it sits on (the pack's)
	TArray<FMIResolvedPart> Parts;
	bool bLaser = false;
};

struct FMIResolvedRun
{
	FMIWeaponsData Weapons;
	FMIViewmodelData View;
	TArray<FMIResolvedGun> Guns;  // slot order
};

class MURDERINC_API FMILoadoutResolver
{
public:
	FMILoadoutResolver(const FMILoadoutData& InData, const TSharedPtr<FJsonObject>& InConfig, const TSharedPtr<FJsonObject>& InPresentation)
		: Data(InData), Config(InConfig), Presentation(InPresentation) {}

	/** `extra` of a gun with every missing field taken from guns.json extraDefaults (numbers, so a mul has a value). */
	TSharedPtr<FJsonObject> FilledExtra(const FMIGunEntry& Gun) const;

	/** The effects of Parts (in slot order) on a {"rules": ..., "extra": ...} document, in place (LOADOUT.md 3.3 ops). */
	bool ApplyEffects(const TArray<const FMIAttachmentDef*>& Parts, const TSharedPtr<FJsonObject>& Doc, FString& OutError) const;

	/** One gun with a build (null: the factory gun). Ready, when given, picks the variant mesh that exists. */
	bool ResolveGun(FName Gun, const FMIGunBuild* Build, const FMIReadiness* Ready, FMIResolvedGun& Out, FString& OutError) const;

	/** The whole run: the carried guns in slot order, the shared common, melee and global view data. */
	bool Resolve(const FMIRunSetup& Setup, const FMIReadiness* Ready, FMIResolvedRun& Out, FString& OutError) const;

	/** The fitted parts of a build in slot order (baselines included: they have no effect). */
	TArray<const FMIAttachmentDef*> FittedParts(FName Gun, const FMIGunBuild* Build) const;

	/** Loads config.json and presentation.json from the data directory. */
	static bool LoadRoots(TSharedPtr<FJsonObject>& OutConfig, TSharedPtr<FJsonObject>& OutPresentation, FString& OutError);

	const FMILoadoutData& GetData() const { return Data; }

private:
	const FMILoadoutData& Data;
	TSharedPtr<FJsonObject> Config;
	TSharedPtr<FJsonObject> Presentation;
};

/** The six rack bars (LOADOUT.md 2.5), 0..1, from a resolved gun's JSON in web units. GoonHp: at the difficulty. */
struct FMIGunBars
{
	double Damage = 0, Kill = 0, Control = 0, Handling = 0, Aimed = 0, Hip = 0;
	/** Rounds and seconds to drop a Goon with body shots at 10 m. */
	int32 Rounds = 0;
	double KillTime = 0;

	static FMIGunBars Of(const FMIResolvedGun& Gun, double GoonHp);
};
