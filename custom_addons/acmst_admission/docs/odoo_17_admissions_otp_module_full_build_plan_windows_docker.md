# Odoo17 Admissions & OTP Module – Full Build Plan (Windows Docker)

> **Goal:** Deliver an Odoo 17 custom module that lets a visitor search their University ID from an admin‑uploaded Excel, proceed with a login/registration flow using **UniversityID + AcademicYear** as a single credential, verify identity via **WhatsApp OTP (Brevo)**, then land on a **Profile** page to complete/update records, and finally **download/print a branded QWeb form** (admission/embassy‑style design).

- **Stack & Env:** Odoo 17, Python 3.11, Postgres 15, wkhtmltopdf, Windows + Docker Desktop (Linux containers).
- **Languages:** Arabic/English content; names matching must be Arabic‑friendly with diacritics normalization.
- **Data Source:** Admin uploads an Excel sheet (candidates list).

---

## High‑Level Architecture

**Module name (suggested):** `acmst_admissions`

**Key Components**
- **Data Import**: Admin uploads Excel → background import → normalized **Candidate** table.
- **Website Lookup Page**: `/admissions/lookup` with a minimal search form (First/Second/Third/Fourth names, Program, optional filters). Returns **University ID** when found.
- **Credential Rule**: single **University ID** input = concatenation of `base_university_id + academic_year_code` (configurable rule), validated against Candidate table.
- **OTP (WhatsApp via Brevo)**: Generate + store OTP with rate‑limit & expiry, send via Brevo WhatsApp template, verify before granting Portal access.
- **Profile**: After OTP success → profile/update page mapped to Partner/Student models.
- **QWeb Report**: Download/print form with new design (admission/embassy‑style). Arabic‑friendly fonts and right‑to‑left tweaks.

---

## Daily Execution Plan (12 Days)

### **Day 1 – Repo, Docker, and Module Skeleton**
**Deliverables**
- Private Git repo created; CI disabled for now.
- `docker-compose.yml` with services: `odoo`, `db`, `mailhog` (optional), volume for `extra-addons`.
- New module scaffold `acmst_admissions/` with `__manifest__.py`, `__init__.py`, `security/ir.model.access.csv`.

**Checklist**
- Confirm wkhtmltopdf present in image (or add layer) for Arabic PDFs.
- `.env` with DB creds and `BREVO_API_KEY` placeholder.

### **Day 2 – Data Model & Config**
**Models**
- `admissions.candidate` – normalized table of uploaded Excel records.
- `admissions.program` – programs (code, name_ar, name_en).
- `admissions.year` – academic years (code, label, start/end dates, is_current).
- `admissions.settings` – system params (OTP TTL, rate limits, ID composition rule).
- `admissions.otp` – OTP store (phone, code, purpose, expiry, attempts, status, ip/user_agent).

**Fields (core)**
- Candidate: `first_ar`, `second_ar`, `third_ar`, `fourth_ar`, `first_en`, `second_en`, `third_en`, `fourth_en`, `program_id`, `base_university_id`, `academic_year_id`, `combined_university_id` (computed & indexed), `dob`, `national_id`, `is_active`, `extra_json`.

**Acceptance**
- Install module → models visible → access rules compile.

### **Day 3 – Excel Import Wizard**
**Wizard** `admissions.import.wizard`
- Binary field upload; sheet name/column mapping (drag‑map or select list).
- Validate headers; preview first 10 rows; background job (queue) to import.
- Deduplication policy (by `base_university_id` + `program` + `year`).
- Name normalization: strip tatweel/diacritics/hamza variants, normalize spaces.

**Acceptance**
- Upload sample Excel → candidates created → logs show counts & rejects.

### **Day 4 – Website Lookup (Public Route)**
**Controller** `/admissions/lookup`
- GET: render form; POST: perform search.
- Search algorithm tiers:
  1) Exact normalized match on all name parts + program + year.
  2) Soft match: allow missing one middle name or reordered tokens.
  3) Fallback: phonetic/levenshtein with threshold, but require program+year exact.
- Results: show masked **University ID** (e.g., show only last N chars) with action **“Use this ID”** → carries the full ID in session.

**Acceptance**
- Arabic/English inputs behave; returns expected candidate; rate‑limit by IP.

### **Day 5 – Custom Auth: UniversityID + Year**
**Flow**
- `/admissions/auth` page asks for **University ID** (single field). The rule is configurable; default concatenation is `base_university_id + academic_year.code` (no delimiter).
- Validate against `admissions.candidate`.
- If not found: link to help/manual review; log attempt.
- If found: proceed → phone capture.

**Acceptance**
- Invalid ID shows message; valid ID advances and binds to candidate in session.

### **Day 6 – Phone UX with Country Codes**
**Implementation**
- Use `res.country` phone codes and client‑side `intl‑tel-input` (served via `web.assets_frontend`).
- Server‑side validation using `phonenumbers` lib; store as E.164.
- Persist phone on candidate and/or partner temp record.

**Acceptance**
- Country dropdown works; mixed Arabic digits normalize to Western digits.

### **Day 7 – OTP Generation & Storage**
**Server**
- `admissions.otp.create_for(phone, purpose)` generates 6‑digit code, TTL (e.g., 5–10 min), stores hashed (e.g., SHA256) + salt.
- Rate‑limit: max N per hour/day per phone + IP; lockout after M failed attempts; audit trail.
- Templates: i18n message body for WhatsApp.

**Acceptance**
- Codes generated, stored hashed, visible in admin list (masked), with expiry indicators.

### **Day 8 – Brevo WhatsApp Integration**
**Service Layer** `admissions.brevo`
- System Parameter: `admissions.brevo_api_key`, `admissions.whatsapp_sender`, `admissions.whatsapp_template`.
- Endpoint wrapper (HTTPX/requests) with retry + logging (mask PII in logs).
- Send message containing OTP & metadata; store provider messageId.

**Acceptance**
- Test button in wizard sends to a sandbox number; green log status; graceful failure on API errors; exponential backoff.

### **Day 9 – OTP Verify + Portal User Creation**
**Flow**
- `/admissions/otp/verify` page; submit code.
- If valid: link candidate → create/find `res.partner` + Portal user (or attach to existing if phone/email matches), log consent flags; sign user in.
- If invalid/expired: safe error; resend policy.

**Acceptance**
- New user ends on profile page as **portal** with `acmst_admissions_portal` group.

### **Day 10 – Profile Page & Data Update**
**Website Page** `/admissions/profile`
- Fields: personal data (names AR/EN, DOB, national/passport no., address, phones, emails), program, year, attachments (photo, docs), guardian info.
- Model writes propagate to `admissions.candidate` + `res.partner`.
- Audit: track changed fields, who/when.

**Acceptance**
- Update works with Arabic text; validation (required fields, formats); file uploads saved to filestore.

### **Day 11 – QWeb Report (Download/Print)**
**Reports**
- `report.acmst_admissions_form`: branded admission form.
- `report.acmst_embassy_style`: embassy‑style variant (RTL layout, boxed inputs, signature areas).

**Implementation Notes**
- Custom fonts with Arabic support embedded (e.g., Amiri, Cairo), CSS for RTL.
- Button on profile: **Download Admission Form (PDF)**.
- `report_action` configured; ensure wkhtmltopdf args for RTL (–enable-local-file-access, proper DPI).

**Acceptance**
- PDF renders correctly (Arabic text, aligned fields, signatures); prints A4 cleanly.

### **Day 12 – Hardening, UAT, and Handover**
**Security/Hardening**
- CSRF + reCAPTCHA on public forms; IP throttling on lookup and OTP send.
- Access rules: candidates readable by own session key; admin full access.
- Logs: OTP audit, provider responses, PII masking.

**UAT**
- End‑to‑end from Excel → Lookup → Auth → OTP → Profile → PDF.
- Export & backup scripts for candidates table.

**Handover**
- README, admin manual, support SOPs, and rollback plan.

---

## Module Structure (Proposed)
```
acmst_admissions/
  __init__.py
  __manifest__.py
  security/
    ir.model.access.csv
    security.xml  # groups: admissions_admin, admissions_officer, admissions_portal
  data/
    admissions_data.xml  # default settings, years, sample programs
  models/
    __init__.py
    candidate.py
    program.py
    year.py
    settings.py
    otp.py
  controllers/
    __init__.py
    website.py   # lookup, auth, otp, profile routes
    api.py       # (optional) JSON endpoints for SPA behavior
  views/
    menu.xml
    candidate_views.xml
    program_views.xml
    settings_views.xml
    website_templates.xml  # lookup/auth/profile templates
  reports/
    report_templates.xml  # qweb templates
    report_actions.xml
  static/
    src/js/phone.js        # intl‑tel‑input init
    src/scss/rtl.scss      # RTL styles for forms & reports
  README.md
```

---

## Data Import Details

**Excel Mapping (wizard)**
- Configurable mapping UI for columns: First/Second/Third/Fourth (AR & EN), Program, Year, BaseID, DOB, NationalID.
- Field normalization (Arabic):
  - Strip diacritics (َ ُ ِ ّ ْ), tatweel (ـ), normalize hamza/ya/aleph variants (أ/إ/ا/آ → ا; ي/ى → ي; ة ↔ ه when needed).
  - Collapse multiple spaces; trim.
- Duplicates: treat rows with same (BaseID, Program, Year) as one (update latest wins; keep change log).
- `combined_university_id = base_university_id + year.code` (default). Rule can be changed with a Jinja‑like format in settings (e.g., `{{ base }}-{{ year }}`).

**Background Job**
- Chunk imports (e.g., 2–5k rows/batch), commit per chunk, show progress.
- Error CSV download with row numbers and causes.

---

## Controllers & Routes

- `GET /admissions/lookup` – render search form; `POST` to search.
- `GET /admissions/auth` – ask for UniversityID (single field); form posts to same.
- `POST /admissions/otp/send` – create OTP and call Brevo.
- `POST /admissions/otp/verify` – verify OTP and sign in.
- `GET/POST /admissions/profile` – display/update profile.

**Security**
- Lookup, auth, otp routes: `auth='public'`, `csrf=True`, throttled.
- Profile: `auth='user'` (portal or above).

---

## OTP Rules

- **Length:** 6 digits (configurable).
- **TTL:** 5–10 minutes (configurable).
- **Rate limits:** 3 sends / 15 min, 10 per day per phone; 5 verify attempts per code.
- **Storage:** hash(otp+salt) only; never log the raw OTP.
- **Abuse controls:** IP + device fingerprint heuristic; blacklisted numbers.

---

## Brevo (WhatsApp) Integration (Service Layer Sketch)

```python
# models/otp.py (excerpt)
from datetime import timedelta
from odoo import api, fields, models, _
import secrets, hashlib

class AdmissionsOtp(models.Model):
    _name = 'admissions.otp'
    phone = fields.Char(required=True, index=True)
    purpose = fields.Selection([('login','Login')], default='login')
    code_hash = fields.Char(index=True)
    salt = fields.Char()
    expire_at = fields.Datetime(index=True)
    attempts = fields.Integer(default=0)
    status = fields.Selection([('new','New'),('sent','Sent'),('ok','Verified'),('bad','Failed'),('exp','Expired')], default='new')

    def _hash(self, code, salt):
        return hashlib.sha256((code + salt).encode()).hexdigest()

    def generate(self, phone):
        code = f"{secrets.randbelow(10**6):06d}"
        salt = secrets.token_hex(8)
        self.write({'code_hash': self._hash(code, salt), 'salt': salt, 'expire_at': fields.Datetime.now() + timedelta(minutes=10)})
        return code
```

```python
# models/settings.py (service call, sketch)
import requests

class AdmissionsSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def brevo_send_whatsapp(self, phone_e164, body):
        api_key = self.env['ir.config_parameter'].sudo().get_param('admissions.brevo_api_key')
        sender = self.env['ir.config_parameter'].sudo().get_param('admissions.whatsapp_sender')
        template = self.env['ir.config_parameter'].sudo().get_param('admissions.whatsapp_template')
        payload = {
          # conform to Brevo WA API structure; include template, language, components/params
        }
        headers = {'api-key': api_key, 'accept': 'application/json', 'content-type': 'application/json'}
        # requests.post('https://api.brevo.com/v1/whatsapp/sendMessage', json=payload, headers=headers)
```

> **Note:** Exact payload/endpoint varies by Brevo account & WhatsApp template approval. Implement with a pluggable adapter and capture provider responses in a log model.

---

## Views (Snippets)

**Website Lookup Form (Jinja/QWeb)**
```xml
<t t-name="acmst_admissions.lookup">
  <div class="o_container">
    <form method="post" t-attf-action="/admissions/lookup" class="o_form">
      <input type="hidden" t-att-name="csrf_token" t-att-value="request.csrf_token()"/>
      <!-- Arabic name parts -->
      <input name="first_ar" required placeholder="الاسم الأول"/>
      <input name="second_ar" required placeholder="اسم الأب"/>
      <input name="third_ar" placeholder="اسم الجد"/>
      <input name="fourth_ar" placeholder="اللقب"/>
      <select name="program_id" required> ... </select>
      <select name="year_id" required> ... </select>
      <button type="submit" class="btn btn-primary">بحث</button>
    </form>
    <t t-if="results"> ... </t>
  </div>
</t>
```

**Auth (UniversityID single field)**
```xml
<t t-name="acmst_admissions.auth">
  <form method="post" action="/admissions/auth">
    <input type="hidden" name="csrf_token" t-att-value="request.csrf_token()"/>
    <input name="university_id" required placeholder="UniversityID (Base+Year)" dir="ltr"/>
    <button class="btn btn-primary" type="submit">متابعة</button>
  </form>
</t>
```

**Phone Input + OTP Send**
```xml
<input id="phone" name="phone" required/>
<script>
  // init intl-tel-input, enforce E.164 before submit
</script>
```

**Report Template (Admission/Embassy style)**
```xml
<template id="report_acmst_admissions_form">
  <t t-call="web.html_container">
    <t t-foreach="docs" t-as="d">
      <div class="rtl a4">
        <h2 class="center">استمارة القبول</h2>
        <!-- grid of labeled boxes, signature lines, photo box -->
      </div>
    </t>
  </t>
</template>
```

---

## Security & Access Rules

- **Groups**: `Admissions Admin`, `Admissions Officer`, `Admissions Portal`.
- **Record Rules**:
  - Portal: can read/write own candidate/partner record (linked via user_id or token).
  - Admin/Officer: full access to candidates & OTP logs.
- **Website**: CSRF on all forms; reCAPTCHA v2/3 for `/lookup` & `/otp/send`.

---

## Validation & Testing

**Unit**
- Name normalization tests (Arabic edge cases).
- ID composition parser: conversion both ways (compose/decompose).
- OTP hashing/expiry/rate limits.

**Integration**
- Excel → candidates (10k rows) within acceptable time.
- Lookup hit‑rate on known data.
- End‑to‑end: Auth → OTP → Profile → PDF.

**UAT Scenarios**
- Missing middle name; different order; extra whitespace.
- Wrong program/year; should **not** return a match.
- OTP expired; resend flow; lockout after 5 bad tries.

---

## Deployment (Windows + Docker Desktop)

**docker-compose.yml (sketch)**
```yaml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: odoo
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: odoo
    volumes:
      - db-data:/var/lib/postgresql/data
  odoo:
    image: odoo:17
    depends_on: [db]
    ports: ["8069:8069"]
    environment:
      HOST: db
      USER: odoo
      PASSWORD: odoo
    volumes:
      - ./.extra-addons:/mnt/extra-addons  # Windows path mounted to Linux path
      - ./odoo-data:/var/lib/odoo
volumes:
  db-data:
```

**Notes**
- On Windows mounts, avoid `chown` inside container; set Windows folder permissions instead.
- Install fonts into the image/volume used by wkhtmltopdf; register in CSS.
- For production: reverse proxy (Nginx) + HTTPS + secure cookies + long session TTL only after OTP.

---

## Configuration Parameters

- `admissions.id_rule` = `{{ base }}{{ year }}`
- `admissions.otp_ttl_minutes` = 10
- `admissions.otp_max_send_per_15m` = 3
- `admissions.otp_max_verify_attempts` = 5
- `admissions.brevo_api_key` = `***`
- `admissions.whatsapp_sender` = `whatsapp:+971XXXX`
- `admissions.whatsapp_template` = `otp_template_code`

---

## Field Mapping (Profile → Report)

| Profile Field | Report Label (AR/EN) | QWeb Expr |
|---|---|---|
| names AR/EN | الاسم الرباعي / Full Name | `t-esc="d.name_ar"` etc. |
| program/year | البرنامج / Program | `d.program_id.name_ar` |
| national/passport | الرقم الوطني / Passport | `d.national_id` |
| phones | هاتف / Phone | `d.phone_e164` |
| address | العنوان | `d.street` `d.city` `d.country_id` |
| guardian | ولي الأمر | `d.guardian_name` / `d.guardian_phone` |
| signatures | توقيع الطالب / ولي الأمر | static boxes |
| photo | صورة | img placeholder |

---

## Future Enhancements
- **Admin Review Queue** for fuzzy matches needing human confirmation.
- **Email/SMS fallback** when WhatsApp delivery fails.
- **Webhook** listener for Brevo delivery receipts.
- **Self‑service corrections** on name spelling pre‑admission lock.
- **Bulk PDF generation** for cohorts.

---

## Acceptance Criteria (Condensed)
1) Admin can upload Excel and import succeeds with normalized, deduplicated rows.
2) Public can find their ID by name/program/year; false positives are prevented.
3) University ID (Base+Year) login flow works; invalid IDs are rejected.
4) Phone capture with country codes and E.164 validation.
5) OTP send via Brevo WhatsApp, with TTL/rate limits and secure verification.
6) After OTP, user lands on Profile and can update required fields.
7) QWeb PDF downloads with Arabic/RTL fidelity and prints cleanly.
8) Logs, throttling, and access rules in place; PII protected.

---

## Admin & Operator SOP (Quick)
- **Upload Excel** → Import Wizard → Check import logs.
- **Lookup complaints** → Search candidate by name/phone; verify audit trail.
- **Resend OTP** → From candidate form action.
- **Regenerate PDF** → From profile button or candidate record action.

---

## README Pointers (to include in repo)
- How to add Arabic fonts for wkhtmltopdf.
- How to configure Brevo WhatsApp template placeholders ({{code}}, {{ttl}}).
- How to change the University ID rule.
- How to export the candidate list for archival.

