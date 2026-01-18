from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import qrcode
import base64
from io import BytesIO
import secrets
import string

class FamilyMember(models.Model):
    _name = 'family.member'
    _description = 'Family Member'
    _rec_name = 'name'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # Tenant and Flat Information
    tenant_id = fields.Many2one('res.partner', string='Tenant', required=True)
    flat_id = fields.Many2one('flat.management', string='Flat', compute='_compute_flat_id', store=True)
    building_id = fields.Many2one('building.management', string='Building', compute='_compute_building_id', store=True)

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

    # @api.constrains('aadhaar_number')
    # def _check_aadhaar_number(self):
    #     pattern = r'^\d{12}$'  # Aadhaar is 12 digits exactly
    #     for record in self:
    #         if record.aadhaar_number and not re.match(pattern, record.aadhaar_number):
    #             raise ValidationError(_('Please enter a valid 12-digit Aadhaar Number.'))

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

    @api.depends('tenant_id')
    def _compute_flat_id(self):
        """Get flat from tenant's current lease"""
        for record in self:
            # Find flat where this tenant is current tenant
            flat = self.env['flat.management'].search([
                ('tenant_id', '=', record.tenant_id.id)
            ], limit=1)
            record.flat_id = flat.id if flat else False

    @api.depends('flat_id')
    def _compute_building_id(self):
        """Get building from flat"""
        for record in self:
            if record.flat_id and record.flat_id.building_id:
                record.building_id = record.flat_id.building_id.id
            else:
                record.building_id = False

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
        import re
        for record in self:
            if record.email:
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', record.email):
                    raise ValidationError("Please enter a valid email address.")

    @api.model
    def default_get(self, fields_list):
        """Set default tenant_id for portal users"""
        res = super(FamilyMember, self).default_get(fields_list)
        # If portal user, set tenant_id to current user's partner
        if self.env.user.has_group('base.group_portal'):
            res['tenant_id'] = self.env.user.partner_id.id
        return res
# ----
    resident_id = fields.Char(
        string='Resident ID',
        readonly=True,
        unique=True,
        copy=False,
        tracking=True
    )

    qr_code = fields.Binary(
        string='QR Code',
        compute='_generate_qr_code',
        store=True,
        readonly=True
    )

    qr_code_image = fields.Binary(
        string='QR Code Image',
        attachment=True
    )

    # Existing fields...

    @api.model
    def create(self, vals):
        """Generate unique Resident ID on create"""
        record = super(FamilyMember, self).create(vals)

        # Generate unique Resident ID if not provided
        if not record.resident_id:
            record.generate_resident_id()

        # Generate QR Code
        record.generate_qr_code_image()

        return record

    def generate_resident_id(self):
        """Generate unique Resident ID"""
        for record in self:
            # Format: SOC-{SequentialID}-{Random6Digits}
            # Get the sequence for this tenant
            tenant_code = ''
            if record.tenant_id:
                # Use tenant's initials
                tenant_name = record.tenant_id.name or ''
                initials = ''.join([word[0].upper() for word in tenant_name.split() if word])
                if initials:
                    tenant_code = initials[:3]
                else:
                    tenant_code = 'TNT'
            else:
                tenant_code = 'TNT'

            # Get sequential number for this tenant's family members
            if record.tenant_id:
                sequence = self.env['family.member'].search_count([
                    ('tenant_id', '=', record.tenant_id.id),
                    ('id', '<', record.id or 0)  # For new records
                ]) + 1
            else:
                sequence = 1

            # Generate 6 random digits
            random_digits = ''.join(secrets.choice(string.digits) for _ in range(6))

            # Create the resident ID
            record.resident_id = f"SOC-{tenant_code}-{sequence:03d}-{random_digits}"

    def generate_qr_code_image(self):
        """Generate QR code image from resident ID"""
        for record in self:
            if record.resident_id:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(record.resident_id)
                qr.make(fit=True)

                img = qr.make_image(fill_color="black", back_color="white")

                # Convert to base64
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                record.qr_code_image = base64.b64encode(buffered.getvalue())

    @api.depends('resident_id')
    def _generate_qr_code(self):
        """Generate QR code for display"""
        for record in self:
            if record.resident_id and not record.qr_code_image:
                record.generate_qr_code_image()

    # Add to your constraints to ensure uniqueness
    _sql_constraints = [
        ('resident_id_unique', 'UNIQUE(resident_id)', 'Resident ID must be unique!'),
    ]

    def action_generate_missing_ids(self):
        """Generate resident IDs for all family members that don't have one"""
        members_without_id = self.search([('resident_id', '=', False)])

        for member in members_without_id:
            member.generate_resident_id()
            member.generate_qr_code_image()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Resident IDs Generated',
                'message': f'Generated resident IDs for {len(members_without_id)} family members',
                'type': 'success',
                'sticky': False,
            }
        }
