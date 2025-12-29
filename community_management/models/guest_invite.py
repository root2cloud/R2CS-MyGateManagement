from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import random
import string
import urllib.parse


class GuestInvite(models.Model):
    _name = 'guest.invite'
    _description = 'Guest Invite'
    _order = 'create_date desc'

    resident_id = fields.Many2one('res.partner', string='Resident', required=True,
                                  default=lambda self: self.env.user.partner_id, ondelete='cascade')

    invite_type = fields.Selection([
        ('once', 'Once'),
        ('frequent', 'Frequently')
    ], string='Invite Type', default='once', required=True)

    # ONCE tab
    once_date = fields.Date(string='Date', default=fields.Date.context_today)
    once_start_time = fields.Float(string='Starting From', default=9.0)  # 9:00
    once_valid_hours = fields.Integer(string='Valid For (Hours)', default=8)

    # FREQUENT tab
    duration_type = fields.Selection([
        ('1w', '1 Week'),
        ('1m', '1 Month'),
        ('gt1m', '>1 Month'),
        ('custom', 'Custom')
    ], string='Allow entry for next', default='1m')
    freq_start_date = fields.Date(string='Start Date', default=fields.Date.context_today)
    freq_end_date = fields.Date(string='End Date')

    is_private = fields.Boolean(string='Make it Private')
    note = fields.Text(string='Note')

    guest_line_ids = fields.One2many('guest.invite.line', 'invite_id', string='Guests')

    # Consolidated validity window
    start_datetime = fields.Datetime(string='Start')
    end_datetime = fields.Datetime(string='End')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')

    otpcode = fields.Char(string='Entry Code / OTP', size=6, readonly=True, copy=False,
                          help='Unique 6-digit OTP for gate entry - ALWAYS GENERATED')

    @api.model
    def create(self, vals):
        """🚀 ALWAYS Generate unique OTP on record creation"""
        record = super(GuestInvite, self).create(vals)
        record.generate_unique_otp()  # ✅ GUARANTEED OTP GENERATION
        return record

    @api.model_create_multi
    def create_multi(self, vals_list):
        """Handle multi-create and generate OTPs"""
        records = super().create_multi(vals_list)
        for record in records:
            record.generate_unique_otp()  # ✅ EVERY record gets OTP
        return records

    def write(self, vals):
        """Regenerate OTP if explicitly cleared"""
        res = super(GuestInvite, self).write(vals)
        if 'otpcode' in vals and not vals['otpcode']:
            for record in self:
                record.generate_unique_otp()
        return res

    def generate_unique_otp(self):
        """🔥 Generate unique 6-digit OTP that NEVER exists"""
        self.ensure_one()
        while True:
            otp = ''.join(random.choices(string.digits, k=6))  # 100000-999999
            if not self.search([('otpcode', '=', otp)], limit=1):
                self.otpcode = otp
                break

    @api.onchange('duration_type', 'freq_start_date')
    def onchange_duration(self):
        """Auto-fill freq_end_date based on duration_type"""
        if not self.freq_start_date:
            return
        start = fields.Date.from_string(self.freq_start_date)
        if self.duration_type == '1w':
            self.freq_end_date = start + relativedelta(weeks=1)
        elif self.duration_type == '1m':
            self.freq_end_date = start + relativedelta(months=1)
        elif self.duration_type == 'gt1m':
            self.freq_end_date = start + relativedelta(months=3)

    def get_start_end_datetimes(self):
        """Return start_dt, end_dt based on invite_type"""
        self.ensure_one()
        if self.invite_type == 'once':
            date_obj = fields.Date.from_string(self.once_date)
            start_dt = datetime.combine(date_obj, fields.Datetime.to_datetime('1970-01-01 00:00:00').time())
            start_dt = start_dt + relativedelta(hours=self.once_start_time)
            end_dt = start_dt + relativedelta(hours=self.once_valid_hours or 8)
            return start_dt, end_dt
        else:
            start_date = fields.Date.from_string(self.freq_start_date)
            if self.freq_end_date:
                end_date = fields.Date.from_string(self.freq_end_date)
            else:
                if self.duration_type == '1w':
                    end_date = start_date + relativedelta(weeks=1)
                elif self.duration_type == '1m':
                    end_date = start_date + relativedelta(months=1)
                elif self.duration_type == 'gt1m':
                    end_date = start_date + relativedelta(months=3)
                else:
                    end_date = start_date
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())
            return start_dt, end_dt

    def action_compute_window(self):
        """✅ Fill dates + GUARANTEE OTP exists + Set active"""
        for rec in self:
            start_dt, end_dt = rec.get_start_end_datetimes()
            rec.start_datetime = start_dt
            rec.end_datetime = end_dt

            # 🚀 ALWAYS ENSURE OTP EXISTS
            if not rec.otpcode:
                rec.generate_unique_otp()

            if rec.state == 'draft':
                rec.state = 'active'

    @api.model
    def cron_expire_invites(self):
        """Auto-expire old invites"""
        expired = self.search([
            ('state', '=', 'active'),
            ('end_datetime', '<', fields.Datetime.now())
        ])
        expired.write({'state': 'expired'})

    def action_share_invite(self):
        """📱 Backend WhatsApp share - Bonus feature"""
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        portal_url = f"{base_url}/my/guest/invites/invite/{self.id}"

        guests = ", ".join([f"{line.guest_name} ({line.guest_mobile})" for line in self.guest_line_ids])
        message = f"""🔔 GATE ENTRY INVITE

🔑 OTP: {self.otpcode}
👤 Resident: {self.resident_id.name}
📅 Valid: {self.start_datetime.strftime('%d/%m %H:%M')} - {self.end_datetime.strftime('%d/%m %H:%M')}
👥 Guests: {guests or 'Not specified'}

🔗 Details: {portal_url}

✅ Show OTP at gate!"""

        whatsapp_url = f"https://web.whatsapp.com/send?text={urllib.parse.quote(message)}"
        return {
            'type': 'ir.actions.act_url',
            'url': whatsapp_url,
            'target': 'new',
        }


class GuestInviteLine(models.Model):
    _name = 'guest.invite.line'
    _description = 'Guest Invite Guest'

    invite_id = fields.Many2one('guest.invite', string='Invite', ondelete='cascade', required=True)
    guest_name = fields.Char(string='Guest Name', required=True)
    guest_mobile = fields.Char(string='Mobile', required=True)
