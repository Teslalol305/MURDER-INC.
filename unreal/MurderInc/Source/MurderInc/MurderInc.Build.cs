using UnrealBuildTool;

// The one gameplay module. Dependencies as agreed in docs/unreal/ARCHITECTURE.md section 2.1.
public class MurderInc : ModuleRules
{
	public MurderInc(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		// Every source file is compiled on its own, with no unity chunks. In a chunk the names that files keep to themselves
		// in an anonymous namespace meet each other and the engine's headers (struct FReader in two files, constexpr Gravity
		// in MIEnemies.cpp ahead of an engine header whose parameter has that name), and a new file anywhere cuts the chunks
		// differently: a clean clone, which is what a release package is built from, then failed to build (found when release
		// 3c added files) while a working clone builds, because UBT's adaptive unity build compiles the files that are
		// changed on their own. 78 files: the full build takes minutes either way.
		bUseUnity = false;

		PublicDependencyModuleNames.AddRange(new string[] {
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput",
			"Slate",
			"SlateCore",
			"Json",
			"Niagara",
			"AnimationCore",
			"PhysicsCore",
			"AudioMixer"
		});

		// GPU frame time and memory for the cloud probe (Cloud/MICloud.cpp).
		// Startup report: shader platform, ray tracing, Nanite and Lumen support (RenderCore RenderUtils.h).
		PrivateDependencyModuleNames.AddRange(new string[] { "RHI", "RenderCore" });

		// Pixel Streaming 2 is enabled for the game target only (MurderInc.uproject: TargetAllowList Game), so the
		// editor and the automation tests never load it. The game reads its connection events and replaces its
		// console-command handler with an allowlist (Cloud/MICloud.cpp; the input handler's interface is in
		// PixelStreaming2Input).
		bool bPixelStreaming = Target.Type == TargetType.Game
			&& (Target.Platform == UnrealTargetPlatform.Linux || Target.Platform == UnrealTargetPlatform.Win64);
		if (bPixelStreaming)
		{
			PrivateDependencyModuleNames.AddRange(new string[] { "PixelStreaming2", "PixelStreaming2Core", "PixelStreaming2Input" });
		}
		PublicDefinitions.Add("MI_WITH_PIXELSTREAMING2=" + (bPixelStreaming ? "1" : "0"));

		// Includes are written from the module root: #include "Core/Data/MIDataSubsystem.h"
		PublicIncludePaths.Add(ModuleDirectory);
	}
}
