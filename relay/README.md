# Speakaj Demo Relay — รหัสทดลอง ไม่ต้องใช้ API key

ตัวกลาง (Cloudflare Worker) ที่ถือ Groq key ของเราไว้ ผู้ทดลองแค่ใส่ **รหัสทดลอง** เช่น `DEMO-AB12-CD34`

- แต่ละรหัสกำหนด **จำนวนวันที่ทดลองได้** (นับจากวันแรกที่ใช้) และ **จำนวนครั้งต่อวัน** ได้ เว้นว่าง = ไม่จำกัด แก้ทีหลังได้ทุกเมื่อ
- ยกเลิกรหัสได้ทันทีจากหน้า `/admin`
- นับวันที่ฝั่งเซิร์ฟเวอร์ ย้อนนาฬิกาในเครื่องเพื่อโกงไม่ได้
- quota ฟรีของ Groq (~2,000 ครั้ง/วัน) นับรวมทุกคนที่ใช้ key เดียวกัน

## ติดตั้ง (ทำครั้งเดียว ~10 นาที ไม่ต้องมีโดเมน)

1. สมัครฟรีที่ <https://dash.cloudflare.com/sign-up>
2. **สร้างที่เก็บรหัส:** เมนูซ้าย **Storage & Databases → KV → Create** ตั้งชื่อ `speakaj-codes`
3. **สร้าง Worker:** เมนู **Workers & Pages → Create → Start with Hello World** ตั้งชื่อ `speakaj-relay` → **Deploy**
4. กด **Edit code** → ลบโค้ดเดิมทั้งหมด → วางโค้ดจากไฟล์ [`worker.js`](worker.js) → **Deploy**
5. กลับไปหน้า Worker → **Settings → Bindings → Add → KV namespace**
   - Variable name: `CODES` · KV namespace: `speakaj-codes` → **Deploy**
6. **Settings → Variables and Secrets → Add** (เลือก Type = **Secret**) 2 ตัว
   - `GROQ_API_KEY` = Groq key ของเรา (`gsk_...`)
   - `ADMIN_TOKEN` = รหัสผ่านสำหรับหน้าจัดการ ตั้งให้ยาวๆ เดายาก
7. จดลิงก์ Worker เช่น `https://speakaj-relay.ชื่อของคุณ.workers.dev` แล้วส่งให้ Claude ใส่ไว้ในโปรแกรม (`DEFAULT_RELAY_URL` ใน `speakaj/config.py`) แล้วออก release ใหม่

## ใช้งาน

- เปิด `https://speakaj-relay.ชื่อของคุณ.workers.dev/admin` → ใส่ `ADMIN_TOKEN` → **สร้างรหัสทดลอง**
- ส่งรหัสให้ผู้ทดลอง พร้อมลิงก์ดาวน์โหลด `Speakaj-Setup.exe`
- ผู้ทดลองเปิดโปรแกรมครั้งแรก ใส่รหัสในช่อง **รหัสทดลอง** → ใช้งานได้ทันที

| ข้อความที่ผู้ทดลองเห็น | ความหมาย |
|---|---|
| รหัสทดลองไม่ถูกต้อง | พิมพ์ผิด หรือรหัสถูกลบ |
| หมดระยะทดลองใช้แล้ว | ครบจำนวนวัน → แก้ "วัน" ในหน้า admin เพื่อต่ออายุ |
| ใช้ครบ N ครั้งของวันนี้แล้ว | ครบโควต้ารายวัน ใช้ต่อได้พรุ่งนี้ |
| รหัสทดลองนี้ถูกยกเลิกแล้ว | กดยกเลิกในหน้า admin |

## ทดสอบโค้ด

```bash
node relay/worker.test.mjs
```
