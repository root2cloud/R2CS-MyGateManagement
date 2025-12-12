# File: community_management/controllers/portal_combined.py
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import base64


class CombinedPortal(CustomerPortal):

    @http.route(['/my/profile'], type='http', auth='user', website=True)
    def portal_my_profile_combined(self, **kw):
        """Single page showing Family Members + Pets + Vehicles"""
        partner = request.env.user.partner_id

        # Fetch all records belonging to the current tenant
        family_members = request.env['family.member'].search([('tenant_id', '=', partner.id)])
        pets           = request.env['pet.management'].search([('tenant_id', '=', partner.id)])
        vehicles       = request.env['vehicle.management'].search([('tenant_id', '=', partner.id)])

        flats = request.env['flat.management'].search([
            '|',
            ('tenant_id', '=', partner.id),
            ('lease_owner_id', '=', partner.id)  # in case they are owner but not living there
        ]).sorted('lease_start_date', reverse=True)

        # Optional: Highlight currently occupied flat
        current_flat = flats.filtered(lambda f: f.status == 'occupied')[:1]  # first active one

        values = {
            'family_members': family_members,
            'pets': pets,
            'vehicles': vehicles,
            'flats': flats,
            'current_flat': current_flat,
            'partner': partner,
            'page_name': 'profile',
        }

        return request.render('community_management.portal_my_profile_combined', values)

