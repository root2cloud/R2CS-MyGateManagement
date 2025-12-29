# New file: parking.py
from odoo import models, fields, api

class ParkingSlot(models.Model):
    _name = 'parking.slot'
    _description = 'Parking Slot'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Slot Number', required=True, tracking=True)
    community_id = fields.Many2one('community.management', string='Community', required=True, tracking=True)
    building_id = fields.Many2one('building.management', string='Building',
                                  domain="[('community_id', '=', community_id)]", tracking=True)

    type = fields.Selection([
        ('covered', 'Covered'),
        ('open', 'Open'),
        ('reserved', 'Reserved')
    ], string='Type', default='open', required=True, tracking=True)
    status = fields.Selection([
        ('available', 'Available'),
        ('assigned', 'Assigned')
    ], string='Status', compute='_compute_status', store=True, tracking=True)
    flat_id = fields.Many2one('flat.management', string='Assigned Flat', tracking=True)
    description = fields.Text(string='Description')

    @api.depends('flat_id')
    def _compute_status(self):
        for record in self:
            record.status = 'assigned' if record.flat_id else 'available'

    @api.onchange('community_id')
    def _onchange_community_id(self):
        if self.community_id:
            self.building_id = False
        return {'domain': {'building_id': [('community_id', '=', self.community_id.id)]}}

    @api.constrains('flat_id')
    def _check_flat_assignment(self):
        for record in self:
            if record.flat_id and record.flat_id.building_id.community_id != record.community_id:
                raise ValidationError("The assigned flat must belong to the same community as the parking slot.")

