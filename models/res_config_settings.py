from odoo import models, fields, api, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    alpha_echo_auto_publish = fields.Boolean(
        string=_('Automate Dual Publishing (Bypass Drafts)'),
        config_parameter='alpha_echo.auto_publish',
        default=False,
        help=_("If enabled, AI generated posts will bypass the draft state and be pushed directly to configured platforms.")
    )
    
    alpha_echo_openai_key = fields.Char(
        string=_('OpenAI API Key'),
        config_parameter='alpha_echo.openai_key',
        help=_("Required for dynamic NLP text formulation")
    )

    alpha_echo_apify_token = fields.Char(
        string=_('Apify API Token'),
        config_parameter='alpha_echo.apify_token',
        help=_("Required for scraping sources")
    )
    
    alpha_echo_supabase_key = fields.Char(
        string=_('Supabase API Key'),
        config_parameter='alpha_echo.supabase_key',
        help=_("Required for edge functions connection")
    )
    
    alpha_echo_x_api_key = fields.Char(
        string=_('X (Twitter) API Token'),
        config_parameter='alpha_echo.x_api_key',
        help=_("Access token for X API publishing")
    )
    
    alpha_echo_wp_token = fields.Char(
        string=_('WordPress Application Password'),
        config_parameter='alpha_echo.wp_token',
        help=_("Auth token for WordPress REST API")
    )
    
    alpha_echo_ai_prompt = fields.Char(
        string=_('Strategic Formulation Prompt (System Prompt)'),
        config_parameter='alpha_echo.ai_prompt',
        default=_("أنت خبير في صياغة المحتوى المؤسسي. قم بإعادة صياغة البيانات المقدمة بلغة عربية مهنية سهلة وواضحة تعزز الموثوقية وتدعم التوجه الاستراتيجي. تجنب المبالغات التسويقية وكن دقيقاً وبسيطاً في تعبيرك ليفهمك الجميع."),
        help=_("Provide instructions for the AI on tone and style.")
    )

    alpha_echo_x_list_id = fields.Char(
        string=_('X/Twitter List ID'),
        config_parameter='alpha_echo.x_list_id',
        help=_("The numeric ID from your Twitter List URL: twitter.com/i/lists/[LIST_ID]")
    )
