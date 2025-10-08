from odoo import api, fields, models


class AdmissionsCandidate(models.Model):
    _name = 'admissions.candidate'
    _description = 'Admissions Candidate'

    # Arabic name parts
    first_ar = fields.Char(string='First (AR)')
    second_ar = fields.Char(string='Second (AR)')
    third_ar = fields.Char(string='Third (AR)')
    fourth_ar = fields.Char(string='Fourth (AR)')

    # English name parts
    first_en = fields.Char(string='First (EN)')
    second_en = fields.Char(string='Second (EN)')
    third_en = fields.Char(string='Third (EN)')
    fourth_en = fields.Char(string='Fourth (EN)')

    program_id = fields.Many2one('admissions.program', string='Program', index=True)
    academic_year_id = fields.Many2one('admissions.year', string='Academic Year', index=True)

    base_university_id = fields.Char(required=True, index=True)
    combined_university_id = fields.Char(string='University ID', compute='_compute_combined_university_id', store=True, index=True)

    dob = fields.Date(string='Date of Birth')
    national_id = fields.Char()
    is_active = fields.Boolean(default=True, index=True)
    extra_json = fields.Json()
    phone = fields.Char(string='Phone (E.164)', index=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    import_job_id = fields.Many2one('admissions.import.job', string='Import Job', index=True)

    @api.depends('base_university_id', 'academic_year_id', 'academic_year_id.code')
    def _compute_combined_university_id(self):
        for rec in self:
            base = rec.base_university_id or ''
            code = rec.academic_year_id.code or '' if rec.academic_year_id else ''
            tail4 = ''
            if code:
                import re as _re
                years = _re.findall(r"\d{4}", code)
                if years:
                    tail4 = max(years)
            rec.combined_university_id = f"{base}{tail4}"
