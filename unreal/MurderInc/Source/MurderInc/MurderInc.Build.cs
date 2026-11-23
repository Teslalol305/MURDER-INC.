using UnrealBuildTool;

// The one gameplay module. Dependencies as agreed in docs/unreal/ARCHITECTURE.md section 2.1.
public class MurderInc : ModuleRules
{
	public MurderInc(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

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
		PrivateDependencyModuleNames.Add("RHI");

		// Pixel Streaming 2 is enabled for the game target only (MurderInc.uproject: TargetAllowList Game), so the
		// editor and the automation tests never load it. The game reads its connection events (Cloud/MICloud.cpp).
		bool bPixelStreaming = Target.Type == TargetType.Game
			&& (Target.Platform == UnrealTargetPlatform.Linux || Target.Platform == UnrealTargetPlatform.Win64);
		if (bPixelStreaming)
		{
			PrivateDependencyModuleNames.AddRange(new string[] { "PixelStreaming2", "PixelStreaming2Core" });
		}
		PublicDefinitions.Add("MI_WITH_PIXELSTREAMING2=" + (bPixelStreaming ? "1" : "0"));

		// Includes are written from the module root: #include "Core/Data/MIDataSubsystem.h"
		PublicIncludePaths.Add(ModuleDirectory);
	}
}
