# File: child_exit_permission.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class ChildExitPermission(models.Model):
    _name = 'child.exit.permission'
    _description = 'Child Exit Permission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # Basic Information
    name = fields.Char(
        string='Permission Name',
        compute='_compute_name',
        store=True
    )

    tenant_id = fields.Many2one(
        'res.partner',
        string='Parent/Tenant',
        required=True,
        tracking=True
    )

    flat_id = fields.Many2one(
        'flat.management',
        string='Flat',
        related='tenant_id.flat_id',
        store=True,
        tracking=True,

    )

    # Child Selection - Only children of the tenant
    child_id = fields.Many2one(
        'family.member',
        string='Child',
        required=True,
        domain="[('tenant_id', '=', tenant_id), ('member_type', '=', 'child')]",
        tracking=True
    )

    # Child's photo for easy identification
    child_photo = fields.Binary(
        string="Child's Photo",
        related='child_id.photo',
        store=True
    )

    # Child's age
    child_age = fields.Integer(
        string="Child's Age",
        related='child_id.age',
        store=True
    )

    # Permission Details
    purpose = fields.Text(
        string='Purpose/Reason',
        required=True,
        tracking=True
    )

    allowed_exit_time = fields.Datetime(
        string='Allowed Exit Time',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )

    duration_hours = fields.Selection([
        ('1', '1 Hour'),
        ('2', '2 Hours'),
        ('4', '4 Hours'),
        ('8', '8 Hours'),
        ('12', '12 Hours'),
        ('24', '24 Hours'),
        ('custom', 'Custom')
    ], string='Duration', default='2', required=True, tracking=True)

    custom_duration_hours = fields.Float(
        string='Custom Hours',
        tracking=True
    )

    valid_until = fields.Datetime(
        string='Valid Until',
        compute='_compute_valid_until',
        store=True,
        tracking=True
    )

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('used', 'Used'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)

    # Tracking
    exit_time = fields.Datetime(
        string='Actual Exit Time',
        tracking=True
    )

    return_time = fields.Datetime(
        string='Actual Return Time',
        tracking=True
    )

    security_guard_id = fields.Many2one(
        'res.users',
        string='Authorized By',
        tracking=True
    )

    # Simple access code (no QR)
    access_code = fields.Char(
        string='Access Code',
        copy=False,
        tracking=True,
        default=lambda self: self._generate_access_code()
    )

    # Quick reference fields
    is_active_now = fields.Boolean(
        string='Currently Active',
        compute='_compute_is_active_now',
        store=True
    )

    time_remaining = fields.Char(
        string='Time Remaining',
        compute='_compute_time_remaining'
    )

    # Computed fields
    @api.depends('child_id', 'allowed_exit_time')
    def _compute_name(self):
        for record in self:
            if record.child_id and record.allowed_exit_time:
                child_name = record.child_id.name
                exit_time = fields.Datetime.context_timestamp(
                    record,
                    fields.Datetime.from_string(record.allowed_exit_time)
                ).strftime('%d-%m-%Y %I:%M %p')
                record.name = f"Exit: {child_name} at {exit_time}"
            else:
                record.name = "New Child Exit Permission"

    @api.depends('allowed_exit_time', 'duration_hours', 'custom_duration_hours')
    def _compute_valid_until(self):
        for record in self:
            if record.allowed_exit_time:
                if record.duration_hours == 'custom':
                    hours = record.custom_duration_hours
                else:
                    hours = float(record.duration_hours)

                valid_until = fields.Datetime.from_string(record.allowed_exit_time) + \
                              timedelta(hours=hours)
                record.valid_until = valid_until
            else:
                record.valid_until = False

    @api.depends('state', 'valid_until')
    def _compute_is_active_now(self):
        """Check if permission is currently active"""
        now = fields.Datetime.now()
        for record in self:
            if record.state == 'active' and record.valid_until and record.valid_until > now:
                record.is_active_now = True
            else:
                record.is_active_now = False

    def _compute_time_remaining(self):
        """Calculate remaining time in human-readable format"""
        now = fields.Datetime.now()
        for record in self:
            if record.state == 'active' and record.valid_until and record.valid_until > now:
                remaining = record.valid_until - now
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)

                if hours > 0:
                    record.time_remaining = f"{hours}h {minutes}m"
                else:
                    record.time_remaining = f"{minutes}m"
            else:
                record.time_remaining = "Expired"

    # Constraints
    @api.constrains('duration_hours', 'custom_duration_hours')
    def _check_duration(self):
        for record in self:
            if record.duration_hours == 'custom' and record.custom_duration_hours <= 0:
                raise ValidationError(_('Custom duration must be greater than 0.'))

    @api.constrains('allowed_exit_time')
    def _check_future_time(self):
        for record in self:
            if record.allowed_exit_time < fields.Datetime.now():
                raise ValidationError(_('Allowed exit time must be in the future.'))

    # Methods
    def _generate_access_code(self):
        """Generate unique 6-digit access code"""
        import random
        return str(random.randint(100000, 999999))

    # Action Methods
    def action_activate(self):
        """Activate the permission"""
        for record in self:
            if record.state == 'draft':
                record.state = 'active'
                # Send notification
                record._send_notification('activated')

    def action_mark_exited(self):
        """Mark child as exited"""
        for record in self:
            if record.state == 'active':
                record.state = 'used'
                record.exit_time = fields.Datetime.now()
                record._send_notification('exited')

    def action_mark_returned(self):
        """Mark child as returned"""
        for record in self:
            if record.state == 'used':
                record.state = 'expired'
                record.return_time = fields.Datetime.now()
                record._send_notification('returned')

    def action_cancel(self):
        """Cancel the permission"""
        for record in self:
            if record.state in ['draft', 'active']:
                record.state = 'cancelled'
                record._send_notification('cancelled')

    def _send_notification(self, notification_type):
        """Send notification about permission status change"""
        # Basic notification - you can expand this with emails/SMS
        notification_map = {
            'activated': f"Exit permission activated for {self.child_id.name}",
            'exited': f"{self.child_id.name} has exited the premises",
            'returned': f"{self.child_id.name} has returned safely",
            'cancelled': f"Exit permission cancelled for {self.child_id.name}"
        }

        message = notification_map.get(notification_type, "Status updated")
        self.message_post(body=message)

    # Cron job to expire permissions
    def _cron_check_expired_permissions(self):
        """Check and expire permissions"""
        expired_permissions = self.search([
            ('state', '=', 'active'),
            ('valid_until', '<', fields.Datetime.now())
        ])

        for permission in expired_permissions:
            permission.state = 'expired'
            permission._send_notification('expired')
            _logger.info(f"Auto-expired permission: {permission.name}")

    # Quick action methods for dashboard
    @api.model
    def create_quick_permission(self, child_id, duration='2'):
        """Quick method to create permission from dashboard"""
        child = self.env['family.member'].browse(child_id)

        permission_vals = {
            'tenant_id': child.tenant_id.id,
            'child_id': child.id,
            'purpose': 'Quick exit permission',
            'allowed_exit_time': fields.Datetime.now(),
            'duration_hours': duration,
            'state': 'active'
        }

        permission = self.create(permission_vals)
        return {
            'access_code': permission.access_code,
            'child_name': child.name,
            'valid_until': permission.valid_until,
            'permission_id': permission.id
        }

    # Portal access control
    def _portal_can_access(self):
        """Check if current portal user can access this permission"""
        self.ensure_one()
        if self.env.user.has_group('base.group_portal'):
            return self.tenant_id == self.env.user.partner_id
        return True