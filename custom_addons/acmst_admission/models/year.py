from odoo import models, fields, api


class AdmissionsYear(models.Model):
    _name = 'admissions.year'
    _description = 'Admissions Academic Year'
    _rec_name = 'name'

    code = fields.Char(required=True, index=True)
    label = fields.Char()
    name = fields.Char(string='Display Name', compute='_compute_name', store=True)
    date_start = fields.Date()
    date_end = fields.Date()
    is_current = fields.Boolean(default=False)

    _sql_constraints = [
        ('year_code_unique', 'unique(code)', 'Academic year code must be unique.'),
    ]

    @api.depends('label', 'code')
    def _compute_name(self):
        for rec in self:
            rec.name = rec.label or rec.code or ''
