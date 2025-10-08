# -*- coding: utf-8 -*-
{
    "name": "ACMST Finance",
    "summary": "Students and student invoicing helpers",
    "version": "17.0.1.1.0",
    "category": "Accounting",
    "author": "Ahmed & ChatGPT",
    "license": "LGPL-3",
    "depends": ["base", "contacts", "mail", "portal", "account"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/student_import_views.xml",
        "views/student_views.xml",
        "views/res_partner_views.xml",
        "views/menu.xml",
        "views/account_move_inherit.xml",
        "views/res_company_signature_views.xml",
        "report/student_invoice_report.xml",
        "report/student_payment_receipt.xml",
        "report/payment_receipt_inherit.xml",
        "views/account_move_form_view.xml",
        "views/account_payment_register_view.xml",
        "report/payment_receipt_inherit.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "acmst_finance/static/src/scss/fonts.scss",
            "acmst_finance/static/src/scss/app_font.scss",
        ],
        "web.assets_frontend": [
            "acmst_finance/static/src/scss/fonts.scss",
            "acmst_finance/static/src/scss/app_font.scss",
        ],
        "web.report_assets_common": [  # للمعاينة HTML
            "acmst_finance/static/src/scss/fonts.scss",
            "acmst_finance/static/src/scss/report_font.scss",
        ],
        "web.report_assets_pdf": [  # للتوليد PDF فعليًا
            "acmst_finance/static/src/scss/fonts.scss",
            "acmst_finance/static/src/scss/report_font.scss",
        ],
        "web.report_assets_common": [
            "/acmst_finance/static/src/fonts/Almarai-Regular.ttf",
            "/acmst_finance/static/src/fonts/Almarai-Bold.ttf",
            "/acmst_finance/static/src/fonts/Almarai-ExtraBold.ttf",
            "/acmst_finance/static/src/fonts/Almarai-Light.ttf",
            "/acmst_finance/static/src/scss/app_fonts.scss",
            "/acmst_finance/static/src/scss/report_font.scss",
        ],
    },
    "installable": True,
    "application": True,
}
