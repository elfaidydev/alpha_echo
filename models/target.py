from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from datetime import datetime, timezone
from dateutil import parser as dateutil_parser

_logger = logging.getLogger(__name__)

# ─── Scan Constants ────────────────────────────────────────────────────────────
MIN_TWEET_LENGTH   = 50   # Skip very short tweets (noise) before touching AI
MAX_POSTS_PER_DAY  = 300  # Hard daily cap — safety net against runaway scans
MAX_PER_ACCOUNT    = 20   # Max new posts per unique account per scan
MAX_PER_SCAN       = 10   # Max new posts created in a single scan run
# ───────────────────────────────────────────────────────────────────────────────


class SmartRadarTarget(models.Model):
    _name        = 'alpha.echo.target'
    _description = 'Alpha Echo: Discovered Accounts from X List'
    _rec_name    = 'name'

    # ── Fields ─────────────────────────────────────────────────────────────────
    name         = fields.Char(string=_('Account Name'), required=True)
    handle       = fields.Char(
        string=_('X/Twitter Handle'), required=True, index=True,
        help=_('Lowercase handle without @, e.g. usaidmiddleeast')
    )
    is_active    = fields.Boolean(string=_('Active'), default=True)
    last_scanned = fields.Datetime(string=_('Last Scanned'), readonly=True)
    image_1920   = fields.Image(string=_('Profile Picture'))

    post_ids     = fields.One2many('alpha.echo.post', 'target_id', string=_('Posts'))
    posts_count  = fields.Integer(
        compute='_compute_posts_count', string=_('Posts Found'), store=False
    )

    _sql_constraints = [
        ('handle_unique', 'unique(handle)',
         'This Twitter handle already exists — duplicates are not allowed.')
    ]

    # ── Computed ────────────────────────────────────────────────────────────────
    @api.depends('post_ids')
    def _compute_posts_count(self):
        for record in self:
            record.posts_count = len(record.post_ids)

    # ── Actions ─────────────────────────────────────────────────────────────────
    def action_view_posts(self):
        self.ensure_one()
        return {
            'name':      _('Posts'),
            'res_model': 'alpha.echo.post',
            'view_mode': 'tree,form',
            'domain':    [('target_id', '=', self.id)],
            'context':   {'default_target_id': self.id},
            'type':      'ir.actions.act_window',
        }

    # ── Target Discovery ────────────────────────────────────────────────────────
    @api.model
    def _get_or_create_target(self, author_handle, name=None, profile_pic=None):
        """
        Find-or-create a Target by handle. Safe against race conditions via
        savepoint. Updates name/pic if they were missing on a previous run.

        Returns: target record or False
        """
        if not author_handle:
            return False

        handle_clean = author_handle.strip().lower().replace('@', '')

        # Fast path: already exists
        target = self.search([('handle', '=', handle_clean)], limit=1)
        if target:
            # Opportunistically update name/pic if still empty
            updates = {}
            if name and target.name == target.handle:
                updates['name'] = name
            if updates:
                target.write(updates)
            return target

        # Slow path: create with savepoint for concurrency safety
        try:
            with self.env.cr.savepoint():
                target = self.create({
                    'name':     name or author_handle,
                    'handle':   handle_clean,
                    'is_active': True,
                })
                _logger.info("Auto-discovered new target: @%s (%s)", handle_clean, name or '')
                return target
        except Exception:
            # Unique constraint violated — another process just created the same handle.
            _logger.debug("Concurrent target creation for @%s, fetching existing.", handle_clean)
            return self.search([('handle', '=', handle_clean)], limit=1)

    # ── Deduplication Utility ─────────────────────────────────────────────────
    @api.model
    def action_deduplicate_targets(self):
        """
        One-time cleanup tool: merges duplicate targets (same handle).
        Keeps the oldest record, re-assigns all posts to it.
        """
        self.env.cr.execute("""
            SELECT handle FROM alpha_echo_target
            GROUP BY handle HAVING COUNT(id) > 1
        """)
        duplicate_handles = [r[0] for r in self.env.cr.fetchall()]

        merged = 0
        for handle in duplicate_handles:
            targets = self.search([('handle', '=', handle)], order='id asc')
            master     = targets[0]
            duplicates = targets[1:]
            for dup in duplicates:
                self.env['alpha.echo.post'].search(
                    [('target_id', '=', dup.id)]
                ).write({'target_id': master.id})
                dup.unlink()
                merged += 1

        _logger.info("Deduplication complete — merged %d duplicate target(s).", merged)
        return {'merged': merged}

    # ── Cron Entry Point ─────────────────────────────────────────────────────
    @api.model
    def cron_fetch_all_targets(self):
        """
        Cron entry point (every 90 min).
        Validates config → acquires lock → fetches Apify → processes tweets.
        """
        config = self.env['alpha.echo.client.config'].get_singleton()

        # ── Pre-flight checks ─────────────────────────────────────────────────
        if not config.is_engine_active:
            _logger.info("Alpha Echo engine is inactive — scan skipped.")
            return

        if not config.x_list_id:
            raise UserError(_(
                "⚠️ X/Twitter List ID غير مُعدّ.\n"
                "أضفه في: الإعدادات → Alpha Echo → X List ID."
            ))

        if not config.apify_token:
            raise UserError(_(
                "⚠️ Apify Token مفقود.\n"
                "أضفه في الإعدادات."
            ))

        if not config.custom_ai_instructions:
            raise UserError(_(
                "⚠️ System Prompt للـ AI غير مكتوب.\n"
                "أكتبه في الإعدادات قبل تشغيل الـ Scan."
            ))

        if not config.openai_api_key:
            raise UserError(_(
                "⚠️ OpenAI API Key مفقود.\n"
                "أضفه في الإعدادات."
            ))

        # ── Concurrency lock (prevents parallel Apify runs = cost control) ───
        LOCK_KEY = 'alpha_echo.scan_in_progress'
        params   = self.env['ir.config_parameter'].sudo()

        if params.get_param(LOCK_KEY) == 'true':
            _logger.warning("Scan already running — skipping to prevent duplicate Apify cost.")
            return

        try:
            params.set_param(LOCK_KEY, 'true')
            self.env.cr.commit()   # Persist lock before any blocking I/O

            _logger.info("Alpha Echo scan starting — List ID: %s", config.x_list_id)

            tweets = self.env['alpha.echo.apify.service'].run_list_and_fetch(
                config.x_list_id, max_items=200
            )

            if tweets:
                new_count = self._process_retrieved_tweets(tweets, config)
                _logger.info("Scan complete — %d new post(s) created.", new_count)
            else:
                _logger.info("Scan complete — Apify returned 0 tweets.")

        finally:
            # Always release lock, even if an exception occurred
            try:
                params.set_param(LOCK_KEY, 'false')
                self.env.cr.commit()
            except Exception:
                _logger.warning(
                    "Could not release lock '%s' — transaction may be poisoned. "
                    "It will auto-clear on the next cron run.",
                    LOCK_KEY
                )
                self.env.cr.rollback()

    # ── Core Processing Pipeline ─────────────────────────────────────────────
    @api.model
    def _process_retrieved_tweets(self, tweets, config=None):
        """
        Processes the raw tweet list from Apify through a strict pipeline:

          1. Length filter  — drop noise (< MIN_TWEET_LENGTH chars)
          2. Original-only  — skip retweets, replies, quotes
          3. Duplicate check — pre-loaded set, O(1) lookup, ZERO extra DB queries
          4. Author check   — extract handle; skip if missing
          5. Per-account cap — MAX_PER_ACCOUNT posts per handle per scan
          6. AI classify + draft — ONE OpenAI call per relevant tweet
          7. Post create    — savepoint-isolated, with target auto-discovery
          8. Auto-publish   — if config.auto_approve_drafts is True

        Cost optimisation:
          • Duplicate tweet IDs are loaded in a SINGLE query before the loop.
          • AI is called ONLY after ALL cheaper checks pass.
          • Newly created post IDs are added to the in-memory set immediately,
            so the same tweet can never be sent to AI twice in one scan.
        """
        if config is None:
            config = self.env['alpha.echo.client.config'].get_singleton()

        PostObj       = self.env['alpha.echo.post']
        system_prompt = config.custom_ai_instructions
        now_utc       = datetime.now(timezone.utc)

        # ── Pre-load existing tweet IDs — single query, O(1) duplicate lookups ──
        self.env.cr.execute("SELECT source_tweet_id FROM alpha_echo_post WHERE source_tweet_id IS NOT NULL")
        existing_ids: set = {row[0] for row in self.env.cr.fetchall()}

        # ── Today's post count for the daily cap ─────────────────────────────
        today_start  = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        posts_today  = PostObj.search_count([
            ('create_date', '>=', fields.Datetime.to_string(today_start))
        ])

        # ── Counters (for the summary log) ───────────────────────────────────
        new_posts      = 0
        sk_short       = 0   # too short
        sk_retweet     = 0   # retweets
        sk_reply       = 0   # replies
        sk_quote       = 0   # quote tweets
        sk_dup         = 0   # already in DB
        sk_no_author   = 0   # missing author handle
        sk_acc_limit   = 0   # per-account cap hit
        sk_ai          = 0   # AI classified as not-relevant
        err_ai         = 0   # AI call failed (technical error)
        err_db         = 0   # DB create failed

        account_counts: dict = {}   # handle → count of posts created this scan

        for tweet in tweets:

            # ── Hard caps ────────────────────────────────────────────────────
            if new_posts >= MAX_PER_SCAN:
                _logger.info("Per-scan limit (%d) reached — stopping.", MAX_PER_SCAN)
                break
            if (posts_today + new_posts) >= MAX_POSTS_PER_DAY:
                _logger.warning("Daily limit (%d) reached — stopping.", MAX_POSTS_PER_DAY)
                break

            # ── 1. Length filter (cheapest possible check) ────────────────────
            text = (tweet.get('text') or '').strip()
            if len(text) < MIN_TWEET_LENGTH:
                sk_short += 1
                continue

            # ── 2. Originals-only gate ────────────────────────────────────────
            if tweet.get('is_retweet'):
                sk_retweet += 1
                continue
            if tweet.get('is_reply'):
                sk_reply += 1
                continue
            if tweet.get('is_quote'):
                sk_quote += 1
                continue
            if tweet.get('type', '').lower() not in ('tweet', ''):
                sk_quote += 1   # treat as non-original
                continue

            # ── 3. Duplicate check — O(1) in-memory, ZERO DB queries ─────────
            tweet_id = str(tweet.get('id', '')).strip()
            if not tweet_id or tweet_id in existing_ids:
                sk_dup += 1
                continue

            # ── 4. Author extraction ──────────────────────────────────────────
            author_handle = tweet.get('author_handle', '').strip()
            if not author_handle:
                sk_no_author += 1
                continue
            author_name    = tweet.get('author_name', author_handle)
            author_pic     = tweet.get('author_pic', '')
            author_clean   = author_handle.lower().replace('@', '')

            # ── 5. Per-account cap ────────────────────────────────────────────
            if account_counts.get(author_clean, 0) >= MAX_PER_ACCOUNT:
                sk_acc_limit += 1
                continue

            # ── 6. AI classify + draft (only now — after all cheap checks) ────
            ai_ok, ai_result = self.env['alpha.echo.openai.service'].classify_and_draft(
                text, system_prompt
            )
            if not ai_ok:
                if ai_result == 'skip':
                    sk_ai += 1
                else:
                    err_ai += 1
                    _logger.warning("AI error for tweet %s: %s", tweet_id, ai_result)
                continue

            # ── 7. Resolve / create target ──────────────────────────────────
            target = self._get_or_create_target(
                author_handle, name=author_name, profile_pic=author_pic
            )
            if not target:
                sk_no_author += 1
                continue

            # ── 8. Create post (savepoint-isolated) ─────────────────────────
            created_at_str = tweet.get('created_at', '')
            try:
                source_dt = dateutil_parser.parse(created_at_str).replace(tzinfo=None)
            except Exception:
                source_dt = None

            try:
                with self.env.cr.savepoint():
                    new_post = PostObj.create({
                        'target_id':            target.id,
                        'source_tweet_id':      tweet_id,
                        'source_url':           tweet.get('url') or '',
                        'source_author_handle': author_handle,
                        'source_created_at':    source_dt or fields.Datetime.now(),
                        'original_text':        text,
                        'ai_generated_text':    ai_result,
                        'state':                'draft',
                    })
                    # Mark as seen immediately (prevents double-processing in same scan)
                    existing_ids.add(tweet_id)
                    new_posts += 1
                    account_counts[author_clean] = account_counts.get(author_clean, 0) + 1
                    target.write({'last_scanned': fields.Datetime.now()})

                    if config.auto_approve_drafts:
                        new_post.action_publish()

            except Exception as exc:
                err_db += 1
                _logger.error(
                    "Failed to create post for tweet %s (@%s): %s",
                    tweet_id, author_handle, exc
                )

        # ── Summary ──────────────────────────────────────────────────────────
        _logger.info(
            "Scan summary — ✅ New: %d | 📏 Short: %d | 🔄 RT: %d | 💬 Reply: %d "
            "| 📝 Quote: %d | 🔁 Duplicate: %d | 👤 No-author: %d | 🚫 AccLimit: %d "
            "| 🤖 AI-skip: %d | ❌ AI-err: %d | 💾 DB-err: %d",
            new_posts, sk_short, sk_retweet, sk_reply,
            sk_quote, sk_dup, sk_no_author, sk_acc_limit,
            sk_ai, err_ai, err_db
        )
        return new_posts
