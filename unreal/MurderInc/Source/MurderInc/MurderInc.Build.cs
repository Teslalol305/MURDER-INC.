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

		// Includes are written from the module root: #include "Core/Data/MIDataSubsystem.h"
		PublicIncludePaths.Add(ModuleDirectory);
	}
}
