#include "Core/Data/MIDataSubsystem.h"

#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "MurderInc.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace MIDataSubsystemPrivate
{
	/** Reads numbers by dotted path ("player.speed.walk") and remembers every path that was not there. */
	struct FReader
	{
		TSharedPtr<FJsonObject> Root;
		TArray<FString> Missing;

		TSharedPtr<FJsonObject> Parent(const FString& Path, FString& OutLeaf) const
		{
			TArray<FString> Parts;
			Path.ParseIntoArray(Parts, TEXT("."));
			TSharedPtr<FJsonObject> Object = Root;
			for (int32 Index = 0; Object.IsValid() && Index < Parts.Num() - 1; ++Index)
			{
				const TSharedPtr<FJsonObject>* Child = nullptr;
				if (Object->TryGetObjectField(Parts[Index], Child) && Child)
				{
					Object = *Child;
				}
				else
				{
					Object.Reset();
				}
			}
			OutLeaf = Parts.Num() > 0 ? Parts.Last() : FString();
			return Object;
		}

		double Number(const TCHAR* Path, double Scale = 1.0)
		{
			FString Leaf;
			double Value = 0.0;
			const TSharedPtr<FJsonObject> Object = Parent(Path, Leaf);
			if (!Object.IsValid() || !Object->TryGetNumberField(Leaf, Value))
			{
				Missing.Add(Path);
				return 0.0;
			}
			return Value * Scale;
		}

		FString String(const TCHAR* Path)
		{
			FString Leaf;
			FString Value;
			const TSharedPtr<FJsonObject> Object = Parent(Path, Leaf);
			if (!Object.IsValid() || !Object->TryGetStringField(Leaf, Value))
			{
				Missing.Add(Path);
			}
			return Value;
		}
	};

	// The file is in metres and radians (meta.units.web); the game runs in centimetres and degrees.
	constexpr double MetresToCm = 100.0;
	constexpr double RadToDeg = 180.0 / UE_DOUBLE_PI;
}

void UMIDataSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);

	FString Error;
	bLoaded = LoadJsonFile(TEXT("config.json"), ConfigJson, Error) && ParseConfig(ConfigJson, Config, Error);
	if (bLoaded)
	{
		UE_LOG(LogMI, Log, TEXT("Data: config.json loaded (%s, schema %d, seed %d) from %s"),
			*Config.Game, Config.Schema, Config.Seed, *GetDataDir());
	}
	else
	{
		ConfigJson.Reset();
		UE_LOG(LogMI, Error, TEXT("Data: %s"), *Error);
	}
}

const UMIDataSubsystem* UMIDataSubsystem::Get(const UObject* WorldContextObject)
{
	const UGameInstance* GameInstance = WorldContextObject ? UGameplayStatics::GetGameInstance(WorldContextObject) : nullptr;
	return GameInstance ? GameInstance->GetSubsystem<UMIDataSubsystem>() : nullptr;
}

FString UMIDataSubsystem::GetDataDir()
{
	return FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Data"));
}

bool UMIDataSubsystem::LoadJsonFile(const FString& FileName, TSharedPtr<FJsonObject>& OutRoot, FString& OutError)
{
	const FString Path = FPaths::Combine(GetDataDir(), FileName);
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *Path))
	{
		OutError = FString::Printf(TEXT("cannot read %s"), *Path);
		return false;
	}
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, OutRoot) || !OutRoot.IsValid())
	{
		OutError = FString::Printf(TEXT("%s is not valid JSON: %s"), *Path, *Reader->GetErrorMessage());
		return false;
	}
	return true;
}

bool UMIDataSubsystem::ParseConfig(const TSharedPtr<FJsonObject>& Root, FMIConfigData& Out, FString& OutError)
{
	using namespace MIDataSubsystemPrivate;
	if (!Root.IsValid())
	{
		OutError = TEXT("config.json: no document");
		return false;
	}
	FReader In{Root};

	Out.Game = In.String(TEXT("meta.game"));
	Out.Schema = static_cast<int32>(In.Number(TEXT("meta.schema")));
	Out.Seed = static_cast<int32>(In.Number(TEXT("meta.seed")));

	FMIPlayerData& P = Out.Player;
	P.Body.Radius = In.Number(TEXT("player.body.radius"), MetresToCm);
	P.Body.Height = In.Number(TEXT("player.body.height"), MetresToCm);
	P.Body.CrouchHeight = In.Number(TEXT("player.body.crouchHeight"), MetresToCm);
	P.Body.Eye = In.Number(TEXT("player.body.eye"), MetresToCm);
	P.Body.CrouchEye = In.Number(TEXT("player.body.crouchEye"), MetresToCm);
	P.Body.EyeRate = In.Number(TEXT("player.body.eyeRate"));
	P.Body.StepHeight = In.Number(TEXT("player.body.stepHeight"), MetresToCm);

	P.Speed.Walk = In.Number(TEXT("player.speed.walk"), MetresToCm);
	P.Speed.Sprint = In.Number(TEXT("player.speed.sprint"), MetresToCm);
	P.Speed.Crouch = In.Number(TEXT("player.speed.crouch"), MetresToCm);
	P.Speed.Ads = In.Number(TEXT("player.speed.ads"), MetresToCm);
	P.Speed.Backpedal = In.Number(TEXT("player.speed.backpedal"));

	P.Accel.Ground = In.Number(TEXT("player.accel.ground"), MetresToCm);
	P.Accel.GroundStop = In.Number(TEXT("player.accel.groundStop"), MetresToCm);
	P.Accel.Air = In.Number(TEXT("player.accel.air"), MetresToCm);
	P.Accel.AirStop = In.Number(TEXT("player.accel.airStop"), MetresToCm);

	P.Jump.Gravity = In.Number(TEXT("player.jump.gravity"), MetresToCm);
	P.Jump.Apex = In.Number(TEXT("player.jump.apex"), MetresToCm);
	P.Jump.Coyote = In.Number(TEXT("player.jump.coyote"));
	P.Jump.Buffer = In.Number(TEXT("player.jump.buffer"));
	P.Jump.Terminal = In.Number(TEXT("player.jump.terminal"), MetresToCm);

	P.Sprint.MinForward = In.Number(TEXT("player.sprint.minForward"));
	P.Sprint.MaxStrafe = In.Number(TEXT("player.sprint.maxStrafe"));
	P.Sprint.MinSpeedFrac = In.Number(TEXT("player.sprint.minSpeedFrac"));

	P.Fov.Base = In.Number(TEXT("player.fov.base"));
	P.Fov.Min = In.Number(TEXT("player.fov.min"));
	P.Fov.Max = In.Number(TEXT("player.fov.max"));
	P.Fov.SprintAdd = In.Number(TEXT("player.fov.sprintAdd"));
	P.Fov.Ads = In.Number(TEXT("player.fov.ads"));
	P.Fov.Rate = In.Number(TEXT("player.fov.rate"));

	P.Look.PitchLimit = In.Number(TEXT("player.look.pitchLimit"), RadToDeg);
	P.Look.MouseDegreesPerCount = In.Number(TEXT("player.input.mouse"), RadToDeg);

	if (In.Missing.Num() > 0)
	{
		OutError = FString::Printf(TEXT("config.json: %d field(s) missing: %s"), In.Missing.Num(), *FString::Join(In.Missing, TEXT(", ")));
		return false;
	}
	return true;
}

bool UMIDataSubsystem::LoadConfig(FMIConfigData& Out, FString& OutError)
{
	TSharedPtr<FJsonObject> Root;
	return LoadJsonFile(TEXT("config.json"), Root, OutError) && ParseConfig(Root, Out, OutError);
}
