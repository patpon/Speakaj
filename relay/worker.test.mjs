// Run: node relay/worker.test.mjs
import assert from "node:assert/strict";
import worker from "./worker.js";

class KV {
  m = new Map();
  async get(k, type) { const v = this.m.get(k); return v == null ? null : type === "json" ? JSON.parse(v) : v; }
  async put(k, v) { this.m.set(k, v); }
  async delete(k) { this.m.delete(k); }
  async list({ prefix }) { return { keys: [...this.m.keys()].filter((k) => k.startsWith(prefix)).map((name) => ({ name })), list_complete: true }; }
}
const env = { CODES: new KV(), GROQ_API_KEY: "gsk_test", ADMIN_TOKEN: "secret" };
let groqCalls = 0;
globalThis.fetch = async (url, opt) => {
  groqCalls++;
  assert.equal(url, "https://api.groq.com/openai/v1/audio/transcriptions");
  assert.equal(opt.headers.Authorization, "Bearer gsk_test");
  assert.equal(opt.body.get("model"), "whisper-large-v3");
  return new Response(JSON.stringify({ text: "สวัสดี" }), { headers: { "content-type": "application/json" } });
};
const call = (path, init = {}) => worker.fetch(new Request("https://relay.test" + path, init), env);
const adminReq = (path, method = "GET", body) =>
  call(path, { method, headers: { authorization: "Bearer secret", "content-type": "application/json" }, body: body && JSON.stringify(body) });
const audio = () => { const f = new FormData(); f.set("file", new Blob([new Uint8Array(10)]), "speech.wav"); return f; };
const speak = (code) => call("/v1/transcribe", { method: "POST", headers: { "x-speakaj-code": code }, body: audio() });

// admin auth
assert.equal((await call("/api/codes")).status, 401);
// create a code with no limits
let r = await adminReq("/api/codes", "POST", { name: "คุณนก", days: "", daily_limit: "" });
assert.equal(r.status, 201);
const c = await r.json();
assert.match(c.code, /^DEMO-[A-Z2-9]{4}-[A-Z2-9]{4}$/);
assert.equal(c.days, null); assert.equal(c.daily_limit, null);

// wrong code rejected, right code works and activates the trial
assert.equal((await speak("DEMO-XXXX-XXXX")).status, 401);
r = await speak(c.code.toLowerCase());
assert.equal(r.status, 200); assert.equal((await r.json()).text, "สวัสดี");
let list = await (await adminReq("/api/codes")).json();
assert.equal(list[0].used_today, 1); assert.ok(list[0].activated_at);

// set limits later: 1 per day -> second call today is refused
r = await adminReq("/api/codes/" + c.code, "PUT", { daily_limit: 1, days: 7 });
assert.equal((await r.json()).daily_limit, 1);
r = await speak(c.code);
assert.equal(r.status, 429); assert.match((await r.json()).error.message, /ครบ 1 ครั้ง/);

// expiry: pretend it was activated 8 days ago
const rec = JSON.parse(env.CODES.m.get("code:" + c.code));
rec.activated_at = Date.now() - 8 * 86400e3; rec.daily_limit = null;
env.CODES.m.set("code:" + c.code, JSON.stringify(rec));
r = await speak(c.code);
assert.equal(r.status, 403); assert.match((await r.json()).error.message, /หมดระยะทดลอง/);

// revoke
await adminReq("/api/codes/" + c.code, "PUT", { reset_trial: true });
assert.equal((await speak(c.code)).status, 200);
await adminReq("/api/codes/" + c.code, "PUT", { revoked: true });
assert.equal((await speak(c.code)).status, 403);

// admin page is served
assert.match(await (await call("/admin")).text(), /จัดการรหัสทดลอง/);
assert.equal(groqCalls, 2);
console.log("relay tests passed");
