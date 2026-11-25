#include "Cloud/MISession.h"

#if PLATFORM_LINUX
#include <cerrno>
#include <csignal>
#include <cstdio>
#include <sys/types.h>
#endif

// ---- the decision ---------------------------------------------------------------------------------------------------

FMISession::FDecision FMISession::Decide(const FOptions& O, const FState& S)
{
	FDecision D;
	if (!O.bStreamed)
	{
		D.Why = EWhy::NotStreamed;
		return D;
	}
	if (O.bKeepAlive)
	{
		D.Why = EWhy::KeepAlive;
		return D;
	}
	// The launcher that started the game is gone: nobody can stop the game any more. Not asked of the viewers: the
	// launcher's own watchdog ends the game of a launcher that was killed, whoever is watching, and a game with no
	// launcher is not a session E3DS (or anybody) can end.
	if (O.LauncherGoneAfter > 0.0 && S.LauncherGoneFor >= O.LauncherGoneAfter)
	{
		D.Action = EAction::Exit;
		D.Why = EWhy::LauncherGone;
		return D;
	}
	// A viewer present keeps the game for as long as he stays: nothing below can end a live session.
	if (S.Viewers > 0)
	{
		D.Why = EWhy::ViewerPresent;
		return D;
	}
	if (S.bHadViewer)
	{
		if (O.ExitAfterEmpty > 0.0 && S.SecondsSinceChange >= O.ExitAfterEmpty)
		{
			D.Action = EAction::Exit;
			D.Why = EWhy::EmptyTooLong;
			return D;
		}
	}
	else if (O.ExitIfNoViewer > 0.0 && S.SecondsSinceStart >= O.ExitIfNoViewer)
	{
		D.Action = EAction::Exit;
		D.Why = EWhy::NeverConnected;
		return D;
	}
	// Idle: nobody for IdleAfter seconds. Before the first viewer the game gets its first seconds to start up.
	const bool bStartingUp = !S.bHadViewer && S.SecondsSinceReady < O.IdleStartupGrace;
	if (O.IdleFps > 0 && !bStartingUp && S.SecondsSinceChange >= O.IdleAfter)
	{
		D.Action = EAction::Idle;
		D.Why = EWhy::Empty;
		return D;
	}
	D.Why = EWhy::Waiting;
	return D;
}

FString FMISession::Describe(const FDecision& D, const FOptions& O, const FState& S)
{
	switch (D.Why)
	{
	case EWhy::NotStreamed:
		return TEXT("not streamed: no session to look after");
	case EWhy::KeepAlive:
		return TEXT("-MIKeepAlive: the game keeps drawing and never quits by itself");
	case EWhy::ViewerPresent:
		return FString::Printf(TEXT("%d viewer(s) connected"), S.Viewers);
	case EWhy::Waiting:
		return S.bHadViewer
			? FString::Printf(TEXT("no viewer for %.1f s (idles after %.1f s, quits after %.1f s)"), S.SecondsSinceChange, O.IdleAfter, O.ExitAfterEmpty)
			: FString::Printf(TEXT("no viewer yet, %.1f s after the start (quits after %.0f s)"), S.SecondsSinceStart, O.ExitIfNoViewer);
	case EWhy::Empty:
		return S.bHadViewer
			? FString::Printf(TEXT("no viewer for %.1f s: idling at %d frames a second until one joins"), S.SecondsSinceChange, O.IdleFps)
			: FString::Printf(TEXT("no viewer yet, %.1f s after the start: idling at %d frames a second until one joins"), S.SecondsSinceStart, O.IdleFps);
	case EWhy::EmptyTooLong:
		return FString::Printf(TEXT("the last viewer left %.1f s ago (MI.Cloud.ExitAfterEmpty %.1f s) and none has come back: the session is over"), S.SecondsSinceChange, O.ExitAfterEmpty);
	case EWhy::NeverConnected:
		return FString::Printf(TEXT("no viewer connected in the %.0f s since the game started (MI.Cloud.ExitIfNoViewer %.0f s): nobody is coming"), S.SecondsSinceStart, O.ExitIfNoViewer);
	case EWhy::LauncherGone:
		return FString::Printf(TEXT("the launcher that started the game has been gone for %.1f s (-MILauncherPid): nothing can stop this game any more"), S.LauncherGoneFor);
	}
	return FString();
}

FMISession::FOptions FMISession::Sanitize(FOptions O)
{
	// A visitor can put any number on a link (the MI.Cloud. family may be tuned from outside), and a number that is not
	// one must not end a session or freeze the game: a non-finite value, or one under its floor, is the default.
	const auto Seconds = [](double V, double Default, double Min, double Max, bool bZeroOff)
	{
		if (!FMath::IsFinite(V))
		{
			return Default;
		}
		if (bZeroOff && V <= 0.0)
		{
			return 0.0;
		}
		return FMath::Clamp(V, Min, Max);
	};
	O.IdleAfter = Seconds(O.IdleAfter, 2.0, 0.5, 3600.0, false);
	O.IdleStartupGrace = Seconds(O.IdleStartupGrace, 10.0, 0.0, 3600.0, false);
	O.ExitAfterEmpty = Seconds(O.ExitAfterEmpty, 60.0, 2.0, 86400.0, true);
	O.ExitIfNoViewer = Seconds(O.ExitIfNoViewer, 600.0, 5.0, 86400.0, true);
	O.LauncherGoneAfter = Seconds(O.LauncherGoneAfter, 5.0, 2.0, 600.0, true);
	O.IdleFps = FMath::Clamp(O.IdleFps, 0, 30);
	return O;
}

// ---- the launcher ---------------------------------------------------------------------------------------------------

void FMILauncherWatch::Start(int32 InPid, double Now)
{
	Pid = InPid;
	bWatching = InPid > 1;
	bDisarmed = bSeenAlive = false;
	GoneSince = -1.0;
	NextPoll = Now;  // look at once: a launcher that is not there at the game's start is not ours to watch
}

double FMILauncherWatch::Feed(EProbe Answer, double Now)
{
	if (!bWatching)
	{
		return -1.0;
	}
	NextPoll = Now + PollEvery;
	switch (Answer)
	{
	case EProbe::Alive:
		bSeenAlive = true;
		GoneSince = -1.0;
		break;
	case EProbe::Unknown:
		// Cannot tell: the same as alive for the clock (never a reason to quit), but it does not make the id ours either.
		GoneSince = -1.0;
		break;
	case EProbe::Gone:
		if (!bSeenAlive)
		{
			// The launcher passed its own id, which is alive when the game starts: an id that was never seen alive is
			// not that launcher (another process namespace, another /proc). Not watched.
			bWatching = false;
			bDisarmed = true;
			return -1.0;
		}
		if (GoneSince < 0.0)
		{
			GoneSince = Now;
		}
		break;
	}
	return GoneSince >= 0.0 ? Now - GoneSince : -1.0;
}

FMILauncherWatch::EProbe MIProbeProcess(int32 Pid, uint64& InOutStartTime)
{
#if PLATFORM_LINUX
	if (Pid <= 1)
	{
		return FMILauncherWatch::EProbe::Unknown;
	}
	// "Is there such a process": ESRCH says no; success and EPERM (another user's process) say yes. /proc may hide the
	// process of another user (hidepid), kill() does not.
	if (kill((pid_t)Pid, 0) != 0 && errno == ESRCH)
	{
		return FMILauncherWatch::EProbe::Gone;
	}
	// A file of /proc reports a size of 0: it is read with stdio, not with the engine's file reader.
	char Raw[2048];
	size_t Got = 0;
	if (FILE* File = fopen(TCHAR_TO_UTF8(*FString::Printf(TEXT("/proc/%d/stat"), Pid)), "r"))
	{
		Got = fread(Raw, 1, sizeof(Raw) - 1, File);
		fclose(File);
	}
	if (Got == 0)
	{
		return FMILauncherWatch::EProbe::Unknown;  // it exists (kill() said so), /proc will not say more
	}
	Raw[Got] = 0;
	const FString Stat = FString(UTF8_TO_TCHAR(Raw));
	// "pid (comm) S ppid ...": comm may hold spaces and brackets, so everything is counted from the last ')'.
	int32 Close = INDEX_NONE;
	if (!Stat.FindLastChar(TEXT(')'), Close))
	{
		return FMILauncherWatch::EProbe::Unknown;
	}
	TArray<FString> Fields;
	Stat.Mid(Close + 1).TrimStartAndEnd().ParseIntoArray(Fields, TEXT(" "), true);
	if (Fields.Num() < 20)
	{
		return FMILauncherWatch::EProbe::Unknown;
	}
	// Fields[0] is the state (field 3 of the file), Fields[19] the start time in ticks since boot (field 22).
	const TCHAR State = Fields[0].Len() > 0 ? Fields[0][0] : TEXT('?');
	if (State == TEXT('Z') || State == TEXT('X') || State == TEXT('x'))
	{
		return FMILauncherWatch::EProbe::Gone;  // killed, and nobody has collected it yet
	}
	const uint64 Start = FCString::Strtoui64(*Fields[19], nullptr, 10);
	if (InOutStartTime == 0)
	{
		InOutStartTime = Start;
	}
	else if (Start != 0 && Start != InOutStartTime)
	{
		return FMILauncherWatch::EProbe::Gone;  // the id belongs to another process now
	}
	return FMILauncherWatch::EProbe::Alive;
#else
	return FMILauncherWatch::EProbe::Unknown;
#endif
}
