from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import base64


class VehiclePortal(CustomerPortal):
    """Portal controller for Vehicle Management"""

    @http.route(['/my/vehicles'], type='http', auth='user', website=True)
    def portal_my_vehicles(self, **kw):
        """Display vehicles list"""
        partner = request.env.user.partner_id
        vehicles = request.env['vehicle.management'].search([('tenant_id', '=', partner.id)])

        return request.render('community_management.portal_my_vehicles', {
            'vehicles': vehicles,
            'page_name': 'vehicles',
        })

    @http.route(['/my/vehicles/new'], type='http', auth='user', website=True)
    def portal_vehicle_new(self, **kw):
        """Show form to add new vehicle"""
        return request.render('community_management.portal_vehicle_form', {
            'vehicle': None,
            'page_name': 'vehicles',
        })

    @http.route(['/my/vehicles/<int:vehicle_id>/edit'], type='http', auth='user', website=True)
    def portal_vehicle_edit(self, vehicle_id, **kw):
        """Show form to edit vehicle"""
        vehicle = request.env['vehicle.management'].browse(vehicle_id)

        if vehicle.tenant_id != request.env.user.partner_id:
            return request.redirect('/my')

        return request.render('community_management.portal_vehicle_form', {
            'vehicle': vehicle,
            'page_name': 'vehicles',
        })

    @http.route(['/my/vehicles/save'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_vehicle_save(self, vehicle_id=None, **post):
        """Save vehicle (create or update)"""
        partner = request.env.user.partner_id

        values = {
            'tenant_id': partner.id,
            'vehicle_number': post.get('vehicle_number'),
            'vehicle_type': post.get('vehicle_type'),
            'make': post.get('make') or False,
            'model': post.get('model') or False,
            'year': int(post.get('year', 0)) if post.get('year') else False,
            'color': post.get('color') or False,
            'notes': post.get('notes') or False,
        }

        # Handle photo upload
        photo_file = request.httprequest.files.get('vehicle_photo')
        if photo_file and photo_file.filename:
            values['vehicle_photo'] = base64.b64encode(photo_file.read())

        if vehicle_id and vehicle_id != 'None':
            vehicle = request.env['vehicle.management'].browse(int(vehicle_id))
            if vehicle.tenant_id == partner:
                vehicle.write(values)
        else:
            request.env['vehicle.management'].create(values)

        return request.redirect('/my/vehicles')

    @http.route(['/my/vehicles/<int:vehicle_id>/delete'], type='http', auth='user', website=True)
    def portal_vehicle_delete(self, vehicle_id, **kw):
        """Delete vehicle"""
        vehicle = request.env['vehicle.management'].browse(vehicle_id)

        if vehicle.tenant_id == request.env.user.partner_id:
            vehicle.unlink()

        return request.redirect('/my/vehicles')
