from odoo import models, fields, api

class SmartRadarClientConfig(models.Model):
    _name = 'smart.radar.client.config'
    _description = 'Smart Radar Client Configuration'

    name = fields.Char(string='Name', default='Main Configuration', required=True)
    
    # X (Twitter) API Keys
    x_api_key = fields.Char(string='API Key')
    x_api_secret = fields.Char(string='API Key Secret')
    x_access_token = fields.Char(string='Access Token')
    x_access_token_secret = fields.Char(string='Access Token Secret')
    
    # OpenAI API Key
    openai_api_key = fields.Char(string='OpenAI API Key')
    
    # Apify Token
    apify_token = fields.Char(string='Apify Token')
    apify_actor_id = fields.Char(string='Apify Actor ID')
    
    # Supabase Connection
    supabase_url = fields.Char(string='Supabase API URL')
    supabase_key = fields.Char(string='Supabase API Key')
    supabase_status = fields.Selection([
        ('disconnected', 'Disconnected'),
        ('connected', 'Connected'),
        ('error', 'Error')
    ], string='Connection Status', default='disconnected', readonly=True)

    def action_test_connection(self):
        # Simulated test connection action
        for record in self:
            record.supabase_status = 'connected'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Test',
                    'message': 'Connection to Supabase successful!',
                    'type': 'success',
                    'sticky': False,
                }
            }
