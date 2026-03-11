from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SmartRadarPost(models.Model):
    _name = 'alpha.echo.post'
    _description = 'Alpha Echo: Formulated Grants'
    _order = 'create_date desc'

    target_id = fields.Many2one(
        'alpha.echo.target', string=_('Target Entity'),
        required=True, ondelete='cascade', index=True
    )

    # ── Source Data ──────────────────────────────────────────────────
    source_url = fields.Char(string=_('Source Tweet URL'), required=True)
    source_tweet_id = fields.Char(
        string=_('Source Tweet ID'), index=True,
        help=_('Unique ID from X/Twitter — used to prevent duplicate processing.')
    )
    source_author_handle = fields.Char(
        string=_('Source Account Handle'),
        help=_('The @handle of the account that originally posted the tweet.')
    )
    source_created_at = fields.Datetime(
        string=_('Tweet Published At'),
        help=_('Original publish time of the source tweet.')
    )
    original_text = fields.Text(string=_('Raw Content (Before AI)'), required=True)

    # ── AI Output ─────────────────────────────────────────────────────
    ai_generated_text = fields.Text(string=_('AI Formulated Draft'), required=True)

    # ── Publication ───────────────────────────────────────────────────
    state = fields.Selection([
        ('draft', _('Draft (Needs Review)')),
        ('published', _('Published Successfully')),
        ('failed', _('Publishing Failed')),
        ('rejected', _('Excluded / Rejected'))
    ], string=_('Status'), default='draft', index=True)

    published_web_url = fields.Char(string=_('Published Website URL'), readonly=True)
    published_x_url = fields.Char(string=_('Published X URL'), readonly=True)
    published_by = fields.Many2one(
        'res.users', string=_('Published By'),
        readonly=True, index=True,
        help=_('The Odoo user who triggered the publish action.')
    )
    published_at = fields.Datetime(
        string=_('Published At'),
        readonly=True,
        help=_('Exact date and time the post was published to X.')
    )

    # ── SQL Constraint — absolute guarantee against duplicate tweets ──
    _sql_constraints = [
        ('unique_source_tweet_id', 'UNIQUE(source_tweet_id)',
         'A post with this Tweet ID already exists. Duplicate processing is not allowed.'),
    ]

    def action_publish(self):
        """Publishes posts to X (Twitter). Supports bulk selection with error resilience."""
        fail_count = 0
        success_count = 0
        errors = []

        for record in self:
            if record.state == 'published':
                continue

            if not record.ai_generated_text:
                record.write({'state': 'failed'})
                errors.append(_("%s: AI text is empty.") % record.target_id.name)
                fail_count += 1
                continue

            success, result = self.env['alpha.echo.x.service'].publish_tweet(
                record.ai_generated_text
            )

            if success:
                record.write({
                    'state': 'published',
                    'published_x_url': result,
                    'published_by': self.env.user.id,
                    'published_at': fields.Datetime.now(),
                })
                success_count += 1
                _logger.info(
                    "Post %d published to X by user '%s'. URL: %s",
                    record.id, self.env.user.name, result
                )
            else:
                record.write({'state': 'failed'})
                fail_count += 1
                errors.append("%s: %s" % (record.target_id.name, result))
                _logger.error("Failed to publish post %d: %s", record.id, result)

        # Summary notification
        title = _("Publishing Complete")
        message = _("Successfully published %s post(s).") % success_count
        msg_type = 'success'

        if fail_count > 0:
            title = _("Publishing Finished with Errors")
            message += _(" %s post(s) failed:\n%s") % (
                fail_count, "\n".join(errors[:3])
            )
            if len(errors) > 3:
                message += " ..."
            msg_type = 'warning'

        # Notify the frontend to refresh the view
        if success_count > 0 or fail_count > 0:
            self.env['bus.bus']._sendone('alpha_echo_updates', 'alpha_echo.post_updated', {})

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
        self.env['bus.bus']._sendone('alpha_echo_updates', 'alpha_echo.post_updated', {})

    def action_revert_to_draft(self):
        for record in self:
            record.state = 'draft'
        self.env['bus.bus']._sendone('alpha_echo_updates', 'alpha_echo.post_updated', {})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env['bus.bus']._sendone('alpha_echo_updates', 'alpha_echo.post_updated', {})
        return records
