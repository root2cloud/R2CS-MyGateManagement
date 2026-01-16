from odoo import models, fields, api


class Room(models.Model):
    _name = 'room.management'
    _description = 'Room'

    name = fields.Char(string='Room Name', compute='_compute_name', store=True)
    flat_id = fields.Many2one('flat.management', string='Flat', required=True, ondelete='cascade')
    room_type = fields.Selection([
        ('bedroom', 'Bedroom'),
        ('living_room', 'Living Room'),
        ('kitchen', 'Kitchen'),
        ('bathroom', 'Bathroom'),
        ('balcony', 'Balcony'),
        ('dining_room', 'Dining Room'),
        ('study_room', 'Study Room'),
        ('store_room', 'Store Room'),
        ('pooja_room', 'Pooja Room'),
        ('other', 'Other')
    ], string='Room Type', required=True)
    area = fields.Float(string='Area (sq.ft)')
    room_image = fields.Image(string='Room Image', max_width=200, max_height=200)

    @api.depends('room_type')
    def _compute_name(self):
        for record in self:
            if record.room_type:
                record.name = dict(record._fields['room_type'].selection).get(record.room_type)
            else:
                record.name = 'Room'
