import logging
from datetime import timedelta
from odoo import models, fields, api
from odoo.fields import Date

_logger = logging.getLogger(__name__)

class DashboardMetrics(models.AbstractModel):
    _name = 'alpha.echo.dashboard'
    _description = 'Dashboard Metrics Aggregator'

    @api.model
    def get_dashboard_metrics(self):
        Target = self.env['alpha.echo.target']
        Post = self.env['alpha.echo.post']

        # Targets stats
        total_targets = Target.search_count([])
        active_targets = Target.search_count([('is_active', '=', True)])

        # Posts stats
        total_posts = Post.search_count([('state', '!=', 'rejected')])
        pending_posts = Post.search_count([('state', '=', 'draft')])
        published_posts = Post.search_count([('state', '=', 'published')])
        rejected_posts = Post.search_count([('state', '=', 'rejected')])

        # Last 7 days post activity
        seven_days_ago = Date.today() - timedelta(days=6)
        posts_history = Post.read_group(
            domain=[
                ('create_date', '>=', fields.Datetime.to_string(seven_days_ago)),
                ('state', '!=', 'rejected')
            ],
            fields=['create_date'],
            groupby=['create_date:day']
        )
        
        # Build consecutive days array to avoid empty days in chart
        daily_activity = {}
        for i in range(7):
            day = Date.to_string(Date.today() - timedelta(days=6-i))
            daily_activity[day] = 0
            
        for group in posts_history:
            day_str = group['create_date:day'] # string "YYYY-MM-DD" or similar depending on grouping
            # Parse Odoo standard grouping string back to YYYY-MM-DD format if needed, but usually Date.to_string match works
            # Let's ensure uniform structure: Odoo 17 grouping returns e.g. "2023-10-01" for :day
            if day_str in daily_activity:
                daily_activity[day_str] = group['create_date_count']

        chart_labels = list(daily_activity.keys())
        chart_data = list(daily_activity.values())

        today_str = Date.to_string(Date.today())
        posts_today = daily_activity.get(today_str, 0)

        return {
            'targets_total': total_targets,
            'targets_active': active_targets,
            'posts_total': total_posts,
            'posts_today': posts_today,
            'posts_pending': pending_posts,
            'posts_published': published_posts,
            'posts_rejected': rejected_posts,
            'chart_labels': chart_labels,
            'chart_data': chart_data,
        }
