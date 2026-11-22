#!/bin/bash
# Run an editor Python script headless in the character scratch project (UnrealEditor-Cmd -run=pythonscript).
# Usage (as root or ue4): cmdlet.sh <script.py> <log name> [extra args]   -> /project/ue/logs/chars/<log name>.log
# Starts detached; poll the log for "MI-DONE" (the scripts print it last) or the process id in <log>.pid.
P=/project/ue/chars
s=$1; name=$2; shift 2
mkdir -p /project/ue/logs/chars; chown ue4 /project/ue/logs/chars 2>/dev/null
if [ "$(id -un)" != ue4 ]; then exec su ue4 -c "$(printf '%q ' bash "$0" "$s" "$name" "$@")"; fi
export HOME=/home/ue4
cd /project/ue/UnrealEngine
setsid nohup env 'UE-LocalDataCachePath=/project/ue/ddc' ./Engine/Binaries/Linux/UnrealEditor-Cmd "$P/Chars.uproject" \
  -run=pythonscript "-script=$s" -unattended -nosplash -NoSound -stdout -FullStdOutLogOutput -NullRHI \
  '-DDC=(ProjectPak,InstalledProjectPak,EnginePak=InstalledEnginePak,EnterprisePak,InstalledLocal)' \
  '-ini:Engine:[Zen]:AutoLaunch=false' '-ini:Engine:[ConsoleVariables]:AssetRegistry.DisableDirectoryWatcher=1' "$@" \
  > /project/ue/logs/chars/$name.log 2>&1 < /dev/null &
echo $! > /project/ue/logs/chars/$name.pid
echo "started $name pid $(cat /project/ue/logs/chars/$name.pid)"
