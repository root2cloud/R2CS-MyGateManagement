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
    community_id = fields.Many2one('community.management', string='Community')

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
    flat_id = fields.Many2one('flat.management', string='Flat', required=True)
    community_id = fields.Many2one('community.management', string='Community', related='flat_id.community_id',
                                   store=True)

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


# =====================================================================
# INVOICE PAYMENT AUTOMATION
# Automatically updates the Amenity Booking when the Invoice is paid
# =====================================================================
class AccountMove(models.Model):
    _inherit = 'account.move'

    def _compute_payment_state(self):
        # 1. Let standard Odoo calculate the payment state first
        super(AccountMove, self)._compute_payment_state()

        # 2. Loop through the invoices being updated
        for move in self:
            # 3. If the invoice is marked as paid...
            if move.payment_state in ['paid', 'in_payment']:

                # 4. Find if there is an Amenity Booking linked to this exact invoice
                bookings = self.env['community.amenity.booking'].sudo().search([
                    ('invoice_id', '=', move.id)
                ])

                # 5. Automatically change the booking status to Approved and Paid!
                for booking in bookings:
                    if booking.state != 'approved' or booking.payment_status != 'paid':
                        booking.write({
                            'state': 'approved',
                            # Note: If your system uses 'confirmed' instead of 'approved', change this word!
                            'payment_status': 'paid'
                        })

    @api.model
    def cron_send_overdue_reminders(self):
        """ Automatically runs every day to send emails for overdue invoices """
        today = fields.Date.today()

        # 1. Find all posted customer invoices that are overdue and not fully paid
        overdue_invoices = self.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<', today)
        ])

        # 2. Get the email template we are about to create in XML
        template = self.env.ref('community_management.email_template_overdue_invoice', raise_if_not_found=False)

        if template:
            for invoice in overdue_invoices:
                # 3. Only send if the partner actually has an email address saved
                if invoice.partner_id.email:
                    # force_send=False puts it in the Odoo mail queue for safe delivery
                    template.send_mail(invoice.id, force_send=False)






