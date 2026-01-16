from odoo import models, fields, api


class Flat(models.Model):
    _name = 'flat.management'
    _description = 'Flat'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Flat Number/Name', required=True, tracking=True)
    building_id = fields.Many2one('building.management', string='Building', required=True, tracking=True)
    floor_id = fields.Many2one('floor.management', string='Floor',
                               domain="[('building_id', '=', building_id)]", tracking=True)

    flat_type_id = fields.Many2one('flat.type', string='Flat Type', required=True, tracking=True)

    area = fields.Float(string='Area (sq.ft.)', tracking=True)
    flat_image = fields.Image(string='Flat Image')
    room_ids = fields.One2many('room.management', 'flat_id', string='Rooms')

    # Status
    status = fields.Selection([
        ('available', 'Available'),
        ('occupied', 'Occupied')
    ], string='Status', default='available', required=True, tracking=True)

    # Pricing
    rent_price = fields.Monetary(string='Rent Price (Monthly)', currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.user.company_id.currency_id.id)

    # Current Lease Information (Auto-updated from active transaction)
    lease_owner_id = fields.Many2one('res.partner', string='Lease Owner',
                                     help="Person who holds lease rights (if any)", tracking=True)
    tenant_id = fields.Many2one('res.partner', string='Tenant',
                                help="Person who lives in the flat", tracking=True)

    # Dates
    lease_start_date = fields.Date(string='Lease Start Date', tracking=True)
    lease_end_date = fields.Date(string='Lease End Date', tracking=True)

    # Transactions
    transaction_ids = fields.One2many('flat.transaction', 'flat_id', string='Lease Transactions')
    transaction_count = fields.Integer(string='Transaction Count',
                                       compute='_compute_transaction_count'
                                       )


    parking_slot_ids = fields.One2many('parking.slot', 'flat_id', string='Parking Slots')
    parking_count = fields.Integer(string='Parking Count',
                                   compute='_compute_parking_count',
                                   store=True)

    @api.depends('parking_slot_ids')
    def _compute_parking_count(self):
        for record in self:
            record.parking_count = len(record.parking_slot_ids)
    #
    def action_view_parking_slots(self):
        """View parking slots assigned to this flat"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Parking Slots - {self.name}',
            'res_model': 'parking.slot',
            'view_mode': 'list,form,kanban',
            'domain': [('flat_id', '=', self.id)],
            'context': {
                'default_flat_id': self.id,
                'default_community_id': self.building_id.community_id.id,
                'default_building_id': self.building_id.id
            },
            'target': 'current',
        }

    @api.depends('transaction_ids')
    def _compute_transaction_count(self):
        for record in self:
            record.transaction_count = len(record.transaction_ids)

    #
    @api.onchange('building_id')
    def _onchange_building_id(self):
        if self.building_id:
            self.floor_id = False
        return {'domain': {'floor_id': [('building_id', '=', self.building_id.id)]}}

    def action_view_transactions(self):
        """View all lease transactions for this flat"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lease Transactions',
            'res_model': 'flat.transaction',
            'domain': [('flat_id', '=', self.id)],
            'view_mode': 'list,form',
            'target': 'current',
            'context': {
                'default_flat_id': self.id,
                'default_building_id': self.building_id.id,
                'default_floor_id': self.floor_id.id
            },
        }


from odoo import models, fields


class FlatType(models.Model):
    _name = 'flat.type'
    _description = 'Flat Type'

    name = fields.Char(string='Flat Type', required=True)
