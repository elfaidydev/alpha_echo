from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    alpha_echo_auto_publish = fields.Boolean(
        string='Automate Dual Publishing (Bypass Drafts)',
        config_parameter='alpha_echo.auto_publish',
        default=False,
        help="If enabled, AI generated posts will bypass the draft state and be pushed directly to configured platforms."
    )
    
    alpha_echo_openai_key = fields.Char(
        string='OpenAI API Key',
        config_parameter='alpha_echo.openai_key',
        help="Required for dynamic NLP text formulation"
    )

    alpha_echo_apify_token = fields.Char(
        string='Apify API Token',
        config_parameter='alpha_echo.apify_token',
        help="Required for scraping sources"
    )
    
    alpha_echo_supabase_key = fields.Char(
        string='Supabase API Key',
        config_parameter='alpha_echo.supabase_key',
        help="Required for edge functions connection"
    )
    
    alpha_echo_x_api_key = fields.Char(
        string='X (Twitter) API Token',
        config_parameter='alpha_echo.x_api_key',
        help="Access token for X API publishing"
    )
    
    alpha_echo_wp_token = fields.Char(
        string='WordPress Application Password',
        config_parameter='alpha_echo.wp_token',
        help="Auth token for WordPress REST API"
    )
    
    alpha_echo_ai_prompt = fields.Text(
        string='Strategic Formulation Prompt (System Prompt)',
        config_parameter='alpha_echo.ai_prompt',
        default="أنت خبير صياغة محتوى مؤسسي. قم بإعادة هيكلة البيانات المقدمة بلغة احترافية تعزز الموثوقية وتدعم التوجه الاستراتيجي. تجنب المبالغات التسويقية وكن دقيقاً.",
        help="Provide instructions for the AI on tone and style."
    )
