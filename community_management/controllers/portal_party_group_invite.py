from odoo import http
from odoo.http import request
from datetime import datetime
import urllib.parse


class PortalPartyGroupInvite(http.Controller):
    @http.route('/my/party/group/invite/delete/<int:invite_id>',
                type='http', auth='user', website=True, csrf=True)
    def delete_invitation(self, invite_id):
        invitation = request.env['party.group.invite'].sudo().browse(invite_id)

        if invitation.exists():
            invitation.unlink()

        return request.redirect('/my/party/group/invite')



    @http.route(
        ['/my/party/group/invite', '/my/party/group/invite/<int:invite_id>'],
        type='http', auth='user', website=True, methods=['GET', 'POST'], csrf=False
    )
    def portal_party_group_invite(self, invite_id=None, **post):
        partner = request.env.user.partner_id
        Invite = request.env['party.group.invite'].sudo()

        invite = Invite.browse(invite_id) if invite_id else False

        # Single submit handling (create or update with all data)
        if post.get('step') == 'submit':
            start_time = 0.0
            if post.get('start_time'):
                try:
                    hh, mm = post.get('start_time').split(':')
                    start_time = int(hh) + int(mm) / 60.0
                except:
                    start_time = 0.0

            vals = {
                'host_id': partner.id,
                'note': post.get('note') or False,
                'description': post.get('description') or False,  # Added if your model has it
                'event_date': post.get('event_date') or False,
                'start_time': start_time,
                'valid_hours': float(post.get('valid_hours') or 8.0),
                'location': post.get('location') or False,
                'max_guests': int(post.get('max_guests') or 5),
            }

            if invite and invite.exists():
                invite.write(vals)
                if invite.state != 'active':
                    invite.action_activate()
            else:
                invite = Invite.create(vals)
                invite.action_activate()

            return request.redirect('/my/party/group/invite')  # Back to list after create/update

        # DELETE invitation
        if post.get('action') == 'delete':
            delete_invite_id = int(post.get('invite_id')) if post.get('invite_id') else None
            if delete_invite_id:
                invite_to_delete = Invite.browse(delete_invite_id)
                if invite_to_delete.exists() and invite_to_delete.host_id == partner:
                    invite_to_delete.unlink()  # Delete the record
            return request.redirect('/my/party/group/invite')

        # Normal page load (list + detail view)
        invites = Invite.search([('host_id', '=', partner.id)], order='id desc')
        if invite_id and not invite.exists():
            invite = False

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