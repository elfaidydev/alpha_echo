import os
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    # Load .env from the module's root directory
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    _logger.warning("python-dotenv not installed. Environment variables from .env will not be loaded.")

class SmartRadarClientConfig(models.Model):
    _name = 'alpha.echo.client.config'
    _description = 'Alpha Echo: Autonomous AI Social Presence Engine'

    name = fields.Char(string=_('Config Name'), default='Alpha Echo Configuration')
    tenant_id = fields.Char(string=_('Client License Key (Tenant ID)'), required=True, default='')
    auto_approve_drafts = fields.Boolean(string=_('Auto-Approve AI Drafts'), default=False)
    is_engine_active = fields.Boolean(string=_('Is Tracking Engine Active'), default=False)
    custom_ai_instructions = fields.Text(string=_('Custom AI Instructions'), default='', help=_("AI prompt: what to look for and how to format the output."))
    
    # Statistics
    targets_count = fields.Integer(string=_('Monitored Accounts'), compute='_compute_targets_count')

    def _compute_targets_count(self):
        TargetObj = self.env['alpha.echo.target']
        for record in self:
            record.targets_count = TargetObj.search_count([('is_active', '=', True)])
    
    # Engine Settings
    ai_model = fields.Selection([
        ('gpt-4o', _('GPT-4o (High Quality)')),
        ('gpt-4o-mini', _('GPT-4o Mini (Fast/Cheap)')),
        ('claude-3-5-sonnet', _('Claude 3.5 Sonnet'))
    ], string=_('AI Model'), default='gpt-4o-mini')
    content_language = fields.Selection([
        ('ar', _('Arabic Only')),
        ('en', _('English Only')),
        ('both', _('Bilingual (Arabic/English)'))
    ], string=_('Content Language'), default='both')

    # API Secrets (Secured by Admin Group)
    openai_api_key = fields.Char(string=_('OpenAI API Key'), groups='base.group_system')
    apify_token = fields.Char(string=_('Apify API Token'), groups='base.group_system')


    # X (Twitter) Settings (Restricted to Admin for security)
    x_api_key = fields.Char(string=_('Twitter API Key'), groups='base.group_system')
    x_api_secret = fields.Char(string=_('Twitter API Secret'), groups='base.group_system')
    x_access_token = fields.Char(string=_('Twitter Access Token'), groups='base.group_system')
    x_access_token_secret = fields.Char(string=_('Twitter Access Secret'), groups='base.group_system')
    
    # X (Twitter) Cookies (For Apify List scraping)
    x_auth_token = fields.Char(string=_('Twitter auth_token Cookie'), groups='base.group_system')
    x_ct0 = fields.Char(string=_('Twitter ct0 Cookie'), groups='base.group_system')
    
    # Cached publisher username (stored after successful test_connection — avoids an API call per publish)
    x_publisher_username = fields.Char(string=_('X Publisher Username'), groups='base.group_system', readonly=True)
    


    @api.model
    def get_singleton(self):
        """Returns the single configuration record or creates it if it doesn't exist."""
        config = self.search([], limit=1)
        if not config:
            config = self.create({})
        return config

    @api.model
    def get_config_data(self):
        """RPC method to get config for the UI."""
        if not self.env.user.has_group('base.group_system'):
            return {'error': _('Unauthorized')}
            
        config = self.get_singleton()
        return {
            'tenant_id': config.tenant_id or '',
            'auto_approve_drafts': config.auto_approve_drafts,
            'is_engine_active': config.is_engine_active,
            'custom_ai_instructions': config.custom_ai_instructions or '',
            'ai_model': config.ai_model,
            'content_language': config.content_language,
            'openai_api_key': config.openai_api_key or '',
            'apify_token': config.apify_token or '',
            'x_api_key': config.x_api_key or '',
            'x_api_secret': config.x_api_secret or '',
            'x_access_token': config.x_access_token or '',
            'x_access_token_secret': config.x_access_token_secret or '',
            'x_auth_token': config.x_auth_token or '',
            'x_ct0': config.x_ct0 or '',
            'targets_count': config.targets_count,
        }
    

    @api.model
    def save_config_data(self, data):
        """RPC method to save config from the UI."""
        if not self.env.user.has_group('base.group_system'):
            return {'error': _('Unauthorized')}
            
        config = self.get_singleton()
        was_active = config.is_engine_active
        
        # Whitelist fields to update
        allowed_fields = [
            'tenant_id', 'auto_approve_drafts', 'is_engine_active',
            'custom_ai_instructions', 'x_api_key', 'x_api_secret',
            'x_access_token', 'x_access_token_secret', 'x_auth_token', 'x_ct0',
            'ai_model', 'content_language',
            'openai_api_key', 'apify_token'
        ]
        
        vals = {k: v for k, v in data.items() if k in allowed_fields}
        
                
        config.write(vals)

        # Immediate start: If engine was just turned on, trigger the cron immediately
        if vals.get('is_engine_active') and not was_active:
            cron = self.env.ref('alpha_echo.ir_cron_twitter_smart_scraper', raise_if_not_found=False)
            if cron:
                cron._trigger()
            
        return {'success': True}

    @api.model
    def disconnect_x(self):
        """Official method to disconnect X account and stop tracking. 
        Clears all credentials and deactivates the engine.
        """
        if not self.env.user.has_group('base.group_system'):
            return {'error': _('Unauthorized')}
            
        config = self.get_singleton()
        config.write({
            'x_api_key': '',
            'x_api_secret': '',
            'x_access_token': '',
            'x_access_token_secret': '',
            'x_publisher_username': '',
            'is_engine_active': False
        })
        return {'success': True}
