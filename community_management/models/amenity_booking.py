from odoo import models, fields, api
from datetime import date


class CommunityAmenity(models.Model):
    _name = 'community.amenity'
    _description = 'Community Amenities'

    name = fields.Char(string='Amenity Name', required=True)
    description = fields.Text(string='Description')
    amenity_type = fields.Selection([
        ('free', 'Free'),
        ('paid', 'Paid')
    ], string='Type', required=True, default='free')
    amount = fields.Float(string='Amount (₹)', default=0.0)
    max_booking_per_day = fields.Integer(string='Max Bookings Per Day', default=1)
    active = fields.Boolean(default=True)
    booking_ids = fields.One2many('community.amenity.booking', 'amenity_id', string='Bookings')

    @api.constrains('amenity_type', 'amount')
    def _check_paid_amenity_amount(self):
        for record in self:
            if record.amenity_type == 'paid' and record.amount <= 0:
                raise models.ValidationError('Paid amenity must have amount greater than 0')


class CommunityAmenityBooking(models.Model):
    _name = 'community.amenity.booking'
    _description = 'Amenity Booking'

    amenity_id = fields.Many2one('community.amenity', string='Amenity', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='User', required=True, ondelete='cascade')
    booking_date = fields.Date(string='Booking Date', required=True)
    remarks = fields.Text(string='Remarks')
    attachment = fields.Binary(string='Attachment')
    attachment_filename = fields.Char(string='Filename')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    amount = fields.Float(string='Amount (₹)', compute='_compute_amount', store=True)
    payment_status = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
        ('partial', 'Partial'),
        ('N/A', 'N/A')
    ], string='Payment Status', default='N/A', tracking=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='pending', tracking=True)

    @api.depends('amenity_id')
    def _compute_amount(self):
        for record in self:
            if record.amenity_id.amenity_type == 'paid':
                record.amount = record.amenity_id.amount
            else:
                record.amount = 0.0

    @api.constrains('booking_date')
    def _check_booking_date(self):
        for record in self:
            if record.booking_date < date.today():
                raise models.ValidationError('Booking date cannot be in the past')

    @api.constrains('amenity_id', 'booking_date')
    def _check_daily_limit(self):
        for record in self:
            bookings = self.search([
                ('amenity_id', '=', record.amenity_id.id),
                ('booking_date', '=', record.booking_date),
                ('state', '!=', 'cancelled'),
                ('id', '!=', record.id)
            ])
            if len(bookings) >= record.amenity_id.max_booking_per_day:
                raise models.ValidationError(
                    f"Maximum {record.amenity_id.max_booking_per_day} bookings allowed for {record.booking_date}"
                )

    def create_invoice(self):
        """Create invoice for paid amenity booking"""
        if self.amenity_id.amenity_type != 'paid':
            return

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'ref': f'Amenity Booking - {self.amenity_id.name} - {self.booking_date}',
            'invoice_line_ids': [(0, 0, {
                'name': f'{self.amenity_id.name} - Booking on {self.booking_date}',
                'quantity': 1,
                'price_unit': self.amenity_id.amount,
            })]
        }

        invoice = self.env['account.move'].sudo().create(invoice_vals)
        self.invoice_id = invoice.id
        self.payment_status = 'unpaid'

    def is_payment_complete(self):
        """Check if invoice is paid and update payment status"""
        if self.invoice_id:
            if self.invoice_id.payment_state == 'paid':
                self.payment_status = 'paid'
            elif self.invoice_id.payment_state == 'partial':
                self.payment_status = 'partial'
            else:
                self.payment_status = 'unpaid'