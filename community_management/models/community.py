from odoo import models, fields, api

class Community(models.Model):
    _name = 'community.management'
    _description = 'Community'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Community Name', required=True)
    country_id = fields.Many2one('res.country', string='Country', required=True)
    state_id = fields.Many2one('res.country.state', string='State', domain="[('country_id', '=', country_id)]")
    city = fields.Char(string='City')
    street = fields.Char(string='Street')
    zip = fields.Char(string='Zip Code')
    logo = fields.Image(string='Community Logo')
    description = fields.Text(string='Description')
    nearby_facility_ids = fields.One2many('nearby.facility', 'community_id', string='Nearby Facilities')
    # --

    building_count = fields.Integer(string='Buildings',
                                    compute='_compute_building_count',
                                    store=True)
    floor_count = fields.Integer(string='Floors',
                                 compute='_compute_floor_count',
                                 store=True)
    flat_count = fields.Integer(string='Flats',
                                compute='_compute_flat_count',
                                store=True)

    building_ids = fields.One2many(
        'building.management',  # model name of buildings
        'community_id',  # Many2one field in building pointing to community
        string='Buildings'
    )

    @api.depends('building_ids')
    def _compute_building_count(self):
        for record in self:
            record.building_count = len(record.building_ids)

    @api.depends('building_ids.floor_ids')
    def _compute_floor_count(self):
        for record in self:
            floors = self.env['floor.management'].search([('building_id.community_id', '=', record.id)])
            record.floor_count = len(floors)

    @api.depends('building_ids.floor_ids.flat_ids')
    def _compute_flat_count(self):
        for record in self:
            flats = self.env['flat.management'].search([('building_id.community_id', '=', record.id)])
            record.flat_count = len(flats)

    # Smart Button Actions
    def action_view_buildings(self):
        """Open Buildings list for this community"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Buildings - {self.name}',
            'res_model': 'building.management',
            'view_mode': 'list,form,kanban',
            'domain': [('community_id', '=', self.id)],
            'context': {'default_community_id': self.id},
            'target': 'current',
        }

    def action_view_floors(self):
        """Open Floors list for this community"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Floors - {self.name}',
            'res_model': 'floor.management',
            'view_mode': 'list,form,kanban',
            'domain': [('building_id.community_id', '=', self.id)],
            'context': {'default_community_id': self.building_ids[0].id if self.building_ids else False},
            'target': 'current',
        }

    def action_view_flats(self):
        """Open Flats list for this community"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Flats - {self.name}',
            'res_model': 'flat.management',
            'view_mode': 'list,form,kanban',
            'domain': [('building_id.community_id', '=', self.id)],
            'context': {'default_community_id': self.building_ids[0].id if self.building_ids else False},
            'target': 'current',
        }







# ---
    @api.onchange('country_id')
    def _onchange_country_id(self):
        # Clear state when country changes
        if self.country_id:
            self.state_id = False
        return {'domain': {'state_id': [('country_id', '=', self.country_id.id)]}}



    # -----
    floor_ids = fields.One2many(
        'floor.management',
        compute='_compute_floor_ids',
        string='Floors',
        store=False
    )

    flat_ids = fields.One2many(
        'flat.management',
        compute='_compute_flat_ids',
        string='Flats',
        store=False
    )

    @api.depends('building_ids.floor_ids')
    def _compute_floor_ids(self):
        for record in self:
            floors = self.env['floor.management'].search([
                ('building_id.community_id', '=', record.id)
            ])
            record.floor_ids = floors

    @api.depends('building_ids.floor_ids.flat_ids')
    def _compute_flat_ids(self):
        for record in self:
            flats = self.env['flat.management'].search([
                ('building_id.community_id', '=', record.id)
            ])
            record.flat_ids = flats



    # ----

    # Updates to community.py (add these to the existing Community model)

    parking_count = fields.Integer(string='Parking Slots',
                                   compute='_compute_parking_count',
                                   store=True)

    @api.depends('building_ids')  # Dependency can be adjusted if needed
    def _compute_parking_count(self):
        for record in self:
            slots = self.env['parking.slot'].search([('community_id', '=', record.id)])
            record.parking_count = len(slots)

    def action_view_parking_slots(self):
        """Open Parking Slots list for this community"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Parking Slots - {self.name}',
            'res_model': 'parking.slot',
            'view_mode': 'list,form,kanban',
            'domain': [('community_id', '=', self.id)],
            'context': {'default_community_id': self.id},
            'target': 'current',
        }

    festivalcount = fields.Integer(string="Festivals",
                                   compute="_compute_festivalcount",
                                   store=True)
    festivalids = fields.One2many('community.festival', 'community_id', string="Festivals")

    @api.depends('festivalids')
    def _compute_festivalcount(self):
        for record in self:
            record.festivalcount = len(record.festivalids)

    post_count = fields.Integer(
        string="Post Count",
        compute="_compute_post_count",
        store=True
    )

    def _compute_post_count(self):
        for community in self:
            community.post_count = self.env['community.post'].search_count([
                ('community_id', '=', community.id),
                ('active', '=', True)
            ])


class ResPartner(models.Model):
    _inherit = "res.partner"

    flat_id = fields.Many2one(
        'flat.management',
        string="Resident Flat",
        help="The flat where this person lives (for residents/tenants/owners)"
    )

    community_id = fields.Many2one(
        'community.management',
        string="Community",
        compute='_compute_community_id',
        store=True
    )

    @api.depends('flat_id')
    def _compute_community_id(self):
        for partner in self:
            if partner.flat_id:
                partner.community_id = partner.flat_id.building_id.community_id
            else:
                partner.community_id = False

    aadhar_number = fields.Char(string="Aadhar Number")
    last_notice_viewed = fields.Datetime(
        string="Last Notice Board Visit",
        default=fields.Datetime.now
    )

    family_member_ids = fields.One2many(
        'family.member',
        'tenant_id',
        string='Family Members'
    )

    pet_ids = fields.One2many(
        'pet.management',
        'tenant_id',
        string='Pets'
    )

    vehicle_ids = fields.One2many(
        'vehicle.management',
        'tenant_id',
        string='Vehicles'
    )

    occupant_type = fields.Selection(
        [
            ('owner', 'Owner'),
            ('tenant', 'Tenant'),
        ],
        string="Occupant Type"
    )

    def action_open_vehicle_details(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vehicle Details',
            'res_model': 'vehicle.management',
            'view_mode': 'list,form,kanban',
            'domain': [('tenant_id', '=', self.id)],
            'context': {'default_tenant_id': self.id},
        }

    def action_open_family_members(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Family Members',
            'res_model': 'family.member',
            'view_mode': 'list,form,kanban',
            'domain': [('tenant_id', '=', self.id)],
            'context': {'default_tenant_id': self.id}
        }

    def action_open_pet_details(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pet Details',
            'res_model': 'pet.management',
            'view_mode': 'list,form,kanban',
            'domain': [('tenant_id', '=', self.id)],
            'context': {'default_tenant_id': self.id},
        }

