from odoo import models, fields


class AdmissionsOtp(models.Model):
    _name = 'admissions.otp'
    _description = 'Admissions OTP Records'

    phone = fields.Char(required=True, index=True)
    purpose = fields.Selection([('login', 'Login')], default='login')
    code_hash = fields.Char(index=True)
    salt = fields.Char()
    expire_at = fields.Datetime(index=True)
    attempts = fields.Integer(default=0)
    status = fields.Selection([
        ('new', 'New'),
        ('sent', 'Sent'),
        ('ok', 'Verified'),
        ('bad', 'Failed'),
        ('exp', 'Expired'),
    ], default='new', index=True)
    ip = fields.Char()
    user_agent = fields.Char()

