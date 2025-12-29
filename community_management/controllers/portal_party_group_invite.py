from odoo import http
from odoo.http import request
from datetime import datetime
import urllib.parse


class PortalPartyGroupInvite(http.Controller):

    @http.route(
        ['/my/party/group/invite', '/my/party/group/invite/<int:invite_id>'],
        type='http', auth='user', website=True, methods=['GET', 'POST'], csrf=False
    )
    def portal_party_group_invite(self, invite_id=None, **post):
        partner = request.env.user.partner_id
        Invite = request.env['party.group.invite'].sudo()

        invite = Invite.browse(invite_id) if invite_id else False

        # STEP 1: basic screen → save note and create draft
        if post.get('step') == 'basic':
            vals = {
                'host_id': partner.id,
                'note': post.get('note') or False,
            }
            if invite:
                invite.write(vals)
            else:
                invite = Invite.create(vals)
            # after Next, show configuration section
            return request.redirect(f"/my/party/group/invite/{invite.id}?show_config=1")

        # STEP 3: configuration form → save date/time/location/guests, activate
        if post.get('step') == 'config' and invite:
            event_date = post.get('event_date') or False

            start_time = 0.0
            if post.get('start_time'):
                hh, mm = post.get('start_time').split(':')
                start_time = int(hh) + int(mm) / 60.0

            valid_hours = float(post.get('valid_hours') or 8.0)
            max_guests = int(post.get('max_guests') or 5)

            invite.write({
                'event_date': event_date,
                'start_time': start_time,
                'valid_hours': valid_hours,
                'location': post.get('location'),
                'max_guests': max_guests,
            })
            invite.action_activate()

            return request.redirect(f"/my/party/group/invite/{invite.id}")

        # LIST + DETAIL
        invites = Invite.search([('host_id', '=', partner.id)], order='id desc')
        if not invite_id or (not invite.exists()):
            invite = False
        # if not invite and invites:
        #     invite = invites[0]

        values = {
            'invite': invite,
            'invites': invites,
        }
        return request.render('community_management.portal_party_group_invite', values)

    @http.route(
        ['/my/party/group/invite/<int:invite_id>/whatsapp_share'],
        type='http', auth='user', website=True
    )
    def portal_party_group_whatsapp_share(self, invite_id, **kw):
        Invite = request.env['party.group.invite'].sudo()
        invite = Invite.browse(invite_id)
        if not invite.exists() or invite.host_id.id != request.env.user.partner_id.id:
            return request.redirect('/my/party/group/invite')

        partner = request.env.user.partner_id

        msg_lines = []
        msg_lines.append("Party invite from %s" % (partner.name or ''))
        if invite.note:
            msg_lines.append("Note: %s" % invite.note)
        if hasattr(invite, 'description') and invite.description:
            msg_lines.append("Description: %s" % invite.description)

        if invite.location:
            msg_lines.append("Location: %s" % invite.location)
        if invite.event_date:
            msg_lines.append("Date: %s" % invite.event_date)
        if invite.valid_hours:
            msg_lines.append("Valid for: %s hours" % invite.valid_hours)
        if invite.max_guests:
            msg_lines.append("Guests: %s" % invite.max_guests)
        if invite.share_link:
            msg_lines.append("Link: %s" % invite.share_link)

        message = "\n".join(msg_lines)
        whatsapp_url = "https://web.whatsapp.com/send?text=%s" % urllib.parse.quote(message)
        return request.redirect(whatsapp_url)

    @http.route(
        ['/party/invite/<int:invite_id>/<string:token>'],
        type='http', auth='public', website=True, methods=['GET', 'POST'], csrf=False
    )
    def public_party_invite(self, invite_id, token, **post):
        Invite = request.env['party.group.invite'].sudo()
        invite = Invite.browse(invite_id)
        if not invite or invite.token != token or invite.state != 'active':
            return request.not_found()

        if request.httprequest.method == 'POST':
            guest_name = post.get('guest_name')
            guest_mobile = post.get('guest_mobile')
            return request.render('community_management.public_party_guest_success', {
                'invite': invite,
                'guest_name': guest_name,
            })

        return request.render('community_management.public_party_guest_form', {
            'invite': invite,
        })
