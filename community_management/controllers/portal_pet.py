from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import base64


class PetPortal(CustomerPortal):
    """Portal controller for Pet Management"""

    @http.route(['/my/pets'], type='http', auth='user', website=True)
    def portal_my_pets(self, **kw):
        """Display pets list"""
        partner = request.env.user.partner_id
        pets = request.env['pet.management'].search([('tenant_id', '=', partner.id)])

        return request.render('community_management.portal_my_pets', {
            'pets': pets,
            'page_name': 'pets',
        })

    @http.route(['/my/pets/new'], type='http', auth='user', website=True)
    def portal_pet_new(self, **kw):
        """Show form to add new pet"""
        return request.render('community_management.portal_pet_form', {
            'pet': None,
            'page_name': 'pets',
        })

    @http.route(['/my/pets/<int:pet_id>/edit'], type='http', auth='user', website=True)
    def portal_pet_edit(self, pet_id, **kw):
        """Show form to edit pet"""
        pet = request.env['pet.management'].browse(pet_id)

        # Check access - tenant can only edit their own pets
        if pet.tenant_id != request.env.user.partner_id:
            return request.redirect('/my')

        return request.render('community_management.portal_pet_form', {
            'pet': pet,
            'page_name': 'pets',
        })

    @http.route(['/my/pets/save'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_pet_save(self, pet_id=None, **post):
        """Save pet (create or update)"""
        partner = request.env.user.partner_id

        # Prepare values from form
        values = {
            'tenant_id': partner.id,
            'name': post.get('name'),
            'pet_type': post.get('pet_type'),
            'breed': post.get('breed') or False,
            'color': post.get('color') or False,
            'gender': post.get('gender') or False,
            'date_of_birth': post.get('date_of_birth') or False,
            'weight': float(post.get('weight', 0)) if post.get('weight') else False,
            'microchip_number': post.get('microchip_number') or False,
            'license_number': post.get('license_number') or False,
            'vaccination_status': post.get('vaccination_status'),
            'last_vaccination_date': post.get('last_vaccination_date') or False,
            'next_vaccination_date': post.get('next_vaccination_date') or False,
            'veterinarian': post.get('veterinarian') or False,
            'vet_phone': post.get('vet_phone') or False,
            'medical_conditions': post.get('medical_conditions') or False,
            'allergies': post.get('allergies') or False,
            'special_needs': post.get('special_needs') or False,
            'notes': post.get('notes') or False,
        }

        # Handle photo upload
        photo_file = request.httprequest.files.get('photo')
        if photo_file and photo_file.filename:
            values['photo'] = base64.b64encode(photo_file.read())

        # Create or update pet
        if pet_id and pet_id != 'None':
            pet = request.env['pet.management'].browse(int(pet_id))
            # Security check - tenant can only update their own pets
            if pet.tenant_id == partner:
                pet.write(values)
        else:
            request.env['pet.management'].create(values)

        return request.redirect('/my/pets')

    @http.route(['/my/pets/<int:pet_id>/delete'], type='http', auth='user', website=True)
    def portal_pet_delete(self, pet_id, **kw):
        """Delete pet"""
        pet = request.env['pet.management'].browse(pet_id)

        # Security check - tenant can only delete their own pets
        if pet.tenant_id == request.env.user.partner_id:
            pet.unlink()

        return request.redirect('/my/pets')
