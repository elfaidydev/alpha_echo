from odoo import http
from odoo.http import request
import json

class SmartRadarConfigController(http.Controller):

    @http.route('/smart_radar/config/get', type='json', auth='user')
    def get_config(self):
        """Fetch the current configuration for the OWL UI."""
        return request.env['smart.radar.client.config'].get_config_data()

    @http.route('/smart_radar/config/save', type='json', auth='user')
    def save_config(self, **kw):
        """Save the updated configuration from the OWL UI."""
        return request.env['smart.radar.client.config'].save_config_data(kw)

    @http.route('/smart_radar/config/test_twitter', type='json', auth='user')
    def test_twitter(self):
        """Test the Twitter connection using saved config."""
        return request.env['smart.radar.x.service'].test_connection()
