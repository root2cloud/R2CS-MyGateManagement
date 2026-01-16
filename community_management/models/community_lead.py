from odoo import models, fields


class CommunityLead(models.Model):
    _name = "community.lead"
    _description = "Community Inquiry Lead"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Full Name", required=True, tracking=True)
    mobile = fields.Char(string="Mobile Number", required=True)
    email = fields.Char(string="Email")

    community_id = fields.Many2one(
        'community.management',
        string="Society / Community",
        required=True
    )

    customer_type = fields.Selection([
        ('rwa', 'RWA Member'),
        ('resident', 'Resident'),
        ('other', 'Other'),
    ], string="Customer Type", required=True)

    city = fields.Char(string="City")
