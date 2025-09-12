from odoo import api, fields, models, _

class AcmstStudent(models.Model):
    _name = "acmst.student"
    # ... your current fields ...
    partner_id = fields.Many2one("res.partner", string="Partner", ondelete="set null")

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        if not rec.partner_id:
            tag = self.env.ref("acmst_finance.partner_category_student", raise_if_not_found=False)
            partner_vals = {
                "name": rec.full_name or rec.n1 or _("Student"),
                "company_type": "person",
            }
            if tag:
                partner_vals["category_id"] = [(4, tag.id)]
            partner = self.env["res.partner"].create(partner_vals)
            rec.partner_id = partner.id
        return rec
