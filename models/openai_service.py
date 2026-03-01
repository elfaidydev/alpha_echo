from odoo import models, api, _
import logging

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# OpenAI API Configuration
_logger = logging.getLogger(__name__)

class SmartRadarOpenAIService(models.AbstractModel):
    _name = 'alpha.echo.openai.service'
    _description = 'OpenAI Integration Service'

    @api.model
    def draft_post(self, original_text, system_prompt):
        """
        Sends original text to OpenAI and returns formatted draft.
        """
        if not OpenAI:
            _logger.error("OpenAI library not installed.")
            return False, _("OpenAI library not installed.")

        # Retrieve config and key
        config = self.env['alpha.echo.client.config'].get_singleton()
        api_key = config.openai_api_key
        
        if not api_key:
            return False, _("OpenAI API Key is not configured in settings.")

        client = OpenAI(api_key=api_key)
        
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
