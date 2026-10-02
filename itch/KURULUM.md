# Eraiser itch.io sayfası: kurulum

Dosyalar:
- `aciklama.html`: sayfa içeriği (Description alanına yapıştırılır).
- `tema.css`: tasarım (Custom CSS alanına yapıştırılır). Kaynağı `tema.src.css`; değiştirince `python3 itch/build.py` ile yeniden üret.
- `onizleme/`: masaüstü ve mobil ekran görüntüleri; `onizleme-hero.mp4`: açılış animasyonu.

## 1. Açıklama

1. itch.io → oyun → **Edit game** → **Description** alanında `<>` (HTML) düğmesine bas.
2. `aciklama.html` dosyasının tamamını yapıştır. Bundan sonra metni hep HTML modunda düzenle; görsel editör sınıfları silebilir.
3. Özel CSS gelmeden de sayfa okunur durumda: görseller, başlıklar ve metinler düz halde görünür.

## 2. Özel CSS izni

itch.io özel CSS'i ancak destek ekibinin onayıyla açıyor (boş hesaplara vermiyorlar; önce sayfayı açıklama ve görsellerle doldur).
https://itch.io/support adresinden şu mesajı gönderebilirsin:

```
Hi! I'd like to request custom CSS access for my game page "Eraiser"
(https://<kullanici-adin>.itch.io/eraiser).

I want to style only my own page content: a notebook-paper look, sticky-note cards,
polaroid-style screenshots and a short animated header where an eraser character
wipes a pencil scribble away to reveal the game.

I understand that I must keep the page accessible and readable, keep it working on
mobile, not alter or hide any of itch.io's built-in UI (buy buttons, footer, etc.),
and scope all rules to my page content inside #wrapper. All custom classes in my
HTML use the "custom-" prefix. I also respect prefers-reduced-motion.

Thanks!
```

İzin gelince: oyun sayfasında **Edit theme** → kenar çubuğunun en altındaki **CSS** kutusuna `tema.css` dosyasının tamamını yapıştır → Save.

## 3. Tema editörü (CSS gelmeden önce de yap)

**Edit theme** içinde:
- Arka plan rengi: `#1d2130`
- Sayfa (ikinci) arka planı: `#f6f1e6`
- Yazı rengi: `#2d2b29`
- Bağlantı rengi: `#d9707d`
- Buton rengi: `#f28f96`
- Başlık fontu: Patrick Hand (listede yoksa en yakın el yazısı font)
- Banner: istersen `gorseller/logo.png` (şeffaf logo) yükle.

## 4. Görseller

Açıklamadaki ve CSS'teki görseller sitenden (`https://bymsec.github.io/Eraiser/gorseller/...`) yükleniyor.
**`logo.webp` yeni eklendi.** Bu dal main'e birleşip GitHub Pages güncellenene kadar internette yok.
O zamana kadar ya dalı birleştir ya da logoyu itch editöründen yükleyip `aciklama.html` içindeki
`logo.webp` adresini itch'in verdiği adresle değiştir.

## Notlar

- Kaydırdıkça kartların süzülerek gelmesi Chrome/Edge'de çalışıyor. Diğer tarayıcılarda kartlar normal (animasyonsuz) görünür, bozulma olmaz.
- "Hareketi azalt" ayarı açık olan ziyaretçilere animasyonlar gösterilmiyor.
- itch ileride kendi sayfa yapısını değiştirirse CSS'in bazı kısımlarının güncellenmesi gerekebilir.
