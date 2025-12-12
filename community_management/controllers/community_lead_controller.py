from odoo import http
from odoo.http import request

class CommunityLeadController(http.Controller):

    @http.route(['/demo/page'], type='http', auth='public', website=True)
    def community_inquiry_page(self, **kwargs):
        communities = request.env['community.management'].sudo().search([])
        return request.render("community_management.demo_inquiry_form", {
            'communities': communities
        })

    @http.route(['/demo/page/submit'], type='http', auth='public', website=True, csrf=False)
    def submit_community_inquiry(self, **post):

        # Prevent GET requests from breaking the page
        if request.httprequest.method == 'GET':
            return request.redirect('/demo/page')

        # Create the lead safely (no int() conversion needed)
        request.env['community.lead'].sudo().create({
            'name': post.get('name'),
            'mobile': post.get('mobile'),
            'email': post.get('email'),
            'community_id': post.get('community_id'),  # SAFE
            'customer_type': post.get('customer_type'),
            'city': post.get('city'),
        })

        return request.render("community_management.demo_inquiry_thanks")
