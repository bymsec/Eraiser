#!/usr/bin/env python3
"""Eraiser fragman sesi: oyunun kendi sesi (ayni zaman haritasiyla, varispeed) + sentez SFX.
Muzik yok. Cikti: mix.wav (loudnorm oncesi)."""
import os, json, math
import numpy as np
from scipy import signal
import soundfile as sf

HERE = os.environ.get('FRAGMAN_WORK', '/tmp/fragman')
SR = 48000
meta = json.load(open(os.path.join(HERE, 'meta.json')))
TOTAL = meta['total']
N = int(math.ceil(TOTAL * SR)) + SR // 2
rng = np.random.default_rng(42)

game, gsr = sf.read(os.path.join(HERE, 'game.wav'), dtype='float32')
assert gsr == SR
if game.ndim == 1: game = np.stack([game, game], 1)

# ---------------------------------------------------------------- yardimcilar
def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype='band', fs=SR, output='sos'); return signal.sosfilt(sos, x, axis=0)
def lp(x, f, order=2):
    sos = signal.butter(order, f, btype='low', fs=SR, output='sos'); return signal.sosfilt(sos, x, axis=0)
def hp(x, f, order=2):
    sos = signal.butter(order, f, btype='high', fs=SR, output='sos'); return signal.sosfilt(sos, x, axis=0)
def noise(n): return rng.normal(0, 1, n).astype(np.float32)
def env_ad(n, a, d_tau):
    t = np.arange(n) / SR
    return np.minimum(t / max(a, 1e-4), 1) * np.exp(-np.maximum(t - a, 0) / d_tau)
def pan(x, p):     # p -1..1 (sabit veya dizi)
    p = np.asarray(p, np.float32)
    l = np.cos((p + 1) * np.pi / 4); r = np.sin((p + 1) * np.pi / 4)
    return np.stack([x * l, x * r], 1)
def fades(x, fi=0.005, fo=0.02):
    n = len(x); a = int(fi * SR); b = int(fo * SR)
    e = np.ones(n, np.float32)
    if a: e[:a] = np.linspace(0, 1, a)
    if b: e[-b:] = np.minimum(e[-b:], np.linspace(1, 0, b))
    return x * (e[:, None] if x.ndim == 2 else e)

def sweep_bp(x, f0, f1, q=1.4, block=256):
    """merkez frekansi f0->f1 (log) kayan band geciren (blok blok)."""
    out = np.zeros_like(x); zi = None
    nb = int(math.ceil(len(x) / block))
    for b in range(nb):
        u = b / max(nb - 1, 1)
        fc = f0 * (f1 / f0) ** u
        bw = fc / q
        lo, hi = max(fc - bw / 2, 40), min(fc + bw / 2, SR / 2 - 200)
        sos = signal.butter(1, [lo, hi], btype='band', fs=SR, output='sos')
        if zi is None: zi = np.zeros((sos.shape[0], 2))
        out[b * block:(b + 1) * block], zi = signal.sosfilt(sos, x[b * block:(b + 1) * block], zi=zi)
    return out

# ---------------------------------------------------------------- SFX sentezi
def s_pencil(dur, fast=False, **_):
    n = int(dur * SR)
    nz = bp(noise(n), 1800, 7500, 2)
    e = np.zeros(n, np.float32); t = 0.0
    while t < dur:
        g = rng.uniform(0.025, 0.06) if fast else rng.uniform(0.04, 0.10)
        a, b = int(t * SR), int(min(t + g, dur) * SR)
        if b > a:
            w = np.sin(np.linspace(0, np.pi, b - a)) ** 0.6 * rng.uniform(0.5, 1.0)
            e[a:b] = np.maximum(e[a:b], w)
        t += g + rng.uniform(0.0, 0.015 if fast else 0.04)
    e *= 1 + 0.4 * rng.normal(0, 1, n).clip(-1, 1) * 0.3
    x = nz * e * 0.5
    return fades(pan(x, rng.uniform(-0.3, 0.3)))

def s_rub(dur, **_):
    n = int(dur * SR); t = np.arange(n) / SR
    nz = bp(noise(n), 350, 2600, 2)
    am = np.abs(np.sin(2 * np.pi * 7.5 * t)) ** 0.7 * 0.8 + 0.2
    sq = np.sin(2 * np.pi * (1900 + 250 * np.sin(2 * np.pi * 6 * t)) * t) * 0.05 * am
    x = (nz * 0.55 + sq) * am * np.sin(np.linspace(0, np.pi, n)) ** 0.5
    return fades(pan(x, np.linspace(-0.6, 0.6, n)), 0.01, 0.04)

def s_whoosh(dur, lo=300, hi=3000, **_):
    n = int(dur * SR)
    x = sweep_bp(noise(n), lo, hi, q=1.2)
    u = np.linspace(0, 1, n)
    e = np.sin(np.pi * np.clip(u / 0.65, 0, 1) * 0.5) ** 2 * np.where(u < 0.65, 1, np.cos((u - 0.65) / 0.35 * np.pi / 2) ** 2)
    x = x * e * 0.9
    return fades(pan(x, np.linspace(-0.7, 0.7, n)))

def s_riser(dur, **_):
    n = int(dur * SR); u = np.linspace(0, 1, n); t = np.arange(n) / SR
    nz = sweep_bp(noise(n), 400, 9000, q=0.9)
    f = 140 * (6.5 ** u)
    ph = 2 * np.pi * np.cumsum(f) / SR
    trem = 0.6 + 0.4 * np.sin(2 * np.pi * np.cumsum(4 + 22 * u ** 2) / SR)
    tone = (np.sin(ph) + 0.35 * np.sin(2 * ph + 0.3)) * trem
    e = 0.12 + 0.88 * u ** 1.5
    x = (nz * 0.6 + tone * 0.18) * e
    return fades(pan(x, 0.0), 0.01, 0.008)

def s_boom(big=False, **_):
    dur = 1.6 if big else 0.9
    n = int(dur * SR); t = np.arange(n) / SR
    f = 38 + (115 - 38) * np.exp(-t / 0.09)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (0.40 if big else 0.28))
    punch = np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.05) * 0.5
    click = lp(noise(n), 3500) * np.exp(-t / 0.012) * 0.9
    crack = bp(noise(n), 900, 6000) * np.exp(-t / 0.06) * (0.55 if big else 0.3)
    x = np.tanh((sub * 1.1 + punch + click + crack) * 1.6) * 0.85
    st = np.stack([x, x], 1)
    st[:, 0] += crack * 0.2; st[:, 1] -= crack * 0.2
    return fades(st, 0.0005, 0.05)

def s_pop(f0=500, **_):
    n = int(0.16 * SR); t = np.arange(n) / SR
    f = f0 * (1 + 0.9 * np.exp(-t / 0.018))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.045)
    x += lp(noise(n), 4000) * np.exp(-t / 0.004) * 0.3
    return fades(pan(x * 0.8, rng.uniform(-0.2, 0.2)), 0.0005, 0.02)

def s_sparkle(**_):
    n = int(1.4 * SR); out = np.zeros((n, 2), np.float32)
    notes = [2093, 2637, 3136, 4186, 5274]
    for i, fr in enumerate(notes):
        off = int(i * 0.045 * SR); m = n - off; t = np.arange(m) / SR
        tone = np.zeros(m)
        for k, (mul, amp) in enumerate([(1, 1.0), (2.76, 0.35), (5.4, 0.15)]):
            tone += amp * np.sin(2 * np.pi * fr * mul * t + k) * np.exp(-t / (0.45 / mul ** 0.5))
        out[off:] += pan(tone * 0.22 * np.minimum(t / 0.002, 1), -0.6 + 1.2 * i / (len(notes) - 1))
    sh = hp(noise(n), 7000) * np.exp(-np.arange(n) / SR / 0.25) * 0.06
    out += np.stack([sh, np.roll(sh, 300)], 1)
    return fades(out, 0.0005, 0.1)

def s_steps(dur, **_):
    n = int(dur * SR); out = np.zeros(n, np.float32)
    k = 0; t0 = 0.0
    while t0 < dur:
        a = int(t0 * SR); m = min(int(0.07 * SR), n - a)
        if m <= 0: break
        t = np.arange(m) / SR
        out[a:a + m] += (np.sin(2 * np.pi * 85 * t) * np.exp(-t / 0.025) + lp(noise(m), 2500) * np.exp(-t / 0.006) * 0.4) * 0.7
        t0 += 1 / 8.5; k += 1
    return fades(pan(out, np.linspace(-0.8, 0.8, n)))

def s_squeak(**_):
    n = int(0.12 * SR); t = np.arange(n) / SR
    f = 1150 + 700 * (t / t[-1]) + 60 * np.sin(2 * np.pi * 38 * t)
    x = (np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.3 * np.sin(4 * np.pi * np.cumsum(f) / SR)) * np.sin(np.pi * t / t[-1]) ** 0.8
    return fades(pan(x * 0.22, 0.1), 0.002, 0.01)

GEN = dict(squeak=s_squeak, thump=lambda **k: s_boom() * 0.6, pencil=s_pencil, rub=s_rub, whoosh=s_whoosh, riser=s_riser, boom=s_boom, pop=s_pop, sparkle=s_sparkle, steps=s_steps)
REVERB_SEND = dict(squeak=0.3, boom=0.35, sparkle=0.55, pop=0.25, whoosh=0.2, riser=0.3, pencil=0.08, rub=0.1, steps=0.1)

# ---------------------------------------------------------------- oyun sesi: zaman haritasi
tm = np.array([[a, (np.nan if b is None else b)] for a, b in meta['tmap']], np.float64)
def game_bus():
    bus = np.zeros((N, 2), np.float32)
    shots = meta['shots']
    for i, s in enumerate(shots):
        a, b = int(round(s['t0'] * SR)), int(round(s['t1'] * SR))
        # kesimlerde 15ms ust uste bindirme
        pre = int(0.015 * SR) if i > 0 else 0
        post = int(0.015 * SR) if i < len(shots) - 1 else 0
        idx = np.arange(a - pre, b + post)
        tout = idx / SR
        msk = (tm[:, 0] >= s['t0'] + 1e-6) & (tm[:, 0] < s['t1'] - 1e-6) & ~np.isnan(tm[:, 1])
        # sinir disi ornekler icin dogrusal uzatma
        tt, ss = tm[msk, 0], tm[msk, 1]
        slope0 = (ss[1] - ss[0]) / (tt[1] - tt[0]); slope1 = (ss[-1] - ss[-2]) / (tt[-1] - tt[-2])
        src = np.interp(tout, tt, ss)
        src = np.where(tout < tt[0], ss[0] + (tout - tt[0]) * slope0, src)
        src = np.where(tout > tt[-1], ss[-1] + (tout - tt[-1]) * slope1, src)
        sp = np.clip(src * SR, 0, len(game) - 2)
        i0 = np.floor(sp).astype(int); fr = (sp - i0)[:, None]
        seg = game[i0] * (1 - fr) + game[i0 + 1] * fr
        # komsu cekim ile surekli mi? (kaynak zamani atlamiyorsa fade gerekmez)
        e = np.ones(len(idx), np.float32)
        def cont(j):
            if j < 0 or j >= len(shots): return False
            A, B = (s, shots[j]) if j > i else (shots[j], s)
            sa = np.interp(A['t1'] - 0.001, tm[:, 0], np.nan_to_num(tm[:, 1]))
            sb = np.interp(B['t0'] + 0.001, tm[:, 0], np.nan_to_num(tm[:, 1]))
            return abs(sb - sa) < 0.01
        if i == 0:
            e[:int(0.12 * SR)] = np.linspace(0, 1, int(0.12 * SR))
        elif pre:
            if cont(i - 1): e[:pre] = 0  # surekli: onceki cekim zaten caliyor
            else: e[:2 * pre] = np.linspace(0, 1, 2 * pre)
        if post:
            if cont(i + 1): e[-post:] = 0
            else: e[-2 * post:] = np.minimum(e[-2 * post:], np.linspace(1, 0, 2 * post))
        bus[idx[0]:idx[-1] + 1] += seg * e[:, None]
    # S6'da karalama ekrani kaplarken oyun sesi kisilir
    s6 = [s for s in shots if s['name'] == 'S6'][0]
    a, b = int((s6['t0'] + 0.22) * SR), int(s6['t1'] * SR)
    bus[a:b] *= np.linspace(1, 0, b - a)[:, None] ** 1.5
    bus[b:] = 0
    return bus

MUSIC = os.path.join(HERE, 'music.wav')
DROP_SRC, HIT_SRC = 7.56, 16.651          # muzikteki drop ve final hit (olculdu)
TAPE_LEN = 0.32

def music_bus():
    mus, msr = sf.read(MUSIC, dtype='float32')
    assert msr == SR
    if mus.ndim == 1: mus = np.stack([mus, mus], 1)
    bus = np.zeros((N, 2), np.float32)
    slam = meta['slam'][0]; end0 = meta['end0']; e_logo = meta['e_logo']
    s6 = [s for s in meta['shots'] if s['name'] == 'S6'][0]
    off1 = DROP_SRC - slam
    ts0 = s6['t0'] + 0.24                  # karalama kaplamaya basladiginda teyp durur
    # 1. parca: 0 .. ts0 normal, sonra teyp durmasi
    n1 = int(ts0 * SR)
    pos = (np.arange(n1) / SR + off1) * SR
    # teyp durmasi: hiz 1 -> 0
    nt = int(TAPE_LEN * SR)
    tau = np.arange(nt) / nt
    rate = (1 - tau) ** 1.6
    pos_t = pos[-1] + np.cumsum(rate)
    allpos = np.concatenate([pos, pos_t])
    i0 = np.floor(allpos).astype(int); fr = (allpos - i0)[:, None]
    seg = mus[i0] * (1 - fr) + mus[i0 + 1] * fr
    e = np.ones(len(seg), np.float32)
    fi = int(0.15 * SR); e[:fi] = np.linspace(0, 1, fi)
    e[n1:] *= (1 - tau) ** 0.6
    seg = seg * e[:, None]
    seg[n1:] = lp(seg[n1:], 2500)
    bus[:len(seg)] += seg
    # 2. parca: son kart, final hit logoya oturur
    off2 = HIT_SRC - e_logo
    a = int(end0 * SR); b = N
    src = (np.arange(a, b) / SR + off2) * SR
    ok = src < len(mus) - 2
    src = np.where(ok, src, len(mus) - 2)
    i0 = np.floor(src).astype(int); fr = (src - i0)[:, None]
    seg = (mus[i0] * (1 - fr) + mus[i0 + 1] * fr) * ok[:, None]
    e = np.ones(len(seg), np.float32)
    k = int(0.008 * SR); e[:k] = np.linspace(0, 1, k)
    tt = np.arange(a, b) / SR
    e *= np.clip((TOTAL - tt) / 0.45, 0, 1) ** 1.5
    bus[a:b] += seg * e[:, None]
    print(f'muzik: off1={off1:.3f} (video 0 = muzik {off1:.2f}s), teyp durmasi {ts0:.2f}s, off2={off2:.3f} (son kart = muzik {end0+off2:.2f}s)')
    return bus

SFX_SCALE = dict(riser=0.35, boom=0.55, thump=0.6, whoosh=0.75, sparkle=0.8, pop=0.8, pencil=0.9, rub=0.8, steps=0.6, squeak=0.9)

def main():
    g = game_bus() * 0.85
    mb = music_bus()
    fx = np.zeros((N, 2), np.float32); rv = np.zeros((N, 2), np.float32)
    for e in meta['sfx']:
        kw = {k: v for k, v in e.items() if k not in ('t', 'kind', 'gain')}
        x = GEN[e['kind']](**kw) * e.get('gain', 1.0) * SFX_SCALE.get(e['kind'], 1.0)
        a = int(e['t'] * SR); b = min(a + len(x), N)
        if a >= N: continue
        fx[a:b] += x[:b - a]
        rv[a:b] += x[:b - a] * REVERB_SEND.get(e['kind'], 0.15)
    # ağır çekim (S2) ve goz kirpma (S5) bolumunde oyun sesi de reverb'e
    for s in meta['shots']:
        if s['name'] in ('S2', 'S5'):
            a, b = int(s['t0'] * SR), int(s['t1'] * SR)
            rv[a:b] += g[a:b] * 0.5
    # sentetik oda/hall IR
    L = int(1.6 * SR); t = np.arange(L) / SR
    ir = np.stack([lp(noise(L), 6000), lp(noise(L), 6000)], 1) * np.exp(-t / 0.38)[:, None]
    ir[:int(0.02 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
    wet = np.stack([signal.fftconvolve(rv[:, c], ir[:, c])[:N] for c in range(2)], 1) * 0.55
    mix = mb * 1.0 + g + fx * 0.6 + wet * 0.8
    mix = hp(mix, 28)
    peak = np.abs(mix).max()
    mix = mix / max(peak, 1e-6) * 0.95
    mix = np.tanh(mix * 1.25) / np.tanh(1.25)
    mix = mix[:int(TOTAL * SR)]
    sf.write(os.path.join(HERE, 'mix.wav'), mix.astype(np.float32), SR, subtype='FLOAT')
    print('mix.wav', mix.shape, 'peak', np.abs(mix).max())

if __name__ == '__main__':
    main()
