#pragma once

#include "CoreMinimal.h"
#include "Core/Data/MIData.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"

/**
 * The loadout data (docs/unreal/LOADOUT.md 3): guns.json, attachments.json, crew.json, levels.json, frontend.json and
 * frontend_text.json, with every {"$ref": "file.json#dotted.path"} resolved. Loaded by UMIDataSubsystem after
 * config.json on its own error path: a missing or invalid file never fails the config load, the front end then offers
 * only the parity set-up.
 *
 * The guns stay JSON in web units (their resolved `rules`, `extra` and `presentation`): FMILoadoutResolver copies
 * them, applies the attachment effects and parses them once (3.7).
 */

/** Small JSON helpers shared by the loader, the resolver and the tests. Paths are dotted, with [i] for array items. */
namespace MIJson
{
	MURDERINC_API TSharedPtr<FJsonValue> DeepCopy(const TSharedPtr<FJsonValue>& Value);
	MURDERINC_API TSharedPtr<FJsonObject> DeepCopy(const TSharedPtr<FJsonObject>& Object);
	/** The value at Path under Root ("spread.hip", "wallPull[0]"), or null. */
	MURDERINC_API TSharedPtr<FJsonValue> Get(const TSharedPtr<FJsonObject>& Root, const FString& Path);
	/** Replaces the value at an existing or new leaf (the parents must exist). */
	MURDERINC_API bool Set(const TSharedPtr<FJsonObject>& Root, const FString& Path, const TSharedPtr<FJsonValue>& Value);
	/** A number, or the string "Infinity" / "-Infinity" (JSON has no infinity: config.json meta.encoding). */
	MURDERINC_API bool Number(const TSharedPtr<FJsonValue>& Value, double& Out);
	MURDERINC_API double NumberOr(const TSharedPtr<FJsonObject>& Root, const FString& Path, double Fallback);
	MURDERINC_API FString StringOr(const TSharedPtr<FJsonObject>& Root, const FString& Path, const FString& Fallback = FString());
	MURDERINC_API TArray<FName> Names(const TSharedPtr<FJsonObject>& Root, const FString& Path);
	/** Condensed text of a value, for byte-equality checks. */
	MURDERINC_API FString Print(const TSharedPtr<FJsonObject>& Object);
	MURDERINC_API TSharedPtr<FJsonValue> MakeNumber(double V);
}

/** A target of an attachment stat: a path into the gun's JSON ("rules.adsTime", "extra.falloff.start",
 *  "rules.wallPull[0]", "rules.reload.*") and its clamp in that target's own web unit. */
struct FMIStatTarget
{
	FString Path;
	bool bClamp = false;
	double Min = 0.0, Max = 0.0;
};

struct FMIStatDef
{
	FName Id;
	TArray<FMIStatTarget> Targets;
	FName Better;  // lower, higher, none
	bool bTrade = false;
	FString Text, TextShorter;  // frontend.effects.* keys (empty: no line)
};

struct FMIEffect
{
	FName Stat;
	FName Op;  // set, add, mul, min, max
	double Value = 0.0;
};

struct FMIAttachmentDef
{
	FName Id;
	FName Slot;
	bool bBaseline = false;
	FString Text;                 // frontend.attachments.items.<x>
	TArray<FMIEffect> Effects;
	FString Mesh;                 // presentation.mesh (null until the pack import fills it)
	FName Variant;                // stock options: the gun variant they select
	TMap<FName, FName> Sockets;   // viewmodel marker -> socket on the part (sightRear -> SightEye ...)
	double Relief = -1.0;         // m, the optic's eye relief (negative: keep the gun's)
	FName ArtStatus;
	FName HandPose;
	bool bSuppressed = false;     // presentation.sound == "suppressed"
	bool bLaser = false;          // has a Beam
};

struct FMISlotDef
{
	FName Id;
	int32 Order = 0;
	FString Text;
	FName Focus;
};

/** attachments.json compatibility.<gun>.<slot> */
struct FMICompatSlot
{
	FName Slot;
	TArray<FName> Options;
	FName Default;      // None = the factory part
	bool bRequired = false;
	FName Mount;        // socket on the gun (guns.json mounts.<slot>.socket)
	bool bVariant = false;
	double GateMaxLength = -1.0;
};

struct FMIGunMount
{
	FName Socket;
	FName Status;
	TArray<FName> Hide;
};

struct FMIGunVariant
{
	FString Mesh;
	FString OpticMesh;  // the irons-folded twin, the base mesh whenever an optic other than the irons is fitted
	FName Status;
};

struct FMIGunEntry
{
	FName Id;
	FName Class;
	FString TextKey;      // text.weapons.chopper or frontend.weapons.stick (name, blurb under it)
	FString MeleeKey;
	bool bParity = false;
	TSharedPtr<FJsonObject> Rules;         // config.json schema, resolved
	TSharedPtr<FJsonObject> Extra;         // the new per-gun fields (may be empty)
	TSharedPtr<FJsonObject> Presentation;  // presentation.json schema, resolved
	TMap<FName, FMIGunVariant> Variants;   // open, folded
	TMap<FName, FMIGunMount> Mounts;       // slot -> mount
	FString MeshAsset;                     // art.mesh.asset
	FName MeshStatus;
	FString StandIn;
	FString Icon;
	TMap<FName, FName> ClipStatus;         // role -> exists, template, procedural, inProgress, inPack, missing, notApplicable
	TArray<FMICompatSlot> Compat;          // in slot order
	FMIWeaponDef Base;                     // parsed once with no parts (validation, the rack)

	const FMICompatSlot* FindCompat(FName Slot) const { return Compat.FindByPredicate([Slot](const FMICompatSlot& C) { return C.Slot == Slot; }); }
	FName ClipOf(FName Role) const { const FName* S = ClipStatus.Find(Role); return S ? *S : FName(TEXT("missing")); }
};

struct FMICrewJewel
{
	FString Mesh;
	FName Bone;
	bool bOffset = false;
	FVector Offset = FVector::ZeroVector;
};

struct FMICrewEntry
{
	FName Id;
	FString TextKey;      // frontend.crew.<id> (name, tagline, taglineFull)
	FString CallName;
	bool bOriginalLines = true;
	bool bParity = false;
	FString Arms;
	TMap<FName, FString> Materials;  // material slot -> material instance path
	TArray<FMICrewJewel> Jewellery;
	TArray<FString> LookAssets;      // every asset of the phase-1 look (offered when all exist)
	TArray<FString> LaterAssets;     // phase 2
	FString Portrait;
};

struct FMILevelProvides
{
	bool bPlayerStart = false, bExtraction = false, bNav = false, bExplosives = false, bTitlePath = false;
	int32 Objectives = 0, Ground = 0, Air = 0;
};

struct FMILevelEntry
{
	FName Id;
	FString TextKey;
	FString Map;
	TMap<FName, FString> Place;  // time -> text key
	TArray<FName> Times;
	FMILevelProvides Provides;
	FString Thumbnail;
};

struct FMIModeEntry
{
	FName Id;
	FString TextKey, Tagline, Radio;
	FMILevelProvides Needs;
	FName Score;
};

/** One gun's build: slot -> part (a missing slot is the factory part). */
struct FMIGunBuild
{
	TMap<FName, FName> Parts;
	bool operator==(const FMIGunBuild& O) const;
};

/** The run's set-up (LOADOUT.md 7): who, what, where and how. Mode, difficulty and time are the settings'. */
struct MURDERINC_API FMIRunSetup
{
	FName Crew;
	TArray<FName> Guns;                  // 1 to 4, slot order
	TMap<FName, FMIGunBuild> Builds;     // every gun ever built
	FName Level;
	FName Mode, Difficulty, Time;
	TArray<FName> Seen;
	bool bPlayed = false;

	const FMIGunBuild* BuildOf(FName Gun) const { return Builds.Find(Gun); }
	FName PartIn(FName Gun, FName Slot) const;
	bool SameLoadout(const FMIRunSetup& O) const;
	FString ToJsonString() const;
};

struct MURDERINC_API FMILoadoutData
{
	// The documents, resolved.
	TSharedPtr<FJsonObject> GunsJson, AttachmentsJson, CrewJson, LevelsJson, FrontendJson, TextJson;

	TArray<FName> Roster;
	TMap<FName, FMIGunEntry> Guns;
	TArray<FName> CoreRoles;
	TArray<FName> Playable;               // clip statuses that play now
	TSharedPtr<FJsonObject> ExtraDefaults;  // name -> value (numbers resolved)
	FName DefaultPool;

	TArray<FMISlotDef> Slots;             // in order
	TMap<FName, FMIStatDef> Stats;
	TMap<FName, FMIAttachmentDef> Attachments;
	double FactorMin = 0.5, FactorMax = 2.0;
	double TradeMin = 0.4, TradeMax = 2.5;

	TArray<FName> CrewOrder;
	TMap<FName, FMICrewEntry> Crew;
	TMap<FString, FString> CrewReplaces;  // text.json key -> frontend.crewLines.* key

	TArray<FName> LevelOrder;
	TMap<FName, FMILevelEntry> Levels;
	TArray<FName> ModeOrder;
	TMap<FName, FMIModeEntry> Modes;
	TArray<FName> Difficulties;

	// frontend.json
	FName ParityCrew, ParityLevel;
	TArray<FName> ParityGuns;
	int32 CarryMax = 4, CarryMin = 1;
	int32 WheelMinGuns = 3;
	double WheelHold = 0.25, WheelDeadzone = 0.5, WheelMouseRadius = 60.0;
	double InspectHold = 0.4, ResetHold = 0.6;

	const FMIGunEntry* FindGun(FName Id) const { return Guns.Find(Id); }
	const FMIAttachmentDef* FindPart(FName Id) const { return Attachments.Find(Id); }
	const FMICrewEntry* FindCrew(FName Id) const { return Crew.Find(Id); }
	const FMISlotDef* FindSlot(FName Id) const { return Slots.FindByPredicate([Id](const FMISlotDef& S) { return S.Id == Id; }); }

	/** frontend_text.json: a plain string, or a template with its arguments. Empty when missing. */
	FString Text(const FString& Key) const;
	FString Format(const FString& Key, const TMap<FString, FString>& Args) const;
	TArray<FString> TextList(const FString& Key) const;
	bool HasText(const FString& Key) const;

	/** $refs that did not resolve while parsing ("guns.json: config.json#weapons.x"). */
	TArray<FString> Unresolved;

	/** The parity set-up (frontend.json parity) with the given settings. */
	FMIRunSetup ParitySetup(FName Mode, FName Difficulty, FName Time) const;

	/** Reads the six files from the data directory. ConfigRoot / PresentationRoot: the documents $refs point into. */
	static bool Load(FMILoadoutData& Out, FString& OutError);
	/** Parses already loaded documents (tests hand in fixtures). Files names the documents a $ref may point at. */
	static bool Parse(const TMap<FString, TSharedPtr<FJsonObject>>& Files, FMILoadoutData& Out, FString& OutError);

	/** Dev only (console MISetup overlay <file>): patches statuses and mesh paths in memory, as the pack import will
	 *  write them (guns.<id>.variants.<v>.{mesh,status}, guns.<id>.mounts.<slot>.status, attachments.<id>.mesh).
	 *  Nothing is written back. Returns the number of fields changed. */
	int32 ApplyOverlay(const TSharedPtr<FJsonObject>& Overlay);

	/** The checks of LOADOUT.md 3.1 that need only the data (no resolver). Every problem is listed. */
	void ValidateData(TArray<FString>& OutProblems) const;
};

/** Is an asset path present (on the box with the pack; not in a clean checkout)? Tests replace it. */
using FMIAssetExists = TFunction<bool(const FString& /*ObjectPath*/)>;

/** What the rack, the Workbench and the crew cards may offer (LOADOUT.md 3.2 ready, 3.3 mounts, 3.4 phases). */
struct MURDERINC_API FMIReadiness
{
	const FMILoadoutData* Data = nullptr;
	FMIAssetExists AssetExists;
	bool bShowUnready = false;  // mi.Setup.ShowUnready 1

	bool IsGunReady(FName Gun) const;
	bool IsGunOffered(FName Gun) const { return IsGunReady(Gun) || bShowUnready; }
	/** The slots offered on a gun, in slot order: listed in its compatibility row, the mount exists (or variants do). */
	TArray<FName> OfferedSlots(FName Gun) const;
	/** The parts offered in a slot (a variant option only when its variant exists). */
	TArray<FName> OfferedParts(FName Gun, FName Slot) const;
	bool IsCrewOffered(FName Crew) const;
	bool HasLater(FName Crew) const;
	/** The base mesh of a build (its stock variant), or the gun's presentation mesh. */
	FString BaseMesh(FName Gun, const FMIGunBuild* Build) const;

	/** LOADOUT.md 7: unknown or unoffered ids dropped, required slots defaulted, duplicates and gaps removed, cut to
	 *  four, a mode the level does not provide -> its first mode. Returns the number of corrections. */
	int32 Validate(FMIRunSetup& Setup) const;
	/** The default build of a gun (every required slot's default). */
	FMIGunBuild DefaultBuild(FName Gun) const;
	TArray<FName> ModesOf(FName Level) const;

	static FMIAssetExists PackageExists();
};
