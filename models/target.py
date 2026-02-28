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

    @api.model
    def cron_fetch_all_targets(self):
        """Called by Odoo Cron to fetch latest from all active targets."""
        targets = self.search([('is_active', '=', True)])
        if not targets:
            return
        
        handles = [t.handle.strip().replace('@', '') for t in targets]
        # Use our Apify Service (Hardcoded keys inside)
        tweets = self.env['smart.radar.apify.service'].run_actor_and_fetch(handles, limit_per_handle=4)
        
        if tweets:
            self._process_retrieved_tweets(tweets)

    @api.model
    def _process_retrieved_tweets(self, tweets):
        """Filters tweets by keywords and sends them to AI."""
        config = self.env['smart.radar.client.config'].get_singleton()
        keywords = (config.target_radar_focus or "").split(',')
        keywords = [k.strip().lower() for k in keywords if k.strip()]
        
        system_prompt = config.custom_ai_instructions or "Reformulate this grant opportunity into a professional post."
        
        PostObj = self.env['smart.radar.post']
        TargetObj = self.env['smart.radar.target']

        for tweet in tweets:
            # 1. Duplicate Check
            existing = PostObj.search([('source_tweet_id', '=', tweet['id'])], limit=1)
            if existing:
                continue

            # 2. Keyword Filtering (Zero-Touch logic)
            text_lower = tweet['text'].lower()
            if keywords and not any(k in text_lower for k in keywords):
                continue
            
            # 3. Identify Target
            target = TargetObj.search([('handle', 'ilike', tweet['author'])], limit=1)
            if not target:
                continue

            # 4. AI Drafting
            success, ai_text = self.env['smart.radar.openai.service'].draft_post(tweet['text'], system_prompt)
            if success:
                new_post = PostObj.create({
                    'target_id': target.id,
                    'source_tweet_id': tweet['id'],
                    'source_url': tweet['url'],
                    'original_text': tweet['text'],
                    'ai_generated_text': ai_text,
                    'state': 'draft'
                })
                
                # 5. Auto Publish if enabled
                if config.auto_approve_drafts:
                    new_post.action_publish()
