// Version 3 (play through the stream): input shaping and the cloud rules that need no world.
//   MurderInc.Input.StreamMouse     Pixel Streaming's mouse counts back to browser pixels, the spike filter, the launch option
//   MurderInc.Input.PadLook         the right stick against numbers worked out with the web game's own functions
//   MurderInc.UI.CardHitTest        which row of a card is under the mouse, and which half of an adjustable row
//   MurderInc.Cloud.Viewers         the click card: for the first viewer and after everybody left, not for a guest
//   MurderInc.Cloud.ViewerCommands  the allowlist for a viewer's console commands
//   MurderInc.Cloud.Quality         Graphics quality while streamed: the frame cap, the resolution and the cloud profile stay

#include "Cloud/MICloud.h"
#include "Core/Data/MIDataSubsystem.h"
#include "HAL/IConsoleManager.h"
#include "Misc/AutomationTest.h"
#include "Misc/ConfigCacheIni.h"
#include "Player/MILookInput.h"
#include "Tests/MITestUtil.h"
#include "UI/MIMenus.h"
#include "UnrealEngine.h"

#if WITH_AUTOMATION_TESTS

namespace MIStreamInputTestsPrivate
{
	/**
	 * What Pixel Streaming 2 (Unreal 5.9) does to one mouse event's movement along one axis on its way to the game, as
	 * read in both sources on 2026-11-24:
	 *  - the browser (Epic's player, Frontend/library/src/Util/InputCoordTranslator.ts translateSigned, sent by
	 *    Inputs/MouseControllerLocked.ts through DataView.setInt16): movement / (0.5 x player size) x 32767, the fraction
	 *    cut and the value wrapped into 16 bits;
	 *  - the engine (PixelStreaming2RTC RTCInputHandler.cpp HandleOnMouseMove; PixelStreaming2Input InputHandler.cpp
	 *    ConvertFromNormalizedScreenLocation): the int16 divided by the float 32767, times the viewport size, cut to int32.
	 */
	int32 ThroughPixelStreaming(int32 MovementPixels, int32 PlayerSize, int32 RenderSize)
	{
		const double Sent = (double)MovementPixels / (0.5 * PlayerSize) * 32767.0;
		int64 Wire = (int64)Sent;                          // ToInt16: toward zero ...
		Wire = ((Wire % 65536) + 65536) % 65536;           // ... modulo 2^16 ...
		if (Wire >= 32768) Wire -= 65536;                  // ... as a signed 16-bit value
		const float Unit = (float)Wire / 32767.f;
		return (int32)((double)Unit * (double)RenderSize);
	}

	FString CVar(const TCHAR* Name)
	{
		const IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(Name);
		return V ? V->GetString() : FString(TEXT("(none)"));
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIStreamMouseTest, "MurderInc.Input.StreamMouse", MITest::Flags)

bool FMIStreamMouseTest::RunTest(const FString& Parameters)
{
	using namespace MIStreamInputTestsPrivate;
	// The picture rendered at the size the player shows it (E3DS's Dynamic resolution): 2 counts per browser pixel,
	// less one count per event. The default shape gives the pixels back exactly.
	FMIStreamMouse Shape;
	Shape.Scale = 0.5;
	Shape.Truncation = 1.0;
	Shape.Glitch = 400.0;
	int32 Wrong = 0, NotTwoLessOne = 0;
	for (int32 M = -300; M <= 300; ++M)
	{
		const int32 Counts = ThroughPixelStreaming(M, 1920, 1920);
		NotTwoLessOne += Counts == (M == 0 ? 0 : 2 * M - FMath::Sign(M)) ? 0 : 1;
		FVector2D Pixels;
		const bool bKept = Shape.Event(FVector2D(Counts, -Counts), Pixels);
		Wrong += bKept && FMath::IsNearlyEqual(Pixels.X, (double)M, 1e-9) && FMath::IsNearlyEqual(Pixels.Y, (double)-M, 1e-9) ? 0 : 1;
	}
	TestEqual(TEXT("equal sizes: every event arrives as 2 counts per pixel less one (the truncation the shape puts back)"), NotTwoLessOne, 0);
	TestEqual(TEXT("equal sizes: 0.5 with the truncation put back gives the browser's pixels, -300..300"), Wrong, 0);
	TestEqual(TEXT("one pixel arrives as one count"), ThroughPixelStreaming(1, 1920, 1920), 1);
	TestEqual(TEXT("ten pixels arrive as nineteen"), ThroughPixelStreaming(10, 1920, 1920), 19);

	// A fixed 1920-wide render shown 1280 wide (the page's frame): 3 counts per pixel less one; the scale is
	// player width / (2 x render width).
	FMIStreamMouse Embedded = Shape;
	Embedded.Scale = 1280.0 / (2.0 * 1920.0);
	Wrong = 0;
	for (int32 M = 1; M <= 300; ++M)
	{
		FVector2D Pixels;
		Embedded.Event(FVector2D(ThroughPixelStreaming(M, 1280, 1920), 0.0), Pixels);
		Wrong += FMath::IsNearlyEqual(Pixels.X, (double)M, 1e-9) ? 0 : 1;
	}
	TestEqual(TEXT("1920 rendered, shown 1280 wide: scale 1/3 gives the pixels back"), Wrong, 0);
	// Shown larger than rendered (1.5 counts per pixel): the lost fraction is no longer a whole count, so the answer
	// is within a third of a pixel.
	FMIStreamMouse Fullscreen = Shape;
	Fullscreen.Scale = 2560.0 / (2.0 * 1920.0);
	double Worst = 0.0;
	for (int32 M = 1; M <= 300; ++M)
	{
		FVector2D Pixels;
		Fullscreen.Event(FVector2D(ThroughPixelStreaming(M, 2560, 1920), 0.0), Pixels);
		Worst = FMath::Max(Worst, FMath::Abs(Pixels.X - M));
	}
	TestTrue(TEXT("1920 rendered, shown 2560 wide: within 0.34 pixel"), Worst <= 0.34);

	// The web game's pointer-lock spike filter (src/input.js onMouseMove): an event beyond mouseGlitch pixels on either
	// axis is dropped whole.
	FVector2D Pixels;
	TestTrue(TEXT("400 pixels in one event are kept"), Shape.Event(FVector2D(ThroughPixelStreaming(400, 1920, 1920), 0.0), Pixels));
	TestFalse(TEXT("401 pixels in one event are a spike"), Shape.Event(FVector2D(ThroughPixelStreaming(401, 1920, 1920), 0.0), Pixels));
	TestFalse(TEXT("a spike on the other axis drops the event too"), Shape.Event(FVector2D(3.0, -1200.0), Pixels));
	// A move of more than half the player's width overflows the 16 bits and arrives reversed: caught by the same filter.
	const int32 Reversed = ThroughPixelStreaming(700, 1280, 1280);
	TestTrue(TEXT("700 pixels in a 1280-wide player arrive reversed"), Reversed < 0);
	TestFalse(TEXT("and are dropped"), Shape.Event(FVector2D(Reversed, 0.0), Pixels));
	// An axis that did not move stays still.
	TestTrue(TEXT("a horizontal move is kept"), Shape.Event(FVector2D(19.0, 0.0), Pixels));
	TestEqual(TEXT("19 counts are 10 pixels"), Pixels.X, 10.0);
	TestEqual(TEXT("the still axis stays 0"), Pixels.Y, 0.0);

	// The desktop: a plain shape changes nothing and drops nothing.
	const FMIStreamMouse Desktop;
	TestTrue(TEXT("desktop: nothing is dropped"), Desktop.Event(FVector2D(100000.0, -5.0), Pixels));
	TestTrue(TEXT("desktop: counts are pixels"), Pixels.X == 100000.0 && Pixels.Y == -5.0);

	// [MICloud] of DefaultGame.ini and the launch options.
	const FMIStreamMouse FromIni = UMICloudSubsystem::ReadMouseShape(TEXT(""), 400.0);
	TestEqual(TEXT("[MICloud] MouseScale"), FromIni.Scale, 0.5);
	TestEqual(TEXT("[MICloud] MouseTruncation"), FromIni.Truncation, 1.0);
	TestEqual(TEXT("the spike size is the caller's (config.json player.input.mouseGlitch)"), FromIni.Glitch, 400.0);
	const FMIStreamMouse Tuned = UMICloudSubsystem::ReadMouseShape(TEXT("MurderInc -MICloud -MIMouseScale=0.25 -MIMouseTruncation=0 -log"), 400.0);
	TestTrue(TEXT("-MIMouseScale=0.25"), FMath::IsNearlyEqual(Tuned.Scale, 0.25, 1e-6));
	TestEqual(TEXT("-MIMouseTruncation=0"), Tuned.Truncation, 0.0);
	const FMIStreamMouse Silly = UMICloudSubsystem::ReadMouseShape(TEXT("-MIMouseScale=900 -MIMouseTruncation=-3"), 400.0);
	TestEqual(TEXT("a scale out of range falls back to 0.5"), Silly.Scale, 0.5);
	TestEqual(TEXT("a truncation out of range falls back to 1"), Silly.Truncation, 1.0);
	FMIConfigData Config;
	FString Error;
	if (TestTrue(TEXT("config.json"), UMIDataSubsystem::LoadConfig(Config, Error)))
	{
		TestEqual(TEXT("player.input.mouseGlitch"), Config.Player.Look.MouseGlitch, 400.0);
		TestEqual(TEXT("player.input.mouseWake"), Config.Player.Look.MouseWake, 4.0);
	}
	return !HasAnyErrors();
}

// The expected numbers come from the web game's own functions (src/input.js deadzone, padCurve, padLook and the boost
// and rate lines of pollPad and update) run in Node with config.json's player.input.pad: full right stick for one
// second at 60 frames a second turns 263.775 degrees (166 degrees a second, rising to 291 with the boost after 0.45 s).
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIPadLookTest, "MurderInc.Input.PadLook", MITest::Flags)

bool FMIPadLookTest::RunTest(const FString& Parameters)
{
	FMIConfigData Config;
	FString Error;
	if (!TestTrue(TEXT("config.json"), UMIDataSubsystem::LoadConfig(Config, Error)))
	{
		AddError(Error);
		return false;
	}
	const FMIPadLookData& P = Config.Player.Look.Pad;
	TestEqual(TEXT("pad.deadzone"), P.Deadzone, 0.14);
	TestEqual(TEXT("pad.trigger"), P.Trigger, 0.35);
	TestTrue(TEXT("pad.yaw 2.9 rad/s in degrees"), FMath::IsNearlyEqual(P.YawRate, 166.15776058793872, 1e-9));
	TestEqual(TEXT("pad.pitchScale"), P.PitchScale, 0.62);
	TestTrue(TEXT("pad.curve"), P.CurveLinear == 0.25 && P.CurveCubic == 0.75);
	TestTrue(TEXT("pad.boost"), P.Boost == 1.75 && P.BoostFrom == 0.92 && P.BoostTime == 0.45 && P.BoostDecay == 0.17);
	TestEqual(TEXT("pad.sprintForward"), P.SprintForward, 0.55);

	TestEqual(TEXT("dead zone: its edge is 0"), MILook::Deadzone(0.14, 0.14), 0.0);
	TestTrue(TEXT("dead zone: 0.57 is half"), FMath::IsNearlyEqual(MILook::Deadzone(0.57, 0.14), 0.5, 1e-12));
	TestEqual(TEXT("dead zone: full stays full"), MILook::Deadzone(-1.0, 0.14), -1.0);
	TestEqual(TEXT("dead zone: beyond full is full"), MILook::Deadzone(1.3, 0.14), 1.0);

	// Unreal's stick (X right, Y up) held for Frames frames; the sum in degrees (X right, Y down).
	const auto Hold = [&P](double X, double Y, int32 Frames, double Fps, double Sens = 1.0, double AimSlow = 1.0, bool bInvert = false)
	{
		FMIPadLook Look;
		Look.Config = P;
		FVector2D Sum = FVector2D::ZeroVector;
		for (int32 I = 0; I < Frames; ++I)
		{
			Sum += Look.Step(FVector2D(X, Y), 1.0 / Fps, Sens, AimSlow, bInvert);
		}
		return Sum;
	};
	const auto Near = [this](const TCHAR* What, double Actual, double Expected)
	{
		if (!FMath::IsNearlyEqual(Actual, Expected, 1e-9 * FMath::Max(1.0, FMath::Abs(Expected))))
		{
			AddError(FString::Printf(TEXT("%s: expected %.12f, got %.12f"), What, Expected, Actual));
		}
	};
	Near(TEXT("full right for 1 s at 60 fps: yaw"), Hold(1, 0, 60, 60).X, 263.77544493335273);
	Near(TEXT("full right for 1 s at 30 fps: yaw"), Hold(1, 0, 30, 30).X, 264.77546849244663);
	Near(TEXT("full right for 2 s at 60 fps: yaw"), Hold(1, 0, 120, 60).X, 554.5515259622457);
	Near(TEXT("full left for 0.5 s: yaw"), Hold(-1, 0, 30, 60).X, -118.38740441890634);
	Near(TEXT("half right for 1 s (no boost): yaw"), Hold(0.5, 0, 60, 60).X, 26.52960986810703);
	Near(TEXT("0.9 right for 1 s (under the boost line): yaw"), Hold(0.9, 0, 60, 60).X, 122.71498890466829);
	Near(TEXT("0.2 right for 1 s: yaw"), Hold(0.2, 0, 60, 60).X, 2.9404199522964043);
	TestEqual(TEXT("at the dead zone's edge nothing turns"), Hold(0.14, 0, 60, 60).X, 0.0);
	// Stick down (Unreal -Y) looks down (+Y), at 62 % of the yaw rate.
	Near(TEXT("full down for 1 s: pitch"), Hold(0, -1, 60, 60).Y, 163.54077585867878);
	TestEqual(TEXT("full down turns no yaw"), Hold(0, -1, 60, 60).X, 0.0);
	const FVector2D Diagonal = Hold(0.7, -0.7, 60, 60);
	Near(TEXT("0.7 right and down for 1 s: yaw"), Diagonal.X, 152.18337296763573);
	Near(TEXT("0.7 right and down for 1 s: pitch"), Diagonal.Y, 94.35369123993411);
	const FVector2D Corner = Hold(1, -1, 60, 60);
	Near(TEXT("the corner of a square gate: yaw"), Corner.X, 186.51740582287255);
	Near(TEXT("the corner of a square gate: pitch"), Corner.Y, 115.64079161018084);
	// Sensitivity and the aim slow-down scale the rate; invert flips the pitch only.
	Near(TEXT("sensitivity 2 doubles the turn"), Hold(1, 0, 60, 60, 2.0).X, 2.0 * 263.77544493335273);
	Near(TEXT("the aim slow-down (0.55 over an enemy) scales the turn"), Hold(1, 0, 60, 60, 1.0, 0.55).X, 0.55 * 263.77544493335273);
	Near(TEXT("invert Y flips the pitch"), Hold(0, -1, 60, 60, 1.0, 1.0, true).Y, -163.54077585867878);
	Near(TEXT("invert Y leaves the yaw"), Hold(0.7, -0.7, 60, 60, 1.0, 1.0, true).X, 152.18337296763573);

	// The boost: full after 0.45 s at the rim, gone 0.17 s after the stick lets go.
	FMIPadLook Look;
	Look.Config = P;
	for (int32 I = 0; I < 27; ++I) Look.Step(FVector2D(1, 0), 1.0 / 60.0, 1.0, 1.0, false);
	TestTrue(TEXT("0.45 s at the rim: full boost"), FMath::IsNearlyEqual(Look.GetBoost(), 1.0, 1e-9));
	for (int32 I = 0; I < 5; ++I) Look.Step(FVector2D::ZeroVector, 1.0 / 60.0, 1.0, 1.0, false);
	TestTrue(TEXT("0.083 s after letting go: about half the boost is left"), Look.GetBoost() > 0.4 && Look.GetBoost() < 0.6);
	for (int32 I = 0; I < 6; ++I) Look.Step(FVector2D::ZeroVector, 1.0 / 60.0, 1.0, 1.0, false);
	TestEqual(TEXT("0.18 s after letting go: no boost"), Look.GetBoost(), 0.0);
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICardHitTest, "MurderInc.UI.CardHitTest", MITest::Flags)

bool FMICardHitTest::RunTest(const FString& Parameters)
{
	// Four rows, 46 high with 8 between, from (682, 500), 548 wide: the pause card at 1920 x 1080 (resume, restart,
	// difficulty with a value, settings).
	FMIMenuLayout L;
	L.Screen = EMIMenuScreen::Pause;
	L.X = 682.0;
	L.Width = 548.0;
	L.Top = 500.0;
	L.RowHeight = 46.0;
	L.RowGap = 8.0;
	L.Adjust = {false, false, true, false};
	const auto Row = [&L](double X, double Y) { return L.HitTest(FVector2D(X, Y)).Row; };
	const auto Side = [&L](double X, double Y) { return L.HitTest(FVector2D(X, Y)).Side; };
	TestEqual(TEXT("the first row's top left corner"), Row(682.0, 500.0), 0);
	TestEqual(TEXT("the first row's last pixel line"), Row(900.0, 545.9), 0);
	TestEqual(TEXT("the gap under the first row hits nothing"), Row(900.0, 546.0), (int32)INDEX_NONE);
	TestEqual(TEXT("the gap's last pixel line hits nothing"), Row(900.0, 553.9), (int32)INDEX_NONE);
	TestEqual(TEXT("the second row"), Row(900.0, 554.0), 1);
	TestEqual(TEXT("the third row"), Row(700.0, 630.0), 2);
	TestEqual(TEXT("the last row"), Row(1229.9, 700.0), 3);
	TestEqual(TEXT("under the last row"), Row(900.0, 708.0), (int32)INDEX_NONE);
	TestEqual(TEXT("far under the card"), Row(900.0, 1000.0), (int32)INDEX_NONE);
	TestEqual(TEXT("above the rows (the card's title)"), Row(900.0, 499.9), (int32)INDEX_NONE);
	TestEqual(TEXT("left of the rows"), Row(681.9, 520.0), (int32)INDEX_NONE);
	TestEqual(TEXT("right of the rows"), Row(1230.0, 520.0), (int32)INDEX_NONE);
	// A button has no sides; an adjustable row's left half is one value back, its right half one forward.
	TestEqual(TEXT("a button: no side"), Side(700.0, 520.0), 0);
	TestEqual(TEXT("an adjustable row, left half: back"), Side(700.0, 630.0), -1);
	TestEqual(TEXT("an adjustable row, just left of the middle: back"), Side(955.9, 630.0), -1);
	TestEqual(TEXT("an adjustable row, the middle: forward"), Side(956.0, 630.0), 1);
	TestEqual(TEXT("an adjustable row, right half: forward"), Side(1200.0, 630.0), 1);
	// No card on screen, or a layout that was never filled: nothing to hit.
	FMIMenuLayout None;
	TestEqual(TEXT("no card: nothing"), None.HitTest(FVector2D(900.0, 520.0)).Row, (int32)INDEX_NONE);
	FMIMenuLayout NoRows = L;
	NoRows.Adjust.Reset();
	TestEqual(TEXT("no rows: nothing"), NoRows.HitTest(FVector2D(900.0, 520.0)).Row, (int32)INDEX_NONE);
	// The menu takes a hit only from the layout of the card it shows now.
	FMIMenu Menu;
	Menu.Screen = EMIMenuScreen::Pause;
	Menu.Items.SetNum(4);
	Menu.Layout = L;
	TestEqual(TEXT("the card's own layout"), Menu.HitTest(FVector2D(900.0, 560.0)).Row, 1);
	Menu.Screen = EMIMenuScreen::Settings;
	TestEqual(TEXT("another card's layout: nothing"), Menu.HitTest(FVector2D(900.0, 560.0)).Row, (int32)INDEX_NONE);
	Menu.Screen = EMIMenuScreen::Pause;
	Menu.Items.SetNum(5);
	TestEqual(TEXT("a layout with another number of rows: nothing"), Menu.HitTest(FVector2D(900.0, 560.0)).Row, (int32)INDEX_NONE);
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICloudViewersTest, "MurderInc.Cloud.Viewers", MITest::Flags)

bool FMICloudViewersTest::RunTest(const FString& Parameters)
{
	FMICloudViewers V;
	TestTrue(TEXT("the first viewer gets the click card"), V.Join());
	TestFalse(TEXT("a guest joining the session does not bring the card back"), V.Join());
	TestFalse(TEXT("nor does a third"), V.Join());
	TestEqual(TEXT("three joins counted"), V.Count, 3);
	V.AllLeft();
	TestEqual(TEXT("everybody left"), V.Count, 0);
	TestTrue(TEXT("the first viewer after everybody left gets the card again"), V.Join());
	TestFalse(TEXT("and the next one does not"), V.Join());
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICloudViewerCommandsTest, "MurderInc.Cloud.ViewerCommands", MITest::Flags)

bool FMICloudViewerCommandsTest::RunTest(const FString& Parameters)
{
	const auto Ok = [](const TCHAR* C) { return UMICloudSubsystem::IsViewerCommandAllowed(C); };
	// The stream's own settings, as E3DS's player sends them for its quality and bitrate controls.
	TestTrue(TEXT("PixelStreaming2.WebRTC.MaxBitrate"), Ok(TEXT("PixelStreaming2.WebRTC.MaxBitrate 20000000")));
	TestTrue(TEXT("the legacy plugin's name"), Ok(TEXT("PixelStreaming.WebRTC.MaxBitrate 20000000")));
	TestTrue(TEXT("PixelStreaming2.Encoder.MaxQuality"), Ok(TEXT("PixelStreaming2.Encoder.MaxQuality 80")));
	TestTrue(TEXT("any letter case, spaces around"), Ok(TEXT("  pixelstreaming2.webrtc.fps 60  ")));
	// Everything else.
	TestFalse(TEXT("quit"), Ok(TEXT("quit")));
	TestFalse(TEXT("a debug command of the game"), Ok(TEXT("MIShot /tmp/x.png")));
	TestFalse(TEXT("a render setting"), Ok(TEXT("r.ScreenPercentage 200")));
	TestFalse(TEXT("the resolution (the browser's size request is its own Pixel Streaming command)"), Ok(TEXT("r.SetRes 3840x2160")));
	TestFalse(TEXT("open a map"), Ok(TEXT("open L_Block")));
	TestFalse(TEXT("an empty command"), Ok(TEXT("   ")));
	TestFalse(TEXT("the prefix without its dot"), Ok(TEXT("PixelStreaming2 quit")));
	TestFalse(TEXT("the prefix inside another word"), Ok(TEXT("xPixelStreaming2.WebRTC.Fps 60")));
	TestFalse(TEXT("a second command behind a bar"), Ok(TEXT("PixelStreaming2.WebRTC.Fps 60 | quit")));
	TestFalse(TEXT("a second command on a new line"), Ok(TEXT("PixelStreaming2.WebRTC.Fps 60\nquit")));
	TestFalse(TEXT("a very long command"), Ok(*(FString(TEXT("PixelStreaming2.X ")) + FString::ChrN(300, TEXT('1')))));
	return !HasAnyErrors();
}

// The Settings card's Graphics quality in a stream (UMICloudSubsystem::ApplyStreamedQuality): the scalability groups
// move, and nothing else does: not the frame cap (UGameUserSettings::ApplySettings cleared t.MaxFPS), not the output
// resolution (it asked for its own stored size and window mode), not the render resolution (Ultra set 100 %), not one
// line of the cloud profile.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMICloudQualityTest, "MurderInc.Cloud.Quality", MITest::Flags)

bool FMICloudQualityTest::RunTest(const FString& Parameters)
{
	using namespace MIStreamInputTestsPrivate;
	IConsoleManager& Console = IConsoleManager::Get();
	TArray<FString> Lines;
	GConfig->GetArray(TEXT("MICloud"), TEXT("CVars"), Lines, GGameIni);
	if (!TestTrue(TEXT("[MICloud] has its CVars lines"), Lines.Num() >= 8))
	{
		return false;
	}
	// What the profile's variables hold now, to put back at the end: the test process is not a stream.
	TMap<FString, FString> Before;
	for (const FString& Line : Lines)
	{
		FString Name, Value;
		if (Line.Split(TEXT("="), &Name, &Value))
		{
			Before.Add(Name.TrimStartAndEnd(), CVar(*Name.TrimStartAndEnd()));
		}
	}
	const int32 ShadowBefore = Console.FindConsoleVariable(TEXT("sg.ShadowQuality"))->GetInt();
	const int32 Applied = UMICloudSubsystem::ApplyCloudProfile();
	TestEqual(TEXT("every line of the cloud profile names a console variable"), Applied, Lines.Num());
	TestEqual(TEXT("the cloud profile caps the frame rate at 60"), CVar(TEXT("t.MaxFPS")), FString(TEXT("60")));

	const TCHAR* Watched[] = {TEXT("t.MaxFPS"), TEXT("r.SetRes"), TEXT("r.ScreenPercentage"), TEXT("sg.ResolutionQuality"), TEXT("r.VSync")};
	TMap<FString, FString> Stream;
	for (const TCHAR* Name : Watched)
	{
		Stream.Add(Name, CVar(Name));
	}
	for (const TPair<FString, FString>& Pair : Before)
	{
		Stream.Add(Pair.Key, CVar(*Pair.Key));
	}
	const uint32 ResX = GSystemResolution.ResX, ResY = GSystemResolution.ResY;
	const int32 Mode = (int32)GSystemResolution.WindowMode;

	const auto Unchanged = [&](const FString& When)
	{
		for (const TPair<FString, FString>& Pair : Stream)
		{
			TestEqual(FString::Printf(TEXT("%s: %s"), *When, *Pair.Key), CVar(*Pair.Key), Pair.Value);
		}
		TestTrue(FString::Printf(TEXT("%s: the output resolution and window mode"), *When),
			GSystemResolution.ResX == ResX && GSystemResolution.ResY == ResY && (int32)GSystemResolution.WindowMode == Mode);
	};
	const TCHAR* Names[] = {TEXT("low"), TEXT("medium"), TEXT("high"), TEXT("ultra")};
	for (int32 Level = 0; Level <= 3; ++Level)
	{
		UMICloudSubsystem::ApplyStreamedQuality(Level);
		Unchanged(Names[Level]);
		TestEqual(FString::Printf(TEXT("%s: the shadow group follows the setting"), Names[Level]), Console.FindConsoleVariable(TEXT("sg.ShadowQuality"))->GetInt(), Level);
		TestEqual(FString::Printf(TEXT("%s: the effects group follows the setting"), Names[Level]), Console.FindConsoleVariable(TEXT("sg.EffectsQuality"))->GetInt(), Level);
	}
	UMICloudSubsystem::ApplyStreamedQuality(-1);
	Unchanged(TEXT("auto"));
	TestEqual(TEXT("auto: the groups are back where the game started"), Console.FindConsoleVariable(TEXT("sg.ShadowQuality"))->GetInt(), ShadowBefore);

	// Put the profile's variables back (same priority, or the set would be refused).
	for (const TPair<FString, FString>& Pair : Before)
	{
		if (IConsoleVariable* V = Console.FindConsoleVariable(*Pair.Key))
		{
			V->Set(*Pair.Value, ECVF_SetByDeviceProfile);
		}
	}
	return !HasAnyErrors();
}

#endif  // WITH_AUTOMATION_TESTS
