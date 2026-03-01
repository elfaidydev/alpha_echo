from odoo import models, api, _
import logging

try:
    import tweepy
except ImportError:
    tweepy = None

_logger = logging.getLogger(__name__)

class SmartRadarXService(models.AbstractModel):
    _name = 'alpha.echo.x.service'
    _description = 'X (Twitter) Integration Service'

    @api.model
    def _get_client(self):
        """Helper to get tweepy client authenticated with DB credentials."""
        if not tweepy:
            return None, _("Tweepy library not installed.")
            
        config = self.env['alpha.echo.client.config'].get_singleton()
        
        # Validate that all keys are present
        if not (config.x_api_key and config.x_api_secret and config.x_access_token and config.x_access_token_secret):
            return None, _("Twitter credentials are not fully configured in settings.")

        try:
            client = tweepy.Client(
                consumer_key=config.x_api_key,
                consumer_secret=config.x_api_secret,
                access_token=config.x_access_token,
                access_token_secret=config.x_access_token_secret
            )
            return client, None
        except Exception as e:
            return None, str(e)

    @api.model
    def test_connection(self):
        """Test Twitter API credentials and return account info."""
        client, error = self._get_client()
        if error:
            return {'success': False, 'error': error}
            
        try:
            # Get the authenticated user's info
            user_info = client.get_me(user_fields=['profile_image_url', 'username'])
            if user_info and user_info.data:
                return {
                    'success': True,
                    'name': user_info.data.name,
                    'username': user_info.data.username,
                    'profile_image_url': user_info.data.profile_image_url
                }
            return {'success': False, 'error': _('Could not retrieve user info.')}
            
        except Exception as e:
            _logger.error(f"Twitter Test Connection Failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    @api.model
    def publish_tweet(self, text):
        """Publish a tweet using v2 API with length verification."""
        if not text:
            return False, _("Tweet text is empty.")

        # X/Twitter character limit for standard accounts is 280.
        # Note: Some accounts have higher limits, but 280 is the safe production baseline.
        if len(text) > 280:
            return False, _("Tweet exceeds 280 character limit (Current length: %s)") % len(text)

        client, error = self._get_client()
        if error:
            return False, error
            
        try:
            response = client.create_tweet(text=text)
            tweet_id = response.data.get('id')
            
            # Fetch user info for URL construction
            user_info = client.get_me()
            username = user_info.data.username if user_info and user_info.data else 'i'
            
            tweet_url = f"https://twitter.com/{username}/status/{tweet_id}"
            return True, tweet_url
            
        except Exception as e:
            _logger.error(f"Twitter Publish Failed: {str(e)}")
            return False, str(e)
