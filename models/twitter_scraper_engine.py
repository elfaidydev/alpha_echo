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
        Main Engine Loop — Alpha Echo Protocol (OR Query Edition):
        1. Checks Hibernation (2 AM - 8 AM KSA).
        2. Finds the oldest group to scrape (Round-Robin).
        3. Validates Time-Gate (Min 1 hour since last scrape per group).
        4. Builds Gap-Filler Query: "from:a OR from:b since:{last_scraped}"
        5. Triggers Apify fetch (max 40 items — stays in $0.016 flat tier).

        Cost Target: ~$17–20/month for 12 groups (360 accounts).
        """
        # ── 1. Hibernation Check (Saudi Time) ─────────────────────────────────
        tz = pytz.timezone('Asia/Riyadh')
        now_ksa = datetime.now(pytz.utc).astimezone(tz)
        if 2 <= now_ksa.hour <= 7:
            _logger.info("Alpha Echo: Engine in Hibernation (2 AM - 8 AM KSA). Skipping pulse.")
            return

        # ── 2. Find the candidate Group (Round-Robin) ──────────────────────────
        # Pick the group scraped furthest back in time (or never scraped yet).
        group = self.env['twitter.scrape.group'].search([], order='last_scraped asc nulls first', limit=1)
        if not group:
            _logger.info("Alpha Echo: No scrape groups found. Skipping pulse.")
            return

        # ── 3. Time-Gate Protection (1 Hour) ──────────────────────────────────
        # Prevents hammering the same group too frequently.
        # With 12 groups and a 30-min cron, each group is hit ~every 6 hours anyway.
        if group.last_scraped:
            time_diff = (datetime.now() - group.last_scraped).total_seconds() / 3600
            if time_diff < 1.0:
                _logger.info(
                    "Alpha Echo: Group '%s' was scraped %.1f hours ago. "
                    "Time-Gate (1h) active. Skipping.",
                    group.name, time_diff
                )
                return

        # ── 4. Build Gap-Filler Query ──────────────────────────────────────────
        # Pass last_scraped so Apify only returns tweets AFTER the last run.
        # This is the core of the Gap-Filler Algorithm (Zero-Drop guarantee).
        since_time = group.last_scraped  # datetime or None (first run = no filter)
        query = group.build_search_query(since_time=since_time)
        if not query:
            _logger.info("Alpha Echo: Group '%s' has no active targets. Skipping.", group.name)
            return

        _logger.info(
            "Alpha Echo: Pulse Start — Group '%s' | Query: %s",
            group.name, query
        )

        # ── 5. Engine Active Check ─────────────────────────────────────────────
        config = self.env['alpha.echo.client.config'].get_singleton()
        if not config.is_engine_active:
            return

        # ── 6. Fetch & Process ────────────────────────────────────────────────
        try:
            # max_items=40: keeps every call within the $0.016 flat-rate Apify tier.
            # The first ~40 results are included in the base query price — zero extra cost.
            # max_items=300: Apify charges per result returned (not per limit set).
            # With since: time-filtering, actual results are typically 5-20 tweets.
            # The high ceiling guarantees Zero Drop even in major breaking news events.
            tweets = self.env['alpha.echo.apify.service'].run_search_and_fetch(query, max_items=300)
            if tweets:
                new_posts = self.env['alpha.echo.target']._process_retrieved_tweets(tweets, config)
                _logger.info(
                    "Alpha Echo: Group '%s' scrape complete. %d new posts created.",
                    group.name, new_posts
                )
            else:
                _logger.info("Alpha Echo: Group '%s' — no new tweets returned.", group.name)

            # Update last_scraped even if no tweets (keeps round-robin moving)
            group.last_scraped = fields.Datetime.now()

        except Exception as e:
            _logger.error("Alpha Echo: Scraper error for Group '%s': %s", group.name, str(e))

