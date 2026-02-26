from odoo import models, fields, api

class SmartRadarClientConfig(models.Model):
    _name = 'smart.radar.client.config'
    _description = 'Smart Radar SaaS Client Configuration'

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
    scraping_interval = fields.Integer(string='Scraping Interval (Minutes)', default=30)
    max_posts_per_day = fields.Integer(string='Max Posts Per Day', default=50)

    # Endpoints
    twitter_api_key = fields.Char(string='Twitter API Key')
    twitter_api_secret = fields.Char(string='Twitter API Secret')
    twitter_access_token = fields.Char(string='Twitter Access Token')
    twitter_access_secret = fields.Char(string='Twitter Access Secret')
    
    # Optional integration with blog.blog if module enabled. Skipping hard dependency for now, saving target as string url/name
    odoo_blog_id = fields.Integer(string='Odoo Blog ID Endpoint', help="ID of the blog.blog if used")

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
        # Check permissions first! Important for SaaS
        if not self.env.user.has_group('base.group_system'):
            return {'error': 'Unauthorized'}
            
        config = self.get_singleton()
        return {
            'tenant_id': config.tenant_id or '',
            'auto_approve_drafts': config.auto_approve_drafts,
            'target_radar_focus': config.target_radar_focus or '',
            'custom_ai_instructions': config.custom_ai_instructions or '',
            'ai_model': config.ai_model,
            'content_language': config.content_language,
            'scraping_interval': config.scraping_interval,
            'max_posts_per_day': config.max_posts_per_day,
            'twitter_api_key': config.twitter_api_key or '',
            'twitter_api_secret': config.twitter_api_secret or '',
            'twitter_access_token': config.twitter_access_token or '',
            'twitter_access_secret': config.twitter_access_secret or '',
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
            'custom_ai_instructions', 'twitter_api_key', 'twitter_api_secret', 
            'twitter_access_token', 'twitter_access_secret', 'odoo_blog_id',
            'ai_model', 'content_language', 'scraping_interval', 'max_posts_per_day'
        ]
        
        vals = {k: v for k, v in data.items() if k in allowed_fields}
                
        config.write(vals)
        return {'success': True}
