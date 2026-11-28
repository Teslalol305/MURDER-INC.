#pragma once

#include "CoreMinimal.h"

/**
 * The game's half of the IPX page bridge (docs/unreal/maps/progression.md 4.4, tools/ipx-bridge/).
 *
 * Page -> game: E3DS's player turns {cmd: 'sendToUe4', value: {...}} into a Pixel Streaming UIInteraction message. The
 * descriptor is read here, checked, and handed to OnReceived; the maps branch's progress store merges it (4.5).
 * Game -> page: SendToPage sends the same JSON as a Pixel Streaming "Response" message to the one controlling viewer
 * (never to every viewer: the code is the player's own, and a spectator must not get it).
 *
 * Message: {"mi":"progress","v":1,"code":"4FMY-N7W6","hold":{"block":12345,"chinatown":0,"midtown":0}}, at most 256
 * UTF-16 units. Nothing here opens the console allowlist or touches a rule of play.
 */
struct MURDERINC_API FMIProgressMessage
{
	/** Canonical 'XXXX-XXXX'. */
	FString Code;
	/** Hold the Block bests: block, chinatown, midtown, each 0..99,999,999. */
	int32 Hold[3] = { 0, 0, 0 };
};

class MURDERINC_API FMIProgressBridge
{
public:
	static constexpr int32 MaxUnits = 256;
	static constexpr int32 MaxHold = 99999999;

	/**
	 * Checks a progress code (progression.md 4.3, format v1): 8 upper-case Crockford base32 characters with an
	 * optional hyphen after the fourth, CRC-16/CCITT-FALSE over "MURDERINC-PROGRESS-1" + the 3 payload bytes, version
	 * 1, reserved bits 0, cleared bits agreeing with points and difficulty, cleared levels a prefix, the album bit
	 * needing all three. Returns the canonical form, or an empty string. (The maps branch's own decoder is the same
	 * rule; when it lands, CheckCode should call it.)
	 */
	static FString CheckCode(const FString& Input);

	/** A descriptor (JSON text) -> a message. False and Out untouched when anything is wrong. */
	static bool ParseDescriptor(const FString& Descriptor, FMIProgressMessage& Out);

	/** The raw UIInteraction message (a 16-bit count of UTF-16 units, then the units, little-endian) -> a message. */
	static bool ParseUIBytes(const TArray<uint8>& Message, FMIProgressMessage& Out);

	/** The JSON a message is sent as. */
	static FString BuildJson(const FMIProgressMessage& Message);

	/** Called on the game thread with a good message from the controlling viewer. The progress store merges it (4.5). */
	DECLARE_MULTICAST_DELEGATE_OneParam(FOnReceived, const FMIProgressMessage&);
	static FOnReceived& OnReceived();

	/** Returns the progress to tell the page: false when the game has nothing to say yet. The progress store sets it. */
	DECLARE_DELEGATE_RetVal_OneParam(bool, FProvider, FMIProgressMessage&);
	static FProvider& Provider();

	/** Says whether a viewer id is the controlling (elevated) viewer. Set once by MICloud next to the handlers. */
	static void SetControllerCheck(TFunction<bool(const FString&)> Check);

	/**
	 * The stream's UIInteraction hook. It runs on the stream's own thread, not the game thread. True when the message
	 * was a well-formed progress message (then it is not passed on, whoever sent it). Only when bController is true is
	 * it published: OnReceived is broadcast on the game thread (AsyncTask), then the current progress is sent back to
	 * the sender, so the page learns the game has merged its value.
	 */
	static bool OnPageMessage(const FString& SourceId, const TArray<uint8>& Message, bool bController);

	/** Sends the message to ONE viewer as a Pixel Streaming Response. False when there is no stream or no viewer. Game thread. */
	static bool SendToPage(const FMIProgressMessage& Message, const FString& PlayerId);

	/** Call after every change of progress (2.4): sends what the Provider says now to the controlling viewer. Game thread. */
	static void SendCurrent();

	/** A viewer joined: 1 s later (the data channel needs that long) the current progress goes to that viewer, if it is the controller. */
	static void ScheduleHello(const FString& PlayerId);
};
