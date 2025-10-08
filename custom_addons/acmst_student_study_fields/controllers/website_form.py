# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request


class WebsiteForm(http.Controller):

    @http.route("/e-learning-registration", type="http", auth="public", website=True)
    def e_learning_registration(self, **kwargs):
        """Display the E-Learning Registration form"""
        return request.render("acmst_student_study_fields.e_learning_registration_form")

    @http.route(
        "/e-learning-registration-success", type="http", auth="public", website=True
    )
    def e_learning_registration_success(self, **kwargs):
        """Display the E-Learning Registration success page"""
        return request.render(
            "acmst_student_study_fields.e_learning_registration_success"
        )

    @http.route("/volunteering-charity", type="http", auth="public", website=True)
    def volunteering_charity(self, **kwargs):
        """Display the Volunteering & Charity form"""
        return request.render("acmst_student_study_fields.volunteering_charity_form")

    @http.route(
        "/volunteering-charity-success", type="http", auth="public", website=True
    )
    def volunteering_charity_success(self, **kwargs):
        """Display the Volunteering & Charity success page"""
        return request.render("acmst_student_study_fields.volunteering_charity_success")

    @http.route(
        "/website/form/acmst.student.study.fields",
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def handle_form_submission(self, **kwargs):
        """Handle form submission and create student record"""
        try:
            # Map form field names to model field names
            field_mapping = {
                "your_name": "name",
                "phone_number": "phone",
                "whatsapp": "whatsapp",
                "your_email": "email",
                "fields": "field_of_interest_id",
            }

            # Prepare data for model creation
            student_data = {}
            for form_field, model_field in field_mapping.items():
                if form_field in kwargs and kwargs[form_field]:
                    student_data[model_field] = kwargs[form_field]

            # Handle field_of_interest_id - convert from name to ID
            if (
                "field_of_interest_id" in student_data
                and student_data["field_of_interest_id"]
            ):
                field_name = student_data["field_of_interest_id"]
                if isinstance(field_name, str):
                    # Find the study field option by name
                    study_field = (
                        request.env["acmst.study.field.option"]
                        .sudo()
                        .search([("name", "ilike", field_name)], limit=1)
                    )
                    if study_field:
                        student_data["field_of_interest_id"] = study_field.id
                    else:
                        # If not found, create a new one
                        study_field = (
                            request.env["acmst.study.field.option"]
                            .sudo()
                            .create(
                                {
                                    "name": field_name,
                                    "code": field_name.upper().replace(" ", "_")[:10],
                                }
                            )
                        )
                        student_data["field_of_interest_id"] = study_field.id

            # Create the student record
            if student_data:
                student_record = (
                    request.env["acmst.student.study.fields"]
                    .sudo()
                    .create(student_data)
                )

                # Determine which success page to redirect to based on the referrer
                referrer = request.httprequest.headers.get("Referer", "")
                if "volunteering-charity" in referrer:
                    return request.redirect(
                        f"/volunteering-charity-success?student_id={student_record.id}"
                    )
                else:
                    return request.redirect(
                        f"/e-learning-registration-success?student_id={student_record.id}"
                    )

            # Redirect to appropriate success page based on referrer
            referrer = request.httprequest.headers.get("Referer", "")
            if "volunteering-charity" in referrer:
                return request.redirect("/volunteering-charity-success")
            else:
                return request.redirect("/e-learning-registration-success")

        except Exception as e:
            # Log error and redirect back to form
            return request.redirect("/e-learning-registration?error=1")
