# ACMST Admissions — Admin & UAT Checklist

## Admin Setup
- Configure Brevo: API key, sender, template, language in Settings.
- Configure reCAPTCHA keys.
- Add Arabic fonts (TTF) under `static/src/fonts/` for PDF.
- Create Programs and Years.

## Import Candidates
- Use Admissions > Import Candidates.
- Optionally provide column mapping JSON.
- Track progress in Admissions > Import Jobs. Download errors CSV if needed.

## Public Flow UAT
- Lookup → Auth → Phone → OTP → Profile → PDFs
- Verify rate limits, reCAPTCHA prompts, OTP resend cooldown, daily cap.
- Confirm portal user auto-created and can access only own candidate.

## Reports
- Download both Admission and Embassy style PDFs.
- Validate Arabic text and RTL layout.

## Backup/Export
- Use admin export route `/admissions/admin/export` (admin/officer only) to CSV backup of candidates.


