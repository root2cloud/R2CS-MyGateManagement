# controllers/community_all_flats_portal.py

from odoo import http
from odoo.http import request

class FlatPortal(http.Controller):

    @http.route('/my/flats', type='http', auth='user', website=True, sitemap=False)
    def portal_my_flats(self, **kw):
        """
        Portal route to display all flats with availability filters.
        """
        # Use sudo() carefully - in production you should add proper access rules
        flats = request.env['flat.management'].sudo().search([])

        available_flats = flats.filtered(lambda f: f.status == 'available')
        occupied_flats = flats.filtered(lambda f: f.status == 'occupied')

        values = {
            'all_flats': flats,
            'available_flats': available_flats,
            'occupied_flats': occupied_flats,
            'page_name': 'my_flats',
        }

        return request.render('community_management.portal_my_flats', values)

    @http.route('/my/flat/<int:flat_id>', type='http', auth='user', website=True)
    def portal_flat_detail(self, flat_id, **kw):
        """
        Display detailed view of a single flat including rooms
        """
        flat = request.env['flat.management'].sudo().browse(flat_id)
        if not flat.exists():
            return request.not_found()

        return request.render('community_management.portal_flat_detail', {
            'flat': flat,
            'rooms': flat.room_ids.sorted(key=lambda r: r.name),
        })