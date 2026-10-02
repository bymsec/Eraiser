#!/usr/bin/env python3
"""Eraiser - 'ciglik atan ses slider'i' dikey videosu.
Kaynak: ana menu kaydi (2560x1440, 60fps). Yardimcilar Movie_024 kurgusundan (edit.py) ice aktarilir."""
import os, sys, math, json, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

ED = os.path.dirname(os.path.abspath(__file__))   # edit.py / audio.py yardimcilari
sys.path.insert(0, ED)
import edit as E      # yardimcilar: text_sprite, place, over, reveal, grade, chroma, grain, Crumbs, karalama, sprite'lar...
from edit import cl, sm, eoc, eoe, eob, eio, lerp, W, H, FPS, GRAPHITE, PINK, PINK_D, WHITE, PAPER

HERE = os.environ.get('SLIDER_WORK', '/tmp/fragman2')   # src.mp4, src.wav, scream.wav, meta.json, mix.wav
SRCF = os.path.join(HERE, 'src.mp4')
SW, SH, SFPS = 2560, 1440, 60
ZB = H / SH            # 1.3333: tam yukseklik 9:16 pencere

# ---------------------------------------------------------------- kaynak okuyucu (segment segment ffmpeg pipe)
class Seg:
    def __init__(self, s0, s1):
        self.i0 = int(round(s0 * SFPS)); self.i1 = int(round(s1 * SFPS)) + 3
        self.p = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{self.i0 / SFPS:.4f}', '-i', SRCF,
                                   '-frames:v', str(self.i1 - self.i0 + 1), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                                  stdout=subprocess.PIPE, bufsize=SW * SH * 3 * 2)
        self.next = self.i0; self.buf = {}
    def get(self, i):
        i = int(cl(i, self.i0, self.i1))
        while self.next <= i:
            raw = self.p.stdout.read(SW * SH * 3)
            if len(raw) < SW * SH * 3:
                self.i1 = self.next - 1; break
            self.buf[self.next] = np.frombuffer(raw, np.uint8).reshape(SH, SW, 3)
            self.next += 1
            for k in [k for k in self.buf if k < self.next - 8]: del self.buf[k]
        i = min(i, max(self.buf))
        return self.buf[i]
    def at(self, ts):
        x = ts * SFPS; i0 = int(math.floor(x)); a = x - i0
        if a < 0.05: return self.get(i0)
        if a > 0.95: return self.get(i0 + 1)
        return cv2.addWeighted(self.get(i0), 1 - a, self.get(i0 + 1), a, 0)

# ---------------------------------------------------------------- cekim listesi
SHOTS = []
def shot(name, dur, s0, s1, cam):
    t0 = SHOTS[-1]['t1'] if SHOTS else 0.0
    SHOTS.append(dict(name=name, t0=t0, t1=t0 + dur, dur=dur, s0=s0, s1=s1, cam=cam))

ROW_C = (625, 640)          # uc slider satirini gosteren merkez
ZR = 1.68
# A: kanca - %100'e geri donus, yakin plan
shot('A', 0.75, 15.25, 16.00, lambda u, d: (2.75 + 0.15 * u / d, 800, 660))
# B: ana menu time-lapse (gece -> gunduz), logodan kitaba pan
shot('B', 1.60, 1.20, 6.30, lambda u, d: (ZB * (1.06 - 0.06 * u / d), lerp(1600, 590, eio(u / d)), 720))
# C: ayarlar acilir, satirlara yaklas
def cam_c(u, d):
    k = eio((u - 0.35) / 0.5)
    return (lerp(ZB, ZR, k), lerp(590, ROW_C[0], k), lerp(720, ROW_C[1], k))
shot('C', 0.90, 6.30, 7.20, cam_c)
# D: master volume (normal)
shot('D', 1.20, 9.35, 10.55, lambda u, d: (ZR, ROW_C[0], ROW_C[1]))
# E: effects - asil sov
EFF0 = 11.75
def cam_e(u, d):
    s = EFF0 + u
    z, cx, cy = ZR, ROW_C[0], ROW_C[1]
    k = eoe((s - 13.95) / 0.14) * (1 - eio((s - 14.55) / 0.25))     # %6'da yakin plan
    z = lerp(z, 3.4, k); cx = lerp(cx, 625, k); cy = lerp(cy, 665, k)
    k2 = eoe((s - 12.18) / 0.12) * (1 - eio((s - 12.9) / 0.4))        # silgi firlayinca kucuk punch
    z = z + 0.25 * k2
    return z, cx, cy
shot('E', 5.00, EFF0, EFF0 + 5.0, cam_e)
T_END0 = SHOTS[-1]['t1']
TOTAL = 12.0
S = {s['name']: s for s in SHOTS}

def shot_at(t):
    for s in SHOTS:
        if s['t0'] <= t < s['t1'] + 1e-9: return s
    return None
def src_of(s, t):
    u = t - s['t0']
    return s['s0'] + (s['s1'] - s['s0']) * u / s['dur']

# slider yuzdesi (karelerden okundu)
PCT_T = [11.75, 12.2, 12.4, 12.6, 12.8, 13.0, 13.2, 13.4, 13.6, 13.8, 14.0, 14.2, 14.4, 14.6, 14.8, 15.0, 15.2, 15.4, 15.6, 17.5]
PCT_V = [100, 100, 98, 85, 72, 62, 49, 37, 29, 20, 10, 6, 6, 24, 43, 65, 80, 95, 100, 100]
def pct(s): return float(np.interp(s, PCT_T, PCT_V))

# ses zarfi (ciglik bandi) -> sarsinti
_y = None
def load_env():
    global ENV_T, ENV_V
    import librosa, scipy.signal as sg
    y, sr = librosa.load(os.path.join(HERE, 'src.wav'), sr=24000, mono=True)
    b, a = sg.butter(4, [700, 4000], 'band', fs=sr); y = sg.filtfilt(b, a, y)
    hop = 240
    r = librosa.feature.rms(y=y, hop_length=hop, frame_length=960)[0]
    ENV_T = np.arange(len(r)) * hop / sr
    v = 20 * np.log10(r + 1e-9)
    ENV_V = np.clip((v + 36) / 22, 0, 1)
load_env()
def env(s): return float(np.interp(s, ENV_T, ENV_V))

# ---------------------------------------------------------------- olaylar
EVENTS = []
def hit(t, shake=0.0, flash=0.0, ca=0.0): EVENTS.append((t, shake, flash, ca))
hit(0.0, shake=0.8, ca=0.9)
hit(S['B']['t0'], flash=0.5, ca=0.5)
hit(S['E']['t0'] + (12.18 - EFF0), shake=0.5, ca=0.7, flash=0.15)
hit(S['E']['t0'] + (13.95 - EFF0), ca=0.6)
hit(S['E']['t0'] + (14.58 - EFF0), shake=0.6, ca=0.8)
E_LOGO = T_END0 + 0.92
hit(E_LOGO, shake=0.45, ca=0.4)

def fx_at(t):
    sh = fl = ca = 0.0
    for te, a, b, c in EVENTS:
        if t >= te:
            dt = t - te
            sh += a * math.exp(-dt / 0.16); fl += b * math.exp(-dt / 0.07); ca += c * math.exp(-dt / 0.14)
    s = shot_at(t)
    if s and s['name'] in ('A', 'E'):
        src = src_of(s, t)
        p = pct(src) / 100.0
        scream = (src > 12.18) and (src < 16.2)
        if scream:
            e = env(src)
            sh += 0.55 * (p ** 2) * e
            ca += 0.6 * (p ** 2) * e
    return sh, min(fl, 1.0), ca

def camera(t):
    s = shot_at(t)
    z, cx, cy = s['cam'](t - s['t0'], s['dur'])
    hw, hh = W / 2 / z, H / 2 / z
    cx = cl(cx, hw, SW - hw); cy = cl(cy, hh, SH - hh)
    sh, _, _ = fx_at(t)
    sx, sy, rot = E.shake_xy(t, sh)
    return z, cx, cy, rot, sx, sy

def video_frame(t, segs):
    s = shot_at(t); seg = segs[s['name']]
    shutter = 0.5 / FPS
    z0, cx0, cy0, *_ = camera(t)
    t1 = min(t + shutter, s['t1'] - 1e-4)
    z1, cx1, cy1, *_ = camera(t1)
    speed = (s['s1'] - s['s0']) / s['dur']
    motion = abs(z1 - z0) / z0 * 300 + math.hypot(cx1 - cx0, cy1 - cy0) * z0 / 4 + (speed - 1) * 1.5
    n = int(cl(2 + motion, 2, 12))
    acc = None
    for k in range(n):
        tk = min(t + shutter * k / n, s['t1'] - 1e-4)
        M = E.cam_matrix(*camera(tk))
        fr = cv2.warpAffine(seg.at(src_of(s, tk)), M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
        acc = fr if acc is None else acc + fr
    return acc / (n * 255.0)

# ---------------------------------------------------------------- yazilar
HOOK1 = E.text_sprite('I made the volume', 120, WHITE, sw=11, shadow=PINK_D + (255,), sh_off=(7, 10))
HOOK2 = E.text_sprite('slider SCREAM.', 165, PINK, sw=13, shadow=(45, 43, 41, 200), sh_off=(9, 12))
TAG1 = E.text_sprite('Even the sliders', 96, GRAPHITE, sw=1)
TAG2 = E.text_sprite('have feelings.', 96, PINK_D, sw=1)
PILL = E.pill_sprite('Coming soon on Steam', 52)
BODYF = E.BODY

_capcache = {}
def caption(text, size, maxw=960):
    key = (text, int(size))
    if key in _capcache: return _capcache[key]
    f = E.font(BODYF, int(size), 800)
    d0 = ImageDraw.Draw(Image.new('RGBA', (8, 8)))
    l, t_, r, b = d0.textbbox((0, 0), text, font=f)
    if r - l > maxw:
        f = E.font(BODYF, int(size * maxw / (r - l)), 800); l, t_, r, b = d0.textbbox((0, 0), text, font=f)
    px, py = int(size * 0.32) + 8, int(size * 0.18) + 6
    w, h = r - l + 2 * px, b - t_ + 2 * py
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=max(6, int(size * 0.18)), fill=(12, 12, 14, 205))
    d.text((px - l, py - t_), text, font=f, fill=(255, 255, 255))
    spr = E.pil2f(im); _capcache[key] = spr
    return spr

def caption_at(t):
    """(metin, boyut, alfa) - CC altyazi; boyutu slider yuzdesini izler."""
    s = shot_at(t)
    if s is None: return None
    if s['name'] == 'A':
        return '[SCREAMING]', 118, 1.0
    if s['name'] == 'D':
        u = t - s['t0']
        return '[normal slider noises]', 62, cl(u / 0.15) * (1 - sm((u - 1.05) / 0.15))
    if s['name'] == 'E':
        src = src_of(s, t)
        if src < 12.18: return None
        p = pct(src)
        size = 44 + 0.78 * p
        if src < 13.75: txt = '[SCREAMING]'
        elif src < 14.55: txt = '[screaming quietly]'
        elif src < 16.15: txt = '[SCREAMING INTENSIFIES]'
        else: return '[heavy breathing]', 58, cl((src - 16.15) / 0.1) * (1 - sm((t - (T_END0 - 0.35)) / 0.2))
        return txt, size, cl((src - 12.18) / 0.06)
    return None

# ---------------------------------------------------------------- render
def render(out, preview=False):
    nfr = int(round(TOTAL * FPS))
    segs = {s['name']: Seg(s['s0'] - 0.05, s['s1'] + 0.05) for s in SHOTS}
    crumbs = E.Crumbs(seed=3)
    emask = E.EraseMask(); prog_prev = 0.0
    ow, oh = (540, 960) if preview else (W, H)
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{ow}x{oh}', '-r', str(FPS),
                            '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast' if preview else 'slow', '-crf', '22' if preview else '15',
                            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    dt = 1 / FPS
    end_strokes = E.END_SCR_STROKES
    for fi in range(nfr):
        t = fi / FPS
        crumbs.step(dt)
        e_run0, e_run1 = T_END0 + 0.10, T_END0 + 0.90
        if e_run0 <= t <= e_run1 + dt:
            pr = cl((t - e_run0) / (e_run1 - e_run0))
            emask.stamp_path(E.end_run_at, prog_prev, pr, 250); prog_prev = pr
            (hx, hy), _ = E.end_run_at(pr)
            if 0 < hx < W: crumbs.emit(hx - 120, hy + 150, 7)
        sh, fl, ca = fx_at(t)
        if t < T_END0:
            s = shot_at(t)
            f = grade_ui(video_frame(t, segs))
            # kanca yazisi (A + B basi)
            if t < S['B']['t0'] + 0.9:
                for spr, y, t0 in ((HOOK1, 300, 0.0), (HOOK2, 470, 0.10)):
                    uu = t - t0
                    if uu < 0: continue
                    k = cl(uu / 0.10)
                    sc = 1 + 1.4 * (1 - k) ** 2
                    a = cl(uu / 0.04) * (1 - sm((t - (S['B']['t0'] + 0.6)) / 0.3))
                    place(f, spr, 540, y, scale=sc, rot=-0.035 if t0 == 0 else 0.03, alpha=a)
            # CC altyazi
            c = caption_at(t)
            if c and c[2] > 0.01:
                txt, size, a = c
                size = int(round(size / 2) * 2)
                spr = caption(txt, size)
                jit = 0
                if s['name'] in ('A', 'E') and txt.isupper():
                    jit = int(6 * fx_at(t)[0])
                place(f, spr, 540 + (jit * math.sin(t * 90)), 1470 + jit * math.cos(t * 77), alpha=a)
            # cikis: karalama kaplar
            if t >= T_END0 - 0.42:
                pr = (t - (T_END0 - 0.42)) / 0.40
                k_pap = sm((t - (T_END0 - 0.16)) / 0.16)
                if k_pap > 0: f = f * (1 - k_pap) + E.PAPER_IMG * k_pap
                E.over(f, E.draw_strokes(end_strokes, prog=eoc(pr), width=8, alpha=0.66, seed=2))
            crumbs.draw(f)
            if fl > 0.003: f = f + (1 - f) * fl
            f = E.chroma(f, ca)
            f = E.grain(f, 0.012)
        else:
            f = end_card(t, emask, crumbs, sh, fl, ca)
        o = np.clip(f * 255 + 0.5, 0, 255).astype(np.uint8)
        if preview: o = cv2.resize(o, (ow, oh), interpolation=cv2.INTER_AREA)
        enc.stdin.write(o.tobytes())
        if fi % 30 == 0: print(f'  kare {fi}/{nfr} t={t:.2f}', flush=True)
    enc.stdin.close(); enc.wait()

place = E.place
def grade_ui(f):
    l = (f[..., 0] * 0.299 + f[..., 1] * 0.587 + f[..., 2] * 0.114)[..., None]
    f = l + (f - l) * 1.08
    f = (f - 0.5) * 1.05 + 0.5
    return f * (1 - (1 - E.VIG) * 0.7)
LOGO_Y = E.LOGO_Y
DIST = None
def end_card(t, emask, crumbs, sh, fl, ca):
    u = t - T_END0
    f = E.PAPER_IMG.copy()
    m_end = emask.full()
    tmp = E.PAPER_IMG.copy()
    pop = 1 + 0.07 * math.exp(-max(0, t - E_LOGO) / 0.09) * (t >= E_LOGO)
    place(tmp, E.TXT_LOGO, 540, LOGO_Y + 6 * math.sin(max(0, t - E_LOGO) * 3.2), scale=pop)
    f = tmp * m_end + f * (1 - m_end)
    pu = (t - (E_LOGO + 0.02)) / 0.22
    if pu > 0:
        ul = E.bezier((180, LOGO_Y + 165), (540, LOGO_Y + 210), (900, LOGO_Y + 150))
        im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        n = int(len(ul) * eoc(pu))
        if n > 1: d.line([tuple(map(float, p)) for p in ul[:n]], fill=PINK + (255,), width=22, joint='curve')
        E.over(f, E.pil2f(im))
    dis = 1 - sm((t - (E_LOGO + 0.05)) / 0.45)
    if dis > 0:
        scr = E.END_SCR.copy(); scr[..., 3] *= (1 - m_end[..., 0]) * dis; E.over(f, scr)
    if T_END0 + 0.10 <= t <= T_END0 + 0.92:
        pr = cl((t - (T_END0 + 0.10)) / 0.80)
        (hx, hy), _ = E.end_run_at(pr)
        fr = E.RUN[int(t * 16) % 8]
        (gx, gy), _ = E.end_run_at(max(0, pr - 0.04))
        place(f, fr, gx, gy, scale=1.45, alpha=0.35)
        place(f, fr, hx, hy, scale=1.45, rot=0.05 * math.sin(t * 40))
    pt = (t - (E_LOGO + 0.25)) / 0.45
    if pt > 0: place(f, E.reveal(TAG1, pt, soft=50), 540, 985, rot=-0.02)
    pt2 = (t - (E_LOGO + 0.55)) / 0.40
    if pt2 > 0: place(f, E.reveal(TAG2, pt2, soft=50), 540, 1090, rot=-0.02)
    pw = (t - (E_LOGO + 0.75)) / 0.32
    if pw > 0:
        fr = E.WAVE[int((t - E_LOGO) * 11) % 8]
        place(f, fr, 540, lerp(2050, 1375, eob(pw, 1.6)), scale=1.5, rot=0.04 * math.sin(t * 5))
    pp = (t - (E_LOGO + 1.00)) / 0.25
    if pp > 0: place(f, PILL, 540, 1680, scale=eob(pp, 2.2))
    pd = (t - (E_LOGO + 0.30)) / 0.3
    if pd > 0: place(f, caption('[distant screaming]', 40), 540, 400, alpha=cl(pd) * 0.9)
    crumbs.draw(f)
    if sh > 0.01:
        sx, sy, rot = E.shake_xy(t, sh)
        f = cv2.warpAffine(f, np.array([[1, 0, sx], [0, 1, sy]], np.float32), (W, H), borderMode=cv2.BORDER_REFLECT)
    kb = 1 + 0.03 * sm((t - E_LOGO) / (TOTAL - E_LOGO))
    if kb > 1.0005:
        M = np.array([[kb, 0, W / 2 * (1 - kb)], [0, kb, H / 2 * (1 - kb)]], np.float32)
        f = cv2.warpAffine(f, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    f = f * (1 - (1 - E.VIG) * 0.45)
    if fl > 0.003: f = f + (1 - f) * fl
    f = E.chroma(f, ca)
    return E.grain(f, 0.010)

def meta():
    return dict(total=TOTAL, end0=T_END0, e_logo=E_LOGO,
                shots=[dict(name=s['name'], t0=s['t0'], t1=s['t1'], s0=s['s0'], s1=s['s1']) for s in SHOTS])

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('-o', default=os.path.join(HERE, 'video.mp4'))
    ap.add_argument('--preview', action='store_true'); ap.add_argument('--meta', action='store_true')
    a = ap.parse_args()
    print({s['name']: (round(s['t0'], 2), round(s['t1'], 2)) for s in SHOTS}, 'END0', T_END0)
    json.dump(meta(), open(os.path.join(HERE, 'meta.json'), 'w'))
    if not a.meta: render(a.o, preview=a.preview)
