# Docker Notes for PDFs and Fonts

The default `odoo:17` image may lack wkhtmltopdf and some fonts needed for Arabic PDFs.

Option A: Use the provided Dockerfile
- Build a custom image with wkhtmltopdf + fonts:

  docker build -f custom_addons/acmst_admission/docker/Dockerfile.odoo -t odoo:17-wkhtml .

- In `docker-compose.yml`, set:

  services:
    odoo:
      image: odoo:17-wkhtml

Option B: Install fonts into the running container
- Exec into the container and install font packages and wkhtmltopdf.

Ensure report engine works and Arabic glyphs render correctly.
