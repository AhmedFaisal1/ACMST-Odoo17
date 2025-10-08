# models/acceptance_guardian.py
from odoo import models, fields, api


class AcceptanceGuardian(models.Model):
    _name = "acmst.acceptance.guardian"
    _description = "Acceptance Guardian (Wizard Line)"

    # Not required: the ORM injects this FK when creating from the one2many.
    wizard_id = fields.Many2one(
        "acmst.acceptance.form",
        ondelete="cascade",
    )

    name = fields.Char(string="اسم ولي الأمر / Guardian Name")
    phone = fields.Char(string="هاتف ولي الأمر / Guardian Phone")
    relation = fields.Char(string="صلة القرابة / Relationship")
    address = fields.Char(string="عنوان ولي الأمر / Address")
    is_default = fields.Boolean(string="Default")

    @api.onchange("is_default")
    def _onchange_is_default(self):
        # Do nothing until this line is attached to a wizard
        if not self.wizard_id:
            return
        if self.is_default:
            for g in self.wizard_id.guardian_ids:
                if g.id and g.id != self.id:
                    g.is_default = False
            self.wizard_id.default_guardian_id = self.id
        else:
            if (
                self.wizard_id.default_guardian_id
                and self.wizard_id.default_guardian_id.id == self.id
            ):
                self.wizard_id.default_guardian_id = False

    @api.model
    def default_get(self, fields_list):
        """Ensure inline creation gets wizard_id from context when available.

        Do not fall back to active_id because the wizard is usually opened
        from another model (e.g., acmst.student), which would set a wrong FK.
        """
        res = super().default_get(fields_list)
        wiz = self.env.context.get("default_wizard_id") or self.env.context.get(
            "wizard_id"
        )
        if wiz:
            res["wizard_id"] = wiz
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Safety net: add wizard_id from context for inline rows.

        Avoid using active_id (it could be a student). Only accept explicit
        default_wizard_id/wizard_id from context.
        """
        wiz = self.env.context.get("default_wizard_id") or self.env.context.get(
            "wizard_id"
        )
        if wiz:
            for vals in vals_list:
                if not vals.get("wizard_id"):
                    vals["wizard_id"] = wiz
        return super().create(vals_list)

    def action_set_default(self):
        self.ensure_one()
        # Ensure exclusivity at the UI level
        if self.wizard_id:
            for g in self.wizard_id.guardian_ids:
                if g.id != self.id and g.is_default:
                    g.is_default = False
            self.wizard_id.default_guardian_id = self.id
        self.is_default = True
        return {"type": "ir.actions.act_window_close"}

    # (Removed duplicate create() that relied on active_id)
