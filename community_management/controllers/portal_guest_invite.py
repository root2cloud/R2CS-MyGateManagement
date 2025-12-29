from odoo import http
from odoo.http import request
from datetime import datetime
import urllib.parse


class PortalGuestInvite(http.Controller):

    @http.route('/my/guest/invites', type='http', auth='user', website=True, methods=['GET', 'POST'], csrf=False)
    def portal_guest_invites(self, **post):
        partner = request.env.user.partner_id
        Invite = request.env['guest.invite'].sudo()

        if request.httprequest.method == 'POST':
            invite_type = post.get('invitetype', 'once')
            vals = {
                'resident_id': partner.id,
                'invite_type': invite_type,
                'duration_type': post.get('durationtype', '1m'),
                'is_private': bool(post.get('isprivate')),
                'note': post.get('note') or False,
            }

            if invite_type == 'once':
                if post.get('oncedate'):
                    vals['once_date'] = post.get('oncedate')
                timestr = post.get('oncestarttime', '09:00')
                try:
                    t = datetime.strptime(timestr, '%H:%M')
                    vals['once_start_time'] = t.hour + t.minute / 60.0
                except:
                    vals['once_start_time'] = 9.0
                vals['once_valid_hours'] = int(post.get('oncevalidhours') or 8)

            if invite_type == 'frequent':
                if post.get('freqstartdate'):
                    vals['freq_start_date'] = post.get('freqstartdate')
                if post.get('freqenddate'):
                    vals['freq_end_date'] = post.get('freqenddate')

            guestname = post.get('guestname')
            guestmobile = post.get('guestmobile')
            if guestname and guestmobile:
                vals['guest_line_ids'] = [(0, 0, {
                    'guest_name': guestname,
                    'guest_mobile': guestmobile
                })]

            invite = Invite.create(vals)
            invite.action_compute_window()
            return request.redirect(f'/my/guest/invites/invite/{invite.id}')

        invites = Invite.search([('resident_id', '=', partner.id)], order='id desc')
        return request.render('community_management.portal_guest_invite_list', {'invites': invites})

    @http.route('/my/guest/invites/invite/<int:invite_id>', type='http', auth='user', website=True)
    def portal_guest_invite_view(self, invite_id, **kw):
        Invite = request.env['guest.invite'].sudo()
        invite = Invite.browse(invite_id)

        if not invite.exists() or invite.resident_id.id != request.env.user.partner_id.id:
            return request.redirect('/my/guest/invites')

        if not invite.start_datetime or not invite.end_datetime:
            invite.action_compute_window()

        return request.render('community_management.portal_guest_invite_view', {'invite': invite})

    @http.route('/my/guest/invites/<int:invite_id>/whatsapp_share', type='http', auth='user', website=True)
    def portal_whatsapp_share(self, invite_id, **kw):
        """🔥 OPENS https://web.whatsapp.com/ WITH PRE-FILLED MESSAGE"""
        Invite = request.env['guest.invite'].sudo()
        invite = Invite.browse(invite_id)

        if not invite.exists() or invite.resident_id.id != request.env.user.partner_id.id:
            return request.redirect('/my/guest/invites')

        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        portal_url = f"{base_url}/my/guest/invites/invite/{invite.id}"

        guests = ", ".join([f"{line.guest_name} ({line.guest_mobile})" for line in invite.guest_line_ids])

        message = f"""🔔 GATE ENTRY INVITE

🔑 OTP: {invite.otpcode}
👤 Resident: {invite.resident_id.name}
📅 Valid: {invite.start_datetime.strftime('%d/%m %H:%M')} - {invite.end_datetime.strftime('%d/%m %H:%M')}
👥 Guests: {guests or 'Not specified'}

🔗 Details: {portal_url}

✅ Show OTP at gate!"""

        # 🔥 YOUR REQUESTED URL - DIRECT WHATSAPP WEB
        whatsapp_url = f"https://web.whatsapp.com/send?text={urllib.parse.quote(message)}"

        return request.redirect(whatsapp_url)
