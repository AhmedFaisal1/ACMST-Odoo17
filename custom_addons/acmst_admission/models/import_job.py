import base64
import csv
from io import StringIO, BytesIO
from datetime import datetime
from odoo import api, fields, models, _


class AdmissionsImportJob(models.Model):
    _name = 'admissions.import.job'
    _description = 'Admissions Import Job'
    _order = 'create_date desc'

    filename = fields.Char()
    data = fields.Binary(string='Source File')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('error', 'Error'),
        ('cancelled', 'Cancelled'),
    ], default='pending', index=True)
    total = fields.Integer()
    processed = fields.Integer()
    imported = fields.Integer()
    rejected = fields.Integer()
    log = fields.Text()
    errors_csv = fields.Binary(string='Errors CSV')
    errors_csv_filename = fields.Char(default='import_errors.csv')
    mapping_json = fields.Text(string='Column Mapping (JSON)')

    # Common header synonyms mapping to expected internal field names
    HEADER_SYNONYMS = {
        'FRMNO': 'base_university_id',
        'FRM': 'base_university_id',
        'BASE_ID': 'base_university_id',
        'UNIV_ID': 'program_code',  # fallback as program code when provided
        'FAC': 'program_code',
        'FACNAME': 'program_name',
        'YEAR': 'year_code',
        'N1': 'first_ar',
        'N2': 'second_ar',
        'N3': 'third_ar',
        'N4': 'fourth_ar',
        'NATIONAL_ID': 'national_id',
    }

    def append_log(self, msg):
        for rec in self:
            rec.log = (rec.log or '') + f"[{fields.Datetime.now()}] {msg}\n"

    @api.model
    def cron_process_import_jobs(self, limit=1, batch_size=1000):
        jobs = self.search([('state', 'in', ('pending', 'processing'))], order='id', limit=limit)
        for job in jobs:
            try:
                job._process_job(batch_size=batch_size)
            except Exception as e:
                job.write({'state': 'error'})
                job.append_log(f"Error: {e}")

    def _process_job(self, batch_size=1000):
        self.ensure_one()
        if not self.data:
            self.write({'state': 'error'})
            self.append_log('No data in job.')
            return
        if self.state == 'cancelled':
            return
        if self.state == 'pending':
            self.write({'state': 'processing', 'processed': 0, 'imported': 0, 'rejected': 0})

        # Decode to rows
        data = base64.b64decode(self.data)
        name = (self.filename or '').lower()
        if name.endswith('.xlsx'):
            rows = self._read_xlsx_rows(data)
        else:
            rows = self._read_csv_rows(data)
        # Apply optional column mapping
        rows = self._apply_mapping(rows)
        # Apply header synonyms if still not mapped
        rows = self._apply_synonyms(rows)
        self.total = len(rows)

        Candidate = self.env['admissions.candidate'].sudo()
        Program = self.env['admissions.program'].sudo()
        Year = self.env['admissions.year'].sudo()
        prog_cache = {}
        year_cache = {}
        from .utils import normalize_arabic, to_western_digits

        error_out = StringIO()
        error_writer = csv.writer(error_out)
        error_writer.writerow(['row', 'reason'])

        start = self.processed
        end = min(start + batch_size, self.total)

        def _to_text(v):
            if v is None:
                return ''
            try:
                # Avoid scientific notation on integers stored as floats
                if isinstance(v, float):
                    if v.is_integer():
                        return str(int(v))
                return str(v)
            except Exception:
                return ''
        batch_vals = []
        for idx in range(start, end):
            if self.state == 'cancelled':
                break
            row = rows[idx]
            try:
                base_id = _to_text(row.get('base_university_id')).strip()
                prog_code = _to_text(row.get('program_code')).strip()
                year_code = _to_text(row.get('year_code')).strip()
                # Keep academic year as provided (e.g., '2023/2022') for code/label
                # Optionally normalize if purely numeric float
                if not (base_id and year_code):
                    self.rejected += 1
                    error_writer.writerow([idx + 2, 'missing base/year'])
                    continue
                # Fallback program code if missing
                if not prog_code:
                    pname = (row.get('program_name') or '').strip()
                    if pname:
                        import re as _re
                        ascii_only = _re.sub(r"[^A-Za-z0-9]+", "_", pname).strip('_')
                        prog_code = ascii_only[:32] or 'GEN'
                    else:
                        prog_code = 'GEN'
                prog = None
                if prog_code in prog_cache:
                    prog = prog_cache[prog_code]
                else:
                    prog = Program.search([('code', '=', prog_code)], limit=1)
                pname = _to_text(row.get('program_name')).strip()
                if not prog:
                    vals_prog = {'code': prog_code}
                    if pname:
                        vals_prog['name_ar'] = pname
                    prog = Program.create(vals_prog)
                else:
                    if pname and not prog.name_ar:
                        prog.write({'name_ar': pname})
                prog_cache[prog_code] = prog
                if year_code in year_cache:
                    year = year_cache[year_code]
                else:
                    year = Year.search([('code', '=', year_code)], limit=1)
                if not year:
                    year = Year.create({'code': year_code, 'label': year_code})
                year_cache[year_code] = year
                vals = {
                    'base_university_id': to_western_digits(base_id),
                    'program_id': prog.id,
                    'academic_year_id': year.id,
                    'first_ar': normalize_arabic(_to_text(row.get('first_ar'))),
                    'second_ar': normalize_arabic(_to_text(row.get('second_ar'))),
                    'third_ar': normalize_arabic(_to_text(row.get('third_ar'))),
                    'fourth_ar': normalize_arabic(_to_text(row.get('fourth_ar'))),
                    'first_en': _to_text(row.get('first_en')).strip(),
                    'second_en': _to_text(row.get('second_en')).strip(),
                    'third_en': _to_text(row.get('third_en')).strip(),
                    'fourth_en': _to_text(row.get('fourth_en')).strip(),
                    'national_id': to_western_digits(_to_text(row.get('national_id')).strip()),
                }
                dob = _to_text(row.get('dob')).strip()
                if dob:
                    try:
                        if '-' in dob:
                            vals['dob'] = dob
                        elif '/' in dob:
                            d, m, y = dob.split('/')
                            vals['dob'] = f"{y}-{int(m):02d}-{int(d):02d}"
                    except Exception:
                        pass
                dup = Candidate.search([
                    ('base_university_id', '=', vals['base_university_id']),
                    ('program_id', '=', prog.id),
                    ('academic_year_id', '=', year.id),
                ], limit=1)
                if dup:
                    vals['import_job_id'] = self.id
                    dup.write(vals)
                else:
                    vals['import_job_id'] = self.id
                    batch_vals.append(vals)
                self.imported += 1
            except Exception as e:
                self.rejected += 1
                error_writer.writerow([idx + 2, str(e)])
            self.processed += 1

        # Bulk create for performance
        if batch_vals:
            Candidate.create(batch_vals)

        # Save errors CSV so far
        self.errors_csv = base64.b64encode(error_out.getvalue().encode('utf-8'))

        if self.processed >= self.total:
            self.state = 'done'
            self.append_log(f"Completed: imported={self.imported}, rejected={self.rejected}")
        else:
            self.append_log(f"Progress: {self.processed}/{self.total}")

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        self.append_log('Cancelled by user.')

    def action_process_now(self):
        for job in self:
            try:
                # Process in large batches until done or cancelled
                while job.state in ('pending', 'processing'):
                    job._process_job(batch_size=10000)
                    if job.state in ('done', 'error', 'cancelled'):
                        break
            except Exception as e:
                job.write({'state': 'error'})
                job.append_log(f"Error on manual process: {e}")

    def _read_csv_rows(self, data):
        text = data.decode('utf-8-sig', errors='ignore')
        f = StringIO(text)
        reader = csv.DictReader(f)
        return list(reader)

    def _read_xlsx_rows(self, data):
        try:
            import openpyxl
        except Exception:
            # fallback by returning no rows
            return []
        wb = openpyxl.load_workbook(filename=BytesIO(data), read_only=True)
        ws = wb.active
        headers = [str(c.value) if c.value is not None else '' for c in next(ws.rows)]
        rows = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            rows.append({headers[j]: (row[j] if j is not None and j < len(row) else None) for j in range(len(headers))})
        return rows

    def _apply_synonyms(self, rows):
        if not rows:
            return rows
        out = []
        for r in rows:
            new_r = dict(r)
            for key, val in list(r.items()):
                k_upper = str(key or '').strip().upper()
                dst = self.HEADER_SYNONYMS.get(k_upper)
                if dst and dst not in new_r:
                    new_r[dst] = val
            out.append(new_r)
        return out

    def _apply_mapping(self, rows):
        if not self.mapping_json:
            return rows
        try:
            import json
            mapping = json.loads(self.mapping_json)
            # mapping: inputName -> expectedField
            out = []
            for r in rows:
                new_r = dict(r)
                for src, dst in mapping.items():
                    if src in r:
                        new_r[dst] = r.get(src)
                out.append(new_r)
            return out
        except Exception:
            return rows
