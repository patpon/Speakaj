// Speakaj demo relay — a Cloudflare Worker that holds the Groq API key so
// demo users only need a demo code. Each code can have an optional trial
// length (days, counted from first use) and an optional daily limit; both can
// be left empty and filled in later from the /admin page.
//
// Bindings (Worker → Settings):
//   CODES          KV namespace
//   GROQ_API_KEY   secret
//   ADMIN_TOKEN    secret (password for /admin)

const GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions";
const DEFAULT_MODEL = "whisper-large-v3";
const TZ_OFFSET_MS = 7 * 3600 * 1000; // count "today" in Thailand time
const DAY_MS = 86400 * 1000;

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
const fail = (status, message) => json({ error: { message } }, status);

const today = (now) => new Date(now + TZ_OFFSET_MS).toISOString().slice(0, 10);

function newCode() {
  const abc = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"; // no 0/O/1/I
  const bytes = crypto.getRandomValues(new Uint8Array(8));
  const s = [...bytes].map((b) => abc[b % abc.length]).join("");
  return `DEMO-${s.slice(0, 4)}-${s.slice(4)}`;
}

function toIntOrNull(v) {
  if (v === null || v === undefined || v === "") return null;
  const n = Number.parseInt(v, 10);
  return Number.isFinite(n) && n > 0 ? n : null;
}

// Status of one code at time `now`: { ok, status, message, info }
async function checkCode(env, code, now) {
  const rec = code && (await env.CODES.get("code:" + code, "json"));
  if (!rec) return { ok: false, status: 401, message: "รหัสทดลองไม่ถูกต้อง" };
  if (rec.revoked) return { ok: false, status: 403, message: "รหัสทดลองนี้ถูกยกเลิกแล้ว" };
  const expiresAt = rec.days && rec.activated_at ? rec.activated_at + rec.days * DAY_MS : null;
  if (expiresAt && now > expiresAt)
    return { ok: false, status: 403, message: "หมดระยะทดลองใช้แล้ว ติดต่อผู้ให้รหัสเพื่อต่ออายุ" };
  const used = Number((await env.CODES.get(`use:${code}:${today(now)}`)) || 0);
  if (rec.daily_limit && used >= rec.daily_limit)
    return { ok: false, status: 429, message: `ใช้ครบ ${rec.daily_limit} ครั้งของวันนี้แล้ว ใช้ต่อได้พรุ่งนี้` };
  return { ok: true, rec, used, expiresAt };
}

async function transcribe(req, env, now) {
  const code = (req.headers.get("x-speakaj-code") || "").trim().toUpperCase();
  const c = await checkCode(env, code, now);
  if (!c.ok) return fail(c.status, c.message);

  const form = await req.formData();
  if (!form.get("file")) return fail(400, "ไม่มีไฟล์เสียง");
  if (!form.get("model")) form.set("model", DEFAULT_MODEL);

  const upstream = await fetch(GROQ_URL, {
    method: "POST",
    headers: { Authorization: `Bearer ${env.GROQ_API_KEY}` },
    body: form,
  });

  if (upstream.ok) {
    if (!c.rec.activated_at) {
      c.rec.activated_at = now; // the trial clock starts at first use
      await env.CODES.put("code:" + code, JSON.stringify(c.rec));
    }
    await env.CODES.put(`use:${code}:${today(now)}`, String(c.used + 1), { expirationTtl: 3 * 86400 });
  }
  return new Response(upstream.body, {
    status: upstream.status,
    headers: { "content-type": upstream.headers.get("content-type") || "application/json" },
  });
}

async function describe(env, code, rec, now) {
  const used = Number((await env.CODES.get(`use:${code}:${today(now)}`)) || 0);
  const expiresAt = rec.days && rec.activated_at ? rec.activated_at + rec.days * DAY_MS : null;
  return { code, ...rec, used_today: used, expires_at: expiresAt };
}

async function admin(req, env, url, now) {
  if (!env.ADMIN_TOKEN || req.headers.get("authorization") !== `Bearer ${env.ADMIN_TOKEN}`)
    return fail(401, "รหัสผ่านผู้ดูแลไม่ถูกต้อง");

  const parts = url.pathname.split("/").filter(Boolean); // ["api","codes",code?,action?]
  if (parts[1] !== "codes") return fail(404, "not found");
  const code = parts[2] && decodeURIComponent(parts[2]).toUpperCase();

  if (!code && req.method === "GET") {
    const out = [];
    let cursor;
    do {
      const page = await env.CODES.list({ prefix: "code:", cursor });
      for (const k of page.keys) {
        const rec = await env.CODES.get(k.name, "json");
        if (rec) out.push(await describe(env, k.name.slice(5), rec, now));
      }
      cursor = page.list_complete ? null : page.cursor;
    } while (cursor);
    out.sort((a, b) => b.created_at - a.created_at);
    return json(out);
  }

  if (!code && req.method === "POST") {
    const body = await req.json().catch(() => ({}));
    const id = newCode();
    const rec = {
      name: String(body.name || "").slice(0, 80),
      days: toIntOrNull(body.days),
      daily_limit: toIntOrNull(body.daily_limit),
      created_at: now,
      activated_at: null,
      revoked: false,
    };
    await env.CODES.put("code:" + id, JSON.stringify(rec));
    return json(await describe(env, id, rec, now), 201);
  }

  const rec = code && (await env.CODES.get("code:" + code, "json"));
  if (!rec) return fail(404, "ไม่พบรหัสนี้");

  if (req.method === "PUT") {
    const body = await req.json().catch(() => ({}));
    if ("name" in body) rec.name = String(body.name || "").slice(0, 80);
    if ("days" in body) rec.days = toIntOrNull(body.days);
    if ("daily_limit" in body) rec.daily_limit = toIntOrNull(body.daily_limit);
    if ("revoked" in body) rec.revoked = Boolean(body.revoked);
    if (body.reset_trial) rec.activated_at = null;
    await env.CODES.put("code:" + code, JSON.stringify(rec));
    return json(await describe(env, code, rec, now));
  }
  if (req.method === "DELETE") {
    await env.CODES.delete("code:" + code);
    return json({ deleted: code });
  }
  return fail(405, "method not allowed");
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const now = Date.now();
    try {
      if (url.pathname === "/v1/transcribe" && req.method === "POST") return await transcribe(req, env, now);
      if (url.pathname === "/v1/status") {
        const code = (req.headers.get("x-speakaj-code") || "").trim().toUpperCase();
        const c = await checkCode(env, code, now);
        if (!c.ok) return fail(c.status, c.message);
        return json({ name: c.rec.name, expires_at: c.expiresAt, used_today: c.used, daily_limit: c.rec.daily_limit });
      }
      if (url.pathname.startsWith("/api/")) return await admin(req, env, url, now);
      if (url.pathname === "/admin")
        return new Response(ADMIN_HTML, { headers: { "content-type": "text/html; charset=utf-8" } });
      return new Response("Speakaj relay is running", { status: 200 });
    } catch (err) {
      return fail(500, "relay error: " + (err && err.message));
    }
  },
};

const ADMIN_HTML = `<!doctype html><html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Speakaj · จัดการรหัสทดลอง</title>
<style>
:root{--bg:#F7F9FE;--card:#fff;--ink:#0B1733;--muted:#55627D;--line:#DCE3F2;--blue:#2350E6;--red:#D03A2A;--ok:#15915A}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 "Leelawadee UI",Tahoma,sans-serif;padding:24px 16px}
.wrap{max-width:1000px;margin:auto;display:grid;gap:18px}h1{margin:0;font-size:24px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px}
label{display:grid;gap:4px;font-size:13px;color:var(--muted)}input{font:inherit;padding:8px 10px;border:1px solid var(--line);border-radius:8px;min-width:0}
.row{display:flex;flex-wrap:wrap;gap:12px;align-items:end}.row label{flex:1 1 140px}
button{font:inherit;font-weight:600;border:0;border-radius:8px;padding:9px 16px;background:var(--blue);color:#fff;cursor:pointer}
button.ghost{background:transparent;color:var(--blue);border:1px solid var(--line)}button.danger{background:transparent;color:var(--red);border:1px solid var(--line)}
.tbl{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:8px;border-bottom:1px solid var(--line);white-space:nowrap}
th{color:var(--muted);font-weight:600}code{font:600 14px Consolas,monospace}
.pill{display:inline-block;padding:1px 9px;border-radius:99px;font-size:12px;border:1px solid currentColor}.on{color:var(--ok)}.off{color:var(--red)}.wait{color:var(--muted)}
#msg{min-height:1.4em;color:var(--red)}td input{width:70px;padding:4px 6px}
</style></head><body><div class="wrap">
<h1>Speakaj · จัดการรหัสทดลอง</h1>
<div class="card row"><label>รหัสผ่านผู้ดูแล (ADMIN_TOKEN)<input id="tok" type="password"></label><button id="login">เข้าสู่ระบบ</button></div>
<div class="card"><div class="row">
<label>ชื่อผู้ทดลอง<input id="name" placeholder="เช่น คุณนก ฝ่ายขาย"></label>
<label>ทดลองได้กี่วัน (เว้นว่าง = ไม่จำกัด)<input id="days" type="number" min="1"></label>
<label>วันละกี่ครั้ง (เว้นว่าง = ไม่จำกัด)<input id="limit" type="number" min="1"></label>
<button id="create">สร้างรหัสทดลอง</button></div><p id="msg"></p></div>
<div class="card tbl"><table><thead><tr><th>รหัส</th><th>ชื่อ</th><th>วัน</th><th>ครั้ง/วัน</th><th>วันนี้ใช้</th><th>หมดอายุ</th><th>สถานะ</th><th></th></tr></thead><tbody id="rows"><tr><td colspan="8">เข้าสู่ระบบเพื่อดูรายการ</td></tr></tbody></table></div>
</div><script>
const $=id=>document.getElementById(id);let tok='';try{tok=localStorage.getItem('sj_tok')||''}catch(e){}$('tok').value=tok;
async function api(path,opt={}){const r=await fetch(path,{...opt,headers:{'authorization':'Bearer '+tok,'content-type':'application/json'}});const d=await r.json();if(!r.ok)throw new Error(d.error&&d.error.message||r.status);return d}
const fmt=t=>t?new Date(t).toLocaleString('th-TH',{dateStyle:'medium',timeStyle:'short'}):'-';
function status(c){if(c.revoked)return'<span class="pill off">ยกเลิก</span>';if(c.expires_at&&Date.now()>c.expires_at)return'<span class="pill off">หมดอายุ</span>';if(!c.activated_at)return'<span class="pill wait">ยังไม่เริ่มใช้</span>';return'<span class="pill on">ใช้งานอยู่</span>'}
async function load(){$('msg').textContent='';try{const list=await api('/api/codes');$('rows').innerHTML=list.length?list.map(c=>'<tr data-c="'+c.code+'"><td><code>'+c.code+'</code></td><td>'+(c.name||'-').replace(/</g,'&lt;')+'</td><td><input class="d" type="number" min="1" value="'+(c.days||'')+'" placeholder="∞"></td><td><input class="l" type="number" min="1" value="'+(c.daily_limit||'')+'" placeholder="∞"></td><td>'+c.used_today+'</td><td>'+(c.days?(c.expires_at?fmt(c.expires_at):'นับเมื่อเริ่มใช้'):'ไม่จำกัด')+'</td><td>'+status(c)+'</td><td><button class="ghost save">บันทึก</button> <button class="ghost copy">คัดลอก</button> <button class="danger rev">'+(c.revoked?'เปิดใหม่':'ยกเลิก')+'</button></td></tr>').join(''):'<tr><td colspan="8">ยังไม่มีรหัส</td></tr>'}catch(e){$('msg').textContent=e.message}}
$('login').onclick=()=>{tok=$('tok').value.trim();try{localStorage.setItem('sj_tok',tok)}catch(e){}load()};
$('create').onclick=async()=>{try{const c=await api('/api/codes',{method:'POST',body:JSON.stringify({name:$('name').value,days:$('days').value,daily_limit:$('limit').value})});$('name').value='';$('msg').style.color='var(--ok)';$('msg').textContent='สร้างแล้ว: '+c.code;load()}catch(e){$('msg').style.color='var(--red)';$('msg').textContent=e.message}};
$('rows').onclick=async e=>{const tr=e.target.closest('tr');if(!tr||!tr.dataset.c)return;const code=tr.dataset.c;try{
if(e.target.classList.contains('save')){await api('/api/codes/'+code,{method:'PUT',body:JSON.stringify({days:tr.querySelector('.d').value,daily_limit:tr.querySelector('.l').value})});load()}
if(e.target.classList.contains('rev')){await api('/api/codes/'+code,{method:'PUT',body:JSON.stringify({revoked:e.target.textContent==='ยกเลิก'})});load()}
if(e.target.classList.contains('copy')){await navigator.clipboard.writeText(code);e.target.textContent='คัดลอกแล้ว'}}catch(err){$('msg').textContent=err.message}};
if(tok)load();
</script></body></html>`;
