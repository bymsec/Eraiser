---
name: fragman
description: Eraiser oyun klibinden sosyal medya fragmani kurgula (dikey 1080x1920, efektli, muzikli) veya fragman icin Suno muzik promptu yaz. Kullanici bir oyun videosu/klip atip "havali yap", "kurgula", "fragman yap", "efekt ekle", "muzik yapalim", "suno prompt" dediginde kullan.
---

# Eraiser fragman kurgusu

Kanitlanmis ornek: `ham/Movie_024`'ten yapilan 12 sn fragman, `fragman/cikti/` icinde.
Kod: `fragman/edit.py` (kare seviyesinde video), `fragman/audio.py` (ses miksi), `fragman/hazirla.sh` (kurulum).
Bu betikler Movie_024'e gore zamanlanmistir; yeni klipte cekim listesini (`shot(...)`), yazilari, doodle/parilti
konumlarini ve SFX zamanlamasini klibe gore yeniden yaz. Altyapi (efektler, gecisler, son kart) aynen kullanilir.

## Kullanicinin tercihleri (ONEMLI)

- Sohbet Turkce ve samimi ("hacı", "kardeş"). Kisa, net konus.
- **Videodaki tum yazilar Ingilizce.** (Site Turkce ama fragman Ingilizce.) Turkce surum ancak istenirse.
- Son kart etiketi: "Coming soon on Steam" (oyun henuz cikmadi; "PC · Steam" YAZMA).
- Muzik konusunda sormadan karar verme: once "sadece oyun sesi mi, muzik mi?" sor.
- Kullanici Suno Premium kullaniyor. Suno promptunda **salise/ondalik saniye verme**, tam saniye kullan (0:04 gibi).
  Muzik dosyasi icin WAV iste (yoksa MP3 olur).
- "Elinden gelen her seyi yap" dediginde gercekten gövde gösterisi bekliyor; ama zevkli kal.

## Is akisi

1. **Incele.** `ffprobe`; `fps=4` ile zaman damgali contact sheet (`drawtext=%{pts\:flt}`) cikar ve bak.
   Kritik anlari (karakter donusu, goz kirpma vb.) 60fps kare kare dogrula. Ses RMS'ini / onset'leri librosa ile cikar.
2. **Plan.** Hikaye ritmini bul (Movie_024: kos → dev fil ortaya cikar → kameraya don → fil goz kirpar). Efektleri
   bu anlara bagla. Toplam 10-12 sn hedefle.
3. **Hazirla.** `FRAGMAN_WORK=/tmp/fragman fragman/hazirla.sh <klip> [muzik.wav] [mi_t0 mi_sure]`
4. **Onizleme.** `python3 fragman/edit.py --preview -o prev.mp4` (540x960, hizli) → contact sheet ile kontrol.
5. **Final.** `python3 fragman/edit.py --meta` (zaman haritasi + SFX listesi → meta.json), `python3 fragman/edit.py -o video.mp4`
   (~8 dk, arka planda calistir), `python3 fragman/audio.py` → mix.wav.
6. **Birlestir + normalize:**
   `ffmpeg -i video.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -af "volume=-2.6dB,alimiter=limit=0.84:attack=0.5:release=60:level=false" -c:a aac -b:a 256k ...`
   Hedef **-14 LUFS, true peak <= -1 dB** (`ebur128=peak=true` ile olc, tahmin etme).
7. **Gonder.** SendUserFile ~45 MB'i reddetti; `-crf 21 -preset slow -tune film` ile ~18 MB web surumu gonder.
8. **Kalite kontrol (gondermeden once):** tam cozunurlukte kritik karelere bak; son dosyada onset'lerin gorsel
   vuruslara oturdugunu olc. Sesi dinleyemedigini soyle, olculen degerleri raporla.

## Teknik dersler

- Klip 60fps; cikis 30fps. 0.5x agir cekim dogal kareleri kullanir. Daha yavasi icin `minterpolate` (mci, aobmc) 240fps
  ara kare uretir — Movie_024'te temiz cikti (~1.2 sn icin ~6 dk).
- **HUD temizligi:** sag ustteki mini harita (merkez ~(893,176), r~186) satir satir lerp + blur ile gokyuzu doldurulur.
  Alttaki can bari icin taban zoom 1.09 ve kadraj alt siniri y<=1770.
- **Guvenli alan:** Reels/TikTok arayuzu altta ~250 px ve ustte ~150 px'i kapatir. Son kart ogeleri y 600-1700 arasi.
- Motion blur: 180° shutter, cikis karesi basina 2+ alt-kare; snap zoom'da 14'e kadar (zoom blur bedavaya gelir).
- `pgrep -f <metin>` kendi bash komutunu da yakalar; render bitisini log satiriyla izle (Monitor).
- Son kart degisikligi icin tum videoyu render etme: `--from <sn>` ile kuyrugu uret, oncesini eski videodan al, birlestir.

## Efekt kutuphanesi (edit.py icinde hazir)

- Kagit + organik kalem karalamasi (`scribble_strokes`, egriligi degisen ilmekler), sitedeki cizgili kagit dokusu.
- **Silgi gecisi:** sitedeki kosan silgi sprite'i (`gorseller/silgi-adam-kosu.webp`, 8 kare) zikzakla karalamayi silip
  oyunu acar; arkasinda hayalet izler + silgi kirintisi partikulleri.
- Kinetik yazi: el yazisiyla belirme (soldan maske), carpma (olcek 2.5→1 + flas + sarsinti + kromatik sapma),
  silgiyle silinerek cikis (tirtikli maske + kirinti).
- Speed ramp (kaynak→cikis zaman tablosu), letterbox bantlari, agir cekimde desature → carpmada renk patlamasi.
- Jump cut + zoom degisimi, snap zoom (eoe), el cizimi doodle (titrek cember, ok, not), yildiz parilti.
- Cikis: ekrani karalama kaplar → son kart: silgi bandi silerek logoyu acar, pembe alt cizgi, slogan, el sallayan
  silgi (`silgi-adam-el.webp`), etiket. Hafif Ken Burns.
- Renk: doygunluk 1.12, kontrast 1.07, bloom, vinyet, gren.
- Fontlar: Patrick Hand (baslik/el yazisi), Nunito 800 (etiket). Renkler `stil.css`'ten (grafit #2d2b29, silgi pembe #f28f96, kilif mavi #5f86b8, kagit #f6f1e6).

## Ses (audio.py)

- Oyun sesi ayni zaman haritasiyla yeniden orneklenir (varispeed: agir cekimde pitch duser); kesimlerde 15-30 ms gecis.
- Sentez SFX: kalem cizirtisi, silgi surtmesi, whoosh (kayan band-pass), riser, boom (sub + click + crack),
  pop, can/parilti, adim, gicirti; sentetik reverb.
- Muzik varsa: tempo/onset analizi (librosa), drop'u ana carpmaya, final hit'i logoya hizala; arada "teyp durmasi".
  Muzik onde, oyun sesi ~0.85, SFX ~0.6 ve muzikle carpan riser/boom kisik.

## Suno promptu (fragman muzigi)

Kullanici sureyi Suno'da kendisi ayarliyor (ornek: 12 sn). Instrumental dugmesi KAPALI (yoksa Lyrics kutusu kaybolur);
Lyrics'e sadece koseli parantez icinde yonerge yaz, tam saniyelerle. Fragmanin cekim zamanlarina gore BPM sec
(Movie_024: 132 BPM → carpma, son kart ve logo olcu/vurus basina dustu). Suno sureyi tutmayabilir (12 istendi, 20 geldi):
olcu sinirlarindan kesip hizala.

Sablon:
- **Lyrics:** `[Intro - 0:00] [...]`, `[Verse - 0:01] [...]`, `[Build - 0:02] [drums drop out, swells]`,
  `[Drop - 0:04] [BIG orchestral hit ...]`, `[Break - 0:05]`, `[Twinkle - 0:06]`, `[Stop - 0:07] [tape stop, sudden silence]`,
  `[Outro - 0:08]`, `[Final Hit - 0:09]`, `[Ending - 0:11] [last warm chord, short ring out]`, `[End]`
- **Styles:** whimsical orchestral pop game trailer, instrumental, <BPM> BPM, 4/4, bright major key, music box, celesta,
  glockenspiel, pizzicato strings, ukulele, toy piano, staccato clarinet and bassoon, hand claps, punchy kick, timpani,
  brass stabs, big cinematic hits, stop-start dynamics, cozy cartoon adventure, playful and mischievous, short and punchy
- **Exclude:** vocals, singing, choir, humming, lyrics, rap, spoken word, dubstep, EDM, supersaw, trap hi-hats,
  distorted guitar, heavy metal, sad, dark, horror, lo-fi, long intro, slow fade out, reverb wash, 8-bit chiptune
