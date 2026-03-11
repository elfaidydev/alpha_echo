from odoo import models, fields

class TwitterScrapeGroup(models.Model):
    _name = 'twitter.scrape.group'
    _description = 'Alpha Echo: Twitter Scrape Group'

    name = fields.Char(string='Group Name', required=True)
    last_scraped = fields.Datetime(string='Last Scraped')
    target_ids = fields.One2many('alpha.echo.target', 'group_id', string='Targets')

    def build_search_query(self, since_time=None):
        """
        Builds an Advanced Twitter Search query for all active targets in the group.

        Args:
            since_time (datetime, optional): If provided, appends a `since:` filter
                so the query only returns tweets AFTER the last successful scrape.
                This is the core of the Gap-Filler Algorithm — ensures zero data loss.

        Returns:
            str: A ready-to-use Twitter search query string, e.g.:
                 "from:acc1 OR from:acc2 since:2026-03-10_18:30:00_UTC"
        """
        self.ensure_one()
        active_targets = self.target_ids.filtered(lambda t: t.is_active and t.handle)
        if not active_targets:
            return ""

        base_query = " OR ".join([f"from:{acc.handle}" for acc in active_targets])

        # ── Gap-Filler: append `since:` to avoid re-fetching old tweets ─────
        if since_time:
            # Format: YYYY-MM-DD_HH:MM:SS_UTC (Twitter Advanced Search syntax)
            since_str = since_time.strftime("%Y-%m-%d_%H:%M:%S_UTC")
            base_query = f"{base_query} since:{since_str}"

        return base_query
