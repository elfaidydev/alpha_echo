from odoo import models, api, _
import logging

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

_logger = logging.getLogger(__name__)

# HARDCODED SECRETS AS REQUESTED
OPENAI_API_KEY = "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"

class SmartRadarOpenAIService(models.AbstractModel):
    _name = 'alpha.echo.openai.service'
    _description = 'OpenAI Integration Service'

    @api.model
    def draft_post(self, original_text, system_prompt):
        """
        Sends the original text to OpenAI and returns the formatted draft.
        """
        if not OpenAI:
            _logger.error("OpenAI library is not installed.")
            return False, "OpenAI library not installed."

        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Retrieve model from config (default to gpt-4o-mini as requested)
        config = self.env['alpha.echo.client.config'].get_singleton()
        model_choice = config.ai_model or 'gpt-4o-mini'

        try:
            response = client.chat.completions.create(
                model=model_choice,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Rewrite this tweet based on the instructions: {original_text}"}
                ],
                temperature=0.7,
            )
            
            draft = response.choices[0].message.content.strip()
            return True, draft

        except Exception as e:
            _logger.error(f"OpenAI API Error: {str(e)}")
            return False, str(e)
