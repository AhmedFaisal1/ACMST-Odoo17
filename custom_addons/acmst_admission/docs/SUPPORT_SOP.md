# ACMST Admissions — Support SOP (No Rollback)

## Scope
- Day-to-day support for admissions lookup, OTP delivery, profile updates, and PDF reports.
- Covers triage steps, where to check, and how to resolve common issues.

## First-Response Checklist (All Issues)
- Reproduce the issue with a non-admin portal account when applicable.
- Check server logs (Odoo logs) for exceptions around the reported time.
- Confirm system parameters in Settings: Brevo, reCAPTCHA, rate limits.
- Verify candidate record exists and is active for the user in question.

## OTP & Brevo
- Verify phone format: E.164 stored on candidate and shown in session.
- Rate limits: ensure user isn’t hitting cooldown or daily cap.
- Blacklist: confirm phone isn’t listed in Settings blacklist.
- Brevo status:
  - View Admissions > OTP Logs for webhook entries and sending errors.
  - If missing logs, verify webhook URL and secret, and provider template status.
- Re-send policy: respect cooldown (Settings) and don’t increase caps without approval.

## reCAPTCHA
- Symptoms: “reCAPTCHA validation failed.”
- Verify site/secret keys in Settings and that the domain matches.
- Browser: ensure no ad/script blockers prevent the widget from loading.
- Server can reach Google verify endpoint (outbound HTTPS).

## Import Jobs
- Use Admissions > Import Jobs to monitor progress.
- For failed rows, download the Errors CSV and correct source data.
- For different headers, use column Mapping JSON in the wizard.
- If large files stall, split into smaller chunks and re-enqueue.

## Lookup & Matching
- Confirm Program and Year selections match imported candidate rows.
- Fuzzy matching: acceptable typos are allowed; if results are noisy, tighten inputs.
- Consider exact search by University ID via Auth when names are ambiguous.

## Profile & Portal Access
- Portal users can only access their own candidate.
- If access denied, link partner to candidate (partner_id) or re-verify OTP flow.
- Update Arabic name fields with normalized text; avoid diacritics in source data.

## PDFs & Fonts
- If Arabic renders as boxes/question marks:
  - Ensure fonts exist in container and in module `static/src/fonts/`.
  - Verify report assets are loaded (web.report_assets_common bundle).
- If download fails, check wkhtmltopdf availability and Odoo log for report errors.

## Data Export/Backup
- Use admin/officer export: `/admissions/admin/export` for CSV.
- Periodic DB backups should be managed by ops; verify schedules.

## Configuration Changes
- All config in Settings > Admissions section (Brevo, reCAPTCHA, blacklist, rate limits).
- Changes take effect immediately; document alterations in a support ticket.

## Diagnostics & Logs
- Odoo logs: look for “Brevo OTP Send” warnings and controller tracebacks.
- OTP Logs: Admissions > OTP Logs for webhook payloads and statuses.
- Import logs: visible on Import Job form (progress and errors).

## Escalation
- Severity 1 (blocking login or PDF for many users): page on-call, attach logs and steps.
- Severity 2 (single user OTP or import row failures): respond within business day; attach evidence.
- Include: user email/phone (masked), time window, environment, screenshots, and exported logs.
