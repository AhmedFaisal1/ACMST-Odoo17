# -*- coding: utf-8 -*-
from odoo import fields, models

class AccountMove(models.Model):
    _inherit = "account.move"
    invoice_origin = fields.Char(string="University ID")
    ref = fields.Char(string="Transaction Number")
    # mirror of acmst.enrollment.payment_type
    acmst_payment_type = fields.Selection(
        [
            ("cash", "Cash"),
            ("bank", "Bank Transfer"),
            ("pos", "POS"),
            ("other", "Other"),
        ],
        string="Payment Type",
        readonly=True,
    )
