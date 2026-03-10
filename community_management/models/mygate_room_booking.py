from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MyGateRoom(models.Model):
    _name = 'mygate.room'
    _description = "Community Room"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Room Number/Name", required=True, tracking=True)
    room_type = fields.Selection([
        ('standard', 'Standard'),
        ('deluxe', 'Deluxe'),
        ('suite', 'Suite')
    ], string="Room Type", required=True, tracking=True)

    state = fields.Selection([
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Maintenance')
    ], string="Status", default='available', tracking=True)

    def action_set_available(self):
        """Manually set the room to Available."""
        self.write({'state': 'available'})

    def action_set_occupied(self):
        """Manually set the room to Occupied (Override)."""
        self.write({'state': 'occupied'})

    def action_set_maintenance(self):
        """Put the room into Maintenance mode so it cannot be booked."""
        self.write({'state': 'maintenance'})


class RoomBooking(models.Model):
    _name = 'mygate.room.booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Room Booking Request"

    name = fields.Char(string="Booking Reference", required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    member_id = fields.Many2one('res.partner', string="Member", required=True, domain=[('is_company', '=', False)])

    # Booking Details
    check_in = fields.Date(string="Check-in Date", required=True)
    check_out = fields.Date(string="Check-out Date", required=True)

    # NEW: Link to the specific room, filtering only available rooms
    room_id = fields.Many2one(
        'mygate.room',
        string="Allocated Room",
        domain="[('state', '=', 'available')]"
    )

    # 2. The Room Type field
    room_type = fields.Selection([
        ('standard', 'Standard'),
        ('deluxe', 'Deluxe'),
        ('suite', 'Suite')
    ], string="Room Type", required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('confirmed', 'Confirmed'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)



    # Policy & Terms
    terms_conditions = fields.Html(string="Terms & Conditions")
    cancellation_fee = fields.Float(string="Cancellation Charges", readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('mygate.room.booking') or _('New')
        return super(RoomBooking, self).create(vals)

    def action_checkout(self):
        """Marks the booking as complete and frees up the room."""
        for record in self:
            # Revert the room status back to available
            if record.room_id:
                record.room_id.state = 'available'

            # Update the booking state
            record.state = 'checked_out'



    @api.onchange('room_id')
    def _onchange_room_id(self):
        """Automatically fetch and set the room type when a room is selected."""
        if self.room_id:
            self.room_type = self.room_id.room_type

    def action_request(self):
        """Moves the booking from Draft to Requested."""
        # You can add validation here (e.g., ensure dates are in the future)
        self.state = 'requested'

    def action_confirm_booking(self):
        """Validates eligibility, allocates the room, and Confirms."""
        # (Keep your existing eligibility and room allocation logic here)
        if not self.room_id:
            raise ValidationError(_("Please allocate a room before confirming the booking."))
        if self.room_id.state != 'available':
            raise ValidationError(_("The selected room is no longer available."))

        self.room_id.state = 'occupied'
        self.state = 'confirmed'

    def action_cancel_booking(self):
        """Cancels the booking, applies fees, and frees up the room."""
        # (Keep your existing cancellation logic here)
        self.cancellation_fee = 500.0
        if self.room_id:
            self.room_id.state = 'available'
        self.state = 'cancelled'

    def action_draft(self):
        """Resets a cancelled booking back to draft."""
        self.state = 'draft'




# from odoo import models, fields, api, _
# from odoo.exceptions import ValidationError
#
#
# class RoomBooking(models.Model):
#     _name = 'mygate.room.booking'
#     _inherit = ['mail.thread', 'mail.activity.mixin']
#     _description = "Room Booking Request"
#
#     name = fields.Char(string="Booking Reference", required=True, copy=False, readonly=True,
#                        default=lambda self: _('New'))
#     member_id = fields.Many2one('res.partner', string="Member", required=True, domain=[('is_company', '=', False)])
#
#     # Booking Details
#     check_in = fields.Date(string="Check-in Date", required=True)
#     check_out = fields.Date(string="Check-out Date", required=True)
#     room_type = fields.Selection([('standard', 'Standard'), ('deluxe', 'Deluxe'), ('suite', 'Suite')], required=True)
#
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('requested', 'Requested'),
#         ('confirmed', 'Confirmed'),
#         ('cancelled', 'Cancelled')
#     ], default='draft', tracking=True)
#
#     # Policy & Terms
#     terms_conditions = fields.Html(string="Terms & Conditions")
#     cancellation_fee = fields.Float(string="Cancellation Charges", readonly=True)
#
#     @api.model
#     def create(self, vals):
#         if vals.get('name', _('New')) == _('New'):
#             vals['name'] = self.env['ir.sequence'].next_by_code('mygate.room.booking') or _('New')
#         return super(RoomBooking, self).create(vals)
#
#     def action_confirm_booking(self):
#         # Logic to check Annual Eligibility
#         # Example: Count existing 'confirmed' bookings for the member this year
#         current_year_bookings = self.search_count([
#             ('member_id', '=', self.member_id.id),
#             ('state', '=', 'confirmed'),
#             ('check_in', '>=', fields.Date.today().replace(month=1, day=1))
#         ])
#         if current_year_bookings >= 5:  # Assuming a limit of 5 per year
#             raise ValidationError(_("Member has reached their annual booking eligibility limit."))
#         self.state = 'confirmed'
#
#     def action_cancel_booking(self):
#         # Logic to apply charges based on policy
#         self.cancellation_fee = 500.0  # Example flat fee
#         self.state = 'cancelled'