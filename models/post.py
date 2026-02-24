from odoo import models, fields, api

class SmartRadarPost(models.Model):
    _name = 'smart.radar.post'
    _description = 'Smart Radar Formulated Grants'
    _order = 'create_date desc'

    target_id = fields.Many2one('smart.radar.target', string='Target Entity', required=True, ondelete='cascade')
    source_url = fields.Char(string='Source Tweet URL', required=True)
    original_text = fields.Text(string='Raw Extracted Material', required=True)
    
    ai_generated_text = fields.Text(string='AI Formulated Draft', required=True)
    ai_confidence = fields.Float(string='AI Match Confidence', default=92.5, help="How confident the AI is that this is a relevant grant.")
    
    state = fields.Selection([
        ('draft', 'Draft (Needs Review)'),
        ('published', 'Published Successfully'),
        ('failed', 'Publishing Failed'),
        ('rejected', 'Excluded / Rejected')
    ], string='Status', default='draft')

    published_web_url = fields.Char(string='Published Website URL', readonly=True)
    published_x_url = fields.Char(string='Published X URL', readonly=True)

    def action_publish(self):
        for record in self:
            record.state = 'published'

    def action_reject(self):
        for record in self:
            record.state = 'rejected'

    def action_revert_to_draft(self):
        for record in self:
            record.state = 'draft'
