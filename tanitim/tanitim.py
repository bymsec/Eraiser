#!/usr/bin/env python3
"""Eraiser tanıtım klibi (TikTok / Reels / Shorts).

Girdi : ../ham/Movie_019.mp4 (1080x1920, 60 fps, sessiz), ../ham/music.mp3
Çıktı : cikti/eraiser_tanitim.mp4 (1080x1920, 30 fps, H.264 ~16 Mbps, AAC)

Tüm zamanlar saniye cinsinden; ayar için aşağıdaki sabitleri değiştir.
"""
import json
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

KOK = Path(__file__).resolve().parent
VIDEO = KOK.parent / "ham" / "Movie_019.mp4"
MUZIK = KOK.parent / "ham" / "music.mp3"
FONT = KOK / "Fredoka-Bold.ttf"
CIKTI = KOK / "cikti" / "eraiser_tanitim.mp4"
# Hedef video bit hızı (Mbps). Varsayılan 16; `python3 tanitim.py 12.4`
# 30 MB altında kalan hafif sürümü üretir.
MBPS = float(sys.argv[1]) if len(sys.argv) > 1 else 16.0
if MBPS != 16.0:
    CIKTI = CIKTI.with_name(f"eraiser_tanitim_{MBPS:g}mbps.mp4")

W, H, FPS = 1080, 1920, 30
SURE = 19.25
SR = 48000

# --- Yazı zamanları -------------------------------------------------------
YAZI1 = (0.0, 3.0)          # "In this world, erasing is forbidden."
SILME_BASLAR = 11.5         # karalamanın silinmeye başladığı an (ham video)
YAZI2 = (SILME_BASLAR, SILME_BASLAR + 3.0)
LOGO = (SURE - 1.5, SURE)   # "Eraiser"
FLASH = 12.85               # duvarın yarıldığı an: yumuşak beyaz parlama

# --- Müzik kurgusu --------------------------------------------------------
# Müzikteki enerjik giriş 8.555 sn'de. Onu SILME_BASLAR'a oturtmak için
# girişten önceki iki ölçü (2.23 -> 6.40, 115.6 BPM) bir kez tekrarlanıyor
# ve müziğin başından MUZIK_BAS kadar kesiliyor.
MUZIK_GIRIS = 8.555
TEKRAR_A, TEKRAR_B = 2.23, 6.40
MUZIK_BAS = MUZIK_GIRIS + (TEKRAR_B - TEKRAR_A) - SILME_BASLAR

# --- Güvenli alan ---------------------------------------------------------
# Alt %20 ve sağ %15 yasak; ekranda ortalı kalıp sağ sınırı (918 px)
# geçmemek için metin genişliği en fazla 2 * (918 - 540) = 756 px.
MAKS_GEN = 740
YAZI_Y = 470                # yazı bloğunun dikey merkezi (üst yarı)
LOGO_Y = 420

BEYAZ = (255, 255, 255, 255)
KONTUR = (43, 24, 56, 255)  # koyu mor, oyunun karalama tonlarına uygun


def ease_out_back(x):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out(x):
    return 1 - (1 - x) ** 3


def klamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def yazi_resmi(satirlar, boyut, kontur=10, golge=True):
    """Beyaz, koyu konturlu, yumuşak gölgeli çok satırlı metin (RGBA).

    Kontur dahil genişlik MAKS_GEN'i aşarsa boyut otomatik küçülür.
    """
    while True:
        font = ImageFont.truetype(str(FONT), boyut)
        if max(font.getbbox(s, stroke_width=kontur)[2]
               - font.getbbox(s, stroke_width=kontur)[0]
               for s in satirlar) <= MAKS_GEN:
            break
        boyut -= 1
    aralik = int(boyut * 1.12)
    genis = [font.getbbox(s, stroke_width=kontur) for s in satirlar]
    gen = max(b[2] - b[0] for b in genis)
    pad = 40
    yuk = aralik * len(satirlar) + kontur * 2
    img = Image.new("RGBA", (gen + pad * 2, yuk + pad * 2), (0, 0, 0, 0))

    def ciz(katman, renk, kontur_renk, dx=0, dy=0):
        d = ImageDraw.Draw(katman)
        for i, s in enumerate(satirlar):
            b = font.getbbox(s, stroke_width=kontur)
            x = pad + (gen - (b[2] - b[0])) // 2 - b[0] + dx
            y = pad + i * aralik + dy
            d.text((x, y), s, font=font, fill=renk, stroke_width=kontur,
                   stroke_fill=kontur_renk)

    if golge:
        g = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ciz(g, (20, 10, 30, 150), (20, 10, 30, 150), dx=0, dy=8)
        img.alpha_composite(g.filter(ImageFilter.GaussianBlur(9)))
    ciz(img, BEYAZ, KONTUR)
    return img


def yildiz(r, renk=(255, 255, 255)):
    """Dört köşeli küçük parıltı."""
    s = r * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = s / 2
    k = r * 0.28
    d.polygon([(c, c - 2 * r), (c + k, c - k), (c + 2 * r, c), (c + k, c + k),
               (c, c + 2 * r), (c - k, c + k), (c - 2 * r, c), (c - k, c - k)],
              fill=renk + (255,))
    parilti = img.filter(ImageFilter.GaussianBlur(r * 0.35))
    parilti.alpha_composite(img)
    return parilti


def alfa_carp(img, a):
    if a >= 0.999:
        return img
    r, g, b, al = img.split()
    al = al.point(lambda v: int(v * a))
    return Image.merge("RGBA", (r, g, b, al))


class Katman:
    def __init__(self):
        self.y1 = yazi_resmi(["In this world,", "erasing is forbidden."], 86)
        self.y2 = yazi_resmi(["I'm the only one", "who can."], 92)
        self.logo = yazi_resmi(["Eraiser"], 74, kontur=8)
        rnd = random.Random(7)
        self.yildizlar = [yildiz(r) for r in (9, 12, 7, 10, 8)]
        lw, lh = self.logo.size
        self.yildiz_yer = [
            (W / 2 - lw * 0.42, LOGO_Y - lh * 0.30, 0.00),
            (W / 2 + lw * 0.40, LOGO_Y - lh * 0.32, 0.25),
            (W / 2 + lw * 0.47, LOGO_Y + lh * 0.18, 0.55),
            (W / 2 - lw * 0.48, LOGO_Y + lh * 0.20, 0.40),
            (W / 2 + lw * 0.05, LOGO_Y - lh * 0.46, 0.75),
        ]
        # Silgi kırıntıları: yazı 2 soldan sağa "silinerek" açılırken
        # açılma kenarından dökülür.
        self.kirinti = []
        for _ in range(70):
            self.kirinti.append(dict(
                u=rnd.random(),                  # kenarın geçtiği an (0-1)
                dy=rnd.uniform(-0.45, 0.45),     # satır yüksekliğinde konum
                vx=rnd.uniform(-60, 90), vy=rnd.uniform(-220, -40),
                r=rnd.uniform(4, 9), omur=rnd.uniform(0.5, 0.9),
                renk=rnd.choice([(255, 182, 203), (255, 255, 255),
                                 (246, 150, 178), (255, 225, 232)])))

    @staticmethod
    def yerlestir(tuval, img, cx, cy, olcek=1.0, alfa=1.0):
        if alfa <= 0.003:
            return
        if abs(olcek - 1) > 0.002:
            img = img.resize((max(1, int(img.width * olcek)),
                              max(1, int(img.height * olcek))), Image.LANCZOS)
        img = alfa_carp(img, alfa)
        tuval.alpha_composite(img, (int(cx - img.width / 2),
                                    int(cy - img.height / 2)))

    def kare(self, t):
        tuval = Image.new("RGBA", (W, H), (0, 0, 0, 0))

        # Yazı 1: yaylanarak "pop" + yumuşak belirme / kaybolma
        a, b = YAZI1
        if a <= t < b:
            giris = klamp((t - a) / 0.45)
            cikis = klamp((b - t) / 0.45)
            olcek = 0.82 + 0.18 * ease_out_back(giris)
            self.yerlestir(tuval, self.y1, W / 2, YAZI_Y, olcek,
                           min(klamp(giris / 0.6), cikis))

        # Yazı 2: silgiyle siliniyormuş gibi soldan sağa açılır, kırıntı saçar
        a, b = YAZI2
        if a <= t < b:
            acilma = ease_out(klamp((t - a) / 0.6))
            cikis = klamp((b - t) / 0.45)
            img = self.y2
            x0 = W / 2 - img.width / 2
            y0 = YAZI_Y - img.height / 2
            kenar = int(img.width * acilma)
            maske = Image.new("L", img.size, 0)
            if kenar > 0:
                md = ImageDraw.Draw(maske)
                md.rectangle([0, 0, kenar, img.height], fill=255)
                maske = maske.filter(ImageFilter.GaussianBlur(14))
            al = Image.composite(img, Image.new("RGBA", img.size), maske)
            self.yerlestir(tuval, al, W / 2, YAZI_Y, 1.0, cikis)
            d = ImageDraw.Draw(tuval)
            for k in self.kirinti:
                t0 = a + 0.6 * k["u"] ** 1.6
                yas = t - t0
                if not (0 <= yas < k["omur"]):
                    continue
                px = x0 + img.width * min(1, k["u"]) + k["vx"] * yas
                py = (y0 + img.height / 2 + k["dy"] * img.height * 0.8
                      + k["vy"] * yas + 0.5 * 900 * yas * yas)
                s = k["r"] * (1 - 0.5 * yas / k["omur"])
                aa = int(255 * (1 - yas / k["omur"]))
                d.rounded_rectangle([px - s, py - s * 0.7, px + s, py + s * 0.7],
                                    radius=s * 0.4, fill=k["renk"] + (aa,))

        # Duvar yarılırken yumuşak beyaz parlama
        if FLASH <= t < FLASH + 0.35:
            aa = int(110 * (1 - (t - FLASH) / 0.35) ** 2)
            tuval.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, aa)))

        # Logo: hafifçe yükselerek belirir, etrafında parıltılar
        a, b = LOGO
        if a <= t:
            giris = ease_out(klamp((t - a) / 0.5))
            self.yerlestir(tuval, self.logo, W / 2, LOGO_Y + 18 * (1 - giris),
                           0.94 + 0.06 * giris, giris)
            for img, (x, y, gec) in zip(self.yildizlar, self.yildiz_yer):
                yas = t - a - 0.25 - gec
                if yas < 0:
                    continue
                parla = math.sin(min(yas / 0.6, 1) * math.pi) if yas < 0.6 else \
                    0.35 + 0.25 * math.sin((yas - 0.6) * 7)
                self.yerlestir(tuval, img, x, y, 0.6 + 0.5 * parla,
                               klamp(parla))
        return tuval


# --- Ses ------------------------------------------------------------------
def muzik_oku():
    ham = subprocess.run(["ffmpeg", "-v", "error", "-i", str(MUZIK), "-ac", "2",
                          "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(ham, dtype=np.float32).reshape(-1, 2).copy()


def muzik_kurgu(m):
    i = lambda s: int(round(s * SR))
    xf = i(0.03)   # ek yerinde 30 ms çapraz geçiş
    p1 = m[i(MUZIK_BAS):i(TEKRAR_B) + xf]
    p2 = m[i(TEKRAR_A):]
    ramp = np.linspace(0, 1, xf)[:, None]
    ek = p1[-xf:] * (1 - ramp) + p2[:xf] * ramp
    out = np.concatenate([p1[:-xf], ek, p2[xf:]])
    n = i(SURE)
    out = out[:n]
    out[:i(0.08)] *= np.linspace(0, 1, i(0.08))[:, None]   # tık önleme
    return out


def sfx_kazima(n_sure, rnd):
    """Silgi sürtünmesi: filtrelenmiş gürültü, ileri-geri darbeler."""
    n = int(n_sure * SR)
    g = rnd.standard_normal(n)
    spek = np.fft.rfft(g)
    f = np.fft.rfftfreq(n, 1 / SR)
    spek *= np.exp(-((np.log(f + 1) - np.log(2200)) ** 2) / 0.5)
    g = np.fft.irfft(spek, n)
    g /= np.abs(g).max()
    t = np.arange(n) / SR
    darbe = 0.55 + 0.45 * np.abs(np.sin(2 * np.pi * 7 * t))
    zarf = np.minimum(1, t / 0.05) * np.minimum(1, (n_sure - t) / 0.25)
    return g * darbe * zarf


def sfx_zil(rnd):
    """Müzik kutusuna uyan yumuşak iki notalı çan."""
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for gecikme, frek in ((0.0, 1318.5), (0.12, 1975.5)):   # E6, B6
        tt = np.clip(t - gecikme, 0, None)
        on = (t >= gecikme)
        ses = (np.sin(2 * np.pi * frek * tt)
               + 0.35 * np.sin(2 * np.pi * frek * 2.76 * tt) * np.exp(-tt * 9)
               + 0.15 * np.sin(2 * np.pi * frek * 5.4 * tt) * np.exp(-tt * 18))
        out += on * ses * np.exp(-tt * 3.2) * np.minimum(1, tt / 0.004)
    return out / np.abs(out).max()


def db(x):
    return 10 ** (x / 20)


def ses_uret(yol):
    rnd = np.random.default_rng(3)
    mix = muzik_kurgu(muzik_oku()).astype(np.float64)
    n = len(mix)

    def ekle(sinyal, t0, kazanc, pan=0.0):
        a = int(t0 * SR)
        b = min(n, a + len(sinyal))
        s = sinyal[:b - a] * kazanc
        mix[a:b, 0] += s * (1 - pan)
        mix[a:b, 1] += s * (1 + pan)

    ekle(sfx_kazima(0.85, rnd), 12.0, db(-20))   # silgi duvara sürtünüyor
    ekle(sfx_zil(rnd), LOGO[0] + 0.1, db(-17))   # logo çanı

    t = np.arange(n) / SR
    mix *= np.clip((SURE - t) / 1.0, 0, 1)[:, None] ** 1.5   # son 1 sn sönme
    mix /= max(1.0, np.abs(mix).max() / 0.98)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR),
                    "-ac", "2", "-i", "-", str(yol)],
                   input=mix.astype(np.float32).tobytes(), check=True)


def ses_normalize(giris, cikis):
    """Sosyal medya için -14 LUFS, iki geçişli (lineer) loudnorm."""
    olc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(giris), "-af",
         "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, check=True).stderr
    m = json.loads(olc[olc.rindex("{"):olc.rindex("}") + 1])
    af = ("loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:"
          f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
          f"offset={m['target_offset']},aresample=48000")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(giris), "-af", af,
                    str(cikis)], check=True)


# --- Kurgu ----------------------------------------------------------------
def main():
    CIKTI.parent.mkdir(exist_ok=True)
    gecici = CIKTI.parent / "_gecici"
    gecici.mkdir(exist_ok=True)
    ham_ses, ses = gecici / "ses_ham.wav", gecici / "ses.wav"
    ses_uret(ham_ses)
    ses_normalize(ham_ses, ses)

    katman = Katman()
    kare_sayisi = int(round(SURE * FPS))
    cmd = [
        "ffmpeg", "-v", "error", "-stats", "-y",
        "-i", str(VIDEO),
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-",
        "-i", str(ses),
        "-filter_complex",
        f"[0:v]fps={FPS},scale={W}:{H}:flags=lanczos,setsar=1,format=rgba[v];"
        "[v][1:v]overlay=0:0:format=auto:shortest=1,format=yuv420p[o]",
        "-map", "[o]", "-map", "2:a",
        "-c:v", "libx264", "-preset", "slow", "-profile:v", "high",
        "-b:v", f"{MBPS}M", "-minrate", "12M", "-maxrate", f"{MBPS * 1.3:.1f}M",
        "-bufsize", f"{MBPS * 2:.0f}M",
        "-g", str(FPS), "-colorspace", "bt709", "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-t", str(SURE), "-movflags", "+faststart", str(CIKTI),
    ]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(kare_sayisi):
        p.stdin.write(katman.kare(i / FPS).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise SystemExit("ffmpeg başarısız")
    print(f"\nMüzik: baştan {MUZIK_BAS:.2f} sn kesildi, "
          f"{TEKRAR_A:.2f}-{TEKRAR_B:.2f} arası bir kez tekrarlandı; "
          f"giriş videoda {SILME_BASLAR:.2f} sn'de.")
    print("Yazdı:", CIKTI)


if __name__ == "__main__":
    main()
