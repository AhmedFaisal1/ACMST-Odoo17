# ACMST Acceptance Form Module

This module provides comprehensive student acceptance form management for ACMST (Al-Ahliyya Amman University for Science and Technology).

## Features

- **Student Acceptance Forms**: Complete form management with personal, academic, and guardian information
- **Guardian Management**: Multiple guardians per student with relationship tracking
- **Multi-language Support**: Arabic and English interface and reports
- **Professional PDF Reports**: Multi-page reports with proper pagination and formatting
- **Medical Declaration Forms**: Separate Arabic and English medical questionnaires
- **Approval Workflows**: Program coordinator approval and signature management

## Models

- `acmst.acceptance.form`: Main acceptance form model
- `acmst.acceptance.guardian`: Guardian information model

## Reports

- **Acceptance Form Report**: Comprehensive multi-page PDF report including:
  - Personal information
  - Academic details
  - Guardian information
  - Program coordinator approval
  - Admission steps and guidelines
  - Registration steps and financial guidelines
  - Undertaking section
  - Medical declaration forms (Arabic and English)

## Installation

1. Copy this module to your Odoo addons directory
2. Update the module list
3. Install the "ACMST Acceptance" module

## Usage

1. Navigate to ACMST Acceptance > Acceptance Forms
2. Create new acceptance forms for students
3. Add guardian information as needed
4. Generate PDF reports for printing or digital distribution

## Technical Details

- Compatible with Odoo 17.0
- Uses QWeb templates for report generation
- Supports RTL (Arabic) and LTR (English) text direction
- Optimized for PDF generation with proper page breaks

