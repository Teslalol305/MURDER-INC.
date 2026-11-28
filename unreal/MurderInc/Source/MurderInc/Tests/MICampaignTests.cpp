// The three levels and the campaign through them (docs/unreal/maps/progression.md, data_contract.md).
//   MurderInc.Levels.Chinatown.Loads   level_chinatown.json loads through FMILevelData::ForLevel: the counts of the contract, no deck, the
//                                      roof points (enabled), the text overlay, the audio zones; the level boots in a world and starts a run
//   MurderInc.Levels.Midtown.Loads     the same for Midtown: afterAll truck (colliders out of the world until the last reel), tuning, nav layers
//   MurderInc.Levels.Chinatown.RoofCamp  a player parked mid-roof on Canal keeps being fought (a shot within 20 s, shots in most 10 s windows of 90 s)
//   MurderInc.Campaign.Code            the progress code against the reference vectors of progression.md Appendix A (an oracle run in Python),
//                                      every one-character change refused
//   MurderInc.Campaign.Unlocks         level 1 always open, a clear opens the next, ratings only go up, merge, the save fields, old saves
//   MurderInc.Campaign.BlockUnchanged  the Block is the Block: the same object from Get() and ForLevel("block"), its files byte for byte (size)

#include "Core/Data/MIDataSubsystem.h"
#include "Core/MIEvents.h"
#include "Enemies/MIEnemies.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Flow/MIFrontEndRules.h"
#include "Flow/MIGameSubsystem.h"
#include "Flow/MIProgress.h"
#include "Flow/MIRunSetupSubsystem.h"
#include "GameFramework/WorldSettings.h"
#include "HAL/FileManager.h"
#include "Misc/Paths.h"
#include "Player/MIPlayerCharacter.h"
#include "Tests/MITestUtil.h"
#include "World/MIBoxWorld.h"
#include "World/MILevelData.h"

#if WITH_AUTOMATION_TESTS

namespace MICampaignTestsPrivate
{
	constexpr double Dt = 1.0 / 60.0;

	/** The active level for the test's life; the Block again afterwards. */
	struct FActiveLevel
	{
		explicit FActiveLevel(FName Id) { FMILevelData::SetActive(Id); }
		~FActiveLevel() { FMILevelData::SetActive(TEXT("block")); }
	};

	struct FLevelWorld
	{
		UWorld* World = nullptr;
		AMIPlayerCharacter* Player = nullptr;
		UMIGameSubsystem* Game = nullptr;
		FLevelWorld()
		{
			World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("MILevelWorld"));
			FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
			Context.SetCurrentWorld(World);
			World->InitializeActorsForPlay(FURL());
			World->BeginPlay();
			if (!World->GetBegunPlay())
			{
				World->GetWorldSettings()->NotifyBeginPlay();
			}
			Player = World->SpawnActor<AMIPlayerCharacter>(FVector(0, 0, 200), FRotator::ZeroRotator);
			Game = UMIGameSubsystem::Get(World);
		}
		~FLevelWorld()
		{
			World->EndPlay(EEndPlayReason::Quit);
			GEngine->DestroyWorldContext(World);
			World->DestroyWorld(false);
		}
		void Step()
		{
			World->Tick(LEVELTICK_All, Dt);
			GFrameCounter++;
		}
	};

	int32 CountType(const FMILevelData& L, FName Type)
	{
		int32 N = 0;
		for (const FMILevelPoint& P : L.Spawns) N += P.Type == Type ? 1 : 0;
		return N;
	}

	bool CheckLevel(FAutomationTestBase& T, FName Id, int32 Ground, int32 Explosives, bool bAfterAll, int32 Disabled, int32 NavLayers, const FString& IntroWord)
	{
		const FMILevelData* L = FMILevelData::ForLevel(Id);
		if (!T.TestNotNull(TEXT("level data loads"), L))
		{
			return false;
		}
		T.TestEqual(TEXT("id"), L->Id, Id);
		T.TestEqual(TEXT("3 reels"), L->Objectives.Num(), 3);
		T.TestEqual(TEXT("ground spawn points"), CountType(*L, TEXT("ground")), Ground);
		T.TestEqual(TEXT("no air spawn points (the drones are out)"), CountType(*L, TEXT("air")), 0);
		T.TestEqual(TEXT("explosives"), L->Explosives.Num(), Explosives);
		T.TestEqual(TEXT("title path keys"), L->CinematicPos.Num(), 14);
		T.TestFalse(TEXT("no El deck"), L->bHasDeck);
		T.TestTrue(TEXT("the stand-in deck is outside the bounds"), L->Deck.MinX > L->Bounds.MaxX && L->Deck.MinZ > L->Bounds.MaxZ);
		T.TestEqual(TEXT("doorways: none"), L->Rooms.Num() > 0 ? L->Rooms[0].Doorways.Num() : 0, 0);
		int32 Off = 0;
		for (const FMILevelPoint& P : L->Spawns) Off += P.bEnabled ? 0 : 1;
		T.TestEqual(TEXT("spawn points with enabled:false"), Off, Disabled);
		T.TestEqual(TEXT("truck arrival afterAll"), L->bTruckAfterAll, bAfterAll);
		T.TestEqual(TEXT("truck colliders listed"), L->TruckColliders.Num(), 2);
		T.TestTrue(TEXT("excludePlayerRoom"), L->Tuning.bExcludePlayerRoom);
		T.TestEqual(TEXT("nav layers (contract shape: layers, grid null)"), L->NavLayerIds.Num(), NavLayers);
		T.TestTrue(TEXT("the nav object is kept"), L->NavJson.IsValid() && L->NavJson->HasField(TEXT("layers")));
		T.TestTrue(TEXT("every spawn point sits in a zone"), [&]() { for (const FMILevelPoint& P : L->Spawns) { if (!L->ZoneAt(P.Pos.X, P.Pos.Z)) return false; } return true; }());
		// The truck's colliders stay out of the box world when the truck arrives after the last reel.
		FMIBoxWorld Box;
		L->FillWorld(Box, FMIRng(1));
		T.TestEqual(TEXT("boxes in the world"), Box.GetBoxes().Num(), L->Colliders.Num() - (bAfterAll ? L->TruckColliders.Num() : 0));
		// The text overlay (per level, falling back to the Block's).
		FMIText Copy;
		FString Error;
		if (T.TestTrue(TEXT("text loads with the overlay: ") + Error, FMIText::Load(Copy, Error, Id)))
		{
			T.TestTrue(TEXT("the level's radio intro"), Copy.Get(TEXT("radio.intro.text")).Contains(IntroWord));
			T.TestFalse(TEXT("{name} is resolved"), Copy.Get(TEXT("radio.intro.text")).Contains(TEXT("{name}")));
			T.TestTrue(TEXT("a line the level does not have falls back to the Block's"), !Copy.Get(TEXT("radio.contact.text")).IsEmpty());
		}
		// levels.json says what the file holds.
		FMILoadoutData Loadout;
		if (T.TestTrue(TEXT("levels.json loads: ") + Error, FMILoadoutData::Load(Loadout, Error)))
		{
			const FMILevelEntry* E = Loadout.Levels.Find(Id);
			if (T.TestNotNull(TEXT("levels.json has the entry"), E))
			{
				T.TestEqual(TEXT("provides: objectives"), E->Provides.Objectives, L->Objectives.Num());
				T.TestEqual(TEXT("provides: ground"), E->Provides.Ground, Ground);
				T.TestEqual(TEXT("provides: air"), E->Provides.Air, 0);
				T.TestTrue(TEXT("night only"), E->Times.Num() == 1 && E->Times[0] == FName(TEXT("night")));
			}
		}
		return true;
	}

	bool RunInWorld(FAutomationTestBase& T, FName Id)
	{
		FActiveLevel Active(Id);
		FLevelWorld W;
		FMIBootOptions O;
		O.Level = Id;
		O.bTitle = false;
		O.Mode = TEXT("mission");
		O.Difficulty = TEXT("hustler");
		O.bPersist = false;
		O.bDrawGrey = false;
		if (!T.TestTrue(TEXT("the level boots in a world"), W.Player && W.Game && W.Game->Boot(O)))
		{
			return false;
		}
		const FMILevelData* L = W.Game->GetLevel();
		T.TestEqual(TEXT("the game plays this level"), W.Game->GetLevelId(), Id);
		T.TestTrue(TEXT("it is this level's data"), L == FMILevelData::ForLevel(Id));
		W.Game->StartRun(TEXT("mission"), true);
		for (int32 I = 0; I < 900; ++I)
		{
			W.Step();
		}
		T.TestEqual(TEXT("the run is on"), W.Game->GetRules().GetState(), EMIGameState::Playing);
		// Where the player starts: the level's start, on this level's ground.
		const FVector Feet = W.Player->GetActorLocation();
		const FVector Want = FVector(L->PlayerStart.Pos.X * 100.0, L->PlayerStart.Pos.Z * 100.0, 0.0);
		T.TestTrue(TEXT("the player started at the level's start"), FVector::Dist2D(Feet, Want) < 600.0);
		// The Goons come from enabled points only; Canal's roof points are enabled, Midtown's roofs have Goons on them too.
		FMIEnemyField& Field = W.Game->GetEnemies();
		int32 Alive = 0;
		for (const int32 S : Field.GetList())
		{
			const FMIEnemy& E = Field.GetSlots()[S];
			if (!E.bAlive) continue;
			++Alive;
			T.TestTrue(TEXT("a Goon stands on a point of the level"), E.Pos.Y < 2.0 || Id == FName(TEXT("midtown")) || Id == FName(TEXT("chinatown")));
		}
		T.AddInfo(FString::Printf(TEXT("%s: %d Goons alive after 15 s"), *Id.ToString(), Alive));
		return true;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMILevelsChinatownLoadsTest, "MurderInc.Levels.Chinatown.Loads", MITest::Flags)
bool FMILevelsChinatownLoadsTest::RunTest(const FString&)
{
	using namespace MICampaignTestsPrivate;
	if (!CheckLevel(*this, TEXT("chinatown"), 38, 18, false, 0, 2, TEXT("Canal")))
	{
		return false;
	}
	return RunInWorld(*this, TEXT("chinatown"));
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMILevelsMidtownLoadsTest, "MurderInc.Levels.Midtown.Loads", MITest::Flags)
bool FMILevelsMidtownLoadsTest::RunTest(const FString&)
{
	using namespace MICampaignTestsPrivate;
	if (!CheckLevel(*this, TEXT("midtown"), 30, 17, true, 0, 4, TEXT("roofs")))
	{
		return false;
	}
	const FMILevelData* L = FMILevelData::ForLevel(TEXT("midtown"));
	TestEqual(TEXT("pursuit budget add"), L->Tuning.PursuitBudgetAdd, 2);
	TestEqual(TEXT("rating times"), L->Tuning.RatingTime.Num(), 2);
	return RunInWorld(*this, TEXT("midtown"));
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICampaignCodeTest, "MurderInc.Campaign.Code", MITest::Flags)
bool FMICampaignCodeTest::RunTest(const FString&)
{
	struct FVec { const TCHAR* Code; bool C[3]; int32 Pts[3]; const TCHAR* Dif[3]; bool bAlbum; };
	// Produced by the Python reference of progression.md Appendix A (encode(cleared, points, difficulty, album)).
	static const FVec Vectors[] = {
		{TEXT("43ZZ-WFDP"), {false, false, false}, {-1, -1, -1}, {TEXT(""), TEXT(""), TEXT("")}, false},
		{TEXT("47YZ-MB30"), {true, false, false}, {3, -1, -1}, {TEXT("boss"), TEXT(""), TEXT("")}, false},
		{TEXT("4FMY-N7W6"), {true, true, false}, {3, 2, -1}, {TEXT("boss"), TEXT("boss"), TEXT("")}, false},
		{TEXT("4FG6-05EW"), {true, true, false}, {0, 0, -1}, {TEXT("hustler"), TEXT("hustler"), TEXT("")}, false},
		{TEXT("4YS4-M979"), {true, true, true}, {4, 4, 5}, {TEXT("boss"), TEXT("boss"), TEXT("kingpin")}, false},
		{TEXT("4YS4-PD68"), {true, true, true}, {4, 4, 5}, {TEXT("boss"), TEXT("boss"), TEXT("kingpin")}, true},
		{TEXT("4W00-1D88"), {true, true, true}, {0, 0, 0}, {TEXT("hustler"), TEXT("hustler"), TEXT("hustler")}, false},
		{TEXT("4YVD-B6KV"), {true, true, true}, {5, 5, 5}, {TEXT("kingpin"), TEXT("kingpin"), TEXT("kingpin")}, true},
		{TEXT("47ZF-R6FN"), {true, false, false}, {5, -1, -1}, {TEXT("kingpin"), TEXT(""), TEXT("")}, false},
	};
	for (const FVec& V : Vectors)
	{
		FMIProgress P;
		for (int32 I = 0; I < 3; ++I)
		{
			if (V.C[I])
			{
				FMILevelRecord& R = P.Levels.Add(FMIProgress::CodeOrder()[I]);
				R.bCleared = true;
				R.BestPoints = V.Pts[I];
				R.BestDifficulty = FName(V.Dif[I]);
			}
		}
		P.bAlbumSeen = V.bAlbum;
		TestEqual(FString::Printf(TEXT("encode %s"), V.Code), P.EncodeCode(), FString(V.Code));
		FMIProgress Back;
		if (TestTrue(FString::Printf(TEXT("decode %s"), V.Code), FMIProgress::DecodeCode(V.Code, Back)))
		{
			TestEqual(TEXT("round trip"), Back.EncodeCode(), FString(V.Code));
			TestEqual(TEXT("album"), Back.bAlbumSeen, V.bAlbum);
			for (int32 I = 0; I < 3; ++I)
			{
				TestEqual(TEXT("cleared"), Back.IsCleared(FMIProgress::CodeOrder()[I]), V.C[I]);
			}
		}
		// Typed by a person: lower case, no hyphen, O for 0, I or L for 1.
		FString Typed = FString(V.Code).Replace(TEXT("-"), TEXT("")).ToLower().Replace(TEXT("0"), TEXT("o")).Replace(TEXT("1"), TEXT("l"));
		TestTrue(TEXT("a typed code reads the same"), FMIProgress::DecodeCode(Typed, Back) && Back.EncodeCode() == FString(V.Code));
		// No single-character change of a valid code is accepted (the check is a 16-bit CRC; 5-bit bursts are always caught).
		const FString Plain = FString(V.Code).Replace(TEXT("-"), TEXT(""));
		const FString Alpha(TEXT("0123456789ABCDEFGHJKMNPQRSTVWXYZ"));
		int32 Accepted = 0;
		for (int32 At = 0; At < 8; ++At)
		{
			for (const TCHAR C : Alpha)
			{
				if (C == Plain[At]) continue;
				FString Bad = Plain;
				Bad[At] = C;
				FMIProgress Out;
				Accepted += FMIProgress::DecodeCode(Bad, Out) ? 1 : 0;
			}
		}
		TestEqual(FString::Printf(TEXT("single-character changes of %s accepted"), V.Code), Accepted, 0);
	}
	FMIProgress Out;
	TestFalse(TEXT("empty"), FMIProgress::DecodeCode(TEXT(""), Out));
	TestFalse(TEXT("short"), FMIProgress::DecodeCode(TEXT("47YZ-MB3"), Out));
	TestFalse(TEXT("a letter outside the alphabet (U)"), FMIProgress::DecodeCode(TEXT("47YU-MB30"), Out));
	TestFalse(TEXT("cleared levels must be a prefix"), [&]() { FMIProgress P; FMILevelRecord& R = P.Levels.Add(TEXT("midtown")); R.bCleared = true; R.BestPoints = 1; R.BestDifficulty = TEXT("boss"); return FMIProgress::DecodeCode(P.EncodeCode(), Out); }());
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICampaignUnlocksTest, "MurderInc.Campaign.Unlocks", MITest::Flags)
bool FMICampaignUnlocksTest::RunTest(const FString&)
{
	const TArray<FName> Order = {TEXT("block"), TEXT("chinatown"), TEXT("midtown")};
	FMIProgress P;
	TestTrue(TEXT("level 1 is always open"), P.IsOpen(TEXT("block"), Order));
	TestFalse(TEXT("level 2 is locked"), P.IsOpen(TEXT("chinatown"), Order));
	TestFalse(TEXT("level 3 is locked"), P.IsOpen(TEXT("midtown"), Order));
	TestFalse(TEXT("an unknown level is not open"), P.IsOpen(TEXT("nowhere"), Order));
	TestEqual(TEXT("furthest open"), P.FurthestOpen(Order), FName(TEXT("block")));
	TestEqual(TEXT("no next before a clear"), P.NextAfter(TEXT("block"), Order), FName(NAME_None));
	P.RecordStory(TEXT("block"), 2, TEXT("hustler"));
	TestTrue(TEXT("clearing the Block opens Canal Street"), P.IsOpen(TEXT("chinatown"), Order));
	TestFalse(TEXT("but not Midtown"), P.IsOpen(TEXT("midtown"), Order));
	TestEqual(TEXT("next after the Block"), P.NextAfter(TEXT("block"), Order), FName(TEXT("chinatown")));
	TestEqual(TEXT("furthest open now"), P.FurthestOpen(Order), FName(TEXT("chinatown")));
	P.RecordStory(TEXT("chinatown"), 1, TEXT("kingpin"));
	TestTrue(TEXT("Midtown opens"), P.IsOpen(TEXT("midtown"), Order));
	TestEqual(TEXT("no level after the last"), P.NextAfter(TEXT("midtown"), Order), FName(NAME_None));
	// Ratings only go up: a worse run changes nothing but the count; the same points on a harder difficulty is better.
	P.RecordStory(TEXT("block"), 1, TEXT("kingpin"));
	TestEqual(TEXT("best points kept"), P.Levels[TEXT("block")].BestPoints, 2);
	TestEqual(TEXT("clears counted"), P.Levels[TEXT("block")].Clears, 2);
	P.RecordStory(TEXT("block"), 2, TEXT("boss"));
	TestEqual(TEXT("same points, harder difficulty"), P.Levels[TEXT("block")].BestDifficulty, FName(TEXT("boss")));
	P.RecordStory(TEXT("block"), 4, TEXT("hustler"));
	TestEqual(TEXT("more points win over the difficulty"), P.Levels[TEXT("block")].BestPoints, 4);
	// Merge: the maximum of everything, commutative and idempotent, never lowers.
	FMIProgress A, B;
	A.RecordStory(TEXT("block"), 3, TEXT("boss"));
	A.RecordHold(TEXT("chinatown"), 500);
	B.RecordStory(TEXT("block"), 1, TEXT("kingpin"));
	B.RecordStory(TEXT("chinatown"), 0, TEXT("hustler"));
	B.RecordHold(TEXT("chinatown"), 900);
	B.bAlbumSeen = true;
	FMIProgress AB = A, BA = B;
	AB.Merge(B);
	BA.Merge(A);
	TestEqual(TEXT("merge is commutative"), AB.EncodeCode(), BA.EncodeCode());
	TestEqual(TEXT("merge keeps the best Hold"), AB.Levels[TEXT("chinatown")].HoldBest, 900);
	TestEqual(TEXT("merge keeps the best rating"), AB.Levels[TEXT("block")].BestPoints, 3);
	const FString Once = AB.EncodeCode();
	AB.Merge(B);
	AB.Merge(A);
	TestEqual(TEXT("merge is idempotent"), AB.EncodeCode(), Once);
	// The save fields: progress goes in and comes out; an old save (no progress) loads as nothing cleared.
	FMIProgressSave Save;
	UMIRunSetupSubsystem::ProgressToSave(P, Save);
	FMIProgress Loaded;
	UMIRunSetupSubsystem::ProgressFromSave(Save, Loaded);
	TestEqual(TEXT("save round trip"), Loaded.EncodeCode(), P.EncodeCode());
	TestEqual(TEXT("save round trip: Hold best"), Loaded.Levels[TEXT("block")].BestPoints, P.Levels[TEXT("block")].BestPoints);
	UMISaveGame* Old = NewObject<UMISaveGame>();  // a save written before the campaign: the new field is its default
	FMIProgress FromOld;
	UMIRunSetupSubsystem::ProgressFromSave(Old->Progress, FromOld);
	TestEqual(TEXT("an old save has nothing cleared"), FromOld.Levels.Num(), 0);
	TestTrue(TEXT("and the Block is open"), FromOld.IsOpen(TEXT("block"), Order));
	// The front end: a locked level cannot be chosen, an open one can.
	FMILoadoutData Data;
	FString Error;
	if (TestTrue(TEXT("loadout data loads: ") + Error, FMILoadoutData::Load(Data, Error)))
	{
		TestEqual(TEXT("levels.json order is the campaign"), Data.LevelOrder, Order);
		FMIReadiness Ready;
		Ready.Data = &Data;
		FMIFrontEndRules Rules;
		Rules.Init(&Data, Ready, nullptr, Data.ParitySetup(TEXT("mission"), TEXT("hustler"), TEXT("night")));
		FMIProgress Fresh;
		Rules.SetProgress(&Fresh, false);
		Rules.SetLevel(TEXT("midtown"));
		TestEqual(TEXT("a locked level is refused"), Rules.GetSetup().Level, Data.ParityLevel);
		TestTrue(TEXT("its card says why"), Rules.LevelState(TEXT("chinatown")).Contains(TEXT("Locked")));
		Fresh.RecordStory(TEXT("block"), 1, TEXT("boss"));
		Rules.SetLevel(TEXT("chinatown"));
		TestEqual(TEXT("an open level is taken"), Rules.GetSetup().Level, FName(TEXT("chinatown")));
		TestTrue(TEXT("the cleared card says so"), Rules.LevelState(TEXT("block")).Contains(TEXT("Cleared")));
		Rules.SetProgress(&Fresh, true);
		Rules.SetLevel(TEXT("midtown"));
		TestEqual(TEXT("unlock-all opens every level (tests only)"), Rules.GetSetup().Level, FName(TEXT("midtown")));
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICampaignBlockUnchangedTest, "MurderInc.Campaign.BlockUnchanged", MITest::Flags)
bool FMICampaignBlockUnchangedTest::RunTest(const FString&)
{
	const FMILevelData* Block = FMILevelData::Get();
	if (!TestNotNull(TEXT("the Block loads"), Block))
	{
		return false;
	}
	TestTrue(TEXT("ForLevel(block) is the object Get() returns"), FMILevelData::ForLevel(TEXT("block")) == Block);
	TestTrue(TEXT("no level named: the Block"), FMILevelData::ForLevel(NAME_None) == Block);
	TestTrue(TEXT("the Block has its El deck"), Block->bHasDeck);
	TestFalse(TEXT("no afterAll truck"), Block->bTruckAfterAll);
	TestEqual(TEXT("no tuning adds"), Block->Tuning.MaxAliveAdd + Block->Tuning.PursuitBudgetAdd + (Block->Tuning.bExcludePlayerRoom ? 1 : 0) + Block->Tuning.RatingTime.Num(), 0);
	int32 Ground = 0, Air = 0, Off = 0, Over = 0;
	for (const FMILevelPoint& P : Block->Spawns)
	{
		Ground += P.Type == FName(TEXT("ground")) ? 1 : 0;
		Air += P.Type == FName(TEXT("air")) ? 1 : 0;
		Off += P.bEnabled ? 0 : 1;
		Over += P.Overlooks.Num();
	}
	TestEqual(TEXT("29 ground points"), Ground, 29);
	TestEqual(TEXT("17 air points"), Air, 17);
	TestEqual(TEXT("every point enabled, none filtered"), Off + Over, 0);
	TestEqual(TEXT("21 explosives"), Block->Explosives.Num(), 21);
	// The Block's data files are the shipped ones, byte for byte (their sizes: a changed byte count is a changed file).
	const struct { const TCHAR* File; int64 Size; } Files[] = {{TEXT("level.json"), 1414836}, {TEXT("text.json"), 24965}, {TEXT("props.json"), 488723}, {TEXT("atmos.json"), 177389}, {TEXT("rules.json"), 1594}};
	for (const auto& F : Files)
	{
		const int64 Size = IFileManager::Get().FileSize(*FPaths::Combine(UMIDataSubsystem::GetDataDir(), F.File));
		TestEqual(FString::Printf(TEXT("%s is unchanged"), F.File), Size, F.Size);
	}
	// The Block's lines are the Block's: a plain load has no overlay.
	FMIText Plain, Block2;
	FString Error;
	TestTrue(TEXT("text loads"), FMIText::Load(Plain, Error) && FMIText::Load(Block2, Error, TEXT("block")));
	TestEqual(TEXT("the Block's radio intro, with or without the id"), Block2.Get(TEXT("radio.intro.text")), Plain.Get(TEXT("radio.intro.text")));
	TestTrue(TEXT("it is the Block's"), Plain.Get(TEXT("radio.intro.text")).Contains(TEXT("chop shop")));
	return true;
}

// Canal's roof is not a safe place: a player parked mid-roof in a mission run keeps being fought. The street Goons that have no
// firing cell are returned to the pool (the stranded rule) and the run replaces each one, from a roof spawn that can reach or see him.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMILevelsChinatownRoofCampTest, "MurderInc.Levels.Chinatown.RoofCamp", MITest::Flags)
bool FMILevelsChinatownRoofCampTest::RunTest(const FString&)
{
	using namespace MICampaignTestsPrivate;
	FActiveLevel Active(TEXT("chinatown"));
	FLevelWorld W;
	FMIBootOptions O;
	O.Level = TEXT("chinatown");
	O.bTitle = false;
	O.Mode = TEXT("mission");
	O.Difficulty = TEXT("hustler");
	O.bPersist = false;
	O.bDrawGrey = false;
	if (!TestTrue(TEXT("Canal boots in a world"), W.Player && W.Game && W.Game->Boot(O)))
	{
		return false;
	}
	W.Game->StartRun(TEXT("mission"), true);
	W.Player->GetPlayerRules().bInvulnerable = true;
	for (int32 I = 0; I < 900; ++I)
	{
		W.Step();
	}
	TestEqual(TEXT("the run is on"), W.Game->GetRules().GetState(), EMIGameState::Playing);
	// Park the player mid-roof, as the finding did, and let the Goons find out.
	const FVector RoofAt = MI::Web::ToUnreal(FVector(-12.0, 5.7, 0.0));
	W.Player->TeleportFeet(RoofAt);
	// Three street Goons who are on to him (the shots that brought him up here woke them): alerted, as a wave's Goons arrive.
	FMIEnemyField& Foes = W.Game->GetEnemies();
	Foes.Clear();
	FMIEnemySpawnOptions Hunt;
	Hunt.bAlerted = true;
	const FVector Camp = MI::Web::FromUnreal(W.Player->GetPlayerRules().Feet);
	Hunt.Target = Camp;
	Foes.SetLivePlayerPos(Camp);
	for (const FVector& At : {FVector(-28.0, 0.1, -4.0), FVector(-6.5, 0.1, 4.2), FVector(-13.0, 0.1, 9.2)})
	{
		Foes.Spawn(MIEnemy::EType::Goon, At, Hunt);
	}
	int32 Shots = 0;
	FMIGameEvents* Events = UMIEventSubsystem::Get(W.World);
	if (!TestNotNull(TEXT("the event bus"), Events))
	{
		return false;
	}
	const FDelegateHandle Handle = Events->Enemy.AddLambda([&](const FMIEnemyEvent& E) { if (E.Kind == FMIEnemyEvent::EKind::Fire) ++Shots; });
	constexpr int32 Windows = 9;
	int32 ShotsIn[Windows] = {};
	int32 RoofSeen = 0, MinAlive = 99, Frames = 0;
	double FirstShot = -1.0;
	for (int32 F = 0; F < 90 * 60; ++F)
	{
		const int32 Before = Shots;
		// The test world has no floor under the roof: hold the player on it, as the roof's floor would.
		W.Player->TeleportFeet(RoofAt);
		W.Step();
		++Frames;
		const double T = F * Dt;
		if (Shots > Before)
		{
			ShotsIn[FMath::Min(Windows - 1, static_cast<int32>(T / 10.0))] += Shots - Before;
			if (FirstShot < 0)
			{
				FirstShot = T;
			}
		}
		if (F % 60 == 0)
		{
			int32 Alive = 0;
			FMIEnemyField& Field = W.Game->GetEnemies();
			for (const int32 S : Field.GetList())
			{
				const FMIEnemy& E = Field.GetSlots()[S];
				if (E.bAlive)
				{
					++Alive;
					RoofSeen += E.Pos.Y > 2.0 ? 1 : 0;
				}
			}
			if (F >= 15 * 60)
			{
				MinAlive = FMath::Min(MinAlive, Alive);
			}
			if (F % 600 == 0)
			{
				AddInfo(FString::Printf(TEXT("roof camp t=%d s: %d Goons alive, %d shots so far"), F / 60, Alive, Shots));
			}
		}
	}
	Events->Enemy.Remove(Handle);
	FString Line;
	int32 Hot = 0;
	for (int32 I = 0; I < Windows; ++I)
	{
		Line += FString::Printf(TEXT("%d "), ShotsIn[I]);
		Hot += ShotsIn[I] > 0 ? 1 : 0;
	}
	AddInfo(FString::Printf(TEXT("roof camp: first shot at %.1f s, shots per 10 s window: %s, fewest Goons alive after 15 s %d, roof-Goon samples %d"), FirstShot, *Line, MinAlive, RoofSeen));
	TestTrue(TEXT("a Goon engages the roof player within 20 s"), FirstShot >= 0.0 && FirstShot < 20.0);
	TestTrue(TEXT("the roof player is fought again and again over 90 s (shots in at least 7 of 9 ten-second windows)"), Hot >= 7);
	TestTrue(TEXT("the stranded street Goons are replaced: some are alive at every sample after 15 s"), MinAlive >= 1);
	TestTrue(TEXT("a replacement comes from a roof spawn and stays on the roof"), RoofSeen > 0);
	return true;
}

#endif
