#pragma once

#include "CoreMinimal.h"
#include "Core/Data/MILoadoutData.h"
#include "Flow/MISettings.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "MIRunSetupSubsystem.generated.h"

/**
 * The run's set-up across level travel, save and load (docs/unreal/LOADOUT.md 7): the crew member, the carried guns
 * in slot order, every gun's build, the level, the NEW badges and whether a run was ever played. Mode, difficulty and
 * time stay the settings (FMISettings). A saved set-up is validated against what is offered now, so a removed pack
 * degrades to a playable set-up, never to a crash.
 */
UCLASS()
class MURDERINC_API UMIRunSetupSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	static UMIRunSetupSubsystem* Get(const UObject* WorldContextObject);

	/** Offered or not, ready or not: the data, the pack's presence on disk, mi.Setup.ShowUnready. */
	FMIReadiness MakeReadiness() const;
	const FMILoadoutData* GetData() const;

	const FMIRunSetup& GetSetup() const { return Setup; }
	/** Replaces the set-up (validated). */
	void SetSetup(const FMIRunSetup& In);
	/** The set-up read from the save game, validated (the parity set-up when there is none). */
	void Load(const UMISaveGame* Save, const FMISettings& Settings);
	void Write(UMISaveGame& Save) const;
	bool HasSetup() const { return bHave; }

	static void ToSave(const FMIRunSetup& In, FMISetupSave& Out);
	static void FromSave(const FMISetupSave& In, FMIRunSetup& Out);

private:
	FMIRunSetup Setup;
	bool bHave = false;
};
