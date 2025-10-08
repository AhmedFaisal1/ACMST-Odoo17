# -*- coding: utf-8 -*-
{
    "name": "ACMST Acceptance Form",
    "version": "17.0.1.0.0",
    "category": "Education",
    "summary": "Student acceptance form management system",
    "description": """
        ACMST Acceptance Form Management
        ===============================
        
        This module provides comprehensive student acceptance form management including:
        - Student acceptance form creation and management
        - Guardian information management
        - PDF report generation with multi-page layout
        - Medical declaration forms (Arabic and English)
        - Program coordinator approval workflow
        
        Features:
        - Multi-language support (Arabic/English)
        - Professional PDF reports with proper pagination
        - Guardian relationship management
        - Medical questionnaire system
        - Signature and approval workflows
    """,
    "author": "ACMST",
    "website": "https://www.acmst.edu",
    "depends": [
        "base",
        "mail",
        "portal",
        "web",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/acceptance_form_data.xml",
        # Load report actions before views that reference them (Preview button)
        "report/acceptance_form_report.xml",
        "views/acceptance_guardian_views.xml",
        "views/acceptance_form_views.xml",
        "views/menu.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
    "application": True,
    "license": "LGPL-3",
}
