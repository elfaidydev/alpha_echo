from odoo import http
from odoo.http import request


class GrantsWebsite(http.Controller):

    @http.route('/grants', type='http', auth='public', website=True)
    def grants_list(self, filter='all', **kw):
        domain = [('website_published', '=', True)]
        # Default filter is 'all'. If filter is active/expired, apply domain.
        if filter in ('active', 'expired'):
            domain.append(('grant_state', '=', filter))

        posts = request.env['alpha.echo.post'].sudo().search(
            domain, order='create_date desc', limit=50
        )

        counts = {
            'active': request.env['alpha.echo.post'].sudo().search_count(
                [('website_published', '=', True), ('grant_state', '=', 'active')]),
            'expired': request.env['alpha.echo.post'].sudo().search_count(
                [('website_published', '=', True), ('grant_state', '=', 'expired')]),
            'all': request.env['alpha.echo.post'].sudo().search_count(
                [('website_published', '=', True)]),
        }
        
        values = {
            'posts': posts,
            'active_filter': filter,
            'counts': counts,
        }

        if kw.get('ajax'):
            return request.render('alpha_echo.grants_grid_partial', values)

        return request.render('alpha_echo.grants_page', values)

    @http.route('/grants/<string:slug>', type='http', auth='public', website=True)
    def grant_detail(self, slug, **kw):
        post = request.env['alpha.echo.post'].sudo().search(
            [('website_slug', '=', slug), ('website_published', '=', True)], limit=1
        )
        if not post:
            return request.not_found()

        return request.render('alpha_echo.grant_detail_page', {'post': post})
