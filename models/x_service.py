from odoo import models, api, _
from odoo.exceptions import UserError
import logging

try:
    import tweepy
except ImportError:
    tweepy = None

_logger = logging.getLogger(__name__)

X_CHAR_LIMIT = 280


class SmartRadarXService(models.AbstractModel):
    _name = 'alpha.echo.x.service'
    _description = 'X (Twitter) Integration Service'

    @api.model
    def _get_client(self):
        """Helper to get tweepy client authenticated with DB credentials."""
        if not tweepy:
            return None, _(
                "⚠️ مكتبة Tweepy غير مثبتة على الخادم.\n"
                "يرجى تشغيل: pip install tweepy"
            )

        config = self.env['alpha.echo.client.config'].get_singleton()

        missing = []
        if not config.x_api_key:
            missing.append("API Key")
        if not config.x_api_secret:
            missing.append("API Secret")
        if not config.x_access_token:
            missing.append("Access Token")
        if not config.x_access_token_secret:
            missing.append("Access Token Secret")

        if missing:
            return None, _(
                "⚠️ بيانات X (Twitter) ناقصة: %s\n"
                "يرجى إكمالها في الإعدادات."
            ) % ", ".join(missing)

        try:
            client = tweepy.Client(
                consumer_key=config.x_api_key,
                consumer_secret=config.x_api_secret,
                access_token=config.x_access_token,
                access_token_secret=config.x_access_token_secret
            )
            return client, None
        except Exception as e:
            _logger.error("Failed to initialize tweepy client: %s", str(e))
            return None, _("⚠️ فشل الاتصال بـ X: %s") % str(e)

    @api.model
    def test_connection(self):
        """Test Twitter API credentials and return account info."""
        client, error = self._get_client()
        if error:
            return {'success': False, 'error': error}

        try:
            user_info = client.get_me(user_fields=['profile_image_url', 'username'])
            if user_info and user_info.data:
                _logger.info(
                    "X connection test successful for @%s.", user_info.data.username
                )
                return {
                    'success': True,
                    'name': user_info.data.name,
                    'username': user_info.data.username,
                    'profile_image_url': user_info.data.profile_image_url
                }
            return {'success': False, 'error': _("⚠️ تعذر استرداد معلومات الحساب من X.")}

        except Exception as e:
            _logger.error("X connection test failed: %s", str(e))
            return {'success': False, 'error': _("⚠️ فشل اختبار الاتصال بـ X: %s") % str(e)}

    @api.model
    def publish_tweet(self, text):
        """
        Publish a tweet using Twitter v2 API.
        Returns (True, tweet_url) on success, or (False, error_message) on failure.
        """
        if not text or not text.strip():
            return False, _("⚠️ نص التغريدة فارغ — لا يمكن النشر.")

        if len(text) > X_CHAR_LIMIT:
            return False, _(
                "⚠️ النص يتجاوز حد X/Twitter (%d حرف). الحجم الحالي: %d حرف.\n"
                "يرجى تقصير النص قبل النشر."
            ) % (X_CHAR_LIMIT, len(text))

        client, error = self._get_client()
        if error:
            return False, error

        try:
            response = client.create_tweet(text=text)
            tweet_id = response.data.get('id')

            # Fetch username for constructing the tweet URL
            user_info = client.get_me()
            username = user_info.data.username if user_info and user_info.data else 'i'
            tweet_url = "https://twitter.com/%s/status/%s" % (username, tweet_id)

            _logger.info("Tweet published successfully: %s", tweet_url)
            return True, tweet_url

        except Exception as e:
            error_str = str(e)
            _logger.error("Tweet publish failed: %s", error_str)

            if '403' in error_str:
                return False, _(
                    "⚠️ رُفض النشر (403 Forbidden).\n"
                    "تحقق من أن تطبيق X لديه صلاحية الكتابة (Read & Write)."
                )
            if '401' in error_str:
                return False, _(
                    "⚠️ خطأ في المصادقة (401 Unauthorized).\n"
                    "يرجى مراجعة بيانات الاعتماد في الإعدادات."
                )
            if '429' in error_str:
                return False, _(
                    "⚠️ تم تجاوز حد النشر (Rate Limit).\n"
                    "يرجى الانتظار قبل المحاولة مرة أخرى."
                )
            return False, _("⚠️ فشل النشر على X: %s") % error_str
