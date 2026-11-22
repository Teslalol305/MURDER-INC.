#include "Weapons/MIViewmodel.h"

#include "Core/Data/MIDataSubsystem.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"

namespace MIViewmodelPrivate
{
	/** Reads dotted paths from a JSON tree and remembers the first missing one. */
	struct FReader
	{
		TSharedPtr<FJsonObject> Root;
		FString Missing;

		TSharedPtr<FJsonValue> Value(const FString& Path) const
		{
			TArray<FString> Keys;
			Path.ParseIntoArray(Keys, TEXT("."));
			TSharedPtr<FJsonObject> O = Root;
			for (int32 I = 0; I < Keys.Num() && O.IsValid(); ++I)
			{
				const TSharedPtr<FJsonValue> V = O->TryGetField(Keys[I]);
				if (!V.IsValid())
				{
					return nullptr;
				}
				if (I == Keys.Num() - 1)
				{
					return V;
				}
				O = V->Type == EJson::Object ? V->AsObject() : nullptr;
			}
			return nullptr;
		}
		double Num(const FString& Path)
		{
			const TSharedPtr<FJsonValue> V = Value(Path);
			if (!V.IsValid() || V->Type != EJson::Number)
			{
				if (Missing.IsEmpty()) Missing = Path;
				return 0.0;
			}
			return V->AsNumber();
		}
		double NumOr(const FString& Path, double Default) const
		{
			const TSharedPtr<FJsonValue> V = Value(Path);
			return V.IsValid() && V->Type == EJson::Number ? V->AsNumber() : Default;
		}
		FString Str(const FString& Path)
		{
			const TSharedPtr<FJsonValue> V = Value(Path);
			if (!V.IsValid() || V->Type != EJson::String)
			{
				if (Missing.IsEmpty()) Missing = Path;
				return FString();
			}
			return V->AsString();
		}
		FString StrOr(const FString& Path) const
		{
			const TSharedPtr<FJsonValue> V = Value(Path);
			return V.IsValid() && V->Type == EJson::String ? V->AsString() : FString();
		}
		TArray<double> Nums(const FString& Path, int32 Count = -1)
		{
			TArray<double> Out;
			const TSharedPtr<FJsonValue> V = Value(Path);
			if (V.IsValid() && V->Type == EJson::Array)
			{
				for (const TSharedPtr<FJsonValue>& E : V->AsArray())
				{
					Out.Add(E.IsValid() && E->Type == EJson::Number ? E->AsNumber() : 0.0);
				}
			}
			if ((Count >= 0 && Out.Num() != Count) || (Count < 0 && !V.IsValid()))
			{
				if (Missing.IsEmpty()) Missing = Path;
				Out.SetNumZeroed(FMath::Max(Count, 0));
			}
			return Out;
		}
		FVector2D Pair(const FString& Path) { const TArray<double> A = Nums(Path, 2); return FVector2D(A[0], A[1]); }
		FVector Vec(const FString& Path) { const TArray<double> A = Nums(Path, 3); return FVector(A[0], A[1], A[2]); }
		bool Bool(const FString& Path) const { const TSharedPtr<FJsonValue> V = Value(Path); return V.IsValid() && V->Type == EJson::Boolean && V->AsBool(); }
	};

	FMIViewPose PoseOf(const TArray<double>& A)
	{
		FMIViewPose P;
		if (A.Num() >= 6)
		{
			P.Pos = FVector(A[0], A[1], A[2]);
			P.Rot = FMIViewmodelRig::EulerYXZ(A[3], A[4], A[5]);
		}
		return P;
	}

	double Ease(double T)
	{
		if (T <= 0.0) return 0.0;
		if (T >= 1.0) return 1.0;
		return T * T * T * (T * (T * 6.0 - 15.0) + 10.0);
	}

	double EaseOutBack(double T, double S = 1.25)
	{
		if (T <= 0.0) return 0.0;
		if (T >= 1.0) return 1.0;
		const double U = T - 1.0;
		return 1.0 + U * U * ((S + 1.0) * U + S);
	}

	double SoftLimit(double X, double Limit) { return Limit > 0.0 ? Limit * X / (Limit + FMath::Abs(X)) : X; }
	double Signed() { return FMath::FRand() * 2.0 - 1.0; }

	/** Piecewise linear (t, value) keys, eased between keys. */
	double SampleKeys(const TArray<FVector2D>& Keys, double T)
	{
		if (Keys.Num() == 0 || T < Keys[0].X || T > Keys.Last().X) return 0.0;
		for (int32 I = 0; I + 1 < Keys.Num(); ++I)
		{
			if (T <= Keys[I + 1].X)
			{
				const double Span = FMath::Max(1e-6, Keys[I + 1].X - Keys[I].X);
				return FMath::Lerp(Keys[I].Y, Keys[I + 1].Y, Ease((T - Keys[I].X) / Span));
			}
		}
		return Keys.Last().Y;
	}
}

FQuat FMIViewmodelRig::EulerYXZ(double Pitch, double Yaw, double Roll)
{
	return FQuat(FVector(0, 1, 0), Yaw) * FQuat(FVector(1, 0, 0), Pitch) * FQuat(FVector(0, 0, 1), Roll);
}

bool FMIViewmodelData::Load(FMIViewmodelData& Out, FString& OutError)
{
	TSharedPtr<FJsonObject> Presentation, Config;
	if (!UMIDataSubsystem::LoadJsonFile(TEXT("presentation.json"), Presentation, OutError))
	{
		OutError = TEXT("presentation.json: ") + OutError;
		return false;
	}
	if (!UMIDataSubsystem::LoadJsonFile(TEXT("config.json"), Config, OutError))
	{
		OutError = TEXT("config.json: ") + OutError;
		return false;
	}
	return Parse(Presentation, Config, Out, OutError);
}

bool FMIViewmodelData::Parse(const TSharedPtr<FJsonObject>& Presentation, const TSharedPtr<FJsonObject>& Config, FMIViewmodelData& Out, FString& OutError)
{
	using namespace MIViewmodelPrivate;
	FReader P{Presentation};
	FReader C{Config};
	Out = FMIViewmodelData();

	Out.Body = FSoftObjectPath(P.Str(TEXT("firstPerson.body")));
	Out.BodyHandSocket = FName(*P.Str(TEXT("firstPerson.bodyHandSocket")));
	Out.FirstPersonScale = P.Num(TEXT("firstPerson.scale"));
	Out.ViewmodelFov = C.Num(TEXT("player.fov.viewmodel"));
	Out.StrideWalk = C.Num(TEXT("player.stride.walk"));
	Out.StrideSprint = C.Num(TEXT("player.stride.sprint"));
	Out.StrideCrouch = C.Num(TEXT("player.stride.crouch"));
	Out.TracerMinHit = P.Num(TEXT("tracer.minHit"));
	Out.TracerLength = P.Num(TEXT("tracer.length"));
	Out.TracerHidden = P.Num(TEXT("tracer.hidden"));
	Out.TracerHiddenFrom = P.Num(TEXT("tracer.hiddenFrom"));
	Out.TracerThickness = P.Num(TEXT("tracer.thickness"));

	FMIViewFeelData& F = Out.Feel;
	F.BreatheHz = P.Num(TEXT("feel.breathe.hz"));
	F.BreatheY = P.Num(TEXT("feel.breathe.y"));
	F.BreathePitch = P.Num(TEXT("feel.breathe.pitch"));
	F.BreatheRoll = P.Num(TEXT("feel.breathe.roll"));
	F.BobY = P.Pair(TEXT("feel.bob.y"));
	F.BobX = P.Pair(TEXT("feel.bob.x"));
	F.BobRoll = P.Pair(TEXT("feel.bob.roll"));
	F.BobPitch = P.Pair(TEXT("feel.bob.pitch"));
	F.BobAdsPos = P.Num(TEXT("feel.bob.adsPos"));
	F.BobAdsRot = P.Num(TEXT("feel.bob.adsRot"));
	F.BobCrouch = P.Num(TEXT("feel.bob.crouch"));
	F.BobRate = P.Num(TEXT("feel.bob.rate"));
	F.BobWalkSpeed = P.Num(TEXT("feel.bob.walkSpeed"));
	F.BobExponent = P.Num(TEXT("feel.bob.exponent"));
	F.BobMoving = P.Num(TEXT("feel.bob.moving"));
	F.LagGain = P.Num(TEXT("feel.lag.gain"));
	F.LagRoll = P.Num(TEXT("feel.lag.roll"));
	F.LagShift = P.Num(TEXT("feel.lag.shift"));
	F.LagAds = P.Num(TEXT("feel.lag.ads"));
	F.InertiaRate = P.Num(TEXT("feel.inertia.rate"));
	F.InertiaStrafe = P.Num(TEXT("feel.inertia.strafe"));
	F.InertiaSurge = P.Num(TEXT("feel.inertia.surge"));
	F.InertiaLean = P.Num(TEXT("feel.inertia.lean"));
	F.InertiaFall = P.Num(TEXT("feel.inertia.fall"));
	F.InertiaFallPitch = P.Num(TEXT("feel.inertia.fallPitch"));
	F.InertiaAds = P.Num(TEXT("feel.inertia.ads"));
	F.InertiaAccelLimit = P.Num(TEXT("feel.inertia.accelLimit"));
	F.InertiaLeanSpeed = P.Num(TEXT("feel.inertia.leanSpeed"));
	F.InertiaFallClamp = P.Pair(TEXT("feel.inertia.fallClamp"));
	F.Jump = P.Num(TEXT("feel.jump"));
	F.LandPerSpeed = P.Num(TEXT("feel.land.perSpeed"));
	F.LandMax = P.Num(TEXT("feel.land.max"));
	F.LandRoll = P.Num(TEXT("feel.land.roll"));
	F.LandAdsY = P.Num(TEXT("feel.land.adsY"));
	F.LandPitch = P.Num(TEXT("feel.land.pitch"));
	F.LandAdsPitch = P.Num(TEXT("feel.land.adsPitch"));
	F.LandSpring = P.Pair(TEXT("feel.landSpring"));
	F.BumpSpring = P.Pair(TEXT("feel.bumpSpring"));
	F.AimArcDrop = P.Num(TEXT("feel.aimArc.drop"));
	F.AimArcRoll = P.Num(TEXT("feel.aimArc.roll"));
	F.TriggerRate = P.Num(TEXT("feel.triggerRate"));
	F.ReloadIn = P.Num(TEXT("feel.reloadBlend.in"));
	F.ReloadOut = P.Num(TEXT("feel.reloadBlend.out"));
	F.ReloadCancelRate = P.Num(TEXT("feel.reloadBlend.cancelRate"));
	F.DropTime = P.Num(TEXT("feel.dropTime"));
	F.DryPitch = P.Num(TEXT("feel.dry.pitch"));
	F.DryY = P.Num(TEXT("feel.dry.y"));
	F.MagOutY = P.Num(TEXT("feel.magout.y"));
	F.MagOutRoll = P.Num(TEXT("feel.magout.roll"));
	F.MagInsertY = P.Num(TEXT("feel.magInsert.y"));
	F.MagInY = P.Num(TEXT("feel.magin.y"));
	F.MagInPitch = P.Num(TEXT("feel.magin.pitch"));
	F.TugY = P.Num(TEXT("feel.tug.y"));
	F.TugPitch = P.Num(TEXT("feel.tug.pitch"));
	F.MeleeEnemy = P.Num(TEXT("feel.meleeLand.enemy"));
	F.MeleeWall = P.Num(TEXT("feel.meleeLand.wall"));
	F.MeleeRoll = P.Num(TEXT("feel.meleeLand.roll"));

	const TSharedPtr<FJsonValue> Order = C.Value(TEXT("weapons.common.order"));
	if (!Order.IsValid() || Order->Type != EJson::Array)
	{
		OutError = TEXT("config.json weapons.common.order is missing");
		return false;
	}
	static const TCHAR* MarkerNames[] = {TEXT("muzzle"), TEXT("eject"), TEXT("sightRear"), TEXT("pivot"), TEXT("grip"), TEXT("support")};
	for (const TSharedPtr<FJsonValue>& IdValue : Order->AsArray())
	{
		const FString Id = IdValue->AsString();
		const FString G = TEXT("guns.") + Id + TEXT(".");
		const FString W = TEXT("weapons.") + Id + TEXT(".");
		FMIGunViewData& D = Out.Guns.AddDefaulted_GetRef();
		D.Id = FName(*Id);
		D.Mesh = FSoftObjectPath(P.Str(G + TEXT("mesh")));
		D.Idle = FSoftObjectPath(P.StrOr(G + TEXT("idle")));
		{
			const FVector Pos = P.Vec(G + TEXT("meshOffset.pos"));
			const FVector Rot = P.Vec(G + TEXT("meshOffset.rot"));
			// The mesh's frame expressed in gun space (web), converted to Unreal gun space.
			D.MeshOffset = FTransform(FMIViewmodelRig::WebToUE(FMIViewmodelRig::EulerYXZ(Rot.X, Rot.Y, Rot.Z)), FMIViewmodelRig::WebToUE(Pos));
		}
		for (const TCHAR* Name : MarkerNames)
		{
			D.Markers.Add(FName(Name), P.Vec(G + TEXT("markers.") + Name));
			const FString Socket = P.StrOr(G + TEXT("sockets.") + Name);
			if (!Socket.IsEmpty())
			{
				D.Sockets.Add(FName(Name), FName(*Socket));
			}
		}
		D.Relief = P.Num(G + TEXT("relief"));
		D.FlashStar = P.Num(G + TEXT("flash.star"));
		D.FlashJet = P.Num(G + TEXT("flash.jet"));
		D.Sprint = PoseOf(P.Nums(G + TEXT("poses.sprint"), 6));
		D.Reload = PoseOf(P.Nums(G + TEXT("poses.reload"), 6));
		D.Wall = PoseOf(P.Nums(G + TEXT("poses.wall"), 6));
		D.Holster = PoseOf(P.Nums(G + TEXT("poses.holster"), 6));
		if (const TSharedPtr<FJsonValue> Views = C.Value(W + TEXT("views")); Views.IsValid() && Views->Type == EJson::Array)
		{
			for (const TSharedPtr<FJsonValue>& V : Views->AsArray())
			{
				TArray<double> A;
				for (const TSharedPtr<FJsonValue>& E : V->AsArray()) A.Add(E->AsNumber());
				D.Hip.Add(PoseOf(A));
			}
		}
		if (D.Hip.Num() == 0)
		{
			OutError = FString::Printf(TEXT("config.json %sviews is missing"), *W);
			return false;
		}
		if (const TSharedPtr<FJsonValue> Keys = P.Value(G + TEXT("melee")); Keys.IsValid() && Keys->Type == EJson::Array)
		{
			for (const TSharedPtr<FJsonValue>& K : Keys->AsArray())
			{
				TArray<double>& Row = D.Melee.AddDefaulted_GetRef();
				for (const TSharedPtr<FJsonValue>& E : K->AsArray()) Row.Add(E->AsNumber());
				Row.SetNumZeroed(7);
			}
		}
		const auto Part = [&P, &G](const TCHAR* Name, FMIGunPartData& PartOut)
		{
			const FString Base = G + TEXT("parts.") + Name + TEXT(".");
			PartOut.Bone = FName(*P.StrOr(Base + TEXT("bone")));
			if (const TSharedPtr<FJsonValue> Axis = P.Value(Base + TEXT("axis")); Axis.IsValid())
			{
				PartOut.Axis = P.Vec(Base + TEXT("axis")).GetSafeNormal();
			}
			PartOut.Travel = P.NumOr(Base + TEXT("travel"), P.NumOr(Base + TEXT("turn"), P.NumOr(Base + TEXT("tilt"), 0.0)));
			PartOut.Back = P.NumOr(Base + TEXT("back"), 0.0);
			PartOut.Forward = P.NumOr(Base + TEXT("forward"), 0.0);
			PartOut.bLockOnEmpty = P.Bool(Base + TEXT("lockOnEmpty"));
			PartOut.ReleaseAt = FName(*P.StrOr(Base + TEXT("releaseAt")));
			PartOut.Release = P.NumOr(Base + TEXT("release"), 0.0);
			PartOut.Share = P.NumOr(Base + TEXT("share"), 0.0);
			if (P.Value(Base + TEXT("drop")).IsValid())
			{
				PartOut.Drop = P.Vec(Base + TEXT("drop"));
			}
			PartOut.OutMark = FName(*P.StrOr(Base + TEXT("out")));
			PartOut.ShowMark = FName(*P.StrOr(Base + TEXT("show")));
			PartOut.InMark = FName(*P.StrOr(Base + TEXT("in")));
		};
		Part(TEXT("bolt"), D.Bolt);
		Part(TEXT("barrel"), D.Barrel);
		Part(TEXT("trigger"), D.Trigger);
		Part(TEXT("magazine"), D.Magazine);
		const auto Keys = [&P, &G](const TCHAR* Name, TArray<FVector2D>& KeysOut)
		{
			if (const TSharedPtr<FJsonValue> V = P.Value(G + TEXT("parts.boltReload.") + Name); V.IsValid() && V->Type == EJson::Array)
			{
				for (const TSharedPtr<FJsonValue>& K : V->AsArray())
				{
					const TArray<TSharedPtr<FJsonValue>>& A = K->AsArray();
					if (A.Num() == 2) KeysOut.Add(FVector2D(A[0]->AsNumber(), A[1]->AsNumber()));
				}
			}
		};
		Keys(TEXT("tactical"), D.BoltReloadTactical);
		Keys(TEXT("empty"), D.BoltReloadEmpty);

		if (const TSharedPtr<FJsonValue> Reload = C.Value(W + TEXT("reload")); Reload.IsValid() && Reload->Type == EJson::Object)
		{
			for (const auto& Pair : Reload->AsObject()->Values)
			{
				if (Pair.Value->Type == EJson::Number)
				{
					D.ReloadMarks.Add(FName(*Pair.Key), Pair.Value->AsNumber());
				}
			}
		}
		D.ReloadTactical = C.Num(W + TEXT("reload.tactical"));
		D.ReloadEmpty = C.Num(W + TEXT("reload.empty"));
		D.bAuto = C.Bool(W + TEXT("auto"));
		D.KickBack = C.Num(W + TEXT("kick.back"));
		D.KickRise = C.Num(W + TEXT("kick.rise"));
		D.KickYaw = C.Num(W + TEXT("kick.yaw"));
		D.KickRoll = C.Num(W + TEXT("kick.roll"));
		D.KickUp = C.Num(W + TEXT("kick.up"));
		D.KickSide = C.Num(W + TEXT("kick.side"));
		D.KickFirst = C.Num(W + TEXT("kick.firstShot"));
		D.KickSecond = C.Num(W + TEXT("kick.secondShot"));
		D.KickRandom = C.Num(W + TEXT("kick.random"));
		D.KickCrouch = C.Num(W + TEXT("kick.crouch"));
		D.KickAdsBack = C.Num(W + TEXT("kick.ads.back"));
		D.KickAdsRot = C.Num(W + TEXT("kick.ads.rot"));
		D.KickAdsPos = C.Num(W + TEXT("kick.ads.pos"));
		D.SpringBack = C.Pair(W + TEXT("kick.springs.back"));
		D.SpringPitch = C.Pair(W + TEXT("kick.springs.pitch"));
		D.SpringYaw = C.Pair(W + TEXT("kick.springs.yaw"));
		D.SpringRoll = C.Pair(W + TEXT("kick.springs.roll"));
		D.SpringPos = C.Pair(W + TEXT("kick.springs.pos"));
		D.AdsSpring = C.Pair(W + TEXT("adsSpring"));
		D.SwaySpring = C.Pair(W + TEXT("swaySpring"));
		D.SwayMax = C.Num(W + TEXT("swayMax"));
	}

	if (!P.Missing.IsEmpty() || !C.Missing.IsEmpty())
	{
		OutError = !P.Missing.IsEmpty() ? TEXT("presentation.json is missing ") + P.Missing : TEXT("config.json is missing ") + C.Missing;
		return false;
	}
	return true;
}

// -------------------------------------------------------------------------------------------------------------

void FMIViewmodelRig::Init(const FMIViewmodelData* InData)
{
	Data = InData;
	Gun = nullptr;
	if (Data && Data->Guns.Num() > 0)
	{
		Equip(Data->Guns[0].Id);
	}
	Reset();
}

void FMIViewmodelRig::Equip(FName Id)
{
	const FMIGunViewData* Next = Data ? Data->Find(Id) : nullptr;
	if (!Next)
	{
		return;
	}
	Gun = Next;
	// The rear sight on the view axis, the eye its relief behind it (viewmodel.js show()).
	const FVector Sight = Gun->Marker(TEXT("sightRear"));
	AdsPose.Pos = FVector(-Sight.X, -Sight.Y, -Gun->Relief - Sight.Z);
	AdsPose.Rot = FQuat::Identity;
	bSlideLocked = false;
	SlideCloseT = -1.0;
	BoltTime = 1e30;
}

void FMIViewmodelRig::OverrideMarker(FName Marker, const FVector& WebGunSpace)
{
	if (FMIGunViewData* G = const_cast<FMIGunViewData*>(Gun))
	{
		G->Markers.Add(Marker, WebGunSpace);
		if (Marker == TEXT("sightRear"))
		{
			Equip(G->Id);
		}
	}
}

void FMIViewmodelRig::Reset()
{
	for (FMIExactSpring* S : {&Aim, &SwayYaw, &SwayPitch, &Land, &BumpY, &BumpPitch, &BumpRoll, &RecBack, &RecPitch, &RecYaw, &RecRoll, &RecSide, &RecUp})
	{
		S->Reset();
	}
	Clock = 0.0;
	ShotAge = 1e30;
	LastAdsLinear = 0.0;
	ReloadWeight = 0.0;
	LastReloadT = 0.0;
	BobPhase = BobAmp = 0.0;
	DropT = 0.0;
	LastVel = FVector2D::ZeroVector;
	InertiaX = InertiaZ = InertiaLean = InertiaFall = 0.0;
	TriggerX = 0.0;
	BoltTime = 1e30;
	bSlideLocked = false;
	SlideCloseT = -1.0;
	Parts = FMIGunParts();
	if (Gun && Gun->Hip.Num() > 0)
	{
		Pose = Gun->Hip[0];
	}
}

void FMIViewmodelRig::BlendTo(const FMIViewPose& Target, double K)
{
	if (K <= 0.0)
	{
		return;
	}
	Pose.Pos = FMath::Lerp(Pose.Pos, Target.Pos, K);
	Pose.Rot = FQuat::Slerp(Pose.Rot, Target.Rot, K);
}

void FMIViewmodelRig::TurnAboutPivot(const FQuat& Q)
{
	const FVector Pivot = Pose.Rot.RotateVector(Gun->Marker(TEXT("pivot"))) + Pose.Pos;
	Pose.Pos = Q.RotateVector(Pose.Pos - Pivot) + Pivot;
	Pose.Rot = Q * Pose.Rot;
}

void FMIViewmodelRig::OnFire(int32 Burst, bool bCrouching, double Ads, bool bEmptied)
{
	if (!Gun)
	{
		return;
	}
	using namespace MIViewmodelPrivate;
	const FMIGunViewData& K = *Gun;
	const double First = Burst == 1 ? K.KickFirst : Burst == 2 ? K.KickSecond : 1.0;
	const double C = bCrouching ? K.KickCrouch : 1.0;
	const auto Vary = [&K, C]() { return (1.0 + Signed() * K.KickRandom) * C; };
	const double Back = FMath::Lerp(1.0, K.KickAdsBack, Ads);
	const double Rot = FMath::Lerp(1.0, K.KickAdsRot, Ads);
	const double Shift = FMath::Lerp(1.0, K.KickAdsPos, Ads);
	RecBack.V += K.KickBack * First * Vary() * Back;
	RecPitch.V += K.KickRise * First * Vary() * Rot;
	RecYaw.V += Signed() * K.KickYaw * Vary() * Rot;
	RecRoll.V += Signed() * K.KickRoll * Vary() * Rot;
	RecUp.V += K.KickUp * Vary() * Shift;
	RecSide.V += Signed() * K.KickSide * Vary() * Shift;
	ShotAge = 0.0;
	BoltTime = 0.0;
	if (bEmptied && K.Bolt.bLockOnEmpty)
	{
		bSlideLocked = true;  // stays back once it has travelled
	}
}

void FMIViewmodelRig::OnDry()
{
	if (Data)
	{
		BumpPitch.V += Data->Feel.DryPitch;
		BumpY.V += Data->Feel.DryY;
	}
}

void FMIViewmodelRig::OnReloadPhase(FName Phase, bool bEmpty)
{
	if (!Data || !Gun)
	{
		return;
	}
	const FMIViewFeelData& F = Data->Feel;
	if (Phase == TEXT("magout"))
	{
		BumpY.V += F.MagOutY;
		BumpRoll.V += F.MagOutRoll;
	}
	else if (Phase == TEXT("magin"))
	{
		BumpY.V += F.MagInY;
		BumpPitch.V += F.MagInPitch;
	}
	else if (Phase == TEXT("bolt"))
	{
		if (Gun->bAuto)
		{
			RecBack.V += bEmpty ? 0.5 : 0.2;
		}
		else
		{
			RecPitch.V += 2.4;
			RecBack.V -= 0.25;
			SlideCloseT = 0.0;  // the slide stop is thumbed: the slide runs home
		}
	}
	else if (Phase == TEXT("cancel"))
	{
		LastReloadT = 0.0;
	}
}

void FMIViewmodelRig::OnMeleeLand(bool bEnemy, bool bSolid)
{
	if (Data && bSolid)
	{
		RecBack.V += bEnemy ? Data->Feel.MeleeEnemy : Data->Feel.MeleeWall;
		BumpRoll.V += Data->Feel.MeleeRoll;
	}
}

void FMIViewmodelRig::OnJump()
{
	if (Data)
	{
		Land.V += Data->Feel.Jump;
	}
}

void FMIViewmodelRig::OnLand(double SpeedCmPerS)
{
	if (Data)
	{
		Land.V -= FMath::Min(SpeedCmPerS / 100.0, Data->Feel.LandMax) * Data->Feel.LandPerSpeed;
		LandRollSign = -LandRollSign;
	}
}

void FMIViewmodelRig::Update(double Dt, const FMIWeaponView& Weapon, double AdsLinear, bool bDropped, const FMIViewmodelPlayer& Player)
{
	using namespace MIViewmodelPrivate;
	if (!Data || !(Dt > 0.0))
	{
		return;
	}
	if (Weapon.Weapon != GetGun() && !bDropped)
	{
		Equip(Weapon.Weapon);
	}
	if (!Gun)
	{
		return;
	}
	const FMIViewFeelData& F = Data->Feel;
	const FMIGunViewData& G = *Gun;
	Clock += Dt;
	ShotAge += Dt;
	const double A = MI::Clamp01(Weapon.Ads);
	const double Calm = 1.0 - A;

	// The aim spring chases the direction the linear aim is moving in.
	double AimTarget;
	if (AdsLinear > LastAdsLinear) AimTarget = 1.0;
	else if (AdsLinear < LastAdsLinear) AimTarget = 0.0;
	else AimTarget = AdsLinear >= 0.5 ? 1.0 : 0.0;
	LastAdsLinear = AdsLinear;
	Aim.Step(AimTarget, G.AdsSpring.X, G.AdsSpring.Y, Dt);
	const double Aimed = MI::Clamp01(Aim.X);

	const bool bReloading = Weapon.Activity == EMIWeaponActivity::Reloading;
	if (bReloading)
	{
		const double Total = Weapon.bReloadEmpty ? G.ReloadEmpty : G.ReloadTactical;
		const double T = Weapon.ActivityTime;
		ReloadWeight = FMath::Min(Ease(T / F.ReloadIn), Ease((Total - T) / F.ReloadOut));
		const auto Crossed = [this, T, &G](const TCHAR* Mark)
		{
			const double* M = G.ReloadMarks.Find(FName(Mark));
			return M && LastReloadT < *M && T >= *M;
		};
		if (Crossed(TEXT("magInsert"))) BumpY.V += F.MagInsertY;
		if (Crossed(TEXT("tug")))
		{
			BumpY.V += F.TugY;
			BumpPitch.V += F.TugPitch;
		}
		if (Crossed(TEXT("boltRelease")) && Weapon.bReloadEmpty)
		{
			RecBack.V -= 0.5;
			BumpPitch.V -= 0.9;
		}
		LastReloadT = T;
	}
	else
	{
		ReloadWeight = MI::Damp(ReloadWeight, 0.0, F.ReloadCancelRate, Dt);
		LastReloadT = 0.0;
	}

	// Layer 1: the base pose.
	Pose = G.Hip[0];
	BlendTo(G.Sprint, Weapon.SprintBlend);
	BlendTo(G.Reload, ReloadWeight);
	BlendTo(G.Wall, Weapon.Wall);
	BlendTo(AdsPose, Aimed);
	const double SwitchK = Weapon.ActivityLength > 0.0 ? MI::Clamp01(Weapon.ActivityTime / Weapon.ActivityLength) : 0.0;
	if (Weapon.Activity == EMIWeaponActivity::Holstering)
	{
		BlendTo(G.Holster, Ease(SwitchK));
	}
	else if (Weapon.Activity == EMIWeaponActivity::Drawing)
	{
		BlendTo(G.Holster, 1.0 - EaseOutBack(SwitchK));
	}
	else if (bDropped)
	{
		DropT += Dt;
		BlendTo(G.Holster, Ease(DropT / F.DropTime));
	}
	if (!bDropped)
	{
		DropT = 0.0;
	}

	// Layer 2: the strike.
	if (Weapon.Activity == EMIWeaponActivity::Striking && G.Melee.Num() >= 2)
	{
		const double T = Weapon.ActivityTime;
		int32 I = 0;
		while (I < G.Melee.Num() - 2 && T >= G.Melee[I + 1][0]) ++I;
		const TArray<double>& KA = G.Melee[I];
		const TArray<double>& KB = G.Melee[I + 1];
		const double K = Ease((T - KA[0]) / FMath::Max(1e-6, KB[0] - KA[0]));
		double S[6];
		for (int32 C = 0; C < 6; ++C) S[C] = KA[C + 1] + (KB[C + 1] - KA[C + 1]) * K;
		Pose.Pos += FVector(S[0], S[1], S[2]);
		TurnAboutPivot(EulerYXZ(S[3], S[4], S[5]));
	}

	// Layer 3: additive motion.
	const double Speed = Player.Speed / 100.0;
	const double Stride = Player.bCrouching ? Data->StrideCrouch : Player.bSprinting ? Data->StrideSprint : Data->StrideWalk;
	if (Player.bOnGround && Speed > F.BobMoving && Stride > 0.0)
	{
		BobPhase += Speed * Dt / Stride;
	}
	const double Gait = !Player.bOnGround ? 0.0 : FMath::Pow(Speed / F.BobWalkSpeed, F.BobExponent) * (Player.bCrouching ? F.BobCrouch : 1.0);
	BobAmp = MI::Damp(BobAmp, Gait, F.BobRate, Dt);
	const double Run = Weapon.SprintBlend;
	const double PosScale = FMath::Lerp(1.0, F.BobAdsPos, A) * BobAmp;
	const double RotScale = FMath::Lerp(1.0, F.BobAdsRot, A) * BobAmp;
	const double Step = FMath::Sin(BobPhase * UE_DOUBLE_PI);
	const double Bounce = FMath::Cos(BobPhase * UE_DOUBLE_PI * 2.0);
	double OffX = Step * FMath::Lerp(F.BobX.X, F.BobX.Y, Run) * PosScale;
	double OffY = -Bounce * FMath::Lerp(F.BobY.X, F.BobY.Y, Run) * PosScale;
	double OffZ = 0.0;
	double Pitch = Bounce * FMath::Lerp(F.BobPitch.X, F.BobPitch.Y, Run) * RotScale;
	double Yaw = 0.0;
	double Roll = Step * FMath::Lerp(F.BobRoll.X, F.BobRoll.Y, Run) * RotScale;

	const double Breath = Clock * F.BreatheHz * UE_DOUBLE_PI * 2.0;
	const double Still = FMath::Lerp(1.0, 0.18, A);
	OffY += FMath::Sin(Breath) * F.BreatheY * Still;
	Pitch += FMath::Sin(Breath + 1.1) * F.BreathePitch * Still;
	Roll += FMath::Sin(Breath * 0.5 + 0.4) * F.BreatheRoll * Still;

	// Look lag: the frame's look delta (radians) into two springs through a soft limit.
	const double LagScale = FMath::Lerp(1.0, F.LagAds, A);
	SwayYaw.X = SoftLimit(SwayYaw.X + MI::DegToRad(Player.LookDelta.X) * F.LagGain, G.SwayMax);
	SwayPitch.X = SoftLimit(SwayPitch.X + MI::DegToRad(Player.LookDelta.Y) * F.LagGain, G.SwayMax);
	SwayYaw.Step(0.0, G.SwaySpring.X, G.SwaySpring.Y, Dt);
	SwayPitch.Step(0.0, G.SwaySpring.X, G.SwaySpring.Y, Dt);
	Yaw += SwayYaw.X * LagScale;
	Pitch += SwayPitch.X * LagScale;
	Roll += SwayYaw.X * F.LagRoll * LagScale;
	OffX -= SwayYaw.X * F.LagShift * LagScale;

	// Movement inertia: acceleration pushes the gun the other way, strafing leans it, falling floats it.
	const double YawRad = MI::DegToRad(Player.Yaw);
	const FVector2D Fwd(FMath::Cos(YawRad), FMath::Sin(YawRad));
	const FVector2D Right(-FMath::Sin(YawRad), FMath::Cos(YawRad));
	const double VX = (Player.Velocity.X * Right.X + Player.Velocity.Y * Right.Y) / 100.0;
	const double VZ = (Player.Velocity.X * Fwd.X + Player.Velocity.Y * Fwd.Y) / 100.0;
	const double AX = (VX - LastVel.X) / Dt;
	const double AZ = (VZ - LastVel.Y) / Dt;
	LastVel = FVector2D(VX, VZ);
	const double Lim = F.InertiaAccelLimit;
	InertiaX = MI::Damp(InertiaX, FMath::Clamp(AX, -Lim, Lim) / Lim, F.InertiaRate, Dt);
	InertiaZ = MI::Damp(InertiaZ, FMath::Clamp(AZ, -Lim, Lim) / Lim, F.InertiaRate, Dt);
	InertiaLean = MI::Damp(InertiaLean, FMath::Clamp(VX / F.InertiaLeanSpeed, -1.0, 1.0), F.InertiaRate, Dt);
	InertiaFall = MI::Damp(InertiaFall, !Player.bOnGround ? FMath::Clamp(Player.Velocity.Z / 100.0, F.InertiaFallClamp.X, F.InertiaFallClamp.Y) : 0.0, F.InertiaRate, Dt);
	const double Drift = FMath::Lerp(1.0, F.InertiaAds, A);
	OffX -= InertiaX * F.InertiaStrafe * Drift;
	OffZ += InertiaZ * F.InertiaSurge * Drift;
	Roll -= InertiaLean * F.InertiaLean * Drift;
	OffY -= InertiaFall * F.InertiaFall * Drift;
	Pitch += InertiaFall * F.InertiaFallPitch * Drift;

	// Jump and landing.
	Land.Step(0.0, F.LandSpring.X, F.LandSpring.Y, Dt);
	OffY += Land.X * FMath::Lerp(1.0, F.LandAdsY, A);
	Pitch += Land.X * F.LandPitch * FMath::Lerp(1.0, F.LandAdsPitch, A);
	Roll += Land.X * F.LandRoll * LandRollSign * Calm;

	// Bumps (dry click, magazine marks).
	BumpY.Step(0.0, F.BumpSpring.X, F.BumpSpring.Y, Dt);
	BumpPitch.Step(0.0, F.BumpSpring.X, F.BumpSpring.Y, Dt);
	BumpRoll.Step(0.0, F.BumpSpring.X, F.BumpSpring.Y, Dt);
	OffY += BumpY.X;
	Pitch += BumpPitch.X;
	Roll += BumpRoll.X;

	// The aim arc: a dip and a cant half way into the sights.
	const double Arc = FMath::Sin(Aimed * UE_DOUBLE_PI);
	OffY -= Arc * F.AimArcDrop;
	Roll += Arc * F.AimArcRoll;

	// Layer 4: the six recoil springs.
	RecBack.Step(0.0, G.SpringBack.X, G.SpringBack.Y, Dt);
	RecPitch.Step(0.0, G.SpringPitch.X, G.SpringPitch.Y, Dt);
	RecYaw.Step(0.0, G.SpringYaw.X, G.SpringYaw.Y, Dt);
	RecRoll.Step(0.0, G.SpringRoll.X, G.SpringRoll.Y, Dt);
	RecSide.Step(0.0, G.SpringPos.X, G.SpringPos.Y, Dt);
	RecUp.Step(0.0, G.SpringPos.X, G.SpringPos.Y, Dt);
	Pitch += RecPitch.X;
	Yaw += RecYaw.X;
	Roll += RecRoll.X;
	OffX += RecSide.X;
	OffY += RecUp.X;

	TurnAboutPivot(EulerYXZ(Pitch, Yaw, Roll));
	Pose.Pos += FVector(OffX, OffY, OffZ);
	Pose.Pos += Pose.Rot.RotateVector(FVector(0, 0, 1)) * RecBack.X;  // straight back along the bore

	UpdateParts(Dt, Weapon);
}

void FMIViewmodelRig::UpdateParts(double Dt, const FMIWeaponView& Weapon)
{
	using namespace MIViewmodelPrivate;
	const FMIGunViewData& G = *Gun;
	const FMIViewFeelData& F = Data->Feel;

	// Trigger: follows "held and allowed to fire".
	TriggerX = MI::Damp(TriggerX, Weapon.bTrigger ? 1.0 : 0.0, F.TriggerRate, Dt);
	Parts.Trigger = TriggerX;

	// Bolt or slide: back in Back seconds, home in Forward seconds after every round.
	BoltTime += Dt;
	double Bolt = 0.0;
	if (BoltTime < G.Bolt.Back)
	{
		Bolt = BoltTime / FMath::Max(1e-6, G.Bolt.Back);
	}
	else if (BoltTime < G.Bolt.Back + G.Bolt.Forward)
	{
		Bolt = bSlideLocked ? 1.0 : 1.0 - Ease((BoltTime - G.Bolt.Back) / FMath::Max(1e-6, G.Bolt.Forward));
	}
	else if (bSlideLocked)
	{
		Bolt = 1.0;
	}
	if (bSlideLocked && SlideCloseT >= 0.0)
	{
		SlideCloseT += Dt;
		Bolt = 1.0 - MI::Clamp01(SlideCloseT / FMath::Max(1e-6, G.Bolt.Release));
		if (SlideCloseT >= G.Bolt.Release)
		{
			bSlideLocked = false;
			SlideCloseT = -1.0;
		}
	}
	if (bSlideLocked && Weapon.Mag > 0 && Weapon.Activity != EMIWeaponActivity::Reloading)
	{
		bSlideLocked = false;  // a cancelled empty reload, a reset: the slide is not left hanging
	}
	// The charging handle in the CHOPPER's reload.
	if (Weapon.Activity == EMIWeaponActivity::Reloading)
	{
		Bolt = FMath::Max(Bolt, SampleKeys(Weapon.bReloadEmpty ? G.BoltReloadEmpty : G.BoltReloadTactical, Weapon.ActivityTime));
	}
	Parts.Bolt = Bolt;
	Parts.bSlideLocked = bSlideLocked;
	Parts.Barrel = G.Barrel.Share > 0.0 ? MI::Clamp01(Bolt / G.Barrel.Share) : 0.0;

	// Magazine: drops at its out mark, hidden until the show mark, rises home by the in mark.
	Parts.Magazine = 0.0;
	Parts.bMagazineVisible = true;
	if (Weapon.Activity == EMIWeaponActivity::Reloading)
	{
		const double* Out = G.ReloadMarks.Find(G.Magazine.OutMark);
		const double* Show = G.ReloadMarks.Find(G.Magazine.ShowMark);
		const double* In = G.ReloadMarks.Find(G.Magazine.InMark);
		const double T = Weapon.ActivityTime;
		if (Out && Show && In)
		{
			if (T >= *Out && T < *Show)
			{
				const double K = MI::Clamp01((T - *Out) / FMath::Max(1e-3, (*Show - *Out) * 0.5));
				Parts.Magazine = Ease(K);
				Parts.bMagazineVisible = K < 1.0;
			}
			else if (T >= *Show && T < *In)
			{
				Parts.Magazine = 1.0 - Ease((T - *Show) / FMath::Max(1e-3, *In - *Show));
			}
		}
	}
}

FTransform FMIViewmodelRig::GetGunTransform() const
{
	return FTransform(WebToUE(Pose.Rot), WebToUE(Pose.Pos));
}

FVector FMIViewmodelRig::GunPointInCamera(const FVector& WebGunPoint) const
{
	return WebToUE(Pose.Pos + Pose.Rot.RotateVector(WebGunPoint));
}
