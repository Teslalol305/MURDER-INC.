#include "Cloud/MIPacing.h"

#include "DynamicRHI.h"
#include "HAL/PlatformProcess.h"
#include "HAL/PlatformTime.h"
#include "Misc/App.h"
#include "Misc/CoreDelegates.h"
#include "Misc/ScopeLock.h"
#include "RHICommandList.h"
#include "RHIResources.h"
#include "RenderingThread.h"
#include "Stats/ThreadIdleStats.h"

// ---- the frame-rate target ------------------------------------------------------------------------------------------

int32 FMIFrameRateGovernor::TargetFor(int32 FramesPerSecond)
{
	if (FramesPerSecond <= 0)
	{
		return Targets[0];
	}
	for (const int32 T : Targets)
	{
		if (FramesPerSecond >= T)
		{
			return T;
		}
	}
	return Targets[NumTargets - 1];
}

void FMIFrameRateGovernor::Pin(int32 FramesPerSecond)
{
	bPinned = FramesPerSecond > 0;
	if (bPinned)
	{
		const int32 T = TargetFor(FramesPerSecond);
		for (int32 I = 0; I < NumTargets; ++I)
		{
			if (Targets[I] == T)
			{
				Index = I;
			}
		}
	}
	OverFor = UnderFor = 0.0;
}

bool FMIFrameRateGovernor::Update(const FInput& In)
{
	const double Step = FMath::Max(0.0, In.Seconds);
	SinceRaise += Step;
	if (RaiseWait <= 0.0)
	{
		RaiseWait = RaiseAfter;
	}
	if (bPinned)
	{
		OverFor = UnderFor = 0.0;
		return false;
	}
	const double Frame = FrameMs();
	// Cannot keep up: over its share of the frame although the picture is already the smallest, or held back by the
	// pacer (the GPU did not finish in time, whatever its measured time says). Only live play counts: the seconds in
	// which the game starts are full of long frames on any card (measured on a free GPU: the pacer waits a third of
	// the first second), and a set-up screen is not what the player came for.
	const bool bOver = !In.bSafeMoment && In.bSmallestPicture && ((In.GpuMs > 0.0 && In.GpuMs > OverShare * Frame) || In.bHeldBack);
	if (bOver)
	{
		UnderFor = 0.0;
		OverFor += Step;
		if (OverFor >= DropAfter && Index < NumTargets - 1)
		{
			const int32 From = Target();
			++Index;
			OverFor = 0.0;
			if (SinceRaise < RetryWindow)
			{
				RaiseWait = FMath::Min(RaiseWait * 2.0, MaxRaiseAfter);  // the last rise did not hold: try later next time
			}
			Reason = FString::Printf(TEXT("%d -> %d frames a second: the GPU took %.1f ms a frame%s at the smallest picture, over %.0f %% of %.1f ms for %.1f s"),
				From, Target(), In.GpuMs, In.bHeldBack ? TEXT(" and held the game back") : TEXT(""), OverShare * 100.0, Frame, DropAfter);
			return true;
		}
		return false;
	}
	OverFor = 0.0;
	const bool bUnder = In.GpuMs > 0.0 && In.GpuMs < UnderShare * Frame && !In.bHeldBack;
	UnderFor = bUnder ? UnderFor + Step : 0.0;
	if (UnderFor >= RaiseWait && In.bSafeMoment && Index > 0)
	{
		const int32 From = Target();
		--Index;
		Reason = FString::Printf(TEXT("%d -> %d frames a second: the GPU took %.1f ms a frame, under %.0f %% of %.1f ms for %.0f s, and no run is being played"),
			From, Target(), In.GpuMs, UnderShare * 100.0, Frame, UnderFor);
		UnderFor = 0.0;
		SinceRaise = 0.0;
		return true;
	}
	return false;
}

// ---- what may be tuned from outside ---------------------------------------------------------------------------------

namespace MITuningPrivate
{
	struct FRule
	{
		const TCHAR* Name;   // a family (ends with a dot) or one variable
		double Min, Max;     // the range of a single variable; Min > Max: any value
	};
	// docs/unreal/PREFLIGHT.md V3-9 and V3-11. The ranges are for the variables that could exhaust the GPU or its
	// memory (a crash is an email to the owner): a visitor can put these on a link.
	const FRule Rules[] = {
		{TEXT("PixelStreaming2."), 1, 0},
		{TEXT("PixelStreaming."), 1, 0},
		{TEXT("MI.Cloud."), 1, 0},
		{TEXT("sg."), 0, 4},
		{TEXT("r.DynamicRes.MinScreenPercentage"), 25, 100},
		{TEXT("r.DynamicRes.MaxScreenPercentage"), 25, 100},
		{TEXT("r.DynamicRes."), 1, 0},
		{TEXT("r.ScreenPercentage"), 25, 100},
		{TEXT("t.MaxFPS"), 0, 120},
		{TEXT("r.Streaming.PoolSize"), 200, 3000},
		{TEXT("r.GTSyncType"), 0, 2},
		{TEXT("r.OneFrameThreadLag"), 0, 1},
		{TEXT("r.VolumetricFog."), 1, 0},
	};

	const FRule* Find(const FString& Name)
	{
		for (const FRule& R : Rules)
		{
			const FString Rule(R.Name);
			if (Rule.EndsWith(TEXT(".")) ? Name.StartsWith(Rule, ESearchCase::IgnoreCase) : Name.Equals(Rule, ESearchCase::IgnoreCase))
			{
				return &R;
			}
		}
		return nullptr;
	}
}

bool MITuning::IsAllowed(const FString& Name, const FString& Value)
{
	if (Name.IsEmpty() || Name.Len() > 96 || Value.Len() > 128)
	{
		return false;
	}
	for (const TCHAR Ch : Name)
	{
		if (!(FChar::IsAlnum(Ch) || Ch == TEXT('.') || Ch == TEXT('_')))
		{
			return false;
		}
	}
	for (const TCHAR Ch : Value)
	{
		// One value: nothing that starts another command or another argument.
		if (Ch < TEXT(' ') || Ch == TEXT('|') || Ch == TEXT(';') || Ch == TEXT('"') || Ch == TEXT('\''))
		{
			return false;
		}
	}
	const MITuningPrivate::FRule* Rule = MITuningPrivate::Find(Name);
	if (!Rule)
	{
		return false;
	}
	if (Rule->Min <= Rule->Max && !Value.IsEmpty())
	{
		if (!Value.IsNumeric())
		{
			return false;
		}
		const double V = FCString::Atod(*Value);
		return V >= Rule->Min && V <= Rule->Max;
	}
	return true;
}

FString MITuning::AllowedList()
{
	FString Out;
	for (const MITuningPrivate::FRule& R : MITuningPrivate::Rules)
	{
		Out += (Out.IsEmpty() ? TEXT("") : TEXT(", "));
		Out += R.Name;
		if (FString(R.Name).EndsWith(TEXT(".")))
		{
			Out += TEXT("*");
		}
		if (R.Min <= R.Max)
		{
			Out += FString::Printf(TEXT(" (%g to %g)"), R.Min, R.Max);
		}
	}
	return Out;
}

void MITuning::ParseOption(const FString& Text, TArray<TPair<FString, FString>>& OutAllowed, TArray<FString>& OutRefused)
{
	FString Clean = Text.TrimStartAndEnd();
	Clean = Clean.TrimQuotes().TrimStartAndEnd();
	TArray<FString> Parts;
	Clean.ParseIntoArray(Parts, TEXT(","), true);
	for (const FString& Part : Parts)
	{
		TArray<FString> Entries;
		Part.ParseIntoArray(Entries, TEXT(";"), true);
		for (FString Entry : Entries)
		{
			Entry.TrimStartAndEndInline();
			if (Entry.IsEmpty())
			{
				continue;
			}
			FString Name, Value;
			if (Entry.Split(TEXT("="), &Name, &Value))
			{
				Name.TrimStartAndEndInline();
				Value.TrimStartAndEndInline();
				if (!Value.IsEmpty() && IsAllowed(Name, Value))
				{
					OutAllowed.Emplace(Name, Value);
					continue;
				}
			}
			OutRefused.Add(Entry.Left(120));
		}
	}
}

// ---- the pacer ------------------------------------------------------------------------------------------------------

struct FMIGpuPacer::FFences
{
	struct FEntry
	{
		uint64 Id = 0;
		FGPUFenceRHIRef Fence;
	};
	FCriticalSection Lock;
	TArray<FEntry> Entries;
};

FMIGpuPacer::FMIGpuPacer() : Fences(MakeShared<FFences, ESPMode::ThreadSafe>()) {}

FMIGpuPacer::~FMIGpuPacer()
{
	Stop();
}

void FMIGpuPacer::Start()
{
	if (bRunning || !FApp::CanEverRender() || !GDynamicRHI)
	{
		return;
	}
	bRunning = true;
	// OnSamplingInput: after the frame cap's sleep and right before the engine reads this frame's input, so the wait
	// costs no frame rate while the GPU keeps up (it has had the whole sleep to finish) and the input the frame is
	// made from is as fresh as it can be when the GPU is the limit.
	BeginHandle = FCoreDelegates::OnSamplingInput.AddRaw(this, &FMIGpuPacer::OnBeginFrame);
	EndHandle = FCoreDelegates::OnEndFrame.AddRaw(this, &FMIGpuPacer::OnEndFrame);
}

void FMIGpuPacer::Stop()
{
	if (bRunning)
	{
		bRunning = false;
		FCoreDelegates::OnSamplingInput.Remove(BeginHandle);
		FCoreDelegates::OnEndFrame.Remove(EndHandle);
	}
}

void FMIGpuPacer::OnEndFrame()
{
	// After everything this frame drew (the scene, Slate, Pixel Streaming's capture copy) and before the engine's own
	// end-of-frame command, which hands the frame's commands to the GPU: the fence is signalled when the GPU has done
	// all of this frame.
	const uint64 Id = ++Enqueued;
	ENQUEUE_RENDER_COMMAND(MIFrameFence)([List = Fences, Id](FRHICommandListImmediate& RHICmdList)
	{
		FFences::FEntry Entry;
		Entry.Id = Id;
		Entry.Fence = RHICreateGPUFence(TEXT("MIFrame"));
		RHICmdList.WriteGPUFence(Entry.Fence);
		FScopeLock Scope(&List->Lock);
		if (List->Entries.Num() > 512)
		{
			List->Entries.RemoveAt(0, 256);  // nobody is reading (the game thread stopped polling): keep it small
		}
		List->Entries.Add(MoveTemp(Entry));
	});
}

int32 FMIGpuPacer::PollCompleted()
{
	FScopeLock Scope(&Fences->Lock);
	int32 Done = 0;
	// In order: the GPU finishes them in the order they were written.
	while (Done < Fences->Entries.Num() && Fences->Entries[Done].Fence.IsValid() && Fences->Entries[Done].Fence->Poll())
	{
		Completed = FMath::Max(Completed, Fences->Entries[Done].Id);
		++Done;
	}
	if (Done > 0)
	{
		Fences->Entries.RemoveAt(0, Done);
		Signalled += (uint64)Done;
	}
	return (int32)(Enqueued - Completed);
}

void FMIGpuPacer::OnBeginFrame()
{
	const uint64 SignalledBefore = Signalled;
	int32 Owed = PollCompleted();
	const int32 OwedAtStart = Owed;
	double Waited = 0.0;
	bool bTimedOut = false;
	if (MaxInFlight >= 0 && Owed > MaxInFlight && FPlatformTime::Seconds() >= PausedUntil)
	{
		// A wait, not work: the engine's game-thread time ("stat unit", the probe line's gameMs) leaves it out.
		UE::Stats::FThreadIdleStats::FScopeIdle Idle;
		const double Start = FPlatformTime::Seconds();
		const double Limit = FMath::Clamp(WaitLimitMs, 1.0, 2000.0) / 1000.0;
		while (Owed > MaxInFlight)
		{
			if (FPlatformTime::Seconds() - Start >= Limit)
			{
				bTimedOut = true;
				// Do not wait for the same frames again at the next start: count from what the GPU owes now.
				Completed = Enqueued > (uint64)MaxInFlight ? Enqueued - MaxInFlight : 0;
				break;
			}
			FPlatformProcess::SleepNoStats(0.0002f);
			Owed = PollCompleted();
		}
		Waited = (FPlatformTime::Seconds() - Start) * 1000.0;
		// Stuck: at the limit, and the GPU has not finished one frame since this frame began to wait. A GPU that is
		// only slow finishes something (the game then stays held: on a time-out it waits for the frames written
		// from now on, which the GPU reaches after it has worked through the pile).
		const bool bStuck = bTimedOut && Signalled == SignalledBefore;
		TimeOutsInARow = bStuck ? TimeOutsInARow + 1 : 0;
		if (TimeOutsInARow >= 3)
		{
			TimeOutsInARow = 0;
			++Pauses;
			PausedUntil = FPlatformTime::Seconds() + PauseSeconds;
		}
	}
	for (FStats& S : Stats)
	{
		++S.Frames;
		S.Held += Waited > 1.0 ? 1 : 0;
		S.TimeOuts += bTimedOut ? 1 : 0;
		S.MaxInFlight = FMath::Max(S.MaxInFlight, OwedAtStart);
		S.WaitMs += Waited;
		S.WorstWaitMs = FMath::Max(S.WorstWaitMs, Waited);
	}
}

FMIGpuPacer::FStats FMIGpuPacer::Take(int32 Reader)
{
	FStats Out = Stats[Reader & 1];
	Stats[Reader & 1] = FStats();
	return Out;
}
