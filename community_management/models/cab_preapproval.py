# models/cab_preapproval.py

from odoo import models, fields, api
from datetime import datetime
from dateutil.relativedelta import relativedelta


class CabPreapproval(models.Model):
    _name = 'cab.preapproval'
    _description = 'Cab Pre-Approval'
    _order = 'create_date desc'

    resident_id = fields.Many2one(
        'res.partner',
        string='Resident',
        required=True,
        default=lambda self: self.env.user.partner_id,
        ondelete='cascade',
    )

    mode = fields.Selection(
        [('once', 'Once'), ('frequent', 'Frequently')],
        string='Mode',
        required=True,
        default='once',
    )

    # ONCE
    once_date = fields.Date(
        string='Date',
        default=fields.Date.context_today,
    )
    once_valid_hours = fields.Integer(
        string='Valid For (Hours)',
        default=1,
    )
    vehicle_last4 = fields.Char(
        string='Last 4 digits of vehicle no.',
        size=4,
    )

    # FREQUENT
    freq_days = fields.Selection(
        [
            ('all', 'All days of Week'),
            ('weekdays', 'Weekdays'),
            # ('custom', 'Custom'),
        ],
        string='Days of Week',
        default='all',
    )
    freq_validity = fields.Selection(
        [
            ('1m', 'For 1 month'),
            ('3m', 'For 3 months'),
            ('6m', 'For 6 months'),
            ('12m', 'For 12 months'),
        ],
        string='Validity',
        default='6m',
    )
    freq_time_from = fields.Float(string='From Time', default=0.0)       # 0:00
    freq_time_to = fields.Float(string='To Time', default=23.9833)       # 23:59
    entries_per_day = fields.Selection(
        [('one', 'One Entry'), ('multi', 'Multiple Entries')],
        string='Entries Per Day',
        default='one',
    )
    company_name = fields.Char(string='Company Name')

    # COMPUTED WINDOW
    start_datetime = fields.Datetime(string='Start')
    end_datetime = fields.Datetime(string='End')

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('expired', 'Expired'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
    )

    def _compute_range(self):
        """Internal helper: compute start/end from once/frequent configuration."""
        self.ensure_one()
        if self.mode == 'once':
            date_obj = fields.Date.from_string(self.once_date)
            start_dt = datetime.combine(date_obj, datetime.min.time())
            start_dt = start_dt + relativedelta(hours=0)  # now → next N hours
            end_dt = start_dt + relativedelta(hours=self.once_valid_hours or 1)
            return start_dt, end_dt
        else:
            today = fields.Date.context_today(self)
            start_date = fields.Date.from_string(today)
            if self.freq_validity == '1m':
                end_date = start_date + relativedelta(months=1)
            elif self.freq_validity == '3m':
                end_date = start_date + relativedelta(months=3)
            elif self.freq_validity == '6m':
                end_date = start_date + relativedelta(months=6)
            else:
                end_date = start_date + relativedelta(months=12)

            start_dt = datetime.combine(start_date, datetime.min.time()) + \
                relativedelta(hours=self.freq_time_from)
            end_dt = datetime.combine(end_date, datetime.min.time()) + \
                relativedelta(hours=self.freq_time_to)
            return start_dt, end_dt

    def action_activate(self):
        """Compute validity window and activate."""
        for rec in self:
            start_dt, end_dt = rec._compute_range()
            rec.write({
                'start_datetime': start_dt,
                'end_datetime': end_dt,
                'state': 'active',
            })

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    @api.model
    def cron_expire_cab_preapprovals(self):
        active = self.search([
            ('state', '=', 'active'),
            ('end_datetime', '<', fields.Datetime.now())
        ])
        active.write({'state': 'expired'})
