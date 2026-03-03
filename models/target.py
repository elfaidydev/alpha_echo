from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from datetime import datetime, timezone, timedelta

_logger = logging.getLogger(__name__)

# Hardcoded system constants
SCAN_AGE_HOURS = 1.6     # Coverage slightly more than 90m to ensure overlap/zero gaps
MIN_TWEET_LENGTH = 50    # Skip very short tweets before AI
MAX_POSTS_PER_DAY = 300  # High daily limit for Zero-Miss strategy
MAX_PER_ACCOUNT_PER_SCAN = 20 # High limit to ensure we don't miss multiple grants from one account


class SmartRadarTarget(models.Model):
    _name = 'alpha.echo.target'
    _description = 'Alpha Echo: Discovered Accounts from X List'
    _rec_name = 'name'

    name = fields.Char(string=_('Account Name'), required=True)
    handle = fields.Char(string=_('X/Twitter Handle'), required=True, help=_('e.g. USAIDMiddleEast'))
    is_active = fields.Boolean(string=_('Active'), default=True)
    last_scanned = fields.Datetime(string=_('Last Scanned'), readonly=True)

    image_1920 = fields.Image(string=_("Logo"))
    post_ids = fields.One2many('alpha.echo.post', 'target_id', string=_("Posts"))
    posts_count = fields.Integer(compute='_compute_posts_count', string=_('Posts Found'))

    @api.depends('post_ids')
    def _compute_posts_count(self):
        for record in self:
            record.posts_count = len(record.post_ids)

    def action_view_posts(self):
        self.ensure_one()
        return {
            'name': _('Posts'),
            'res_model': 'alpha.echo.post',
            'view_mode': 'tree,form',
            'domain': [('target_id', '=', self.id)],
            'context': {'default_target_id': self.id},
            'type': 'ir.actions.act_window',
        }

    @api.model
    def _get_or_create_target(self, author_handle, name=None):
        """
        Auto-discover: find existing target by handle or create a new one.
        Now supports optional display name.
        """
        if not author_handle:
            return False
            
        handle_clean = author_handle.strip().lower().replace('@', '')
        target = self.search([('handle', '=', handle_clean)], limit=1)
        
        if not target:
            target = self.create({
                'name': name or author_handle,
                'handle': handle_clean,
                'is_active': True,
            })
            _logger.info("Auto-discovered new target: @%s", handle_clean)
        elif name and target.name == target.handle:
            # Update name if we only had the handle before
            target.write({'name': name})
            
        return target

    @api.model
    def cron_fetch_all_targets(self):
        """Called by Odoo Cron every 3 hours. Fetches tweets from the X List."""
        config = self.env['alpha.echo.client.config'].get_singleton()

        if not config.is_engine_active:
            _logger.info("Alpha Echo engine is inactive. Skipping scan.")
            return

        if not config.x_list_id:
            raise UserError(_(
                "⚠️ X/Twitter List ID غير موجود.\n"
                "يرجى إضافته في الإعدادات: Settings → Alpha Echo → X List ID."
            ))

        if not config.apify_token:
            raise UserError(_(
                "⚠️ Apify Token غير موجود.\n"
                "يرجى إضافته في الإعدادات أو ملف .env"
            ))

        if not config.custom_ai_instructions:
            raise UserError(_(
                "⚠️ لم يُكتب System Prompt بعد.\n"
                "يرجى كتابة تعليمات الـ AI في الإعدادات قبل تشغيل الـ Scan."
            ))

        _logger.info("Alpha Echo Scan started using List ID: %s", config.x_list_id)

        # Single Apify run → Fetch 1000 items to ensure ZERO miss for 350 accounts
        tweets = self.env['alpha.echo.apify.service'].run_list_and_fetch(
            config.x_list_id, max_items=1000
        )

        if tweets:
            new_count = self._process_retrieved_tweets(tweets, config)
            _logger.info("Scan complete. %d new posts created.", new_count)
        else:
            _logger.info("Scan complete. No tweets returned from List.")

    @api.model
    def _process_retrieved_tweets(self, tweets, config=None):
        """
        Processes tweets from the List timeline:
          1. Age filter (ignore > SCAN_AGE_HOURS)
          2. Length filter (< MIN_TWEET_LENGTH)
          3. Duplicate check
          4. Auto-create target if new account discovered
          5. AI classify + draft (single call)
          6. Hard daily post cap (MAX_POSTS_PER_DAY)
          7. Auto-publish if enabled
        """
        if config is None:
            config = self.env['alpha.echo.client.config'].get_singleton()

        system_prompt = config.custom_ai_instructions
        PostObj = self.env['alpha.echo.post']
        now_utc = datetime.now(timezone.utc)
        cutoff_time = now_utc - timedelta(hours=SCAN_AGE_HOURS)

        # Count today's posts for the hard cap
        today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        posts_today = PostObj.search_count([
            ('create_date', '>=', fields.Datetime.to_string(today_start))
        ])

        new_posts_count = 0
        skipped_old = skipped_short = skipped_duplicate = skipped_ai = ai_errors = skipped_limit = 0
        
        # Track counts per account for this specific scan
        account_scan_counts = {}

        for tweet in tweets:
            # Hard daily cap
            if (posts_today + new_posts_count) >= MAX_POSTS_PER_DAY:
                _logger.warning("Daily limit (%d) reached. Stopping.", MAX_POSTS_PER_DAY)
                break

            # 1. Age filter
            created_at_str = tweet.get('created_at', '')
            if created_at_str:
                try:
                    tweet_time = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    if tweet_time < cutoff_time:
                        skipped_old += 1
                        continue
                except (ValueError, TypeError):
                    pass

            # 2. Length filter
            text = tweet.get('text', '').strip()
            if len(text) < MIN_TWEET_LENGTH:
                skipped_short += 1
                continue

            # 3. Duplicate check
            tweet_id = tweet.get('id', '')
            if PostObj.search_count([('source_tweet_id', '=', tweet_id)]):
                skipped_duplicate += 1
                continue

            # 4. Auto-discover target from tweet author
            author = tweet.get('author', '').strip()
            if not author:
                continue
            
            # Per-account limit check for this scan
            author_key = author.lower()
            if account_scan_counts.get(author_key, 0) >= MAX_PER_ACCOUNT_PER_SCAN:
                skipped_limit += 1
                continue

            target = self._get_or_create_target(author)

            # 5. AI classify + draft (one call)
            success, result = self.env['alpha.echo.openai.service'].classify_and_draft(
                text, system_prompt
            )

            if not success:
                if result == 'skip':
                    skipped_ai += 1
                else:
                    ai_errors += 1
                    _logger.warning("AI error for tweet %s: %s", tweet_id, result)
                continue

            # 6. Create post
            try:
                new_post = PostObj.create({
                    'target_id': target.id,
                    'source_tweet_id': tweet_id,
                    'source_url': tweet.get('url', ''),
                    'source_author_handle': author,
                    'source_created_at': created_at_str[:19].replace('T', ' ') if created_at_str else False,
                    'original_text': text,
                    'ai_generated_text': result,
                    'state': 'draft',
                })
                new_posts_count += 1
                account_scan_counts[author_key] = account_scan_counts.get(author_key, 0) + 1

                # Update last_scanned for this target
                target.write({'last_scanned': fields.Datetime.now()})

                # 7. Auto-publish if enabled
                if config.auto_approve_drafts:
                    new_post.action_publish()

            except Exception as e:
                _logger.error("Failed to create post for tweet %s: %s", tweet_id, str(e))

        _logger.info(
            "Processing summary — ✅ New: %d | ⏰ Old: %d | 📏 Short: %d "
            "| 🔁 Duplicate: %d | 🤖 AI skipped: %d | ❌ AI errors: %d | 🚫 Per-Acc Limit: %d",
            new_posts_count, skipped_old, skipped_short,
            skipped_duplicate, skipped_ai, ai_errors, skipped_limit
        )
        return new_posts_count
