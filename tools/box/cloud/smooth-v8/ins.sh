#!/bin/bash
# SMOOTH.md v8 (performance engineer): export an Unreal Insights trace to CSV on the box.
#   ins.sh <name>   trace /tmp/v8/tr/<name>.utrace -> /tmp/v8/ins/<name>-gt.csv (game thread) and -timers.csv
# (the same trace with -startTime= -endTime= and no -threads gives <name>-win.csv, plus ExportThreads <name>-threads.csv, for thr.py / busy.py)
n=$1; mkdir -p /tmp/v8/ins/home
cat > /tmp/v8/ins/$n-cmds.txt <<EOT
TimingInsights.ExportTimingEvents /tmp/v8/ins/$n-gt.csv -threads=GameThread -columns=ThreadId,TimerId,StartTime,EndTime,Duration,Depth
TimingInsights.ExportTimers /tmp/v8/ins/$n-timers.csv
EOT
cd /project/ue/UnrealEngine/Engine/Binaries/Linux
HOME=/tmp/v8/ins/home ./UnrealInsights -OpenTraceFile=/tmp/v8/tr/$n.utrace -NoUI -AutoQuit -ExecOnAnalysisCompleteCmd="@=/tmp/v8/ins/$n-cmds.txt" > /tmp/v8/ins/$n-ins.log 2>&1
