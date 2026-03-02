from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Vehicle(models.Model):
    _name = 'vehicle.management'
    _description = 'Vehicle Management'
    _rec_name = 'vehicle_number'

    # Tenant and Flat Information
    tenant_id = fields.Many2one('res.partner', string='Owner (Tenant)', required=True)
    flat_id = fields.Many2one('flat.management', string='Flat', required=True,
                              help="The flat where this vehicle is registered")
    building_id = fields.Many2one('building.management', string='Building',
                                  related='flat_id.building_id', store=True)
    community_id = fields.Many2one('community.management', string='Community',
                                   related='flat_id.community_id', store=True,
                                   help="The community where this vehicle is registered")

    # Vehicle Information
    vehicle_photo = fields.Image(string='Vehicle Photo', max_width=200, max_height=200)
    vehicle_number = fields.Char(string='Vehicle Number', required=True)
    vehicle_type = fields.Selection([
        ('car', 'Car'),
        ('motorcycle', 'Motorcycle'),
        ('bicycle', 'Bicycle'),
        ('scooter', 'Scooter'),
        ('other', 'Other')
    ], string='Vehicle Type', required=True, default='car')

    make = fields.Char(string='Make/Brand')
    model = fields.Char(string='Model')
    year = fields.Integer(string='Year')
    color = fields.Char(string='Color')

    # Additional Information
    notes = fields.Text(string='Additional Notes')
    active = fields.Boolean(string='Active', default=True)

    @api.model
    def default_get(self, fields_list):
        """Set default tenant_id for portal users and auto-set flat from tenant"""
        res = super(Vehicle, self).default_get(fields_list)

        # If portal user, set tenant_id to current user's partner
        if self.env.user.has_group('base.group_portal'):
            partner = self.env.user.partner_id
            res['tenant_id'] = partner.id

            # Auto-set flat_id from tenant's current lease if not already set
            if 'flat_id' not in res or not res.get('flat_id'):
                flat = self.env['flat.management'].search([
                    ('tenant_id', '=', partner.id)
                ], limit=1)
                if flat:
                    res['flat_id'] = flat.id

        return res

    @api.constrains('vehicle_number')
    def _check_vehicle_number(self):
        """Validate vehicle number uniqueness"""
        for record in self:
            if record.vehicle_number:
                existing = self.search([
                    ('vehicle_number', '=', record.vehicle_number),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(f"Vehicle number {record.vehicle_number} is already registered!")

# from odoo import models, fields, api
# from odoo.exceptions import ValidationError
#
#
# class Vehicle(models.Model):
#     _name = 'vehicle.management'
#     _description = 'Vehicle Management'
#     _rec_name = 'vehicle_number'
#
#     # Tenant and Flat Information
#     tenant_id = fields.Many2one('res.partner', string='Owner (Tenant)', required=True)
#     flat_id = fields.Many2one('flat.management', string='Flat', compute='_compute_flat_id', store=True)
#     building_id = fields.Many2one('building.management', string='Building', compute='_compute_building_id', store=True)
#
#     # Vehicle Information
#     vehicle_photo = fields.Image(string='Vehicle Photo', max_width=200, max_height=200)
#     vehicle_number = fields.Char(string='Vehicle Number', required=True)
#     vehicle_type = fields.Selection([
#         ('car', 'Car'),
#         ('motorcycle', 'Motorcycle'),
#         ('bicycle', 'Bicycle'),
#         ('scooter', 'Scooter'),
#         ('other', 'Other')
#     ], string='Vehicle Type', required=True, default='car')
#
#     make = fields.Char(string='Make/Brand')
#     model = fields.Char(string='Model')
#     year = fields.Integer(string='Year')
#     color = fields.Char(string='Color')
#
#     # Additional Information
#     notes = fields.Text(string='Additional Notes')
#     active = fields.Boolean(string='Active', default=True)
#
#     @api.depends('tenant_id')
#     def _compute_flat_id(self):
#         """Get flat from tenant's current lease"""
#         for record in self:
#             flat = self.env['flat.management'].search([
#                 ('tenant_id', '=', record.tenant_id.id)
#             ], limit=1)
#             record.flat_id = flat.id if flat else False
#
#     @api.depends('flat_id')
#     def _compute_building_id(self):
#         """Get building from flat"""
#         for record in self:
#             if record.flat_id and record.flat_id.building_id:
#                 record.building_id = record.flat_id.building_id.id
#             else:
#                 record.building_id = False
#
#     @api.model
#     def default_get(self, fields_list):
#         """Set default tenant_id for portal users"""
#         res = super(Vehicle, self).default_get(fields_list)
#         if self.env.user.has_group('base.group_portal'):
#             res['tenant_id'] = self.env.user.partner_id.id
#         return res
#
#     @api.constrains('vehicle_number')
#     def _check_vehicle_number(self):
#         """Validate vehicle number uniqueness"""
#         for record in self:
#             if record.vehicle_number:
#                 existing = self.search([
#                     ('vehicle_number', '=', record.vehicle_number),
#                     ('id', '!=', record.id)
#                 ])
#                 if existing:
#                     raise ValidationError(f"Vehicle number {record.vehicle_number} is already registered!")
