from odoo import http
from odoo.http import request
import datetime
import base64


class AmenityPortal(http.Controller):

    @http.route('/my/amenities', type='http', auth='user', website=True)
    def amenities(self, search=None):
        domain = [('active', '=', True)]
        if search:
            domain.append(('name', 'ilike', search))

        amenities = request.env['community.amenity'].sudo().search(domain)
        return request.render('community_management.portal_amenities', {
            'amenities': amenities,
            'search': search or '',
        })

    @http.route('/my/amenities/book/<int:amenity_id>', type='http', auth='user', website=True)
    def book_amenity(self, amenity_id):
        amenity = request.env['community.amenity'].sudo().browse(amenity_id)
        return request.render('community_management.portal_amenity_book', {
            'amenity': amenity,
            'datetime': datetime
        })

    @http.route('/my/amenities/confirm', type='http', auth='user', website=True, methods=['POST'])
    def confirm_booking(self, **post):
        booking_data = {
            'amenity_id': int(post.get('amenity_id')),
            'partner_id': request.env.user.partner_id.id,
            'booking_date': post.get('booking_date'),
            'remarks': post.get('remarks', ''),
        }

        # Handle file attachment
        files = request.httprequest.files.getlist('attachments')
        if files and len(files) > 0:
            file = files[0]
            file_data = file.read()
            booking_data['attachment'] = base64.b64encode(file_data)
            booking_data['attachment_filename'] = file.filename

        booking = request.env['community.amenity.booking'].sudo().create(booking_data)

        # If paid amenity, create invoice
        if booking.amenity_id.amenity_type == 'paid':
            booking.create_invoice()
            # Just show success page, let user access invoice from their account
            return request.redirect('/my/amenities/bookings/success/%s' % booking.id)

        return request.redirect('/my/amenities/bookings/success/%s' % booking.id)

    @http.route('/my/amenities/bookings/success/<int:booking_id>', type='http', auth='user', website=True)
    def booking_success(self, booking_id):
        booking = request.env['community.amenity.booking'].sudo().browse(booking_id)
        return request.render('community_management.portal_booking_successs', {
            'booking': booking
        })

    @http.route('/my/amenities/bookings', type='http', auth='user', website=True)
    def my_bookings(self):
        bookings = request.env['community.amenity.booking'].sudo().search([
            ('partner_id', '=', request.env.user.partner_id.id)
        ], order='booking_date desc')

        # Update payment status for all bookings
        for booking in bookings:
            booking.is_payment_complete()

        return request.render('community_management.portal_my_bookings', {
            'bookings': bookings
        })