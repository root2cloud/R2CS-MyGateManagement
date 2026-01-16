from odoo import models, fields

class VisitingHelpCategory(models.Model):
    _name = 'community.visiting.help.category'
    _description = 'Visiting Help Category'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)




class CommunityWeekDay(models.Model):
    _name = 'community.week.day'
    _description = 'Week Day'

    name = fields.Char(required=True)
    code = fields.Char(required=True)

class VisitingHelpEntry(models.Model):
    _name = 'community.visiting.help.entry'
    _description = 'Visiting Help Entry'
    _order = 'create_date desc'

    tenant_id = fields.Many2one(
        'res.partner',
        string="Tenant",
        default=lambda self: self.env.user.partner_id,
        readonly=True
    )

    category_id = fields.Many2one(
        'community.visiting.help.category',
        string="Visiting Help Category",
        required=True
    )

    entry_type = fields.Selection([
        ('once', 'Once'),
        ('frequent', 'Frequently')
    ], required=True, default='once')

    # =====================
    # ONCE ENTRY
    # =====================
    visit_date = fields.Date(string="Visit Date")
    start_time = fields.Float(string="Starting From")

    valid_for = fields.Selection([
        ('1', '1 Hour'),
        ('2', '2 Hours'),
        ('4', '4 Hours'),
        ('8', '8 Hours'),
        ('12', '12 Hours'),
        ('24', '24 Hours'),
    ], string="Valid For")

    # =====================
    # FREQUENT ENTRY
    # =====================
    day_ids = fields.Many2many(
        'community.week.day',
        string="Days of Week"
    )

    validity = fields.Selection([
        ('1w', '1 Week'),
        ('15d', '15 Days'),
        ('1m', '1 Month'),
        ('6m', '6 Months'),
    ], string="Validity")

    time_from = fields.Float(string="Time From")
    time_to = fields.Float(string="Time To")

    entries_per_day = fields.Selection([
        ('one', 'One Entry'),
        ('multiple', 'Multiple Entries'),
    ], string="Entries Per Day")

    company_name = fields.Char(string="Company Name")

    state = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired')
    ], default='active')


