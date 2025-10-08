# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

# --- Selections ---
SEMESTERS = [(str(i), str(i)) for i in range(1, 11)]
LEVELS = [(str(i), str(i)) for i in range(1, 6)]
PROGRAMS = [
    ("medicine", "Medicine"),
    ("dentistry", "Dentistry"),
    ("civil", "Civil Engineering"),
    ("pharmacy", "Pharmacy"),
    ("nursing", "Nursing"),
    ("lab", "Medical Laboratory Science"),
    ("it", "Information Technology"),
    ("admin", "Administrative Sciences"),
]
PAYMENT_TYPES = [
    ("cash", "Cash"),
    ("bank", "Bank Transfer"),
    ("card", "Card / POS"),
    ("mobile", "Mobile Wallet"),
    ("cheque", "Cheque"),
]


class AcmstEnrollment(models.Model):
    _name = "acmst.enrollment"
    _description = "Student Payment"
    _order = "create_date desc"
    _rec_name = "display_name"

    # --- Student & linked info ---
    student_id = fields.Many2one(
        "acmst.student", string="Student", required=True, ondelete="restrict", index=True
    )
    student_name = fields.Char(
        string="Student Name",
        related="student_id.full_name",
        store=True,
        readonly=True,
        index=True,
    )
    frmno = fields.Char(
        string="University ID",
        related="student_id.frmno",
        store=True,
        readonly=True,
        index=True,
    )

    year = fields.Char(string="Year")
    level = fields.Selection(LEVELS, string="Level")
    semester = fields.Selection(SEMESTERS, string="Semester")
    program = fields.Selection(PROGRAMS, string="Program")

    date = fields.Date(string="Date", default=fields.Date.context_today)

    # Payment info
    payment_type = fields.Selection(
        PAYMENT_TYPES, string="Payment Type", required=True, default="cash"
    )
    transaction_number = fields.Char(string="Transaction Number")
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id.id,
    )
    payment = fields.Monetary(string="Payment", currency_field="currency_id")

    # Scans (at least one must be provided)
    passport_scan = fields.Binary(string="Passport (scan)")
    passport_filename = fields.Char()
    national_id_scan = fields.Binary(string="National ID (scan)")
    national_id_filename = fields.Char()

    # Invoice link / number
    invoice_move_id = fields.Many2one(
        "account.move", string="Invoice", readonly=True, ondelete="set null"
    )
    internal_number = fields.Char(
        string="Invoice Number",
        related="invoice_move_id.name",
        store=True,
        readonly=True,
    )

    state = fields.Selection(
        [("draft", "Draft"), ("invoiced", "Invoiced")], default="draft"
    )

    # Display name
    display_name = fields.Char(compute="_compute_display_name", store=True)

    # ---------- computes ----------
    @api.depends("internal_number", "student_name")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.internal_number or rec.student_name or _("Draft")

    # ---------- onchange ----------
    @api.onchange("student_id")
    def _onchange_student_id(self):
        if self.student_id:
            self.year = self.student_id.year or ""

    # ---------- helpers ----------
    def _ensure_partner(self):
        self.ensure_one()
        stu = self.student_id
        if not stu:
            raise UserError(_("Select a student first."))
        if not stu.partner_id:
            partner = self.env["res.partner"].create(
                {"name": stu.full_name or stu.n1 or _("Student"), "company_type": "person"}
            )
            stu.partner_id = partner.id
        return stu.partner_id

    def _fallback_income_account(self):
        account = self.env["account.account"].search(
            [("account_type", "=", "income")], limit=1
        )
        if not account:
            raise UserError(
                _(
                    "No income account found. Please create an Income account "
                    "in Accounting > Configuration > Chart of Accounts."
                )
            )
        return account

    def _build_transaction_reference(self):
        """
        Compose the value shown on the invoice header as 'Transaction Number':
        - Use manual transaction_number if provided.
        - Otherwise build '<FRMNO> / <Year>' using student data.
        """
        self.ensure_one()
        manual = (self.transaction_number or "").strip()
        if manual:
            return manual
        frmno = self.frmno or (self.student_id and self.student_id.frmno)
        year = self.year or (self.student_id and self.student_id.year)
        parts = [p for p in [frmno, year] if p]
        return " / ".join(parts) if parts else False

    # ---------- constraints ----------
    @api.constrains("passport_scan", "national_id_scan")
    def _check_one_id_doc(self):
        for rec in self:
            if not rec.passport_scan and not rec.national_id_scan:
                raise UserError(_("Please upload at least Passport or National ID."))

    @api.constrains("payment_type", "transaction_number", "frmno", "year")
    def _check_payment_type_reference(self):
        for rec in self:
            # For non-cash: require either a manual number OR enough data to auto-build
            if rec.payment_type != "cash" and not rec._build_transaction_reference():
                raise UserError(
                    _(
                        "Transaction Number is required for non-cash payments "
                        "— enter it, or make sure University ID and Year are set so "
                        "we can compose it automatically."
                    )
                )

    # ---------- actions ----------
    def action_create_invoice(self):
        """
        Create & post a Student Invoice from the payment record.
        - University ID  -> invoice_origin
        - Transaction No -> payment_reference (manual or FRMNO/Year)
        - Payment Type   -> acmst_payment_type (custom field on account.move)
        - One line: Student Name, qty=1, price=payment
        """
        for rec in self:
            if rec.invoice_move_id:
                raise UserError(_("An invoice already exists for this record."))
            if not rec.payment or rec.payment <= 0:
                raise UserError(_("Payment amount must be greater than zero."))
            if not (rec.passport_scan or rec.national_id_scan):
                raise UserError(_("Please upload Passport or National ID (at least one)."))

            partner = rec._ensure_partner()
            income_account = rec._fallback_income_account()
            sale_journal = self.env["account.journal"].search([("type", "=", "sale")], limit=1)

            payment_ref = rec._build_transaction_reference()

            move_vals = {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "invoice_date": rec.date or fields.Date.context_today(rec),
                "currency_id": rec.currency_id.id,
                "invoice_origin": rec.frmno or rec.student_name or "",  # University ID
                **({"journal_id": sale_journal.id} if sale_journal else {}),
                "invoice_line_ids": [(0, 0, {
                    "name": rec.student_name or _("Tuition"),
                    "quantity": 1.0,
                    "price_unit": rec.payment or 0.0,
                    "account_id": income_account.id,
                })],
            }

            # 👇 Add this block (or fold these two keys into move_vals above)
            move_vals.update({
                "ref": rec.transaction_number or False,  # Transaction Number
                "acmst_payment_type": rec.payment_type or False,  # shows in header
            })

            move = self.env["account.move"].create(move_vals)
            move.action_post()

            # Link back & persist composed transaction number for visibility in the form/list
            if not rec.transaction_number and payment_ref:
                rec.transaction_number = payment_ref
            rec.invoice_move_id = move.id
            rec.state = "invoiced"

        return True

    def action_open_invoice(self):
        self.ensure_one()
        if not self.invoice_move_id:
            raise UserError(_("No invoice to open."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.invoice_move_id.id,
            "view_mode": "form",
            "target": "current",
        }
