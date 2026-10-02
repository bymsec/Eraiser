#!/usr/bin/env bash
# Fragman calisma alanini hazirlar: bagimliliklar, fontlar, ham kare/ses cikarma, istege bagli agir cekim ara kareleri.
# Kullanim: fragman/hazirla.sh <klip.mp4> [muzik.wav] [mi_baslangic_sn mi_sure_sn]
#   ornek:  fragman/hazirla.sh ham/Movie_024.mp4 ham/Cartoon_Chase.wav 1.70 1.2
set -euo pipefail
KLIP="$1"; MUZIK="${2:-}"; MI_T0="${3:-}"; MI_DUR="${4:-}"
WORK="${FRAGMAN_WORK:-/tmp/fragman}"
mkdir -p "$WORK/fonts"

pip install -q numpy pillow opencv-python-headless librosa scipy soundfile matplotlib 2>&1 | grep -v WARN || true

# sitenin fontlari (Google Fonts reposundan)
[ -f "$WORK/fonts/PatrickHand-Regular.ttf" ] || curl -sSfL -o "$WORK/fonts/PatrickHand-Regular.ttf" \
  https://raw.githubusercontent.com/google/fonts/main/ofl/patrickhand/PatrickHand-Regular.ttf
[ -f "$WORK/fonts/Nunito-var.ttf" ] || curl -sSfL -o "$WORK/fonts/Nunito-var.ttf" \
  "https://raw.githubusercontent.com/google/fonts/main/ofl/nunito/Nunito%5Bwght%5D.ttf"

ffprobe -v error -show_entries format=duration:stream=codec_type,width,height,r_frame_rate -of compact "$KLIP"
# ham RGB kareler (edit.py memmap ile okur) + oyun sesi
ffmpeg -v error -y -i "$KLIP" -f rawvideo -pix_fmt rgb24 "$WORK/src.rgb"
ffmpeg -v error -y -i "$KLIP" -vn -ac 2 -ar 48000 -c:a pcm_f32le "$WORK/game.wav" || echo "klipte ses yok"
[ -n "$MUZIK" ] && ffmpeg -v error -y -i "$MUZIK" -ac 2 -ar 48000 -c:a pcm_s16le "$WORK/music.wav"

# agir cekim bolumu icin hareket-telafili ara kareler (240fps). Yavas: ~1 sn icin birkac dakika.
if [ -n "$MI_T0" ]; then
  ffmpeg -v error -y -ss "$MI_T0" -t "$MI_DUR" -i "$KLIP" -an \
    -vf "minterpolate=fps=240:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1" \
    -f rawvideo -pix_fmt rgb24 "$WORK/mi.rgb"
fi
echo "hazir: $WORK"
