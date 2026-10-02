#!/usr/bin/env python3
"""Hero icin organik kalem karalamasi SVG'si uretir (kagit zemin + ilmekli grafit cizgiler) -> data URI."""
import math, random, urllib.parse

def strokes(seed=7, n=11, w=1000, h=562):
    rnd = random.Random(seed)
    out = []
    for k in range(n):
        dirx = 1 if k % 2 == 0 else -1
        x = -60.0 if dirx > 0 else w + 60.0
        y = (k + rnd.uniform(0.15, 0.85)) / n * h
        th = rnd.uniform(0, 6.28); sp = rnd.uniform(13, 19)
        om0 = rnd.uniform(0.17, 0.30) * rnd.choice([-1, 1])
        dx, dy = dirx * rnd.uniform(3.2, 5.0), rnd.uniform(-1.2, 1.2)
        p1, p2 = rnd.uniform(0, 6.28), rnd.uniform(0, 6.28)
        pts = []
        for i in range(3000):
            om = om0 * (1 + 0.55 * math.sin(i * 0.011 + p1)) + 0.07 * math.sin(i * 0.047 + p2)
            th += om
            x += sp * 0.62 * math.cos(th) + dx
            y += sp * 0.62 * math.sin(th) + dy
            if y < -30 or y > h + 30: dy = -dy
            pts.append((round(x), round(y)))
            if (dirx > 0 and x > w + 70) or (dirx < 0 and x < -70): break
        out.append((pts, rnd.uniform(4.5, 8.5), rnd.uniform(0.45, 0.8)))
    return out

def svg(w=1000, h=562):
    lines = ''.join(f'<path d="M0 {y}H{w}" stroke="#2d2b29" stroke-opacity=".07" stroke-width="1.5"/>' for y in range(40, h, 36))
    paths = ''
    for pts, sw, op in strokes(w=w, h=h):
        d = 'M' + ' '.join(f'{x} {y}' for x, y in pts)
        paths += f'<path d="{d}" fill="none" stroke="#2d2b29" stroke-opacity="{op:.2f}" stroke-width="{sw:.1f}" stroke-linecap="round" stroke-linejoin="round"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid slice">'
            f'<rect width="{w}" height="{h}" fill="#f6f1e6"/>{lines}'
            f'<path d="M70 0V{h}" stroke="#d9707d" stroke-opacity=".35" stroke-width="2"/>{paths}</svg>')

def data_uri():
    return 'data:image/svg+xml,' + urllib.parse.quote(svg(), safe=' =:/-.,')

if __name__ == '__main__':
    u = data_uri(); print(len(u))
