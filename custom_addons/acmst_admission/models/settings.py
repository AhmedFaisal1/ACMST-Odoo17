from odoo import api, fields, models


class AdmissionsSettings(models.Model):
    _name = 'admissions.settings'
    _description = 'Admissions Settings'

    otp_length = fields.Integer(default=6)
    otp_ttl_minutes = fields.Integer(default=10)
    rate_limit_window_minutes = fields.Integer(default=15)
    rate_limit_sends_per_window = fields.Integer(default=3)
    rate_limit_daily_sends = fields.Integer(default=10)
    verify_attempts_per_code = fields.Integer(default=5)
    id_comp_rule = fields.Char(string='ID Composition Rule', default='{{ base }}{{ year }}')
    otp_cooldown_seconds = fields.Integer(string='OTP Cooldown (sec)', default=60)

    @api.model
    def get_settings(self):
        return self.sudo().search([], limit=1, order='id desc')
