# models/daily_slot.py
from odoo import models, fields, api


# models/daily_slot.py (add booking fields + method)
class DailySlot(models.Model):
    _name = 'res.partner.daily.slot'
    _description = 'Daily Slots'

    partner_id = fields.Many2one('res.partner', string='Contact', required=True, ondelete='cascade')
    start_time = fields.Float(string='Start Time', required=True)
    end_time = fields.Float(string='End Time', required=True)
    notes = fields.Text(string='Notes')
    is_available = fields.Boolean(string='Available', default=True)

    # BOOKING FIELDS
    booked_by = fields.Many2one('res.partner', string='Booked By', domain=[('category_custom_id', '=', False)])
    booking_date = fields.Datetime(string='Booked Date')
    booking_notes = fields.Text(string='Booking Notes')

    def action_book_slot(self, user_id):
        """Book this slot for user"""
        self.write({
            'is_available': False,
            'booked_by': user_id,
            'booking_date': fields.Datetime.now(),
        })
