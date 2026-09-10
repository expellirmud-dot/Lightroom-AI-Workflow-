# คู่มือผู้ใช้ — Lightroom AI Exposure Assist

คู่มือนี้เป็นขั้นตอนใช้งานปกติของระบบ **Minimal Production / one-job workflow** สำหรับเจ้าของงานหรือผู้ใช้งานทั่วไป โดยไม่ต้องจำคำสั่ง legacy แบบ session/pass รุ่นเก่า

## วิธีใช้งานปกติ

1. เปิด **Lightroom Classic → Library** แล้วเลือกโฟลเดอร์งานที่ต้องการประมวลผล
2. เลือก Preset / Develop baseline ที่ต้องการให้ระบบใช้เป็นจุดเริ่มต้น และบันทึก Metadata/XMP ตาม workflow ของงาน
3. รัน **Library → Plug-in Extras → AI Exposure Assist — Continue Exposure Workflow**
4. ถ้าเป็นโฟลเดอร์ใหม่ ระบบจะสร้าง production job เพียงหนึ่งงาน พร้อม preview/contact sheet และแสดง **Job ID** กับโฟลเดอร์ของ job
5. แจ้ง Nexus/ChatGPT ว่า production package พร้อมแล้ว เพื่อให้ทำขั้น **Visual Semantics**
6. AI มีหน้าที่เฉพาะการดูภาพและตีความเชิงภาพ ได้แก่:
   - จัดภาพที่เป็นช็อตหรือสภาพแสงเดียวกันให้อยู่กลุ่มเดียวกัน
   - เลือกภาพอ้างอิง (reference) ที่เหมาะสมของแต่ละกลุ่ม
   - ระบุภาพที่ดูโอเคและไม่จำเป็นต้องปรับ
   - ระบุภาพที่ไม่ควรตัดสินอัตโนมัติเป็น `UNRESOLVED`
   - **AI ไม่คำนวณตัวเลข EV และไม่มีสิทธิ์เขียนค่าเข้า Lightroom**
7. Python ใช้ผล Visual Semantics ร่วมกับ measurement แบบ deterministic เพื่อ:
   - วัดความสว่างของภาพ
   - คำนวณ Exposure delta / target
   - จำกัดค่าตาม safety bounds
   - จัดทุกภาพเป็น `WILL_ADJUST`, `NO_CHANGE` หรือ `UNRESOLVED`
   - การวัด **ไม่บังคับว่าต้องมีใบหน้า**; production route รองรับ scene-based measurement สำหรับภาพทั่วไป
8. เมื่อขั้นวิเคราะห์เสร็จ ให้กลับมาที่โฟลเดอร์เดิมใน Lightroom แล้วรัน **Continue Exposure Workflow** อีกครั้ง
9. เมื่อขึ้น `READY_TO_APPLY` ระบบจะแสดงจำนวน:
   - Total
   - Will adjust
   - No change
   - Unresolved

   ตรวจตัวเลขก่อน แล้วกด **Apply Exposure** เฉพาะเมื่อยืนยันว่าจะเขียนค่าจริง
10. ระบบจะส่งเฉพาะภาพ `WILL_ADJUST` ผ่าน `CatalogApplyBarrier.lua` เท่านั้น ภาพ `NO_CHANGE` และ `UNRESOLVED` จะไม่ถูกแก้ในรอบนั้น
11. หลัง Catalog apply ผ่าน ระบบจะขึ้น `VERIFYING` ให้รอ Lightroom refresh preview ของภาพที่เพิ่งปรับ แล้วรัน **Continue Exposure Workflow** อีกครั้ง
12. ระบบจะอ่าน fresh preview และตรวจผลหลังปรับจริง
13. ถ้าบางภาพยังต้องแก้เล็กน้อย ระบบอนุญาต **residual correction ได้เพียง 1 รอบ** และต้องขึ้นหน้าต่างให้เจ้าของงานยืนยัน **Fine-Tune Exposure** แยกต่างหาก
14. หลัง residual apply ให้รอ Lightroom refresh preview อีกครั้ง แล้วรัน **Continue Exposure Workflow** เป็นครั้งสุดท้าย
15. เมื่อขึ้น `COMPLETE` ให้ดู `Final accounting` ซึ่งต้องรวมครบทุกภาพ และ `Invariant verified` ต้องเป็น `true`
16. การ Export JPEG ขั้นสุดท้ายยังทำเองตามปกติใน Lightroom

## ความหมายของสถานะที่เห็นใน Lightroom

- `READY` — พร้อมเริ่มงานใหม่
- `ANALYZING` — production package ถูกสร้างแล้ว และกำลังรอ/ทำ Visual Semantics หรือ deterministic planning
- `READY_TO_APPLY` — แผนคำนวณเสร็จ พร้อมให้เจ้าของงานยืนยันก่อนเขียนค่า Exposure
- `VERIFYING` — เขียนค่าแล้ว กำลังรอ/ตรวจ fresh preview
- `COMPLETE` — งานจบและ accounted for ครบ
- `NEEDS_ATTENTION` — ต้องตรวจปัญหาก่อนดำเนินการต่อ

คำศัพท์ legacy เช่น Gate / Pass / AUTO_READY / session convergence ไม่ใช่ workflow ปกติของ production route นี้

## ถ้าเจอ `UNRESOLVED`

`UNRESOLVED` ไม่ได้แปลว่าโปรแกรมพัง แต่หมายถึงระบบเลือก **ไม่ฝืนปรับอัตโนมัติ** เมื่อหลักฐานหรือค่าที่ต้องแก้เกินขอบเขตที่อนุญาต

ตัวอย่าง reason ที่อาจพบ:

- `DELTA_OUT_OF_BOUNDS` — ค่า Exposure ที่คำนวณได้เกิน safety bound จึงไม่เขียนอัตโนมัติ
- `RESIDUAL_NOT_SETTLED` — ใช้ residual correction ครบ 1 รอบแล้ว แต่ผลยังไม่เข้าเกณฑ์ จึงหยุดและให้ตรวจด้วยคน

ภาพ `UNRESOLVED` ต้องตรวจและปรับเองใน Lightroom ตามความเหมาะสม

## ถ้า AI/provider ช้าหรือต้องการเปลี่ยน AI

ขอบเขต Visual Semantics ออกแบบให้ **ไม่ล็อกผู้ให้บริการ AI รายใดรายหนึ่ง**

AI ตัวใหม่ต้องทำงานกับ production package เดิมและคืนเฉพาะผล semantic contract เดิม ได้แก่ grouping / reference / no-change / unresolved เท่านั้น การเปลี่ยน AI ต้องไม่:

- เริ่ม Lightroom job ใหม่โดยไม่จำเป็น
- คำนวณ numeric EV เอง
- เขียนค่าเข้า Lightroom
- สร้าง Catalog writer ตัวที่สอง

External AI / AGY / worker อื่นเป็นเพียงผู้ช่วย Visual Semantics และไม่มี Catalog mutation authority

## คำสั่ง legacy

เมนูต่อไปนี้เป็น compatibility/recovery surface ไม่ใช่ workflow ปกติ:

- `Prepare AI Package`
- `Import / Apply AI Results`
- `Prepare Next AI Package`
- legacy single-pass commands

สำหรับการใช้งานทั่วไป ให้เลือกโฟลเดอร์งานที่ถูกต้องแล้วใช้ **Continue Exposure Workflow** เป็นหลัก

## กฎ Production ที่สำคัญ

workflow ปกติคือ:

`AI semantics 1 รอบ → deterministic measurement/plan → guarded apply → fresh verification เฉพาะภาพที่ปรับ → residual ได้สูงสุด 1 รอบ → final accounting`

## ความปลอดภัย

- ห้ามแก้ฐานข้อมูล Lightroom Catalog โดยตรง
- ห้ามเขียนไฟล์ภายใน `.lrdata` โดยตรง
- ห้ามแก้ RAW/JPEG ต้นฉบับ
- AI ไม่มีสิทธิ์ mutate Lightroom
- Initial Catalog apply ต้องได้รับการยืนยันจากเจ้าของงาน
- Residual Catalog apply ต้องได้รับการยืนยันแยกอีกครั้ง
- การเปลี่ยน Exposure จริงเกิดผ่าน guarded Lightroom Catalog boundary เท่านั้น

## ตัวอย่างผลยืนยันจากงานจริง

Production job `job-1789032689` บนโฟลเดอร์ `D:\2569-09-03` จบ `COMPLETE` และ accounted for ครบ `752/752` ภาพ:

- Adjusted: **432**
- No change: **232**
- Unresolved: **88**
- Invariant verified: **true**

ใน 88 ภาพที่ unresolved:

- `DELTA_OUT_OF_BOUNDS`: 87 ภาพ
- `RESIDUAL_NOT_SETTLED`: 1 ภาพ

ผลนี้ยืนยันว่า workflow สามารถทำตั้งแต่ production package → AI semantics → deterministic planning → guarded Catalog apply → fresh verification → residual → final accounting ได้จบครบทั้งอัลบั้ม โดยภาพที่เกิน safety bound ถูกหยุดไว้แทนการฝืนปรับอัตโนมัติ
