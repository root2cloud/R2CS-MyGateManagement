from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import base64


class FamilyMemberPortal(CustomerPortal):

    @http.route(['/my/family'], type='http', auth='user', website=True)
    def portal_my_family_members(self, **kw):
        """Display family members list"""
        partner = request.env.user.partner_id

        # Get family members for current tenant
        family_members = request.env['family.member'].search([('tenant_id', '=', partner.id)])

        return request.render('community_management.portal_my_family_members', {
            'family_members': family_members,
            'page_name': 'family',
        })

    @http.route(['/my/family/new'], type='http', auth='user', website=True)
    def portal_family_member_new(self, **kw):
        """Show form to add new family member"""
        return request.render('community_management.portal_family_member_form', {
            'member': None,
            'page_name': 'family',
        })

    @http.route(['/my/family/<int:member_id>/edit'], type='http', auth='user', website=True)
    def portal_family_member_edit(self, member_id, **kw):
        """Show form to edit family member"""
        member = request.env['family.member'].browse(member_id)

        # Check access
        if member.tenant_id != request.env.user.partner_id:
            return request.redirect('/my')

        return request.render('community_management.portal_family_member_form', {
            'member': member,
            'page_name': 'family',
        })

    @http.route(['/my/family/save'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_family_member_save(self, member_id=None, **post):
        """Save family member (create or update)"""
        partner = request.env.user.partner_id

        # Prepare values
        values = {
            'tenant_id': partner.id,
            'name': post.get('name'),
            'member_type': post.get('member_type'),
            'relationship': post.get('relationship') or False,
            'gender': post.get('gender') or False,
            'date_of_birth': post.get('date_of_birth') or False,
            'email': post.get('email') or False,
            'phone': post.get('phone') or False,
            'notes': post.get('notes') or False,
            'aadhaar_number': post.get('aadhaar_number') or False,
        }

        # Handle photo upload
        photo_file = request.httprequest.files.get('photo')
        if photo_file and photo_file.filename:
            values['photo'] = base64.b64encode(photo_file.read())

        # Create or update
        if member_id and member_id != 'None':
            member = request.env['family.member'].browse(int(member_id))
            # Check access
            if member.tenant_id == partner:
                member.write(values)
        else:
            request.env['family.member'].create(values)

        return request.redirect('/my/family')

    @http.route(['/my/family/<int:member_id>/delete'], type='http', auth='user', website=True)
    def portal_family_member_delete(self, member_id, **kw):
        """Delete family member"""
        member = request.env['family.member'].browse(member_id)

        # Check access
        if member.tenant_id == request.env.user.partner_id:
            member.unlink()

        return request.redirect('/my/family')
