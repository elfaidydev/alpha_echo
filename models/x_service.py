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
                "⚠️ Tweepy library is not installed on the server.\n"
                "Please run: pip install tweepy"
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
                "⚠️ Missing X (Twitter) credentials: %s\n"
                "Please complete them in Settings."
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
            return None, _("⚠️ Failed to connect to X: %s") % str(e)

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
                # Cache the publisher username to avoid a get_me() call on every publish
                config = self.env['alpha.echo.client.config'].get_singleton()
                config.sudo().write({'x_publisher_username': user_info.data.username})
                return {
                    'success': True,
                    'name': user_info.data.name,
                    'username': user_info.data.username,
                    'profile_image_url': user_info.data.profile_image_url
                }
            return {'success': False, 'error': _("⚠️ Unable to retrieve account information from X.")}

        except Exception as e:
            _logger.error("X connection test failed: %s", str(e))
            return {'success': False, 'error': _("⚠️ X connection test failed: %s") % str(e)}

    @api.model
    def publish_tweet(self, text):
        """
        Publish a tweet using Twitter v2 API.
        Returns (True, tweet_url) on success, or (False, error_message) on failure.
        """
        if not text or not text.strip():
            return False, _("⚠️ Tweet text is empty — cannot publish.")

        if len(text) > X_CHAR_LIMIT:
            return False, _(
                "⚠️ Text exceeds X/Twitter limit (%d characters). Current size: %d characters.\n"
                "Please shorten the text before publishing."
            ) % (X_CHAR_LIMIT, len(text))

        client, error = self._get_client()
        if error:
            return False, error

        try:
            response = client.create_tweet(text=text)
            tweet_id = response.data.get('id')

            # Build URL using saved handle from config (no extra API call needed)
            config = self.env['alpha.echo.client.config'].get_singleton()
            username = config.x_publisher_username or 'i'
            tweet_url = "https://twitter.com/%s/status/%s" % (username, tweet_id)

            _logger.info("Tweet published successfully: %s", tweet_url)
            return True, tweet_url

        except Exception as e:
            error_str = str(e)
            _logger.error("Tweet publish failed: %s", error_str)

            if '402' in error_str:
                return False, _(
                    "⚠️ Payment failed or out of credit (402 Payment Required).\n"
                    "Please check your X Developer Portal subscription."
                )
            if '403' in error_str:
                return False, _(
                    "⚠️ Publishing rejected (403 Forbidden).\n"
                    "Verify that your X app has Read & Write permissions."
                )
            if '401' in error_str:
                return False, _(
                    "⚠️ Authentication error (401 Unauthorized).\n"
                    "Please review your credentials in Settings."
                )
            if '429' in error_str:
                return False, _(
                    "⚠️ Publishing rate limit exceeded.\n"
                    "Please wait before trying again."
                )
            return False, _("⚠️ Failed to publish on X: %s") % error_str
