#include "Flow/MISettings.h"

#include "Core/Data/MIDataSubsystem.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"

namespace MISettingsPrivate
{
	void Range(const TSharedPtr<FJsonObject>& O, const TCHAR* Field, double& Min, double& Max)
	{
		const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
		if (O->TryGetArrayField(Field, A) && A->Num() == 2)
		{
			Min = (*A)[0]->AsNumber();
			Max = (*A)[1]->AsNumber();
		}
	}

	void Names(const TSharedPtr<FJsonObject>& O, const TCHAR* Field, TArray<FName>& Out)
	{
		const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
		if (O->TryGetArrayField(Field, A))
		{
			Out.Reset();
			for (const TSharedPtr<FJsonValue>& V : *A)
			{
				Out.Add(FName(V->AsString()));
			}
		}
	}
}

bool FMISettings::LoadDefaults(FMISettings& Out, FString& OutError)
{
	using namespace MISettingsPrivate;
	TSharedPtr<FJsonObject> Config, RulesJson;
	if (!UMIDataSubsystem::LoadJsonFile(TEXT("config.json"), Config, OutError) || !UMIDataSubsystem::LoadJsonFile(TEXT("rules.json"), RulesJson, OutError))
	{
		return false;
	}
	Out = FMISettings();
	const TSharedPtr<FJsonObject>* R = nullptr;
	if (!RulesJson->TryGetObjectField(TEXT("settings"), R))
	{
		OutError = TEXT("rules.json: settings missing");
		return false;
	}
	FRules& T = Out.Rules;
	(*R)->TryGetStringField(TEXT("slot"), T.Slot);
	Range(*R, TEXT("sens"), T.SensMin, T.SensMax);
	Range(*R, TEXT("fov"), T.FovMin, T.FovMax);
	Range(*R, TEXT("volume"), T.VolumeMin, T.VolumeMax);
	double VMin = 1, VMax = 3;
	Range(*R, TEXT("view"), VMin, VMax);
	T.ViewMin = static_cast<int32>(VMin);
	T.ViewMax = static_cast<int32>(VMax);
	(*R)->TryGetNumberField(TEXT("sensStep"), T.SensStep);
	(*R)->TryGetNumberField(TEXT("fovStep"), T.FovStep);
	(*R)->TryGetNumberField(TEXT("volumeStep"), T.VolumeStep);
	Names(*R, TEXT("quality"), T.Qualities);
	Names(*R, TEXT("mode"), T.Modes);
	Names(*R, TEXT("difficulty"), T.Difficulties);
	Names(*R, TEXT("time"), T.Times);

	const TSharedPtr<FJsonObject>* S = nullptr;
	const TSharedPtr<FJsonObject>* D = nullptr;
	if (!Config->TryGetObjectField(TEXT("settings"), S) || !(*S)->TryGetObjectField(TEXT("defaults"), D))
	{
		OutError = TEXT("config.json: settings.defaults missing");
		return false;
	}
	const TSharedPtr<FJsonObject>& Def = *D;
	Out.Mode = FName(Def->GetStringField(TEXT("mode")));
	Out.Difficulty = FName(Def->GetStringField(TEXT("difficulty")));
	Out.Time = FName(Def->GetStringField(TEXT("time")));
	Out.Quality = FName(Def->GetStringField(TEXT("quality")));
	Out.Sens = Def->GetNumberField(TEXT("sens"));
	Out.bInvertY = Def->GetBoolField(TEXT("invertY"));
	Out.Volume = Def->GetNumberField(TEXT("volume"));
	Out.Fov = Def->GetNumberField(TEXT("fov"));
	Out.View = static_cast<int32>(Def->GetNumberField(TEXT("view")));
	return true;
}

bool FMISettings::SetName(FName& Field, FName V, const TArray<FName>& Allowed)
{
	if (!Allowed.Contains(V) || Field == V)
	{
		return false;
	}
	Field = V;
	return true;
}

FName FMISettings::Next(FName Current, const TArray<FName>& Values, int32 Step)
{
	if (Values.Num() == 0)
	{
		return Current;
	}
	const int32 I = FMath::Max(0, Values.IndexOfByKey(Current));
	return Values[((I + Step) % Values.Num() + Values.Num()) % Values.Num()];
}

bool FMISettings::SetSens(double V)
{
	if (!FMath::IsFinite(V))
	{
		return false;
	}
	V = FMath::Clamp(V, Rules.SensMin, Rules.SensMax);
	if (V == Sens)
	{
		return false;
	}
	Sens = V;
	return true;
}

bool FMISettings::SetVolume(double V)
{
	if (!FMath::IsFinite(V))
	{
		return false;
	}
	V = FMath::Clamp(V, Rules.VolumeMin, Rules.VolumeMax);
	if (V == Volume)
	{
		return false;
	}
	Volume = V;
	return true;
}

bool FMISettings::SetFov(double V)
{
	if (!FMath::IsFinite(V))
	{
		return false;
	}
	V = FMath::FloorToDouble(FMath::Clamp(V, Rules.FovMin, Rules.FovMax) + 0.5);
	if (V == Fov)
	{
		return false;
	}
	Fov = V;
	return true;
}

bool FMISettings::SetView(int32 V)
{
	if (V < Rules.ViewMin || V > Rules.ViewMax || V == View)
	{
		return false;
	}
	View = V;
	return true;
}

bool FMISettings::SetInvertY(bool V)
{
	if (V == bInvertY)
	{
		return false;
	}
	bInvertY = V;
	return true;
}

bool FMISettings::SetPadPlayStation(bool V)
{
	if (V == bPadPlayStation)
	{
		return false;
	}
	bPadPlayStation = V;
	return true;
}

bool FMISettings::SetGuide(bool V)
{
	if (V == bGuide)
	{
		return false;
	}
	bGuide = V;
	return true;
}

bool FMISettings::SetBest(double Score)
{
	const int32 N = static_cast<int32>(FMath::FloorToDouble(Score + 0.5));
	SessionBest = FMath::Max(SessionBest, N);
	if (N <= Best)
	{
		return false;
	}
	Best = N;
	return true;
}

void FMISettings::ToSave(UMISaveGame& Save) const
{
	Save.Mode = Mode.ToString();
	Save.Difficulty = Difficulty.ToString();
	Save.Time = Time.ToString();
	Save.Quality = Quality.ToString();
	Save.Sens = Sens;
	Save.bInvertY = bInvertY;
	Save.bPadPlayStation = bPadPlayStation;
	Save.bGuide = bGuide;
	Save.Volume = Volume;
	Save.Fov = Fov;
	Save.View = View;
	Save.Best = Best;
}

void FMISettings::FromSave(const UMISaveGame& Save)
{
	SetMode(FName(Save.Mode));
	SetDifficulty(FName(Save.Difficulty));
	SetTime(FName(Save.Time));
	SetQuality(FName(Save.Quality));
	SetSens(Save.Sens);
	SetInvertY(Save.bInvertY);
	SetPadPlayStation(Save.bPadPlayStation);
	SetGuide(Save.bGuide);
	SetVolume(Save.Volume);
	SetFov(Save.Fov);
	SetView(Save.View);
	Best = FMath::Max(0, Save.Best);
}
