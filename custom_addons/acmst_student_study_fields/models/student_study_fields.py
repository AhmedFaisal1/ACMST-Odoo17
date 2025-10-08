from odoo import models, fields


class StudentStudyFields(models.Model):
    _name = "acmst.student.study.fields"
    _description = "Student Study Fields"
    _inherit = ["website.published.mixin"]

    name = fields.Char("Full Name", required=True)
    phone = fields.Char("Phone Number", required=True)
    whatsapp = fields.Char("WhatsApp", required=True)
    email = fields.Char("Email", required=True)

    field_of_interest_id = fields.Many2one(
        "acmst.study.field.option",
        string="Field of Interest",
        required=True,
    )
