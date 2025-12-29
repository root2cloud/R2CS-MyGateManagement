from datetime import datetime, time, timedelta

from odoo import api, fields, models


class DeliveryPass(models.Model):
    _name = 'community.delivery.pass'
    _description = 'Delivery Pre‑Approval'

    MODE_SELECTION = [
        ('once', 'Once'),
        ('frequent', 'Frequently'),
    ]

    STATE_SELECTION = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]

    resident_id = fields.Many2one(
        'res.partner',
        string='Resident',
        required=True,
    )

    mode = fields.Selection(
        MODE_SELECTION,
        string='Mode',
        default='once',
        required=True,
    )

    is_surprise = fields.Boolean(string='Surprise Delivery')
    allow_leave_at_gate = fields.Boolean(string='Leave at Gate', default=True)

    # ONCE
    once_date = fields.Date(string='Date')
    once_start_time = fields.Float(string='Start Time')  # 22.5 => 10:30 pm
    once_valid_hours = fields.Selection(
        [
            ('1', '1 Hour'),
            ('2', '2 Hours'),
            ('4', '4 Hours'),
            ('8', '8 Hours'),
            ('12', '12 Hours'),
            ('24', '24 Hours'),
        ],
        string='Valid For (Hrs)',
        default='1',
    )

    # FREQUENT
    freq_days = fields.Char(
        string='Days Of Week'
    )  # e.g. "all", "mon,wed,fri"

    freq_time_from = fields.Float(string='From Time')
    freq_time_to = fields.Float(string='To Time')

    freq_validity = fields.Selection(
        [
            ('1w', '1 Week'),
            ('15d', '15 Days'),
            ('1m', '1 Month'),
            ('6m', '6 Months'),
        ],
        string='Validity',
        default='6m',
    )
    freq_valid_till = fields.Date(string='Valid Till', readonly=True)

    entries_per_day = fields.Selection(
        [('one', 'One Entry'), ('multi', 'Multiple Entries')],
        string='Entries Per Day',
        default='one',
    )

    company_name = fields.Char(string='Company Name')

    start_datetime = fields.Datetime(
        string='From',
        compute='_compute_window',
        store=True,
    )
    end_datetime = fields.Datetime(
        string='To',
        compute='_compute_window',
        store=True,
    )

    state = fields.Selection(
        STATE_SELECTION,
        string='Status',
        default='active',
    )

    @api.depends(
        'mode',
        'once_date',
        'once_start_time',
        'once_valid_hours',
        'freq_time_from',
        'freq_time_to',
        'freq_valid_till',
        'freq_validity',
    )
    def _compute_window(self):
        for rec in self:
            # ONCE
            if rec.mode == 'once' and rec.once_date and rec.once_start_time:
                base_dt = datetime.combine(rec.once_date, time(0, 0, 0))
                dt = base_dt + timedelta(hours=rec.once_start_time)
                rec.start_datetime = dt

                hours = int(rec.once_valid_hours or '1')
                rec.end_datetime = dt + timedelta(hours=hours)

            # FREQUENT
            elif rec.mode == 'frequent':
                today = fields.Date.today()
                if rec.freq_validity == '1w':
                    rec.freq_valid_till = today + timedelta(days=7)
                elif rec.freq_validity == '15d':
                    rec.freq_valid_till = today + timedelta(days=15)
                elif rec.freq_validity == '1m':
                    rec.freq_valid_till = today + timedelta(days=30)
                elif rec.freq_validity == '6m':
                    rec.freq_valid_till = today + timedelta(days=180)
                else:
                    rec.freq_valid_till = False

                if rec.freq_valid_till:
                    now_dt = fields.Datetime.now()
                    rec.start_datetime = now_dt
                    rec.end_datetime = datetime.combine(
                        rec.freq_valid_till, time(23, 59, 0)
                    )
                else:
                    rec.start_datetime = False
                    rec.end_datetime = False
            else:
                rec.start_datetime = False
                rec.end_datetime = False

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
