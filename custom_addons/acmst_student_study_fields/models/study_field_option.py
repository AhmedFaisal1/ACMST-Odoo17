from odoo import models, fields


class StudyFieldOption(models.Model):
    _name = "acmst.study.field.option"
    _description = "Study Field Option"

    name = fields.Char("Field Name", required=True)
    code = fields.Char("Code")  # اختياري (مثلاً AI, DS, MED...)
    active = fields.Boolean("Active", default=True)
