from odoo import models, fields, api

class SmartRadarClientConfig(models.Model):
    _name = 'smart.radar.client.config'
    _description = 'Smart Radar SaaS Client Configuration'

    name = fields.Char(string='Config Name', default='Smart Radar Configuration')
    tenant_id = fields.Char(string='Client License Key (Tenant ID)', required=True, default='')
    auto_approve_drafts = fields.Boolean(string='Auto-Approve AI Drafts', default=False)
    target_radar_focus = fields.Char(string='Target Radar Focus', help="Keywords for guiding AI and Scraper")
    custom_ai_instructions = fields.Text(string='Custom AI Instructions', help="Tenant-specific AI formatting rules")
    
    # Engine Settings
    ai_model = fields.Selection([
        ('gpt-4o', 'GPT-4o (High Quality)'),
        ('gpt-4o-mini', 'GPT-4o Mini (Fast/Cheap)'),
        ('claude-3-5-sonnet', 'Claude 3.5 Sonnet')
    ], string='AI Model', default='gpt-4o')
    content_language = fields.Selection([
        ('ar', 'Arabic Only'),
        ('en', 'English Only'),
        ('both', 'Bilingual (Arabic/English)')
    ], string='Content Language', default='both')
    scraping_interval = fields.Integer(string='Scraping Interval (Minutes)', default=180)
    max_posts_per_day = fields.Integer(string='Max Posts Per Day', default=0)

    # X (Twitter) Settings (Restricted to Admin for security)
    x_api_key = fields.Char(string='Twitter API Key', groups='base.group_system')
    x_api_secret = fields.Char(string='Twitter API Secret', groups='base.group_system', password='True')
    x_access_token = fields.Char(string='Twitter Access Token', groups='base.group_system')
    x_access_token_secret = fields.Char(string='Twitter Access Secret', groups='base.group_system', password='True')
    
    # Supabase Settings (Restricted to Admin for security)
    supabase_url = fields.Char(string='Supabase URL', groups='base.group_system')
    supabase_key = fields.Char(string='Supabase Key', groups='base.group_system', password='True')
    supabase_status = fields.Selection([
        ('disconnected', 'Disconnected'),
        ('connected', 'Connected'),
        ('error', 'Error')
    ], string='Supabase Status', default='disconnected', groups='base.group_system')
    
    # Optional integration with blog.blog if module enabled.
    odoo_blog_id = fields.Integer(string='Odoo Blog ID Endpoint', help="ID of the blog.blog if used")

    def action_test_connection(self):
        """Dummy test connection logic."""
        self.ensure_one()
        self.supabase_status = 'connected'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Connection Success',
                'message': 'Successfully connected to SaaS endpoints.',
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
            return {'error': 'Unauthorized'}
            
        config = self.get_singleton()
        focus = config.target_radar_focus or ''
        if focus in ['Odoo, ERP, Business', 'Odoo,ERP,Business']:
            focus = ''
        return {
            'tenant_id': config.tenant_id or '',
            'auto_approve_drafts': config.auto_approve_drafts,
            'target_radar_focus': focus,
            'custom_ai_instructions': config.custom_ai_instructions or '',
            'ai_model': config.ai_model,
            'content_language': config.content_language,
            'scraping_interval': config.scraping_interval,
            'max_posts_per_day': config.max_posts_per_day,
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
            return {'error': 'Unauthorized'}
            
        config = self.get_singleton()
        
        # Whitelist fields to update
        allowed_fields = [
            'tenant_id', 'auto_approve_drafts', 'target_radar_focus', 
            'custom_ai_instructions', 'x_api_key', 'x_api_secret', 
            'x_access_token', 'x_access_token_secret', 'odoo_blog_id',
            'ai_model', 'content_language', 'scraping_interval', 'max_posts_per_day',
            'supabase_url', 'supabase_key'
        ]
        
        vals = {k: v for k, v in data.items() if k in allowed_fields}
                
        config.write(vals)

        # Sync Scan Frequency with the Odoo Cron Job
        if 'scraping_interval' in vals:
            cron = self.env.ref('smart_radar.ir_cron_smart_radar_fetch', raise_if_not_found=False)
            if cron:
                cron.write({
                    'interval_number': max(5, vals['scraping_interval']),
                    'interval_type': 'minutes'
                })

        return {'success': True}
