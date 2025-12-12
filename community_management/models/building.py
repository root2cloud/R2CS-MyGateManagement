from odoo import models, fields

class Building(models.Model):
    _name = 'building.management'
    _description = 'Building'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Building Name', required=True)
    community_id = fields.Many2one('community.management', string='Community', required=True)
    total_floors = fields.Integer(string='Total Floors')
    building_image = fields.Image(string='Building Image')
    floor_ids = fields.One2many('floor.management', 'building_id', string='Floors')
