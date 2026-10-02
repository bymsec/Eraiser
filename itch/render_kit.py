#!/usr/bin/env python3
"""Ozel CSS olmadan kullanmak icin: tema.css ile tasarlanan bloklari gorsel olarak render eden sayfa uretir.
Cikti: /tmp/itch/kit/render.html (Playwright ile her .shot ogesi PNG olarak cekilir)."""
import os, re
HERE = os.path.dirname(os.path.abspath(__file__))
css = open(os.path.join(HERE, 'tema.css'), encoding='utf-8').read()
desc = open(os.path.join(HERE, 'aciklama.html'), encoding='utf-8').read()

def block(cls, html=None):
    if html is None:
        m = re.search(r'(<(div|p)\s+class="%s"[^>]*>.*?</\2>)\s*\n(?=<|$)' % re.escape(cls), desc, re.S)
        html = m.group(1)
    return html

def outer(tag_start):
    """aciklama.html icinde verilen acilis etiketiyle baslayan blogun tamamini (ic ice div'lerle) dondur."""
    i = desc.index(tag_start); depth = 0; j = i
    for m in re.finditer(r'<(/?)div\b[^>]*>', desc[i:]):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return desc[i:i + m.end()]
    raise ValueError(tag_start)

H = re.findall(r'<h2 class="custom-h[^"]*">(.*?)</h2>', desc)
shots = {}
shots['pills'] = block('custom-pills')
for k, h in enumerate(H):
    shots[f'baslik-{k + 1}'] = f'<h2 class="custom-h">{h}</h2>'
shots['notlar'] = outer('<div class="custom-notes">')
shots['dongu'] = outer('<div class="custom-loop">')
shots['gun'] = outer('<div class="custom-day">')
shots['adalar'] = outer('<div class="custom-isles">')
shots['karakterler'] = outer('<div class="custom-tags">')
shots['fotolar'] = outer('<div class="custom-shots">')
shots['kapanis'] = outer('<div class="custom-end">')

body = ''.join(f'<div class="shot" id="s-{k}">{v}</div>\n' for k, v in shots.items())
page = f'''<!doctype html><html><head><meta charset="utf-8"><style>{css}</style>
<style>
html,body{{margin:0;background:#f6f1e6}}
#wrapper{{background:#f6f1e6 !important}}
.shot{{width:600px;padding:30px 26px;background:#f6f1e6;box-sizing:border-box}}
.shot .custom-h{{animation:none !important;background-size:100% 100% !important;margin:0 !important}}
.shot .custom-pills{{margin:0 !important}}
.shot .custom-end{{margin:0 !important}}
</style></head><body><div id="wrapper"><div class="formatted_description">{body}</div></div></body></html>'''
os.makedirs('/tmp/itch/kit', exist_ok=True)
open('/tmp/itch/kit/render.html', 'w', encoding='utf-8').write(page)
print(list(shots))
