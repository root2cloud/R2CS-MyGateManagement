from odoo import models, fields, api


class Floor(models.Model):
    _name = 'floor.management'
    _description = 'Floor Management'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Floor Name', required=True)
    building_id = fields.Many2one('building.management', string='Building', required=True, ondelete='cascade')
    total_flats = fields.Integer(string='Total Flats on Floor')
    floor_plan = fields.Image(string='Floor Plan Image')
    description = fields.Text(string='Description')

    flat_ids = fields.One2many('flat.management', 'floor_id', string='Flats on this Floor')
    flat_count = fields.Integer(string='Flat Count',
                                compute='_compute_flat_count',
                                store=True)

    @api.depends('flat_ids')
    def _compute_flat_count(self):
        for record in self:
            record.flat_count = len(record.flat_ids)
