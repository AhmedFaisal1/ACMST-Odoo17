
# -*- coding: utf-8 -*-
from odoo import fields, models

class AccountMove(models.Model):
    _inherit = 'account.move'

    x_student_id = fields.Many2one('acmst.student', string="Student")
    x_payment_method = fields.Selection([
        ('cash','Cash'),
        ('bank','Bank Transfer'),
        ('mobile','Mobile / Wallet'),
        ('pos','POS'),
        ('other','Other'),
    ], string="Payment")
    x_transaction_number = fields.Char("Transaction Number")
