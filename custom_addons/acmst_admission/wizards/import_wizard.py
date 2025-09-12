import base64
import csv
from io import StringIO, BytesIO
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ..models.utils import normalize_arabic, to_western_digits


EXPECTED_HEADERS = [
    'first_ar', 'second_ar', 'third_ar', 'fourth_ar',
    'first_en', 'second_en', 'third_en', 'fourth_en',
    'program_code', 'year_code', 'base_university_id', 'dob', 'national_id',
]
HEADER_SYNONYMS = {
    'FRMNO': 'base_university_id',
    'FRM': 'base_university_id',
    'UNIV_ID': 'program_code',
    'FAC': 'program_code',
    'FACNAME': 'program_name',
    'YEAR': 'year_code',
    'N1': 'first_ar',
    'N2': 'second_ar',
    'N3': 'third_ar',
    'N4': 'fourth_ar',
    'NATIONAL_ID': 'national_id',
}


class AdmissionsImportWizard(models.TransientModel):
    _name = 'admissions.import.wizard'
    _description = 'Admissions Import Wizard'

    upload = fields.Binary(string='CSV/XLSX File', required=True)
    filename = fields.Char()
    preview = fields.Text(readonly=True)
    imported_count = fields.Integer(readonly=True)
    rejected_count = fields.Integer(readonly=True)
    mapping_json = fields.Text(string='Column Mapping (JSON)',
                               help='Optional JSON mapping of input column names to expected fields, e.g. {"BaseID":"base_university_id"}.')

    def action_preview(self):
        self.ensure_one()
        rows = self._read_rows(limit=10)
        out = []
        out.append(','.join(EXPECTED_HEADERS) + '  # synonyms accepted: ' + ', '.join([f"{k}->{v}" for k,v in HEADER_SYNONYMS.items()]))
        for r in rows:
            # apply synonyms for preview
            r2 = dict(r)
            for k, v in HEADER_SYNONYMS.items():
                if k in r and v not in r2:
                    r2[v] = r.get(k)
            out.append(','.join([str(r2.get(h, '')) for h in EXPECTED_HEADERS]))
        self.preview = '\n'.join(out)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'admissions.import.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_import(self):
        self.ensure_one()
        # Enqueue as background job processed by cron
        if not self.upload:
            return
        job = self.env['admissions.import.job'].sudo().create({
            'filename': self.filename or 'import.csv',
            'data': self.upload,
            'state': 'pending',
            'mapping_json': self.mapping_json,
        })
        self.preview = _('Import enqueued as job #%s. Check Admissions > Import Jobs for progress.') % job.id
        self.imported_count = 0
        self.rejected_count = 0
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'admissions.import.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_download_sample(self):
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/admissions/import/sample-csv',
        }

    # Helpers
    def _read_rows(self, limit=None):
        if not self.upload:
            raise UserError(_('No file uploaded'))
        data = base64.b64decode(self.upload)
        name = (self.filename or '').lower()
        if name.endswith('.csv') or not name:
            return self._read_csv(data, limit=limit)
        elif name.endswith('.xlsx'):
            try:
                return self._read_xlsx(data, limit=limit)
            except Exception as e:
                raise UserError(_('Failed to read XLSX. Install openpyxl or upload CSV.\nError: %s') % e)
        else:
            raise UserError(_('Unsupported file type. Please upload CSV or XLSX.'))

    def _read_csv(self, data, limit=None):
        text = data.decode('utf-8-sig')
        f = StringIO(text)
        reader = csv.DictReader(f)
        rows = []
        for i, row in enumerate(reader):
            rows.append(row)
            if limit and len(rows) >= limit:
                break
        return rows

    def _read_xlsx(self, data, limit=None):
        import openpyxl  # noqa: F401
        wb = openpyxl.load_workbook(filename=BytesIO(data), read_only=True)
        ws = wb.active
        headers = [c.value for c in next(ws.rows)]
        rows = []
        for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True)):
            rec = {headers[j]: (row[j] if j < len(row) else None) for j in range(len(headers))}
            rows.append(rec)
            if limit and len(rows) >= limit:
                break
        return rows
