from odoo import models, fields, api


class AdmissionsProgram(models.Model):
    _name = 'admissions.program'
    _description = 'Admissions Program'
    _rec_name = 'name'

    code = fields.Char(required=True, index=True)
    name_ar = fields.Char(string='Name (AR)')
    name_en = fields.Char(string='Name (EN)')
    name = fields.Char(string='Display Name', compute='_compute_name', store=True)

    _sql_constraints = [
        ('program_code_unique', 'unique(code)', 'Program code must be unique.'),
    ]

    @api.depends('name_ar', 'name_en', 'code')
    def _compute_name(self):
        for rec in self:
            rec.name = rec.name_ar or rec.name_en or rec.code or ''
