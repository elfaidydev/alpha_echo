from odoo import models, fields

class TwitterScrapeGroup(models.Model):
    _name = 'twitter.scrape.group'

    name = fields.Char(string='Group Name', required=True)
    last_scraped = fields.Datetime(string='Last Scraped')
    target_ids = fields.One2many('alpha.echo.target', 'group_id', string='Targets')

    def build_search_query(self):
        self.ensure_one()
        active_targets = self.target_ids.filtered(lambda t: t.is_active and t.handle)
        if not active_targets:
            return ""
        return " OR ".join([f"from:{acc.handle}" for acc in active_targets])
