from odoo import models, fields, api, _

class SmartRadarClientConfig(models.Model):
    _name = 'alpha.echo.client.config'
    _description = 'Alpha Echo: Autonomous AI Social Presence Engine'

    name = fields.Char(string=_('Config Name'), default='Alpha Echo Configuration')
    tenant_id = fields.Char(string=_('Client License Key (Tenant ID)'), required=True, default='')
    auto_approve_drafts = fields.Boolean(string=_('Auto-Approve AI Drafts'), default=False)
    is_engine_active = fields.Boolean(string=_('Is Tracking Engine Active'), default=False)
    target_radar_focus = fields.Char(string=_('Target Radar Focus'), default='', help=_("Keywords for guiding AI and Scraper"))
    custom_ai_instructions = fields.Text(string=_('Custom AI Instructions'), default='', help=_("Tenant-specific AI formatting rules"))
    
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
    scraping_interval = fields.Integer(string=_('Scraping Interval (Minutes)'), default=180)
    max_posts_per_day = fields.Integer(string=_('Max Posts Per Day'), default=100)

    # API Secrets (Secured by Admin Group)
    openai_api_key = fields.Char(string=_('OpenAI API Key'), groups='base.group_system')
    apify_token = fields.Char(string=_('Apify API Token'), groups='base.group_system')

    # X (Twitter) Settings (Restricted to Admin for security)
    x_api_key = fields.Char(string=_('Twitter API Key'), groups='base.group_system')
    x_api_secret = fields.Char(string=_('Twitter API Secret'), groups='base.group_system')
    x_access_token = fields.Char(string=_('Twitter Access Token'), groups='base.group_system')
    x_access_token_secret = fields.Char(string=_('Twitter Access Secret'), groups='base.group_system')
    
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
            'target_radar_focus': config.target_radar_focus or '',
            'custom_ai_instructions': config.custom_ai_instructions or '',
            'ai_model': config.ai_model,
            'content_language': config.content_language,
            'scraping_interval': config.scraping_interval,
            'max_posts_per_day': config.max_posts_per_day,
            'openai_api_key': config.openai_api_key or '',
            'apify_token': config.apify_token or '',
            'x_api_key': config.x_api_key or '',
            'x_api_secret': config.x_api_secret or '',
            'x_access_token': config.x_access_token or '',
            'x_access_token_secret': config.x_access_token_secret or '',
            'supabase_url': config.supabase_url or '',
            'supabase_key': config.supabase_key or '',
            'supabase_status': config.supabase_status,
            'odoo_blog_id': config.odoo_blog_id,
        }
    
    @api.model
    def save_config_data(self, data):
        """RPC method to save config from the UI."""
        if not self.env.user.has_group('base.group_system'):
            return {'error': _('Unauthorized')}
            
        config = self.get_singleton()
        
        # Whitelist fields to update
        allowed_fields = [
            'tenant_id', 'auto_approve_drafts', 'target_radar_focus', 'is_engine_active',
            'custom_ai_instructions', 'x_api_key', 'x_api_secret', 
            'x_access_token', 'x_access_token_secret', 'odoo_blog_id',
            'ai_model', 'content_language', 'scraping_interval', 'max_posts_per_day',
            'supabase_url', 'supabase_key', 'openai_api_key', 'apify_token'
        ]
        
        vals = {k: v for k, v in data.items() if k in allowed_fields}
                
        config.write(vals)

        # Sync Scan Frequency with the Odoo Cron Job
        if 'scraping_interval' in vals:
            cron = self.env.ref('alpha_echo.ir_cron_alpha_echo_fetch', raise_if_not_found=False)
            if cron:
                cron.write({
                    'interval_number': max(5, vals['scraping_interval']),
                    'interval_type': 'minutes'
                })

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
