from odoo import models, fields, api, _

class SmartRadarPost(models.Model):
    _name = 'alpha.echo.post'
    _description = 'Alpha Echo: Formulated Grants'
    _order = 'create_date desc'

    target_id = fields.Many2one('alpha.echo.target', string=_('Target Entity'), required=True, ondelete='cascade')
    source_url = fields.Char(string=_('Source Tweet URL'), required=True)
    source_tweet_id = fields.Char(string=_('Source Tweet ID'), index=True)
    original_text = fields.Text(string=_('Raw Extracted Material'), required=True)
    
    ai_generated_text = fields.Text(string=_('AI Formulated Draft'), required=True)
    ai_confidence = fields.Float(string=_('AI Match Confidence'), default=92.5, help=_("How confident the AI is that this is a relevant grant."))
    
    state = fields.Selection([
        ('draft', _('Draft (Needs Review)')),
        ('published', _('Published Successfully')),
        ('failed', _('Publishing Failed')),
        ('rejected', _('Excluded / Rejected'))
    ], string=_('Status'), default='draft')

    published_web_url = fields.Char(string='Published Website URL', readonly=True)
    published_x_url = fields.Char(string='Published X URL', readonly=True)

    def action_publish(self):
        for record in self:
            success, result = self.env['alpha.echo.x.service'].publish_tweet(record.ai_generated_text)
            if success:
                record.write({
                    'state': 'published',
                    'published_x_url': result
                })
            else:
                record.write({
                    'state': 'failed'
                })
                # Log error or notify
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Publishing Failed'),
                        'message': _('Error from X: %s') % result,
                        'type': 'danger',
                    }
                }

    def action_reject(self):
        for record in self:
            record.state = 'rejected'

    def action_revert_to_draft(self):
        for record in self:
            record.state = 'draft'
