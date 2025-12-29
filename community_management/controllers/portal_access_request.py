# community_management/controllers/portal.py

import base64
from odoo import http
from odoo.http import request


class ResidentAccessRequestPortal(http.Controller):

    @http.route('/resident/request', type='http', auth='public', website=True, csrf=False)
    def resident_request_form(self, **kw):
        communities = request.env['community.management'].sudo().search([])
        occupancy_types = request.env['resident.access.request'].fields_get(['occupancy_type'])['occupancy_type']['selection']

        values = {
            'communities': communities,
            'occupancy_types': occupancy_types,
            'error': kw.get('error'),
        }
        return request.render('community_management.resident_request_template', values)

    @http.route('/resident/request/submit', type='http', auth='public', website=True, csrf=True, methods=['POST'])
    def resident_request_submit(self, **post):
        # Handle file upload
        rental_file = post.get('rental_agreement_datas')
        rental_filename = rental_file.filename if rental_file else False
        rental_datas = base64.b64encode(rental_file.read()) if rental_file else False

        # === SAFELY HANDLE OWNER_ID FROM TEXT INPUT ===
        owner_id = False
        owner_name = post.get('owner_id')
        if owner_name:
            owner_name = owner_name.strip()
            if owner_name:
                # Search for existing partner by name (case-insensitive, partial match)
                partner = request.env['res.partner'].sudo().search([
                    ('name', 'ilike', owner_name)
                ], limit=1)
                if partner:
                    owner_id = partner.id
        # =============================================

        # Prepare values
        vals = {
            'name': post.get('name'),
            'phone': post.get('phone'),
            'email': post.get('email'),
            'community_id': int(post['community_id']) if post.get('community_id') else False,
            'building_id': int(post['building_id']) if post.get('building_id') else False,
            'floor_id': int(post['floor_id']) if post.get('floor_id') and post['floor_id'] != '' else False,
            'flat_id': int(post['flat_id']) if post.get('flat_id') else False,
            'occupancy_type': post.get('occupancy_type'),
            'rental_agreement_datas': rental_datas,
            'rental_agreement_filename': rental_filename,

            # === THREE NEW FIELDS ===
            'lease_start_date': post.get('lease_start_date') or False,
            'lease_end_date': post.get('lease_end_date') or False,
            'owner_id': owner_id,  # Now safely resolved to integer ID or False
            # =========================
        }

        try:
            new_request = request.env['resident.access.request'].sudo().create(vals)
            new_request.action_submit()  # Sets to pending and notifies approver
            return request.render('community_management.resident_request_success_template')
        except Exception as e:
            return request.redirect(f"/resident/request?error={str(e)}")

    # JSON endpoints for dynamic dropdowns
    @http.route('/resident/get_buildings', type='json', auth='public')
    def get_buildings(self, community_id):
        buildings = request.env['building.management'].sudo().search([('community_id', '=', int(community_id))])
        return [{'id': b.id, 'name': b.name} for b in buildings]

    @http.route('/resident/get_floors', type='json', auth='public')
    def get_floors(self, building_id):
        floors = request.env['floor.management'].sudo().search([('building_id', '=', int(building_id))])
        return [{'id': f.id, 'name': f.name} for f in floors]

    @http.route('/resident/get_flats', type='json', auth='public')
    def get_flats(self, building_id):
        flats = request.env['flat.management'].sudo().search([('building_id', '=', int(building_id))])
        return [{'id': fl.id, 'name': fl.name} for fl in flats]