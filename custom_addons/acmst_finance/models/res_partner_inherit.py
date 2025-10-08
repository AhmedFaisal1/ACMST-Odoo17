# in models/res_partner_inherit.py (same file where is_student is defined)
from odoo import fields, models

class ResPartner(models.Model):
    _inherit = "res.partner"
    is_student = fields.Boolean(string="Is Student", index=True)
    university_id = fields.Char(string="University ID")
    student_year  = fields.Char(string="Year")

    def name_get(self):
        res = []
        Student = self.env["acmst.student"]
        for p in self:
            name = super(ResPartner, p).name_get()[0][1] if False else p.name
            if getattr(p, "is_student", False):
                stu = Student.search([("partner_id", "=", p.id)], limit=1)
                if stu and stu.frmno:
                    name = f"{name} [{stu.frmno}]"
            res.append((p.id, name))
        return res
