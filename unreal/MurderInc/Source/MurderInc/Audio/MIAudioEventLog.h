#pragma once

#include "CoreMinimal.h"

struct FMIGameEvents;
class FJsonObject;
class FMIAudioDirector;

/**
 * A recorded stream of bus events with their times, plus samples of what the audio host observes (the listener, the
 * player's health, enemy positions). Recorded from a live bus (console MIAudioRecord) and replayed into a bus and a
 * director (MurderInc.Audio.Mixdown). File format: docs/unreal/AUDIO.md section 7.
 */
class MURDERINC_API FMIAudioEventLog
{
public:
	/** Record every event of this bus from now on; Now() gives the time. */
	void Record(FMIGameEvents& Bus, TFunction<double()> InNow);
	void StopRecording();
	/** A sample of the observed state (call it at a few hertz while recording). */
	void Observe(double Time, const FVector& Listener, const FVector& Forward, double Health, bool bAlive);

	bool Save(const FString& Path) const;
	bool Load(const FString& Path, FString& OutError);
	bool Parse(const TSharedPtr<FJsonObject>& Root, FString& OutError);

	double Duration() const;
	int32 Num() const { return Entries.Num(); }

	/**
	 * Replay every entry with Time in (From, To]: events are broadcast on the bus, observations go to the director.
	 * Returns the number of entries replayed.
	 */
	int32 ReplayRange(double From, double To, FMIGameEvents& Bus, FMIAudioDirector* Director) const;

private:
	struct FEntry
	{
		double Time = 0.0;
		TSharedPtr<FJsonObject> Json;
	};
	void Add(const TSharedPtr<FJsonObject>& J);

	TArray<FEntry> Entries;
	TFunction<double()> Now;
	FMIGameEvents* Bus = nullptr;
	TArray<FDelegateHandle> Handles;
};
