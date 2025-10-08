{
    "name": "ACMST Student Study Fields",
    "version": "1.0",
    "summary": "Collect & manage students' fields of interest from website forms",
    "author": "ACMST",
    "license": "LGPL-3",
    "depends": ["base", "website"],
    "data": [
        "security/ir.model.access.csv",
        "data/study_field_options_data.xml",
        "views/study_field_option_views.xml",
        "views/student_study_fields_views.xml",
        "views/website_templates.xml",
    ],
    "installable": True,
    "application": True,
}
