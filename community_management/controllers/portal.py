from odoo import http
from odoo.http import request
import base64


class PortalFamilyMember(http.Controller):

    # =====================================================
    # CREATE FAMILY MEMBER
    # =====================================================
    @http.route(['/my/family-member/create'], type='http', auth="user", website=True)
    def create_family_member(self, **post):

        partner = request.env.user.partner_id

        if request.httprequest.method == 'POST':

            flat_id = int(post.get('flat_id'))

            # Security check
            flat = request.env['flat.management'].sudo().search([
                '|',
                ('tenant_id', '=', partner.id),
                ('lease_owner_id', '=', partner.id),
                ('id', '=', flat_id)
            ], limit=1)

            if not flat:
                return request.redirect('/my/my-properties')

            # Handle Photo
            photo = False
            if post.get('photo'):
                photo = base64.b64encode(post.get('photo').read())

            request.env['family.member'].sudo().create({
                'tenant_id': partner.id,
                'name': post.get('name'),
                'member_type': post.get('member_type'),
                'gender': post.get('gender'),
                'date_of_birth': post.get('date_of_birth'),
                'relationship': post.get('relationship'),
                'email': post.get('email'),
                'phone': post.get('phone'),
                'aadhaar_number': post.get('aadhaar_number'),
                'notes': post.get('notes'),
                'photo': photo,
            })

            return request.redirect('/my/my-properties?property_id=%s&success=created' % flat_id)

        flat = request.env['flat.management'].sudo().browse(int(post.get('flat_id')))
        return request.render('community_management.portal_family_member_form', {
            'page_name': 'create_family_member',
            'flat': flat,
            'member': False,
            'relationships': request.env['family.member']._fields['relationship'].selection,
            'genders': request.env['family.member']._fields['gender'].selection,
            'member_types': request.env['family.member']._fields['member_type'].selection,
        })


    # =====================================================
    # EDIT FAMILY MEMBER
    # =====================================================
    @http.route(['/my/family-member/edit/<int:member_id>'], type='http', auth="user", website=True)
    def edit_family_member(self, member_id, **post):

        partner = request.env.user.partner_id
        member = request.env['family.member'].sudo().browse(member_id)

        if member.tenant_id.id != partner.id:
            return request.redirect('/my/my-properties')

        if request.httprequest.method == 'POST':

            photo = member.photo
            if post.get('photo'):
                photo = base64.b64encode(post.get('photo').read())

            member.write({
                'name': post.get('name'),
                'member_type': post.get('member_type'),
                'gender': post.get('gender'),
                'date_of_birth': post.get('date_of_birth'),
                'relationship': post.get('relationship'),
                'email': post.get('email'),
                'phone': post.get('phone'),
                'aadhaar_number': post.get('aadhaar_number'),
                'notes': post.get('notes'),
                'photo': photo,
            })

            return request.redirect('/my/my-properties?property_id=%s&success=updated' % member.flat_id.id)

        return request.render('community_management.portal_family_member_form', {
            'page_name': 'edit_family_member',
            'member': member,
            'flat': member.flat_id,
            'relationships': request.env['family.member']._fields['relationship'].selection,
            'genders': request.env['family.member']._fields['gender'].selection,
            'member_types': request.env['family.member']._fields['member_type'].selection,
        })
