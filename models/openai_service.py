from odoo import models, api, _
import logging

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

_logger = logging.getLogger(__name__)

# The exact signal the AI must return to mark a tweet as irrelevant.
# Documented here so the system_prompt wrapper stays in-sync with detection.
_SKIP_SIGNALS = frozenset({
    'skip_not_relevant',   # canonical sentinel
    'skip',                # shorthand (often used in Arabic system prompts)
})


class SmartRadarOpenAIService(models.AbstractModel):
    _name        = 'alpha.echo.openai.service'
    _description = 'OpenAI Integration Service'

    @api.model
    def classify_and_draft(self, original_text: str, system_prompt: str) -> tuple[bool, str]:
        """
        Classify a tweet AND draft the output post in a SINGLE OpenAI call.

        The system_prompt (set by the admin) tells the AI:
          • Which tweets are relevant (topic/criteria)
          • How to format the output post

        If the tweet is NOT relevant the AI must reply with EXACTLY one of:
          SKIP_NOT_RELEVANT   (canonical)
          skip                (shorthand accepted for Arabic prompts)

        Returns:
          (True,  draft_text)   → relevant — create a post
          (False, 'skip')       → not relevant — silently skip
          (False, error_msg)    → technical error — log and skip
        """
        # ── Library guard ─────────────────────────────────────────────────────
        if not OpenAI:
            _logger.error("openai library not installed.")
            return False, _("⚠️ مكتبة OpenAI غير مثبتة. شغّل: pip install openai")

        # ── Input guard ───────────────────────────────────────────────────────
        if not original_text or not original_text.strip():
            return False, 'skip'

        # ── Load config ───────────────────────────────────────────────────────
        config  = self.env['alpha.echo.client.config'].get_singleton()
        api_key = config.openai_api_key
        if not api_key:
            _logger.warning("OpenAI API key not configured.")
            return False, _("⚠️ OpenAI API Key غير موجود. أضفه في الإعدادات.")

        model = config.ai_model or 'gpt-4o-mini'

        # ── Build classifier-wrapper around the admin prompt ──────────────────
        # We append a mandatory exit clause so the AI knows exactly what to send
        # when the tweet is irrelevant — avoids ambiguous freeform rejections.
        wrapped_prompt = (
            f"{system_prompt.strip()}\n\n"
            "---\n"
            "IMPORTANT: If the tweet below does NOT meet your criteria, "
            "reply with ONLY the word: SKIP_NOT_RELEVANT\n"
            "Do NOT add any other text. If it DOES match, reply with the formatted post only."
        )

        # ── Call OpenAI ───────────────────────────────────────────────────────
        try:
            client   = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": wrapped_prompt},
                    {"role": "user",   "content": original_text},
                ],
                temperature=0.5,
                max_tokens=500,
            )
            result = (response.choices[0].message.content or '').strip()

        except Exception as exc:
            err = str(exc)
            _logger.error("OpenAI API error: %s", err)

            if '429' in err or 'quota' in err.lower():
                return False, _("⚠️ تم تجاوز حصة OpenAI (Rate Limit). انتظر أو رقّي الخطة.")
            if 'invalid' in err.lower() and 'key' in err.lower():
                return False, _("⚠️ OpenAI API Key غير صحيح. راجع الإعدادات.")
            return False, _("⚠️ خطأ في OpenAI: %s") % err

        # ── Classify response ─────────────────────────────────────────────────
        if not result:
            return False, 'skip'

        if result.lower() in _SKIP_SIGNALS or 'SKIP_NOT_RELEVANT' in result:
            _logger.debug("AI: tweet not relevant — skipping.")
            return False, 'skip'

        _logger.info("AI (%s): tweet classified RELEVANT (%d chars).", model, len(result))
        return True, result
