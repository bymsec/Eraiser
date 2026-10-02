#!/usr/bin/env python3
"""tema.src.css + karalama SVG -> tema.css ; istege bagli: --preview ile itch sayfasi benzeri onizleme HTML'i."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from karalama import data_uri

css = open(os.path.join(HERE, 'tema.src.css'), encoding='utf-8').read().replace('__KARALAMA__', data_uri())
open(os.path.join(HERE, 'tema.css'), 'w', encoding='utf-8').write(css)
print('tema.css', len(css), 'bayt')

if '--preview' in sys.argv:
    # gercek bir itch oyun sayfasini sablon olarak kullan (ITCH_TEMPLATE), aciklamayi ve stili bizimkiyle degistir
    tpl = open(os.environ.get('ITCH_TEMPLATE', '/tmp/itch/bs.html'), encoding='utf-8', errors='ignore').read()
    desc = open(os.path.join(HERE, 'aciklama.html'), encoding='utf-8').read()
    tpl = re.sub(r'<script.*?</script>', '', tpl, flags=re.S)
    a = tpl.index('<div class="formatted_description user_formatted">') + len('<div class="formatted_description user_formatted">')
    b = tpl.index('<div class="more_information_toggle">', a)
    tpl = tpl[:a] + desc + '</div>' + tpl[b:]
    # basliktaki banner -> duz baslik, video/yorum/devlog cikar
    h0 = re.search(r'<div[^>]*id="header"', tpl).start(); h1 = re.search(r'<div[^>]*id="view_game_', tpl[h0:]).start() + h0
    tpl = tpl[:h0] + '<div id="header" class="header align_center"><h1 class="game_title">Eraiser</h1></div>' + tpl[h1:]
    tpl = re.sub(r'<div class="video_embed">.*?</div>', '', tpl, flags=re.S)
    tpl = re.sub(r'<section id="devlog".*?</section>', '', tpl, flags=re.S)
    i = tpl.find('<div id="game_comments_'); j = tpl.find('<div class="right_col column">')
    if 0 < i < j: tpl = tpl[:i] + '</div>' + tpl[j:]
    shots = ''.join(f'<a href="#"><img class="screenshot" src="https://bymsec.github.io/Eraiser/gorseller/ekran-{k}.jpg"></a>' for k in (8, 6, 12))
    tpl = re.sub(r'<div class="screenshot_list">.*?</div>', f'<div class="screenshot_list">{shots}</div>', tpl, count=1, flags=re.S)
    tpl = tpl.replace('Buckshot Roulette', 'Eraiser')
    tpl = tpl.replace('</head>', f'<style id="custom_css">{css}</style></head>')
    # henuz yayinda olmayan yeni gorseller onizlemede yerelden okunur
    for f in ('logo.webp',):
        tpl = tpl.replace(f'https://bymsec.github.io/Eraiser/gorseller/{f}', 'file://' + os.path.join(os.path.dirname(HERE), 'gorseller', f))
    open(os.path.join(os.environ.get('PREVIEW_OUT', '/tmp/itch'), 'onizleme.html'), 'w', encoding='utf-8').write(tpl)
    print('onizleme.html yazildi')
