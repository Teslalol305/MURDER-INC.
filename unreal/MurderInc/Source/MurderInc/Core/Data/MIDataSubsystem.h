#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Core/Data/MIData.h"
#include "MIDataSubsystem.generated.h"

class FJsonObject;

/**
 * Loads Content/Data/config.json once when the game instance starts and hands out the tuning tables.
 * Every gameplay number comes from here; the code holds no tuning constants.
 * The loading functions are static so that automation tests and editor tools can use them without a game instance.
 */
UCLASS()
class MURDERINC_API UMIDataSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;

	/** The subsystem of the game instance that owns this object's world, or null (editor world, no game running). */
	static const UMIDataSubsystem* Get(const UObject* WorldContextObject);

	/** False when config.json was missing or incomplete; the reason is in the log (LogMI, Error). */
	bool IsLoaded() const { return bLoaded; }
	const FMIConfigData& GetConfig() const { return Config; }
	const FMIPlayerData& GetPlayer() const { return Config.Player; }
	const FMIWeaponsData& GetWeapons() const { return Config.Weapons; }
	const FMIExplosivesData& GetExplosives() const { return Config.Explosives; }

	/** The whole config.json document, for tables that have no struct yet. Null when loading failed. */
	TSharedPtr<FJsonObject> GetConfigJson() const { return ConfigJson; }

	/** <project>/Content/Data: loose files in the editor and in packaged builds (staged as non-UFS). */
	static FString GetDataDir();

	/** Read and parse one file of the data directory, for example "config.json". */
	static bool LoadJsonFile(const FString& FileName, TSharedPtr<FJsonObject>& OutRoot, FString& OutError);

	/** Fill the structs from a parsed config.json, converting to Unreal units. Fails when a field is missing. */
	static bool ParseConfig(const TSharedPtr<FJsonObject>& Root, FMIConfigData& Out, FString& OutError);

	/** LoadJsonFile("config.json") followed by ParseConfig. */
	static bool LoadConfig(FMIConfigData& Out, FString& OutError);

private:
	FMIConfigData Config;
	TSharedPtr<FJsonObject> ConfigJson;
	bool bLoaded = false;
};
