from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class Amenity(models.Model):
    _name = 'amenity.amenity'
    _description = 'Community Amenity'

    name = fields.Char(string='Amenity Name', required=True)
    description = fields.Text(string='Description')
    image = fields.Image(string='Image')
    slot_ids = fields.One2many('amenity.time.slot', 'amenity_id', string='Time Slots')
    active = fields.Boolean(default=True)

class AmenityTimeSlot(models.Model):
    _name = 'amenity.time.slot'
    _description = 'Amenity Time Slot'
    _order = 'start_time'

    amenity_id = fields.Many2one('amenity.amenity', string='Amenity', required=True, ondelete='cascade')
    start_time = fields.Float(string='Start Time', required=True)
    end_time = fields.Float(string='End Time', required=True)
    display_name = fields.Char(string='Display Name',
                               compute='_compute_display_name',
                               store=True)

    @api.depends('start_time', 'end_time')
    def _compute_display_name(self):
        for slot in self:
            start_hour, start_minute = divmod(int(slot.start_time * 60), 60)
            end_hour, end_minute = divmod(int(slot.end_time * 60), 60)
            slot.display_name = f"{start_hour:02d}:{start_minute:02d} - {end_hour:02d}:{end_minute:02d}"

class AmenityBooking(models.Model):
    _name = 'amenity.booking'
    _description = 'Amenity Booking'
    _order = 'booking_date desc, time_slot_id'

    amenity_id = fields.Many2one('amenity.amenity', string='Amenity', required=True, ondelete='cascade')
    time_slot_id = fields.Many2one('amenity.time.slot', string='Time Slot', required=True, ondelete='cascade')
    booking_date = fields.Date(string='Booking Date', required=True)
    tenant_id = fields.Many2one('res.partner', string='Booked By', required=True)
    state = fields.Selection([
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='confirmed', required=True)

    payment_option = fields.Selection([
        ('pay_now', 'Pay Now'),
        ('pay_later', 'Pay Later')
    ], string="Payment Option", default="pay_later")

    _sql_constraints = [
        ('unique_booking', 'unique(amenity_id, time_slot_id, booking_date)',
         'This time slot has already been booked for the selected date.')
    ]

    @api.constrains('booking_date')
    def _check_booking_date(self):
        for record in self:
            if record.booking_date < fields.Date.today():
                raise ValidationError(_("You cannot book an amenity for a past date."))

