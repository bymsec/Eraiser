#!/usr/bin/env python3
"""Slider videosu sesi: kayit sesi (menu muzigi + ciglik, goruntuyle senkron) + temiz ciglik + hafif SFX."""
import os, sys, json, math
import numpy as np, soundfile as sf
from scipy import signal

ED = os.path.dirname(os.path.abspath(__file__))   # edit.py / audio.py yardimcilari
sys.path.insert(0, ED)
import audio as AU     # SFX sentezleyicileri
HERE = os.environ.get('SLIDER_WORK', '/tmp/fragman2')   # src.mp4, src.wav, scream.wav, meta.json, mix.wav
SR = 48000
m = json.load(open(os.path.join(HERE, 'meta.json')))
TOTAL = m['total']; N = int(TOTAL * SR)
src, _ = sf.read(os.path.join(HERE, 'src.wav'), dtype='float32')
scr, ssr = sf.read(os.path.join(HERE, 'scream.wav'), dtype='float32')
assert ssr == SR
if scr.ndim == 1: scr = np.stack([scr, scr], 1)
SH = {s['name']: s for s in m['shots']}
XF = int(0.04 * SR)

def take(s0, n):
    a = int(s0 * SR); seg = src[a:a + n]
    if len(seg) < n: seg = np.concatenate([seg, np.zeros((n - len(seg), 2), np.float32)])
    return seg.copy()

def place_seg(bus, seg, t0, fin=True, fout=True):
    a = int(round(t0 * SR)) - (XF // 2 if fin else 0)
    a = max(a, 0)
    seg = seg.copy(); n = len(seg)
    if fin: seg[:XF] *= np.sqrt(np.linspace(0, 1, XF))[:, None]
    if fout: seg[-XF:] *= np.sqrt(np.linspace(1, 0, XF))[:, None]
    b = min(a + n, len(bus)); bus[a:b] += seg[:b - a]

def tape_stop(x, dur):
    n = len(x); nt = int(dur * SR); keep = n - nt
    tau = np.arange(nt) / nt; rate = (1 - tau) ** 1.6
    pos = keep + np.cumsum(rate)
    i0 = np.clip(np.floor(pos).astype(int), 0, n - 2); fr = (pos - i0)[:, None]
    tail = (x[i0] * (1 - fr) + x[i0 + 1] * fr) * ((1 - tau) ** 0.5)[:, None]
    tail = AU.lp(tail, 3000)
    return np.concatenate([x[:keep], tail])

def main():
    bus = np.zeros((N + SR, 2), np.float32)
    # A: kanca (senkron) + temiz ciglik ustune
    A = SH['A']; nA = int((A['t1'] - A['t0']) * SR) + XF
    a = take(A['s0'], nA)
    sc = scr[:nA] if len(scr) >= nA else np.concatenate([scr, np.zeros((nA - len(scr), 2), np.float32)])
    a = a + sc * 0.75
    a = tape_stop(a, 0.20)
    place_seg(bus, a, 0.0, fin=False)
    # B: menu muzigi yatagi (video time-lapse, ses normal hizda)
    B = SH['B']; place_seg(bus, take(1.20, int(B['dur'] * SR) + XF if 'dur' in B else int((B['t1'] - B['t0']) * SR) + XF), B['t0'])
    for k in ('C', 'D', 'E'):
        s = SH[k]; n = int((s['t1'] - s['t0']) * SR) + XF
        place_seg(bus, take(s['s0'], n), s['t0'])
    # F: son kart - menu muzigi devam, sonda fade
    n = int((TOTAL - m['end0']) * SR) + XF
    f = take(2.80, n)
    f *= np.clip((TOTAL - (m['end0'] + np.arange(n) / SR)) / 0.6, 0, 1)[:, None] ** 1.5
    place_seg(bus, f * 0.9, m['end0'], fout=False)
    # uzaktan ciglik
    dist = AU.lp(scr, 1400) * 0.22
    d0 = m['e_logo'] + 0.30; i = int(d0 * SR); j = min(i + len(dist), len(bus))
    dist = dist[:j - i] * np.clip((TOTAL - (d0 + np.arange(j - i) / SR)) / 0.5, 0, 1)[:, None]
    bus[i:j] += dist
    rv = np.zeros_like(bus); rv[i:j] += dist * 1.2
    # SFX (hafif)
    fx = np.zeros_like(bus)
    E0 = SH['E']['t0'] - SH['E']['s0']
    ev = [(0.0, 'boom', dict(), 0.45), (SH['B']['t0'] - 0.05, 'whoosh', dict(dur=0.3, lo=2500, hi=300), 0.5),
          (0.10, 'pop', dict(f0=380), 0.5),
          (E0 + 12.10, 'whoosh', dict(dur=0.18, lo=700, hi=4000), 0.5),
          (E0 + 13.90, 'whoosh', dict(dur=0.16, lo=900, hi=5000), 0.45),
          (E0 + 14.52, 'whoosh', dict(dur=0.2, lo=4000, hi=500), 0.45),
          (SH['D']['t0'] + 0.02, 'pop', dict(f0=600), 0.35),
          (m['end0'] - 0.42, 'pencil', dict(dur=0.42, fast=True), 0.7),
          (m['end0'] + 0.10, 'rub', dict(dur=0.8), 0.7), (m['end0'] + 0.10, 'steps', dict(dur=0.8), 0.45),
          (m['e_logo'], 'boom', dict(big=True), 0.5), (m['e_logo'] + 0.02, 'sparkle', dict(), 0.5),
          (m['e_logo'] + 0.25, 'pencil', dict(dur=0.7), 0.35), (m['e_logo'] + 0.78, 'pop', dict(f0=420), 0.55),
          (m['e_logo'] + 1.02, 'pop', dict(f0=700), 0.5)]
    for t, kind, kw, g in ev:
        x = AU.GEN[kind](**kw) * g
        i = int(t * SR); j = min(i + len(x), len(fx)); fx[i:j] += x[:j - i]
        rv[i:j] += x[:j - i] * AU.REVERB_SEND.get(kind, 0.15)
    L = int(1.4 * SR); tt = np.arange(L) / SR
    ir = np.stack([AU.lp(AU.noise(L), 6000), AU.lp(AU.noise(L), 6000)], 1) * np.exp(-tt / 0.35)[:, None]
    ir[:int(0.02 * SR)] = 0; ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
    wet = np.stack([signal.fftconvolve(rv[:, c], ir[:, c])[:len(bus)] for c in range(2)], 1) * 0.45
    mix = bus * 1.0 + fx * 0.55 + wet
    mix = AU.hp(mix, 25)
    mix = mix / max(np.abs(mix).max(), 1e-6) * 0.95
    mix = np.tanh(mix * 1.2) / np.tanh(1.2)
    sf.write(os.path.join(HERE, 'mix.wav'), mix[:N].astype(np.float32), SR, subtype='FLOAT')
    print('ok', mix[:N].shape)

if __name__ == '__main__':
    main()
