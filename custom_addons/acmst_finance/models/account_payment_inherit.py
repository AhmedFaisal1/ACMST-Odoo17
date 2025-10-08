# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from urllib.parse import quote_plus


class AccountPayment(models.Model):
    _inherit = "account.payment"

    student_academic_year = fields.Char(
        string="Academic Year",
        related="student_id.academic_year",
        store=True,
        readonly=True,
    )
    acmst_bank_account_label = fields.Char(
        string="ACMST Bank Account Label",
        compute="_compute_acmst_bank_account_label",
        store=False,
    )
    acmst_qr_value = fields.Char(
        string="QR Value", compute="_compute_acmst_qr_value", store=False
    )
    acmst_qr_url = fields.Char(
        string="QR Image URL", compute="_compute_acmst_qr_value", store=False
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="move_id.company_id",
        store=True,
        index=True,
        readonly=True,
    )

    # uniqueness
    bank_reference = fields.Char(string="Bank Reference", index=True)
    _sql_constraints = [
        (
            "account_payment_uniq_bank_reference_company",
            "unique(company_id, bank_reference)",
            "Bank Reference must be unique per company.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "bank_reference" in vals:
                vals["bank_reference"] = (vals["bank_reference"] or "").strip() or False
        records = super().create(vals_list)
        records._infer_student_from_partner()
        return records

    def write(self, vals):
        if "bank_reference" in vals:
            vals["bank_reference"] = (vals["bank_reference"] or "").strip() or False
        res = super().write(vals)
        if "partner_id" in vals or "student_id" not in vals:
            self._infer_student_from_partner()
        return res

    @api.constrains("bank_reference")
    def _check_bank_reference_not_spaces(self):
        for rec in self:
            if rec.bank_reference and not rec.bank_reference.strip():
                raise ValidationError(_("Bank Reference cannot be only spaces."))

    # your existing helpers
    def _infer_student_from_partner(self):
        Student = self.env["acmst.student"].sudo()
        for pay in self:
            if not pay.student_id and pay.partner_id:
                stu = Student.search([("partner_id", "=", pay.partner_id.id)], limit=1)
                if stu:
                    pay.student_id = stu.id

    def _compute_acmst_bank_account_label(self):
        for pay in self:
            labels = []
            invoices = pay.reconciled_invoice_ids or pay.reconciled_bill_ids

            for inv in invoices:
                inv_label = ""
                # Use the invoice's selected GL account
                if inv.acmst_gl_bank_account_id:
                    account = inv.acmst_gl_bank_account_id
                    code = (account.code or "").strip()
                    name = (account.name or "").strip()
                    if code and name:
                        inv_label = f"{code} - {name}"
                    elif code:
                        inv_label = code
                    elif name:
                        inv_label = name
                elif inv.journal_id and inv.journal_id.default_account_id:
                    # Fallback to journal's default account
                    acc = inv.journal_id.default_account_id
                    code = (getattr(acc, "code", "") or "").strip()
                    name = (acc.name or "").strip()
                    inv_label = (f"{code} {name}").strip()

                if inv_label and inv_label not in labels:
                    labels.append(inv_label)

            label = "، ".join(labels)
            if not label and pay.journal_id and pay.journal_id.default_account_id:
                acc = pay.journal_id.default_account_id
                code = (getattr(acc, "code", "") or "").strip()
                name = (acc.name or "").strip()
                label = (f"{code} {name}").strip()

            pay.acmst_bank_account_label = label

    def _compute_acmst_qr_value(self):
        ICP = self.env["ir.config_parameter"].sudo()
        base_url = ICP.get_param("web.base.url") or ""
        for pay in self:
            value = (
                f"{base_url}/report/pdf/acmst_finance.report_student_payment_receipt/{pay.id}"
                if pay.id
                else ""
            )
            pay.acmst_qr_value = value
            pay.acmst_qr_url = (
                f"https://chart.googleapis.com/chart?chs=150x150&cht=qr&choe=UTF-8&chl={quote_plus(value)}"
                if value
                else ""
            )

    # print helpers
    def action_print_payment_receipt_pdf(self):
        self.ensure_one()
        action = self.env.ref(
            "acmst_finance.report_student_payment_receipt_action_html"
        ).report_action(self)
        action["report_type"] = "qweb-pdf"
        action.update({"close_on_report_download": True})
        return action

    def action_preview_payment_receipt_html(self):
        self.ensure_one()
        action = self.env.ref(
            "acmst_finance.report_student_payment_receipt_action_html"
        ).read()[0]
        action["context"] = dict(self.env.context, active_ids=[self.id])
        return action


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    bank_reference = fields.Char(string="Bank Reference")
    bankak_pay_date = fields.Date(string="Bankak Pay Date")
    bankak_receipt = fields.Binary(string="Bankak Receipt (PNG)", attachment=True)
    bankak_receipt_filename = fields.Char(string="Receipt Filename")

    @api.constrains("bank_reference")
    def _check_bank_reference_live(self):
        for wiz in self:
            if not wiz.bank_reference:
                continue
            bank_ref = wiz.bank_reference.strip()
            company = wiz.company_id or self.env.company
            dup = self.env["account.payment"].search(
                [
                    ("company_id", "=", company.id),
                    ("bank_reference", "=", bank_ref),
                ],
                limit=1,
            )
            if dup:
                raise ValidationError(
                    _("Bank Reference you entered is repeated (already used on %s).")
                    % dup.display_name
                )

    def _create_payments(self):
        if self.bank_reference:
            bank_ref = self.bank_reference.strip()
            company = self.company_id or self.env.company
            dup = self.env["account.payment"].search(
                [
                    ("company_id", "=", company.id),
                    ("bank_reference", "=", bank_ref),
                ],
                limit=1,
            )
            if dup:
                raise ValidationError(
                    _("Bank Reference you entered is repeated (already used on %s).")
                    % dup.display_name
                )

        payments = super()._create_payments()
        if payments:
            vals = {}
            if self.bank_reference:
                vals["bank_reference"] = self.bank_reference.strip()
            if self.bankak_pay_date:
                vals["bankak_pay_date"] = self.bankak_pay_date
            if self.bankak_receipt:
                vals["bankak_receipt"] = self.bankak_receipt
                vals["bankak_receipt_filename"] = self.bankak_receipt_filename
            if vals:
                payments.write(vals)
        return payments
