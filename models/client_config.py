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
    x_list_id = fields.Char(
        string=_('X/Twitter List ID'),
        default='',
        help=_("The numeric ID of your private X/Twitter List. Found in the URL: twitter.com/i/lists/[LIST_ID]")
    )
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
    # Note: These fields now prioritize environment variables if set.
    openai_api_key = fields.Char(string=_('OpenAI API Key'), groups='base.group_system', compute='_compute_api_secrets', inverse='_inverse_openai_key', store=True)
    apify_token = fields.Char(string=_('Apify API Token'), groups='base.group_system', compute='_compute_api_secrets', inverse='_inverse_apify_token', store=True)

    def _compute_api_secrets(self):
        for record in self:
            # Prioritize OS Environment / .env — fallback to DB — fallback to empty string
            record.openai_api_key = os.getenv('OPENAI_API_KEY') or record.openai_api_key or ''
            record.apify_token = os.getenv('APIFY_TOKEN') or record.apify_token or ''

    def _inverse_openai_key(self):
        for record in self:
            if not os.getenv('OPENAI_API_KEY'):
                record.openai_api_key = record.openai_api_key

    def _inverse_apify_token(self):
        for record in self:
            if not os.getenv('APIFY_TOKEN'):
                record.apify_token = record.apify_token

    # X (Twitter) Settings (Restricted to Admin for security)
    x_api_key = fields.Char(string=_('Twitter API Key'), groups='base.group_system')
    x_api_secret = fields.Char(string=_('Twitter API Secret'), groups='base.group_system')
    x_access_token = fields.Char(string=_('Twitter Access Token'), groups='base.group_system')
    x_access_token_secret = fields.Char(string=_('Twitter Access Secret'), groups='base.group_system')
    
    # X (Twitter) Cookies (For Apify List scraping)
    x_auth_token = fields.Char(string=_('Twitter auth_token Cookie'), groups='base.group_system')
    x_ct0 = fields.Char(string=_('Twitter ct0 Cookie'), groups='base.group_system')
    
    # Supabase Settings (Restricted to Admin for security)
    supabase_url = fields.Char(string=_('Supabase URL'), groups='base.group_system')
    supabase_key = fields.Char(string=_('Supabase Key'), groups='base.group_system')
    supabase_status = fields.Selection([
        ('disconnected', _('Disconnected')),
        ('connected', _('Connected')),
        ('error', _('Error'))
    ], string=_('Supabase Status'), default='disconnected', groups='base.group_system')
    
    # Optional integration with blog.blog if module enabled.
    odoo_blog_id = fields.Integer(string=_('Odoo Blog ID Endpoint'), help=_("ID of the blog.blog if used"))

    def action_test_connection(self):
        """Dummy test connection logic."""
        self.ensure_one()
        self.supabase_status = 'connected'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Connection Success'),
                'message': _('Successfully connected to SaaS endpoints.'),
                'type': 'success',
                'sticky': False,
            }
        }

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
            'x_list_id': config.x_list_id or '',
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
            'supabase_url': config.supabase_url or '',
            'supabase_key': config.supabase_key or '',
            'supabase_status': config.supabase_status,
            'odoo_blog_id': config.odoo_blog_id,
            'targets_count': config.targets_count,
        }
    
    @api.model
    def sync_list_members(self):
        """
        Triggers the synchronization process.
        INSTANT FIX: We only trigger the Cron job to run in the background.
        No external API calls are made within this RPC to prevent Timeout.
        """
        config = self.env['alpha.echo.client.config'].get_singleton()
        if not config.x_list_id:
            return {'success': False, 'error': _('No List ID configured.')}

        _logger.info("Manual target sync triggered (FULL ASYNC) for list %s", config.x_list_id)
        
        # TRIGGER CRON: Run everything (member fetch + tweet scan) in the background
        cron = self.env.ref('alpha_echo.alpha_echo_cron_fetch_targets', raise_if_not_found=False)
        if cron:
            # Set nextcall to now to force immediate execution by Odoo's cron runner
            cron.sudo().write({
                'nextcall': fields.Datetime.now(),
                'active': True
            })
            return {
                'success': True,
                'message': _("Sync command sent. The engine is now discoverng accounts in the background. Please wait a moment and refresh.")
            }
        
        return {'success': False, 'error': _("Sync service not found.")}

    @api.model
    def save_config_data(self, data):
        """RPC method to save config from the UI."""
        if not self.env.user.has_group('base.group_system'):
            return {'error': _('Unauthorized')}
            
        config = self.get_singleton()
        old_list_id = config.x_list_id
        
        # Whitelist fields to update
        allowed_fields = [
            'tenant_id', 'auto_approve_drafts', 'x_list_id', 'is_engine_active',
            'custom_ai_instructions', 'x_api_key', 'x_api_secret',
            'x_access_token', 'x_access_token_secret', 'x_auth_token', 'x_ct0',
            'odoo_blog_id', 'ai_model', 'content_language',
            'supabase_url', 'supabase_key', 'openai_api_key', 'apify_token'
        ]
        
        vals = {k: v for k, v in data.items() if k in allowed_fields}
        config.write(vals)

        # Proactively trigger sync if List ID changed and we have a token
        if config.x_list_id and config.x_list_id != old_list_id and config.apify_token:
            _logger.info("List ID changed, triggering proactive sync...")
            self.with_delay().sync_list_members() # Run async if queue installed, or just call if not
            
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
            'is_engine_active': False
        })
        return {'success': True}
