# PC Köprüsü

Buluttaki Claude oturumunun senin bilgisayarındaki şunlara erişmesini sağlar:

- **dosya**: proje klasörün (okuma + yazma, sadece verdiğin klasörler)
- **hafiza**: VS Code'daki Claude'un hafızası (`CLAUDE.md` ve `memory` notları)
- **blender**: Blender MCP
- **unity**: Unity MCP (istersen açılır)

Böylece iş bulutta yapılır, bulut kredisi harcanır, normal limitine dokunmaz.

> ⚠️ Köprü açıkken adres + şifre kimdeyse proje dosyalarına erişebilir ve Blender'da kod
> çalıştırabilir. Adresi sadece Claude oturumuna yapıştır, işin bitince pencereyi kapat.
> `.claude` klasöründeki giriş bilgilerine (`.credentials.json`) köprü **erişemez**.

---

## 1. Bir kere yapılacak kurulum

PowerShell aç ve şunları çalıştır:

```powershell
winget install OpenJS.NodeJS.LTS
winget install --id Cloudflare.cloudflared
winget install --id astral-sh.uv        # Blender MCP için
```

Kurulumdan sonra PowerShell'i kapatıp yeniden aç.

Bu klasörü bilgisayarına al (repo zaten bilgisayarındaysa sadece `git pull` yap):

```powershell
git clone https://github.com/bymsec/Eraiser.git
```

## 2. Ayarlar

`pc-kopru` klasöründe `baslat.bat`'a bir kere çift tıkla. `kopru.config.json` oluşur, pencereyi kapat.

`kopru.config.json`'u Not Defteri ile aç ve **proje klasörünü** yaz. Yolda `\` yerine `/` kullan:

```json
"klasorler": [
  "C:/Users/Ahmet/Projeler/OyunProjem"
]
```

Birden fazla klasör ekleyebilirsin. Kullanmadığın bir şeyi kapatmak için `"acik": false` yap.

Bu dosyada senin gizli şifren (`token`) var, bu yüzden git'e gönderilmez.

## 3. Her kullanımda

1. Unity'yi aç (MCP for Unity'de **Session Active** yeşil olsun). Blender kullanacaksan
   Blender'ı aç ve Blender MCP eklentisinde **Connect**'e bas.
2. `baslat.bat`'a çift tıkla.
3. Pencerede şuna benzer adresler çıkar (`kopru-adresleri.txt`'ye de yazılır):

   ```
   Durum:   https://ornek-kelime.trycloudflare.com/<şifre>/
   dosya    https://ornek-kelime.trycloudflare.com/<şifre>/dosya/mcp
   ...
   ```
4. **Durum** satırındaki adresi buluttaki Claude oturumuna yapıştır.
5. İşin bitince pencereyi kapat. Köprü ve tünel birlikte kapanır.

Hızlı tünel adresi her açılışta değişir, bu normal.

## 4. Bulut oturumunda ağ izni (bir kere)

Bulut oturumu varsayılan olarak her siteye bağlanamaz. Oturumun başlığındaki ortam
menüsünden **Edit → Network access** kısmına gir ve izinli domainlere şunu ekle:

```
*.trycloudflare.com
```

## Unity MCP

Varsayılan ayar **MCP for Unity** (v10+) için hazır, ekstra bir şey kurmana gerek yok:

1. Unity'de **MCP for Unity** sekmesini aç.
2. **Transport: HTTPLocal**, **HTTP URL: `http://127.0.0.1:8080`** olmalı.
3. Sunucu çalışıyor olmalı: yeşil **Session Active** yazısı görünmeli (**Stop Server** butonu kırmızı görünüyorsa sunucu açık demektir).

HTTP URL farklıysa `kopru.config.json`'da `unity.hedef`'i ona göre değiştir (sonuna `/mcp` ekle).
Unity'yi kullanmayacaksan `unity.acik`'i `false` yap.

## Sorun çözme

| Sorun | Çözüm |
|---|---|
| `cloudflared bulunamadı` | 1. adımdaki `winget` komutunu çalıştır, pencereyi yeniden aç |
| Blender araçları hata veriyor | Blender açık mı, eklentide **Connect**'e bastın mı? |
| Claude "403" diyor | 4. adımdaki ağ iznini ekle |
| Adres hiç çıkmıyor | Tünelin açılması 10-20 saniye sürebilir, bekle |
| Şifre ele geçti sanıyorsan | `kopru.config.json`'da `token`'ı sil (`""` yap) ve yeniden başlat, yenisi üretilir |
