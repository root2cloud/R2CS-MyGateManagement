from odoo import models, fields
from datetime import datetime

class PropertyNoticeBoard(models.Model):
    _name = 'property.notice.board'
    _description = 'Property Notice Board'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Inherit mail thread and activity mixin for chatter

    name = fields.Char(string="Title", required=True, tracking=True)
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
    target_group_ids = fields.Many2many('res.partner', string="Target Tenants", tracking=True)
    active = fields.Boolean(default=False, tracking=True)

    # def is_visible_for_user(self, user):
    #     today = fields.Date.today()
    #     if self.date_start and today < self.date_start:
    #         return False
    #     if self.date_end and today > self.date_end:
    #         return False
    #     return not self.target_group_ids or user.partner_id in self.target_group_ids
