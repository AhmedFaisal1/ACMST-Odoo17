from odoo import fields, models


class AdmissionsOtpLog(models.Model):
    _name = 'admissions.otp.log'
    _description = 'Admissions OTP Provider Log'
    _order = 'create_date desc'

    provider = fields.Char(default='brevo', index=True)
    phone = fields.Char(index=True)
    event = fields.Char()
    status = fields.Char(index=True)
    payload = fields.Json(string='Payload')
    message = fields.Char()

