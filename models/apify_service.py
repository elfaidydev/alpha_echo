from odoo import models, api, _
from odoo.exceptions import UserError
import logging

try:
    from apify_client import ApifyClient
except ImportError:
    ApifyClient = None

_logger = logging.getLogger(__name__)

# HARDCODED SECRETS AS REQUESTED
APIFY_TOKEN = "apify_api_CNaYglOmQwzMHpkdK8Hx7U2GueoZNt4wxa5J"

class SmartRadarApifyService(models.AbstractModel):
    _name = 'alpha.echo.apify.service'
    _description = 'Apify Integration Service'

    @api.model
    def run_actor_and_fetch(self, handles, limit_per_handle=4):
        """
        Runs the apidojo/twitter-scraper-lite actor for a list of handles.
        Returns a list of parsed tweets.
        """
        if not ApifyClient:
            _logger.error("Apify Client library is not installed.")
            return []

        client = ApifyClient(APIFY_TOKEN)
        
        # Prepare the input for the actor
        run_input = {
            "searchTerms": [],
            "twitterHandles": handles,
            "maxItems": limit_per_handle * len(handles),
            "sort": "Latest",
            "tweetLanguage": "all"
        }

        _logger.info(f"Starting Apify Actor (apidojo/twitter-scraper-lite) for handles: {handles}")
        try:
            # Run the actor and wait for it to finish
            run = client.actor("apidojo/twitter-scraper-lite").call(run_input=run_input)
            
            # Fetch results from the dataset
            dataset_items = client.dataset(run["defaultDatasetId"]).iterate_items()
            
            results = []
            for item in dataset_items:
                results.append({
                    'id': str(item.get('id')),
                    'text': item.get('text', ''),
                    'author': item.get('author', {}).get('userName', ''),
                    'url': item.get('url', ''),
                    'created_at': item.get('createdAt', '')
                })
            
            _logger.info(f"Apify Actor finished successfully. Retrieved {len(results)} items.")
            return results

        except Exception as e:
            _logger.error(f"Failed to run Apify actor: {str(e)}")
            return []
