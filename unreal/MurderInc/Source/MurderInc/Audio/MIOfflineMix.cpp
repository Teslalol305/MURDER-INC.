#include "Audio/MIOfflineMix.h"

#include "Audio/MIAudioMaster.h"

#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace MIOfflinePrivate
{
	int32 Le16(const uint8* P) { return (int16)(P[0] | (P[1] << 8)); }
	uint32 Le32(const uint8* P) { return P[0] | (P[1] << 8) | (P[2] << 16) | ((uint32)P[3] << 24); }

}

// --------------------------------------------------------------------------------------------------------- WAV

float FMIWav::Peak() const
{
	float P = 0.f;
	for (const float S : Samples)
	{
		P = FMath::Max(P, FMath::Abs(S));
	}
	return P;
}

double FMIWav::Rms() const
{
	double E = 0.0;
	for (const float S : Samples)
	{
		E += double(S) * S;
	}
	return Samples.Num() ? FMath::Sqrt(E / Samples.Num()) : 0.0;
}

bool FMIWav::Parse(const TArray<uint8>& B, FMIWav& Out, FString* OutError)
{
	using namespace MIOfflinePrivate;
	auto Fail = [OutError](const TCHAR* Why) { if (OutError) { *OutError = Why; } return false; };
	if (B.Num() < 44 || FMemory::Memcmp(B.GetData(), "RIFF", 4) != 0 || FMemory::Memcmp(B.GetData() + 8, "WAVE", 4) != 0)
	{
		return Fail(TEXT("not a RIFF WAVE file"));
	}
	int32 Format = 0, Bits = 0;
	int64 Pos = 12;
	const uint8* DataPtr = nullptr;
	int64 DataSize = 0;
	while (Pos + 8 <= B.Num())
	{
		const uint8* C = B.GetData() + Pos;
		const int64 Size = Le32(C + 4);
		if (FMemory::Memcmp(C, "fmt ", 4) == 0 && Size >= 16)
		{
			Format = Le16(C + 8) & 0xFFFF;
			Out.Channels = Le16(C + 10);
			Out.Rate = (int32)Le32(C + 12);
			Bits = Le16(C + 22);
			if (Format == 0xFFFE && Size >= 40)
			{
				Format = Le16(C + 32) & 0xFFFF;  // the sub-format's first two bytes
			}
		}
		else if (FMemory::Memcmp(C, "data", 4) == 0)
		{
			DataPtr = C + 8;
			DataSize = FMath::Min<int64>(Size, B.Num() - Pos - 8);
		}
		Pos += 8 + Size + (Size & 1);
	}
	if (!DataPtr || Out.Channels <= 0 || Out.Rate <= 0)
	{
		return Fail(TEXT("no fmt or data chunk"));
	}
	const int32 Bytes = Bits / 8;
	if (Bytes <= 0)
	{
		return Fail(TEXT("bad bit depth"));
	}
	const int64 N = DataSize / Bytes;
	Out.Samples.SetNumUninitialized(N);
	for (int64 I = 0; I < N; ++I)
	{
		const uint8* P = DataPtr + I * Bytes;
		float V = 0.f;
		if (Format == 3 && Bits == 32)
		{
			uint32 U = Le32(P);
			FMemory::Memcpy(&V, &U, 4);
		}
		else if (Bits == 16)
		{
			V = Le16(P) / 32768.f;
		}
		else if (Bits == 24)
		{
			int32 S = P[0] | (P[1] << 8) | (P[2] << 16);
			if (S & 0x800000)
			{
				S |= ~0xFFFFFF;
			}
			V = S / 8388608.f;
		}
		else if (Bits == 32)
		{
			V = (int32)Le32(P) / 2147483648.f;
		}
		else if (Bits == 8)
		{
			V = (P[0] - 128) / 128.f;
		}
		Out.Samples[I] = V;
	}
	Out.Samples.SetNum(N - N % Out.Channels);
	return true;
}

bool FMIWav::Load(const FString& Path, FMIWav& Out, FString* OutError)
{
	TArray<uint8> Bytes;
	if (!FFileHelper::LoadFileToArray(Bytes, *Path, FILEREAD_Silent))
	{
		if (OutError)
		{
			*OutError = TEXT("cannot read ") + Path;
		}
		return false;
	}
	return Parse(Bytes, Out, OutError);
}

bool FMIWav::Save16(const FString& Path) const
{
	TArray<uint8> B;
	const int32 DataBytes = Samples.Num() * 2;
	B.SetNumZeroed(44 + DataBytes);
	auto W32 = [&B](int32 At, uint32 V) { B[At] = V & 255; B[At + 1] = (V >> 8) & 255; B[At + 2] = (V >> 16) & 255; B[At + 3] = (V >> 24) & 255; };
	auto W16 = [&B](int32 At, uint32 V) { B[At] = V & 255; B[At + 1] = (V >> 8) & 255; };
	FMemory::Memcpy(B.GetData(), "RIFF", 4);
	W32(4, 36 + DataBytes);
	FMemory::Memcpy(B.GetData() + 8, "WAVEfmt ", 8);
	W32(16, 16);
	W16(20, 1);
	W16(22, Channels);
	W32(24, Rate);
	W32(28, Rate * Channels * 2);
	W16(32, Channels * 2);
	W16(34, 16);
	FMemory::Memcpy(B.GetData() + 36, "data", 4);
	W32(40, DataBytes);
	for (int32 I = 0; I < Samples.Num(); ++I)
	{
		const int32 S = FMath::Clamp(FMath::RoundToInt(Samples[I] * 32767.f), -32768, 32767);
		W16(44 + I * 2, (uint32)(S & 0xFFFF));
	}
	return FFileHelper::SaveArrayToFile(B, *Path);
}

// --------------------------------------------------------------------------------------------------------- mix

void FMIOfflineMix::Begin(const FMIAudioData* InData, double Secs)
{
	Data = InData;
	if (Root.IsEmpty())
	{
		Root = FMIAudioData::AudioDir();
	}
	Out.Reset();
	Out.Reserve(int64(Secs * Rate) * 2 + 1024);
	Frame = 0;
	Voices.Reset();
	Queue.Reset();
	Started = 0;
	InitReverb();
	Master.Init(Data ? FMIMasterChain::FromData(*Data) : FMIMasterChain(), Rate);
}

const FMIWav* FMIOfflineMix::Get(const FString& File)
{
	if (const TSharedPtr<FMIWav>* W = Cache.Find(File))
	{
		return W->Get();
	}
	TSharedPtr<FMIWav> W = MakeShared<FMIWav>();
	if (!FMIWav::Load(FPaths::Combine(Root, File), *W))
	{
		Missing.Add(File);
		W.Reset();
	}
	Cache.Add(File, W);
	return W.Get();
}

double FMIOfflineMix::FileSecs(const FString& File)
{
	const FMIWav* W = Get(File);
	return W ? W->Secs() : 0.0;
}

void FMIOfflineMix::Apply(const TArray<FMIAudioCmd>& Cmds)
{
	Queue.Append(Cmds);
}

void FMIOfflineMix::Execute(const FMIAudioCmd& C)
{
	switch (C.Type)
	{
	case EMIAudioCmd::Start:
	{
		const FMIWav* W = Get(C.File);
		if (!W)
		{
			return;
		}
		FVoice V;
		V.Wav = W;
		V.Category = C.Category;
		V.Pitch = C.Pitch;
		V.Step = double(W->Rate) / Rate * C.Pitch;
		V.Volume = C.Volume;
		V.b3D = C.b3D;
		V.Where = C.Pos;
		V.Ref = C.Ref;
		V.Roll = C.Roll;
		V.bLoop = C.bLoop;
		V.StartFrame = Frame;
		Voices.Add(C.Id, V);
		++Started;
		break;
	}
	case EMIAudioCmd::Set:
		if (FVoice* V = Voices.Find(C.Id))
		{
			V->Volume = C.Volume;
			if (C.Pitch > 0.0)
			{
				V->Pitch = C.Pitch;
				V->Step = double(V->Wav->Rate) / Rate * C.Pitch;
			}
			if (C.b3D)
			{
				V->Where = C.Pos;
			}
		}
		break;
	case EMIAudioCmd::Stop:
		if (FVoice* V = Voices.Find(C.Id))
		{
			V->StopFrame = Frame;
			V->FadeFrames = FMath::Max(1.0, C.Fade * Rate);
		}
		break;
	}
}

void FMIOfflineMix::InitReverb()
{
	const int32 CombLen[4] = {1557, 1617, 1491, 1422};
	const int32 AllLen[2] = {556, 441};
	for (int32 Ch = 0; Ch < 2; ++Ch)
	{
		for (int32 I = 0; I < 4; ++I)
		{
			Combs[Ch][I].Buf.Init(0.f, int32((CombLen[I] + Ch * 23) * Rate / 44100.0));
			Combs[Ch][I].I = 0;
			Combs[Ch][I].Store = 0.f;
		}
		for (int32 I = 0; I < 2; ++I)
		{
			Alls[Ch][I].Buf.Init(0.f, int32((AllLen[I] + Ch * 23) * Rate / 44100.0));
			Alls[Ch][I].I = 0;
		}
	}
	bReverbReady = true;
}

float FMIOfflineMix::Reverb(int32 Ch, float In, float Decay)
{
	float Sum = 0.f;
	for (FComb& C : Combs[Ch])
	{
		const float Y = C.Buf[C.I];
		C.Store = Y * 0.75f + C.Store * 0.25f;  // damping
		C.Buf[C.I] = In + C.Store * Decay;
		C.I = (C.I + 1) % C.Buf.Num();
		Sum += Y;
	}
	for (FComb& A : Alls[Ch])
	{
		const float B = A.Buf[A.I];
		const float Y = -Sum + B;
		A.Buf[A.I] = Sum + B * 0.5f;
		A.I = (A.I + 1) % A.Buf.Num();
		Sum = Y;
	}
	return Sum * 0.25f;
}

void FMIOfflineMix::RenderTo(double T, const FMIMixState& Mix, const FVector& Listener, const FVector& Forward)
{
	using namespace MIOfflinePrivate;
	const int64 End = int64(T * Rate);
	if (End <= Frame)
	{
		return;
	}
	Queue.StableSort([](const FMIAudioCmd& A, const FMIAudioCmd& B) { return A.Time < B.Time; });
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Forward.GetSafeNormal2D()).GetSafeNormal();  // +Y for +X: Unreal's right

	// Reverb decay and return by zone.
	float Decay = 0.82f, Return = 0.22f;
	if (Mix.Reverb == TEXT("shop"))
	{
		Decay = 0.7f;
		Return = 0.3f;
	}
	else if (Mix.Reverb == TEXT("underEl"))
	{
		Decay = 0.76f;
		Return = 0.28f;
	}
	const double MuffleA = 1.0 - FMath::Exp(-2.0 * PI * Mix.MuffleCutoff / Rate);
	const double MusicA = 1.0 - FMath::Exp(-2.0 * PI * Mix.MusicCutoff / Rate);
	const double AmbienceA = 1.0 - FMath::Exp(-2.0 * PI * Mix.AmbienceCutoff / Rate);

	while (Frame < End)
	{
		// Commands due at this frame.
		while (Queue.Num() > 0 && int64(Queue[0].Time * Rate) <= Frame)
		{
			Execute(Queue[0]);
			Queue.RemoveAt(0);
		}
		const int64 BlockEnd = FMath::Min(End, Queue.Num() > 0 ? FMath::Max(Frame + 1, int64(Queue[0].Time * Rate)) : End);
		const int32 N = int32(BlockEnd - Frame);
		TArray<float> L, R, SendL, SendR;
		L.Init(0.f, N);
		R.Init(0.f, N);
		SendL.Init(0.f, N);
		SendR.Init(0.f, N);

		for (auto It = Voices.CreateIterator(); It; ++It)
		{
			FVoice& V = It->Value;
			const FMIAudioCategory* Cat = Data ? Data->Categories.Find(V.Category) : nullptr;
			const double CatGain = Mix.Gain.Contains(V.Category) ? Mix.Gain[V.Category] : 1.0;
			double Gain = V.Volume * CatGain;
			double PanL = 0.7071, PanR = 0.7071;
			double Cut = 20000.0;
			if (V.b3D)
			{
				const FVector D = V.Where - Listener;
				const double Dist = D.Size() / 100.0;
				Gain *= FMIAudioData::DistanceGain(Dist, V.Ref / 100.0, V.Roll);
				const double X = Dist > 0.01 ? FVector::DotProduct(D.GetSafeNormal(), Right) : 0.0;
				const double Angle = (X + 1.0) * 0.25 * PI;  // 0 left .. pi/2 right
				PanL = FMath::Cos(Angle);
				PanR = FMath::Sin(Angle);
				Cut = FMath::Clamp(20000.0 * FMath::Exp(-Dist / (Data ? Data->AirScale : 48.0)), Data ? Data->AirMin : 1600.0, 20000.0);
			}
			double A = Cut < 19999.0 ? 1.0 - FMath::Exp(-2.0 * PI * Cut / Rate) : 1.0;
			if (Cat && Cat->bMuffled)
			{
				A = FMath::Min(A, MuffleA);
			}
			if (V.Category == TEXT("music"))
			{
				A = FMath::Min(A, MusicA);
			}
			else if (V.Category == TEXT("ambience"))
			{
				A = FMath::Min(A, AmbienceA);
			}
			const double Send = Cat ? Cat->Reverb : 0.0;
			const double G0 = V.Gain, G1 = Gain;
			const int32 Frames = V.Wav->Frames();
			const int32 Chs = V.Wav->Channels;
			bool bDone = false;
			for (int32 I = 0; I < N; ++I)
			{
				const int64 F = Frame + I;
				double G = G0 + (G1 - G0) * (double(I + 1) / N);
				if (V.StopFrame >= 0)
				{
					const double U = double(F - V.StopFrame) / V.FadeFrames;
					if (U >= 1.0)
					{
						bDone = true;
						break;
					}
					G *= FMath::Exp(-3.0 * FMath::Max(0.0, U));
				}
				if (V.Pos >= Frames - 1)
				{
					if (!V.bLoop)
					{
						bDone = true;
						break;
					}
					V.Pos = FMath::Fmod(V.Pos, double(Frames - 1));
				}
				const int32 P0 = (int32)V.Pos;
				const float Fr = float(V.Pos - P0);
				const int32 P1 = FMath::Min(P0 + 1, Frames - 1);
				float SL = V.Wav->Samples[P0 * Chs] * (1.f - Fr) + V.Wav->Samples[P1 * Chs] * Fr;
				float SR = Chs > 1 ? V.Wav->Samples[P0 * Chs + 1] * (1.f - Fr) + V.Wav->Samples[P1 * Chs + 1] * Fr : SL;
				V.LpL += float(A) * (SL - V.LpL);
				V.LpR += float(A) * (SR - V.LpR);
				const float OL = V.LpL * float(G * (Chs > 1 && !V.b3D ? 1.0 : PanL * 1.4142));
				const float OR = V.LpR * float(G * (Chs > 1 && !V.b3D ? 1.0 : PanR * 1.4142));
				L[I] += OL;
				R[I] += OR;
				if (Send > 0.0)
				{
					SendL[I] += OL * float(Send);
					SendR[I] += OR * float(Send);
				}
				V.Pos += V.Step;
			}
			V.Gain = G1;
			if (bDone)
			{
				It.RemoveCurrent();
			}
		}

		// Reverb return (muffled with the effects), sum, the master chain (compressor, make-up, soft clip).
		for (int32 I = 0; I < N; ++I)
		{
			float WL = Reverb(0, SendL[I], Decay) * Return;
			float WR = Reverb(1, SendR[I], Decay) * Return;
			RevLp[0] += float(MuffleA) * (WL - RevLp[0]);
			RevLp[1] += float(MuffleA) * (WR - RevLp[1]);
			float OL = L[I] + RevLp[0], OR = R[I] + RevLp[1];
			Master.Process(OL, OR);
			Out.Add(OL);
			Out.Add(OR);
		}
		Frame = BlockEnd;
	}
}

bool FMIOfflineMix::Save(const FString& Path) const
{
	FMIWav W;
	W.Rate = Rate;
	W.Channels = 2;
	W.Samples = Out;
	return W.Save16(Path);
}

double FMIOfflineMix::PeakDb() const
{
	float P = 0.f;
	for (const float S : Out)
	{
		P = FMath::Max(P, FMath::Abs(S));
	}
	return P > 0.f ? 20.0 * FMath::LogX(10.0, P) : -200.0;
}
