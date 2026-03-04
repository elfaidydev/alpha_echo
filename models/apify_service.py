from odoo import models, api, _
from odoo.exceptions import UserError
import logging

try:
    from apify_client import ApifyClient
except ImportError:
    ApifyClient = None

_logger = logging.getLogger(__name__)

# Maximum items fetched from Apify per scan (cost control hard limit)
MAX_APIFY_ITEMS = 200


def _parse_list_id(raw: str) -> str:
    """Extract the numeric List ID from either a raw ID or a full URL."""
    raw = raw.strip()
    if 'lists/' in raw:
        raw = raw.split('lists/')[-1].split('?')[0].strip('/').split('/')[0]
    return raw


class SmartRadarApifyService(models.AbstractModel):
    _name        = 'alpha.echo.apify.service'
    _description = 'Apify Integration Service'

    @api.model
    def run_list_and_fetch(self, list_id: str, max_items: int = MAX_APIFY_ITEMS) -> list:
        """
        Fetch the most-recent tweets from a Twitter/X List timeline via Apify.

        Uses a SINGLE actor run for the entire list — far cheaper than
        per-handle scraping. Returns a normalized list of tweet dicts.

        Args:
            list_id:   Numeric ID of the X/Twitter List (or full URL).
            max_items: Maximum number of tweets to retrieve (capped at MAX_APIFY_ITEMS).

        Returns:
            list of dicts with keys:
              id, text, author_handle, author_name, author_pic,
              url, created_at, is_retweet, is_reply, is_quote, type
        """
        # ── Guard: library available? ─────────────────────────────────────────
        if not ApifyClient:
            raise UserError(_(
                "⚠️ مكتبة Apify غير مثبتة.\n"
                "يرجى تشغيل: pip install apify-client"
            ))

        if not list_id or not str(list_id).strip():
            raise UserError(_(
                "⚠️ X/Twitter List ID غير مُعدّ.\n"
                "أضفه في: الإعدادات → Alpha Echo → X List ID."
            ))

        # ── Load credentials ──────────────────────────────────────────────────
        config = self.env['alpha.echo.client.config'].get_singleton()
        token  = config.apify_token
        if not token:
            raise UserError(_(
                "⚠️ Apify API Token مفقود.\n"
                "أضفه في: الإعدادات → Alpha Echo → API Credentials."
            ))

        # ── Build inputs ──────────────────────────────────────────────────────
        clean_id = _parse_list_id(str(list_id))
        list_url = f"https://twitter.com/i/lists/{clean_id}"

        # Keep max_items within the allowed ceiling
        safe_max = min(int(max_items), MAX_APIFY_ITEMS)

        run_input = {
            "includeSearchTerms": False,
            "maxItems":           safe_max,
            "sort":               "Latest",
            "startUrls":          [list_url],
            "proxyConfig": {
                "useApifyProxy":      True,
                "apifyProxyGroups":   ["DATACENTER"],
            },
        }

        # Inject session cookies if stored (improves scraping reliability)
        if config.x_auth_token and config.x_ct0:
            run_input["twitterCookies"] = [
                {"domain": ".x.com", "name": "auth_token", "value": config.x_auth_token},
                {"domain": ".x.com", "name": "ct0",        "value": config.x_ct0},
            ]

        _logger.info("Apify scan — List: %s | max_items: %d", list_url, safe_max)

        # ── Execute ───────────────────────────────────────────────────────────
        try:
            client = ApifyClient(token)
            run    = client.actor("apidojo/twitter-scraper-lite").call(run_input=run_input)

            if not run or not run.get("defaultDatasetId"):
                raise UserError(_(
                    "⚠️ Apify لم يُرجع أي بيانات.\n"
                    "تحقق من صحة الـ List ID والـ Token."
                ))

            results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                normalized = _normalize_tweet(item)
                if normalized:
                    results.append(normalized)

            _logger.info("Apify scan complete — %d usable tweet(s) from List %s.",
                         len(results), clean_id)
            return results

        except UserError:
            raise   # re-raise our own friendly errors as-is
        except Exception as exc:
            _logger.error("Apify scan failed: %s", exc)
            raise UserError(_(
                "⚠️ فشل الاتصال بـ Apify:\n%s\n\n"
                "تحقق من الـ Token وصحة الـ List ID."
            ) % str(exc))


def _normalize_tweet(item: dict) -> dict | None:
    """
    Convert a raw Apify tweet item into a clean, normalized dict.
    Returns None for items that lack required fields.
    """
    tweet_id = str(item.get('id', '')).strip()
    # fullText contains the untruncated body; fall back to text
    text     = (item.get('fullText') or item.get('text') or '').strip()

    # Author is a nested object from the Apify schema
    author_raw = item.get('author', {})
    if isinstance(author_raw, dict):
        author_handle = author_raw.get('userName', '').strip()
        author_name   = author_raw.get('name', author_handle)
        author_pic    = author_raw.get('profilePicture', '')
    else:
        author_handle = str(author_raw).strip()
        author_name   = author_handle
        author_pic    = ''

    # Drop items without the bare minimum fields
    if not tweet_id or not text or not author_handle:
        return None

    return {
        'id':            tweet_id,
        'text':          text,
        'author_handle': author_handle,
        'author_name':   author_name,
        'author_pic':    author_pic,
        'url':           item.get('url', ''),
        'created_at':    item.get('createdAt', ''),
        'is_retweet':    bool(item.get('isRetweet', False)),
        'is_reply':      bool(item.get('isReply',   False)),
        'is_quote':      bool(item.get('isQuote',   False)),
        'type':          str(item.get('type', 'tweet')).lower(),
    }
