#!/usr/bin/env python3
"""Eraiser - Movie_024 fragman kurgusu.

Kare seviyesinde render: zaman haritasi (speed ramp, jump cut), kamera (zoom/pan/sarsinti),
motion blur, renk, bloom, kromatik sapma, letterbox, karalama/silgi gecisleri, kinetik yazi,
el cizimi doodle, silgi kirintisi partikulleri, son kart. Ses ayri: audio.py.
"""
import os, sys, math, json, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Ara dosyalar (src.rgb, game.wav, mi.rgb, music.wav, meta.json, fontlar) repoya girmez: FRAGMAN_WORK
HERE = os.environ.get('FRAGMAN_WORK', '/tmp/fragman')
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(HERE, 'fonts')
HAND = os.path.join(FONTS, 'PatrickHand-Regular.ttf')
BODY = os.path.join(FONTS, 'Nunito-var.ttf')
W, H, FPS, SFPS = 1080, 1920, 30, 60
SRC = np.memmap(os.path.join(HERE, 'src.rgb'), dtype=np.uint8, mode='r').reshape(-1, H, W, 3)
NS = SRC.shape[0]
Z0 = 1.09          # taban zoom: alttaki can barini kadrajdan atar
CROP_BOTTOM = 1770

GRAPHITE = (45, 43, 41); PINK = (242, 143, 150); PINK_D = (217, 112, 125)
CREAM = (248, 237, 224); PAPER = (246, 241, 230); KILIF = (95, 134, 184)
WHITE = (255, 255, 255)

# ---------------------------------------------------------------- easing
def cl(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def sm(x): x = cl(x); return x * x * (3 - 2 * x)
def eoc(x): x = cl(x); return 1 - (1 - x) ** 3
def eoe(x): x = cl(x); return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)
def eob(x, s=1.9): x = cl(x) - 1; return 1 + x * x * ((s + 1) * x + s)
def eio(x): x = cl(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def lerp(a, b, t): return a + (b - a) * t

# ---------------------------------------------------------------- timeline
SFX = []           # (zaman, tur, parametreler) -> audio.py okur
def sfx(t, kind, **kw): SFX.append(dict(t=round(t, 4), kind=kind, **kw))

INTRO_REVEAL = 0.55      # silgi bu anda girer, video alttan akmaya baslar
INTRO_PASS = (0.55, 1.55)

# S2 speed ramp tablosu (kaynak zamani -> cikis zamani)
def _v2(s):
    a = sm((s - 1.85) / 0.12)
    b = 1 - sm((s - 2.25) / 0.45)
    return 1 - 0.62 * min(a, b)
_s2 = np.linspace(1.85, 2.80, 4001)
_mid = (_s2[1:] + _s2[:-1]) / 2
_o2 = np.concatenate([[0], np.cumsum(np.diff(_s2) / np.array([_v2(s) for s in _mid]))])

SHOTS = []
def shot(name, dur, src, cam):
    t0 = SHOTS[-1]['t1'] if SHOTS else INTRO_REVEAL
    SHOTS.append(dict(name=name, t0=t0, t1=t0 + dur, dur=dur, src=src, cam=cam))

def cam_s1(u, d):
    z = Z0 + 0.32 * (1 - eoc(u / 1.0))
    return z, 530 + 10 * math.sin(u * 1.7), 1000
shot('S1', 1.85, lambda u: u, cam_s1)
shot('S2', float(_o2[-1]), lambda u: float(np.interp(u, _o2, _s2)),
     lambda u, d: (Z0 + 0.09 * sm(u / d), 540, 930))
shot('S3', 1.357, lambda u: 2.80 + u,
     lambda u, d: (1.18 + 0.05 * u / d + 0.13 * math.exp(-u * 11), 520, 880))
shot('S4', 0.905, lambda u: 4.795 + u,
     lambda u, d: (1.32 + 0.06 * u / d, 430, 860))
def cam_s5(u, d):
    k = eoe(u / 0.16)
    return (lerp(1.38, 2.12, k) + 0.06 * u / d, lerp(430, 262, k), lerp(860, 700, k))
shot('S5', 0.28 / 0.35, lambda u: 5.70 + 0.35 * u, cam_s5)
def cam_s6(u, d):
    k = eio(u / 0.22)
    return (lerp(2.18, Z0 + 0.04, k), lerp(262, 540, k), lerp(700, 930, k))
shot('S6', 0.72, lambda u: 5.98 + u, cam_s6)
END0 = SHOTS[-1]['t1']
END_DUR = 12.0 - END0
TOTAL = END0 + END_DUR
S = {s['name']: s for s in SHOTS}

def shot_at(t):
    for s in SHOTS:
        if s['t0'] <= t < s['t1'] + 1e-9: return s
    return None

def src_time(t):
    s = shot_at(t)
    return None if s is None else s['src'](t - s['t0'])

# ---------------------------------------------------------------- olaylar (sarsinti / flas / kromatik)
EVENTS = []   # (t, shake, flash, ca)
def hit(t, shake=0.0, flash=0.0, ca=0.0): EVENTS.append((t, shake, flash, ca))

S2t, S3t, S4t, S5t, S6t = S['S2']['t0'], S['S3']['t0'], S['S4']['t0'], S['S5']['t0'], S['S6']['t0']
T_SLAM2 = S3t + 0.13
BLINK = S5t + (5.783 - 5.70) / 0.35
hit(S['S1']['t0'] + 1.00, shake=0.35, ca=0.25)          # oyundaki yuksek efekt sesi
hit(S3t, shake=1.0, flash=0.75, ca=1.0)                 # DUNYAYI
hit(T_SLAM2, shake=0.7, flash=0.25, ca=0.7)             # AC.
hit(S4t, flash=0.35, ca=0.6)                            # jump cut
hit(S5t + 0.02, ca=0.8, shake=0.25)                     # snap zoom
hit(BLINK, flash=0.18)
hit(S6t + 0.02, ca=0.7)
E_LOGO = END0 + 0.92
hit(E_LOGO, shake=0.55, ca=0.5)

def fx_at(t):
    sh = fl = ca = 0.0
    for te, a, b, c in EVENTS:
        if t >= te:
            dt = t - te
            sh += a * math.exp(-dt / 0.16)
            fl += b * math.exp(-dt / 0.07)
            ca += c * math.exp(-dt / 0.14)
    return sh, min(fl, 1.0), ca

def shake_xy(t, amp):
    if amp < 1e-3: return 0.0, 0.0, 0.0
    sx = amp * 30 * (0.6 * math.sin(t * 91.0 + 1.3) + 0.4 * math.sin(t * 157.0 + 4.1))
    sy = amp * 30 * (0.6 * math.sin(t * 77.0 + 2.7) + 0.4 * math.sin(t * 133.0 + 0.4))
    rot = amp * 0.014 * math.sin(t * 63.0 + 0.9)
    return sx, sy, rot

def camera(t):
    s = shot_at(t)
    z, cx, cy = s['cam'](t - s['t0'], s['dur'])
    hw, hh = W / 2 / z, H / 2 / z
    cx = cl(cx, hw, W - hw)
    cy = cl(cy, hh, CROP_BOTTOM - hh)
    sh, _, _ = fx_at(t)
    sx, sy, rot = shake_xy(t, sh)
    return z, cx, cy, rot, sx, sy

def cam_matrix(z, cx, cy, rot, sx, sy):
    c, s_ = math.cos(rot), math.sin(rot)
    M = np.array([[z * c, -z * s_, 0], [z * s_, z * c, 0]], np.float64)
    M[:, 2] = np.array([W / 2 + sx, H / 2 + sy]) - M[:, :2] @ np.array([cx, cy])
    return M

def src2out(p, t):
    M = cam_matrix(*camera(t))
    return M[:, :2] @ np.array(p, float) + M[:, 2]

# ---------------------------------------------------------------- kaynak kare: minimap temizligi + ara kare
MM_CX, MM_CY, MM_R = 893, 176, 186
_rows = np.arange(0, MM_CY + MM_R + 1)
_half = np.sqrt(np.clip(MM_R ** 2 - (_rows - MM_CY) ** 2, 0, None))
_xl = np.clip((MM_CX - _half).astype(int) - 4, 0, W - 1)
_xr = np.clip((MM_CX + _half).astype(int) + 4, 0, W - 1)
_valid = _half > 0
X0R = 690
_xs = np.arange(X0R, W)
_wt = np.clip((_xs[None, :] - _xl[:, None]) / np.maximum(_xr - _xl, 1)[:, None], 0, 1).astype(np.float32)
_hole = ((_xs[None, :] >= _xl[:, None]) & (_xs[None, :] <= _xr[:, None]) & _valid[:, None])
_hole_soft = cv2.GaussianBlur(_hole.astype(np.float32), (0, 0), 3)[..., None]

_cache = {}
def clean(i):
    i = int(cl(i, 0, NS - 1))
    if i in _cache: return _cache[i]
    f = np.array(SRC[i])
    roi = f[:len(_rows), X0R:].astype(np.float32)
    L = f[_rows, _xl].astype(np.float32)[:, None, :]
    R = f[_rows, np.minimum(_xr, W - 1)].astype(np.float32)[:, None, :]
    fill = L * (1 - _wt[..., None]) + R * _wt[..., None]
    fill = cv2.GaussianBlur(fill, (0, 0), 6)
    roi = roi * (1 - _hole_soft) + fill * _hole_soft
    f[:len(_rows), X0R:] = np.clip(roi, 0, 255).astype(np.uint8)
    if len(_cache) > 40: _cache.pop(next(iter(_cache)))
    _cache[i] = f
    return f

MI = None
MI_T0, MI_FPS = 1.70, 240
if os.path.exists(os.path.join(HERE, 'mi.rgb')) and os.environ.get('USE_MI', '1') == '1':
    MI = np.memmap(os.path.join(HERE, 'mi.rgb'), dtype=np.uint8, mode='r').reshape(-1, H, W, 3)
_mcache = {}
def mi_clean(j):
    if j in _mcache: return _mcache[j]
    f = np.array(MI[j])
    roi = f[:len(_rows), X0R:].astype(np.float32)
    L = f[_rows, _xl].astype(np.float32)[:, None, :]
    R = f[_rows, np.minimum(_xr, W - 1)].astype(np.float32)[:, None, :]
    fill = cv2.GaussianBlur(L * (1 - _wt[..., None]) + R * _wt[..., None], (0, 0), 6)
    f[:len(_rows), X0R:] = np.clip(roi * (1 - _hole_soft) + fill * _hole_soft, 0, 255).astype(np.uint8)
    if len(_mcache) > 20: _mcache.pop(next(iter(_mcache)))
    _mcache[j] = f
    return f

def sample(ts, slow=False):
    if MI is not None and slow and MI_T0 + 0.01 <= ts < MI_T0 + (MI.shape[0] - 2) / MI_FPS:
        return mi_clean(int(round((ts - MI_T0) * MI_FPS)))
    x = ts * SFPS
    i0 = int(math.floor(x)); a = x - i0
    if a < 0.04 or i0 + 1 >= NS: return clean(i0)
    if a > 0.96: return clean(i0 + 1)
    return cv2.addWeighted(clean(i0), 1 - a, clean(i0 + 1), a, 0)

# ---------------------------------------------------------------- renk
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H / 2) / (H / 2)) ** 2) / math.sqrt(2)
VIG = (1 - 0.30 * _r ** 2.3).astype(np.float32)[..., None]

def grade(f, sat=1.12, vig=1.0):
    l = (f[..., 0] * 0.299 + f[..., 1] * 0.587 + f[..., 2] * 0.114)[..., None]
    f = l + (f - l) * sat
    f = (f - 0.5) * 1.07 + 0.5
    f[..., 0] *= 1.015; f[..., 2] *= 0.985
    small = cv2.resize(f, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
    hi = cv2.GaussianBlur(np.clip(small - 0.70, 0, 1) * 2.0, (0, 0), 6)
    f = f + cv2.resize(hi, (W, H)) * 0.32
    v = VIG if vig == 1.0 else (1 - (1 - VIG) * vig)
    return f * v

def chroma(f, ca):
    if ca < 0.03: return f
    k = 0.0085 * ca
    out = f.copy()
    for ch, s in ((0, 1 + k), (2, 1 - k)):
        M = np.array([[s, 0, W / 2 * (1 - s)], [0, s, H / 2 * (1 - s)]], np.float32)
        out[..., ch] = cv2.warpAffine(np.ascontiguousarray(f[..., ch]), M, (W, H), borderMode=cv2.BORDER_REFLECT)
    return out

_grng = np.random.default_rng(7)
def grain(f, amt=0.013):
    n = _grng.normal(0, amt, (H // 2, W // 2)).astype(np.float32)
    return f + cv2.resize(n, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]

# ---------------------------------------------------------------- RGBA katman yardimcilari
def over(dst, rgba, x=0, y=0):
    """float dst (H,W,3) uzerine float rgba (h,w,4) premultiplied degil; x,y sol ust."""
    h, w = rgba.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0: return
    s = rgba[y0 - y:y1 - y, x0 - x:x1 - x]
    a = s[..., 3:4]
    dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - a) + s[..., :3] * a

def place(dst, spr, cx, cy, scale=1.0, rot=0.0, alpha=1.0, flip=False):
    """spr float rgba; merkezi (cx,cy) olacak sekilde olcek/donus ile cizer."""
    if alpha <= 0.002 or scale <= 0.01: return
    h, w = spr.shape[:2]
    if flip: spr = spr[:, ::-1]
    c, s_ = math.cos(rot), math.sin(rot)
    # cikti kutusu
    R = max(w, h) * scale * 0.75 + 4
    bx0, by0 = int(cx - R), int(cy - R)
    bw = bh = int(2 * R)
    M = np.array([[scale * c, -scale * s_, 0], [scale * s_, scale * c, 0]], np.float64)
    M[:, 2] = np.array([cx - bx0, cy - by0]) - M[:, :2] @ np.array([w / 2, h / 2])
    out = cv2.warpAffine(spr, M, (bw, bh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    if alpha < 1: out[..., 3] *= alpha
    over(dst, out, bx0, by0)

def pil2f(im): return np.asarray(im.convert('RGBA'), dtype=np.float32) / 255.0

def font(path, size, wght=None):
    f = ImageFont.truetype(path, size)
    if wght is not None:
        try: f.set_variation_by_axes([wght])
        except Exception: pass
    return f

def text_sprite(s, size, fill, stroke=GRAPHITE, sw=10, halo=None, hw=0, shadow=None, path=HAND, wght=None, sh_off=(8, 10)):
    f = font(path, size, wght)
    tmp = ImageDraw.Draw(Image.new('RGBA', (8, 8)))
    big = max(sw, hw)
    l, t_, r, b = tmp.textbbox((0, 0), s, font=f, stroke_width=big)
    pad = big + 30
    w, h = r - l + 2 * pad + abs(sh_off[0]), b - t_ + 2 * pad + abs(sh_off[1])
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o = (pad - l, pad - t_)
    if shadow:
        sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((o[0] + sh_off[0], o[1] + sh_off[1]), s, font=f, fill=shadow, stroke_width=big, stroke_fill=shadow)
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(2)))
    if halo:
        d.text(o, s, font=f, fill=halo, stroke_width=hw, stroke_fill=halo)
    d.text(o, s, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke)
    return pil2f(im)

def wipe_mask(w, h, prog, soft=40, jag=0.0, seed=0, reverse=False):
    """soldan saga ilerleyen yumusak maske (1 = gorunur)."""
    xs = np.arange(w, dtype=np.float32)[None, :]
    edge = prog * (w + 2 * soft) - soft
    if jag:
        ys = np.arange(h, dtype=np.float32)[:, None]
        edge = edge + jag * (np.sin(ys * 0.045 + seed) * 0.6 + np.sin(ys * 0.13 + seed * 2) * 0.4)
    m = np.clip((edge - xs) / soft + 0.5, 0, 1)
    if reverse: m = 1 - m
    return np.broadcast_to(m, (h, w)).astype(np.float32)

def reveal(spr, prog, **kw):
    if prog >= 1: return spr
    out = spr.copy()
    out[..., 3] *= wipe_mask(spr.shape[1], spr.shape[0], prog, **kw)
    return out

# ---------------------------------------------------------------- kagit + karalama
def paper_base(seed=3):
    rng = np.random.default_rng(seed)
    p = np.ones((H, W, 3), np.float32) * (np.array(PAPER, np.float32) / 255)
    n = cv2.GaussianBlur(rng.normal(0, 1, (H // 3, W // 3)).astype(np.float32), (0, 0), 1.2)
    n = cv2.resize(n, (W, H))[..., None]
    p = p * (1 + 0.018 * n)
    for y in range(96, H, 72):   # sitedeki kagit cizgileri
        p[y:y + 2] = p[y:y + 2] * 0.93
    p[:, 120:123] = p[:, 120:123] * np.array([1.0, 0.86, 0.86], np.float32)   # kenar boslugu cizgisi
    return np.clip(p, 0, 1)

def scribble_strokes(seed, n, y0, y1, **_):
    """Organik kalem karalamasi: egriligi surekli degisen, ekrani bir uctan obur uca gecen ilmekler."""
    rng = np.random.default_rng(seed)
    strokes = []
    for k in range(n):
        dirx = 1 if k % 2 == 0 else -1
        x = -120.0 if dirx > 0 else W + 120.0
        y = lerp(y0, y1, (k + rng.uniform(0.1, 0.9)) / n)
        th = rng.uniform(0, 2 * np.pi)
        sp = rng.uniform(24, 36)
        om0 = rng.uniform(0.17, 0.30) * rng.choice([-1, 1])
        dx, dy = dirx * rng.uniform(5.5, 9.0), rng.uniform(-2.0, 2.0)
        p1, p2, p3 = rng.uniform(0, 6.28, 3)
        pts = []
        for i in range(2400):
            om = om0 * (1 + 0.55 * math.sin(i * 0.011 + p1)) + 0.07 * math.sin(i * 0.047 + p2)
            th += om
            x += sp * 0.62 * math.cos(th) + dx * (1 + 0.5 * math.sin(i * 0.02 + p3))
            y += sp * 0.62 * math.sin(th) + dy
            if y < y0 - 60 or y > y1 + 60: dy = -dy
            pts.append((x, y))
            if (dirx > 0 and x > W + 160) or (dirx < 0 and x < -160): break
        strokes.append(np.array(pts))
    return strokes

def draw_strokes(strokes, prog=1.0, width=6, color=GRAPHITE, alpha=0.62, ss=2, seed=0):
    """PIL ile kalem cizgisi; prog = her cizginin cizilmis orani."""
    im = Image.new('L', (W * ss // 2, H * ss // 2), 0)
    d = ImageDraw.Draw(im)
    k = ss / 2
    wr = np.random.default_rng(seed + 100)
    for i, st in enumerate(strokes):
        n = int(len(st) * cl(prog))
        wi = width * wr.uniform(0.6, 1.35)
        val = int(255 * wr.uniform(0.6, 1.0))
        if n < 2: continue
        pts = [(float(a * k), float(b * k)) for a, b in st[:n]]
        d.line(pts, fill=val, width=max(1, int(wi * k)), joint='curve')
    a = np.asarray(im, np.float32) / 255
    a = cv2.resize(a, (W, H), interpolation=cv2.INTER_LINEAR)
    rng = np.random.default_rng(seed)
    tex = cv2.resize(rng.uniform(0.55, 1.0, (H // 2, W // 2)).astype(np.float32), (W, H))
    a = a * tex * alpha
    rgba = np.zeros((H, W, 4), np.float32)
    rgba[..., :3] = np.array(color, np.float32) / 255
    rgba[..., 3] = a
    return rgba

# ---------------------------------------------------------------- silgi sprite'lari
def load_sheet(path, n):
    im = Image.open(path).convert('RGBA')
    fw = im.width // n
    return [pil2f(im.crop((i * fw, 0, (i + 1) * fw, im.height))) for i in range(n)]
RUN = load_sheet(os.path.join(REPO, 'gorseller/silgi-adam-kosu.webp'), 8)
WAVE = load_sheet(os.path.join(REPO, 'gorseller/silgi-adam-el.webp'), 8)

# ---------------------------------------------------------------- partikuller (silgi kirintisi)
class Crumbs:
    COLS = [PINK, CREAM, CREAM, (232, 214, 205), (170, 160, 158), PINK_D]
    def __init__(self, seed=11):
        self.p = []; self.rng = np.random.default_rng(seed)
    def emit(self, x, y, n, vx=(-500, 500), vy=(-900, -300), size=(7, 16), life=(0.45, 0.8)):
        r = self.rng
        for _ in range(int(n)):
            self.p.append(dict(x=x + r.normal(0, 14), y=y + r.normal(0, 8), vx=r.uniform(*vx), vy=r.uniform(*vy),
                               s=r.uniform(*size), a=r.uniform(0, 6.28), va=r.uniform(-14, 14),
                               age=0.0, life=r.uniform(*life), c=self.COLS[r.integers(len(self.COLS))],
                               e=r.uniform(1.2, 2.0)))
    def step(self, dt):
        for q in self.p:
            q['age'] += dt; q['vy'] += 2600 * dt; q['vx'] *= (1 - 1.5 * dt)
            q['x'] += q['vx'] * dt; q['y'] += q['vy'] * dt; q['a'] += q['va'] * dt
        self.p = [q for q in self.p if q['age'] < q['life'] and q['y'] < H + 60]
    def draw(self, dst):
        if not self.p: return
        im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for q in self.p:
            fade = 1 - sm((q['age'] / q['life'] - 0.6) / 0.4)
            s = q['s']; e = q['e']
            ang = np.linspace(0, 2 * np.pi, 10, endpoint=False)
            ca, sa = math.cos(q['a']), math.sin(q['a'])
            pts = [(q['x'] + (s * e * math.cos(t)) * ca - (s * math.sin(t)) * sa,
                    q['y'] + (s * e * math.cos(t)) * sa + (s * math.sin(t)) * ca) for t in ang]
            d.polygon(pts, fill=q['c'] + (int(255 * fade),), outline=GRAPHITE + (int(200 * fade),), width=2)
        over(dst, pil2f(im))

# ---------------------------------------------------------------- statik varliklar
print('varliklar hazirlaniyor...', flush=True)
PAPER_IMG = paper_base()
INTRO_SCR = draw_strokes(scribble_strokes(5, 19, -60, H + 60), width=7, alpha=0.60, seed=1)
TXT_KARA = text_sprite('ERASE THE', 200, GRAPHITE, stroke=GRAPHITE, sw=3, halo=PAPER, hw=22)
TXT_SIL = text_sprite('SCRIBBLE', 240, PINK, stroke=GRAPHITE, sw=9, halo=PAPER, hw=26, shadow=(45, 43, 41, 110))
TXT_DUN = text_sprite('UNLOCK THE', 170, WHITE, sw=12, shadow=PINK_D + (255,), sh_off=(9, 12))
TXT_AC = text_sprite('WORLD.', 300, PINK, sw=13, shadow=(45, 43, 41, 200), sh_off=(10, 14))
TXT_NOTE = text_sprite('teapot elephant?!', 92, GRAPHITE, sw=2, halo=WHITE, hw=14)
TXT_KIRP = text_sprite('*blink*', 96, GRAPHITE, sw=2, halo=WHITE, hw=14)
END_SCR_STROKES = scribble_strokes(9, 18, -60, H + 60)
END_SCR = draw_strokes(END_SCR_STROKES, width=8, alpha=0.66, seed=2)
TXT_LOGO = text_sprite('Eraiser', 315, GRAPHITE, sw=2, shadow=(45, 43, 41, 60), sh_off=(6, 9))
TXT_TAG = text_sprite('Erase the scribble.', 92, GRAPHITE, sw=1)
TXT_TAG2 = text_sprite('Unlock the world.', 92, PINK_D, sw=1)

def pill_sprite(label, size=50):
    f = font(BODY, size, 800)
    d0 = ImageDraw.Draw(Image.new('RGBA', (8, 8)))
    l, t_, r, b = d0.textbbox((0, 0), label, font=f)
    pw, ph = r - l + 80, b - t_ + 44
    im = Image.new('RGBA', (pw + 20, ph + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((8, 12, pw + 8, ph + 12), radius=ph // 2, fill=(45, 43, 41, 90))
    d.rounded_rectangle((2, 2, pw, ph), radius=ph // 2, fill=KILIF, outline=GRAPHITE, width=5)
    d.text((40 - l, 22 - t_), label, font=f, fill=WHITE)
    return pil2f(im)
PILL = pill_sprite('Coming soon on Steam', 52)

def star_sprite(r, col):
    s = int(r * 2.6)
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = s / 2; pts = []
    for i in range(8):
        a = i * math.pi / 4 - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.32
        pts.append((c + rr * math.cos(a), c + rr * math.sin(a)))
    d.polygon(pts, fill=col, outline=GRAPHITE, width=max(3, int(r * 0.09)))
    return pil2f(im)
STARS = [star_sprite(70, PINK), star_sprite(46, (255, 236, 140)), star_sprite(36, WHITE), star_sprite(54, (255, 236, 140)), star_sprite(30, PINK)]

# silgi zig-zag gecis yolu (intro)
def zigzag(passes, r_over=0.62):
    pts = []
    band = H / passes
    for k in range(passes):
        y = band * (k + 0.5)
        xa, xb = (-260, W + 260) if k % 2 == 0 else (W + 260, -260)
        pts.append((xa, y - band * 0.12)); pts.append((xb, y + band * 0.12))
    pts = np.array(pts, float)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    return pts, cum, band * r_over

ZZ_PTS, ZZ_CUM, ZZ_R = zigzag(3)
def zz_at(prog):
    L = ZZ_CUM[-1] * cl(prog)
    i = min(int(np.searchsorted(ZZ_CUM, L, side='right') - 1), len(ZZ_PTS) - 2)
    a = (L - ZZ_CUM[i]) / max(ZZ_CUM[i + 1] - ZZ_CUM[i], 1e-6)
    p = ZZ_PTS[i] + (ZZ_PTS[i + 1] - ZZ_PTS[i]) * a
    d = ZZ_PTS[i + 1] - ZZ_PTS[i]
    return p, d

class EraseMask:
    """Kumulatif silinmis bolge (1 = silindi), 1/4 cozunurlukte."""
    def __init__(self):
        self.m = np.zeros((H // 4, W // 4), np.float32)
        self.last = 0.0
        self.rng = np.random.default_rng(5)
    def stamp_path(self, fn, p0, p1, r):
        steps = max(2, int((p1 - p0) * 400))
        for q in np.linspace(p0, p1, steps):
            (x, y), _ = fn(q)
            rr = r * self.rng.uniform(0.94, 1.04)
            cv2.circle(self.m, (int(x / 4), int(y / 4)), int(rr / 4), 1.0, -1)
    def full(self):
        return cv2.resize(cv2.GaussianBlur(self.m, (0, 0), 2.5), (W, H))[..., None]

# ---------------------------------------------------------------- son kart yolu (tek gecis, logo bandi)
LOGO_Y = 720
def end_run_at(prog):
    x = lerp(-300, W + 300, prog)
    y = LOGO_Y + 30 + 18 * math.sin(prog * 18)
    return np.array([x, y]), np.array([1.0, 0.0])

# ---------------------------------------------------------------- doodle (S4)
def wobbly_ellipse(cx, cy, rx, ry, seed=4, turns=1.12, n=160):
    rng = np.random.default_rng(seed)
    t = np.linspace(-0.4, -0.4 + turns * 2 * np.pi, n)
    j = 1 + 0.04 * np.sin(t * 3 + rng.uniform(0, 6)) + 0.02 * np.sin(t * 7)
    return np.stack([cx + rx * j * np.cos(t), cy + ry * j * np.sin(t)], 1)

def draw_poly(dst, pts, prog, width=10, halo=16, color=GRAPHITE):
    n = int(len(pts) * cl(prog))
    if n < 2: return
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    P = [tuple(map(float, p)) for p in pts[:n]]
    d.line(P, fill=WHITE + (255,), width=width + halo, joint='curve')
    d.line(P, fill=color + (255,), width=width, joint='curve')
    over(dst, pil2f(im))

def bezier(p0, p1, p2, n=60):
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 2 * np.array(p0) + 2 * (1 - t) * t * np.array(p1) + t ** 2 * np.array(p2)

# ---------------------------------------------------------------- video katmani
def video_frame(t):
    s = shot_at(t)
    shutter = 0.5 / FPS
    z0, cx0, cy0, *_ = camera(t)
    t1 = min(t + shutter, s['t1'] - 1e-4)
    z1, cx1, cy1, *_ = camera(t1)
    motion = abs(z1 - z0) / z0 * 300 + math.hypot(cx1 - cx0, cy1 - cy0) * z0 / 4
    n = int(cl(2 + motion, 2, 14))
    slow = s['name'] in ('S2',)
    acc = None
    for k in range(n):
        tk = min(t + shutter * k / n, s['t1'] - 1e-4)
        src = sample(s['src'](tk - s['t0']), slow=slow)
        M = cam_matrix(*camera(tk))
        fr = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
        acc = fr if acc is None else acc + fr
    return acc / (n * 255.0)

def sat_at(t):
    # agir cekimde hafif soluk, carpista patlayan renk
    s2 = S['S2']
    if s2['t0'] <= t < s2['t1']:
        u = (t - s2['t0']) / s2['dur']
        return 1.12 - 0.22 * sm(u / 0.3) * (1 - sm((u - 0.85) / 0.15)), 1.0 + 0.6 * sm(u / 0.3)
    if S3t <= t < S3t + 0.6:
        return 1.12 + 0.18 * (1 - (t - S3t) / 0.6), 1.0
    return 1.12, 1.0

def bars_at(t):
    s2 = S['S2']
    if s2['t0'] <= t < S3t:
        return 150 * eoc((t - s2['t0']) / 0.35)
    if S3t <= t < S3t + 0.10:
        return 150 * (1 - (t - S3t) / 0.10)
    return 0

# ---------------------------------------------------------------- ana render
def render(out_path, preview=False, t_from=0.0, t_to=None):
    t_to = TOTAL if t_to is None else t_to
    nframes = int(round(TOTAL * FPS))
    crumbs = Crumbs()
    emask = EraseMask(); prog_prev = 0.0
    emask_end = EraseMask(); endprog_prev = 0.0
    oh = 960 if preview else H; ow = 540 if preview else W
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{ow}x{oh}',
                            '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast' if preview else 'slow',
                            '-crf', '22' if preview else '15', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out_path],
                           stdin=subprocess.PIPE)
    dt = 1 / FPS
    for fi in range(nframes):
        t = fi / FPS
        # --- partikul ve maskeler her karede ilerler (atlanan karelerde de)
        crumbs.step(dt)
        if INTRO_PASS[0] <= t <= INTRO_PASS[1] + dt:
            pr = cl((t - INTRO_PASS[0]) / (INTRO_PASS[1] - INTRO_PASS[0]))
            emask.stamp_path(zz_at, prog_prev, pr, ZZ_R); prog_prev = pr
            (hx, hy), _ = zz_at(pr)
            if 0 < hx < W: crumbs.emit(hx, hy + 120, 9, vy=(-1100, -300))
        e_run0, e_run1 = END0 + 0.10, END0 + 0.90
        if e_run0 <= t <= e_run1 + dt:
            pr = cl((t - e_run0) / (e_run1 - e_run0))
            emask_end.stamp_path(end_run_at, endprog_prev, pr, 250); endprog_prev = pr
            (hx, hy), _ = end_run_at(pr)
            if 0 < hx < W: crumbs.emit(hx - 120, hy + 150, 7)
        s1 = S['S1']
        st = src_time(t)
        if s1['t0'] + 0.35 <= t < S['S2']['t0'] + 0.6 and int(t * FPS) % 1 == 0:
            fx, fy = src2out((505, 1405), t)
            crumbs.emit(fx, fy, 3, vx=(-420, 420), vy=(-700, -200), size=(5, 11))
        if t < t_from - 1e-6 or t > t_to:
            continue

        sh, fl, ca = fx_at(t)
        if t < END0:
            # ================= OYUN BOLUMU =================
            if t >= INTRO_REVEAL:
                sat, vig = sat_at(t)
                f = grade(video_frame(t), sat=sat, vig=vig)
            else:
                f = np.zeros((H, W, 3), np.float32)
            # --- intro: kagit + karalama + el yazisi, silgi zig-zag ile siliniyor
            if t < INTRO_PASS[1] + 0.05:
                pap = PAPER_IMG.copy()
                over(pap, INTRO_SCR)
                pk = (t - 0.04) / 0.30
                if pk > 0: place(pap, reveal(TXT_KARA, eoc(pk), soft=60), 540, 720, rot=-0.05)
                ps = (t - 0.28) / 0.20
                if ps > 0:
                    place(pap, TXT_SIL, 550, 960, scale=lerp(1.5, 1.0, eob(ps)), rot=-0.06 + 0.05 * (1 - eoc(ps)), alpha=cl(ps * 3))
                m = emask.full() if t >= INTRO_PASS[0] else 0.0
                f = f * m + pap * (1 - m)
                if INTRO_PASS[0] <= t <= INTRO_PASS[1]:
                    pr = cl((t - INTRO_PASS[0]) / (INTRO_PASS[1] - INTRO_PASS[0]))
                    (hx, hy), d = zz_at(pr)
                    fr = RUN[int(t * 16) % 8]
                    for g, ga in ((0.06, 0.25), (0.03, 0.45)):
                        (gx, gy), _ = zz_at(max(0, pr - g))
                        place(f, fr, gx, gy, scale=1.9, alpha=ga, flip=d[0] < 0)
                    place(f, fr, hx, hy, scale=1.9, flip=d[0] < 0, rot=0.06 * math.sin(t * 40))
            # --- S1 hafif ara: bir sey yok, kirinti yeter
            # --- S3 yazilari
            if S3t <= t < S['S3']['t1']:
                u = t - S3t
                end_k = cl((t - (S['S3']['t1'] - 0.26)) / 0.26)
                for spr, y, t0 in ((TXT_DUN, 290, 0.0), (TXT_AC, 500, 0.13)):
                    uu = u - t0
                    if uu < 0: continue
                    k = cl(uu / 0.10)
                    sc = 1 + 1.5 * (1 - k) ** 2 + 0.012 * math.sin(uu * 9)
                    sp = spr
                    if end_k > 0:
                        sp = reveal(spr, end_k, soft=30, jag=20, seed=3, reverse=True)
                    place(f, sp, 540, y, scale=sc, rot=-0.04 if t0 == 0 else 0.03, alpha=cl(uu / 0.04))
                if 0 < end_k < 1 and int(t * FPS) % 1 == 0:
                    ex = lerp(80, 1000, end_k)
                    crumbs.emit(ex, 290, 4, vy=(-500, 100)); crumbs.emit(ex, 500, 4, vy=(-500, 100))
            # --- S4 doodle
            if S4t <= t < S['S4']['t1']:
                u = t - S4t
                c = src2out((240, 690), t); z = camera(t)[0]
                ell = wobbly_ellipse(c[0], c[1], 205 * z, 135 * z)
                draw_poly(f, ell, eoc((u - 0.08) / 0.32))
                note_xy = (700, 330)
                pn = (u - 0.30) / 0.30
                if pn > 0: place(f, reveal(TXT_NOTE, eoc(pn), soft=40), note_xy[0], note_xy[1], rot=-0.07)
                tip = (c[0] + 205 * z * 0.72, c[1] - 135 * z * 0.75)
                arr = bezier((700, 405), (690, 560), tip)
                pa = eoc((u - 0.52) / 0.22)
                draw_poly(f, arr, pa, width=9, halo=14)
                if pa >= 1:
                    d = arr[-1] - arr[-6]; d /= np.linalg.norm(d) + 1e-6
                    nrm = np.array([-d[1], d[0]])
                    for sgn in (1, -1):
                        draw_poly(f, np.array([arr[-1] - d * 46 + sgn * nrm * 30, arr[-1]]), 1.0, width=9, halo=14)
            # --- S5 goz kirpma parilti
            if S5t <= t < S['S5']['t1'] + 0.25:
                u = t - BLINK
                if u > -0.02:
                    eyes = src2out((256, 634), t)
                    offs = [(-150, -175, 0), (165, -205, 0.04), (300, -40, 0.08), (-215, 15, 0.06), (60, -300, 0.11)]
                    for (ox, oy, d0), spr in zip(offs, STARS):
                        uu = u - d0
                        if uu <= 0: continue
                        k = eob(uu / 0.16, 2.6)
                        fade = 1 - sm((uu - 0.45) / 0.2)
                        place(f, spr, eyes[0] + ox * 1.0, eyes[1] + oy * 1.0, scale=k * fade, rot=uu * 3.2)
                    pk = (u - 0.05) / 0.14
                    if pk > 0:
                        place(f, TXT_KIRP, eyes[0] + 330, eyes[1] - 300, scale=eob(pk), rot=0.12, alpha=1 - sm((u - 0.55) / 0.2))
            # --- S6 cikis: karalama ekrani kaplar
            s6 = S['S6']
            if s6['t0'] + 0.24 <= t < END0:
                pr = (t - (s6['t0'] + 0.24)) / 0.40
                k_pap = sm((t - (END0 - 0.17)) / 0.17)
                if k_pap > 0:
                    f = f * (1 - k_pap) + PAPER_IMG * k_pap
                over(f, draw_strokes(END_SCR_STROKES, prog=eoc(pr), width=8, alpha=0.66, seed=2))
            crumbs.draw(f)
            bh = int(bars_at(t))
            if bh > 0:
                f[:bh] = 0; f[H - bh:] = 0
            if fl > 0.003: f = f + (1 - f) * fl
            f = chroma(f, ca)
            f = grain(f, 0.014)
        else:
            # ================= SON KART =================
            u = t - END0
            f = PAPER_IMG.copy()
            m_end = emask_end.full()
            # logo: silinen bantta ortaya cikar
            logo_l = np.zeros((H, W, 3), np.float32); tmp = PAPER_IMG.copy()
            pop = 1 + 0.07 * math.exp(-max(0, t - E_LOGO) / 0.09) * (t >= E_LOGO)
            place(tmp, TXT_LOGO, 540, LOGO_Y + 6 * math.sin(max(0, t - E_LOGO) * 3.2), scale=pop)
            f = tmp * m_end + f * (1 - m_end)
            # pembe alt cizgi
            pu = (t - (E_LOGO + 0.02)) / 0.22
            if pu > 0:
                ul = bezier((180, LOGO_Y + 165), (540, LOGO_Y + 210), (900, LOGO_Y + 150))
                im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
                n = int(len(ul) * eoc(pu))
                if n > 1: d.line([tuple(map(float, p)) for p in ul[:n]], fill=PINK + (255,), width=22, joint='curve')
                over(f, pil2f(im))
            # kalan karalama: silinmemis yerlerde, logodan sonra eriyip gider
            dis = 1 - sm((t - (E_LOGO + 0.05)) / 0.45)
            if dis > 0:
                scr = END_SCR.copy()
                scr[..., 3] *= (1 - m_end[..., 0]) * dis
                over(f, scr)
            # kosan silgi
            if END0 + 0.10 <= t <= END0 + 0.92:
                pr = cl((t - (END0 + 0.10)) / 0.80)
                (hx, hy), _ = end_run_at(pr)
                fr = RUN[int(t * 16) % 8]
                (gx, gy), _ = end_run_at(max(0, pr - 0.04))
                place(f, fr, gx, gy, scale=1.45, alpha=0.35)
                place(f, fr, hx, hy, scale=1.45, rot=0.05 * math.sin(t * 40))
            # slogan
            pt = (t - (E_LOGO + 0.30)) / 0.55
            if pt > 0: place(f, reveal(TXT_TAG, pt, soft=50), 540, 985, rot=-0.02)
            pt2 = (t - (E_LOGO + 0.62)) / 0.45
            if pt2 > 0: place(f, reveal(TXT_TAG2, pt2, soft=50), 540, 1090, rot=-0.02)
            # el sallayan silgi
            pw = (t - (E_LOGO + 0.85)) / 0.32
            if pw > 0:
                fr = WAVE[int((t - E_LOGO) * 11) % 8]
                place(f, fr, 540, lerp(2050, 1375, eob(pw, 1.6)), scale=1.5, rot=0.04 * math.sin(t * 5))
            pp = (t - (E_LOGO + 1.20)) / 0.25
            if pp > 0: place(f, PILL, 540, 1680, scale=eob(pp, 2.2))
            crumbs.draw(f)
            if sh > 0.01:
                sx, sy, rot = shake_xy(t, sh)
                M = np.array([[1, 0, sx], [0, 1, sy]], np.float32)
                f = cv2.warpAffine(f, M, (W, H), borderMode=cv2.BORDER_REFLECT)
            kb = 1 + 0.035 * sm((t - E_LOGO) / (TOTAL - E_LOGO))
            if kb > 1.0005:
                M = np.array([[kb, 0, W / 2 * (1 - kb)], [0, kb, H / 2 * (1 - kb)]], np.float32)
                f = cv2.warpAffine(f, M, (W, H), borderMode=cv2.BORDER_REFLECT)
            f = f * (1 - (1 - VIG) * 0.45)
            if fl > 0.003: f = f + (1 - f) * fl
            f = chroma(f, ca)
            f = grain(f, 0.010)
        out = np.clip(f * 255 + 0.5, 0, 255).astype(np.uint8)
        if preview: out = cv2.resize(out, (ow, oh), interpolation=cv2.INTER_AREA)
        enc.stdin.write(out.tobytes())
        if fi % 15 == 0: print(f'  kare {fi}/{nframes}  t={t:.2f}', flush=True)
    enc.stdin.close(); enc.wait()

def dump_meta(path):
    meta = dict(total=TOTAL, intro_reveal=INTRO_REVEAL, intro_pass=INTRO_PASS, end0=END0, e_logo=E_LOGO,
                blink=BLINK, slam=[S3t, T_SLAM2],
                shots=[dict(name=s['name'], t0=s['t0'], t1=s['t1']) for s in SHOTS],
                # ses icin yogun zaman haritasi (cikis t -> kaynak t)
                tmap=[[round(t, 5), (None if src_time(t) is None else round(src_time(t), 5))]
                      for t in np.arange(0, TOTAL, 0.001)],
                sfx=SFX)
    json.dump(meta, open(path, 'w'))

# ---------------------------------------------------------------- ses efekti zamanlamasi
def schedule_sfx():
    sfx(0.04, 'pencil', dur=0.30, gain=0.55)
    sfx(0.28, 'pop', gain=0.8, f0=520)
    sfx(0.30, 'thump', gain=0.55)
    p0, p1 = INTRO_PASS
    for k in range(3):
        a = p0 + (p1 - p0) * k / 3
        sfx(a, 'rub', dur=(p1 - p0) / 3 * 0.95, gain=0.9)
        sfx(a + 0.02, 'whoosh', dur=0.26, gain=0.5, lo=500, hi=2600)
    sfx(p1 - 0.05, 'whoosh', dur=0.45, gain=0.45, lo=300, hi=1600)
    s2 = S['S2']
    sfx(s2['t0'] - 0.05, 'whoosh', dur=0.5, gain=0.7, lo=180, hi=1400)
    sfx(s2['t0'] + 0.15, 'riser', dur=S3t - s2['t0'] - 0.15, gain=0.65)
    sfx(S3t, 'boom', gain=0.85, big=True)
    sfx(T_SLAM2, 'boom', gain=0.65)
    sfx(T_SLAM2, 'pop', gain=0.5, f0=300)
    sfx(S['S3']['t1'] - 0.26, 'rub', dur=0.26, gain=0.6)
    sfx(S4t - 0.10, 'whoosh', dur=0.24, gain=0.7, lo=600, hi=3500)
    sfx(S4t + 0.08, 'pencil', dur=0.32, gain=0.5)
    sfx(S4t + 0.30, 'pencil', dur=0.30, gain=0.45)
    sfx(S4t + 0.52, 'pencil', dur=0.24, gain=0.45)
    sfx(S5t - 0.03, 'whoosh', dur=0.22, gain=0.8, lo=900, hi=5000)
    sfx(BLINK, 'sparkle', gain=0.75)
    sfx(BLINK + 0.05, 'pop', gain=0.45, f0=900)
    sfx(S6t, 'whoosh', dur=0.30, gain=0.7, lo=4000, hi=500)
    sfx(S6t + 0.24, 'pencil', dur=0.42, gain=0.8, fast=True)
    sfx(END0 + 0.10, 'rub', dur=0.80, gain=0.85)
    sfx(END0 + 0.10, 'steps', dur=0.80, gain=0.5)
    sfx(E_LOGO, 'boom', gain=0.9, big=True)
    sfx(E_LOGO + 0.02, 'sparkle', gain=0.6)
    sfx(E_LOGO + 0.30, 'pencil', dur=0.55, gain=0.45)
    sfx(E_LOGO + 0.62, 'pencil', dur=0.45, gain=0.4)
    sfx(E_LOGO + 0.89, 'pop', gain=0.7, f0=420)
    sfx(E_LOGO + 1.22, 'pop', gain=0.6, f0=700)
    sfx(E_LOGO + 1.30, 'squeak', gain=0.8)
    sfx(E_LOGO + 2.05, 'squeak', gain=0.6)
schedule_sfx()

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('-o', default=os.path.join(HERE, 'video.mp4'))
    ap.add_argument('--preview', action='store_true')
    ap.add_argument('--meta', action='store_true')
    ap.add_argument('--from', dest='tf', type=float, default=0.0)
    ap.add_argument('--to', dest='tt', type=float, default=None)
    a = ap.parse_args()
    print(json.dumps({s['name']: [round(s['t0'], 3), round(s['t1'], 3)] for s in SHOTS}), 'END0', round(END0, 3), 'TOTAL', round(TOTAL, 3))
    if a.meta:
        dump_meta(os.path.join(HERE, 'meta.json')); sys.exit()
    render(a.o, preview=a.preview, t_from=a.tf, t_to=a.tt)
