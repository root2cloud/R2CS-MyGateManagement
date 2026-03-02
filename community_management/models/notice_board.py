from odoo import models, fields, api


class PropertyNoticeBoard(models.Model):
    _name = 'property.notice.board'
    _description = 'Property Notice Board'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Title", required=True, tracking=True)

    community_id = fields.Many2one(
        'community.management',
        string="Community",
        tracking=True,
        help="Select a community to filter the target flats."
    )

    notice_type = fields.Selection([
        ('society', 'Society'),
        ('event', 'Event'),
        ('emergency', 'Emergency'),
        ('promotion', 'Promotion'),
    ], string="Type", required=True, tracking=True)

    description = fields.Html(string="Description")
    image = fields.Binary(string="Image")
    date_start = fields.Datetime(string="Start Date", tracking=True)
    date_end = fields.Datetime(string="End Date", tracking=True)

    # THIS IS THE FIX: Target flats instead of tenants
    target_flat_ids = fields.Many2many(
        'flat.management',
        string="Target Flats",
        tracking=True,
        help="Select specific flats. Leave empty to notify ALL flats in the community."
    )

    # Checkbox to make notice visible (Make sure to check this in the backend!)
    active = fields.Boolean(string="Active", default=True, tracking=True)

    @api.onchange('community_id')
    def _onchange_community_id(self):
        """Clear target flats if the community is changed to avoid mismatches"""
        if self.community_id:
            self.target_flat_ids = False

# from odoo import models, fields
# from datetime import datetime
#
# class PropertyNoticeBoard(models.Model):
#     _name = 'property.notice.board'
#     _description = 'Property Notice Board'
#     _inherit = ['mail.thread', 'mail.activity.mixin']  # Inherit mail thread and activity mixin for chatter
#
#     name = fields.Char(string="Title", required=True, tracking=True)
#     notice_type = fields.Selection([
#         ('society', 'Society'),
#         ('event', 'Event'),
#         ('emergency', 'Emergency'),
#         ('promotion', 'Promotion'),
#     ], string="Type", required=True, tracking=True)
#     description = fields.Html(string="Description")
#     image = fields.Binary(string="Image")
#     date_start = fields.Datetime(string="Start Date", tracking=True)
#     date_end = fields.Datetime(string="End Date", tracking=True)
#     target_group_ids = fields.Many2many('res.partner', string="Target Tenants", tracking=True)
#     active = fields.Boolean(default=False, tracking=True)
#
#     # def is_visible_for_user(self, user):
#     #     today = fields.Date.today()
#     #     if self.date_start and today < self.date_start:
#     #         return False
#     #     if self.date_end and today > self.date_end:
#     #         return False
#     #     return not self.target_group_ids or user.partner_id in self.target_group_ids
