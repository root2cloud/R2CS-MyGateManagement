# ----original perfect one
from odoo import http, fields
from odoo.http import request
import base64
import logging
import random
import string
import urllib.parse
from datetime import datetime

_logger = logging.getLogger(__name__)


class MultiPropertyPortal(http.Controller):

    @http.route(['/my/my-properties'], type='http', auth="user", website=True)
    def portal_my_properties(self, property_id=None, **kwargs):
        partner = request.env.user.partner_id

        # Get all flats where user is tenant or lease owner
        flats = request.env['flat.management'].sudo().search([
            '|',
            ('tenant_id', '=', partner.id),
            ('lease_owner_id', '=', partner.id)
        ])

        selected_flat = None
        family_members = []
        pets = []
        vehicles = []
        notices = []
        visitors = []
        child_permissions = []
        service_providers = []
        guest_invites = []
        amenities = []
        amenity_bookings = []
        party_invites = []
        delivery_passes = []
        visiting_helps = []
        visiting_categories = []
        week_days = []

        cab_preapprovals = []  # <-- NEW VARIABLE FOR CAB PRE-APPROVALS

        if property_id:
            try:
                selected_flat = request.env['flat.management'].sudo().browse(int(property_id))

                if selected_flat and selected_flat in flats:
                    family_members = request.env['family.member'].sudo().search([('flat_id', '=', selected_flat.id)])
                    pets = request.env['pet.management'].sudo().search([('flat_id', '=', selected_flat.id)])
                    vehicles = request.env['vehicle.management'].sudo().search([('flat_id', '=', selected_flat.id)])

                    # --- LOAD NOTICES ---
                    now = fields.Datetime.now()
                    domain = [
                        ('active', '=', True),
                        '|', ('community_id', '=', False), ('community_id', '=', selected_flat.community_id.id),
                        '|', ('date_start', '=', False), ('date_start', '<=', now),
                        '|', ('date_end', '=', False), ('date_end', '>=', now),
                    ]
                    raw_notices = request.env['property.notice.board'].sudo().search(domain, order='date_start desc')
                    for n in raw_notices:
                        if not n.target_flat_ids or selected_flat in n.target_flat_ids:
                            notices.append(n)

                    # --- LOAD VISITORS ---
                    visitors = request.env['mygate.visitor'].sudo().search([('flat_id', '=', selected_flat.id)],
                                                                           order='create_date desc')
                    for v in visitors:
                        if v.state == 'approved' and not v.access_code:
                            v.sudo().write({'access_code': ''.join(random.choices(string.digits, k=6))})

                    # --- LOAD CHILD EXIT PERMISSIONS ---
                    child_permissions = request.env['child.exit.permission'].sudo().search(
                        [('flat_id', '=', selected_flat.id)], order='create_date desc')

                    # --- LOAD DELIVERY PASSES ---
                    delivery_passes = request.env['community.delivery.pass'].sudo().search([
                        ('flat_id', '=', selected_flat.id)
                    ], order='create_date desc')

                    # --- LOAD VISITING HELPS ---
                    visiting_helps = request.env['community.visiting.help.entry'].sudo().search([
                        ('flat_id', '=', selected_flat.id)
                    ], order='create_date desc')

                    # Load Dropdowns for forms
                    visiting_categories = request.env['community.visiting.help.category'].sudo().search(
                        [('active', '=', True)])
                    week_days = request.env['community.week.day'].sudo().search([])







                    # --- LOAD SERVICE PROVIDERS ---
                    service_providers = request.env['res.partner'].sudo().search([
                        ('community_id', '=', selected_flat.community_id.id),
                        ('category_custom_id', '!=', False),
                        ('daily_slot_ids', '!=', False)
                    ])

                    # --- LOAD AMENITIES & BOOKINGS ---
                    amenities = request.env['community.amenity'].sudo().search([
                        ('active', '=', True),
                        '|', ('community_id', '=', False), ('community_id', '=', selected_flat.community_id.id)
                    ])
                    amenity_bookings = request.env['community.amenity.booking'].sudo().search([
                        ('flat_id', '=', selected_flat.id)
                    ], order='booking_date desc')

                    # --- LOAD GUEST INVITES ---
                    guest_invites = request.env['guest.invite'].sudo().search([
                        ('flat_id', '=', selected_flat.id)
                    ], order='create_date desc')

                    # --- LOAD PARTY GROUP INVITES ---
                    party_invites = request.env['party.group.invite'].sudo().search([
                        ('flat_id', '=', selected_flat.id)
                    ], order='create_date desc')

                    # --- LOAD CAB PRE-APPROVALS ---
                    cab_preapprovals = request.env['cab.preapproval'].sudo().search([
                        ('flat_id', '=', selected_flat.id)
                    ], order='create_date desc')

                else:
                    selected_flat = None
            except (ValueError, TypeError):
                selected_flat = None

        return request.render('community_management.portal_my_properties_template', {
            'flats': flats,
            'selected_flat': selected_flat,
            'family_members': family_members,
            'pets': pets,
            'vehicles': vehicles,
            'notices': notices,
            'visitors': visitors,
            'child_permissions': child_permissions,
            'service_providers': service_providers,
            'guest_invites': guest_invites,
            'party_invites': party_invites,
            'cab_preapprovals': cab_preapprovals,
            'page_name': 'my_properties',
            'pet_types': request.env['pet.management']._fields['pet_type'].selection,
            'genders': request.env['pet.management']._fields['gender'].selection,
            'vehicle_types': request.env['vehicle.management']._fields['vehicle_type'].selection,
            'delivery_passes': delivery_passes,
            'visiting_helps': visiting_helps,
            'visiting_categories': visiting_categories,
            'week_days': week_days,
            'delivery_modes': request.env['community.delivery.pass']._fields['mode'].selection,
            'visiting_entry_types': request.env['community.visiting.help.entry']._fields['entry_type'].selection,
            'amenities': amenities,
            'amenity_bookings': amenity_bookings,
        })

    # =====================================================
    # CAB PRE-APPROVAL PORTAL
    # =====================================================

    @http.route(['/my/cab-preapproval/create'], type='http', auth="user", website=True)
    def create_cab_preapproval(self, **post):
        """Create a new Cab Pre-Approval from the portal"""
        partner = request.env.user.partner_id

        if request.httprequest.method == 'POST':
            flat_id = post.get('flat_id')
            if not flat_id: return request.redirect('/my/my-properties?error=missing_flat_id')
            try:
                flat_id = int(flat_id)
            except:
                return request.redirect('/my/my-properties?error=invalid_flat_id')

            flat = request.env['flat.management'].sudo().search([
                '|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id), ('id', '=', flat_id)
            ], limit=1)

            if not flat: return request.redirect('/my/my-properties?error=access_denied')

            try:
                mode = post.get('mode', 'once')

                vals = {
                    'resident_id': partner.id,
                    'flat_id': flat_id,
                    'mode': mode,
                    'company_name': post.get('company_name', 'uber'),
                    'vehicle_last4': post.get('vehicle_last4', ''),
                }

                if mode == 'once':
                    vals['once_date'] = post.get('once_date')
                    vals['once_valid_hours'] = post.get('once_valid_hours', '1')
                else:
                    vals['freq_days'] = post.get('freq_days', 'all')
                    vals['freq_time_from'] = float(post.get('freq_time_from', 0.0))
                    vals['freq_time_to'] = float(post.get('freq_time_to', 23.99))
                    vals['entries_per_day'] = post.get('entries_per_day', '1')
                    vals['freq_validity'] = post.get('freq_validity', '1m')

                new_cab = request.env['cab.preapproval'].sudo().create(vals)
                new_cab.action_activate()

                return request.redirect('/my/my-properties?property_id=%s&success=cab_preapproval_created' % flat_id)

            except Exception as e:
                _logger.error("Error creating cab preapproval: %s", str(e))
                return request.redirect('/my/my-properties?property_id=%s&error=creation_failed' % flat_id)

        flat_id = post.get('flat_id') or request.params.get('flat_id')
        if not flat_id: return request.redirect('/my/my-properties?error=missing_flat_id')

        try:
            flat = request.env['flat.management'].sudo().browse(int(flat_id))
            if flat.tenant_id.id != partner.id and flat.lease_owner_id.id != partner.id:
                return request.redirect('/my/my-properties?error=access_denied')
        except:
            return request.redirect('/my/my-properties?error=invalid_flat_id')

        return request.render('community_management.portal_cab_preapproval_form', {
            'page_name': 'create_cab_preapproval',
            'flat': flat,
            'freq_days_types': request.env['cab.preapproval']._fields['freq_days'].selection,
            'freq_validity_types': request.env['cab.preapproval']._fields['freq_validity'].selection,
            'company_types': request.env['cab.preapproval']._fields['company_name'].selection,
            'valid_hours_types': request.env['cab.preapproval']._fields['once_valid_hours'].selection,
            'entries_types': request.env['cab.preapproval']._fields['entries_per_day'].selection,
        })

    @http.route(['/my/cab-preapproval/<int:cab_id>'], type='http', auth="user", website=True)
    def portal_cab_preapproval_detail(self, cab_id, **kwargs):
        """View details of a Cab Pre-Approval"""
        partner = request.env.user.partner_id
        cab = request.env['cab.preapproval'].sudo().browse(cab_id)

        if not cab.exists() or (cab.flat_id.tenant_id != partner and cab.flat_id.lease_owner_id != partner):
            return request.redirect('/my/my-properties?error=access_denied')

        return request.render('community_management.portal_cab_preapproval_detail', {
            'cab': cab,
            'flat': cab.flat_id,
            'page_name': 'cab_preapproval_detail',
        })

    @http.route(['/my/cab-preapproval/cancel/<int:cab_id>'], type='http', auth="user", website=True)
    def cancel_cab_preapproval(self, cab_id, **kwargs):
        partner = request.env.user.partner_id
        cab = request.env['cab.preapproval'].sudo().browse(cab_id)

        if cab.exists() and (cab.flat_id.tenant_id == partner or cab.flat_id.lease_owner_id == partner):
            cab.action_cancel()
            return request.redirect('/my/my-properties?property_id=%s&success=cab_cancelled' % cab.flat_id.id)

        return request.redirect('/my/my-properties?error=access_denied')

    # =====================================================
    # PARTY / GROUP INVITE PORTAL
    # =====================================================
    @http.route(['/my/party-invite/create'], type='http', auth="user", website=True)
    def create_party_invite(self, **post):
        partner = request.env.user.partner_id

        if request.httprequest.method == 'POST':
            flat_id = post.get('flat_id')
            if not flat_id: return request.redirect('/my/my-properties?error=missing_flat_id')
            try:
                flat_id = int(flat_id)
            except:
                return request.redirect('/my/my-properties?error=invalid_flat_id')

            flat = request.env['flat.management'].sudo().search([
                '|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id), ('id', '=', flat_id)
            ], limit=1)

            if not flat: return request.redirect('/my/my-properties?error=access_denied')

            try:
                vals = {
                    'name': post.get('name', 'Party Invite'),
                    'host_id': partner.id,
                    'flat_id': flat_id,
                    'event_date': post.get('event_date'),
                    'start_time': float(post.get('start_time')),
                    'valid_hours': float(post.get('valid_hours', 8.0)),
                    'max_guests': int(post.get('max_guests', 5)),
                    'location': post.get('location') or flat.name,
                    'note': post.get('note'),
                    'state': 'active'
                }

                request.env['party.group.invite'].sudo().create(vals)
                return request.redirect('/my/my-properties?property_id=%s&success=party_invite_created' % flat_id)

            except Exception as e:
                _logger.error("Error creating party invite: %s", str(e))
                return request.redirect('/my/my-properties?property_id=%s&error=creation_failed' % flat_id)

        flat_id = post.get('flat_id') or request.params.get('flat_id')
        if not flat_id: return request.redirect('/my/my-properties?error=missing_flat_id')

        try:
            flat = request.env['flat.management'].sudo().browse(int(flat_id))
            if flat.tenant_id.id != partner.id and flat.lease_owner_id.id != partner.id:
                return request.redirect('/my/my-properties?error=access_denied')
        except:
            return request.redirect('/my/my-properties?error=invalid_flat_id')

        return request.render('community_management.portal_party_invite_form', {
            'page_name': 'create_party_invite',
            'flat': flat,
        })

    @http.route(['/my/party-invite/<int:invite_id>'], type='http', auth="user", website=True)
    def portal_party_invite_detail(self, invite_id, **kwargs):
        partner = request.env.user.partner_id
        invite = request.env['party.group.invite'].sudo().browse(invite_id)

        if not invite.exists() or (invite.flat_id.tenant_id != partner and invite.flat_id.lease_owner_id != partner):
            return request.redirect('/my/my-properties?error=access_denied')

        return request.render('community_management.portal_party_invite_detail', {
            'invite': invite,
            'flat': invite.flat_id,
            'page_name': 'party_invite_detail',
        })

    @http.route(['/my/party-invite/share/<int:invite_id>'], type='http', auth="user", website=True)
    def share_party_invite_whatsapp(self, invite_id, **kwargs):
        partner = request.env.user.partner_id
        invite = request.env['party.group.invite'].sudo().browse(invite_id)

        if not invite.exists() or (invite.flat_id.tenant_id != partner and invite.flat_id.lease_owner_id != partner):
            return request.redirect('/my/my-properties?error=access_denied')

        event_date_str = invite.event_date.strftime('%d/%m/%Y') if invite.event_date else 'TBD'
        start_time_str = '%02d:%02d' % (
        int(invite.start_time), int(round((invite.start_time % 1) * 60))) if invite.start_time else 'TBD'

        message = f"🎉 *YOU ARE INVITED!*\n\n📝 *Event:* {invite.name}\n👤 *Host:* {invite.host_id.name}\n📅 *Date:* {event_date_str}\n⏰ *Time:* {start_time_str}\n📍 *Location:* {invite.location or invite.flat_id.name}\n👥 *Max Guests allowed:* {invite.max_guests}\n\n🔑 *Entry Token:* {invite.token}\n\n"
        if invite.note:
            message += f"💡 *Note:* {invite.note}\n\n"
        message += f"✅ Please show the Entry Token at the gate to get access!"

        encoded_message = urllib.parse.quote(message)
        whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_message}"

        return request.redirect(whatsapp_url, local=False)

    # =====================================================
    # GUEST INVITE (PRE-APPROVAL) PORTAL
    # =====================================================
    @http.route(['/my/guest-invite/create'], type='http', auth="user", website=True)
    def create_guest_invite(self, **post):
        partner = request.env.user.partner_id

        if request.httprequest.method == 'POST':
            flat_id = post.get('flat_id')
            if not flat_id: return request.redirect('/my/my-properties?error=missing_flat_id')

            try:
                flat_id = int(flat_id)
            except:
                return request.redirect('/my/my-properties?error=invalid_flat_id')

            flat = request.env['flat.management'].sudo().search([
                '|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id), ('id', '=', flat_id)
            ], limit=1)

            if not flat: return request.redirect('/my/my-properties?error=access_denied')

            try:
                invite_type = post.get('invite_type', 'once')

                invite_vals = {
                    'resident_id': partner.id,
                    'flat_id': flat_id,
                    'invite_type': invite_type,
                    'note': post.get('note'),
                    'is_private': bool(post.get('is_private')),
                }

                if invite_type == 'once':
                    invite_vals['once_date'] = post.get('once_date')
                    invite_vals['once_start_time'] = float(post.get('once_start_time'))
                    invite_vals['once_valid_hours'] = int(post.get('once_valid_hours', 8))
                else:
                    invite_vals['duration_type'] = post.get('duration_type')
                    invite_vals['freq_start_date'] = post.get('freq_start_date') or fields.Date.context_today(
                        request.env.user)

                new_invite = request.env['guest.invite'].sudo().create(invite_vals)

                request.env['guest.invite.line'].sudo().create({
                    'invite_id': new_invite.id,
                    'guest_name': post.get('guest_name'),
                    'guest_mobile': post.get('guest_mobile')
                })

                new_invite.action_compute_window()

                return request.redirect('/my/my-properties?property_id=%s&success=guest_invite_created' % flat_id)

            except Exception as e:
                _logger.error("Error creating guest invite: %s", str(e))
                return request.redirect('/my/my-properties?property_id=%s&error=creation_failed' % flat_id)

        flat_id = post.get('flat_id') or request.params.get('flat_id')
        if not flat_id: return request.redirect('/my/my-properties?error=missing_flat_id')

        try:
            flat = request.env['flat.management'].sudo().browse(int(flat_id))
            if flat.tenant_id.id != partner.id and flat.lease_owner_id.id != partner.id:
                return request.redirect('/my/my-properties?error=access_denied')
        except:
            return request.redirect('/my/my-properties?error=invalid_flat_id')

        return request.render('community_management.portal_guest_invite_form', {
            'page_name': 'create_guest_invite',
            'flat': flat,
            'duration_types': request.env['guest.invite']._fields['duration_type'].selection,
        })

    @http.route(['/my/guest-invite/share/<int:invite_id>'], type='http', auth="user", website=True)
    def share_guest_invite_whatsapp(self, invite_id, **kwargs):
        partner = request.env.user.partner_id
        invite = request.env['guest.invite'].sudo().browse(invite_id)

        if not invite.exists() or (invite.flat_id.tenant_id != partner and invite.flat_id.lease_owner_id != partner):
            return request.redirect('/my/my-properties?error=access_denied')

        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        portal_url = f"{base_url}/my/guest/invites/invite/{invite.id}"

        guests = ", ".join([f"{line.guest_name} ({line.guest_mobile})" for line in invite.guest_line_ids])
        start_str = invite.start_datetime.strftime('%d/%m %H:%M') if invite.start_datetime else 'N/A'
        end_str = invite.end_datetime.strftime('%d/%m %H:%M') if invite.end_datetime else 'N/A'

        message = f"🔔 GATE ENTRY INVITE\n\n🔑 OTP: {invite.otpcode}\n👤 Resident: {invite.resident_id.name}\n📅 Valid: {start_str} - {end_str}\n👥 Guests: {guests or 'Not specified'}\n\n🔗 Details: {portal_url}\n\n✅ Show OTP at gate!"
        encoded_message = urllib.parse.quote(message)

        phone = ""
        if invite.guest_line_ids and invite.guest_line_ids[0].guest_mobile:
            phone = ''.join(filter(str.isdigit, invite.guest_line_ids[0].guest_mobile))

        if phone:
            whatsapp_url = f"https://api.whatsapp.com/send?phone={phone}&text={encoded_message}"
        else:
            whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_message}"

        return request.redirect(whatsapp_url, local=False)

    # =====================================================
    # BOOK SERVICE SLOTS
    # =====================================================
    @http.route(['/my/service/book/<int:slot_id>'], type='http', auth="user", website=True)
    def portal_book_service(self, slot_id, flat_id=None, **kwargs):
        partner = request.env.user.partner_id
        slot = request.env['res.partner.daily.slot'].sudo().browse(slot_id)

        if not slot.exists():
            return request.redirect('/my/my-properties?error=slot_not_found')

        if slot.is_available:
            slot.action_book_slot(partner.id)
            if flat_id:
                return request.redirect('/my/my-properties?property_id=%s&success=slot_booked' % flat_id)
            return request.redirect('/my/my-properties?success=slot_booked')
        else:
            if flat_id:
                return request.redirect('/my/my-properties?property_id=%s&error=slot_already_booked' % flat_id)
            return request.redirect('/my/my-properties?error=slot_already_booked')

    # =====================================================
    # CHILD EXIT PERMISSION PORTAL
    # =====================================================
    @http.route(['/my/child-exit/create'], type='http', auth="user", website=True)
    def create_child_exit(self, **post):
        partner = request.env.user.partner_id

        if request.httprequest.method == 'POST':
            flat_id = post.get('flat_id')
            if not flat_id: return request.redirect('/my/my-properties?error=missing_flat_id')
            try:
                flat_id = int(flat_id)
            except (ValueError, TypeError):
                return request.redirect('/my/my-properties?error=invalid_flat_id')

            flat = request.env['flat.management'].sudo().search([
                '|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id),
                ('id', '=', flat_id)
            ], limit=1)

            if not flat: return request.redirect('/my/my-properties?error=access_denied')

            time_str = post.get('allowed_exit_time')
            if time_str:
                formatted_time = time_str.replace('T', ' ')
                if len(formatted_time) == 16:
                    formatted_time += ':00'
            else:
                formatted_time = fields.Datetime.now()

            try:
                vals = {
                    'tenant_id': partner.id,
                    'flat_id': flat_id,
                    'child_id': int(post.get('child_id')),
                    'purpose': post.get('purpose'),
                    'allowed_exit_time': formatted_time,
                    'duration_hours': post.get('duration_hours'),
                    'state': 'active'
                }
                request.env['child.exit.permission'].sudo().create(vals)
                return request.redirect('/my/my-properties?property_id=%s&success=child_exit_created' % flat_id)

            except Exception as e:
                _logger.error("Error creating child exit permission: %s", str(e))
                return request.redirect('/my/my-properties?property_id=%s&error=creation_failed' % flat_id)

        flat_id = post.get('flat_id') or request.params.get('flat_id')
        if not flat_id: return request.redirect('/my/my-properties?error=missing_flat_id')

        try:
            flat = request.env['flat.management'].sudo().browse(int(flat_id))
            if flat.tenant_id.id != partner.id and flat.lease_owner_id.id != partner.id:
                return request.redirect('/my/my-properties?error=access_denied')
            children = request.env['family.member'].sudo().search(
                [('flat_id', '=', flat.id), ('member_type', '=', 'child')])
        except (ValueError, TypeError):
            return request.redirect('/my/my-properties?error=invalid_flat_id')

        return request.render('community_management.portal_child_exit_form', {
            'page_name': 'create_child_exit',
            'flat': flat,
            'children': children,
            'durations': request.env['child.exit.permission']._fields['duration_hours'].selection,
        })

    # =====================================================
    # VISITOR DETAIL & APPROVAL PORTAL
    # =====================================================
    @http.route(['/my/visitor/<int:visitor_id>'], type='http', auth="user", website=True)
    def portal_visitor_detail(self, visitor_id, **kwargs):
        partner = request.env.user.partner_id
        visitor = request.env['mygate.visitor'].sudo().browse(visitor_id)
        if not visitor.exists(): return request.redirect('/my/my-properties?error=visitor_not_found')
        if visitor.flat_id.tenant_id != partner and visitor.flat_id.lease_owner_id != partner:
            return request.redirect('/my/my-properties?error=access_denied')
        if visitor.state == 'approved' and not visitor.access_code:
            visitor.sudo().write({'access_code': ''.join(random.choices(string.digits, k=6))})
        return request.render('community_management.portal_visitor_detail', {
            'visitor': visitor, 'flat': visitor.flat_id, 'page_name': 'visitor_detail',
        })

    @http.route(['/my/visitor/approve/<int:visitor_id>'], type='http', auth="user", website=True)
    def portal_visitor_approve(self, visitor_id, **kwargs):
        partner = request.env.user.partner_id
        visitor = request.env['mygate.visitor'].sudo().browse(visitor_id)
        if visitor.exists() and (visitor.flat_id.tenant_id == partner or visitor.flat_id.lease_owner_id == partner):
            if visitor.state == 'pending':
                if hasattr(visitor, 'action_approve'):
                    visitor.action_approve()
                else:
                    access_code = ''.join(random.choices(string.digits, k=6))
                    visitor.sudo().write({'state': 'approved', 'access_code': access_code})
            return request.redirect('/my/visitor/%s?success=approved' % visitor.id)
        return request.redirect('/my/my-properties?error=access_denied')

    @http.route(['/my/visitor/reject/<int:visitor_id>'], type='http', auth="user", website=True)
    def portal_visitor_reject(self, visitor_id, **kwargs):
        partner = request.env.user.partner_id
        visitor = request.env['mygate.visitor'].sudo().browse(visitor_id)
        if visitor.exists() and (visitor.flat_id.tenant_id == partner or visitor.flat_id.lease_owner_id == partner):
            if visitor.state == 'pending':
                if hasattr(visitor, 'action_reject'):
                    visitor.action_reject()
                else:
                    visitor.sudo().write({'state': 'rejected'})
            return request.redirect('/my/visitor/%s?success=rejected' % visitor.id)
        return request.redirect('/my/my-properties?error=access_denied')

    # =====================================================
    # NOTICE BOARD DETAIL PORTAL
    # =====================================================
    @http.route(['/my/notice/<int:notice_id>'], type='http', auth="user", website=True)
    def portal_notice_detail(self, notice_id, flat_id=None, **kwargs):
        notice = request.env['property.notice.board'].sudo().browse(notice_id)
        if not notice.exists(): return request.redirect('/my/my-properties?error=notice_not_found')
        flat = None
        if flat_id:
            try:
                flat = request.env['flat.management'].sudo().browse(int(flat_id))
            except (ValueError, TypeError):
                pass
        return request.render('community_management.portal_notice_detail', {
            'notice': notice, 'flat': flat, 'page_name': 'notice_detail',
        })

    # =====================================================
    # FAMILY MEMBER MANAGEMENT
    # =====================================================
    @http.route(['/my/family-member/create'], type='http', auth="user", website=True)
    def create_family_member(self, **post):
        partner = request.env.user.partner_id
        if request.httprequest.method == 'POST':
            flat_id = post.get('flat_id')
            if not flat_id: return request.redirect('/my/my-properties?error=missing_flat_id')
            try:
                flat_id = int(flat_id)
            except (ValueError, TypeError):
                return request.redirect('/my/my-properties?error=invalid_flat_id')
            flat = request.env['flat.management'].sudo().search(
                ['|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id), ('id', '=', flat_id)],
                limit=1)
            if not flat: return request.redirect('/my/my-properties?error=access_denied')
            photo = False
            if post.get('photo') and hasattr(post.get('photo'), 'read'):
                try:
                    photo = base64.b64encode(post.get('photo').read())
                except Exception as e:
                    _logger.error("Error processing photo: %s", str(e))
                    photo = False
            try:
                member_vals = {
                    'tenant_id': partner.id, 'flat_id': flat_id, 'name': post.get('name'),
                    'member_type': post.get('member_type'),
                    'gender': post.get('gender'), 'date_of_birth': post.get('date_of_birth'),
                    'relationship': post.get('relationship'),
                    'email': post.get('email'), 'phone': post.get('phone'),
                    'aadhaar_number': post.get('aadhaar_number'),
                    'notes': post.get('notes'), 'photo': photo,
                }
                member_vals = {k: v for k, v in member_vals.items() if v}
                new_member = request.env['family.member'].sudo().create(member_vals)
                return request.redirect('/my/my-properties?property_id=%s&success=created' % flat_id)
            except Exception as e:
                _logger.error("Error creating family member: %s", str(e))
                return request.redirect('/my/my-properties?property_id=%s&error=creation_failed' % flat_id)

        flat_id = post.get('flat_id')
        if not flat_id: return request.redirect('/my/my-properties?error=missing_flat_id')
        try:
            flat = request.env['flat.management'].sudo().browse(int(flat_id))
            if flat.tenant_id.id != partner.id and flat.lease_owner_id.id != partner.id: return request.redirect(
                '/my/my-properties?error=access_denied')
        except (ValueError, TypeError):
            return request.redirect('/my/my-properties?error=invalid_flat_id')
        return request.render('community_management.portal_family_member_form', {
            'page_name': 'create_family_member', 'flat': flat, 'member': False,
            'relationships': request.env['family.member']._fields['relationship'].selection,
            'genders': request.env['family.member']._fields['gender'].selection,
            'member_types': request.env['family.member']._fields['member_type'].selection,
        })

    @http.route(['/my/family-member/edit/<int:member_id>'], type='http', auth="user", website=True)
    def edit_family_member(self, member_id, **post):
        partner = request.env.user.partner_id
        member = request.env['family.member'].sudo().browse(member_id)
        if not member.exists(): return request.redirect('/my/my-properties?error=member_not_found')
        if member.tenant_id.id != partner.id: return request.redirect('/my/my-properties?error=access_denied')
        if request.httprequest.method == 'POST':
            photo = member.photo
            if post.get('photo') and hasattr(post.get('photo'), 'read'):
                try:
                    photo = base64.b64encode(post.get('photo').read())
                except Exception as e:
                    photo = member.photo
            try:
                member_vals = {
                    'name': post.get('name'), 'member_type': post.get('member_type'), 'gender': post.get('gender'),
                    'date_of_birth': post.get('date_of_birth'), 'relationship': post.get('relationship'),
                    'email': post.get('email'), 'phone': post.get('phone'),
                    'aadhaar_number': post.get('aadhaar_number'),
                    'notes': post.get('notes'), 'photo': photo,
                }
                member_vals = {k: v for k, v in member_vals.items() if v is not None}
                member.write(member_vals)
                return request.redirect('/my/my-properties?property_id=%s&success=updated' % member.flat_id.id)
            except Exception as e:
                return request.redirect('/my/my-properties?property_id=%s&error=update_failed' % member.flat_id.id)
        return request.render('community_management.portal_family_member_form', {
            'page_name': 'edit_family_member', 'member': member, 'flat': member.flat_id,
            'relationships': request.env['family.member']._fields['relationship'].selection,
            'genders': request.env['family.member']._fields['gender'].selection,
            'member_types': request.env['family.member']._fields['member_type'].selection,
        })

    @http.route(['/my/family-member/delete/<int:member_id>'], type='http', auth="user", website=True)
    def delete_family_member(self, member_id, **post):
        partner = request.env.user.partner_id
        member = request.env['family.member'].sudo().browse(member_id)
        if not member.exists(): return request.redirect('/my/my-properties?error=member_not_found')
        if member.tenant_id.id != partner.id: return request.redirect('/my/my-properties?error=access_denied')
        flat_id = member.flat_id.id
        try:
            member.unlink()
            return request.redirect('/my/my-properties?property_id=%s&success=deleted' % flat_id)
        except Exception as e:
            return request.redirect('/my/my-properties?property_id=%s&error=delete_failed' % flat_id)

    @http.route(['/my/family-member/view-qr/<int:member_id>'], type='http', auth="user", website=True)
    def view_family_member_qr(self, member_id, **kwargs):
        partner = request.env.user.partner_id
        member = request.env['family.member'].sudo().browse(member_id)
        if not member.exists(): return request.redirect('/my/my-properties?error=member_not_found')
        if member.tenant_id.id != partner.id: return request.redirect('/my/my-properties?error=access_denied')
        return request.render('community_management.portal_qr_code_download',
                              {'member': member, 'page_name': 'qr_code_download'})

    @http.route(['/my/family-member/download-qr/<int:member_id>'], type='http', auth="user", website=True)
    def download_family_member_qr(self, member_id, **kwargs):
        partner = request.env.user.partner_id
        member = request.env['family.member'].sudo().browse(member_id)
        if not member.exists(): return request.redirect('/my/my-properties?error=member_not_found')
        if member.tenant_id.id != partner.id: return request.redirect('/my/my-properties?error=access_denied')
        if member.qr_code_image:
            try:
                if isinstance(member.qr_code_image, bytes):
                    image_data = base64.b64decode(member.qr_code_image)
                else:
                    image_data = base64.b64decode(member.qr_code_image.encode('utf-8'))
                filename = "QR_%s_%s.png" % (member.resident_id or 'member', member.name.replace(' ', '_'))
                headers = [('Content-Type', 'image/png'),
                           ('Content-Disposition', 'attachment; filename="%s"' % filename),
                           ('Content-Length', str(len(image_data)))]
                return request.make_response(image_data, headers)
            except Exception as e:
                return request.redirect('/my/my-properties?property_id=%s&error=qr_download_failed' % member.flat_id.id)
        else:
            return request.redirect('/my/my-properties?property_id=%s&error=qr_not_found' % member.flat_id.id)

    @http.route(['/my/family-member/generate-all-qr'], type='http', auth="user", website=True)
    def generate_all_qr_codes(self, **kwargs):
        partner = request.env.user.partner_id
        family_members = request.env['family.member'].sudo().search([('tenant_id', '=', partner.id)])
        count = 0
        for member in family_members:
            try:
                if not member.qr_code_image and member.resident_id:
                    member.generate_qr_code_image()
                    count += 1
            except Exception as e:
                _logger.error("Error generating QR for member %s: %s", member.name, str(e))
        return request.redirect('/my/my-properties?success=qr_generated&count=%s' % count)

    # =====================================================
    # PET MANAGEMENT PORTAL
    # =====================================================
    @http.route(['/my/pet/create'], type='http', auth="user", website=True)
    def create_pet(self, **post):
        partner = request.env.user.partner_id
        if request.httprequest.method == 'POST':
            flat_id = post.get('flat_id')
            if not flat_id: return request.redirect('/my/my-properties?error=missing_flat_id')
            try:
                flat_id = int(flat_id)
            except (ValueError, TypeError):
                return request.redirect('/my/my-properties?error=invalid_flat_id')
            flat = request.env['flat.management'].sudo().search(
                ['|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id), ('id', '=', flat_id)],
                limit=1)
            if not flat: return request.redirect('/my/my-properties?error=access_denied')
            photo = False
            if post.get('photo') and hasattr(post.get('photo'), 'read'):
                try:
                    photo = base64.b64encode(post.get('photo').read())
                except Exception:
                    photo = False
            try:
                pet_vals = {
                    'tenant_id': partner.id, 'flat_id': flat_id, 'name': post.get('name'),
                    'pet_type': post.get('pet_type'),
                    'breed': post.get('breed'), 'color': post.get('color'), 'gender': post.get('gender'),
                    'date_of_birth': post.get('date_of_birth'), 'weight': post.get('weight'),
                    'microchip_number': post.get('microchip_number'), 'license_number': post.get('license_number'),
                    'last_vaccination_date': post.get('last_vaccination_date'),
                    'next_vaccination_date': post.get('next_vaccination_date'),
                    'veterinarian': post.get('veterinarian'), 'vet_phone': post.get('vet_phone'),
                    'medical_conditions': post.get('medical_conditions'), 'allergies': post.get('allergies'),
                    'special_needs': post.get('special_needs'), 'notes': post.get('notes'), 'photo': photo,
                }
                pet_vals = {k: v for k, v in pet_vals.items() if v}
                request.env['pet.management'].sudo().create(pet_vals)
                return request.redirect('/my/my-properties?property_id=%s&success=pet_created' % flat_id)
            except Exception:
                return request.redirect('/my/my-properties?property_id=%s&error=creation_failed' % flat_id)

        flat_id = post.get('flat_id')
        if not flat_id: return request.redirect('/my/my-properties?error=missing_flat_id')
        try:
            flat = request.env['flat.management'].sudo().browse(int(flat_id))
            if flat.tenant_id.id != partner.id and flat.lease_owner_id.id != partner.id: return request.redirect(
                '/my/my-properties?error=access_denied')
        except (ValueError, TypeError):
            return request.redirect('/my/my-properties?error=invalid_flat_id')
        return request.render('community_management.portal_pet_form', {
            'page_name': 'create_pet', 'flat': flat, 'pet': False,
            'pet_types': request.env['pet.management']._fields['pet_type'].selection,
            'genders': request.env['pet.management']._fields['gender'].selection,
        })

    @http.route(['/my/pet/edit/<int:pet_id>'], type='http', auth="user", website=True)
    def edit_pet(self, pet_id, **post):
        partner = request.env.user.partner_id
        pet = request.env['pet.management'].sudo().browse(pet_id)
        if not pet.exists(): return request.redirect('/my/my-properties?error=pet_not_found')
        if pet.tenant_id.id != partner.id: return request.redirect('/my/my-properties?error=access_denied')
        if request.httprequest.method == 'POST':
            photo = pet.photo
            if post.get('photo') and hasattr(post.get('photo'), 'read'):
                try:
                    photo = base64.b64encode(post.get('photo').read())
                except Exception:
                    photo = pet.photo
            try:
                pet_vals = {
                    'name': post.get('name'), 'pet_type': post.get('pet_type'), 'breed': post.get('breed'),
                    'color': post.get('color'), 'gender': post.get('gender'),
                    'date_of_birth': post.get('date_of_birth'),
                    'weight': post.get('weight'), 'microchip_number': post.get('microchip_number'),
                    'license_number': post.get('license_number'),
                    'last_vaccination_date': post.get('last_vaccination_date'),
                    'next_vaccination_date': post.get('next_vaccination_date'),
                    'veterinarian': post.get('veterinarian'), 'vet_phone': post.get('vet_phone'),
                    'medical_conditions': post.get('medical_conditions'), 'allergies': post.get('allergies'),
                    'special_needs': post.get('special_needs'), 'notes': post.get('notes'), 'photo': photo,
                }
                pet_vals = {k: v for k, v in pet_vals.items() if v is not None}
                pet.write(pet_vals)
                return request.redirect('/my/my-properties?property_id=%s&success=pet_updated' % pet.flat_id.id)
            except Exception:
                return request.redirect('/my/my-properties?property_id=%s&error=update_failed' % pet.flat_id.id)
        return request.render('community_management.portal_pet_form', {
            'page_name': 'edit_pet', 'pet': pet, 'flat': pet.flat_id,
            'pet_types': request.env['pet.management']._fields['pet_type'].selection,
            'genders': request.env['pet.management']._fields['gender'].selection,
        })

    @http.route(['/my/pet/delete/<int:pet_id>'], type='http', auth="user", website=True)
    def delete_pet(self, pet_id, **post):
        partner = request.env.user.partner_id
        pet = request.env['pet.management'].sudo().browse(pet_id)
        if not pet.exists(): return request.redirect('/my/my-properties?error=pet_not_found')
        if pet.tenant_id.id != partner.id: return request.redirect('/my/my-properties?error=access_denied')
        flat_id = pet.flat_id.id
        try:
            pet.unlink()
            return request.redirect('/my/my-properties?property_id=%s&success=pet_deleted' % flat_id)
        except Exception:
            return request.redirect('/my/my-properties?property_id=%s&error=delete_failed' % flat_id)

    # =====================================================
    # VEHICLE MANAGEMENT PORTAL
    # =====================================================
    @http.route(['/my/vehicle/create'], type='http', auth="user", website=True)
    def create_vehicle(self, **post):
        partner = request.env.user.partner_id
        if request.httprequest.method == 'POST':
            flat_id = post.get('flat_id')
            if not flat_id: return request.redirect('/my/my-properties?error=missing_flat_id')
            try:
                flat_id = int(flat_id)
            except (ValueError, TypeError):
                return request.redirect('/my/my-properties?error=invalid_flat_id')
            flat = request.env['flat.management'].sudo().search(
                ['|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id), ('id', '=', flat_id)],
                limit=1)
            if not flat: return request.redirect('/my/my-properties?error=access_denied')
            vehicle_photo = False
            if post.get('vehicle_photo') and hasattr(post.get('vehicle_photo'), 'read'):
                try:
                    vehicle_photo = base64.b64encode(post.get('vehicle_photo').read())
                except Exception:
                    vehicle_photo = False
            try:
                vehicle_vals = {
                    'tenant_id': partner.id, 'flat_id': flat_id, 'vehicle_number': post.get('vehicle_number'),
                    'vehicle_type': post.get('vehicle_type'), 'make': post.get('make'), 'model': post.get('model'),
                    'year': post.get('year') or 0, 'color': post.get('color'), 'notes': post.get('notes'),
                    'vehicle_photo': vehicle_photo,
                }
                vehicle_vals = {k: v for k, v in vehicle_vals.items() if v}
                request.env['vehicle.management'].sudo().create(vehicle_vals)
                return request.redirect('/my/my-properties?property_id=%s&success=vehicle_created' % flat_id)
            except Exception:
                return request.redirect('/my/my-properties?property_id=%s&error=creation_failed' % flat_id)

        flat_id = post.get('flat_id')
        if not flat_id: return request.redirect('/my/my-properties?error=missing_flat_id')
        try:
            flat = request.env['flat.management'].sudo().browse(int(flat_id))
            if flat.tenant_id.id != partner.id and flat.lease_owner_id.id != partner.id: return request.redirect(
                '/my/my-properties?error=access_denied')
        except (ValueError, TypeError):
            return request.redirect('/my/my-properties?error=invalid_flat_id')
        return request.render('community_management.portal_vehicle_form', {
            'page_name': 'create_vehicle', 'flat': flat, 'vehicle': False,
            'vehicle_types': request.env['vehicle.management']._fields['vehicle_type'].selection,
        })

    @http.route(['/my/vehicle/edit/<int:vehicle_id>'], type='http', auth="user", website=True)
    def edit_vehicle(self, vehicle_id, **post):
        partner = request.env.user.partner_id
        vehicle = request.env['vehicle.management'].sudo().browse(vehicle_id)
        if not vehicle.exists(): return request.redirect('/my/my-properties?error=vehicle_not_found')
        if vehicle.tenant_id.id != partner.id: return request.redirect('/my/my-properties?error=access_denied')
        if request.httprequest.method == 'POST':
            vehicle_photo = vehicle.vehicle_photo
            if post.get('vehicle_photo') and hasattr(post.get('vehicle_photo'), 'read'):
                try:
                    vehicle_photo = base64.b64encode(post.get('vehicle_photo').read())
                except Exception:
                    vehicle_photo = vehicle.vehicle_photo
            try:
                vehicle_vals = {
                    'vehicle_number': post.get('vehicle_number'), 'vehicle_type': post.get('vehicle_type'),
                    'make': post.get('make'), 'model': post.get('model'), 'year': post.get('year') or 0,
                    'color': post.get('color'), 'notes': post.get('notes'), 'vehicle_photo': vehicle_photo,
                }
                vehicle_vals = {k: v for k, v in vehicle_vals.items() if v is not None}
                vehicle.write(vehicle_vals)
                return request.redirect('/my/my-properties?property_id=%s&success=vehicle_updated' % vehicle.flat_id.id)
            except Exception:
                return request.redirect('/my/my-properties?property_id=%s&error=update_failed' % vehicle.flat_id.id)
        return request.render('community_management.portal_vehicle_form', {
            'page_name': 'edit_vehicle', 'vehicle': vehicle, 'flat': vehicle.flat_id,
            'vehicle_types': request.env['vehicle.management']._fields['vehicle_type'].selection,
        })

    @http.route(['/my/vehicle/delete/<int:vehicle_id>'], type='http', auth="user", website=True)
    def delete_vehicle(self, vehicle_id, **post):
        partner = request.env.user.partner_id
        vehicle = request.env['vehicle.management'].sudo().browse(vehicle_id)
        if not vehicle.exists(): return request.redirect('/my/my-properties?error=vehicle_not_found')
        if vehicle.tenant_id.id != partner.id: return request.redirect('/my/my-properties?error=access_denied')
        flat_id = vehicle.flat_id.id
        try:
            vehicle.unlink()
            return request.redirect('/my/my-properties?property_id=%s&success=vehicle_deleted' % flat_id)
        except Exception:
            return request.redirect('/my/my-properties?property_id=%s&error=delete_failed' % flat_id)

    # =====================================================
    # DELIVERY PASS PORTAL
    # =====================================================
    @http.route(['/my/delivery-pass/create'], type='http', auth="user", website=True)
    def create_delivery_pass(self, **post):
        partner = request.env.user.partner_id
        if request.httprequest.method == 'POST':
            flat_id = post.get('flat_id')
            if not flat_id: return request.redirect('/my/my-properties?error=missing_flat_id')

            flat = request.env['flat.management'].sudo().search([
                '|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id), ('id', '=', int(flat_id))
            ], limit=1)
            if not flat: return request.redirect('/my/my-properties?error=access_denied')

            try:
                mode = post.get('mode', 'once')
                vals = {
                    'resident_id': partner.id,
                    'flat_id': flat.id,
                    'mode': mode,
                    'company_name': post.get('company_name'),
                    'is_surprise': bool(post.get('is_surprise')),
                    'allow_leave_at_gate': bool(post.get('allow_leave_at_gate')),
                    'state': 'active'
                }

                if mode == 'once':
                    vals['once_date'] = post.get('once_date') or fields.Date.context_today(request.env.user)
                    start_val = post.get('once_start_time')
                    vals['once_start_time'] = float(start_val) if start_val else 0.0

                    # FIX: Safely parse as string for Selection field
                    hrs_val = post.get('once_valid_hours')
                    vals['once_valid_hours'] = str(hrs_val) if hrs_val else '1'
                else:
                    vals['freq_validity'] = post.get('freq_validity', '1m')

                request.env['community.delivery.pass'].sudo().create(vals)
                return request.redirect(f'/my/my-properties?property_id={flat.id}&success=delivery_pass_created')
            except Exception as e:
                _logger.error("Error creating delivery pass: %s", str(e))
                return request.redirect(f'/my/my-properties?property_id={flat.id}&error=creation_failed')

        flat_id = post.get('flat_id') or request.params.get('flat_id')
        flat = request.env['flat.management'].sudo().browse(int(flat_id))
        return request.render('community_management.portal_delivery_pass_form', {
            'page_name': 'create_delivery_pass', 'flat': flat,
            'validity_types': request.env['community.delivery.pass']._fields['freq_validity'].selection
        })

    # =====================================================
    # VISITING HELP PORTAL
    # =====================================================
    @http.route(['/my/visiting-help/create'], type='http', auth="user", website=True)
    def create_visiting_help(self, **post):
        partner = request.env.user.partner_id
        if request.httprequest.method == 'POST':
            flat_id = post.get('flat_id')
            flat = request.env['flat.management'].sudo().search([
                '|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id), ('id', '=', int(flat_id))
            ], limit=1)
            if not flat: return request.redirect('/my/my-properties?error=access_denied')

            try:
                entry_type = post.get('entry_type', 'once')
                vals = {
                    'tenant_id': partner.id,
                    'flat_id': flat.id,
                    'category_id': int(post.get('category_id')),
                    'company_name': post.get('company_name'),
                    'entry_type': entry_type,
                }

                if entry_type == 'once':
                    vals['visit_date'] = post.get('visit_date') or fields.Date.context_today(request.env.user)
                    start_val = post.get('start_time')
                    vals['start_time'] = float(start_val) if start_val else 0.0
                    vals['valid_for'] = post.get('valid_for', '1')
                else:
                    day_ids = request.httprequest.form.getlist('day_ids')
                    if day_ids:
                        vals['day_ids'] = [(6, 0, [int(d) for d in day_ids if d])]

                    vals['validity'] = post.get('validity', '1m')

                    tf_val = post.get('time_from')
                    vals['time_from'] = float(tf_val) if tf_val else 0.0

                    tt_val = post.get('time_to')
                    vals['time_to'] = float(tt_val) if tt_val else 23.99

                    # FIX: parse as string for Selection field
                    entries_val = post.get('entries_per_day')
                    vals['entries_per_day'] = str(entries_val) if entries_val else 'one'

                request.env['community.visiting.help.entry'].sudo().create(vals)
                return request.redirect(f'/my/my-properties?property_id={flat.id}&success=visiting_help_created')
            except Exception as e:
                _logger.error("Error creating visiting help: %s", str(e))
                return request.redirect(f'/my/my-properties?property_id={flat.id}&error=creation_failed')

        flat_id = post.get('flat_id') or request.params.get('flat_id')
        flat = request.env['flat.management'].sudo().browse(int(flat_id))

        categories = request.env['community.visiting.help.category'].sudo().search([('active', '=', True)])
        if not categories:
            for cat_name in ['Maid', 'Cook', 'Driver', 'Nanny', 'Electrician']:
                request.env['community.visiting.help.category'].sudo().create({'name': cat_name, 'active': True})
            categories = request.env['community.visiting.help.category'].sudo().search([('active', '=', True)])

        week_days = request.env['community.week.day'].sudo().search([])
        if not week_days:
            for day_name in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                request.env['community.week.day'].sudo().create({'name': day_name, 'code': day_name.lower()})
            week_days = request.env['community.week.day'].sudo().search([])

        return request.render('community_management.portal_visiting_help_form', {
            'page_name': 'create_visiting_help', 'flat': flat,
            'categories': categories, 'week_days': week_days,
            'valid_for_types': request.env['community.visiting.help.entry']._fields['valid_for'].selection,
            'validity_types': request.env['community.visiting.help.entry']._fields['validity'].selection,
        })

    # =====================================================
    # AMENITY BOOKING PORTAL
    # =====================================================
    @http.route(['/my/amenity/book'], type='http', auth="user", website=True)
    def create_amenity_booking(self, **post):
        partner = request.env.user.partner_id
        if request.httprequest.method == 'POST':
            flat_id = post.get('flat_id')
            if not flat_id: return request.redirect('/my/my-properties?error=missing_flat_id')
            flat = request.env['flat.management'].sudo().search([
                '|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id), ('id', '=', int(flat_id))
            ], limit=1)
            if not flat: return request.redirect('/my/my-properties?error=access_denied')

            try:
                amenity_id = int(post.get('amenity_id'))
                amenity = request.env['community.amenity'].sudo().browse(amenity_id)

                # Safely handle the file upload
                attachment = False
                if post.get('attachment') and hasattr(post.get('attachment'), 'read'):
                    attachment = base64.b64encode(post.get('attachment').read())

                # BULLETPROOF STATE CHECK: Dynamically grab valid states from your model
                valid_states = dict(request.env['community.amenity.booking']._fields['state'].selection).keys()

                if amenity.amenity_type == 'free':
                    # Auto-detect whether your model uses 'approved' or 'confirmed'
                    final_state = 'approved' if 'approved' in valid_states else (
                        'confirmed' if 'confirmed' in valid_states else list(valid_states)[0])
                else:
                    final_state = 'pending' if 'pending' in valid_states else (
                        'draft' if 'draft' in valid_states else list(valid_states)[0])

                vals = {
                    'partner_id': partner.id,
                    'flat_id': flat.id,
                    'amenity_id': amenity_id,
                    'booking_date': post.get('booking_date'),
                    'remarks': post.get('remarks'),
                    'attachment': attachment,
                    'state': final_state
                }

                booking = request.env['community.amenity.booking'].sudo().create(vals)

                if amenity.amenity_type == 'paid':
                    if hasattr(booking, 'create_invoice'):
                        booking.create_invoice()

                return request.redirect(f'/my/my-properties?property_id={flat.id}&success=amenity_booked')
            except Exception as e:
                _logger.error("Error booking amenity: %s", str(e))
                return request.redirect(f'/my/my-properties?property_id={flat.id}&error=booking_failed')

        flat_id = post.get('flat_id') or request.params.get('flat_id')
        flat = request.env['flat.management'].sudo().browse(int(flat_id))
        amenities = request.env['community.amenity'].sudo().search([
            ('active', '=', True),
            '|', ('community_id', '=', False), ('community_id', '=', flat.community_id.id)
        ])
        return request.render('community_management.portal_amenity_booking_form', {
            'page_name': 'book_amenity', 'flat': flat, 'amenities': amenities
        })



#
# from odoo import http, fields
# from odoo.http import request
# import base64, logging, random, string, urllib.parse
# from datetime import datetime
#
# _logger = logging.getLogger(__name__)
#
# class MultiPropertyPortal(http.Controller):
#     @http.route(['/my/my-properties'], type='http', auth="user", website=True)
#     def portal_my_properties(self, property_id=None, **kwargs):
#         partner = request.env.user.partner_id
#         flats = request.env['flat.management'].sudo().search(['|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id)])
#         selected_flat, family_members, pets, vehicles, notices, visitors, child_permissions, service_providers = None, [], [], [], [], [], [], []
#         guest_invites, party_invites, cab_preapprovals, delivery_passes, visiting_helps, amenities, amenity_bookings = [], [], [], [], [], [], []
#
#         if property_id:
#             try:
#                 selected_flat = request.env['flat.management'].sudo().browse(int(property_id))
#                 if selected_flat and selected_flat in flats:
#                     sid = selected_flat.id
#                     cid = selected_flat.community_id.id
#                     now = fields.Datetime.now()
#                     family_members = request.env['family.member'].sudo().search([('flat_id', '=', sid)])
#                     pets = request.env['pet.management'].sudo().search([('flat_id', '=', sid)])
#                     vehicles = request.env['vehicle.management'].sudo().search([('flat_id', '=', sid)])
#                     domain = [('active', '=', True), '|', ('community_id', '=', False), ('community_id', '=', cid), '|', ('date_start', '=', False), ('date_start', '<=', now), '|', ('date_end', '=', False), ('date_end', '>=', now)]
#                     raw_notices = request.env['property.notice.board'].sudo().search(domain, order='date_start desc')
#                     for n in raw_notices:
#                         if not n.target_flat_ids or selected_flat in n.target_flat_ids: notices.append(n)
#                     visitors = request.env['mygate.visitor'].sudo().search([('flat_id', '=', sid)], order='create_date desc')
#                     for v in visitors:
#                         if v.state == 'approved' and not v.access_code: v.sudo().write({'access_code': ''.join(random.choices(string.digits, k=6))})
#                     child_permissions = request.env['child.exit.permission'].sudo().search([('flat_id', '=', sid)], order='create_date desc')
#                     service_providers = request.env['res.partner'].sudo().search([('community_id', '=', cid), ('category_custom_id', '!=', False), ('daily_slot_ids', '!=', False)])
#                     guest_invites = request.env['guest.invite'].sudo().search([('flat_id', '=', sid)], order='create_date desc')
#                     party_invites = request.env['party.group.invite'].sudo().search([('flat_id', '=', sid)], order='create_date desc')
#                     cab_preapprovals = request.env['cab.preapproval'].sudo().search([('flat_id', '=', sid)], order='create_date desc')
#                     delivery_passes = request.env['community.delivery.pass'].sudo().search([('flat_id', '=', sid)], order='create_date desc')
#                     visiting_helps = request.env['community.visiting.help.entry'].sudo().search([('flat_id', '=', sid)], order='create_date desc')
#                     amenities = request.env['community.amenity'].sudo().search([('active', '=', True), '|', ('community_id', '=', False), ('community_id', '=', cid)])
#                     amenity_bookings = request.env['community.amenity.booking'].sudo().search([('flat_id', '=', sid)], order='booking_date desc')
#                 else: selected_flat = None
#             except: selected_flat = None
#
#         return request.render('community_management.portal_my_properties_template', {
#             'flats': flats, 'selected_flat': selected_flat, 'family_members': family_members, 'pets': pets, 'vehicles': vehicles,
#             'notices': notices, 'visitors': visitors, 'child_permissions': child_permissions, 'service_providers': service_providers,
#             'guest_invites': guest_invites, 'party_invites': party_invites, 'cab_preapprovals': cab_preapprovals,
#             'delivery_passes': delivery_passes, 'visiting_helps': visiting_helps, 'amenities': amenities, 'amenity_bookings': amenity_bookings,
#             'page_name': 'my_properties'
#         })
#
#     @http.route(['/my/delivery-pass/create'], type='http', auth="user", website=True)
#     def create_delivery_pass(self, **post):
#         partner = request.env.user.partner_id
#         if request.httprequest.method == 'POST':
#             flat_id = post.get('flat_id')
#             flat = request.env['flat.management'].sudo().search(['|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id), ('id', '=', int(flat_id))], limit=1)
#             if not flat: return request.redirect('/my/my-properties?error=access_denied')
#             try:
#                 mode = post.get('mode', 'once')
#                 vals = {'resident_id': partner.id, 'flat_id': flat.id, 'mode': mode, 'company_name': post.get('company_name'), 'is_surprise': bool(post.get('is_surprise')), 'allow_leave_at_gate': bool(post.get('allow_leave_at_gate')), 'state': 'active'}
#                 if mode == 'once':
#                     vals['once_date'] = post.get('once_date') or fields.Date.context_today(request.env.user)
#                     vals['once_start_time'] = float(post.get('once_start_time') or 0.0)
#                     vals['once_valid_hours'] = str(post.get('once_valid_hours') or '1')
#                 else: vals['freq_validity'] = post.get('freq_validity', '1m')
#                 request.env['community.delivery.pass'].sudo().create(vals)
#                 return request.redirect(f'/my/my-properties?property_id={flat.id}&success=delivery_pass_created')
#             except: return request.redirect(f'/my/my-properties?property_id={flat.id}&error=creation_failed')
#         flat = request.env['flat.management'].sudo().browse(int(post.get('flat_id') or request.params.get('flat_id')))
#         return request.render('community_management.portal_delivery_pass_form', {'page_name': 'create_delivery_pass', 'flat': flat, 'validity_types': request.env['community.delivery.pass']._fields['freq_validity'].selection})
#
#     @http.route(['/my/visiting-help/create'], type='http', auth="user", website=True)
#     def create_visiting_help(self, **post):
#         partner = request.env.user.partner_id
#         if request.httprequest.method == 'POST':
#             flat_id = post.get('flat_id')
#             flat = request.env['flat.management'].sudo().search(['|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id), ('id', '=', int(flat_id))], limit=1)
#             if not flat: return request.redirect('/my/my-properties?error=access_denied')
#             try:
#                 entry_type = post.get('entry_type', 'once')
#                 vals = {'tenant_id': partner.id, 'flat_id': flat.id, 'category_id': int(post.get('category_id')), 'company_name': post.get('company_name'), 'entry_type': entry_type}
#                 if entry_type == 'once':
#                     vals['visit_date'] = post.get('visit_date') or fields.Date.context_today(request.env.user)
#                     vals['start_time'] = float(post.get('start_time') or 0.0)
#                     vals['valid_for'] = post.get('valid_for', '1')
#                 else:
#                     day_ids = request.httprequest.form.getlist('day_ids')
#                     if day_ids: vals['day_ids'] = [(6, 0, [int(d) for d in day_ids if d])]
#                     vals['validity'], vals['time_from'], vals['time_to'], vals['entries_per_day'] = post.get('validity', '1m'), float(post.get('time_from') or 0.0), float(post.get('time_to') or 23.99), str(post.get('entries_per_day') or '1')
#                 request.env['community.visiting.help.entry'].sudo().create(vals)
#                 return request.redirect(f'/my/my-properties?property_id={flat.id}&success=visiting_help_created')
#             except: return request.redirect(f'/my/my-properties?property_id={flat.id}&error=creation_failed')
#         flat = request.env['flat.management'].sudo().browse(int(post.get('flat_id') or request.params.get('flat_id')))
#         categories = request.env['community.visiting.help.category'].sudo().search([('active', '=', True)])
#         if not categories:
#             for cat in ['Maid', 'Cook', 'Driver', 'Nanny']: request.env['community.visiting.help.category'].sudo().create({'name': cat, 'active': True})
#             categories = request.env['community.visiting.help.category'].sudo().search([('active', '=', True)])
#         week_days = request.env['community.week.day'].sudo().search([])
#         if not week_days:
#             for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']: request.env['community.week.day'].sudo().create({'name': day, 'code': day.lower()})
#             week_days = request.env['community.week.day'].sudo().search([])
#         return request.render('community_management.portal_visiting_help_form', {'page_name': 'create_visiting_help', 'flat': flat, 'categories': categories, 'week_days': week_days, 'valid_for_types': request.env['community.visiting.help.entry']._fields['valid_for'].selection, 'validity_types': request.env['community.visiting.help.entry']._fields['validity'].selection})
#
#     @http.route(['/my/cab-preapproval/create'], type='http', auth="user", website=True)
#     def create_cab_preapproval(self, **post):
#         partner = request.env.user.partner_id
#         if request.httprequest.method == 'POST':
#             flat_id = post.get('flat_id')
#             flat = request.env['flat.management'].sudo().search(['|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id), ('id', '=', int(flat_id))], limit=1)
#             if not flat: return request.redirect('/my/my-properties?error=access_denied')
#             try:
#                 mode = post.get('mode', 'once')
#                 vals = {'resident_id': partner.id, 'flat_id': flat_id, 'mode': mode, 'company_name': post.get('company_name', 'uber'), 'vehicle_last4': post.get('vehicle_last4', '')}
#                 if mode == 'once': vals.update({'once_date': post.get('once_date'), 'once_valid_hours': str(post.get('once_valid_hours') or '1')})
#                 else: vals.update({'freq_days': post.get('freq_days', 'all'), 'freq_time_from': float(post.get('freq_time_from') or 0.0), 'freq_time_to': float(post.get('freq_time_to') or 23.99), 'entries_per_day': str(post.get('entries_per_day') or '1'), 'freq_validity': post.get('freq_validity', '1m')})
#                 new_cab = request.env['cab.preapproval'].sudo().create(vals)
#                 new_cab.action_activate()
#                 return request.redirect('/my/my-properties?property_id=%s&success=cab_preapproval_created' % flat_id)
#             except: return request.redirect('/my/my-properties?property_id=%s&error=creation_failed' % flat_id)
#         flat = request.env['flat.management'].sudo().browse(int(post.get('flat_id') or request.params.get('flat_id')))
#         return request.render('community_management.portal_cab_preapproval_form', {'page_name': 'create_cab_preapproval', 'flat': flat, 'freq_days_types': request.env['cab.preapproval']._fields['freq_days'].selection, 'freq_validity_types': request.env['cab.preapproval']._fields['freq_validity'].selection, 'company_types': request.env['cab.preapproval']._fields['company_name'].selection, 'valid_hours_types': request.env['cab.preapproval']._fields['once_valid_hours'].selection, 'entries_types': request.env['cab.preapproval']._fields['entries_per_day'].selection})
#
#     @http.route(['/my/cab-preapproval/<int:cab_id>'], type='http', auth="user", website=True)
#     def portal_cab_preapproval_detail(self, cab_id, **kwargs):
#         partner, cab = request.env.user.partner_id, request.env['cab.preapproval'].sudo().browse(cab_id)
#         if not cab.exists() or (cab.flat_id.tenant_id != partner and cab.flat_id.lease_owner_id != partner): return request.redirect('/my/my-properties?error=access_denied')
#         return request.render('community_management.portal_cab_preapproval_detail', {'cab': cab, 'flat': cab.flat_id, 'page_name': 'cab_preapproval_detail'})
#
#     @http.route(['/my/cab-preapproval/cancel/<int:cab_id>'], type='http', auth="user", website=True)
#     def cancel_cab_preapproval(self, cab_id, **kwargs):
#         partner, cab = request.env.user.partner_id, request.env['cab.preapproval'].sudo().browse(cab_id)
#         if cab.exists() and (cab.flat_id.tenant_id == partner or cab.flat_id.lease_owner_id == partner): cab.action_cancel()
#         return request.redirect('/my/my-properties?property_id=%s&success=cab_cancelled' % cab.flat_id.id)
#
#     @http.route(['/my/party-invite/create'], type='http', auth="user", website=True)
#     def create_party_invite(self, **post):
#         partner = request.env.user.partner_id
#         if request.httprequest.method == 'POST':
#             flat_id = post.get('flat_id')
#             flat = request.env['flat.management'].sudo().search(['|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id), ('id', '=', int(flat_id))], limit=1)
#             if not flat: return request.redirect('/my/my-properties?error=access_denied')
#             try:
#                 request.env['party.group.invite'].sudo().create({'name': post.get('name', 'Party Invite'), 'host_id': partner.id, 'flat_id': flat.id, 'event_date': post.get('event_date'), 'start_time': float(post.get('start_time')), 'valid_hours': float(post.get('valid_hours', 8.0)), 'max_guests': int(post.get('max_guests', 5)), 'location': post.get('location') or flat.name, 'note': post.get('note'), 'state': 'active'})
#                 return request.redirect('/my/my-properties?property_id=%s&success=party_invite_created' % flat.id)
#             except: return request.redirect('/my/my-properties?property_id=%s&error=creation_failed' % flat.id)
#         flat = request.env['flat.management'].sudo().browse(int(post.get('flat_id') or request.params.get('flat_id')))
#         return request.render('community_management.portal_party_invite_form', {'page_name': 'create_party_invite', 'flat': flat})
#
#     @http.route(['/my/party-invite/<int:invite_id>'], type='http', auth="user", website=True)
#     def portal_party_invite_detail(self, invite_id, **kwargs):
#         partner, invite = request.env.user.partner_id, request.env['party.group.invite'].sudo().browse(invite_id)
#         if not invite.exists() or (invite.flat_id.tenant_id != partner and invite.flat_id.lease_owner_id != partner): return request.redirect('/my/my-properties?error=access_denied')
#         return request.render('community_management.portal_party_invite_detail', {'invite': invite, 'flat': invite.flat_id, 'page_name': 'party_invite_detail'})
#
#     @http.route(['/my/party-invite/share/<int:invite_id>'], type='http', auth="user", website=True)
#     def share_party_invite_whatsapp(self, invite_id, **kwargs):
#         partner, invite = request.env.user.partner_id, request.env['party.group.invite'].sudo().browse(invite_id)
#         if not invite.exists() or (invite.flat_id.tenant_id != partner and invite.flat_id.lease_owner_id != partner): return request.redirect('/my/my-properties?error=access_denied')
#         edate = invite.event_date.strftime('%d/%m/%Y') if invite.event_date else 'TBD'
#         etime = '%02d:%02d' % (int(invite.start_time), int(round((invite.start_time % 1) * 60))) if invite.start_time else 'TBD'
#         msg = f"🎉 *YOU ARE INVITED!*\n\n📝 Event: {invite.name}\n👤 Host: {invite.host_id.name}\n📅 Date: {edate}\n⏰ Time: {etime}\n📍 Location: {invite.location or invite.flat_id.name}\n👥 Max Guests: {invite.max_guests}\n\n🔑 *Entry Token:* {invite.token}\n\n✅ Show Entry Token at gate!"
#         return request.redirect(f"https://api.whatsapp.com/send?text={urllib.parse.quote(msg)}", local=False)
#
#     @http.route(['/my/guest-invite/create'], type='http', auth="user", website=True)
#     def create_guest_invite(self, **post):
#         partner = request.env.user.partner_id
#         if request.httprequest.method == 'POST':
#             flat_id = post.get('flat_id')
#             flat = request.env['flat.management'].sudo().search(['|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id), ('id', '=', int(flat_id))], limit=1)
#             if not flat: return request.redirect('/my/my-properties?error=access_denied')
#             try:
#                 itype = post.get('invite_type', 'once')
#                 vals = {'resident_id': partner.id, 'flat_id': flat.id, 'invite_type': itype, 'note': post.get('note'), 'is_private': bool(post.get('is_private'))}
#                 if itype == 'once': vals.update({'once_date': post.get('once_date'), 'once_start_time': float(post.get('once_start_time') or 0.0), 'once_valid_hours': int(post.get('once_valid_hours') or 8)})
#                 else: vals.update({'duration_type': post.get('duration_type'), 'freq_start_date': post.get('freq_start_date') or fields.Date.context_today(request.env.user)})
#                 inv = request.env['guest.invite'].sudo().create(vals)
#                 request.env['guest.invite.line'].sudo().create({'invite_id': inv.id, 'guest_name': post.get('guest_name'), 'guest_mobile': post.get('guest_mobile')})
#                 inv.action_compute_window()
#                 return request.redirect('/my/my-properties?property_id=%s&success=guest_invite_created' % flat.id)
#             except: return request.redirect('/my/my-properties?property_id=%s&error=creation_failed' % flat.id)
#         flat = request.env['flat.management'].sudo().browse(int(post.get('flat_id') or request.params.get('flat_id')))
#         return request.render('community_management.portal_guest_invite_form', {'page_name': 'create_guest_invite', 'flat': flat, 'duration_types': request.env['guest.invite']._fields['duration_type'].selection})
#
#     @http.route(['/my/guest-invite/share/<int:invite_id>'], type='http', auth="user", website=True)
#     def share_guest_invite_whatsapp(self, invite_id, **kwargs):
#         partner, invite = request.env.user.partner_id, request.env['guest.invite'].sudo().browse(invite_id)
#         if not invite.exists() or (invite.flat_id.tenant_id != partner and invite.flat_id.lease_owner_id != partner): return request.redirect('/my/my-properties?error=access_denied')
#         base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
#         guests = ", ".join([f"{l.guest_name} ({l.guest_mobile})" for l in invite.guest_line_ids])
#         start_str = invite.start_datetime.strftime('%d/%m %H:%M') if invite.start_datetime else 'N/A'
#         end_str = invite.end_datetime.strftime('%d/%m %H:%M') if invite.end_datetime else 'N/A'
#         msg = f"🔔 GATE ENTRY INVITE\n\n🔑 OTP: {invite.otpcode}\n👤 Resident: {invite.resident_id.name}\n📅 Valid: {start_str} - {end_str}\n👥 Guests: {guests}\n\n🔗 Details: {base_url}/my/guest/invites/invite/{invite.id}\n\n✅ Show OTP at gate!"
#         phone = ''.join(filter(str.isdigit, invite.guest_line_ids[0].guest_mobile)) if invite.guest_line_ids and invite.guest_line_ids[0].guest_mobile else ""
#         return request.redirect(f"https://api.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(msg)}" if phone else f"https://api.whatsapp.com/send?text={urllib.parse.quote(msg)}", local=False)
#
#     @http.route(['/my/service/book/<int:slot_id>'], type='http', auth="user", website=True)
#     def portal_book_service(self, slot_id, flat_id=None, **kwargs):
#         partner, slot = request.env.user.partner_id, request.env['res.partner.daily.slot'].sudo().browse(slot_id)
#         if not slot.exists(): return request.redirect('/my/my-properties?error=slot_not_found')
#         if slot.is_available:
#             slot.action_book_slot(partner.id)
#             return request.redirect(f'/my/my-properties?property_id={flat_id}&success=slot_booked' if flat_id else '/my/my-properties?success=slot_booked')
#         return request.redirect(f'/my/my-properties?property_id={flat_id}&error=slot_already_booked' if flat_id else '/my/my-properties?error=slot_already_booked')
#
#     @http.route(['/my/amenity/book'], type='http', auth="user", website=True)
#     def create_amenity_booking(self, **post):
#         partner = request.env.user.partner_id
#         if request.httprequest.method == 'POST':
#             flat_id = post.get('flat_id')
#             flat = request.env['flat.management'].sudo().search(['|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id), ('id', '=', int(flat_id))], limit=1)
#             if not flat: return request.redirect('/my/my-properties?error=access_denied')
#             try:
#                 amenity = request.env['community.amenity'].sudo().browse(int(post.get('amenity_id')))
#                 valid_states = dict(request.env['community.amenity.booking']._fields['state'].selection).keys()
#                 final_state = ('approved' if 'approved' in valid_states else 'confirmed') if amenity.amenity_type == 'free' else ('pending' if 'pending' in valid_states else 'draft')
#                 attach = base64.b64encode(post.get('attachment').read()) if post.get('attachment') and hasattr(post.get('attachment'), 'read') else False
#                 b = request.env['community.amenity.booking'].sudo().create({'partner_id': partner.id, 'flat_id': flat.id, 'amenity_id': amenity.id, 'booking_date': post.get('booking_date'), 'remarks': post.get('remarks'), 'attachment': attach, 'state': final_state})
#                 if amenity.amenity_type == 'paid' and hasattr(b, 'create_invoice'): b.create_invoice()
#                 return request.redirect(f'/my/my-properties?property_id={flat.id}&success=amenity_booked')
#             except: return request.redirect(f'/my/my-properties?property_id={flat.id}&error=booking_failed')
#         flat = request.env['flat.management'].sudo().browse(int(post.get('flat_id') or request.params.get('flat_id')))
#         amenities = request.env['community.amenity'].sudo().search([('active', '=', True), '|', ('community_id', '=', False), ('community_id', '=', flat.community_id.id)])
#         return request.render('community_management.portal_amenity_booking_form', {'page_name': 'book_amenity', 'flat': flat, 'amenities': amenities})
#
#     @http.route(['/my/child-exit/create'], type='http', auth="user", website=True)
#     def create_child_exit(self, **post):
#         partner = request.env.user.partner_id
#         if request.httprequest.method == 'POST':
#             flat_id = post.get('flat_id')
#             flat = request.env['flat.management'].sudo().search(['|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id), ('id', '=', int(flat_id))], limit=1)
#             if not flat: return request.redirect('/my/my-properties?error=access_denied')
#             time_str = post.get('allowed_exit_time')
#             try:
#                 request.env['child.exit.permission'].sudo().create({'tenant_id': partner.id, 'flat_id': flat.id, 'child_id': int(post.get('child_id')), 'purpose': post.get('purpose'), 'allowed_exit_time': (time_str.replace('T', ' ') + ':00' if time_str and len(time_str) == 16 else fields.Datetime.now()), 'duration_hours': post.get('duration_hours'), 'state': 'active'})
#                 return request.redirect('/my/my-properties?property_id=%s&success=child_exit_created' % flat.id)
#             except: return request.redirect('/my/my-properties?property_id=%s&error=creation_failed' % flat.id)
#         flat = request.env['flat.management'].sudo().browse(int(post.get('flat_id') or request.params.get('flat_id')))
#         return request.render('community_management.portal_child_exit_form', {'page_name': 'create_child_exit', 'flat': flat, 'children': request.env['family.member'].sudo().search([('flat_id', '=', flat.id), ('member_type', '=', 'child')]), 'durations': request.env['child.exit.permission']._fields['duration_hours'].selection})
#
#     @http.route(['/my/visitor/<int:visitor_id>'], type='http', auth="user", website=True)
#     def portal_visitor_detail(self, visitor_id, **kwargs):
#         partner, visitor = request.env.user.partner_id, request.env['mygate.visitor'].sudo().browse(visitor_id)
#         if not visitor.exists() or (visitor.flat_id.tenant_id != partner and visitor.flat_id.lease_owner_id != partner): return request.redirect('/my/my-properties?error=access_denied')
#         if visitor.state == 'approved' and not visitor.access_code: visitor.sudo().write({'access_code': ''.join(random.choices(string.digits, k=6))})
#         return request.render('community_management.portal_visitor_detail', {'visitor': visitor, 'flat': visitor.flat_id, 'page_name': 'visitor_detail'})
#
#     @http.route(['/my/visitor/approve/<int:visitor_id>'], type='http', auth="user", website=True)
#     def portal_visitor_approve(self, visitor_id, **kwargs):
#         partner, visitor = request.env.user.partner_id, request.env['mygate.visitor'].sudo().browse(visitor_id)
#         if visitor.exists() and (visitor.flat_id.tenant_id == partner or visitor.flat_id.lease_owner_id == partner) and visitor.state == 'pending':
#             visitor.action_approve() if hasattr(visitor, 'action_approve') else visitor.sudo().write({'state': 'approved', 'access_code': ''.join(random.choices(string.digits, k=6))})
#         return request.redirect('/my/visitor/%s?success=approved' % visitor.id)
#
#     @http.route(['/my/visitor/reject/<int:visitor_id>'], type='http', auth="user", website=True)
#     def portal_visitor_reject(self, visitor_id, **kwargs):
#         partner, visitor = request.env.user.partner_id, request.env['mygate.visitor'].sudo().browse(visitor_id)
#         if visitor.exists() and (visitor.flat_id.tenant_id == partner or visitor.flat_id.lease_owner_id == partner) and visitor.state == 'pending':
#             visitor.action_reject() if hasattr(visitor, 'action_reject') else visitor.sudo().write({'state': 'rejected'})
#         return request.redirect('/my/visitor/%s?success=rejected' % visitor.id)
#
#     @http.route(['/my/notice/<int:notice_id>'], type='http', auth="user", website=True)
#     def portal_notice_detail(self, notice_id, flat_id=None, **kwargs):
#         notice = request.env['property.notice.board'].sudo().browse(notice_id)
#         if not notice.exists(): return request.redirect('/my/my-properties?error=notice_not_found')
#         return request.render('community_management.portal_notice_detail', {'notice': notice, 'flat': request.env['flat.management'].sudo().browse(int(flat_id)) if flat_id else None, 'page_name': 'notice_detail'})
#
#     @http.route(['/my/family-member/create'], type='http', auth="user", website=True)
#     def create_family_member(self, **post):
#         partner = request.env.user.partner_id
#         if request.httprequest.method == 'POST':
#             flat_id = post.get('flat_id')
#             flat = request.env['flat.management'].sudo().search(['|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id), ('id', '=', int(flat_id))], limit=1)
#             if not flat: return request.redirect('/my/my-properties?error=access_denied')
#             photo = base64.b64encode(post.get('photo').read()) if post.get('photo') and hasattr(post.get('photo'), 'read') else False
#             request.env['family.member'].sudo().create({k: v for k, v in {'tenant_id': partner.id, 'flat_id': flat.id, 'name': post.get('name'), 'member_type': post.get('member_type'), 'gender': post.get('gender'), 'date_of_birth': post.get('date_of_birth'), 'relationship': post.get('relationship'), 'email': post.get('email'), 'phone': post.get('phone'), 'aadhaar_number': post.get('aadhaar_number'), 'notes': post.get('notes'), 'photo': photo}.items() if v})
#             return request.redirect('/my/my-properties?property_id=%s&success=created' % flat.id)
#         flat = request.env['flat.management'].sudo().browse(int(post.get('flat_id')))
#         return request.render('community_management.portal_family_member_form', {'page_name': 'create_family_member', 'flat': flat, 'member': False, 'relationships': request.env['family.member']._fields['relationship'].selection, 'genders': request.env['family.member']._fields['gender'].selection, 'member_types': request.env['family.member']._fields['member_type'].selection})
#
#     @http.route(['/my/family-member/edit/<int:member_id>'], type='http', auth="user", website=True)
#     def edit_family_member(self, member_id, **post):
#         partner, member = request.env.user.partner_id, request.env['family.member'].sudo().browse(member_id)
#         if not member.exists() or member.tenant_id.id != partner.id: return request.redirect('/my/my-properties?error=access_denied')
#         if request.httprequest.method == 'POST':
#             photo = base64.b64encode(post.get('photo').read()) if post.get('photo') and hasattr(post.get('photo'), 'read') else member.photo
#             member.write({k: v for k, v in {'name': post.get('name'), 'member_type': post.get('member_type'), 'gender': post.get('gender'), 'date_of_birth': post.get('date_of_birth'), 'relationship': post.get('relationship'), 'email': post.get('email'), 'phone': post.get('phone'), 'aadhaar_number': post.get('aadhaar_number'), 'notes': post.get('notes'), 'photo': photo}.items() if v is not None})
#             return request.redirect('/my/my-properties?property_id=%s&success=updated' % member.flat_id.id)
#         return request.render('community_management.portal_family_member_form', {'page_name': 'edit_family_member', 'member': member, 'flat': member.flat_id, 'relationships': request.env['family.member']._fields['relationship'].selection, 'genders': request.env['family.member']._fields['gender'].selection, 'member_types': request.env['family.member']._fields['member_type'].selection})
#
#     @http.route(['/my/family-member/delete/<int:member_id>'], type='http', auth="user", website=True)
#     def delete_family_member(self, member_id, **post):
#         partner, member = request.env.user.partner_id, request.env['family.member'].sudo().browse(member_id)
#         if not member.exists() or member.tenant_id.id != partner.id: return request.redirect('/my/my-properties?error=access_denied')
#         flat_id = member.flat_id.id
#         member.unlink()
#         return request.redirect('/my/my-properties?property_id=%s&success=deleted' % flat_id)
#
#     @http.route(['/my/family-member/view-qr/<int:member_id>'], type='http', auth="user", website=True)
#     def view_family_member_qr(self, member_id, **kwargs):
#         partner, member = request.env.user.partner_id, request.env['family.member'].sudo().browse(member_id)
#         if not member.exists() or member.tenant_id.id != partner.id: return request.redirect('/my/my-properties?error=access_denied')
#         return request.render('community_management.portal_qr_code_download', {'member': member, 'page_name': 'qr_code_download'})
#
#     @http.route(['/my/family-member/download-qr/<int:member_id>'], type='http', auth="user", website=True)
#     def download_family_member_qr(self, member_id, **kwargs):
#         partner, member = request.env.user.partner_id, request.env['family.member'].sudo().browse(member_id)
#         if not member.exists() or member.tenant_id.id != partner.id: return request.redirect('/my/my-properties?error=access_denied')
#         if member.qr_code_image:
#             image_data = base64.b64decode(member.qr_code_image) if isinstance(member.qr_code_image, bytes) else base64.b64decode(member.qr_code_image.encode('utf-8'))
#             return request.make_response(image_data, [('Content-Type', 'image/png'), ('Content-Disposition', 'attachment; filename="QR_%s.png"' % (member.resident_id or 'member')), ('Content-Length', str(len(image_data)))])
#         return request.redirect('/my/my-properties?property_id=%s&error=qr_not_found' % member.flat_id.id)
#
#     @http.route(['/my/family-member/generate-all-qr'], type='http', auth="user", website=True)
#     def generate_all_qr_codes(self, **kwargs):
#         for member in request.env['family.member'].sudo().search([('tenant_id', '=', request.env.user.partner_id.id)]):
#             if not member.qr_code_image and member.resident_id: member.generate_qr_code_image()
#         return request.redirect('/my/my-properties?success=qr_generated')
#
#     @http.route(['/my/pet/create'], type='http', auth="user", website=True)
#     def create_pet(self, **post):
#         partner = request.env.user.partner_id
#         if request.httprequest.method == 'POST':
#             flat_id = int(post.get('flat_id'))
#             flat = request.env['flat.management'].sudo().search(['|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id), ('id', '=', flat_id)], limit=1)
#             if not flat: return request.redirect('/my/my-properties?error=access_denied')
#             photo = base64.b64encode(post.get('photo').read()) if post.get('photo') and hasattr(post.get('photo'), 'read') else False
#             request.env['pet.management'].sudo().create({k: v for k, v in {'tenant_id': partner.id, 'flat_id': flat.id, 'name': post.get('name'), 'pet_type': post.get('pet_type'), 'breed': post.get('breed'), 'color': post.get('color'), 'gender': post.get('gender'), 'date_of_birth': post.get('date_of_birth'), 'weight': post.get('weight'), 'microchip_number': post.get('microchip_number'), 'license_number': post.get('license_number'), 'last_vaccination_date': post.get('last_vaccination_date'), 'next_vaccination_date': post.get('next_vaccination_date'), 'veterinarian': post.get('veterinarian'), 'vet_phone': post.get('vet_phone'), 'medical_conditions': post.get('medical_conditions'), 'allergies': post.get('allergies'), 'special_needs': post.get('special_needs'), 'notes': post.get('notes'), 'photo': photo}.items() if v})
#             return request.redirect('/my/my-properties?property_id=%s&success=pet_created' % flat.id)
#         flat = request.env['flat.management'].sudo().browse(int(post.get('flat_id')))
#         return request.render('community_management.portal_pet_form', {'page_name': 'create_pet', 'flat': flat, 'pet': False, 'pet_types': request.env['pet.management']._fields['pet_type'].selection, 'genders': request.env['pet.management']._fields['gender'].selection})
#
#     @http.route(['/my/pet/edit/<int:pet_id>'], type='http', auth="user", website=True)
#     def edit_pet(self, pet_id, **post):
#         partner, pet = request.env.user.partner_id, request.env['pet.management'].sudo().browse(pet_id)
#         if not pet.exists() or pet.tenant_id.id != partner.id: return request.redirect('/my/my-properties?error=access_denied')
#         if request.httprequest.method == 'POST':
#             photo = base64.b64encode(post.get('photo').read()) if post.get('photo') and hasattr(post.get('photo'), 'read') else pet.photo
#             pet.write({k: v for k, v in {'name': post.get('name'), 'pet_type': post.get('pet_type'), 'breed': post.get('breed'), 'color': post.get('color'), 'gender': post.get('gender'), 'date_of_birth': post.get('date_of_birth'), 'weight': post.get('weight'), 'microchip_number': post.get('microchip_number'), 'license_number': post.get('license_number'), 'last_vaccination_date': post.get('last_vaccination_date'), 'next_vaccination_date': post.get('next_vaccination_date'), 'veterinarian': post.get('veterinarian'), 'vet_phone': post.get('vet_phone'), 'medical_conditions': post.get('medical_conditions'), 'allergies': post.get('allergies'), 'special_needs': post.get('special_needs'), 'notes': post.get('notes'), 'photo': photo}.items() if v is not None})
#             return request.redirect('/my/my-properties?property_id=%s&success=pet_updated' % pet.flat_id.id)
#         return request.render('community_management.portal_pet_form', {'page_name': 'edit_pet', 'pet': pet, 'flat': pet.flat_id, 'pet_types': request.env['pet.management']._fields['pet_type'].selection, 'genders': request.env['pet.management']._fields['gender'].selection})
#
#     @http.route(['/my/pet/delete/<int:pet_id>'], type='http', auth="user", website=True)
#     def delete_pet(self, pet_id, **post):
#         partner, pet = request.env.user.partner_id, request.env['pet.management'].sudo().browse(pet_id)
#         if not pet.exists() or pet.tenant_id.id != partner.id: return request.redirect('/my/my-properties?error=access_denied')
#         flat_id = pet.flat_id.id
#         pet.unlink()
#         return request.redirect('/my/my-properties?property_id=%s&success=pet_deleted' % flat_id)
#
#     @http.route(['/my/vehicle/create'], type='http', auth="user", website=True)
#     def create_vehicle(self, **post):
#         partner = request.env.user.partner_id
#         if request.httprequest.method == 'POST':
#             flat_id = int(post.get('flat_id'))
#             flat = request.env['flat.management'].sudo().search(['|', ('tenant_id', '=', partner.id), ('lease_owner_id', '=', partner.id), ('id', '=', flat_id)], limit=1)
#             if not flat: return request.redirect('/my/my-properties?error=access_denied')
#             photo = base64.b64encode(post.get('vehicle_photo').read()) if post.get('vehicle_photo') and hasattr(post.get('vehicle_photo'), 'read') else False
#             request.env['vehicle.management'].sudo().create({k: v for k, v in {'tenant_id': partner.id, 'flat_id': flat.id, 'vehicle_number': post.get('vehicle_number'), 'vehicle_type': post.get('vehicle_type'), 'make': post.get('make'), 'model': post.get('model'), 'year': post.get('year') or 0, 'color': post.get('color'), 'notes': post.get('notes'), 'vehicle_photo': photo}.items() if v})
#             return request.redirect('/my/my-properties?property_id=%s&success=vehicle_created' % flat.id)
#         flat = request.env['flat.management'].sudo().browse(int(post.get('flat_id')))
#         return request.render('community_management.portal_vehicle_form', {'page_name': 'create_vehicle', 'flat': flat, 'vehicle': False, 'vehicle_types': request.env['vehicle.management']._fields['vehicle_type'].selection})
#
#     @http.route(['/my/vehicle/edit/<int:vehicle_id>'], type='http', auth="user", website=True)
#     def edit_vehicle(self, vehicle_id, **post):
#         partner, vehicle = request.env.user.partner_id, request.env['vehicle.management'].sudo().browse(vehicle_id)
#         if not vehicle.exists() or vehicle.tenant_id.id != partner.id: return request.redirect('/my/my-properties?error=access_denied')
#         if request.httprequest.method == 'POST':
#             photo = base64.b64encode(post.get('vehicle_photo').read()) if post.get('vehicle_photo') and hasattr(post.get('vehicle_photo'), 'read') else vehicle.vehicle_photo
#             vehicle.write({k: v for k, v in {'vehicle_number': post.get('vehicle_number'), 'vehicle_type': post.get('vehicle_type'), 'make': post.get('make'), 'model': post.get('model'), 'year': post.get('year') or 0, 'color': post.get('color'), 'notes': post.get('notes'), 'vehicle_photo': photo}.items() if v is not None})
#             return request.redirect('/my/my-properties?property_id=%s&success=vehicle_updated' % vehicle.flat_id.id)
#         return request.render('community_management.portal_vehicle_form', {'page_name': 'edit_vehicle', 'vehicle': vehicle, 'flat': vehicle.flat_id, 'vehicle_types': request.env['vehicle.management']._fields['vehicle_type'].selection})
#
#     @http.route(['/my/vehicle/delete/<int:vehicle_id>'], type='http', auth="user", website=True)
#     def delete_vehicle(self, vehicle_id, **post):
#         partner, vehicle = request.env.user.partner_id, request.env['vehicle.management'].sudo().browse(vehicle_id)
#         if not vehicle.exists() or vehicle.tenant_id.id != partner.id: return request.redirect('/my/my-properties?error=access_denied')
#         flat_id = vehicle.flat_id.id
#         vehicle.unlink()
#         return request.redirect('/my/my-properties?property_id=%s&success=vehicle_deleted' % flat_id)
