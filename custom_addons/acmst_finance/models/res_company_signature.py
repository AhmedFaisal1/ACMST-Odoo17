# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    acmst_signature_invoice = fields.Binary(
        string='Invoice Signature (PNG)',
        help='Signature image to print on ACMST Student Invoices.'
    )
    acmst_signature_receipt = fields.Binary(
        string='Receipt Signature (PNG)',
        help='Signature image to print on ACMST Payment Receipts.'
    )
    acmst_college_stamp = fields.Binary(
        string='College Stamp (PNG)',
        help='College stamp image printed on Student Invoices and Payment Receipts.'
    )
