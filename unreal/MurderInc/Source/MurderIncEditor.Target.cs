using UnrealBuildTool;
using System.Collections.Generic;

public class MurderIncEditorTarget : TargetRules
{
	public MurderIncEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V8;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_9;
		ExtraModuleNames.Add("MurderInc");
	}
}
