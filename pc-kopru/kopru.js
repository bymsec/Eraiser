#!/usr/bin/env node
// PC Köprüsü: bilgisayardaki MCP sunucularını (dosyalar, Claude hafızası,
// Blender, Unity) tek bir şifreli adresten buluttaki Claude'a açar.
// Bağımlılık yok, sadece Node 18+ gerekir.

'use strict';

const http = require('http');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { spawn, execFile } = require('child_process');

const KOPRU_DIZINI = __dirname;
const AYAR_DOSYASI = path.join(KOPRU_DIZINI, 'kopru.config.json');
const ORNEK_AYAR = path.join(KOPRU_DIZINI, 'kopru.config.ornek.json');
const ADRES_DOSYASI = path.join(KOPRU_DIZINI, 'kopru-adresleri.txt');

const ISTEK_ZAMAN_ASIMI_MS = 120_000;
const OTURUM_BOSTA_MS = 30 * 60_000;
const AZAMI_GOVDE = 20 * 1024 * 1024;

function log(...a) {
  console.log(new Date().toLocaleTimeString('tr-TR'), ...a);
}

// ---------- Ayarlar ----------

function ayarlariYukle() {
  const ilkKurulum = !fs.existsSync(AYAR_DOSYASI);
  if (ilkKurulum) fs.copyFileSync(ORNEK_AYAR, AYAR_DOSYASI);
  let ayar;
  try {
    ayar = JSON.parse(fs.readFileSync(AYAR_DOSYASI, 'utf8'));
  } catch (e) {
    log('kopru.config.json okunamadı (yazım hatası olabilir, yollarda \\ yerine / kullan):', e.message);
    process.exit(1);
  }
  if (!ayar.token || ayar.token.length < 32) {
    ayar.token = crypto.randomBytes(24).toString('hex');
    fs.writeFileSync(AYAR_DOSYASI, JSON.stringify(ayar, null, 2) + '\n');
    log('Yeni gizli anahtar üretildi ve kopru.config.json içine yazıldı.');
  }
  if (ilkKurulum) {
    log('kopru.config.json oluşturuldu. İçindeki proje klasörü yolunu düzenleyip tekrar başlat.');
    process.exit(0);
  }
  ayar.port = ayar.port || 8787;
  ayar.sunucular = ayar.sunucular || {};
  return ayar;
}

function komutuHazirla(sunucu) {
  let komut = sunucu.komut.replaceAll('{KOPRU}', KOPRU_DIZINI);
  if (Array.isArray(sunucu.klasorler)) {
    komut += ' ' + sunucu.klasorler.map((k) => `"${k}"`).join(' ');
  }
  return komut;
}

// ---------- stdio MCP sunucusu için oturum ----------
// Her MCP oturumu için sunucu ayrı bir süreç olarak başlatılır. HTTP'den gelen
// JSON-RPC mesajları stdin'e yazılır, cevaplar stdout'tan id ile eşleştirilir.

class StdioOturumu {
  constructor(ad, komut, env) {
    this.ad = ad;
    this.id = crypto.randomUUID();
    this.bekleyen = new Map();
    this.sonKullanim = Date.now();
    this.kapandi = false;
    this.tampon = '';

    this.surec = spawn(komut, {
      shell: true,
      cwd: KOPRU_DIZINI,
      env: { ...process.env, ...env },
      stdio: ['pipe', 'pipe', 'pipe'],
      detached: process.platform !== 'win32',
      windowsHide: true,
    });
    this.surec.stdout.setEncoding('utf8');
    this.surec.stdout.on('data', (d) => this._veri(d));
    this.surec.stderr.on('data', (d) => {
      for (const satir of String(d).split(/\r?\n/)) if (satir.trim()) log(`[${ad}]`, satir);
    });
    this.surec.on('exit', (kod) => {
      this.kapandi = true;
      for (const { hata } of this.bekleyen.values()) hata(new Error(`${ad} sunucusu kapandı (kod ${kod})`));
      this.bekleyen.clear();
    });
    this.surec.on('error', (e) => log(`[${ad}] başlatılamadı:`, e.message));
  }

  _veri(d) {
    this.tampon += d;
    let i;
    while ((i = this.tampon.indexOf('\n')) >= 0) {
      const satir = this.tampon.slice(0, i).trim();
      this.tampon = this.tampon.slice(i + 1);
      if (!satir) continue;
      let mesaj;
      try {
        mesaj = JSON.parse(satir);
      } catch {
        log(`[${this.ad}] JSON olmayan çıktı:`, satir.slice(0, 200));
        continue;
      }
      this._mesaj(mesaj);
    }
  }

  _mesaj(m) {
    if (m.id !== undefined && m.method === undefined) {
      const b = this.bekleyen.get(String(m.id));
      if (b) {
        this.bekleyen.delete(String(m.id));
        b.cevap(m);
      }
    } else if (m.id !== undefined && m.method) {
      // Sunucudan istemciye istek (sampling, roots vb.) desteklenmiyor.
      this._yaz({ jsonrpc: '2.0', id: m.id, error: { code: -32601, message: 'Köprü bu isteği desteklemiyor' } });
    }
    // Bildirimler (notification) yok sayılır.
  }

  _yaz(m) {
    this.surec.stdin.write(JSON.stringify(m) + '\n');
  }

  gonder(m) {
    this.sonKullanim = Date.now();
    if (this.kapandi) return Promise.reject(new Error(`${this.ad} sunucusu çalışmıyor`));
    if (m.id === undefined) {
      this._yaz(m);
      return Promise.resolve(null);
    }
    return new Promise((cevap, hata) => {
      const zamanlayici = setTimeout(() => {
        this.bekleyen.delete(String(m.id));
        cevap({ jsonrpc: '2.0', id: m.id, error: { code: -32000, message: 'Zaman aşımı' } });
      }, ISTEK_ZAMAN_ASIMI_MS);
      this.bekleyen.set(String(m.id), {
        cevap: (x) => { clearTimeout(zamanlayici); cevap(x); },
        hata: (e) => { clearTimeout(zamanlayici); hata(e); },
      });
      this._yaz(m);
    });
  }

  kapat() {
    if (this.kapandi) return;
    this.kapandi = true;
    const pid = this.surec.pid;
    if (!pid) return;
    if (process.platform === 'win32') {
      execFile('taskkill', ['/pid', String(pid), '/T', '/F'], () => {});
    } else {
      try { process.kill(-pid, 'SIGTERM'); } catch {}
    }
  }
}

const oturumlar = new Map(); // oturumId -> StdioOturumu

setInterval(() => {
  for (const [id, o] of oturumlar) {
    if (o.kapandi || Date.now() - o.sonKullanim > OTURUM_BOSTA_MS) {
      o.kapat();
      oturumlar.delete(id);
      log(`[${o.ad}] boşta kalan oturum kapatıldı`);
    }
  }
}, 60_000).unref();

// ---------- HTTP yardımcıları ----------

function govdeOku(req) {
  return new Promise((cevap, hata) => {
    const parcalar = [];
    let boyut = 0;
    req.on('data', (p) => {
      boyut += p.length;
      if (boyut > AZAMI_GOVDE) {
        hata(new Error('İstek çok büyük'));
        req.destroy();
      } else parcalar.push(p);
    });
    req.on('end', () => cevap(Buffer.concat(parcalar).toString('utf8')));
    req.on('error', hata);
  });
}

function jsonGonder(res, durum, veri, basliklar = {}) {
  res.writeHead(durum, { 'Content-Type': 'application/json; charset=utf-8', ...basliklar });
  res.end(JSON.stringify(veri));
}

function esitMi(a, b) {
  const x = Buffer.from(String(a));
  const y = Buffer.from(String(b));
  return x.length === y.length && crypto.timingSafeEqual(x, y);
}

// ---------- stdio sunucusu için Streamable HTTP ----------

async function stdioIstegi(ad, sunucu, req, res, ekEnv) {
  const oturumId = req.headers['mcp-session-id'];

  if (req.method === 'DELETE') {
    const o = oturumId && oturumlar.get(oturumId);
    if (o) { o.kapat(); oturumlar.delete(oturumId); }
    res.writeHead(204).end();
    return;
  }
  if (req.method === 'GET') {
    // Sunucudan istemciye ayrı SSE akışı sunmuyoruz (spesifikasyona uygun).
    res.writeHead(405, { Allow: 'POST, DELETE' }).end();
    return;
  }
  if (req.method !== 'POST') {
    res.writeHead(405).end();
    return;
  }

  let govde;
  try {
    govde = JSON.parse(await govdeOku(req));
  } catch {
    jsonGonder(res, 400, { jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Geçersiz JSON' } });
    return;
  }
  const mesajlar = Array.isArray(govde) ? govde : [govde];
  const ilkBaglanti = mesajlar.some((m) => m && m.method === 'initialize');

  let oturum;
  if (ilkBaglanti) {
    oturum = new StdioOturumu(ad, komutuHazirla(sunucu), { ...sunucu.env, ...ekEnv });
    oturumlar.set(oturum.id, oturum);
    log(`[${ad}] yeni oturum açıldı`);
  } else if (!oturumId) {
    jsonGonder(res, 400, { jsonrpc: '2.0', id: null, error: { code: -32000, message: 'Mcp-Session-Id eksik' } });
    return;
  } else {
    oturum = oturumlar.get(oturumId);
    if (!oturum || oturum.kapandi) {
      jsonGonder(res, 404, { jsonrpc: '2.0', id: null, error: { code: -32001, message: 'Oturum bulunamadı' } });
      return;
    }
  }

  try {
    const cevaplar = (await Promise.all(mesajlar.map((m) => oturum.gonder(m)))).filter(Boolean);
    const basliklar = { 'Mcp-Session-Id': oturum.id };
    if (cevaplar.length === 0) {
      res.writeHead(202, basliklar).end();
    } else {
      jsonGonder(res, 200, Array.isArray(govde) ? cevaplar : cevaplar[0], basliklar);
    }
  } catch (e) {
    jsonGonder(res, 502, { jsonrpc: '2.0', id: null, error: { code: -32000, message: e.message } });
  }
}

// ---------- Zaten HTTP ile çalışan sunucuya aktarma (ör. Unity) ----------

function httpAktar(sunucu, req, res, sorgu) {
  const hedef = new URL(sunucu.hedef);
  const basliklar = { ...req.headers, host: hedef.host };
  delete basliklar.authorization;
  const ileri = http.request(
    {
      hostname: hedef.hostname,
      port: hedef.port || 80,
      path: hedef.pathname + sorgu,
      method: req.method,
      headers: basliklar,
    },
    (hr) => {
      res.writeHead(hr.statusCode, hr.headers);
      hr.pipe(res);
    }
  );
  ileri.on('error', (e) => jsonGonder(res, 502, { hata: `Sunucuya ulaşılamadı (${sunucu.hedef}). Program açık ve MCP sunucusu çalışıyor mu? ${e.message}` }));
  req.pipe(ileri);
}

// ---------- Ana sunucu ----------

function sunucuyuBaslat(ayar) {
  const acik = Object.entries(ayar.sunucular).filter(([, s]) => s.acik);

  // Hafıza sunucusu, dosya sunucusuna verilen proje klasörlerindeki CLAUDE.md'leri de görsün.
  const projeler = (ayar.sunucular.dosya && ayar.sunucular.dosya.klasorler) || [];
  const hafizaEnv = { HAFIZA_PROJELER: projeler.join(path.delimiter) };

  const sunucu = http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url, 'http://yerel');
      const parcalar = url.pathname.split('/').filter(Boolean);

      // Adres biçimi: /<token>/<sunucu>/mcp  ya da  Authorization: Bearer <token> + /<sunucu>/mcp
      let token = null;
      const yetki = req.headers.authorization || '';
      if (yetki.startsWith('Bearer ')) token = yetki.slice(7).trim();
      else if (parcalar.length) token = parcalar.shift();

      if (!token || !esitMi(token, ayar.token)) {
        jsonGonder(res, 401, { hata: 'Yetkisiz' });
        return;
      }

      if (parcalar.length === 0) {
        jsonGonder(res, 200, {
          kopru: 'calisiyor',
          sunucular: acik.map(([ad, s]) => ({ ad, tip: s.tip, yol: `/${ad}/mcp`, aciklama: s.aciklama || '' })),
        });
        return;
      }

      const [ad, uc] = parcalar;
      const s = ayar.sunucular[ad];
      if (!s || !s.acik || uc !== 'mcp' || parcalar.length !== 2) {
        jsonGonder(res, 404, { hata: 'Böyle bir sunucu yok' });
        return;
      }

      if (s.tip === 'http') httpAktar(s, req, res, url.search);
      else await stdioIstegi(ad, s, req, res, ad === 'hafiza' ? hafizaEnv : {});
    } catch (e) {
      log('Hata:', e.message);
      if (!res.headersSent) jsonGonder(res, 500, { hata: e.message });
    }
  });

  // Sadece bu bilgisayardan erişilebilir. Dışarıya sadece tünel üzerinden çıkar.
  sunucu.listen(ayar.port, '127.0.0.1', () => {
    log(`Köprü hazır: http://127.0.0.1:${ayar.port}`);
    log('Açık sunucular:', acik.map(([ad]) => ad).join(', ') || '(hiçbiri)');
    tuneliBaslat(ayar, acik.map(([ad]) => ad));
  });
}

// ---------- Tünel (cloudflared) ----------

function adresleriYaz(taban, ayar, adlar) {
  const satirlar = [
    'Bu adresler gizli anahtarı içerir, kimseyle paylaşma (sadece Claude oturumuna yapıştır).',
    '',
    `Durum:   ${taban}/${ayar.token}/`,
    ...adlar.map((ad) => `${ad.padEnd(8)} ${taban}/${ayar.token}/${ad}/mcp`),
    '',
  ];
  fs.writeFileSync(ADRES_DOSYASI, satirlar.join('\n'));
  console.log('\n' + '='.repeat(70));
  for (const s of satirlar) console.log(s);
  console.log(`(Adresler ${path.basename(ADRES_DOSYASI)} dosyasına da yazıldı.)`);
  console.log('='.repeat(70) + '\n');
}

function tuneliBaslat(ayar, adlar) {
  const tunel = ayar.tunel || { tip: 'hizli' };
  if (tunel.tip === 'yok') {
    adresleriYaz(`http://127.0.0.1:${ayar.port}`, ayar, adlar);
    return;
  }

  const argumanlar =
    tunel.tip === 'sabit'
      ? ['tunnel', '--no-autoupdate', 'run', '--url', `http://127.0.0.1:${ayar.port}`, tunel.ad]
      : ['tunnel', '--no-autoupdate', '--url', `http://127.0.0.1:${ayar.port}`];

  const cf = spawn(tunel.komut || 'cloudflared', argumanlar, { windowsHide: true });
  let bulundu = false;

  if (tunel.tip === 'sabit') {
    if (tunel.adres) adresleriYaz(tunel.adres.replace(/\/$/, ''), ayar, adlar);
    else log('Sabit tünel için "tunel.adres" ayarını gir (ör. https://kopru.alanadin.com).');
    bulundu = true;
  }

  const oku = (d) => {
    const metin = String(d);
    if (!bulundu) {
      const m = metin.match(/https:\/\/[a-z0-9-]+\.trycloudflare\.com/);
      if (m) {
        bulundu = true;
        adresleriYaz(m[0], ayar, adlar);
      }
    }
    if (/ERR|error/i.test(metin)) log('[tunel]', metin.trim().split('\n').pop());
  };
  cf.stdout.on('data', oku);
  cf.stderr.on('data', oku);
  cf.on('error', (e) => {
    if (e.code === 'ENOENT') {
      log('cloudflared bulunamadı. Kurmak için: winget install --id Cloudflare.cloudflared');
      log('Kurduktan sonra bu pencereyi kapatıp tekrar aç.');
    } else log('Tünel hatası:', e.message);
  });
  cf.on('exit', (kod) => log(`Tünel kapandı (kod ${kod}).`));
  tunelSureci = cf;
}

let tunelSureci = null;
function kapat() {
  try { if (tunelSureci) tunelSureci.kill(); } catch {}
  for (const o of oturumlar.values()) o.kapat();
  process.exit(0);
}
process.on('SIGINT', kapat);
process.on('SIGTERM', kapat);

sunucuyuBaslat(ayarlariYukle());
