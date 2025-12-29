# portal_daily_slots.py [file:d482d4f0-b544-45cf-9c97-6ad43b7b7b53] - SEARCH ADDED
from odoo import http
from odoo.http import request


class PortalDailySlots(http.Controller):

    @http.route(['/my/daily_slots'], type='http', auth="user", website=True)
    def portal_daily_slots(self, **kw):
        # 🔍 NEW: SEARCH PARAMETERS (Your existing code untouched)
        search_name = kw.get('search_name', '').strip()
        search_category = kw.get('search_category', '').strip()

        domain = [('category_custom_id', '!=', False)]

        # 🔍 NEW: NAME SEARCH
        if search_name:
            domain += [('name', 'ilike', search_name)]

        # 🔍 NEW: CATEGORY SEARCH
        if search_category:
            domain += [('category_custom_id.name', 'ilike', search_category)]

        # YOUR EXISTING CODE (unchanged)
        contacts = request.env['res.partner'].sudo().search(domain)

        slots_data = []
        for contact in contacts:
            available_slots = contact.daily_slot_ids.filtered('is_available')
            if available_slots:
                slots_data.append({
                    'contact': contact,
                    'slots': available_slots,
                })

        # 🔍 NEW: Pass search terms to template
        return request.render("community_management.portal_daily_slots_template", {
            'slots_data': slots_data,
            'search_name': search_name,
            'search_category': search_category,
            # Your existing booking route (unchanged)
        })

    # YOUR EXISTING BOOKING ROUTE (100% unchanged)
    @http.route(['/my/book_slot/<int:slot_id>'], type='http', auth="user",
                website=True, methods=['POST'], csrf=False)
    def book_slot_form(self, slot_id):
        slot = request.env['res.partner.daily.slot'].sudo().browse(slot_id)
        if slot.exists() and slot.is_available:
            slot.action_book_slot(request.env.user.partner_id.id)
            return request.render("community_management.portal_booking_success")
        return request.redirect('/my/daily_slots')
