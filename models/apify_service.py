from odoo import models, api, _
from odoo.exceptions import UserError
import logging

try:
    from apify_client import ApifyClient
except ImportError:
    ApifyClient = None

_logger = logging.getLogger(__name__)


class SmartRadarApifyService(models.AbstractModel):
    _name = 'alpha.echo.apify.service'
    _description = 'Apify Integration Service'

    @api.model
    def run_list_and_fetch(self, list_id, max_items=100):
        """
        Fetches recent tweets from a Twitter/X List timeline via Apify.
        Uses a SINGLE Actor run for all list members — far cheaper than per-handle scraping.

        Args:
            list_id:   The numeric ID of the X/Twitter List (from the URL)
            max_items: Max tweets to retrieve across all list members
        """
        if not ApifyClient:
            raise UserError(_(
                "⚠️ مكتبة Apify غير مثبتة.\n"
                "يرجى تشغيل: pip install apify-client"
            ))

        if not list_id or not list_id.strip():
            raise UserError(_(
                "⚠️ لم يتم إعداد X/Twitter List ID.\n"
                "يرجى إضافة List ID في الإعدادات (Settings → Alpha Echo → X List ID)."
            ))

        config = self.env['alpha.echo.client.config'].get_singleton()
        token = config.apify_token

        if not token:
            raise UserError(_(
                "⚠️ Apify API Token غير موجود.\n"
                "يرجى إضافته في الإعدادات أو ملف .env"
            ))

        client = ApifyClient(token)
        
        # Support both numeric ID and full URL pasting
        clean_list_id = list_id.strip()
        if 'twitter.com/i/lists/' in clean_list_id or 'x.com/i/lists/' in clean_list_id:
            clean_list_id = clean_list_id.split('lists/')[-1].split('?')[0].strip('/').split('/')[0]
            
        list_url = f"https://twitter.com/i/lists/{clean_list_id}"

        tag_limit = 200 # Fixed explicitly to user's requested 200 value
        
        # Build the exact JSON schema that works with Apify twitter-scraper-lite
        run_input = {
            "includeSearchTerms": False,
            "maxItems": tag_limit,
            "sort": "Latest",
            "startUrls": [list_url],
            "proxyConfig": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
                # Country can be kept generic unless strictly needed
            }
        }
        
        # Inject cookies if stored securely in Odoo Config
        if config.x_auth_token and config.x_ct0:
            run_input["twitterCookies"] = [
                {
                    "domain": ".x.com",
                    "name": "auth_token",
                    "value": config.x_auth_token
                },
                {
                    "domain": ".x.com",
                    "name": "ct0",
                    "value": config.x_ct0
                }
            ]

        _logger.info(
            "Starting Apify scan for X List: %s (max %d items)", list_url, tag_limit
        )

        try:
            run = client.actor("apidojo/twitter-scraper-lite").call(run_input=run_input)

            if not run or not run.get("defaultDatasetId"):
                raise UserError(_(
                    "⚠️ Apify لم يُرجع أي بيانات.\n"
                    "تحقق من صحة الـ List ID والـ Token."
                ))

            results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                tweet_id = str(item.get('id', ''))
                text = item.get('text', '').strip()
                author = item.get('author', {}).get('userName', '')
                url = item.get('url', '')
                created_at = item.get('createdAt', '')

                if not tweet_id or not text or not author:
                    continue

                results.append({
                    'id': tweet_id,
                    'text': text,
                    'author': author,
                    'url': url,
                    'created_at': created_at,
                })

            _logger.info(
                "Apify List scan complete. Retrieved %d tweets from list %s.",
                len(results), list_id
            )
            return results

        except UserError:
            raise
        except Exception as e:
            _logger.error("Apify List scan failed: %s", str(e))
            raise UserError(_(
                "⚠️ فشل الاتصال بـ Apify:\n%s\n\n"
                "تحقق من الـ Token وصحة الـ List ID."
            ) % str(e))

    @api.model
    def fetch_list_members(self, list_id):
        """
        Fetches the actual members of a specific Twitter/X List.
        """
        if not ApifyClient:
            return []

        config = self.env['alpha.echo.client.config'].get_singleton()
        token = config.apify_token
        if not token:
            return []

        client = ApifyClient(token)
        
        # Support both numeric ID and full URL pasting
        clean_list_id = list_id.strip()
        if 'twitter.com/i/lists/' in clean_list_id or 'x.com/i/lists/' in clean_list_id:
            clean_list_id = clean_list_id.split('lists/')[-1].split('?')[0].strip('/').split('/')[0]

        # Using a specialized actor or the same one with a different URL pattern
        list_url = f"https://twitter.com/i/lists/{clean_list_id}/members"
        
        run_input = {
            "startUrls": [list_url],
            "maxItems": 200, # Reasonable limit for list members
        }

        try:
            run = client.actor("apidojo/twitter-scraper-lite").call(run_input=run_input)
            results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                # Extract author info from the nested 'author' object if it's a tweet item
                author_data = item.get('author') if isinstance(item.get('author'), dict) else item
                username = author_data.get('userName') or author_data.get('screen_name') or author_data.get('handle')
                
                if not username:
                    continue
                    
                results.append({
                    'name': author_data.get('name', username),
                    'handle': username.strip().lower().replace('@', ''),
                })
            return results
        except Exception as e:
            _logger.error("Failed to fetch list members: %s", str(e))
            return []
