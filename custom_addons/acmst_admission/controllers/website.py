from odoo import http, fields
from odoo.http import request
from ..models.utils import normalize_arabic, to_western_digits


class AdmissionsWebsite(http.Controller):
    @http.route('/admissions/health', type='http', auth='public')
    def admissions_health(self, **kwargs):
        return "OK"

    @http.route('/admissions/lookup', type='http', auth='public', website=True, csrf=True, methods=['GET', 'POST'])
    def admissions_lookup(self, **kwargs):
        env = request.env
        programs = env['admissions.program'].sudo().search([], order='code')
        years = env['admissions.year'].sudo().search([], order='code desc')
        values = {
            'results': [],
            'query': kwargs,
            'programs': programs,
            'years': years,
            'recaptcha_site_key': env['ir.config_parameter'].sudo().get_param('acmst_admission.recaptcha_site_key') or '',
        }
        if request.httprequest.method == 'POST':
            ip = request.httprequest.remote_addr or '0.0.0.0'
            settings = env['admissions.settings'].sudo().search([], limit=1) or env['admissions.settings']
            window = settings.rate_limit_window_minutes or 15
            max_hits = 30  # per window for lookup
            limited = env['admissions.rate.limit'].sudo().is_limited('lookup', ip, window, max_hits)
            if limited:
                values['error'] = 'Too many requests. Please try again later.'
                return request.render('acmst_admission.lookup', values)
            env['admissions.rate.limit'].sudo().hit('lookup', ip)

            # Optional reCAPTCHA verification
            token = kwargs.get('g-recaptcha-response')
            if not self._verify_recaptcha(token, ip):
                # If not configured, _verify_recaptcha returns True
                values['error'] = 'reCAPTCHA validation failed.'
                return request.render('acmst_admission.lookup', values)

            # Inputs
            first_ar = normalize_arabic(kwargs.get('first_ar'))
            second_ar = normalize_arabic(kwargs.get('second_ar'))
            third_ar = normalize_arabic(kwargs.get('third_ar'))
            fourth_ar = normalize_arabic(kwargs.get('fourth_ar'))
            program_code = (kwargs.get('program_code') or '').strip()
            year_code = (kwargs.get('year_code') or '').strip()

            domain = []
            if program_code:
                prog = env['admissions.program'].sudo().search([('code', '=', program_code)], limit=1)
                if prog:
                    domain.append(('program_id', '=', prog.id))
            if year_code:
                year = env['admissions.year'].sudo().search([('code', '=', year_code)], limit=1)
                if year:
                    domain.append(('academic_year_id', '=', year.id))

            # Tier 1: Exact normalized match on all provided Arabic name parts
            candidates = env['admissions.candidate'].sudo().search(domain, limit=500)
            def norm(s):
                return (normalize_arabic(s or '') or '').lower()
            results = []
            for c in candidates:
                if first_ar and norm(c.first_ar) != norm(first_ar):
                    continue
                if second_ar and norm(c.second_ar) != norm(second_ar):
                    continue
                if third_ar and norm(c.third_ar) != norm(third_ar):
                    continue
                if fourth_ar and norm(c.fourth_ar) != norm(fourth_ar):
                    continue
                results.append({
                    'id': c.id,
                    'name_ar': ' '.join(filter(None, [c.first_ar, c.second_ar, c.third_ar, c.fourth_ar])),
                    'uid': c.combined_university_id or '',
                    'masked_id': (c.combined_university_id or '')[-4:],
                })
            # Tier 2: Soft match allowing one missing middle name
            if not results and any([first_ar, second_ar, third_ar, fourth_ar]):
                for c in candidates:
                    parts_q = [p for p in [first_ar, second_ar, third_ar, fourth_ar] if p]
                    parts_c = [normalize_arabic(p) for p in [c.first_ar, c.second_ar, c.third_ar, c.fourth_ar] if p]
                    # Allow one token difference
                    matches = sum(1 for p in parts_q if normalize_arabic(p) in parts_c)
                    if matches >= max(1, len(parts_q) - 1):
                        results.append({
                            'id': c.id,
                            'name_ar': ' '.join(filter(None, [c.first_ar, c.second_ar, c.third_ar, c.fourth_ar])),
                            'uid': c.combined_university_id or '',
                            'masked_id': (c.combined_university_id or '')[-4:],
                        })
            # Tier 3: Fuzzy ratio using difflib on concatenated names and token-level average
            if not results and any([first_ar, second_ar, third_ar, fourth_ar]):
                # Prefer rapidfuzz if available; fallback to difflib
                query_tokens = [t for t in normalize_arabic(' '.join(filter(None, [first_ar, second_ar, third_ar, fourth_ar]))).split(' ') if t]
                try:
                    from rapidfuzz import fuzz
                    def score(a, b):
                        return max(fuzz.partial_ratio(a, b), fuzz.token_set_ratio(a, b)) / 100.0
                except Exception:
                    import difflib
                    def score(a, b):
                        return difflib.SequenceMatcher(None, a, b).ratio()
                query_name = ' '.join(query_tokens)
                for c in candidates:
                    cand_tokens = [t for t in normalize_arabic(' '.join(filter(None, [c.first_ar, c.second_ar, c.third_ar, c.fourth_ar]))).split(' ') if t]
                    cand_name = ' '.join(cand_tokens)
                    ratio = score(query_name, cand_name)
                    token_scores = []
                    for qt in query_tokens:
                        best = 0.0
                        for ct in cand_tokens:
                            s = score(qt, ct)
                            if s > best:
                                best = s
                        if best:
                            token_scores.append(best)
                    avg_token = sum(token_scores) / len(token_scores) if token_scores else 0
                    if ratio >= 0.8 or avg_token >= 0.85:
                        results.append({
                            'id': c.id,
                            'name_ar': ' '.join(filter(None, [c.first_ar, c.second_ar, c.third_ar, c.fourth_ar])),
                            'uid': c.combined_university_id or '',
                            'masked_id': (c.combined_university_id or '')[-4:],
                        })
            values['results'] = results[:20]
        return request.render('acmst_admission.lookup', values)

    @http.route('/admissions/use_id', type='http', auth='public', website=True)
    def admissions_use_id(self, id=None, **kwargs):
        if not id:
            return request.redirect('/admissions/lookup')
        cand = request.env['admissions.candidate'].sudo().browse(int(id))
        if not cand:
            return request.redirect('/admissions/lookup')
        request.session['admissions_candidate_id'] = cand.id
        uid = cand.combined_university_id or ''
        request.session['admissions_university_id'] = uid
        return request.redirect('/admissions/auth?university_id=%s' % uid)

    @http.route('/admissions/import/sample-csv', type='http', auth='user')
    def admissions_sample_csv(self, **kwargs):
        # Provide a sample CSV with expected headers
        headers = [
            'first_ar','second_ar','third_ar','fourth_ar',
            'first_en','second_en','third_en','fourth_en',
            'program_code','year_code','base_university_id','dob','national_id',
        ]
        content = ','.join(headers) + "\n"
        return request.make_response(
            content.encode('utf-8'),
            headers=[
                ('Content-Type', 'text/csv; charset=utf-8'),
                ('Content-Disposition', 'attachment; filename="admissions_sample.csv"'),
            ],
        )

    @http.route('/admissions/admin/export', type='http', auth='user')
    def admissions_export_csv(self, **kwargs):
        # Admin/officer-only CSV export of candidates
        user = request.env.user
        if not (user.has_group('acmst_admission.group_admissions_admin') or user.has_group('acmst_admission.group_admissions_officer')):
            return request.not_found()
        fields_out = ['combined_university_id','base_university_id','program','year','first_ar','second_ar','third_ar','fourth_ar','first_en','second_en','third_en','fourth_en','dob','national_id','phone']
        Candidate = request.env['admissions.candidate'].sudo()
        recs = Candidate.search([], limit=50000)
        import io, csv
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(fields_out)
        for c in recs:
            writer.writerow([
                c.combined_university_id or '', c.base_university_id or '', c.program_id.code or '', c.academic_year_id.code or '',
                c.first_ar or '', c.second_ar or '', c.third_ar or '', c.fourth_ar or '',
                c.first_en or '', c.second_en or '', c.third_en or '', c.fourth_en or '',
                c.dob or '', c.national_id or '', c.phone or ''
            ])
        content = out.getvalue().encode('utf-8')
        return request.make_response(
            content,
            headers=[('Content-Type','text/csv; charset=utf-8'), ('Content-Disposition','attachment; filename="admissions_export.csv"')]
        )

    @http.route('/admissions/auth', type='http', auth='public', website=True, csrf=True, methods=['GET', 'POST'])
    def admissions_auth(self, **kwargs):
        env = request.env
        values = {'error': None,
                  'recaptcha_site_key': env['ir.config_parameter'].sudo().get_param('acmst_admission.recaptcha_site_key') or ''}
        if request.httprequest.method == 'POST':
            # Optional reCAPTCHA
            token = kwargs.get('g-recaptcha-response')
            if not self._verify_recaptcha(token, request.httprequest.remote_addr or '0.0.0.0'):
                values['error'] = 'reCAPTCHA validation failed.'
                return request.render('acmst_admission.auth', values)
            uid_input = to_western_digits(kwargs.get('university_id') or '').strip()
            # Try exact combined match first
            cand = env['admissions.candidate'].sudo().search([('combined_university_id', '=', uid_input)], limit=1)
            if not cand and uid_input.isdigit() and len(uid_input) > 4:
                # Fallback: treat as base + last 4-digit year
                base_part = uid_input[:-4]
                year_tail = uid_input[-4:]
                cand = env['admissions.candidate'].sudo().search([
                    ('base_university_id', '=', base_part),
                    ('academic_year_id.code', 'ilike', year_tail),
                ], limit=1)
            if not cand:
                values['error'] = 'University ID not found.'
            else:
                request.session['admissions_candidate_id'] = cand.id
                return request.redirect('/admissions/phone')
        # Prefill University ID if present
        uni = kwargs.get('university_id') or request.session.get('admissions_university_id') or ''
        values['university_id'] = uni
        return request.render('acmst_admission.auth', values)

    @http.route('/admissions/phone', type='http', auth='public', website=True, csrf=True, methods=['GET', 'POST'])
    def admissions_phone(self, **kwargs):
        env = request.env
        cand_id = request.session.get('admissions_candidate_id')
        if not cand_id:
            return request.redirect('/admissions/auth')
        values = {
            'error': None,
            'recaptcha_site_key': env['ir.config_parameter'].sudo().get_param('acmst_admission.recaptcha_site_key') or '',
        }
        if request.httprequest.method == 'POST':
            phone = kwargs.get('phone')
            from ..models.utils import try_format_e164
            e164 = try_format_e164(phone)
            if not e164:
                values['error'] = 'Invalid phone number.'
            else:
                request.session['admissions_phone'] = e164
                return request.redirect('/admissions/otp')
        return request.render('acmst_admission.phone', values)

    @http.route('/admissions/otp/send', type='json', auth='public', csrf=True)
    def admissions_otp_send(self, phone=None, recaptcha_token=None, **kwargs):
        env = request.env
        ip = request.httprequest.remote_addr or '0.0.0.0'
        # Optional reCAPTCHA verification
        if not self._verify_recaptcha(recaptcha_token, ip):
            return {'ok': False, 'message': 'reCAPTCHA validation failed.'}
        settings = env['admissions.settings'].sudo().search([], limit=1) or env['admissions.settings']
        window = settings.rate_limit_window_minutes or 15
        if env['admissions.rate.limit'].sudo().is_limited('otp_send', ip, window, settings.rate_limit_sends_per_window or 3):
            return {'ok': False, 'message': 'Too many OTP requests. Please wait.'}
        env['admissions.rate.limit'].sudo().hit('otp_send', ip)

        phone = phone or request.session.get('admissions_phone')
        if not phone:
            return {'ok': False, 'message': 'No phone in session.'}

        # Blacklist check
        raw_blacklist = request.env['ir.config_parameter'].sudo().get_param('acmst_admission.blacklist_phones') or ''
        import re
        blacklist = [p.strip() for p in re.split(r'[\s,;]+', raw_blacklist) if p.strip()]
        if phone in blacklist:
            return {'ok': False, 'message': 'Phone number is not allowed.'}

        # Per-phone daily cap
        from datetime import timedelta
        from odoo import fields as oof
        since = oof.Datetime.now() - timedelta(days=1)
        sent_count = env['admissions.otp'].sudo().search_count([
            ('phone', '=', phone), ('create_date', '>=', since), ('purpose', '=', 'login')
        ])
        daily_cap = int(settings.rate_limit_daily_sends or 10)
        if sent_count >= daily_cap:
            return {'ok': False, 'message': 'Daily OTP limit reached for this phone.'}

        # Cooldown enforcement
        cooldown = int(settings.otp_cooldown_seconds or 60)
        last = env['admissions.otp'].sudo().search([('phone', '=', phone), ('purpose', '=', 'login')], order='id desc', limit=1)
        if last and last.create_date and (oof.Datetime.now() - last.create_date).total_seconds() < cooldown:
            return {'ok': False, 'message': 'Please wait before requesting another OTP.'}

        # Generate OTP and store (hash)
        import secrets, hashlib
        length = settings.otp_length or 6
        code = ''.join(secrets.choice('0123456789') for _ in range(length))
        salt = secrets.token_hex(8)
        code_hash = hashlib.sha256((code + salt).encode()).hexdigest()
        from datetime import timedelta
        expire_at = fields.Datetime.now() + timedelta(minutes=int(settings.otp_ttl_minutes or 10))
        env['admissions.otp'].sudo().create({
            'phone': phone,
            'purpose': 'login',
            'code_hash': code_hash,
            'salt': salt,
            'expire_at': expire_at,
            'status': 'sent',
            'ip': ip,
            'user_agent': request.httprequest.headers.get('User-Agent'),
        })

        # Send via Brevo (template)
        msg = 'OTP sent'
        try:
            self._send_brevo_whatsapp(phone, code)
        except Exception as e:
            # Log and fallback
            request.env['ir.logging'].sudo().create({
                'name': 'Brevo OTP Send',
                'type': 'server',
                'level': 'WARNING',
                'message': f'Brevo send failed: {e}',
                'path': __name__,
                'func': '_send_brevo_whatsapp',
                'line': 0,
            })
            msg = 'OTP generated (provider not configured)'
        return {'ok': True, 'message': msg}

    @http.route('/admissions/otp/verify', type='json', auth='public', csrf=True)
    def admissions_otp_verify(self, phone=None, code=None, recaptcha_token=None, **kwargs):
        env = request.env
        # Optional reCAPTCHA verification
        if not self._verify_recaptcha(recaptcha_token, request.httprequest.remote_addr or '0.0.0.0'):
            return {'ok': False, 'message': 'reCAPTCHA validation failed.'}
        phone = phone or request.session.get('admissions_phone')
        if not (phone and code):
            return {'ok': False, 'message': 'Missing phone or code.'}
        rec = env['admissions.otp'].sudo().search([('phone', '=', phone), ('purpose', '=', 'login')], order='id desc', limit=1)
        if not rec:
            return {'ok': False, 'message': 'No OTP found.'}
        import hashlib
        if rec.status in ('ok', 'exp'):
            return {'ok': False, 'message': 'OTP already used or expired.'}
        if rec.attempts >= (env['admissions.settings'].sudo().search([], limit=1).verify_attempts_per_code or 5):
            rec.write({'status': 'bad'})
            return {'ok': False, 'message': 'Too many attempts.'}
        code_hash = hashlib.sha256((code + (rec.salt or '')).encode()).hexdigest()
        if code_hash != rec.code_hash:
            rec.write({'attempts': rec.attempts + 1})
            return {'ok': False, 'message': 'Invalid code.'}
        if fields.Datetime.now() > rec.expire_at:
            rec.write({'status': 'exp'})
            return {'ok': False, 'message': 'Code expired.'}
        rec.write({'status': 'ok'})
        request.session['admissions_otp_ok'] = True

        # Create/link partner and portal user, then authenticate
        cand_id = request.session.get('admissions_candidate_id')
        if not cand_id:
            return {'ok': True, 'message': 'Verified'}  # proceed but cannot bind user
        cand = env['admissions.candidate'].sudo().browse(int(cand_id))
        if not cand.exists():
            return {'ok': True, 'message': 'Verified'}
        if not cand.partner_id:
            display_name = ' '.join(filter(None, [cand.first_ar, cand.second_ar, cand.third_ar, cand.fourth_ar])) or cand.combined_university_id
            partner = env['res.partner'].sudo().create({
                'name': display_name,
                'phone': phone,
            })
            cand.sudo().partner_id = partner.id
        else:
            partner = cand.partner_id.sudo()
            if phone and partner.phone != phone:
                partner.phone = phone

        # Persist E.164 phone to candidate record
        if phone and (not cand.phone or cand.phone != phone):
            cand.sudo().write({'phone': phone})

        # Ensure portal user
        login = f"admissions-{cand.id}"
        Users = env['res.users'].sudo().with_context(no_reset_password=True)
        user = Users.search([('login', '=', login)], limit=1)
        import secrets
        password = secrets.token_urlsafe(12)
        group_ids = []
        try:
            group_ids.append(env.ref('portal.group_portal').id)
        except Exception:
            pass
        try:
            group_ids.append(env.ref('acmst_admission.group_admissions_portal').id)
        except Exception:
            pass
        if not user:
            vals = {
                'name': partner.name,
                'login': login,
                'password': password,
                'partner_id': partner.id,
            }
            if group_ids:
                vals['groups_id'] = [(6, 0, group_ids)]
            user = Users.create(vals)
        else:
            write_vals = {'password': password, 'partner_id': partner.id}
            if group_ids:
                write_vals['groups_id'] = [(6, 0, group_ids)]
            user.write(write_vals)

        try:
            request.session.authenticate(request.session.db, login, password)
        except Exception:
            # Authentication failure should not block flow; user can still continue via session flags
            pass

        return {'ok': True, 'message': 'Verified'}

    @http.route('/admissions/profile', type='http', auth='user', website=True, csrf=True, methods=['GET', 'POST'])
    def admissions_profile(self, **kwargs):
        env = request.env
        cand_id = request.session.get('admissions_candidate_id')
        if not cand_id:
            # try to locate candidate by logged-in partner
            partner = env.user.partner_id
            cand = env['admissions.candidate'].sudo().search([('partner_id', '=', partner.id)], limit=1)
            if cand:
                request.session['admissions_candidate_id'] = cand.id
            else:
                return request.redirect('/admissions/auth')
        cand = env['admissions.candidate'].sudo().browse(int(request.session.get('admissions_candidate_id')))
        if request.httprequest.method == 'POST':
            vals = {
                'first_ar': normalize_arabic(kwargs.get('first_ar')),
                'second_ar': normalize_arabic(kwargs.get('second_ar')),
                'third_ar': normalize_arabic(kwargs.get('third_ar')),
                'fourth_ar': normalize_arabic(kwargs.get('fourth_ar')),
            }
            cand.write(vals)
            return request.redirect('/admissions/profile')
        return request.render('acmst_admission.profile', {'cand': cand})

    @http.route('/admissions/report', type='http', auth='user', website=True)
    def admissions_report(self, **kwargs):
        env = request.env
        cand_id = request.session.get('admissions_candidate_id')
        if not cand_id:
            partner = env.user.partner_id
            cand = env['admissions.candidate'].sudo().search([('partner_id', '=', partner.id)], limit=1)
            if not cand:
                return request.redirect('/admissions/auth')
        cand = env['admissions.candidate'].sudo().browse(int(request.session.get('admissions_candidate_id')))
        return request.env.ref('acmst_admission.report_acmst_admissions_form').report_action(cand)

    @http.route('/admissions/report/embassy', type='http', auth='user', website=True)
    def admissions_report_embassy(self, **kwargs):
        env = request.env
        cand_id = request.session.get('admissions_candidate_id')
        if not cand_id:
            partner = env.user.partner_id
            cand = env['admissions.candidate'].sudo().search([('partner_id', '=', partner.id)], limit=1)
            if not cand:
                return request.redirect('/admissions/auth')
        cand = env['admissions.candidate'].sudo().browse(int(request.session.get('admissions_candidate_id')))
        return request.env.ref('acmst_admission.report_acmst_embassy_style').report_action(cand)

    @http.route('/admissions/otp/send', type='json', auth='public', csrf=True)
    def admissions_otp_send(self, phone=None, recaptcha_token=None, **kwargs):
        env = request.env
        ip = request.httprequest.remote_addr or '0.0.0.0'
        # Optional reCAPTCHA verification
        if not self._verify_recaptcha(recaptcha_token, ip):
            return {'ok': False, 'message': 'reCAPTCHA validation failed.'}
        settings = env['admissions.settings'].sudo().search([], limit=1) or env['admissions.settings']
        window = settings.rate_limit_window_minutes or 15
        if env['admissions.rate.limit'].sudo().is_limited('otp_send', ip, window, settings.rate_limit_sends_per_window or 3):
            return {'ok': False, 'message': 'Too many OTP requests. Please wait.'}
        env['admissions.rate.limit'].sudo().hit('otp_send', ip)

        # Normalize and persist phone in session
        phone = phone or request.session.get('admissions_phone')
        if not phone:
            return {'ok': False, 'message': 'No phone number.'}
        try:
            from ..models.utils import try_format_e164
            e164 = try_format_e164(phone)
            if not e164:
                return {'ok': False, 'message': 'Invalid phone number.'}
            phone = e164
        except Exception:
            pass
        request.session['admissions_phone'] = phone

        # Blacklist check
        raw_blacklist = request.env['ir.config_parameter'].sudo().get_param('acmst_admission.blacklist_phones') or ''
        import re
        blacklist = [p.strip() for p in re.split(r'[\s,;]+', raw_blacklist) if p.strip()]
        if phone in blacklist:
            return {'ok': False, 'message': 'Phone number is not allowed.'}

        # Generate and send OTP via WhatsApp (Brevo)
        import secrets, hashlib
        length = settings.otp_length or 6
        code = ''.join(secrets.choice('0123456789') for _ in range(length))
        salt = secrets.token_hex(8)
        code_hash = hashlib.sha256((code + salt).encode()).hexdigest()
        from datetime import timedelta
        expire_at = fields.Datetime.now() + timedelta(minutes=int(settings.otp_ttl_minutes or 10))
        env['admissions.otp'].sudo().create({
            'phone': phone,
            'purpose': 'login',
            'code_hash': code_hash,
            'salt': salt,
            'expire_at': expire_at,
            'status': 'sent',
            'ip': ip,
            'user_agent': request.httprequest.headers.get('User-Agent'),
        })
        # Candidate name for templating
        name_param = ''
        cand_id = request.session.get('admissions_candidate_id')
        if cand_id:
            cand = env['admissions.candidate'].sudo().browse(int(cand_id))
            if cand.exists():
                name_param = ' '.join([p for p in [cand.first_ar, cand.second_ar, cand.third_ar, cand.fourth_ar] if p])
        try:
            self._send_brevo_whatsapp(phone, code, name_param)
            return {'ok': True, 'message': 'OTP sent via WhatsApp'}
        except Exception as e:
            request.env['ir.logging'].sudo().create({
                'name': 'Brevo OTP Send', 'type': 'server', 'level': 'WARNING',
                'message': f'Brevo send failed: {e}', 'path': __name__, 'func': '_send_brevo_whatsapp', 'line': 0,
            })
            return {'ok': False, 'message': 'Provider not configured. Contact support.'}

    # Provider hook
    def _send_brevo_whatsapp(self, phone_e164: str, otp_code: str, name_param: str = ''):
        # Realistic Brevo WhatsApp template send
        # Configure these system params: acmst_admission.brevo_api_key, acmst_admission.brevo_sender, acmst_admission.brevo_template, acmst_admission.brevo_language
        ICP = request.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('acmst_admission.brevo_api_key')
        sender = ICP.get_param('acmst_admission.brevo_sender')  # WhatsApp sender number (international format)
        template = ICP.get_param('acmst_admission.brevo_template') or 'otp'
        language = ICP.get_param('acmst_admission.brevo_language') or 'ar'
        if not (api_key and sender):
            raise Exception('Brevo API not configured')
        import requests
        headers = {
            'accept': 'application/json',
            'api-key': api_key,
            'content-type': 'application/json',
        }
        payload = {
            'senderNumber': sender,
            'contactNumber': phone_e164,
            'templateName': template,
            # Match your template variables: {{name}} and {{otp}}
            'params': {'name': name_param or '', 'otp': otp_code},
            'language': language,
        }
        url = 'https://api.brevo.com/v3/whatsapp/sendTemplate'
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code >= 300:
            raise Exception(f'Brevo error {resp.status_code}: {resp.text}')

    def _verify_recaptcha(self, token: str, ip: str) -> bool:
        ICP = request.env['ir.config_parameter'].sudo()
        secret = ICP.get_param('acmst_admission.recaptcha_secret_key')
        if not secret:
            return True  # not configured; skip enforcement
        if not token:
            return False
        import requests
        data = {'secret': secret, 'response': token, 'remoteip': ip}
        try:
            r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data, timeout=5)
            ok = r.json().get('success') is True
            return ok
        except Exception:
            return False

    @http.route('/admissions/brevo/webhook', type='http', auth='public', csrf=False, methods=['POST'])
    def brevo_webhook(self, **kwargs):
        # Basic webhook endpoint for Brevo callbacks; validates optional secret token
        ICP = request.env['ir.config_parameter'].sudo()
        secret = ICP.get_param('acmst_admission.brevo_webhook_secret')
        token = request.httprequest.headers.get('X-Webhook-Token') or request.params.get('token')
        if secret and token != secret:
            return request.make_response('Forbidden', [('Content-Type', 'text/plain')], 403)
        payload = {}
        try:
            payload = request.get_json_data(force=True, silent=True) or {}
        except Exception:
            payload = {}
        phone = payload.get('to') or payload.get('phone') or ''
        status = payload.get('status') or payload.get('event') or ''
        event = payload.get('event') or payload.get('type') or 'delivery'
        request.env['admissions.otp.log'].sudo().create({
            'provider': 'brevo',
            'phone': phone,
            'status': status,
            'event': event,
            'payload': payload,
            'message': payload.get('message') or '',
        })
        return request.make_response('OK', [('Content-Type', 'text/plain')], 200)
