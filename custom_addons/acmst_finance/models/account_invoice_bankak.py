# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    bankak_pay_date = fields.Date(string="Bankak Pay Date")
    bankak_receipt = fields.Binary(string="Bankak Receipt (PNG)", attachment=True)
    bankak_receipt_filename = fields.Char(string="Receipt Filename")


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    # shown in the Register Payment wizard
    bankak_pay_date = fields.Date(string="Bankak Pay Date")
    bankak_receipt = fields.Binary(string="Bankak Receipt (PNG)", attachment=True)
    bankak_receipt_filename = fields.Char(string="Receipt Filename")

    def _create_payments(self):
        """Create payments normally, then write Bankak fields to:
        - the created payment(s)
        - the target invoice(s) (account.move) being paid
        """
        payments = super()._create_payments()

        # Write to created payment records
        if payments:
            payments.write(
                {
                    "bankak_pay_date": self.bankak_pay_date,
                    "bankak_receipt": self.bankak_receipt,
                    "bankak_receipt_filename": self.bankak_receipt_filename,
                }
            )

        # Write to the invoices this wizard is paying
        # Wizard has self.line_ids pointing at receivable/payable move lines
        target_moves = self.line_ids.mapped("move_id")
        if target_moves:
            target_moves.write(
                {
                    "bankak_pay_date": self.bankak_pay_date,
                    "bankak_receipt": self.bankak_receipt,
                    "bankak_receipt_filename": self.bankak_receipt_filename,
                }
            )
        return payments


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # keep a copy on the payment itself (handy for receipts)
    bankak_pay_date = fields.Date(string="Bankak Pay Date")
    bankak_receipt = fields.Binary(string="Bankak Receipt (PNG)", attachment=True)
    bankak_receipt_filename = fields.Char(string="Receipt Filename")
