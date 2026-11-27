#include "UI/MIStyle.h"

#include "Engine/Font.h"
#include "Fonts/CompositeFont.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "UObject/Package.h"

namespace MIStylePrivate
{
	FLinearColor Hex(const TCHAR* H) { return FLinearColor::FromSRGBColor(FColor::FromHex(H)); }

	/** The face file for a name: the project's own, else the engine's. Found once per name and kept: a screen rebuild asks for
	 *  a font several hundred times, and each ask was a file-system check (SMOOTH.md: 3 to 9 ms of the game thread on every
	 *  key press of the front end). */
	FString FontFile(const TCHAR* Name, const TCHAR* EngineFallback)
	{
		static FCriticalSection Lock;
		static TMap<FString, FString> Found;
		FScopeLock Guard(&Lock);
		if (const FString* Have = Found.Find(Name))
		{
			return *Have;
		}
		const FString Own = FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Fonts"), Name);
		FString Path = IFileManager::Get().FileExists(*Own) ? Own : FPaths::Combine(FPaths::EngineContentDir(), TEXT("Slate/Fonts"), EngineFallback);
		Found.Add(Name, Path);
		return Path;
	}

	UFont* MakeCanvasFont(const FString& File, int32 Size, UFont*& Holder)
	{
		if (!Holder)
		{
			UFont* F = NewObject<UFont>(GetTransientPackage(), NAME_None, RF_Transient);
			F->FontCacheType = EFontCacheType::Runtime;
			F->LegacyFontSize = Size;
			F->CompositeFont.DefaultTypeface.AppendFont(TEXT("Regular"), File, EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
			F->CompositeFont.FallbackTypeface.Typeface.AppendFont(TEXT("Regular"), MIStyle::SymbolFontFile(), EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
			F->AddToRoot();  // lives for the process, like the engine's own fonts
			Holder = F;
		}
		return Holder;
	}
}

FLinearColor MIStyle::Bg() { static const FLinearColor C = MIStylePrivate::Hex(TEXT("07080a")); return C; }
FLinearColor MIStyle::Plate() { static const FLinearColor C = MIStylePrivate::Hex(TEXT("0f1114")); return C; }
FLinearColor MIStyle::PlateEdge() { static const FLinearColor C = MIStylePrivate::Hex(TEXT("2a2e35")); return C; }
FLinearColor MIStyle::Ink() { static const FLinearColor C = MIStylePrivate::Hex(TEXT("f4f2ec")); return C; }
FLinearColor MIStyle::InkDim() { static const FLinearColor C = MIStylePrivate::Hex(TEXT("b4b2ab")); return C; }
FLinearColor MIStyle::InkFaint() { static const FLinearColor C = MIStylePrivate::Hex(TEXT("8b8983")); return C; }
FLinearColor MIStyle::Gold() { static const FLinearColor C = MIStylePrivate::Hex(TEXT("f6c21a")); return C; }
FLinearColor MIStyle::Red() { static const FLinearColor C = MIStylePrivate::Hex(TEXT("e2222b")); return C; }
FLinearColor MIStyle::Oxblood() { static const FLinearColor C = MIStylePrivate::Hex(TEXT("6b1218")); return C; }
FLinearColor MIStyle::Cyan() { static const FLinearColor C = MIStylePrivate::Hex(TEXT("39d0e0")); return C; }

FLinearColor MIStyle::Line(int32 Index)
{
	static const FLinearColor Lines[] = {
		MIStylePrivate::Hex(TEXT("f2762e")), MIStylePrivate::Hex(TEXT("1fa463")), MIStylePrivate::Hex(TEXT("3b82f0")),
		MIStylePrivate::Hex(TEXT("f6c21a")), MIStylePrivate::Hex(TEXT("e2222b"))};
	return Lines[FMath::Clamp(Index, 0, 4)];
}

FLinearColor MIStyle::WithAlpha(const FLinearColor& C, float A)
{
	return FLinearColor(C.R, C.G, C.B, A);
}

namespace MIStylePrivate
{
	FString DisplayFile() { return FontFile(TEXT("Anton-Regular.ttf"), TEXT("Roboto-Black.ttf")); }
	FString BodyFile(bool bBold)
	{
		// Archivo ships as one variable font; its default instance is the regular weight. Bold takes Roboto's bold face
		// until the static Archivo weights are added (spec 07 F_UI).
		return bBold ? FontFile(TEXT("Archivo-Bold.ttf"), TEXT("Roboto-Bold.ttf")) : FontFile(TEXT("Archivo.ttf"), TEXT("Roboto-Regular.ttf"));
	}

	/** One composite font per face file, kept for the process: the face, then the symbol face for what it lacks. */
	TSharedPtr<const FCompositeFont> Composite(const FString& File)
	{
		static TMap<FString, TSharedPtr<const FCompositeFont>> Cache;
		if (const TSharedPtr<const FCompositeFont>* Have = Cache.Find(File))
		{
			return *Have;
		}
		TSharedRef<FCompositeFont> F = MakeShared<FCompositeFont>();
		F->DefaultTypeface.AppendFont(TEXT("Regular"), File, EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
		F->FallbackTypeface.Typeface.AppendFont(TEXT("Regular"), MIStyle::SymbolFontFile(), EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
		Cache.Add(File, F);
		return F;
	}

	uint16 U16(const TArray<uint8>& B, int64 At) { return B.IsValidIndex(At + 1) ? uint16(B[At] << 8 | B[At + 1]) : 0; }
	uint32 U32(const TArray<uint8>& B, int64 At) { return B.IsValidIndex(At + 3) ? uint32(B[At]) << 24 | uint32(B[At + 1]) << 16 | uint32(B[At + 2]) << 8 | B[At + 3] : 0; }

	/** The code points a TrueType / OpenType file maps to a real glyph (its cmap, format 4 or 12). */
	TSet<int32> ReadCmap(const FString& File)
	{
		TSet<int32> Out;
		TArray<uint8> B;
		if (!FFileHelper::LoadFileToArray(B, *File) || B.Num() < 12)
		{
			return Out;
		}
		const int32 NumTables = U16(B, 4);
		int64 Cmap = -1;
		for (int32 I = 0; I < NumTables; ++I)
		{
			const int64 Rec = 12 + I * 16;
			if (B.IsValidIndex(Rec + 3) && B[Rec] == 'c' && B[Rec + 1] == 'm' && B[Rec + 2] == 'a' && B[Rec + 3] == 'p')
			{
				Cmap = U32(B, Rec + 8);
			}
		}
		if (Cmap < 0)
		{
			return Out;
		}
		// The best Unicode subtable: full repertoire (format 12) first, then the BMP (format 4).
		int64 Best = -1;
		int32 BestRank = 0;
		const int32 Subtables = U16(B, Cmap + 2);
		for (int32 I = 0; I < Subtables; ++I)
		{
			const int64 Rec = Cmap + 4 + I * 8;
			const int32 Platform = U16(B, Rec), Encoding = U16(B, Rec + 2);
			const int64 At = Cmap + U32(B, Rec + 4);
			const int32 Format = U16(B, At);
			const bool bUnicode = Platform == 0 || (Platform == 3 && (Encoding == 1 || Encoding == 10));
			const int32 Rank = !bUnicode ? 0 : Format == 12 ? 2 : Format == 4 ? 1 : 0;
			if (Rank > BestRank)
			{
				Best = At;
				BestRank = Rank;
			}
		}
		if (Best < 0)
		{
			return Out;
		}
		if (U16(B, Best) == 12)
		{
			const uint32 Groups = U32(B, Best + 12);
			for (uint32 G = 0; G < Groups && G < 100000; ++G)
			{
				const int64 At = Best + 16 + G * 12;
				const uint32 First = U32(B, At), Last = FMath::Min(U32(B, At + 4), 0x10FFFFu), Glyph = U32(B, At + 8);
				for (uint32 C = First; C <= Last; ++C)
				{
					if (Glyph + (C - First) != 0) Out.Add(static_cast<int32>(C));
				}
			}
			return Out;
		}
		const int32 Segs = U16(B, Best + 6) / 2;
		const int64 Ends = Best + 14, Starts = Ends + Segs * 2 + 2, Deltas = Starts + Segs * 2, Offsets = Deltas + Segs * 2;
		for (int32 S = 0; S < Segs; ++S)
		{
			const int32 End = U16(B, Ends + S * 2), Start = U16(B, Starts + S * 2);
			const int32 Delta = U16(B, Deltas + S * 2), RangeOffset = U16(B, Offsets + S * 2);
			for (int32 C = Start; C <= End && C != 0xFFFF; ++C)
			{
				int32 Glyph = 0;
				if (RangeOffset == 0)
				{
					Glyph = (C + Delta) & 0xFFFF;
				}
				else
				{
					Glyph = U16(B, Offsets + S * 2 + RangeOffset + (C - Start) * 2);
					Glyph = Glyph != 0 ? (Glyph + Delta) & 0xFFFF : 0;
				}
				if (Glyph != 0) Out.Add(C);
			}
		}
		return Out;
	}

	const TSet<int32>& Cmap(const FString& File)
	{
		static TMap<FString, TSet<int32>> Cache;
		if (const TSet<int32>* Have = Cache.Find(File))
		{
			return *Have;
		}
		return Cache.Add(File, ReadCmap(File));
	}
}

FString MIStyle::SymbolFontFile()
{
	// The engine's Droid Sans Fallback (Apache 2.0, in every checkout): its character map holds the arrows, the
	// geometric marks and the infinity sign the faces lack (Noto Sans Symbols 2 has no arrows; checked by
	// MurderInc.Frontend.Glyphs).
	return FPaths::Combine(FPaths::EngineContentDir(), TEXT("Slate/Fonts"), TEXT("DroidSansFallback.ttf"));
}

TArray<FString> MIStyle::FaceFiles()
{
	return {MIStylePrivate::DisplayFile(), MIStylePrivate::BodyFile(false), MIStylePrivate::BodyFile(true)};
}

bool MIStyle::FontHasGlyphs(const FString& File)
{
	return MIStylePrivate::Cmap(File).Num() > 0;
}

FString MIStyle::MissingGlyphs(const FString& Text)
{
	using namespace MIStylePrivate;
	const TSet<int32>& Fallback = Cmap(SymbolFontFile());
	FString Missing;
	for (const FString& File : FaceFiles())
	{
		const TSet<int32>& Face = Cmap(File);
		if (Face.Num() == 0)
		{
			continue;  // unreadable: nothing can be said about it
		}
		for (const TCHAR Ch : Text)
		{
			const int32 C = static_cast<int32>(Ch);
			if (C < 32 || C == 0xA0 || Face.Contains(C) || Fallback.Contains(C))
			{
				continue;
			}
			const FString One = FString::Chr(Ch);
			if (!Missing.Contains(One))
			{
				Missing += One;
			}
		}
	}
	return Missing;
}

FSlateFontInfo MIStyle::Display(float Size)
{
	return FSlateFontInfo(MIStylePrivate::Composite(MIStylePrivate::DisplayFile()), Size, TEXT("Regular"));
}

FSlateFontInfo MIStyle::Body(float Size, bool bBold)
{
	return FSlateFontInfo(MIStylePrivate::Composite(MIStylePrivate::BodyFile(bBold)), Size, TEXT("Regular"));
}

UFont* MIStyle::CanvasDisplay()
{
	static UFont* Holder = nullptr;
	return MIStylePrivate::MakeCanvasFont(MIStylePrivate::DisplayFile(), 26, Holder);
}

UFont* MIStyle::CanvasBody()
{
	static UFont* Holder = nullptr;
	return MIStylePrivate::MakeCanvasFont(MIStylePrivate::BodyFile(false), 18, Holder);
}
