from odoo import models, fields, api

class SmartRadarTarget(models.Model):
    _name = 'smart.radar.target'
    _description = 'Smart Radar Managed Targets'
    _rec_name = 'name'

    name = fields.Char(string='Entity Name', required=True, help='Name of the organization, e.g. USAID')
    handle = fields.Char(string='X/Twitter Handle', required=True, help='e.g. @USAIDMiddleEast')
    category = fields.Selection([
        ('general', 'General Grants'),
        ('health', 'Health & Medicine'),
        ('education', 'Education & Research'),
        ('tech', 'Technology & Startups')
    ], string='Focus Area', default='general')
    is_active = fields.Boolean(string='Active for Monitoring', default=True)
    last_scanned = fields.Datetime(string='Last Scanned Date', readonly=True)
    
    # Premium Fields for Advanced UI
    image_1920 = fields.Image(string="Entity Logo")
    post_ids = fields.One2many('smart.radar.post', 'target_id', string="Grants")
    posts_count = fields.Integer(compute='_compute_posts_count', string='Total Grants Detected')

    @api.depends('post_ids')
    def _compute_posts_count(self):
        for record in self:
            record.posts_count = len(record.post_ids)

    def action_view_posts(self):
        self.ensure_one()
        return {
            'name': 'Grants & Posts',
            'res_model': 'smart.radar.post',
            'view_mode': 'tree,form',
            'domain': [('target_id', '=', self.id)],
            'context': {'default_target_id': self.id},
            'type': 'ir.actions.act_window',
        }
