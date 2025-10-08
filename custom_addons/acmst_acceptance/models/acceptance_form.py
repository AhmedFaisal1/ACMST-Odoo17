from odoo import models, fields, api, _


class AcceptanceForm(models.Model):
    _name = "acmst.acceptance.form"
    _description = "Acceptance Form Wizard"
    _rec_name = "full_name_ar"

    # Guardians
    guardian_ids = fields.One2many(
        "acmst.acceptance.guardian", "wizard_id", string="Guardians"
    )
    default_guardian_id = fields.Many2one(
        "acmst.acceptance.guardian",
        string="Default Guardian",
        domain="[('wizard_id','=',id)]",
    )

    # Type of Admission (updated list)
    admission_type = fields.Selection(
        selection=[
            ("direct", "قبول مباشر / Direct Admission"),
            ("general", "عام / General"),
            ("regular", "نظامي / Regular"),
            ("private", "خاص / Private"),
            ("transfer", "تحويل / Transfer"),
            ("bridging", "تجسير / Bridging"),
            ("degree_holder", "حملة درجات علمية / Degree Holders"),
            ("private_grant", "منح التعليم الأهلي / Private Education Grant"),
        ],
        string="نوع القبول / Type of Admission",
        required=True,
        default="direct",
    )

    photo = fields.Binary(string="الصورة / Photo")

    # Company (for logo on report)
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )

    # Personal
    full_name_ar = fields.Char(
        string="الاسم الرباعي بالعربي / Full Name in Arabic", required=True
    )
    full_name_en = fields.Char(
        string="الاسم الرباعي بالإنجليزي / Full Name in English", required=True
    )
    gender = fields.Selection(
        selection=[("male", "ذكر / Male"), ("female", "أنثى / Female")],
        string="النوع / Sex",
    )
    nationality = fields.Char(string="الجنسية / Nationality")
    religion = fields.Char(string="الديانة / Religion")
    birth_date = fields.Date(string="تاريخ الميلاد / Date of Birth")
    birth_place = fields.Char(string="مكان الميلاد / Place of Birth")
    email = fields.Char(string="البريد الإلكتروني / Email")

    # Unified identification choice + number
    identification_document = fields.Selection(
        selection=[
            ("nid", "رقم الهوية / National ID"),
            ("passport", "رقم الجواز / Passport No."),
        ],
        string="وثيقة الهوية للشخصية / Identification Document",
        default="nid",
    )
    document_number = fields.Char(string="رقم الوثيقة / Document Number")

    # (You can keep these if used elsewhere; not shown in the form)
    national_id = fields.Char(string="رقم الهوية / National ID")
    passport_no = fields.Char(string="رقم الجواز / Passport No.")

    address = fields.Char(string="العنوان بالتفصيل / Address")
    city = fields.Char(string="مدينة السكن / City")
    phone1 = fields.Char(string="رقم هاتف (1) / Phone (1)")
    phone2 = fields.Char(string="رقم هاتف (2) / Phone (2)")

    # Admission (matches your screenshot)
    academic_year = fields.Char(string="عام القبول / Admission Year")
    program_name = fields.Char(string="البرنامج / Program")
    university_id = fields.Char(string="الرقم الجامعي / University ID")
    admission_date = fields.Date(
        string="تاريخ القبول / Admission Date", default=fields.Date.context_today
    )

    certificate_type = fields.Selection(
        selection=[
            ("sudanese", "سودانية / Sudanese"),
            ("igcse", "IGCSE / British"),
            ("american", "American"),
            ("other", "أخرى / Other"),
        ],
        string="نوع الشهادة / Certificate Type",
    )
    secondary_school = fields.Char(string="مدرسة الشهادة الثانوية / Secondary School")
    secondary_percentage = fields.Float(
        string="نسبة الشهادة للثانوية / Secondary Certificate Percentage",
        digits=(16, 2),
    )

    # Optional legacy fields kept for report compatibility
    college_name = fields.Char(
        string="الكلية / College", default="كلية المدن للعلوم الطبية والتكنولوجيا"
    )
    level_name = fields.Char(string="المستوى / Level-Intake")
    application_no = fields.Char(string="رقم المعاملة / Application No.")
    admission_status = fields.Char(string="الحالة / Status", default="New")

    # Undertaking
    undertake_date = fields.Date(string="Undertake Date")
    signature_place = fields.Char(string="Signature Place")

    # Medical declaration
    med_diabetes = fields.Boolean(string="Diabetes")
    med_hypertension = fields.Boolean(string="Hypertension")
    med_asthma = fields.Boolean(string="Asthma")
    med_hepb = fields.Boolean(string="Hepatitis B")
    med_heart = fields.Boolean(string="Heart disease")
    med_disability = fields.Boolean(string="Physical disability")
    med_psych = fields.Boolean(string="Psychiatric")
    med_other = fields.Char(string="Other condition")
    med_hospitalized = fields.Boolean(string="Hospitalized before")
    med_surgery = fields.Boolean(string="Surgery before")

    # Compatibility fields expected by the report (computed from new fields)
    full_name = fields.Char(
        string="Full Name", compute="_compute_compat_fields", store=False
    )
    hs_certificate_type = fields.Char(
        string="High School Certificate", compute="_compute_compat_fields", store=False
    )
    hs_percentage = fields.Float(
        string="HS Percentage", compute="_compute_compat_fields", store=False
    )
    previous_institution = fields.Char(
        string="Previous Institution", compute="_compute_compat_fields", store=False
    )
    previous_years = fields.Integer(
        string="Previous Years", compute="_compute_compat_fields", store=False
    )
    guardian_name = fields.Char(
        string="Guardian Name (compat)", compute="_compute_compat_fields", store=False
    )
    guardian_phone = fields.Char(
        string="Guardian Phone (compat)", compute="_compute_compat_fields", store=False
    )
    guardian_relation = fields.Char(
        string="Guardian Relation (compat)",
        compute="_compute_compat_fields",
        store=False,
    )
    guardian_address = fields.Char(
        string="Guardian Address (compat)",
        compute="_compute_compat_fields",
        store=False,
    )

    # Committee decision (used by report)
    medical_pass = fields.Boolean(string="Medical Check Passed")
    committee_recommendation = fields.Char(string="Committee Recommendation")
    committee_chair = fields.Char(string="Committee Chair")
    committee_notes = fields.Text(string="Committee Notes")
    coordinator_name = fields.Char(string="Program Coordinator")
    admissions_manager = fields.Char(string="Admissions Director")
    # ---- Previous institution (for Bridging / Transfer / Degree Holders / Mature) ----
    prev_inst_name = fields.Char(string="اسم المؤسسة / Institution Name")
    prev_inst_join_year = fields.Char(string="عام الإلتحاق بالمؤسسة / Year of Joining")
    prev_inst_years_completed = fields.Integer(
        string="عدد السنوات الدراسية التي أكملها / Years Completed"
    )
    prev_inst_program = fields.Char(
        string="الكلية/البرنامج/التخصص / College/Program/Major"
    )
    # Free-text instead of selection
    prev_grad_cert_type = fields.Char(
        string="نوع شهادة التخرج / Graduation Certificate Type"
    )

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref(
            "acmst_acceptance.action_report_acceptance_form_wiz"
        ).report_action(self)

    @api.depends(
        "full_name_en",
        "full_name_ar",
        "certificate_type",
        "secondary_percentage",
        "prev_inst_name",
        "prev_inst_years_completed",
        "default_guardian_id",
        "guardian_ids.name",
        "guardian_ids.phone",
        "guardian_ids.relation",
        "guardian_ids.address",
    )
    def _compute_compat_fields(self):
        label_map = (
            dict(self._fields["certificate_type"].selection)
            if self._fields.get("certificate_type")
            else {}
        )
        for rec in self:
            rec.full_name = rec.full_name_en or rec.full_name_ar or False
            rec.hs_certificate_type = label_map.get(
                rec.certificate_type, rec.certificate_type or False
            )
            rec.hs_percentage = rec.secondary_percentage or 0.0
            rec.previous_institution = rec.prev_inst_name or False
            rec.previous_years = rec.prev_inst_years_completed or 0
            g = rec.default_guardian_id or (
                rec.guardian_ids[:1] if rec.guardian_ids else False
            )
            if g:
                rec.guardian_name = g.name
                rec.guardian_phone = g.phone
                rec.guardian_relation = g.relation
                rec.guardian_address = g.address
            else:
                rec.guardian_name = rec.guardian_phone = rec.guardian_relation = (
                    rec.guardian_address
                ) = False

    @api.model
    def default_get(self, fields_list):
        """Prefill from active Student when opened from Students list/form."""
        res = super().default_get(fields_list)
        if self.env.context.get(
            "active_model"
        ) == "acmst.student" and self.env.context.get("active_id"):
            student = (
                self.env["acmst.student"].browse(self.env.context["active_id"]).exists()
            )
            if student:
                # Safe mappings
                mapping = {
                    "academic_year": student.academic_year,
                    "program_name": student.facname or "",
                    "university_id": student.frmno or "",
                    "full_name_ar": student.full_name or "",
                }
                for k, v in mapping.items():
                    if k in fields_list:
                        res[k] = v
        return res

    def action_save(self):
        """Explicit save button: ensures changes are stored and stays on form."""
        self.ensure_one()
        # nothing special: pressing the button saves the record before calling
        # this method; return a small notification
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Saved"),
                "message": _("Acceptance form data saved."),
                "sticky": False,
                "type": "success",
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Ensure guardian rows are linked after the wizard is created.

        We first create the wizard(s) without the one2many payload, then
        write the guardians back with the correct `wizard_id`.
        """
        records = self.browse()
        for vals in vals_list:
            cmds = vals.pop("guardian_ids", [])
            rec = super(AcceptanceForm, self).create(vals)
            if cmds:
                fixed_cmds = []
                for cmd in cmds:
                    if isinstance(cmd, (list, tuple)) and len(cmd) == 3:
                        if cmd[0] == 0:
                            row_vals = dict(cmd[2] or {})
                            row_vals.setdefault("wizard_id", rec.id)
                            fixed_cmds.append((0, 0, row_vals))
                        else:
                            fixed_cmds.append(cmd)
                    else:
                        fixed_cmds.append(cmd)
                rec.write({"guardian_ids": fixed_cmds})
            records |= rec
        return records

    # Make sure inline guardian rows always receive the FK when saving
    def write(self, vals):
        if vals.get("guardian_ids"):
            fixed_cmds = []
            for cmd in vals["guardian_ids"]:
                # x2many command format: (0, 0, vals) to create
                if isinstance(cmd, (list, tuple)) and len(cmd) == 3 and cmd[0] == 0:
                    row_vals = dict(cmd[2] or {})
                    if not row_vals.get("wizard_id"):
                        # ensure the parent FK is set
                        row_vals["wizard_id"] = self.id
                    fixed_cmds.append((0, 0, row_vals))
                else:
                    fixed_cmds.append(cmd)
            vals = dict(vals, guardian_ids=fixed_cmds)
        return super().write(vals)
