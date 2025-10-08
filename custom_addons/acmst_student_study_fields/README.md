# ACMST Student Study Fields

This module captures student registration data from website forms and stores it in the Student Study Fields model.

## Features

- Website form for E-Learning Registration
- Automatic data capture from form to model
- Field mapping between form fields and model fields
- Success page after form submission
- Backend management interface for viewing registrations

## Installation

1. Install the module in Odoo
2. The module will automatically create sample study field options
3. Access the form at: `http://your-domain/e-learning-registration`

## Form Fields

The form captures the following data:

- **Your Name** → `name` field
- **Phone Number** → `phone` field
- **WhatsApp** → `whatsapp` field
- **Your Email** → `email` field
- **Fields** → `field_of_interest_id` field (dropdown with study field options)

## Backend Access

After installation, you can view submitted registrations in:

- **Student Study Fields** → **Student Registrations** menu
- **Student Study Fields** → **Field Options** menu (to manage study fields)

## Customization

To modify the form fields or add new ones:

1. Update the form template in `views/website_templates.xml`
2. Update the field mapping in `controllers/website_form.py`
3. Update the model fields in `models/student_study_fields.py`
4. Update the views in `views/student_study_fields_views.xml`

## Study Field Options

The module comes with pre-configured study field options:

- Artificial Intelligence (AI)
- Data Science
- Web Development
- Mobile Development
- Cybersecurity
- Cloud Computing

You can add more options through the backend interface.

