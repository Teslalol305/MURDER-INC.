#include "Flow/MIFrontEndRules.h"

namespace MIFrontEndPrivate
{
	const TCHAR* Up = TEXT("▲");
	const TCHAR* Down = TEXT("▼");
	const TCHAR* Dot = TEXT("•");
	const TCHAR* Minus = TEXT("−");
}

void FMIFrontEndRules::Init(const FMILoadoutData* InData, const FMIReadiness& InReady, const FMILoadoutResolver* InResolver, const FMIRunSetup& Saved)
{
	Data = InData;
	Ready = InReady;
	Ready.Data = InData;
	Resolver = InResolver;
	Setup = Saved;
	Ready.Validate(Setup);
	Screen = EMIFrontScreen::Home;
	bEdit = false;
	SelectedSlot = INDEX_NONE;
	FocusedGun = Setup.Guns.Num() > 0 ? Setup.Guns[0] : NAME_None;
	BenchGun = NAME_None;
}

int32 FMIFrontEndRules::StepOf(EMIFrontScreen S)
{
	switch (S)
	{
	case EMIFrontScreen::Crew: return 1;
	case EMIFrontScreen::Loadout:
	case EMIFrontScreen::Workbench: return 2;
	case EMIFrontScreen::Where: return 3;
	case EMIFrontScreen::Briefing: return 4;
	default: return 0;
	}
}

FString FMIFrontEndRules::ScreenName(EMIFrontScreen S)
{
	static const TCHAR* Names[] = {TEXT("home"), TEXT("crew"), TEXT("loadout"), TEXT("workbench"), TEXT("where"), TEXT("briefing")};
	return Names[static_cast<int32>(S)];
}

bool FMIFrontEndRules::ParseScreen(const FString& Name, EMIFrontScreen& Out)
{
	for (int32 I = 0; I <= static_cast<int32>(EMIFrontScreen::Briefing); ++I)
	{
		if (Name.Equals(ScreenName(static_cast<EMIFrontScreen>(I)), ESearchCase::IgnoreCase))
		{
			Out = static_cast<EMIFrontScreen>(I);
			return true;
		}
	}
	return false;
}

bool FMIFrontEndRules::IsValid() const
{
	if (Setup.Guns.Num() < Data->CarryMin || Setup.Guns.Num() > Data->CarryMax)
	{
		return false;
	}
	for (const FName G : Setup.Guns)
	{
		const FMIGunEntry* Gun = Data->FindGun(G);
		if (!Gun) return false;
		for (const FMICompatSlot& C : Gun->Compat)
		{
			// A required slot with no entry is on its default (the build is filled when saved).
			if (C.bRequired && Setup.PartIn(G, C.Slot).IsNone() && C.Default.IsNone() && Ready.OfferedParts(G, C.Slot).Num() > 0) return false;
		}
	}
	return true;
}

FString FMIFrontEndRules::NextBlocked() const
{
	if (Screen == EMIFrontScreen::Loadout && Setup.Guns.Num() == 0)
	{
		return Text(TEXT("frontend.loadout.needOne"));
	}
	return FString();
}

bool FMIFrontEndRules::IsStepReachable(int32 Step) const
{
	return Step <= StepOf(Screen) || IsValid();
}

void FMIFrontEndRules::Go(EMIFrontScreen S)
{
	Screen = S;
	bPreview = false;
	ResetHeld = 0.0;
	LastMessage.Reset();
	if (S == EMIFrontScreen::Loadout && FocusedGun.IsNone() && Setup.Guns.Num() > 0)
	{
		FocusedGun = Setup.Guns[0];
	}
}

EMIFrontRequest FMIFrontEndRules::HitTheBlock()
{
	if (Screen == EMIFrontScreen::Home && !Setup.bPlayed)
	{
		bEdit = false;
		Go(EMIFrontScreen::Crew);  // every player walks the flow once
		return EMIFrontRequest::None;
	}
	if (!IsValid())
	{
		return EMIFrontRequest::None;
	}
	Setup.bPlayed = true;
	bRemember = true;
	return EMIFrontRequest::StartRun;
}

void FMIFrontEndRules::GearUp()
{
	bEdit = false;
	Go(EMIFrontScreen::Crew);
}

void FMIFrontEndRules::Edit(EMIFrontScreen S)
{
	bEdit = S != EMIFrontScreen::Briefing && S != EMIFrontScreen::Home;
	Go(S);
}

EMIFrontRequest FMIFrontEndRules::Next()
{
	switch (Screen)
	{
	case EMIFrontScreen::Home:
		return HitTheBlock();
	case EMIFrontScreen::Crew:
		bRemember = true;
		Go(bEdit ? EMIFrontScreen::Briefing : EMIFrontScreen::Loadout);
		break;
	case EMIFrontScreen::Loadout:
		if (!NextBlocked().IsEmpty())
		{
			LastMessage = NextBlocked();
			return EMIFrontRequest::None;
		}
		bRemember = true;
		Go(bEdit ? EMIFrontScreen::Briefing : EMIFrontScreen::Where);
		break;
	case EMIFrontScreen::Workbench:
		bRemember = true;  // Done
		Go(EMIFrontScreen::Loadout);
		return EMIFrontRequest::None;
	case EMIFrontScreen::Where:
		bRemember = true;
		Go(EMIFrontScreen::Briefing);
		break;
	case EMIFrontScreen::Briefing:
		if (!IsValid())
		{
			return EMIFrontRequest::None;
		}
		Setup.bPlayed = true;
		bRemember = true;
		return EMIFrontRequest::StartRun;
	}
	if (Screen == EMIFrontScreen::Briefing)
	{
		bEdit = false;
	}
	return EMIFrontRequest::None;
}

void FMIFrontEndRules::Back()
{
	if (bEdit && Screen != EMIFrontScreen::Workbench)
	{
		bEdit = false;
		Go(EMIFrontScreen::Briefing);
		return;
	}
	switch (Screen)
	{
	case EMIFrontScreen::Crew: Go(EMIFrontScreen::Home); break;
	case EMIFrontScreen::Loadout: Go(EMIFrontScreen::Crew); break;
	case EMIFrontScreen::Workbench: bRemember = true; Go(EMIFrontScreen::Loadout); break;
	case EMIFrontScreen::Where: Go(EMIFrontScreen::Loadout); break;
	case EMIFrontScreen::Briefing: Go(EMIFrontScreen::Where); break;
	default: break;
	}
}

bool FMIFrontEndRules::ToBriefing()
{
	if (Screen == EMIFrontScreen::Home || !IsValid())
	{
		return false;
	}
	bRemember = true;
	bEdit = false;
	Go(EMIFrontScreen::Briefing);
	return true;
}

bool FMIFrontEndRules::GoToStep(int32 Step)
{
	if (!IsStepReachable(Step))
	{
		return false;
	}
	static const EMIFrontScreen Steps[] = {EMIFrontScreen::Home, EMIFrontScreen::Crew, EMIFrontScreen::Loadout, EMIFrontScreen::Where, EMIFrontScreen::Briefing};
	Go(Steps[FMath::Clamp(Step, 0, 4)]);
	return true;
}

void FMIFrontEndRules::OpenBriefing()
{
	bEdit = false;
	Go(EMIFrontScreen::Briefing);
}

void FMIFrontEndRules::OpenHome()
{
	bEdit = false;
	Go(EMIFrontScreen::Home);
}

// ------------------------------------------------------------------------------------------------- Crew

TArray<FName> FMIFrontEndRules::OfferedCrew() const
{
	TArray<FName> Out;
	for (const FName C : Data->CrewOrder)
	{
		if (Ready.IsCrewOffered(C)) Out.Add(C);
	}
	return Out;
}

void FMIFrontEndRules::ChooseCrew(FName Crew)
{
	if (Ready.IsCrewOffered(Crew))
	{
		Setup.Crew = Crew;
		Seen(Crew);
	}
}

FString FMIFrontEndRules::CrewTagline(FName Crew) const
{
	const FMICrewEntry* C = Data->FindCrew(Crew);
	if (!C) return FString();
	const FString Full = Text(C->TextKey + TEXT(".taglineFull"));
	return Ready.HasLater(Crew) && !Full.IsEmpty() ? Full : Text(C->TextKey + TEXT(".tagline"));
}

// ------------------------------------------------------------------------------------------------- Loadout

TArray<FName> FMIFrontEndRules::Rack(FName Filter) const
{
	TArray<FName> Out;
	for (const FName G : Data->Roster)
	{
		if (!Ready.IsGunOffered(G)) continue;
		const FMIGunEntry* Gun = Data->FindGun(G);
		if (Filter == TEXT("all") || Filter.IsNone() || (Filter == TEXT("new") && IsNew(G)) || Gun->Class == Filter) Out.Add(G);
	}
	return Out;
}

bool FMIFrontEndRules::Carry(FName Gun)
{
	LastMessage.Reset();
	if (!Ready.IsGunOffered(Gun))
	{
		return false;
	}
	Seen(Gun);
	FocusedGun = Gun;
	const int32 Have = SlotOf(Gun);
	if (Have != INDEX_NONE)
	{
		SelectedSlot = Have;  // a carried gun stays selectable: selecting it focuses its slot
		return true;
	}
	if (Setup.Guns.Num() < Data->CarryMax)
	{
		Setup.Guns.Add(Gun);
		return true;
	}
	if (Setup.Guns.IsValidIndex(SelectedSlot))
	{
		Setup.Guns[SelectedSlot] = Gun;
		return true;
	}
	LastMessage = Text(TEXT("frontend.loadout.full"));  // a fifth carry asks for a slot
	return false;
}

bool FMIFrontEndRules::PutInSlot(FName Gun, int32 Slot)
{
	if (!Ready.IsGunOffered(Gun) || Slot < 0 || Slot >= Data->CarryMax)
	{
		return false;
	}
	Seen(Gun);
	const int32 Have = SlotOf(Gun);
	if (Have != INDEX_NONE)
	{
		SwapSlots(Have, FMath::Min(Slot, Setup.Guns.Num() - 1));
		return true;
	}
	if (Slot >= Setup.Guns.Num())
	{
		Setup.Guns.Add(Gun);  // contiguous: an empty slot past the end fills the next free one
	}
	else
	{
		Setup.Guns[Slot] = Gun;
	}
	return true;
}

void FMIFrontEndRules::SwapSlots(int32 A, int32 B)
{
	if (Setup.Guns.IsValidIndex(A) && Setup.Guns.IsValidIndex(B) && A != B)
	{
		Setup.Guns.Swap(A, B);
		SelectedSlot = B;
	}
}

void FMIFrontEndRules::EmptySlot(int32 Slot)
{
	if (Setup.Guns.IsValidIndex(Slot))
	{
		Setup.Guns.RemoveAt(Slot);  // the rest close up
		SelectedSlot = INDEX_NONE;
	}
}

void FMIFrontEndRules::FocusGun(FName Gun)
{
	FocusedGun = Gun;
	Seen(Gun);
}

void FMIFrontEndRules::OpenWorkbench(FName Gun)
{
	if (!Data->FindGun(Gun))
	{
		return;
	}
	BenchGun = Gun;
	const TArray<FName> Slots = BenchSlots();
	BenchSlot = Slots.Num() > 0 ? Slots[0] : NAME_None;
	Go(EMIFrontScreen::Workbench);
}

// ------------------------------------------------------------------------------------------------- Workbench

FMIGunBuild& FMIFrontEndRules::BuildOf(FName Gun)
{
	FMIGunBuild* B = Setup.Builds.Find(Gun);
	if (!B)
	{
		B = &Setup.Builds.Add(Gun, Ready.DefaultBuild(Gun));
	}
	return *B;
}

void FMIFrontEndRules::ChooseBenchSlot(FName Slot)
{
	if (BenchSlots().Contains(Slot))
	{
		BenchSlot = Slot;
		bPreview = false;
	}
}

TArray<FName> FMIFrontEndRules::BenchOptions(FName Slot) const
{
	TArray<FName> Out;
	const FMIGunEntry* G = Data->FindGun(BenchGun);
	const FMICompatSlot* C = G ? G->FindCompat(Slot) : nullptr;
	if (!C)
	{
		return Out;
	}
	if (!C->bRequired)
	{
		Out.Add(NAME_None);  // Factory: what it came with
	}
	Out.Append(Ready.OfferedParts(BenchGun, Slot));
	return Out;
}

FName FMIFrontEndRules::FittedIn(FName Slot) const
{
	const FName P = Setup.PartIn(BenchGun, Slot);
	if (!P.IsNone()) return P;
	const FMIGunEntry* G = Data->FindGun(BenchGun);
	const FMICompatSlot* C = G ? G->FindCompat(Slot) : nullptr;
	return C && C->bRequired ? C->Default : NAME_None;
}

void FMIFrontEndRules::Fit(FName Part)
{
	if (BenchSlot.IsNone() || !BenchOptions(BenchSlot).Contains(Part))
	{
		return;
	}
	FMIGunBuild& B = BuildOf(BenchGun);
	if (Part.IsNone())
	{
		B.Parts.Remove(BenchSlot);
	}
	else
	{
		B.Parts.Add(BenchSlot, Part);
		Seen(Part);
	}
	bPreview = false;
}

void FMIFrontEndRules::FitFactory()
{
	const FMIGunEntry* G = Data->FindGun(BenchGun);
	const FMICompatSlot* C = G ? G->FindCompat(BenchSlot) : nullptr;
	if (C && !C->bRequired)
	{
		Fit(NAME_None);
	}
}

FMIGunBuild FMIFrontEndRules::ShownBuild() const
{
	const FMIGunBuild* Have = Setup.BuildOf(BenchGun);
	FMIGunBuild B = Have ? *Have : Ready.DefaultBuild(BenchGun);
	if (bPreview && !BenchSlot.IsNone())
	{
		if (Previewed.IsNone()) B.Parts.Remove(BenchSlot);
		else B.Parts.Add(BenchSlot, Previewed);
	}
	return B;
}

bool FMIFrontEndRules::HoldReset(double Dt, bool bHeld)
{
	if (!bHeld)
	{
		ResetHeld = 0.0;  // a tap does nothing: no action that loses work is on a tap
		return false;
	}
	ResetHeld += Dt;
	if (ResetHeld + 1e-9 >= Data->ResetHold)
	{
		ResetHeld = 0.0;
		Setup.Builds.Add(BenchGun, Ready.DefaultBuild(BenchGun));  // every slot back to its default
		bPreview = false;
		return true;
	}
	return false;
}

void FMIFrontEndRules::BenchNextGun(int32 Dir)
{
	if (Setup.Guns.Num() == 0 || Dir == 0)
	{
		return;
	}
	const int32 At = Setup.Guns.IndexOfByKey(BenchGun);
	const int32 N = Setup.Guns.Num();
	const int32 Next = At == INDEX_NONE ? 0 : ((At + Dir) % N + N) % N;
	OpenWorkbench(Setup.Guns[Next]);
}

TArray<FMIEffectLine> FMIFrontEndRules::EffectLines(FName Gun, FName PartId) const
{
	using namespace MIFrontEndPrivate;
	TArray<FMIEffectLine> Out;
	const FMIAttachmentDef* Part = Data->FindPart(PartId);
	if (!Part || !Resolver)
	{
		return Out;
	}
	const FMIGunBuild* Have = Setup.BuildOf(Gun);
	FMIGunBuild Without = Have ? *Have : Ready.DefaultBuild(Gun);
	Without.Parts.Remove(Part->Slot);
	FMIGunBuild With = Without;
	With.Parts.Add(Part->Slot, PartId);
	FMIResolvedGun A, B;
	FString Error;
	if (!Resolver->ResolveGun(Gun, &Without, &Ready, A, Error) || !Resolver->ResolveGun(Gun, &With, &Ready, B, Error))
	{
		return Out;
	}
	const auto Doc = [](const FMIResolvedGun& G)
	{
		TSharedPtr<FJsonObject> D = MakeShared<FJsonObject>();
		D->SetObjectField(TEXT("rules"), G.Rules);
		D->SetObjectField(TEXT("extra"), G.Extra);
		return D;
	};
	const TSharedPtr<FJsonObject> DA = Doc(A), DB = Doc(B);
	const auto Round = [](double V) { return FString::FromInt(FMath::RoundToInt32(V)); };
	for (const FMIEffect& E : Part->Effects)
	{
		const FMIStatDef* S = Data->Stats.Find(E.Stat);
		if (!S || S->Text.IsEmpty() || S->Targets.Num() == 0) continue;
		FString Path = S->Targets[0].Path;
		if (Path.EndsWith(TEXT(".*"))) Path = Path.LeftChop(2) + TEXT(".tactical");
		double Old = 0.0, New = 0.0;
		if (!MIJson::Number(MIJson::Get(DA, Path), Old) || !MIJson::Number(MIJson::Get(DB, Path), New) || Old == New) continue;
		const bool bLowerBetter = S->Better == TEXT("lower");
		const bool bHigherBetter = S->Better == TEXT("higher");
		const int32 Sign = bLowerBetter ? (New < Old ? 1 : -1) : bHigherBetter ? (New > Old ? 1 : -1) : 0;
		TMap<FString, FString> Args;
		Args.Add(TEXT("mark"), Sign > 0 ? Up : Sign < 0 ? Down : Dot);
		FString Key = S->Text;
		if (E.Stat == TEXT("adsFov") || E.Stat == TEXT("noise"))
		{
			Args.Add(TEXT("value"), Round(New));
			Args.Add(TEXT("base"), Round(Old));
		}
		else if (E.Stat == TEXT("falloff.start"))
		{
			Args.Add(TEXT("value"), Round(New));
		}
		else if (E.Stat == TEXT("falloff.min"))
		{
			Args.Add(TEXT("value"), Round(New * 100.0));
		}
		else
		{
			const double Pct = (New / Old - 1.0) * 100.0;
			Args.Add(TEXT("sign"), Pct > 0.0 ? TEXT("+") : Minus);
			Args.Add(TEXT("pct"), Round(FMath::Abs(Pct)));
			if (E.Stat == TEXT("length") && New < Old && !S->TextShorter.IsEmpty()) Key = S->TextShorter;
		}
		Out.Add({Data->Format(Key, Args), Sign});
	}
	return Out;
}

double FMIFrontEndRules::GoonHp(FName Difficulty) const
{
	return MIJson::NumberOr(ConfigJson, FString::Printf(TEXT("enemies.difficulty.%s.goon.hp"), *Difficulty.ToString()), 110.0);
}

FMIGunBars FMIFrontEndRules::Bars(FName Gun, const FMIGunBuild* Build) const
{
	FMIResolvedGun G;
	FString Error;
	if (!Resolver || !Resolver->ResolveGun(Gun, Build, &Ready, G, Error))
	{
		return FMIGunBars();
	}
	return FMIGunBars::Of(G, GoonHp(Setup.Difficulty.IsNone() ? FName(TEXT("boss")) : Setup.Difficulty));
}

// ------------------------------------------------------------------------------------------------- Block & Style

bool FMIFrontEndRules::IsLevelOpen(FName Level) const
{
	return !Progress || bUnlockAll || Progress->IsOpen(Level, Data->LevelOrder);
}

FName FMIFrontEndRules::LevelBefore(FName Level) const
{
	const int32 I = Data->LevelOrder.IndexOfByKey(Level);
	return I > 0 ? Data->LevelOrder[I - 1] : NAME_None;
}

FString FMIFrontEndRules::RatingName(int32 Points) const
{
	const TSharedPtr<FJsonValue> V = MIJson::Get(TextJson, TEXT("text.ratings"));
	if (V.IsValid() && V->Type == EJson::Array && V->AsArray().IsValidIndex(Points))
	{
		return V->AsArray()[Points]->AsString();
	}
	return FString::FromInt(Points);
}

FString FMIFrontEndRules::LevelState(FName Level) const
{
	if (!Progress)
	{
		return FString();
	}
	if (!IsLevelOpen(Level))
	{
		const FName Before = LevelBefore(Level);
		return Text(TEXT("frontend.level.locked")) + TEXT(" \u00b7 ") + Data->Format(TEXT("frontend.level.lockedHint"), {{TEXT("level"), Text(FString::Printf(TEXT("frontend.levels.%s.name"), *Before.ToString()))}});
	}
	const FMILevelRecord* R = Progress->Levels.Find(Level);
	if (R && R->bCleared)
	{
		return Data->Format(TEXT("frontend.level.cleared"), {{TEXT("rating"), RatingName(R->BestPoints)},
			{TEXT("difficulty"), Text(TEXT("text.difficulties.") + R->BestDifficulty.ToString())}});
	}
	return Text(TEXT("frontend.level.notCleared"));
}

void FMIFrontEndRules::SetLevel(FName Level)
{
	if (Data->Levels.Contains(Level) && IsLevelOpen(Level))
	{
		Setup.Level = Level;
		Seen(Level);
		const TArray<FName> M = Modes();
		if (M.Num() > 0 && !M.Contains(Setup.Mode)) Setup.Mode = M[0];
	}
}

void FMIFrontEndRules::SetMode(FName Mode)
{
	if (Modes().Contains(Mode))
	{
		Setup.Mode = Mode;
	}
}

// ------------------------------------------------------------------------------------------------- text

FString FMIFrontEndRules::Text(const FString& Key) const
{
	if (Key.StartsWith(TEXT("frontend.")))
	{
		return Data->Text(Key);
	}
	if (Key.StartsWith(TEXT("text.")) && TextJson.IsValid())
	{
		FString S = MIJson::StringOr(TextJson, Key);
		if (S.IsEmpty() && Key.StartsWith(TEXT("text.interface.")))
		{
			S = MIJson::StringOr(TextJson, Key.Mid(5));
		}
		return S;
	}
	return FString();
}

FString FMIFrontEndRules::GunName(FName Gun) const
{
	const FMIGunEntry* G = Data->FindGun(Gun);
	const FString Name = G ? Text(G->TextKey + TEXT(".name")) : FString();
	return Name.IsEmpty() ? Gun.ToString().ToUpper() : Name;
}

FString FMIFrontEndRules::PartName(FName Part) const
{
	if (Part.IsNone()) return Text(TEXT("frontend.attachments.factory"));
	const FMIAttachmentDef* P = Data->FindPart(Part);
	return P ? Text(P->Text + TEXT(".name")) : Part.ToString();
}

FString FMIFrontEndRules::CrewName(FName Crew) const
{
	const FMICrewEntry* C = Data->FindCrew(Crew);
	return C ? Text(C->TextKey + TEXT(".name")) : Crew.ToString().ToUpper();
}

FString FMIFrontEndRules::Summary() const
{
	TArray<FString> Guns;
	for (const FName G : Setup.Guns) Guns.Add(GunName(G));
	const FMILevelEntry* L = Data->Levels.Find(Setup.Level);
	TMap<FString, FString> Args;
	Args.Add(TEXT("crew"), CrewName(Setup.Crew));
	Args.Add(TEXT("guns"), FString::Join(Guns, TEXT(" / ")));
	Args.Add(TEXT("level"), L ? Text(L->TextKey + TEXT(".name")) : Setup.Level.ToString());
	Args.Add(TEXT("time"), Text(TEXT("frontend.level.times.") + Setup.Time.ToString()));
	Args.Add(TEXT("mode"), Text(TEXT("text.modes.") + Setup.Mode.ToString() + TEXT(".name")));
	Args.Add(TEXT("difficulty"), Text(TEXT("text.difficulties.") + Setup.Difficulty.ToString()));
	return Data->Format(TEXT("frontend.home.summary"), Args);
}
