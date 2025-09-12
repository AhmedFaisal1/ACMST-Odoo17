from datetime import datetime, timedelta
from odoo import api, fields, models


class AdmissionsRateLimit(models.Model):
    _name = 'admissions.rate.limit'
    _description = 'Admissions Rate Limit'
    _rec_name = 'route'

    route = fields.Char(required=True, index=True)
    ip = fields.Char(required=True, index=True)
    created_at = fields.Datetime(default=lambda self: fields.Datetime.now(), index=True)

    @api.model
    def hit(self, route: str, ip: str):
        self.create({'route': route, 'ip': ip})

    @api.model
    def is_limited(self, route: str, ip: str, window_minutes: int, max_hits: int) -> bool:
        since = fields.Datetime.to_string(datetime.utcnow() - timedelta(minutes=window_minutes))
        count = self.search_count([
            ('route', '=', route), ('ip', '=', ip), ('created_at', '>=', since)
        ])
        return count >= max_hits

