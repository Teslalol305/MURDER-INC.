#!/bin/bash
# Create the MetaHuman scratch project /project/ue/metahuman (MetaHuman Creator plugins enabled, MCP port 8006).
# Copies Config from the character scratch project and the mannequin + template weapons content (for the clip test).
# Re-runnable: existing files are kept. Nothing in this project is ever committed (Epic-derived content).
P=/project/ue/metahuman; C=/project/ue/chars
if [ "$(id -un)" != ue4 ]; then mkdir -p $P /project/ue/logs/metahuman; chown ue4 $P /project/ue/logs/metahuman; exec su ue4 -c "$(printf '%q ' bash "$0" "$@")"; fi
mkdir -p $P/Config $P/Content/Characters $P/scripts /project/ue/logs/metahuman
cat > $P/MHScratch.uproject <<'EOF'
{
	"FileVersion": 3,
	"EngineAssociation": "5.9",
	"Category": "",
	"Description": "MURDER INC. MetaHuman scratch project (feasibility of MetaHuman Creator headless)",
	"Plugins": [
		{ "Name": "PythonScriptPlugin", "Enabled": true },
		{ "Name": "EditorScriptingUtilities", "Enabled": true },
		{ "Name": "ModelContextProtocol", "Enabled": true },
		{ "Name": "AllToolsets", "Enabled": true },
		{ "Name": "ControlRig", "Enabled": true },
		{ "Name": "MetaHumanCharacter", "Enabled": true },
		{ "Name": "MetaHumanSDK", "Enabled": true },
		{ "Name": "MetaHuman", "Enabled": true },
		{ "Name": "MetaHumanCoreTech", "Enabled": true },
		{ "Name": "HairStrands", "Enabled": true },
		{ "Name": "ChaosClothAsset", "Enabled": true },
		{ "Name": "ChaosOutfitAsset", "Enabled": true },
		{ "Name": "RigLogic", "Enabled": true }
	]
}
EOF
[ -f $P/Config/DefaultEngine.ini ] || cp $C/Config/DefaultEngine.ini $C/Config/DefaultInput.ini $P/Config/
[ -d $P/Content/Characters/Mannequins ] || cp -r $C/Content/Characters/Mannequins $P/Content/Characters/
[ -d $P/Content/Weapons ] || cp -r $C/Content/Weapons $P/Content/
[ -d $P/Content/Characters/Goons ] || cp -r $C/Content/Characters/Goons $P/Content/Characters/
cp /project/ue/repo/tools/box/mi_mcp.py $P/scripts/ 2>/dev/null || cp $C/scripts/mi_mcp.py $P/scripts/
echo SETUP-MH-DONE
