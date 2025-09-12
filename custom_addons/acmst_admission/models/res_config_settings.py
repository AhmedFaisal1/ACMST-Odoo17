from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    brevo_api_key = fields.Char(string='Brevo API Key', config_parameter='acmst_admission.brevo_api_key')
    brevo_sender = fields.Char(string='Brevo WhatsApp Sender', config_parameter='acmst_admission.brevo_sender')
    brevo_template = fields.Char(string='Brevo Template Name', default='otp', config_parameter='acmst_admission.brevo_template')
    brevo_language = fields.Char(string='Brevo Template Language', default='en', config_parameter='acmst_admission.brevo_language')

    recaptcha_site_key = fields.Char(string='reCAPTCHA Site Key', config_parameter='acmst_admission.recaptcha_site_key')
    recaptcha_secret_key = fields.Char(string='reCAPTCHA Secret Key', config_parameter='acmst_admission.recaptcha_secret_key')

    blacklist_phones = fields.Char(string='OTP Blacklist Phones',
                                   help='Comma- or line-separated E.164 phone numbers to block OTP sending.',
                                   config_parameter='acmst_admission.blacklist_phones')

    brevo_webhook_secret = fields.Char(string='Brevo Webhook Secret',
                                       help='Shared secret used to validate Brevo webhook callbacks.',
                                       config_parameter='acmst_admission.brevo_webhook_secret')
