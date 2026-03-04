from odoo import models, api, _
from odoo.exceptions import UserError
import logging
import requests

_logger = logging.getLogger(__name__)

# Maximum items fetched from Apify per scan (cost control hard limit)
MAX_APIFY_ITEMS = 200

# Direct sync endpoint — same as the working Postman call
# Returns results immediately without polling (no async actor lifecycle)
APIFY_SYNC_URL = (
    "https://api.apify.com/v2/acts/apidojo~twitter-scraper-lite"
    "/run-sync-get-dataset-items"
)


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

        Uses the SYNCHRONOUS endpoint (run-sync-get-dataset-items) — identical
        to a cURL/Postman call. No polling, no actor lifecycle, no hanging.

        Args:
            list_id:   Numeric ID of the X/Twitter List (or full URL).
            max_items: Maximum number of tweets to retrieve.

        Returns:
            list of dicts with keys:
              id, text, author_handle, author_name, author_pic,
              url, created_at, is_retweet, is_reply, is_quote, type
        """
        if not list_id or not str(list_id).strip():
            raise UserError(_(
                "⚠️ X/Twitter List ID غير مُعدّ.\n"
                "أضفه في: الإعدادات → Alpha Echo → X List ID."
            ))

        # ── Load credentials ──────────────────────────────────────────────────
        config = self.env['alpha.echo.client.config'].get_singleton()
        
        # VERY IMPORTANT: explicitly cast config fields to strings 
        # to ensure no Odoo ORM wrappers break the JSON serialization
        token = str(config.apify_token or '').strip()
        auth  = str(config.x_auth_token or '').strip()
        ct    = str(config.x_ct0 or '').strip()
        
        if not token:
            raise UserError(_(
                "⚠️ Apify API Token مفقود.\n"
                "أضفه في: الإعدادات → Alpha Echo → API Credentials."
            ))

        # ── Build request body — exactly matching the working Postman call ────
        clean_id = _parse_list_id(str(list_id))
        list_url = f"https://x.com/i/lists/{clean_id}?s=20"
        safe_max = min(int(max_items), MAX_APIFY_ITEMS)

        body = {
            "includeSearchTerms": False,
            "maxItems":           safe_max,
            "sort":               "Latest",
            "startUrls":          [list_url],
            "proxyConfig": {
                "useApifyProxy":      True,
                "apifyProxyGroups":   ["RESIDENTIAL"],
                "apifyProxyCountry":  "SA",
            },
        }

        # Inject session cookies if available in config
        if auth and ct:
            body["twitterCookies"] = [
                {"domain": ".x.com", "name": "auth_token", "value": auth},
                {"domain": ".x.com", "name": "ct0",        "value": ct},
            ]

        _logger.info(
            "Apify sync scan — List: %s | max_items: %d | cookies: %s",
            list_url, safe_max, "yes" if auth else "no"
        )

        # ── Execute — direct HTTP POST, same as Postman ───────────────────────
        try:
            resp = requests.post(
                APIFY_SYNC_URL,
                params={"token": token},
                json=body,
                headers={"User-Agent": "PostmanRuntime/7.36.0", "Accept": "*/*"},
                timeout=300,   # 5-minute hard timeout
            )
        except requests.exceptions.Timeout:
            raise UserError(_(
                "⚠️ انتهت مهلة الاتصال بـ Apify (5 دقائق).\n"
                "تحقق من صحة الـ List ID والـ Token."
            ))
        except requests.exceptions.RequestException as exc:
            _logger.error("Apify HTTP error: %s", exc)
            raise UserError(_("⚠️ خطأ شبكة أثناء الاتصال بـ Apify:\n%s") % str(exc))

        # ── Handle HTTP errors ────────────────────────────────────────────────
        if resp.status_code == 401:
            raise UserError(_("⚠️ Apify Token غير صحيح (401 Unauthorized)."))
        if resp.status_code == 402:
            raise UserError(_("⚠️ رصيد Apify غير كافٍ (402 Payment Required)."))
        if resp.status_code == 429:
            raise UserError(_("⚠️ تم تجاوز حد طلبات Apify (429 Rate Limit). انتظر قليلاً."))
        if not resp.ok:
            raise UserError(_(
                "⚠️ Apify أرجع خطأ HTTP %d:\n%s"
            ) % (resp.status_code, resp.text[:300]))

        # ── Parse response ────────────────────────────────────────────────────
        try:
            raw_items = resp.json()
        except Exception:
            raise UserError(_("⚠️ Apify أرجع استجابة غير قابلة للتحليل:\n%s") % resp.text[:300])

        if not isinstance(raw_items, list):
            raise UserError(_("⚠️ Apify أرجع استجابة غير متوقعة (ليست قائمة)."))

        results = []
        for item in raw_items:
            normalized = _normalize_tweet(item)
            if normalized:
                results.append(normalized)

        _logger.info(
            "Apify sync scan complete — %d usable tweet(s) from List %s.",
            len(results), clean_id
        )
        return results


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
