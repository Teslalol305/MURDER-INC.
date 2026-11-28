#include "Cloud/MIProgressBridge.h"

#include "Async/Async.h"
#include "Containers/Ticker.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "MurderInc.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

#if MI_WITH_PIXELSTREAMING2
#include "IPixelStreaming2Module.h"
#include "IPixelStreaming2Streamer.h"
#endif

namespace
{
	const TCHAR* const Alphabet = TEXT("0123456789ABCDEFGHJKMNPQRSTVWXYZ");

	uint16 Crc16(const TArray<uint8>& Bytes)
	{
		uint32 Crc = 0xFFFF;
		for (const uint8 B : Bytes)
		{
			Crc ^= (uint32)B << 8;
			for (int32 I = 0; I < 8; ++I)
			{
				Crc = (Crc & 0x8000) ? (((Crc << 1) ^ 0x1021) & 0xFFFF) : ((Crc << 1) & 0xFFFF);
			}
		}
		return (uint16)Crc;
	}

	bool ReadHold(const TSharedPtr<FJsonObject>& Hold, const TCHAR* Key, int32& Out)
	{
		Out = 0;
		if (!Hold.IsValid() || !Hold->HasField(Key))
		{
			return true;  // a missing level is zero
		}
		double V = 0.0;
		if (!Hold->TryGetNumberField(Key, V) || !FMath::IsFinite(V) || V != FMath::FloorToDouble(V) || V < 0.0 || V > (double)FMIProgressBridge::MaxHold)
		{
			return false;
		}
		Out = (int32)V;
		return true;
	}
}

FString FMIProgressBridge::CheckCode(const FString& Input)
{
	FString S = Input;
	if (S.Len() == 9 && S[4] == TEXT('-'))
	{
		S = S.Left(4) + S.Mid(5);
	}
	if (S.Len() != 8)
	{
		return FString();
	}
	uint64 Big = 0;
	const FString Letters(Alphabet);
	for (int32 I = 0; I < 8; ++I)
	{
		int32 Index = INDEX_NONE;
		if (!Letters.FindChar(S[I], Index))
		{
			return FString();
		}
		Big = Big * 32 + (uint64)Index;
	}
	const uint32 Payload = (uint32)(Big >> 16);
	const uint32 Check = (uint32)(Big & 0xFFFF);
	TArray<uint8> Bytes;
	const FString Salt = TEXT("MURDERINC-PROGRESS-1");
	for (int32 I = 0; I < Salt.Len(); ++I)
	{
		Bytes.Add((uint8)Salt[I]);
	}
	Bytes.Add((uint8)((Payload >> 16) & 255));
	Bytes.Add((uint8)((Payload >> 8) & 255));
	Bytes.Add((uint8)(Payload & 255));
	if (Crc16(Bytes) != Check || ((Payload >> 21) & 7) != 1 || ((Payload >> 19) & 3) != 0)
	{
		return FString();
	}
	const uint32 Mask = (Payload >> 16) & 7;
	bool bPrev = true, bAll = true;
	for (int32 L = 0; L < 3; ++L)
	{
		const bool bCleared = ((Mask >> L) & 1) != 0;
		const uint32 Points = (Payload >> (7 + 3 * L)) & 7;
		const uint32 Diff = (Payload >> (1 + 2 * L)) & 3;
		if (Points == 6 || bCleared != (Points != 7) || bCleared != (Diff != 3) || (bCleared && !bPrev))
		{
			return FString();
		}
		bPrev = bCleared;
		bAll = bAll && bCleared;
	}
	if ((Payload & 1) != 0 && !bAll)
	{
		return FString();
	}
	return S.Left(4) + TEXT("-") + S.Mid(4);
}

bool FMIProgressBridge::ParseDescriptor(const FString& Descriptor, FMIProgressMessage& Out)
{
	if (Descriptor.Len() <= 0 || Descriptor.Len() > MaxUnits || !Descriptor.Contains(TEXT("progress")))
	{
		return false;
	}
	TSharedPtr<FJsonObject> Json;
	if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Descriptor), Json) || !Json.IsValid())
	{
		return false;
	}
	FString Mi, Code;
	double Version = 0.0;
	if (!Json->TryGetStringField(TEXT("mi"), Mi) || Mi != TEXT("progress") || !Json->TryGetNumberField(TEXT("v"), Version) || Version != 1.0
		|| !Json->TryGetStringField(TEXT("code"), Code))
	{
		return false;
	}
	FMIProgressMessage M;
	M.Code = CheckCode(Code);
	if (M.Code.IsEmpty())
	{
		return false;
	}
	TSharedPtr<FJsonObject> Hold;
	if (Json->HasField(TEXT("hold")))
	{
		const TSharedPtr<FJsonObject>* HoldPtr = nullptr;
		if (!Json->TryGetObjectField(TEXT("hold"), HoldPtr) || !HoldPtr)
		{
			return false;
		}
		Hold = *HoldPtr;
	}
	if (!ReadHold(Hold, TEXT("block"), M.Hold[0]) || !ReadHold(Hold, TEXT("chinatown"), M.Hold[1]) || !ReadHold(Hold, TEXT("midtown"), M.Hold[2]))
	{
		return false;
	}
	Out = M;
	return true;
}

bool FMIProgressBridge::ParseUIBytes(const TArray<uint8>& Message, FMIProgressMessage& Out)
{
	const int32 Units = Message.Num() >= 2 ? (int32)(Message[0] | (Message[1] << 8)) : 0;
	if (Units <= 0 || Units > MaxUnits || Message.Num() < 2 + 2 * Units)
	{
		return false;
	}
	FString Descriptor;
	Descriptor.Reserve(Units);
	for (int32 I = 0; I < Units; ++I)
	{
		Descriptor.AppendChar((TCHAR)(Message[2 + 2 * I] | (Message[3 + 2 * I] << 8)));
	}
	// A page that stringifies its value twice sends a JSON string holding the JSON: read through one level.
	if (Descriptor.StartsWith(TEXT("\"")))
	{
		TSharedPtr<FJsonValue> Value;
		FString Inner;
		if (FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Descriptor), Value) && Value.IsValid() && Value->TryGetString(Inner))
		{
			Descriptor = Inner;
		}
	}
	return ParseDescriptor(Descriptor, Out);
}

FString FMIProgressBridge::BuildJson(const FMIProgressMessage& Message)
{
	FString Out;
	const TSharedRef<TJsonWriter<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>> W = TJsonWriterFactory<TCHAR, TCondensedJsonPrintPolicy<TCHAR>>::Create(&Out);
	W->WriteObjectStart();
	W->WriteValue(TEXT("mi"), TEXT("progress"));
	W->WriteValue(TEXT("v"), 1);
	W->WriteValue(TEXT("code"), Message.Code);
	W->WriteObjectStart(TEXT("hold"));
	W->WriteValue(TEXT("block"), FMath::Clamp(Message.Hold[0], 0, MaxHold));
	W->WriteValue(TEXT("chinatown"), FMath::Clamp(Message.Hold[1], 0, MaxHold));
	W->WriteValue(TEXT("midtown"), FMath::Clamp(Message.Hold[2], 0, MaxHold));
	W->WriteObjectEnd();
	W->WriteObjectEnd();
	W->Close();
	return Out;
}

FMIProgressBridge::FOnReceived& FMIProgressBridge::OnReceived()
{
	static FOnReceived D;
	return D;
}

namespace
{
	// Touched on the game thread only.
	TFunction<bool(const FString&)> GControllerCheck;
	FString GControllerId;
}

void FMIProgressBridge::SetControllerCheck(TFunction<bool(const FString&)> Check)
{
	GControllerCheck = MoveTemp(Check);
}

FMIProgressBridge::FProvider& FMIProgressBridge::Provider()
{
	static FProvider P;
	return P;
}

bool FMIProgressBridge::OnPageMessage(const FString& SourceId, const TArray<uint8>& Message, bool bController)
{
	FMIProgressMessage M;
	if (!ParseUIBytes(Message, M))
	{
		return false;  // most UIInteraction messages are not ours (the away word)
	}
	if (bController && !SourceId.IsEmpty())
	{
		// The stream calls this on its own thread; the store and the Pixel Streaming sender are used on the game thread.
		AsyncTask(ENamedThreads::GameThread, [M, SourceId]()
		{
			GControllerId = SourceId;
			OnReceived().Broadcast(M);
			SendCurrent();  // the answer that tells the page the game has merged its value
		});
	}
	return true;
}

bool FMIProgressBridge::SendToPage(const FMIProgressMessage& Message, const FString& PlayerId)
{
#if MI_WITH_PIXELSTREAMING2
	if (PlayerId.IsEmpty() || !IPixelStreaming2Module::IsAvailable())
	{
		return false;
	}
	IPixelStreaming2Module& Module = IPixelStreaming2Module::Get();
	if (!Module.IsReady())
	{
		return false;
	}
	const TSharedPtr<IPixelStreaming2Streamer> Streamer = Module.FindStreamer(Module.GetDefaultStreamerID());
	if (!Streamer.IsValid())
	{
		return false;
	}
	// A Pixel Streaming "Response" message to one player: the player's onResponse, which E3DS's page relays (README: check
	// once). The streamer call is written from memory of the PS2 interface: compile it first.
	Streamer->SendPlayerMessage(PlayerId, TEXT("Response"), BuildJson(Message));
	return true;
#else
	return false;
#endif
}

void FMIProgressBridge::SendCurrent()
{
	FMIProgressMessage M;
	if (GControllerId.IsEmpty() || !GControllerCheck || !GControllerCheck(GControllerId))
	{
		return;
	}
	if (Provider().IsBound() && Provider().Execute(M) && !CheckCode(M.Code).IsEmpty())
	{
		SendToPage(M, GControllerId);
	}
}

void FMIProgressBridge::ScheduleHello(const FString& PlayerId)
{
	FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([PlayerId](float)
	{
		if (GControllerCheck && GControllerCheck(PlayerId))
		{
			GControllerId = PlayerId;
			SendCurrent();
		}
		return false;  // once
	}), 1.0f);
}
