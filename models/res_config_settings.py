from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    smart_radar_auto_publish = fields.Boolean(
        string='Automate Dual Publishing (Bypass Drafts)',
        config_parameter='smart_radar.auto_publish',
        default=False,
        help="If enabled, AI generated posts will bypass the draft state and be pushed directly to configured platforms."
    )
    
    smart_radar_openai_key = fields.Char(
        string='OpenAI API Key',
        config_parameter='smart_radar.openai_key',
        help="Required for dynamic NLP text formulation"
    )
    
    smart_radar_supabase_key = fields.Char(
        string='Supabase API Key',
        config_parameter='smart_radar.supabase_key',
        help="Required for edge functions connection"
    )
    
    smart_radar_x_api_key = fields.Char(
        string='X (Twitter) API Token',
        config_parameter='smart_radar.x_api_key',
        help="Access token for X API publishing"
    )
    
    smart_radar_wp_token = fields.Char(
        string='WordPress Application Password',
        config_parameter='smart_radar.wp_token',
        help="Auth token for WordPress REST API"
    )
    
    smart_radar_ai_prompt = fields.Text(
        string='Strategic Formulation Prompt (System Prompt)',
        config_parameter='smart_radar.ai_prompt',
        default="أنت خبير صياغة محتوى مؤسسي. قم بإعادة هيكلة البيانات المقدمة بلغة احترافية تعزز الموثوقية وتدعم التوجه الاستراتيجي. تجنب المبالغات التسويقية وكن دقيقاً.",
        help="Provide instructions for the AI on tone and style."
    )
