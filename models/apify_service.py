from odoo import models, api, _
from odoo.exceptions import UserError
import logging
import requests

_logger = logging.getLogger(__name__)

# Maximum items typically expected per search pulse (for safety)
MAX_ITEMS_SOFT_LIMIT = 150

# Direct sync endpoint — returns results immediately
APIFY_SYNC_URL = (
    "https://api.apify.com/v2/acts/apidojo~twitter-scraper-lite"
    "/run-sync-get-dataset-items"
)


class SmartRadarApifyService(models.AbstractModel):
    _name        = 'alpha.echo.apify.service'
    _description = 'Alpha Echo: Apify Search Service'


    @api.model
    def run_search_and_fetch(self, query: str, max_items: int = 150) -> list:
        """
        Fetch tweets using Advanced Search terms (OR queries).
        Uses the synchronous endpoint for immediate response.

        Args:
            query: The X Search Query (e.g. 'from:user1 OR from:user2')
            max_items: Max tweets to retrieve (standardized to 100).
        """
        config = self.env['alpha.echo.client.config'].get_singleton()
        token = str(config.apify_token or '').strip()
        auth  = str(config.x_auth_token or '').strip()
        ct    = str(config.x_ct0 or '').strip()

        if not token:
            raise UserError(_("⚠️ Apify API Token is missing."))

        body = {
            "searchTerms":        [query],
            "sort":               "Latest",
            "maxItems":           int(max_items),
            "includeSearchTerms": False,
            "proxyConfig": {
                "useApifyProxy":      True,
                "apifyProxyGroups":   ["RESIDENTIAL"],
                "apifyProxyCountry":  "SA",
            },
        }

        if auth and ct:
            body["twitterCookies"] = [
                {"domain": ".x.com", "name": "auth_token", "value": auth},
                {"domain": ".x.com", "name": "ct0",        "value": ct},
            ]

        _logger.info("Apify Search Pulse — Query: %s | max_items: %d", query, max_items)

        try:
            resp = requests.post(
                APIFY_SYNC_URL,
                params={"token": token},
                json=body,
                headers={"User-Agent": "PostmanRuntime/7.36.0", "Accept": "*/*"},
                timeout=300,
            )
            if not resp.ok:
                raise UserError(_("Apify Search Error: %s") % resp.text[:300])

            raw_items = resp.json()
            results = []
            for item in raw_items:
                normalized = _normalize_tweet(item)
                if normalized:
                    results.append(normalized)
            return results

        except Exception as e:
            _logger.error("Apify Search Request Failed: %s", str(e))
            return []


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
