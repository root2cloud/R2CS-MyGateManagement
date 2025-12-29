# models/res_partner_category.py
from odoo import models, fields

class ResPartnerCategoryCustom(models.Model):
    _name = 'res.partner.category.custom'
    _description = 'Contact Category'

    name = fields.Char(string='Category', required=True)
    active = fields.Boolean(default=True)

# models/res_partner_inherit.py

class ResPartner(models.Model):
    _inherit = 'res.partner'

    category_custom_id = fields.Many2one(
        'res.partner.category.custom',
        string='Category',
        ondelete='set null',  # keep partner if category deleted
    )
    daily_slot_ids = fields.One2many(
        'res.partner.daily.slot',
        'partner_id',
        string='Daily Slots'
    )
    is_security_guard = fields.Boolean(
        string='Security Guard',
        default=False
    )

    community_role = fields.Selection([
        ('', ''),  # Empty option - No role
        ('president', 'President'),
        ('secretary', 'Secretary'),
        ('treasurer', 'Treasurer'),
        ('committee_member', 'Committee Member'),
        ('resident_representative', 'Resident Representative'),
    ], string='Community Role', default=False)
