#!/usr/bin/env node
// Claude hafıza sunucusu (stdio MCP).
// Sadece şu dosyalara erişir, .claude klasörünün geri kalanına (giriş bilgileri,
// ayarlar, konuşma kayıtları) dokunmaz:
//   ~/.claude/CLAUDE.md                       (kullanıcı hafızası)
//   ~/.claude/projects/<proje>/memory/**      (otomatik notlar)
//   ayarlarda verilen proje klasörlerindeki CLAUDE.md ve CLAUDE.local.md
// Yazma sadece HAFIZA_YAZMA=1 ise açıktır.

'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');

const CLAUDE_DIZINI = path.resolve(process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude'));
const YAZMA_ACIK = process.env.HAFIZA_YAZMA === '1';
const PROJE_KLASORLERI = (process.env.HAFIZA_PROJELER || '')
  .split(path.delimiter)
  .filter(Boolean)
  .map((p) => path.resolve(p));
const PROJE_DOSYALARI = ['CLAUDE.md', 'CLAUDE.local.md'];

// ---------- Yol denetimi ----------

function icindeMi(ust, yol) {
  const g = path.relative(ust, yol);
  return g !== '' && !g.startsWith('..') && !path.isAbsolute(g);
}

function izinliMi(mutlak) {
  if (mutlak === path.join(CLAUDE_DIZINI, 'CLAUDE.md')) return true;
  const projeler = path.join(CLAUDE_DIZINI, 'projects');
  if (icindeMi(projeler, mutlak)) {
    const p = path.relative(projeler, mutlak).split(path.sep);
    if (p.length >= 3 && p[1] === 'memory' && !p.includes('..')) return true;
  }
  for (const k of PROJE_KLASORLERI) {
    for (const d of PROJE_DOSYALARI) if (mutlak === path.join(k, d)) return true;
  }
  return false;
}

// "~/..." ya da "claude:<göreli>" ya da tam yol kabul edilir.
function yoluCoz(girdi) {
  if (typeof girdi !== 'string' || !girdi.trim()) throw new Error('yol boş olamaz');
  let y = girdi.trim();
  if (y.startsWith('~/') || y.startsWith('~\\')) y = path.join(os.homedir(), y.slice(2));
  else if (!path.isAbsolute(y)) y = path.join(CLAUDE_DIZINI, y);
  const mutlak = path.resolve(y);
  if (!izinliMi(mutlak)) throw new Error(`Bu yola izin yok: ${girdi}`);
  // Sembolik bağlantıyla dışarı kaçmayı engelle.
  if (fs.existsSync(mutlak) && !izinliMi(fs.realpathSync(mutlak))) throw new Error('Bağlantı izinli alanın dışını gösteriyor');
  return mutlak;
}

function goster(mutlak) {
  return icindeMi(CLAUDE_DIZINI, mutlak) ? path.relative(CLAUDE_DIZINI, mutlak).split(path.sep).join('/') : mutlak;
}

function dosyalariTopla(dizin, sonuc) {
  let girdiler;
  try { girdiler = fs.readdirSync(dizin, { withFileTypes: true }); } catch { return; }
  for (const g of girdiler) {
    const tam = path.join(dizin, g.name);
    if (g.isDirectory()) dosyalariTopla(tam, sonuc);
    else if (g.isFile()) sonuc.push(tam);
  }
}

function hafizaListesi() {
  const liste = [];
  const ekle = (f) => {
    try {
      const st = fs.statSync(f);
      liste.push({ yol: goster(f), boyut: st.size, degisme: st.mtime.toISOString() });
    } catch {}
  };
  const kullanici = path.join(CLAUDE_DIZINI, 'CLAUDE.md');
  if (fs.existsSync(kullanici)) ekle(kullanici);

  const projeler = path.join(CLAUDE_DIZINI, 'projects');
  let dizinler = [];
  try { dizinler = fs.readdirSync(projeler, { withFileTypes: true }).filter((d) => d.isDirectory()); } catch {}
  for (const d of dizinler) {
    const dosyalar = [];
    dosyalariTopla(path.join(projeler, d.name, 'memory'), dosyalar);
    dosyalar.forEach(ekle);
  }
  for (const k of PROJE_KLASORLERI) {
    for (const ad of PROJE_DOSYALARI) {
      const f = path.join(k, ad);
      if (fs.existsSync(f)) ekle(f);
    }
  }
  return liste;
}

// ---------- Araçlar ----------

const ARACLAR = [
  {
    name: 'hafiza_listele',
    description:
      "Bilgisayardaki Claude hafıza dosyalarını listeler: kullanıcı CLAUDE.md'si, projelerin otomatik not (memory) klasörleri ve proje CLAUDE.md dosyaları.",
    inputSchema: { type: 'object', properties: {} },
  },
  {
    name: 'hafiza_oku',
    description: "Bir hafıza dosyasını okur. 'yol', hafiza_listele'nin verdiği yoldur (ör. 'CLAUDE.md' veya 'projects/<proje>/memory/MEMORY.md').",
    inputSchema: { type: 'object', properties: { yol: { type: 'string' } }, required: ['yol'] },
  },
  {
    name: 'hafiza_yaz',
    description:
      "Bir hafıza dosyasının içeriğini tamamen değiştirir veya dosyayı oluşturur. Sadece izinli hafıza konumlarında çalışır. Önce hafiza_oku ile mevcut içeriği okuyup birleştirin.",
    inputSchema: {
      type: 'object',
      properties: { yol: { type: 'string' }, icerik: { type: 'string' } },
      required: ['yol', 'icerik'],
    },
  },
];

function aracCalistir(ad, arg = {}) {
  if (ad === 'hafiza_listele') {
    const liste = hafizaListesi();
    return liste.length ? JSON.stringify(liste, null, 2) : 'Hiç hafıza dosyası bulunamadı.';
  }
  if (ad === 'hafiza_oku') {
    const f = yoluCoz(arg.yol);
    if (!fs.existsSync(f)) throw new Error(`Dosya yok: ${arg.yol}`);
    return fs.readFileSync(f, 'utf8');
  }
  if (ad === 'hafiza_yaz') {
    if (!YAZMA_ACIK) throw new Error('Hafızaya yazma kapalı (kopru.config.json içinde hafiza.yazma: true yapılmalı).');
    if (typeof arg.icerik !== 'string') throw new Error('icerik metin olmalı');
    const f = yoluCoz(arg.yol);
    fs.mkdirSync(path.dirname(f), { recursive: true });
    if (!izinliMi(fs.realpathSync(path.dirname(f)) + path.sep + path.basename(f))) throw new Error('Bu yola izin yok');
    fs.writeFileSync(f, arg.icerik, 'utf8');
    return `Yazıldı: ${goster(f)} (${Buffer.byteLength(arg.icerik)} bayt)`;
  }
  throw new Error(`Bilinmeyen araç: ${ad}`);
}

// ---------- MCP (JSON-RPC, satır satır stdio) ----------

function gonder(m) {
  process.stdout.write(JSON.stringify(m) + '\n');
}

function isle(m) {
  if (!m || m.id === undefined) return; // bildirim
  const { id, method, params } = m;
  try {
    if (method === 'initialize') {
      gonder({
        jsonrpc: '2.0',
        id,
        result: {
          protocolVersion: (params && params.protocolVersion) || '2025-06-18',
          capabilities: { tools: {} },
          serverInfo: { name: 'claude-hafiza', version: '1.0.0' },
          instructions:
            "Kullanıcının kendi bilgisayarındaki Claude hafızası. Oturum başında hafiza_listele ve hafiza_oku ile ilgili notları oku.",
        },
      });
    } else if (method === 'ping') {
      gonder({ jsonrpc: '2.0', id, result: {} });
    } else if (method === 'tools/list') {
      const araclar = YAZMA_ACIK ? ARACLAR : ARACLAR.filter((a) => a.name !== 'hafiza_yaz');
      gonder({ jsonrpc: '2.0', id, result: { tools: araclar } });
    } else if (method === 'tools/call') {
      try {
        const metin = aracCalistir(params.name, params.arguments);
        gonder({ jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: metin }] } });
      } catch (e) {
        gonder({ jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: e.message }], isError: true } });
      }
    } else {
      gonder({ jsonrpc: '2.0', id, error: { code: -32601, message: `Desteklenmeyen metot: ${method}` } });
    }
  } catch (e) {
    gonder({ jsonrpc: '2.0', id, error: { code: -32603, message: e.message } });
  }
}

let tampon = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (d) => {
  tampon += d;
  let i;
  while ((i = tampon.indexOf('\n')) >= 0) {
    const satir = tampon.slice(0, i).trim();
    tampon = tampon.slice(i + 1);
    if (!satir) continue;
    try { isle(JSON.parse(satir)); } catch {
      gonder({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Geçersiz JSON' } });
    }
  }
});
process.stdin.on('end', () => process.exit(0));
