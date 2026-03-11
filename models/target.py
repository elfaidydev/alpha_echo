from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
from datetime import datetime, timezone
from dateutil import parser as dateutil_parser

_logger = logging.getLogger(__name__)

# ─── Scan Constants ────────────────────────────────────────────────────────────
MIN_TWEET_LENGTH   = 10   # Skip very short tweets (noise) before touching AI
MAX_POSTS_PER_DAY  = 2000 # Hard daily cap — safety net against runaway scans
MAX_PER_ACCOUNT    = 200  # Max new posts per unique account per scan
MAX_PER_SCAN       = 200  # Max new posts created in a single scan run
# ───────────────────────────────────────────────────────────────────────────────


class SmartRadarTarget(models.Model):
    _name        = 'alpha.echo.target'
    _description = 'Alpha Echo: Target Accounts'
    _rec_name    = 'name'

    # ── Fields ─────────────────────────────────────────────────────────────────
    name         = fields.Char(string=_('Account Name'), required=False)
    handle       = fields.Char(
        string=_('X/Twitter Handle'), required=True, index=True,
        help=_('Lowercase handle without @, e.g. usaidmiddleeast')
    )
    is_active    = fields.Boolean(string=_('Active'), default=True)
    last_scanned = fields.Datetime(string=_('Last Scanned'), readonly=True)
    image_1920   = fields.Image(string=_('Profile Picture'))
    group_id     = fields.Many2one('twitter.scrape.group', string=_('Scrape Group'), ondelete='set null')
    latest_seen_tweet_id = fields.Char(string=_('Latest Seen Tweet ID'), readonly=True, help=_('Highest tweet ID evaluated. Prevents re-sending discarded tweets to AI.'))

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

    # ── Group Automation ────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('handle'):
                vals['handle'] = vals['handle'].strip().lower().replace('@', '')
            if not vals.get('name') and vals.get('handle'):
                vals['name'] = f"@{vals['handle']}"
        records = super().create(vals_list)
        for record in records:
            if not record.group_id:
                record._auto_assign_group()
        return records

    def write(self, vals):
        if 'handle' in vals and vals.get('handle'):
            vals['handle'] = vals['handle'].strip().lower().replace('@', '')
        return super().write(vals)

    def _auto_assign_group(self):
        self.ensure_one()
        groups = self.env['twitter.scrape.group'].search([], order='id asc')
        assigned_group = False
        for g in groups:
            # Cap at 25 accounts per group (not 30).
            # A 30-handle OR query = ~557 chars, exceeding Twitter's 512-char safe limit.
            # 25 handles = ~465 chars, safely under the limit even with since: added.
            if len(g.target_ids) < 25:
                assigned_group = g
                break

        if not assigned_group:
            assigned_group = self.env['twitter.scrape.group'].create({
                'name': f'Scrape Group {len(groups) + 1}'
            })

        self.group_id = assigned_group.id


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




    # ── Core Processing Pipeline ─────────────────────────────────────────────
    @api.model
    def _process_retrieved_tweets(self, tweets, config=None, authorized_handles=None):
        """
        Processes the raw tweet list from Apify through a strict pipeline:

          1. Length filter   — drop noise (< MIN_TWEET_LENGTH chars)
          2. Originals only  — skip retweets, replies, quotes
          3. MEMBER-ONLY     — [GUARDRAIL] Discard any account not in our active targets
          4. Duplicate check — indexed O(1) in-memory lookup
          5. Per-account cap — MAX_PER_ACCOUNT posts per handle
          6. AI classification — ONE OpenAI call per relevant post
          7. Post creation   — savepoint-isolated
        """
        if config is None:
            config = self.env['alpha.echo.client.config'].get_singleton()

        PostObj       = self.env['alpha.echo.post']
        system_prompt = config.custom_ai_instructions
        now_utc       = datetime.now(timezone.utc)

        # ── Pre-load Authorized Handles (Guardrail) ──────────────────────────
        # We only ever process tweets from our designated active targets.
        if authorized_handles is None:
            active_targets = self.search([('is_active', '=', True)])
            authorized_handles = {t.handle.lower().strip() for t in active_targets if t.handle}
            handle_to_target = {t.handle.lower().strip(): t.id for t in active_targets if t.handle}
        else:
            # If handles were passed (optimization), we still need the ID mapping
            authorized_handles = {h.lower().strip() for h in authorized_handles}
            active_targets = self.search([('handle', 'in', list(authorized_handles)), ('is_active', '=', True)])
            handle_to_target = {t.handle.lower().strip(): t.id for t in active_targets}

        # ── Pre-load existing tweet IDs — single query ──────────────────────
        self.env.cr.execute("SELECT source_tweet_id FROM alpha_echo_post WHERE source_tweet_id IS NOT NULL")
        existing_ids: set = {row[0] for row in self.env.cr.fetchall()}

        # ── Today's post count for the daily cap ─────────────────────────────
        today_start  = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        posts_today  = PostObj.search_count([
            ('create_date', '>=', fields.Datetime.to_string(today_start))
        ])

        # Track max seen tweet ID per target to prevent future re-processing
        latest_seen_per_target = {t.id: int(t.latest_seen_tweet_id or 0) for t in active_targets}
        max_seen_per_target = {}

        # ── Counters (for the summary log) ───────────────────────────────────
        new_posts      = 0
        sk_short       = 0   # too short
        sk_retweet     = 0   # retweets
        sk_reply       = 0   # replies
        sk_quote       = 0   # quote tweets
        sk_non_target  = 0   # [GUARDRAIL] unauthorized account
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

            # ── 4. [GUARDRAIL] Strict Target Check ────────────────────────────
            # Never process content from an account not in our 'Active' list.
            # This prevents 'Auto-Discovery' of random accounts in search results.
            author_handle = (tweet.get('author_handle') or '').strip().lower().replace('@', '')
            if not author_handle or author_handle not in authorized_handles:
                sk_non_target += 1
                continue
            
            target_id = handle_to_target.get(author_handle)

            # ── 5. Duplicate check & Highest Seen check ──────────────────────
            tweet_id = str(tweet.get('id', '')).strip()
            if not tweet_id or tweet_id in existing_ids:
                sk_dup += 1
                continue
                
            try:
                tweet_id_int = int(tweet_id)
                # If we've already parsed a tweet this new or newer, completely skip it
                if target_id in latest_seen_per_target and tweet_id_int <= latest_seen_per_target[target_id]:
                    sk_dup += 1
                    continue
                # Track highest id in memory for this batch
                max_seen_per_target[target_id] = max(max_seen_per_target.get(target_id, 0), tweet_id_int)
            except (ValueError, TypeError):
                pass

            # ── 6. Per-account cap ────────────────────────────────────────────
            if account_counts.get(author_handle, 0) >= MAX_PER_ACCOUNT:
                sk_acc_limit += 1
                continue

            # ── 7. AI classify + draft (only now — after all cheap checks) ────
            ai_ok, ai_result = self.env['alpha.echo.openai.service'].classify_and_draft(
                text, system_prompt
            )
            if not ai_ok:
                if ai_result == 'skip':
                    sk_ai += 1
                    existing_ids.add(tweet_id) # memory lockout for this loop iteration
                    continue
                else:
                    err_ai += 1
                    _logger.warning("AI error for tweet %s: %s", tweet_id, ai_result)
                    ai_fetch_failed = True
                    ai_fetch_error = ai_result
                    ai_post_text = ''
                    ai_grant_end_date = None
                    new_post_state = 'failed'
            else:
                ai_fetch_failed = False
                ai_fetch_error = ""
                # ai_result is now a dict: {post_text, grant_end_date}
                ai_post_text = ai_result.get('post_text', '') if isinstance(ai_result, dict) else str(ai_result)
                ai_grant_end_date = ai_result.get('grant_end_date') if isinstance(ai_result, dict) else None
                new_post_state = 'draft'

            # ── 8. Create post (savepoint-isolated) ─────────────────────────
            created_at_str = tweet.get('created_at', '')
            try:
                source_dt = dateutil_parser.parse(created_at_str).replace(tzinfo=None)
            except Exception:
                source_dt = None

            try:
                with self.env.cr.savepoint():
                    ai_text = f"⚠️ SYSTEM ERROR: {ai_fetch_error}" if ai_fetch_failed else ai_post_text

                    create_vals = {
                        'target_id':            target_id,
                        'source_tweet_id':      tweet_id,
                        'source_url':           tweet.get('url') or '',
                        'source_author_handle': author_handle,
                        'source_created_at':    source_dt or fields.Datetime.now(),
                        'original_text':        text,
                        'ai_generated_text':    ai_text,
                        'state':                new_post_state,
                    }
                    if ai_grant_end_date:
                        create_vals['grant_end_date'] = ai_grant_end_date

                    new_post = PostObj.create(create_vals)
                    # Mark as seen immediately (prevents double-processing in same scan)
                    existing_ids.add(tweet_id)
                    new_posts += 1
                    account_counts[author_handle] = account_counts.get(author_handle, 0) + 1

                    # Only auto-approve if AI succeeded
                    if config.auto_approve_drafts and new_post_state == 'draft':
                        new_post.action_publish()

                # Commit immediately so the realtime WebSocket bus pushes this to the frontend
                self.env.cr.commit()

            except Exception as exc:
                err_db += 1
                _logger.error(
                    "Failed to create post for tweet %s (@%s): %s",
                    tweet_id, author_handle, exc
                )

        # ── 9. Final target updates ──────────────────────────────────────────
        for t in active_targets:
            vals = {'last_scanned': fields.Datetime.now()}
            new_max = max_seen_per_target.get(t.id, 0)
            if new_max > latest_seen_per_target.get(t.id, 0):
                vals['latest_seen_tweet_id'] = str(new_max)
            t.write(vals)

        # ── Summary ──────────────────────────────────────────────────────────
        _logger.info(
            "Scan summary — ✅ New: %d | 📏 Short: %d | 🔄 RT: %d | 💬 Reply: %d "
            "| 📝 Quote: %d | 🛡️ Guarded: %d | 🔁 Duplicate: %d | 🚫 AccLimit: %d "
            "| 🤖 AI-skip: %d | ❌ AI-err: %d | 💾 DB-err: %d",
            new_posts, sk_short, sk_retweet, sk_reply,
            sk_quote, sk_non_target, sk_dup, sk_acc_limit,
            sk_ai, err_ai, err_db
        )
        return new_posts
