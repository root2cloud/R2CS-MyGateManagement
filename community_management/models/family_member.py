from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import qrcode
import base64
from io import BytesIO
import secrets
import string
import logging

_logger = logging.getLogger(__name__)


class FamilyMember(models.Model):
    _name = 'family.member'
    _description = 'Family Member'
    _rec_name = 'name'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # Tenant and Flat Information
    tenant_id = fields.Many2one('res.partner', string='Tenant', required=True)
    flat_id = fields.Many2one('flat.management', string='Flat', required=True,
                              help="The flat where this family member resides")
    building_id = fields.Many2one('building.management', string='Building',
                                  related='flat_id.building_id', store=True)
    community_id = fields.Many2one('community.management', string='Community',
                                   related='flat_id.community_id', store=True,
                                   help="The community where this family member resides")

    # Personal Information
    name = fields.Char(string='Name', required=True)
    photo = fields.Image(string='Photo', max_width=200, max_height=200)
    member_type = fields.Selection([
        ('adult', 'Adult'),
        ('child', 'Child')
    ], string='Type', required=True, default='adult')

    # Contact Information
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    aadhaar_number = fields.Char(string='Aadhaar Number', tracking=True)

    # Additional Information
    date_of_birth = fields.Date(string='Date of Birth')
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender')

    relationship = fields.Selection([
        ('spouse', 'Spouse'),
        ('son', 'Son'),
        ('daughter', 'Daughter'),
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('brother', 'Brother'),
        ('sister', 'Sister'),
        ('other', 'Other')
    ], string='Relationship with Tenant')

    notes = fields.Text(string='Notes')

    # Resident ID and QR Code
    resident_id = fields.Char(
        string='Resident ID',
        readonly=True,
        copy=False,
        tracking=True
    )

    # IMPORTANT: Binary field without attachment=True for portal display
    qr_code_image = fields.Binary(
        string='QR Code Image',
        help="QR Code generated from Resident ID",
        attachment=False  # This ensures it's stored in database directly
    )

    @api.depends('date_of_birth')
    def _compute_age(self):
        """Calculate age from date of birth"""
        from datetime import date
        for record in self:
            if record.date_of_birth:
                today = date.today()
                dob = fields.Date.from_string(record.date_of_birth)
                record.age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            else:
                record.age = 0

    @api.constrains('email')
    def _check_email(self):
        """Validate email format"""
        for record in self:
            if record.email:
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', record.email):
                    raise ValidationError("Please enter a valid email address.")

    @api.model
    def create(self, vals):
        """Generate unique Resident ID and QR code on create"""
        # First create the record
        record = super(FamilyMember, self).create(vals)

        # Then generate resident ID
        if not record.resident_id:
            record._generate_resident_id()

        # Then generate QR code
        record._generate_qr_code_image()

        return record

    def write(self, vals):
        """Update record and regenerate QR code if needed"""
        result = super(FamilyMember, self).write(vals)

        # Regenerate QR code if resident_id or name changed and we're not already updating QR
        if 'qr_code_image' not in vals:
            for record in self:
                if record.resident_id:
                    record._generate_qr_code_image()

        return result

    def _generate_resident_id(self):
        """Generate unique Resident ID"""
        for record in self:
            if not record.resident_id:
                community_code = 'COM'
                if record.community_id:
                    community_code = record.community_id.name[:3].upper()

                if record.tenant_id:
                    sequence = self.env['family.member'].search_count([
                        ('tenant_id', '=', record.tenant_id.id),
                        ('id', '<', record.id or 0)
                    ]) + 1
                else:
                    sequence = 1

                # Get tenant initials
                tenant_initials = ''
                if record.tenant_id and record.tenant_id.name:
                    tenant_initials = ''.join([word[0].upper() for word in record.tenant_id.name.split() if word])[:3]

                random_digits = ''.join(secrets.choice(string.digits) for _ in range(6))
                record.resident_id = "SOC-%s-%s-%03d-%s" % (community_code, tenant_initials, sequence, random_digits)

                _logger.info("Generated Resident ID: %s for member: %s", record.resident_id, record.name)

    def _generate_qr_code_image(self):
        """
        Generate QR code image from resident ID and store as base64.
        This is the fixed version that ensures proper QR generation.
        """
        for record in self:
            if not record.resident_id:
                _logger.warning("Cannot generate QR - no resident_id for member: %s", record.name)
                continue

            try:
                # Create QR code instance
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )

                # Prepare QR data with comprehensive information
                qr_data = f"""Resident ID: {record.resident_id}
Name: {record.name}
Flat: {record.flat_id.name if record.flat_id else 'N/A'}
Community: {record.community_id.name if record.community_id else 'N/A'}
Phone: {record.phone or 'N/A'}
Email: {record.email or 'N/A'}
Type: {record.member_type}
Relationship: {record.relationship or 'N/A'}"""

                qr.add_data(qr_data)
                qr.make(fit=True)

                # Create image
                img = qr.make_image(fill_color="black", back_color="white")

                # Convert to bytes
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_bytes = buffered.getvalue()

                # Convert to base64 (as bytes, not string)
                base64_bytes = base64.b64encode(img_bytes)

                # Update the record
                record.write({'qr_code_image': base64_bytes})

                _logger.info("Generated QR Code for member: %s (resident_id: %s)",
                             record.name, record.resident_id)

            except Exception as e:
                _logger.error("Error generating QR code for %s: %s", record.name, str(e))

    def generate_resident_id(self):
        """Public method to generate resident ID (for server actions)"""
        self._generate_resident_id()
        return True

    def generate_qr_code_image(self):
        """Public method to generate QR code (for server actions)"""
        self._generate_qr_code_image()
        return True

    def action_generate_missing_ids(self):
        """Generate resident IDs and QR codes for all members missing them"""
        members_without_id = self.search([
            '|',
            ('resident_id', '=', False),
            ('qr_code_image', '=', False)
        ])

        for member in members_without_id:
            if not member.resident_id:
                member._generate_resident_id()
            if not member.qr_code_image:
                member._generate_qr_code_image()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Generated resident IDs and QR codes for %d family members' % len(members_without_id),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_regenerate_qr_codes(self):
        """Regenerate QR codes for selected members"""
        for record in self:
            record._generate_qr_code_image()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'QR codes regenerated for %d members' % len(self),
                'type': 'success',
                'sticky': False,
            }
        }

# from odoo import models, fields, api, _
# from odoo.exceptions import ValidationError
# import re
# import qrcode
# import base64
# from io import BytesIO
# import secrets
# import string
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class FamilyMember(models.Model):
#     _name = 'family.member'
#     _description = 'Family Member'
#     _rec_name = 'name'
#     _inherit = ["mail.thread", "mail.activity.mixin"]
#
#     # Tenant and Flat Information
#     tenant_id = fields.Many2one('res.partner', string='Tenant', required=True)
#     flat_id = fields.Many2one('flat.management', string='Flat', required=True,
#                               help="The flat where this family member resides")
#     building_id = fields.Many2one('building.management', string='Building',
#                                   related='flat_id.building_id', store=True)
#     community_id = fields.Many2one('community.management', string='Community',
#                                    related='flat_id.community_id', store=True,
#                                    help="The community where this family member resides")
#
#     # Personal Information
#     name = fields.Char(string='Name', required=True)
#     photo = fields.Image(string='Photo', max_width=200, max_height=200)
#     member_type = fields.Selection([
#         ('adult', 'Adult'),
#         ('child', 'Child')
#     ], string='Type', required=True, default='adult')
#
#     # Contact Information
#     email = fields.Char(string='Email')
#     phone = fields.Char(string='Phone')
#     aadhaar_number = fields.Char(string='Aadhaar Number', tracking=True)
#
#     # Additional Information
#     date_of_birth = fields.Date(string='Date of Birth')
#     age = fields.Integer(string='Age', compute='_compute_age', store=True)
#     gender = fields.Selection([
#         ('male', 'Male'),
#         ('female', 'Female'),
#         ('other', 'Other')
#     ], string='Gender')
#
#     relationship = fields.Selection([
#         ('spouse', 'Spouse'),
#         ('son', 'Son'),
#         ('daughter', 'Daughter'),
#         ('father', 'Father'),
#         ('mother', 'Mother'),
#         ('brother', 'Brother'),
#         ('sister', 'Sister'),
#         ('other', 'Other')
#     ], string='Relationship with Tenant')
#
#     notes = fields.Text(string='Notes')
#
#     # Resident ID and QR Code
#     resident_id = fields.Char(
#         string='Resident ID',
#         readonly=True,
#         copy=False,
#         tracking=True
#     )
#
#     # FIXED: No attachment=True to store as plain base64
#     qr_code_image = fields.Binary(
#         string='QR Code Image',
#         help="QR Code generated from Resident ID"
#     )
#
#     @api.depends('date_of_birth')
#     def _compute_age(self):
#         """Calculate age from date of birth"""
#         from datetime import date
#         for record in self:
#             if record.date_of_birth:
#                 today = date.today()
#                 dob = fields.Date.from_string(record.date_of_birth)
#                 record.age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
#             else:
#                 record.age = 0
#
#     @api.constrains('email')
#     def _check_email(self):
#         """Validate email format"""
#         for record in self:
#             if record.email:
#                 if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', record.email):
#                     raise ValidationError("Please enter a valid email address.")
#
#     @api.model
#     def default_get(self, fields_list):
#         """Set default tenant_id for portal users and auto-set flat from tenant"""
#         res = super(FamilyMember, self).default_get(fields_list)
#
#         if self.env.user.has_group('base.group_portal'):
#             partner = self.env.user.partner_id
#             res['tenant_id'] = partner.id
#
#             if 'flat_id' not in res or not res.get('flat_id'):
#                 flat = self.env['flat.management'].search([
#                     ('tenant_id', '=', partner.id)
#                 ], limit=1)
#                 if flat:
#                     res['flat_id'] = flat.id
#
#         return res
#
#     @api.model
#     def create(self, vals):
#         """Generate unique Resident ID and QR code on create"""
#         # First create the record
#         record = super(FamilyMember, self).create(vals)
#
#         # Then generate resident ID
#         record._generate_resident_id()
#
#         # Then generate QR code
#         record._generate_qr_code_image()
#
#         return record
#
#     def write(self, vals):
#         """FIXED: No infinite recursion - separate QR generation logic"""
#         result = super(FamilyMember, self).write(vals)
#
#         # Only generate QR if we're not already writing it and if resident_id exists
#         for record in self:
#             if 'qr_code_image' not in vals and record.resident_id:
#                 # Generate QR code only if it doesn't exist
#                 if not record.qr_code_image:
#                     record._generate_qr_code_image()
#
#         return result
#
#     def _generate_resident_id(self):
#         """Generate unique Resident ID (internal method)"""
#         for record in self:
#             if not record.resident_id:
#                 community_code = 'COM'
#                 if record.community_id:
#                     community_code = record.community_id.name[:3].upper()
#
#                 if record.tenant_id:
#                     sequence = self.env['family.member'].search_count([
#                         ('tenant_id', '=', record.tenant_id.id),
#                         ('id', '<', record.id or 0)
#                     ]) + 1
#                 else:
#                     sequence = 1
#
#                 random_digits = ''.join(secrets.choice(string.digits) for _ in range(6))
#                 record.resident_id = "SOC-%s-%03d-%s" % (community_code, sequence, random_digits)
#
#                 _logger.info("Generated Resident ID: %s for member: %s", record.resident_id, record.name)
#
#     def _generate_qr_code_image(self):
#         """
#         Generate QR code image from resident ID and store as plain base64.
#         FIXED: No recursion, proper error handling, and correct base64 encoding.
#         """
#         for record in self:
#             if not record.resident_id:
#                 _logger.warning("Cannot generate QR - no resident_id for member: %s", record.name)
#                 continue
#
#             try:
#                 qr = qrcode.QRCode(
#                     version=1,
#                     error_correction=qrcode.constants.ERROR_CORRECT_L,
#                     box_size=10,
#                     border=4,
#                 )
#
#                 # Prepare QR data with comprehensive information
#                 qr_data = "\n".join([
#                     f"Resident ID: {record.resident_id}",
#                     f"Name: {record.name}",
#                     f"Flat: {record.flat_id.name if record.flat_id else 'N/A'}",
#                     f"Community: {record.community_id.name if record.community_id else 'N/A'}",
#                     f"Phone: {record.phone or 'N/A'}",
#                     f"Email: {record.email or 'N/A'}"
#                 ])
#
#                 qr.add_data(qr_data)
#                 qr.make(fit=True)
#
#                 img = qr.make_image(fill_color="black", back_color="white")
#
#                 buffered = BytesIO()
#                 img.save(buffered, format="PNG")
#
#                 # Convert to base64 and decode to string
#                 base64_string = base64.b64encode(buffered.getvalue()).decode('utf-8')
#
#                 # Update without triggering recursion (using super write)
#                 super(FamilyMember, record).write({'qr_code_image': base64_string})
#
#                 _logger.info("Generated QR Code for member: %s (resident_id: %s)",
#                              record.name, record.resident_id)
#
#             except Exception as e:
#                 _logger.error("Error generating QR code for %s: %s", record.name, str(e))
#
#     def generate_resident_id(self):
#         """Public method to generate resident ID (for server actions)"""
#         self._generate_resident_id()
#         return True
#
#     def generate_qr_code_image(self):
#         """Public method to generate QR code (for server actions)"""
#         self._generate_qr_code_image()
#         return True
#
#     def action_generate_missing_ids(self):
#         """Generate resident IDs and QR codes for all members missing them"""
#         members_without_id = self.search([
#             '|',
#             ('resident_id', '=', False),
#             ('qr_code_image', '=', False)
#         ])
#
#         for member in members_without_id:
#             if not member.resident_id:
#                 member._generate_resident_id()
#             if not member.qr_code_image:
#                 member._generate_qr_code_image()
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': 'Success',
#                 'message': 'Generated resident IDs and QR codes for %d family members' % len(members_without_id),
#                 'type': 'success',
#                 'sticky': False,
#             }
#         }
#
#     def action_regenerate_qr_codes(self):
#         """Regenerate QR codes for selected members"""
#         for record in self:
#             record._generate_qr_code_image()
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': 'Success',
#                 'message': 'QR codes regenerated for %d members' % len(self),
#                 'type': 'success',
#                 'sticky': False,
#             }
#         }
#
# # from odoo import models, fields, api, _
# # from odoo.exceptions import ValidationError
# # import re
# # import qrcode
# # import base64
# # from io import BytesIO
# # import secrets
# # import string
# # import logging
# #
# # _logger = logging.getLogger(__name__)
# #
# #
# # class FamilyMember(models.Model):
# #     _name = 'family.member'
# #     _description = 'Family Member'
# #     _rec_name = 'name'
# #     _inherit = ["mail.thread", "mail.activity.mixin"]
# #
# #     # Tenant and Flat Information
# #     tenant_id = fields.Many2one('res.partner', string='Tenant', required=True)
# #     flat_id = fields.Many2one('flat.management', string='Flat', required=True,
# #                               help="The flat where this family member resides")
# #     building_id = fields.Many2one('building.management', string='Building',
# #                                   related='flat_id.building_id', store=True)
# #     community_id = fields.Many2one('community.management', string='Community',
# #                                    related='flat_id.community_id', store=True,
# #                                    help="The community where this family member resides")
# #
# #     # Personal Information
# #     name = fields.Char(string='Name', required=True)
# #     photo = fields.Image(string='Photo', max_width=200, max_height=200)
# #     member_type = fields.Selection([
# #         ('adult', 'Adult'),
# #         ('child', 'Child')
# #     ], string='Type', required=True, default='adult')
# #
# #     # Contact Information
# #     email = fields.Char(string='Email')
# #     phone = fields.Char(string='Phone')
# #     aadhaar_number = fields.Char(string='Aadhaar Number', tracking=True)
# #
# #     # Additional Information
# #     date_of_birth = fields.Date(string='Date of Birth')
# #     age = fields.Integer(string='Age', compute='_compute_age', store=True)
# #     gender = fields.Selection([
# #         ('male', 'Male'),
# #         ('female', 'Female'),
# #         ('other', 'Other')
# #     ], string='Gender')
# #
# #     relationship = fields.Selection([
# #         ('spouse', 'Spouse'),
# #         ('son', 'Son'),
# #         ('daughter', 'Daughter'),
# #         ('father', 'Father'),
# #         ('mother', 'Mother'),
# #         ('brother', 'Brother'),
# #         ('sister', 'Sister'),
# #         ('other', 'Other')
# #     ], string='Relationship with Tenant')
# #
# #     notes = fields.Text(string='Notes')
# #
# #     # Resident ID and QR Code
# #     resident_id = fields.Char(
# #         string='Resident ID',
# #         readonly=True,
# #         copy=False,
# #         tracking=True
# #     )
# #
# #     # -------------------------------------------------------
# #     # KEY FIX: removed attachment=True
# #     # With attachment=True, Odoo stores the image as an IR
# #     # attachment and returns it differently — the portal
# #     # template's  data:image/png;base64,%s  rendering breaks.
# #     # Without attachment=True, the base64 string is stored
# #     # directly in the DB column and reads correctly.
# #     # -------------------------------------------------------
# #     qr_code_image = fields.Binary(
# #         string='QR Code Image',
# #         help="QR Code generated from Resident ID"
# #     )
# #
# #     @api.depends('date_of_birth')
# #     def _compute_age(self):
# #         """Calculate age from date of birth"""
# #         from datetime import date
# #         for record in self:
# #             if record.date_of_birth:
# #                 today = date.today()
# #                 dob = fields.Date.from_string(record.date_of_birth)
# #                 record.age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
# #             else:
# #                 record.age = 0
# #
# #     @api.constrains('email')
# #     def _check_email(self):
# #         """Validate email format"""
# #         for record in self:
# #             if record.email:
# #                 if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', record.email):
# #                     raise ValidationError("Please enter a valid email address.")
# #
# #     @api.model
# #     def default_get(self, fields_list):
# #         """Set default tenant_id for portal users and auto-set flat from tenant"""
# #         res = super(FamilyMember, self).default_get(fields_list)
# #
# #         if self.env.user.has_group('base.group_portal'):
# #             partner = self.env.user.partner_id
# #             res['tenant_id'] = partner.id
# #
# #             if 'flat_id' not in res or not res.get('flat_id'):
# #                 flat = self.env['flat.management'].search([
# #                     ('tenant_id', '=', partner.id)
# #                 ], limit=1)
# #                 if flat:
# #                     res['flat_id'] = flat.id
# #
# #         return res
# #
# #     @api.model
# #     def create(self, vals):
# #         """Generate unique Resident ID and QR code on create"""
# #         record = super(FamilyMember, self).create(vals)
# #
# #         if not record.resident_id:
# #             record.generate_resident_id()
# #
# #         # Generate QR code after resident_id is set
# #         record.generate_qr_code_image()
# #
# #         return record
# #
# #     def write(self, vals):
# #         """
# #         FIX: The original write() called generate_qr_code_image() which
# #         itself calls record.write({'qr_code_image': ...}), causing infinite
# #         recursion. We now guard against this by checking if we are already
# #         writing qr_code_image to prevent the loop.
# #         """
# #         result = super(FamilyMember, self).write(vals)
# #
# #         # Only regenerate QR if we are NOT already writing the qr_code_image
# #         # (avoids infinite recursion: write -> generate_qr -> write -> ...)
# #         if 'qr_code_image' not in vals:
# #             for record in self:
# #                 if not record.resident_id:
# #                     record.generate_resident_id()
# #                 if not record.qr_code_image:
# #                     record.generate_qr_code_image()
# #
# #         return result
# #
# #     def generate_resident_id(self):
# #         """Generate unique Resident ID"""
# #         for record in self:
# #             community_code = 'COM'
# #             if record.community_id:
# #                 community_code = record.community_id.name[:3].upper()
# #
# #             if record.tenant_id:
# #                 sequence = self.env['family.member'].search_count([
# #                     ('tenant_id', '=', record.tenant_id.id),
# #                     ('id', '<', record.id or 0)
# #                 ]) + 1
# #             else:
# #                 sequence = 1
# #
# #             random_digits = ''.join(secrets.choice(string.digits) for _ in range(6))
# #             record.resident_id = "SOC-%s-%03d-%s" % (community_code, sequence, random_digits)
# #
# #             _logger.info("Generated Resident ID: %s for member: %s", record.resident_id, record.name)
# #
# #     def generate_qr_code_image(self):
# #         """
# #         Generate QR code image from resident ID and store as plain base64.
# #         The field must NOT have attachment=True for portal rendering to work.
# #         """
# #         for record in self:
# #             if not record.resident_id:
# #                 _logger.warning("Cannot generate QR - no resident_id for member: %s", record.name)
# #                 continue
# #             try:
# #                 qr = qrcode.QRCode(
# #                     version=1,
# #                     error_correction=qrcode.constants.ERROR_CORRECT_L,
# #                     box_size=10,
# #                     border=4,
# #                 )
# #
# #                 qr_data = (
# #                     "Resident ID: %s\n"
# #                     "Name: %s\n"
# #                     "Flat: %s\n"
# #                     "Community: %s"
# #                 ) % (
# #                     record.resident_id,
# #                     record.name,
# #                     record.flat_id.name if record.flat_id else 'N/A',
# #                     record.community_id.name if record.community_id else 'N/A',
# #                 )
# #
# #                 qr.add_data(qr_data)
# #                 qr.make(fit=True)
# #
# #                 img = qr.make_image(fill_color="black", back_color="white")
# #
# #                 buffered = BytesIO()
# #                 img.save(buffered, format="PNG")
# #
# #                 # Store as base64 — works correctly with portal template:
# #                 # t-att-src="'data:image/png;base64,%s' % member.qr_code_image"
# #                 record.qr_code_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
# #
# #                 _logger.info("Generated QR Code for member: %s (resident_id: %s)",
# #                              record.name, record.resident_id)
# #
# #             except Exception as e:
# #                 _logger.error("Error generating QR code for %s: %s", record.name, str(e))
# #
# #     def action_generate_missing_ids(self):
# #         """Generate resident IDs and QR codes for all members missing them"""
# #         members_without_id = self.search([
# #             '|',
# #             ('resident_id', '=', False),
# #             ('qr_code_image', '=', False)
# #         ])
# #
# #         for member in members_without_id:
# #             if not member.resident_id:
# #                 member.generate_resident_id()
# #             if not member.qr_code_image:
# #                 member.generate_qr_code_image()
# #
# #         return {
# #             'type': 'ir.actions.client',
# #             'tag': 'display_notification',
# #             'params': {
# #                 'title': 'Resident IDs Generated',
# #                 'message': 'Generated resident IDs and QR codes for %d family members' % len(members_without_id),
# #                 'type': 'success',
# #                 'sticky': False,
# #             }
# #         }
# #
# #
