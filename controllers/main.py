from odoo import http
from odoo.http import request
import json

class SmartRadarConfigController(http.Controller):

    @http.route('/alpha_echo/config/get', type='json', auth='user')
    def get_config(self):
        """Fetch the current configuration for the OWL UI."""
        return request.env['alpha.echo.client.config'].get_config_data()

    @http.route('/alpha_echo/config/save', type='json', auth='user')
    def save_config(self, **kw):
        """Save the updated configuration from the OWL UI."""
        return request.env['alpha.echo.client.config'].save_config_data(kw)

    @http.route('/alpha_echo/config/test_twitter', type='json', auth='user')
    def test_twitter(self):
        """Test the Twitter connection using saved config."""
        return request.env['alpha.echo.x.service'].test_connection()

    @http.route('/alpha_echo/config/sync_list', type='json', auth='user')
    def sync_list(self):
        """Trigger the X List member sync."""
        return request.env['alpha.echo.client.config'].sync_list_members()

    @http.route('/alpha_echo/config/disconnect_x', type='json', auth='user')
    def disconnect_x(self):
        """Disconnect X account."""
        return request.env['alpha.echo.client.config'].disconnect_x()
