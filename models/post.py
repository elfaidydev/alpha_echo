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

    published_web_url = fields.Char(string=_('Published Website URL'), readonly=True)
    published_x_url = fields.Char(string=_('Published X URL'), readonly=True)

    def action_publish(self):
        """Publishes posts to X (Twitter). Supports bulk selection with error resilience."""
        fail_count = 0
        success_count = 0
        errors = []

        for record in self:
            if record.state == 'published':
                continue
                
            success, result = self.env['alpha.echo.x.service'].publish_tweet(record.ai_generated_text)
            if success:
                record.write({
                    'state': 'published',
                    'published_x_url': result
                })
                success_count += 1
            else:
                record.write({'state': 'failed'})
                fail_count += 1
                errors.append(f"{record.target_id.name}: {result}")

        # Provide a summary notification
        title = _("Publishing Complete")
        message = _("Successfully published %s posts.") % success_count
        msg_type = 'success'
        
        if fail_count > 0:
            title = _("Publishing Finished with Errors")
            message += _(" %s posts failed. Errors: %s") % (fail_count, ", ".join(errors[:3]))
            if len(errors) > 3:
                message += " ..."
            msg_type = 'warning'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': msg_type,
                'sticky': fail_count > 0,
            }
        }

    def action_reject(self):
        for record in self:
            record.state = 'rejected'

    def action_revert_to_draft(self):
        for record in self:
            record.state = 'draft'
