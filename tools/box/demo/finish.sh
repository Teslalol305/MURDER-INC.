#!/bin/bash
# The deliverable: a 2 s title card "MURDER INC. - Unreal Engine 5 build", then the captured take with its sound.
# H.264 High 1920 x 1080 at 60 fps (capped at 22 Mbit/s: under 300 MB for two minutes), AAC 192 kbit/s stereo
# (the render's front left and right), loudness normalised to -16 LUFS with peaks under -1.5 dBTP.
# Usage: finish.sh [name] [font file] [end s: where the take is cut]   Output: <logs>/demo/<name>-final.mp4 and <name>-final.txt (its facts)
. "$(dirname "${BASH_SOURCE[0]}")/../lib.sh"
dir=$MI_LOGS/demo; name=${1:-demo}
font=${2:-}; end=${3:-}
cut=(); [ -n "$end" ] && cut=(-t "$end")
for f in "$font" /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf $(fc-list -f '%{file}\n' 2>/dev/null | grep -i bold | head -1); do
  [ -n "$f" ] && [ -f "$f" ] && { font=$f; break; }
done
[ -f "$font" ] || { echo "FINISH FAILED: no font (apt-get install -y fonts-dejavu-core)"; exit 1; }
[ -s "$dir/$name.mp4" ] && [ -s "$dir/$name.wav" ] || { echo "FINISH FAILED: $dir/$name.mp4 or .wav missing"; exit 1; }
out=$dir/$name-final.mp4
ffmpeg -y -loglevel warning \
  -f lavfi -i "color=c=0x0a0a0a:s=1920x1080:r=60:d=2" "${cut[@]}" -i "$dir/$name.mp4" "${cut[@]}" -i "$dir/$name.wav" \
  -filter_complex "[0:v]drawtext=fontfile=$font:text='MURDER INC. - Unreal Engine 5 build':fontcolor=0xf4f2ec:fontsize=76:x=(w-text_w)/2:y=(h-text_h)/2,fade=t=in:st=0:d=0.35,fade=t=out:st=1.6:d=0.4,format=yuv420p,setsar=1[t];\
[1:v]format=yuv420p,setsar=1,setpts=PTS-STARTPTS[v];[t][v]concat=n=2:v=1:a=0[vv];\
[2:a]pan=stereo|c0=c0|c1=c1,adelay=2000|2000,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,alimiter=limit=0.79:level=false,afade=t=out:st=$(( ${end:-600} + 1 )):d=1[aa]" \
  -map "[vv]" -map "[aa]" -c:v libx264 -preset slow -crf 18 -maxrate 22M -bufsize 44M -profile:v high -pix_fmt yuv420p -r 60 \
  -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart "$out" || { echo "FINISH FAILED"; exit 1; }
ffprobe -v error -show_entries format=duration,size,bit_rate:stream=codec_name,width,height,r_frame_rate,channels,sample_rate -of default=nw=1 "$out" | tee "$dir/$name-final.txt"
echo "FINISH DONE $out"
