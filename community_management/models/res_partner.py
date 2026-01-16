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
    # ---

    last_notice_viewed = fields.Datetime(string="Last Notice Viewed", default=fields.Datetime.now)

    def get_unread_notice_count(self):
        """Get count of unread notices for this partner"""
        notice_model = self.env['property.notice.board']

        all_notices = notice_model.get_user_notices(self.env.user)
        last_viewed = self.last_notice_viewed or fields.Datetime.from_string('1900-01-01')

        unread_count = sum(1 for notice in all_notices if notice.create_date > last_viewed)
        return unread_count
