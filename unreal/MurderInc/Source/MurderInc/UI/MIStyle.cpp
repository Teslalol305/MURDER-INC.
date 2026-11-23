#include "UI/MIStyle.h"

#include "Engine/Font.h"
#include "Fonts/CompositeFont.h"
#include "HAL/FileManager.h"
#include "Misc/Paths.h"
#include "UObject/Package.h"

namespace MIStylePrivate
{
	FLinearColor Hex(const TCHAR* H) { return FLinearColor::FromSRGBColor(FColor::FromHex(H)); }

	FString FontFile(const TCHAR* Name, const TCHAR* EngineFallback)
	{
		const FString Own = FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Fonts"), Name);
		if (IFileManager::Get().FileExists(*Own))
		{
			return Own;
		}
		return FPaths::Combine(FPaths::EngineContentDir(), TEXT("Slate/Fonts"), EngineFallback);
	}

	UFont* MakeCanvasFont(const FString& File, int32 Size, UFont*& Holder)
	{
		if (!Holder)
		{
			UFont* F = NewObject<UFont>(GetTransientPackage(), NAME_None, RF_Transient);
			F->FontCacheType = EFontCacheType::Runtime;
			F->LegacyFontSize = Size;
			F->CompositeFont.DefaultTypeface.AppendFont(TEXT("Regular"), File, EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
			F->AddToRoot();  // lives for the process, like the engine's own fonts
			Holder = F;
		}
		return Holder;
	}
}

FLinearColor MIStyle::Bg() { return MIStylePrivate::Hex(TEXT("07080a")); }
FLinearColor MIStyle::Plate() { return MIStylePrivate::Hex(TEXT("0f1114")); }
FLinearColor MIStyle::PlateEdge() { return MIStylePrivate::Hex(TEXT("2a2e35")); }
FLinearColor MIStyle::Ink() { return MIStylePrivate::Hex(TEXT("f4f2ec")); }
FLinearColor MIStyle::InkDim() { return MIStylePrivate::Hex(TEXT("b4b2ab")); }
FLinearColor MIStyle::InkFaint() { return MIStylePrivate::Hex(TEXT("8b8983")); }
FLinearColor MIStyle::Gold() { return MIStylePrivate::Hex(TEXT("f6c21a")); }
FLinearColor MIStyle::Red() { return MIStylePrivate::Hex(TEXT("e2222b")); }
FLinearColor MIStyle::Oxblood() { return MIStylePrivate::Hex(TEXT("6b1218")); }
FLinearColor MIStyle::Cyan() { return MIStylePrivate::Hex(TEXT("39d0e0")); }

FLinearColor MIStyle::Line(int32 Index)
{
	static const TCHAR* Lines[] = {TEXT("f2762e"), TEXT("1fa463"), TEXT("3b82f0"), TEXT("f6c21a"), TEXT("e2222b")};
	return MIStylePrivate::Hex(Lines[FMath::Clamp(Index, 0, 4)]);
}

FLinearColor MIStyle::WithAlpha(const FLinearColor& C, float A)
{
	return FLinearColor(C.R, C.G, C.B, A);
}

FSlateFontInfo MIStyle::Display(float Size)
{
	return FSlateFontInfo(MIStylePrivate::FontFile(TEXT("Anton-Regular.ttf"), TEXT("Roboto-Black.ttf")), Size);
}

FSlateFontInfo MIStyle::Body(float Size, bool bBold)
{
	// Archivo ships as one variable font; its default instance is the regular weight. Bold takes Roboto's bold face
	// until the static Archivo weights are added (spec 07 F_UI).
	if (bBold)
	{
		return FSlateFontInfo(MIStylePrivate::FontFile(TEXT("Archivo-Bold.ttf"), TEXT("Roboto-Bold.ttf")), Size);
	}
	return FSlateFontInfo(MIStylePrivate::FontFile(TEXT("Archivo.ttf"), TEXT("Roboto-Regular.ttf")), Size);
}

UFont* MIStyle::CanvasDisplay()
{
	static UFont* Holder = nullptr;
	return MIStylePrivate::MakeCanvasFont(MIStylePrivate::FontFile(TEXT("Anton-Regular.ttf"), TEXT("Roboto-Black.ttf")), 26, Holder);
}

UFont* MIStyle::CanvasBody()
{
	static UFont* Holder = nullptr;
	return MIStylePrivate::MakeCanvasFont(MIStylePrivate::FontFile(TEXT("Archivo.ttf"), TEXT("Roboto-Regular.ttf")), 18, Holder);
}
