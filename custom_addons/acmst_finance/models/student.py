# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AcmstStudent(models.Model):
    _name = "acmst.student"
    _description = "ACMST Student"
    _order = "create_date desc"
    _rec_name = "full_name"  # what Many2one shows by default

    # ------------ Fields ------------
    frmno = fields.Char("University ID", index=True)
    fac = fields.Char("FAC")
    univ_id = fields.Char("UNIV_ID")
    n1 = fields.Char("N1 (First Name)")
    n2 = fields.Char("N2 (Father Name)")
    n3 = fields.Char("N3 (Grandfather Name)")
    n4 = fields.Char("N4 (Family Name)")
    full_name = fields.Char("Full Name", compute="_compute_full_name", store=True)
    scname = fields.Char("SCNAME (School)")
    gobno = fields.Char("GOBNO")
    facname = fields.Char("FACNAME (Faculty)")
    gobols = fields.Char("GOBOLS (System)")
    year = fields.Char("YEAR")
    national_id = fields.Char("NATIONAL_ID")
    sex = fields.Selection(
        [('m', 'Male'), ('f', 'Female')],
        string='Sex'
    )
    university = fields.Char("UNIVERSITY")
    partner_id = fields.Many2one(
        'res.partner', string="Related Contact", ondelete='set null'
    )

    _sql_constraints = [
        ('frmno_unique', 'unique(frmno)', 'FRMNO must be unique.')
    ]

    # ------------ Compute ------------
    @api.depends('n1', 'n2', 'n3', 'n4')
    def _compute_full_name(self):
        for rec in self:
            parts = [rec.n1, rec.n2, rec.n3, rec.n4]
            rec.full_name = " ".join([p for p in parts if p])

    # ------------ UI helpers ------------
    def name_get(self):
        """Show 'Full Name - FRMNO' (fallbacks if missing)."""
        res = []
        for rec in self:
            base = rec.full_name or rec.n1 or _("Student")
            label = f"{base} - {rec.frmno}" if rec.frmno else base
            res.append((rec.id, label))
        return res

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """
        Search by full name OR FRMNO OR NATIONAL_ID.
        """
        args = args or []
        if name:
            domain = ['|', '|',
                      ('full_name', operator, name),
                      ('frmno', operator, name),
                      ('national_id', operator, name)]
        else:
            domain = []
        recs = self.search(args + domain, limit=limit)
        return recs.name_get()

    # ------------ Actions ------------
    def action_create_partner(self):
        for rec in self:
            if not rec.partner_id:
                partner = self.env['res.partner'].create({
                    'name': rec.full_name or rec.n1 or _('Student'),
                    'company_type': 'person',
                })
                rec.partner_id = partner.id
        return True
