from odoo import models, api, _
import logging

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

_logger = logging.getLogger(__name__)

# Sentinel returned by AI when a tweet is NOT relevant — never shown to the user
AI_SKIP_SIGNAL = "SKIP_NOT_RELEVANT"


class SmartRadarOpenAIService(models.AbstractModel):
    _name = 'alpha.echo.openai.service'
    _description = 'OpenAI Integration Service'

    @api.model
    def classify_and_draft(self, original_text, system_prompt):
        """
        Sends a tweet to the AI for BOTH classification and drafting in a single API call.

        The system_prompt (written by the admin in Settings) tells the AI:
          - Which tweets are relevant (e.g. "grants with open applications")
          - How to format the output post

        If the tweet is NOT relevant, the AI must return exactly: SKIP_NOT_RELEVANT
        If the tweet IS relevant, the AI returns the formatted post.

        Returns:
          (True,  draft_text)  → relevant, post ready
          (False, 'skip')      → not relevant, skip silently
          (False, error_msg)   → real technical error, log it
        """
        if not OpenAI:
            msg = _(
                "⚠️ مكتبة OpenAI غير مثبتة.\n"
                "يرجى تشغيل: pip install openai"
            )
            _logger.error("OpenAI library not installed.")
            return False, msg

        if not original_text or not original_text.strip():
            return False, 'skip'

        config = self.env['alpha.echo.client.config'].get_singleton()
        api_key = config.openai_api_key

        if not api_key:
            msg = _(
                "⚠️ مفتاح OpenAI API غير موجود.\n"
                "يرجى إضافته في الإعدادات أو ملف .env"
            )
            _logger.warning("OpenAI API key is not configured.")
            return False, msg

        model_choice = config.ai_model or 'gpt-4o-mini'
        client = OpenAI(api_key=api_key)

        # Build a structured prompt that forces the AI to either produce content or skip
        classification_wrapper = (
            "%s\n\n"
            "---\n"
            "IMPORTANT: If the tweet below does NOT match your criteria, "
            "respond with ONLY this exact text and nothing else: %s\n"
            "If it DOES match, respond with the formatted post only."
        ) % (system_prompt.strip(), AI_SKIP_SIGNAL)

        try:
            response = client.chat.completions.create(
                model=model_choice,
                messages=[
                    {"role": "system", "content": classification_wrapper},
                    {"role": "user", "content": original_text}
                ],
                temperature=0.5,
                max_tokens=500,
            )

            result = response.choices[0].message.content.strip()

            if not result:
                return False, 'skip'

            # Check if AI decided to skip this tweet
            if AI_SKIP_SIGNAL in result:
                _logger.debug("AI classified tweet as not relevant — skipping.")
                return False, 'skip'

            _logger.info(
                "AI (%s) classified tweet as RELEVANT and generated draft (%d chars).",
                model_choice, len(result)
            )
            return True, result

        except Exception as e:
            error_str = str(e)
            _logger.error("OpenAI API error: %s", error_str)

            if 'quota' in error_str.lower() or '429' in error_str:
                return False, _(
                    "⚠️ تم تجاوز حصة OpenAI (Rate Limit).\n"
                    "يرجى الانتظار أو الترقية لخطة أعلى."
                )
            if 'invalid' in error_str.lower() and 'key' in error_str.lower():
                return False, _(
                    "⚠️ مفتاح OpenAI غير صحيح.\n"
                    "يرجى مراجعة الإعدادات."
                )
            return False, _("⚠️ خطأ في OpenAI: %s") % error_str
