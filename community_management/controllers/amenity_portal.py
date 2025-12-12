# controllers/portal.py
from odoo import http
from odoo.http import request
from datetime import date

class AmenityPortal(http.Controller):

    @http.route('/my/amenities', type='http', auth='user', website=True)
    def my_amenities(self, **kw):
        amenities = request.env['amenity.amenity'].sudo().search([('active', '=', True)])
        return request.render('amenity_booking.portal_amenities_list', {
            'amenities': amenities,
        })

    @http.route('/my/amenity/<model("amenity.amenity"):amenity>', type='http', auth='user', website=True)
    def amenity_booking_page(self, amenity, selected_date=None, **kw):
        if not selected_date:
            selected_date = date.today().strftime('%Y-%m-%d')

        all_slots = amenity.slot_ids.sorted(key=lambda s: s.start_time)
        booked = request.env['amenity.booking'].sudo().search([
            ('amenity_id', '=', amenity.id),
            ('booking_date', '=', selected_date),
            ('state', '=', 'confirmed')
        ]).mapped('time_slot_id.id')

        available_slots = all_slots.filtered(lambda s: s.id not in booked)

        return request.render('amenity_booking.portal_amenity_booking', {
            'amenity': amenity,
            'available_slots': available_slots,
            'selected_date': selected_date,
        })

    @http.route('/my/amenity/book', type='json', auth='user', website=True)
    def book_amenity_slots(self, amenity_id, booking_date, slot_ids):
        if not slot_ids:
            return {'success': False, 'message': 'Please select at least one slot.'}

        amenity = request.env['amenity.amenity'].sudo().browse(int(amenity_id))
        if not amenity.exists():
            return {'success': False, 'message': 'Amenity not found.'}

        partner = request.env.user.partner_id

        existing = request.env['amenity.booking'].sudo().search_count([
            ('amenity_id', '=', amenity.id),
            ('booking_date', '=', booking_date),
            ('time_slot_id', 'in', slot_ids),
            ('state', '=', 'confirmed')
        ])
        if existing > 0:
            return {'success': False, 'message': 'One or more slots are already booked.'}

        bookings = []
        for slot_id in slot_ids:
            booking = request.env['amenity.booking'].sudo().create({
                'amenity_id': amenity.id,
                'time_slot_id': int(slot_id),
                'booking_date': booking_date,
                'tenant_id': partner.id,
                'state': 'confirmed',
            })
            bookings.append(booking.id)

        return {'success': True, 'message': f'Successfully booked {len(bookings)} slot(s)!'}