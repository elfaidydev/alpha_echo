from odoo import models, fields, api
from datetime import datetime
import pytz
import logging

_logger = logging.getLogger(__name__)

class TwitterScraperEngine(models.AbstractModel):
    _name = 'twitter.scraper.engine'
    _description = 'Alpha Echo: Intelligent Search-Based Scraper Engine'

    @api.model
    def run_smart_scraper(self):
        """
        Main Engine Loop:
        1. Checks Hibernation (2 AM - 8 AM KSA).
        2. Finds the oldest group to scrape.
        3. Validates Time-Gate (Min 3 hours since last scrape).
        4. Triggers Search-based Apify fetch.
        """
        # ── 1. Hibernation Check (Saudi Time) ─────────────────────────────────
        tz = pytz.timezone('Asia/Riyadh')
        now_ksa = datetime.now(pytz.utc).astimezone(tz)
        if 2 <= now_ksa.hour <= 7:
            _logger.info("Alpha Echo: Engine in Hibernation (2 AM - 8 AM KSA). Skipping pulse.")
            return

        # ── 2. Find the candidate Group ───────────────────────────────────────
        # We pick the group that was scraped the furthest back in time (or never).
        group = self.env['twitter.scrape.group'].search([], order='last_scraped asc nulls first', limit=1)
        if not group:
            _logger.info("Alpha Echo: No scrape groups found. Skipping pulse.")
            return

        # ── 3. Time-Gate Protection (3 Hours) ─────────────────────────────────
        # This prevents over-spending if only a few groups exist.
        if group.last_scraped:
            time_diff = (datetime.now() - group.last_scraped).total_seconds() / 3600
            if time_diff < 3.0:
                _logger.info("Alpha Echo: Group '%s' was scraped %.1f hours ago. Time-Gate (3h) active. skipping.", group.name, time_diff)
                return

        # ── 4. Build Query & Trigger Scrape ──────────────────────────────────
        query = group.build_search_query()
        if not query:
            _logger.info("Alpha Echo: Group '%s' has no active targets. skipping.", group.name)
            return

        _logger.info("Alpha Echo: Pulse Start - Group '%s' | Query: %s", group.name, query)
        
        # Trigger the real fetch
        # Note: We use the existing processing pipeline in alpha.echo.target
        config = self.env['alpha.echo.client.config'].get_singleton()
        if not config.is_engine_active:
            return

        try:
            # We call the apify service to fetch by search
            # We then pass results to target model for processing
            tweets = self.env['alpha.echo.apify.service'].run_search_and_fetch(query, max_items=100)
            if tweets:
                new_posts = self.env['alpha.echo.target']._process_retrieved_tweets(tweets, config)
                _logger.info("Alpha Echo: Group '%s' scrape complete. %d new posts created.", group.name, new_posts)
            
            # Update last_scraped even if no tweets found to keep the cycle moving
            group.last_scraped = fields.Datetime.now()
            
        except Exception as e:
            _logger.error("Alpha Echo: Scraper error for Group '%s': %s", group.name, str(e))
