# -*- coding: utf-8 -*-
{
    "name": "ACMST Finance",
    "summary": "Student admissions, quotations, and invoicing for ACMST",
    "version": "17.0.1.0.0",
    "category": "Accounting",
    "author": "Ahmed & ChatGPT",
    "website": "https://example.com",
    "license": "LGPL-3",
    "depends": ["base", "account", "product"],
    "data": [
    "security/ir.model.access.csv",
    "wizards/student_import_views.xml",
    "views/student_views.xml",
    "views/enrollment_views.xml",
    "views/menu.xml",
    "report/invoice_inherit.xml",
    "views/account_move_inherit.xml",
    ],
"assets": {
    "web.assets_backend": [
        "acmst_finance/static/src/scss/hide_customer_invoice.scss",
    ],
},
    "installable": True,
    "application": True
}
