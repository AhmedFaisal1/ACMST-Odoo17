# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AcmstStudent(models.Model):
    _name = "acmst.student"
    _description = "ACMST Student"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"
    _rec_name = "full_name"

    # ------------ Fields ------------
    frmno = fields.Char("University ID", index=True, tracking=True)
    fac = fields.Char("FAC")
    univ_id = fields.Char("UNIV_ID")

    n1 = fields.Char("N1 (First Name)", tracking=True)
    n2 = fields.Char("N2 (Father Name)")
    n3 = fields.Char("N3 (Grandfather Name)")
    n4 = fields.Char("N4 (Family Name)")
    full_name = fields.Char("Full Name", compute="_compute_full_name", store=True)

    scname = fields.Char("SCNAME (School)")
    gobno = fields.Char("GOBNO")
    facname = fields.Char("FACNAME (Faculty)")
    gobols = fields.Char("GOBOLS (System)")

    year = fields.Char("YEAR", tracking=True)
    level = fields.Char("LEVEL", tracking=True)
    academic_year = fields.Char("ACADEMIC_YEAR", tracking=True)
    national_id = fields.Char("NATIONAL_ID")
    sex = fields.Selection([("m", "Male"), ("f", "Female")], string="Sex")
    university = fields.Char("UNIVERSITY")

    partner_id = fields.Many2one(
        "res.partner", string="Related Contact", ondelete="set null", tracking=True
    )

    # Smart button
    invoice_count = fields.Integer(string="Invoices", compute="_compute_invoice_count")

    # One2many helper to show all invoices on the form
    invoice_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="student_id",
        string="Invoices",
        help="All customer invoices linked to this student.",
    )

    receipt_ids = fields.One2many(
        comodel_name="account.payment",
        inverse_name="student_id",
        string="Receipts",
        help="All payment receipts linked to this student.",
    )

    _sql_constraints = [("frmno_unique", "unique(frmno)", "FRMNO must be unique.")]

    # ------------ Compute ------------
    @api.depends("n1", "n2", "n3", "n4")
    def _compute_full_name(self):
        for rec in self:
            parts = [rec.n1, rec.n2, rec.n3, rec.n4]
            rec.full_name = " ".join([p for p in parts if p])

    def name_get(self):
        res = []
        for rec in self:
            label = rec.full_name or rec.display_name or ""
            if rec.frmno:
                label = f"{label} ({rec.frmno})"
            res.append((rec.id, label))
        return res

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = args or []
        domain = []
        if name:
            domain = ["|", ("full_name", operator, name), ("frmno", operator, name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()

    # ------------ Smart button compute ------------
    @api.depends("partner_id")  # any lightweight dep, not strictly required
    def _compute_invoice_count(self):
        Move = self.env["account.move"].sudo()
        for rec in self:
            rec.invoice_count = Move.search_count(
                [
                    ("move_type", "=", "out_invoice"),
                    ("student_id", "=", rec.id),
                ]
            )

    # ------------ Partner helpers ------------
    def _ensure_partner_vals(self):
        """Build safe vals for res.partner (only set fields that really exist)."""
        self.ensure_one()
        vals = {
            "name": self.full_name or self.n1 or _("Student"),
            "company_type": "person",
            "customer_rank": 1,
        }
        Partner = self.env["res.partner"]
        if "is_student" in Partner._fields:
            vals["is_student"] = True
        if "university_id" in Partner._fields:
            vals["university_id"] = self.frmno or False
        if "student_year" in Partner._fields:
            vals["student_year"] = self.year or False
        return vals

    def action_create_partner(self):
        for rec in self:
            vals = rec._ensure_partner_vals()
            if rec.partner_id:
                rec.partner_id.write(vals)
            else:
                rec.partner_id = self.env["res.partner"].create(vals).id
        return True

    # ------------ Invoicing actions (buttons) ------------
    def action_view_invoices(self):
        self.ensure_one()
        action = self.env.ref("account.action_move_out_invoice_type").read()[0]
        action.update(
            {
                "domain": [
                    ("move_type", "=", "out_invoice"),
                    ("student_id", "=", self.id),
                ],
                "context": {
                    "default_move_type": "out_invoice",
                    "student_invoice_ui": 1,
                    "default_student_id": self.id,
                    "default_partner_id": self.partner_id.id,
                },
            }
        )
        return action

    def _get_sale_journal(self):
        return self.env["account.journal"].search(
            [
                ("type", "=", "sale"),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
            order="sequence,id",
        )

    def action_generate_invoice(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(
                _("Please set a Related Contact before generating an invoice.")
            )
        journal = self._get_sale_journal()
        if not journal:
            raise UserError(_("Please create at least one Sales Journal."))
        return {
            "type": "ir.actions.act_window",
            "name": _("New Student Invoice"),
            "res_model": "account.move",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_move_type": "out_invoice",
                "student_invoice_ui": 1,
                "default_student_id": self.id,
                "default_partner_id": self.partner_id.id,
                "default_journal_id": journal.id,
                "default_invoice_date": fields.Date.today(),
            },
        }

    def action_pay_latest_invoice(self):
        self.ensure_one()
        inv = self.env["account.move"].search(
            [
                ("move_type", "=", "out_invoice"),
                ("student_id", "=", self.id),
            ],
            order="id desc",
            limit=1,
        )
        if not inv:
            raise UserError(_("No invoice found for this student. Generate one first."))
        if inv.state != "posted":
            raise UserError(_("The latest invoice is not posted. Confirm it first."))
        return inv.action_register_payment()

    # ------------ CRUD / sync + chatter ------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec.action_create_partner()
            rec.message_post(
                body=_("Student record created by %s.") % rec.env.user.display_name
            )
        return records

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.partner_id:
                rec.partner_id.write(rec._ensure_partner_vals())
        return res

    # ------------ Portal (optional) ------------
    def action_grant_portal_access(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Please set a Related Contact first."))
        Wizard = self.env.get("portal.wizard")
        WizardUser = self.env.get("portal.wizard.user")
        if not Wizard or not WizardUser:
            raise UserError(_("Install the Portal app to grant portal access."))
        wizard = Wizard.create({})
        WizardUser.create(
            {
                "wizard_id": wizard.id,
                "partner_id": self.partner_id.id,
                "email": self.partner_id.email or "",
                "in_portal": True,
            }
        )
        wizard.action_apply()
        self.message_post(
            body=_("Portal access granted to %s.") % self.partner_id.display_name
        )
        return True
