# -*- coding: utf-8 -*-
"""
acmst_finance/models/account_move_inherit.py

Custom fields + behavior for Student Invoices without touching
standard Customer/Vendor invoices (Odoo 17).
"""
from odoo import api, fields, models
from urllib.parse import quote_plus
from odoo.exceptions import UserError

# --- Choices -----------------------------------------------------------------
PAYMENT_TYPES = [
    ("cash", "Cash"),
    ("bank", "Bank Transfer"),
    ("card", "Card / POS"),
    ("mobile", "Mobile Wallet"),
    ("cheque", "Cheque"),
]

LEVELS = [(str(i), str(i)) for i in range(1, 6)]  # 1–5
SEMESTERS = [(str(i), str(i)) for i in range(1, 11)]  # 1–10

PROGRAMS = [
    ("medicine", "Medicine"),
    ("dentistry", "Dentistry"),
    ("civil_engineering", "Civil Engineering"),
    ("pharmacy", "Pharmacy"),
    ("nursing", "Nursing"),
    ("medical_lab_science", "Medical Laboratory Science"),
    ("it", "Information Technology"),
    ("administrative_sciences", "Administrative Sciences"),
]


class AccountMove(models.Model):
    _inherit = "account.move"

    # --- Student links & info -------------------------------------------------
    student_id = fields.Many2one(
        "acmst.student",
        string="Student (Record)",
        help="Select the student to invoice; partner is auto-synced.",
    )
    university_id = fields.Char(
        string="University ID",
        related="student_id.frmno",
        store=True,
        readonly=True,
    )
    student_year = fields.Char(
        string="YEAR",
        related="student_id.year",
        store=True,
        readonly=True,
    )
    student_level = fields.Selection(LEVELS, string="Student Level")
    student_semester = fields.Selection(SEMESTERS, string="Student Semester")
    student_program = fields.Selection(PROGRAMS, string="Student Program")

    last_receipt_download_at = fields.Datetime(
        string="Receipt Downloaded At",
        readonly=True,
    )
    student_academic_year = fields.Char(
        string="Academic Year",
        related="student_id.academic_year",
        store=True,
        readonly=True,
        help="Copied from the student's Academic Year.",
    )

    # --- Right side fields ----------------------------------------------------
    transaction_number = fields.Char(string="Student Transaction No.")
    acmst_payment_type = fields.Selection(PAYMENT_TYPES, string="Student Payment Type")
    student_payment_amount = fields.Monetary(
        string="Student Payment Amount",
        currency_field="currency_id",
    )
    # Bank GL account to print on the documents (does not impact posting logic)
    acmst_gl_bank_account_id = fields.Many2one(
        "account.account",
        string="Printed Bank Account",
        help="Select the GL account to display as 'حساب البنك باسم' on the Student Invoice.\n"
        "This does not change revenue posting; it is only printed on the document.",
        ondelete="set null",
    )

    passport_scan = fields.Binary(string="Passport Scan")
    national_id_scan = fields.Binary(string="National ID Scan")

    # QR link + ready-to-use external image URL (Google Charts)
    acmst_qr_value = fields.Char(
        string="QR Value", compute="_compute_acmst_qr_value", store=False
    )
    acmst_qr_url = fields.Char(
        string="QR Image URL", compute="_compute_acmst_qr_value", store=False
    )

    # Display-only: bank account label to show on documents (from invoice line account)
    acmst_bank_account_label = fields.Char(
        string="ACMST Bank Account Label",
        compute="_compute_acmst_bank_account_label",
        store=False,
    )

    # --- Sync partner ↔ student ----------------------------------------------
    @api.onchange("student_id")
    def _onchange_student_id(self):
        """When a student is chosen, set the partner to the student's contact."""
        for move in self:
            if move.student_id and move.student_id.partner_id:
                move.partner_id = move.student_id.partner_id

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        """When a partner is chosen, fetch the linked student if any."""
        Student = self.env["acmst.student"]
        for move in self:
            if move.partner_id:
                stu = Student.search([("partner_id", "=", move.partner_id.id)], limit=1)
                move.student_id = stu or False

    # --- Defaults / View routing for Student Invoices ------------------------
    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        if self.env.context.get("student_invoice_ui"):
            vals.setdefault("company_id", self.env.company.id)
            vals.setdefault("move_type", "out_invoice")
            vals.setdefault("currency_id", self.env.company.currency_id.id)
            sale_journal = (
                self.env["account.journal"]
                .sudo()
                .search(
                    [("type", "=", "sale"), ("company_id", "=", self.env.company.id)],
                    order="sequence,id",
                    limit=1,
                )
            )
            if sale_journal:
                vals.setdefault("journal_id", sale_journal.id)

            # Pick a default bank account to print (first bank journal default account)
            bank_journal = (
                self.env["account.journal"]
                .sudo()
                .search(
                    [("type", "=", "bank"), ("company_id", "=", self.env.company.id)],
                    order="sequence,id",
                    limit=1,
                )
            )
            if bank_journal and bank_journal.bank_account_id:
                vals.setdefault("partner_bank_id", bank_journal.bank_account_id.id)
        return vals

    @api.model
    def get_formview_id(self, access_uid=None):
        if self.env.context.get("student_invoice_ui"):
            return self.env.ref("acmst_finance.view_move_form_student_custom").id
        return super().get_formview_id(access_uid=access_uid)

    # --- Helpers --------------------------------------------------------------
    def _get_student_income_account(self):
        """Prefer the journal's default if it's an income account; else any income account."""
        self.ensure_one()
        acc = self.journal_id.default_account_id
        if acc and acc.account_type == "income":
            return acc
        return self.env["account.account"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("account_type", "=", "income"),  # Odoo 17 field
                ("deprecated", "=", False),
            ],
            limit=1,
        )

    # --- Auto-create/update a single revenue line from 'student_payment_amount'
    def _ensure_student_single_line(self):
        """Only used in the Student UI.
        - Keeps section/note lines.
        - Ensures exactly one real revenue line that mirrors student_payment_amount.
        """
        for move in self:
            if move.move_type != "out_invoice":
                continue

            amount = move.student_payment_amount or 0.0
            # Separate real vs display lines
            real_lines = move.invoice_line_ids.filtered(lambda l: not l.display_type)

            commands = []

            # remove all existing real lines
            for rl in real_lines:
                commands.append((2, rl.id))

            if amount > 0:
                income = move._get_student_income_account()
                if not income:
                    raise UserError(
                        "No income account configured for this company/journal. "
                        "Please set a revenue account on the journal or create an income account."
                    )
                commands.append(
                    (
                        0,
                        0,
                        {
                            "name": "Student Payment",
                            "quantity": 1.0,
                            "price_unit": amount,
                            "account_id": income.id,  # safe if no product is used
                        },
                    )
                )

            if commands:
                move.write({"invoice_line_ids": commands})

    @api.onchange("student_payment_amount")
    def _onchange_student_payment_amount(self):
        if self.env.context.get("student_invoice_ui"):
            self._ensure_student_single_line()

    # --- Post safeguard -------------------------------------------------------
    def action_post(self):
        if self.env.context.get("student_invoice_ui"):
            self._ensure_student_single_line()
        return super().action_post()

    # --- Reporting (PDF / HTML) ----------------------------------------------
    def action_print_student_invoice_pdf(self):
        self.ensure_one()
        action = self.env.ref(
            "acmst_finance.report_student_invoice_action"
        ).report_action(self)
        # close dialog after download if triggered from wizard/modal
        action.update({"close_on_report_download": True})
        return action

    def action_preview_student_invoice_html(self):
        self.ensure_one()
        # Use a dedicated HTML report action to preview in-browser
        action = self.env.ref(
            "acmst_finance.report_student_invoice_action_html"
        ).read()[0]
        action.setdefault("context", {})
        ctx = dict(self.env.context, active_ids=[self.id])
        action["context"] = ctx
        return action

    # --- Presentation helpers -------------------------------------------------
    def _compute_acmst_qr_value(self):
        ICP = self.env["ir.config_parameter"].sudo()
        base_url = ICP.get_param("web.base.url") or ""
        for move in self:
            value = (
                f"{base_url}/report/pdf/acmst_finance.report_student_invoice/{move.id}"
                if move.id
                else ""
            )
            move.acmst_qr_value = value
            move.acmst_qr_url = (
                (
                    f"https://chart.googleapis.com/chart?chs=150x150&cht=qr&choe=UTF-8&chl={quote_plus(value)}"
                )
                if value
                else ""
            )

    @api.depends(
        "acmst_gl_bank_account_id",
        "acmst_gl_bank_account_id.code",
        "acmst_gl_bank_account_id.name",
    )
    def _compute_acmst_bank_account_label(self):
        for move in self:
            label = ""
            # Use the selected GL account for the bank account label
            if move.acmst_gl_bank_account_id:
                account = move.acmst_gl_bank_account_id
                code = (account.code or "").strip()
                name = (account.name or "").strip()

                # Format: "code - name"
                if code and name:
                    label = f"{code} - {name}"
                elif code:
                    label = code
                elif name:
                    label = name

            move.acmst_bank_account_label = label

    # --- Auto-link invoices created from Accounting to Student ---------------
    def _find_student_for_partner(self, partner_id):
        if not partner_id:
            return False
        return (
            self.env["acmst.student"]
            .sudo()
            .search([("partner_id", "=", partner_id)], limit=1)
        )

    def _is_customer_move(self, move_type):
        return move_type in ("out_invoice", "out_refund", "out_receipt")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            move_type = vals.get("move_type") or "entry"
            # If user picked a student but no partner, sync the partner
            if vals.get("student_id") and not vals.get("partner_id"):
                stu = self.env["acmst.student"].browse(vals["student_id"])
                if stu and stu.partner_id:
                    vals["partner_id"] = stu.partner_id.id
            # If created from the Accounting app (no student set), infer from partner
            if (
                self._is_customer_move(move_type)
                and not vals.get("student_id")
                and vals.get("partner_id")
            ):
                stu = self._find_student_for_partner(vals["partner_id"])
                if stu:
                    vals["student_id"] = stu.id
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get("skip_student_sync"):
            return res
        for move in self:
            updates = {}
            # If student changed, keep partner in sync
            if "student_id" in vals:
                if (
                    move.student_id
                    and move.student_id.partner_id
                    and move.partner_id != move.student_id.partner_id
                ):
                    updates["partner_id"] = move.student_id.partner_id.id
            # If partner changed (or set) and student not explicitly set, infer student
            if (
                "partner_id" in vals
                and "student_id" not in vals
                and self._is_customer_move(move.move_type)
            ):
                if not move.student_id and move.partner_id:
                    stu = self._find_student_for_partner(move.partner_id.id)
                    if stu:
                        updates["student_id"] = stu.id
            if updates:
                move.with_context(skip_student_sync=True).write(updates)
        return res


def action_print_payment_receipt_pdf(self):
    self.ensure_one()
    self.write({"last_receipt_download_at": fields.Datetime.now()})
    action = self.env.ref(
        "acmst_finance.report_student_payment_receipt_action_html"
    ).report_action(self)
    action["report_type"] = "qweb-pdf"
    action["close_on_report_download"] = True
    return action
