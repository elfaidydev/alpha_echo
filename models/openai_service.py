from odoo import models, api, _
import logging
import json

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

_logger = logging.getLogger(__name__)

# The exact signal the AI must return to mark a tweet as irrelevant.
_SKIP_SIGNALS = frozenset({
    'skip_not_relevant',   # canonical sentinel
    'skip',                # shorthand (often used in Arabic system prompts)
})


class SmartRadarOpenAIService(models.AbstractModel):
    _name        = 'alpha.echo.openai.service'
    _description = 'OpenAI Integration Service'

    @api.model
    def classify_and_draft(self, original_text: str, system_prompt: str) -> tuple:
        """
        Classify a tweet AND draft the output post in a SINGLE OpenAI call.

        The system_prompt (set by the admin) tells the AI:
          • Which tweets are relevant (topic/criteria)
          • How to format the output post

        If the tweet is NOT relevant the AI must reply with EXACTLY one of:
          SKIP_NOT_RELEVANT   (canonical)
          skip                (shorthand accepted for Arabic prompts)

        Returns:
          (True,  {"post_text": "...", "grant_end_date": "YYYY-MM-DD or None"})
              → relevant — create a post
          (False, 'skip')       → not relevant — silently skip
          (False, error_msg)    → technical error — log and skip
        """
        # ── Library guard ─────────────────────────────────────────────────────
        if not OpenAI:
            _logger.error("openai library not installed.")
            return False, _("⚠️ OpenAI library is not installed. Run: pip install openai")

        # ── Input guard ───────────────────────────────────────────────────────
        if not original_text or not original_text.strip():
            return False, 'skip'

        # ── Load config ───────────────────────────────────────────────────────
        config  = self.env['alpha.echo.client.config'].get_singleton()
        api_key = config.openai_api_key
        if not api_key:
            _logger.warning("OpenAI API key not configured.")
            return False, _("⚠️ OpenAI API Key is missing. Please add it in settings.")

        model = config.ai_model or 'gpt-4o-mini'

        # ── Build classifier-wrapper around the admin prompt ──────────────────
        wrapped_prompt = (
            f"{system_prompt.strip()}\n\n"
            "---\n"
            "IMPORTANT RULES:\n"
            "1. If the tweet does NOT meet your criteria, reply with ONLY: SKIP_NOT_RELEVANT\n"
            "2. If it DOES match, reply with ONLY a valid JSON object (no markdown, no code block):\n"
            '   {"post_text": "Your formatted post here", "grant_end_date": "YYYY-MM-DD or null"}\n'
            "   - post_text: the fully formatted post text\n"
            "   - grant_end_date: the application deadline if mentioned (ISO format), otherwise null\n"
            "3. Do NOT add any extra text outside the JSON."
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
                return False, _("⚠️ OpenAI quota exceeded (Rate Limit). Please wait or upgrade your plan.")
            if 'invalid' in err.lower() and 'key' in err.lower():
                return False, _("⚠️ Invalid OpenAI API Key. Please check the settings.")
            return False, _("⚠️ OpenAI Error: %s") % err

        # ── Classify response ─────────────────────────────────────────────────
        if not result:
            return False, 'skip'

        if result.lower() in _SKIP_SIGNALS or 'SKIP_NOT_RELEVANT' in result:
            _logger.debug("AI: tweet not relevant — skipping.")
            return False, 'skip'

        # ── Parse JSON response ───────────────────────────────────────────────
        try:
            # Strip markdown code fences if the model included them despite instructions
            clean = result.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[-2] if "```" in clean[3:] else clean[3:]
                clean = clean.lstrip("json").strip()

            data = json.loads(clean)
            post_text = (data.get('post_text') or '').strip()
            grant_end_date = data.get('grant_end_date')  # "YYYY-MM-DD" or null

            if not post_text:
                _logger.warning("AI returned JSON but post_text is empty. Raw: %s", result[:200])
                return False, 'skip'

            # Validate date format
            if grant_end_date:
                try:
                    from datetime import date
                    date.fromisoformat(grant_end_date)
                except (ValueError, TypeError):
                    _logger.warning("AI returned invalid date '%s', ignoring.", grant_end_date)
                    grant_end_date = None

            _logger.info("AI (%s): tweet classified RELEVANT (%d chars). Deadline: %s",
                         model, len(post_text), grant_end_date or 'none')
            return True, {'post_text': post_text, 'grant_end_date': grant_end_date}

        except (json.JSONDecodeError, ValueError):
            # Fallback: AI didn't return JSON — treat the whole response as post_text
            _logger.info(
                "AI response was not valid JSON, treating as plain text. "
                "Consider updating your AI prompt. Raw: %.100s", result
            )
            return True, {'post_text': result, 'grant_end_date': None}
