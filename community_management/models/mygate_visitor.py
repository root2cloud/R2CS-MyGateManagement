from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class MyGateVisitor(models.Model):
    _name = 'mygate.visitor'
    _description = 'MyGate Visitor Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # Basic Information
    name = fields.Char(string='Visitor Name', required=True, tracking=True)
    mobile = fields.Char(string='Mobile Number', required=True, tracking=True)
    company = fields.Char(string='Company Name', tracking=True)

    # Visitor Details
    visitor_type = fields.Selection([
        ('guest', 'Guest'),
        ('delivery', 'Delivery'),
        ('service', 'Service Provider'),
        ('cab', 'Cab/Taxi'),
        ('other', 'Other')
    ], string='Visitor Type', default='guest', required=True, tracking=True)

    purpose = fields.Text(string='Purpose of Visit', tracking=True)
    visitor_count = fields.Integer(string='Number of Visitors', default=1, tracking=True)

    # Vehicle Information
    vehicle_number = fields.Char(string='Vehicle Number', tracking=True)

    # Flat and Tenant Information
    flat_id = fields.Many2one(
        'flat.management',
        string='Flat Number',
        required=True,
        domain="[('status', '=', 'occupied')]",
        tracking=True
    )

    tenant_id = fields.Many2one(
        'res.partner',
        string='Tenant',
        compute='_compute_tenant_id',
        store=True,
        tracking=True
    )

    building_id = fields.Many2one(
        'building.management',
        string='Building',
        related='flat_id.building_id',
        store=True,
        tracking=True
    )

    community_id = fields.Many2one(
        'community.management',
        string='Community',
        related='building_id.community_id',
        store=True,
        tracking=True
    )

    # Status and Approval
    state = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Visit Completed')
    ], string='Status', default='pending', required=True, tracking=True)

    approval_date = fields.Datetime(string='Approval Date', tracking=True)
    rejection_date = fields.Datetime(string='Rejection Date', tracking=True)
    completion_date = fields.Datetime(string='Completion Date', tracking=True)

    # Time Management
    requested_date = fields.Datetime(
        string='Requested Date & Time',
        default=fields.Datetime.now,
        required=True,
        tracking=True
    )

    expected_arrival = fields.Datetime(
        string='Expected Arrival',
        required=True,
        tracking=True
    )

    actual_arrival = fields.Datetime(string='Actual Arrival', tracking=True)
    actual_departure = fields.Datetime(string='Actual Departure', tracking=True)

    # Duration
    expected_duration = fields.Float(
        string='Expected Duration (hours)',
        default=1.0,
        tracking=True
    )

    # Approval Information
    approved_by_id = fields.Many2one(
        'res.users',
        string='Approved By',
        tracking=True
    )

    rejected_by_id = fields.Many2one(
        'res.users',
        string='Rejected By',
        tracking=True
    )

    # OTP/PIN for gate access
    access_code = fields.Char(
        string='Access Code',
        copy=False,
        tracking=True
    )

    validity_duration = fields.Integer(
        string='Validity (minutes)',
        default=60,
        tracking=True
    )

    valid_until = fields.Datetime(string='Valid Until', tracking=True)

    # Security Information
    security_notes = fields.Text(string='Security Notes')
    gate_number = fields.Char(string='Gate Number')
    security_guard_id = fields.Many2one(
        'res.users',
        string='Security Guard',
        tracking=True
    )

    # QR Code
    qr_code = fields.Binary(string='QR Code', attachment=True)
    qr_code_image = fields.Char(string='QR Code URL', compute='_compute_qr_code_image')

    # Portal Access
    portal_user_id = fields.Many2one(
        'res.users',
        string='Portal User',
        compute='_compute_portal_user_id',
        store=True
    )

    portal_notification_sent = fields.Boolean(
        string='Portal Notification Sent',
        default=False,
        tracking=True
    )

    # History
    approval_history = fields.Text(string='Approval History', tracking=True)

    visitor_image = fields.Binary(
        string='Visitor Photo',
        attachment=True,

    )

    visitor_image_filename = fields.Char(string='Photo Filename')

    # Computed Fields
    @api.depends('flat_id', 'flat_id.tenant_id')
    def _compute_tenant_id(self):
        for record in self:
            record.tenant_id = record.flat_id.tenant_id if record.flat_id else False

    @api.depends('tenant_id', 'tenant_id.user_ids')
    def _compute_portal_user_id(self):
        for record in self:
            if record.tenant_id and record.tenant_id.user_ids:
                # Find the portal user
                portal_user = record.tenant_id.user_ids.filtered(
                    lambda u: u.has_group('base.group_portal')
                )
                record.portal_user_id = portal_user[0] if portal_user else False
            else:
                record.portal_user_id = False

    def _compute_qr_code_image(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            if record.access_code:
                record.qr_code_image = f"{base_url}/mygate/qr/{record.access_code}"
            else:
                record.qr_code_image = False

    # Constraints and Validations
    @api.constrains('mobile')
    def _check_mobile(self):
        for record in self:
            if record.mobile and not record.mobile.isdigit():
                raise ValidationError(_("Mobile number should contain only digits."))



    def action_confirm_request(self):
        """Confirm the visitor request and send notification to tenant"""
        for record in self:
            # Generate access code
            import random
            import string
            access_code = ''.join(random.choices(string.digits, k=6))
            record.access_code = access_code

            # Calculate validity
            if record.expected_arrival:
                valid_until = fields.Datetime.from_string(record.expected_arrival) + timedelta(
                    minutes=record.validity_duration
                )
                record.valid_until = valid_until

            # Generate QR code immediately (ADD THIS LINE)
            record._generate_qr_code()

            # Send notification to tenant
            record._send_portal_notification()

            # Create activity for tenant
            record._create_approval_activity()


    def _send_portal_notification(self):
        """Send notification to tenant's portal"""
        for record in self:
            if record.portal_user_id:
                try:
                    # Send email notification
                    template = self.env.ref('community_management.email_template_visitor_request')
                    template.send_mail(record.id, force_send=True)

                    # Create portal message
                    record.message_post(
                        body=f"Visitor request for {record.name} has been sent for approval.",
                        partner_ids=record.tenant_id.ids,
                        subtype_xmlid='mail.mt_comment'
                    )

                    record.portal_notification_sent = True
                except Exception as e:
                    _logger.error(f"Failed to send portal notification: {e}")

    def _create_approval_activity(self):
        """Create activity for tenant to approve/reject"""
        for record in self:
            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': f'Approve Visitor: {record.name}',
                'note': f'Please approve or reject visitor request for {record.name}',
                'user_id': record.portal_user_id.id if record.portal_user_id else False,
                'res_id': record.id,
                'res_model_id': self.env['ir.model']._get_id('mygate.visitor'),
                'date_deadline': fields.Datetime.from_string(record.expected_arrival)
            })

    def get_portal_url(self):
        """Get the portal URL for this visitor"""
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/my/visitors/{self.id}"

    def action_approve(self):
        """Approve the visitor request from portal"""
        for record in self:
            # if record.state != 'pending':
            #     raise UserError(_("Only pending requests can be approved."))

            record.state = 'approved'
            record.approval_date = fields.Datetime.now()
            record.approved_by_id = self.env.user.id

            # Generate QR code
            record._generate_qr_code()

            # Send approval notification
            record._send_approval_notification()

            # Mark activity as done
            activities = self.env['mail.activity'].search([
                ('res_id', '=', record.id),
                ('res_model', '=', 'mygate.visitor'),
                ('user_id', '=', self.env.user.id)
            ])
            if activities:
                activities.action_feedback(feedback=f"Visitor {record.name} approved.")

    def action_reject(self):
        """Reject the visitor request from portal"""
        for record in self:
            if record.state != 'pending':
                raise UserError(_("Only pending requests can be rejected."))

            record.state = 'rejected'
            record.rejection_date = fields.Datetime.now()
            record.rejected_by_id = self.env.user.id

            # Send rejection notification
            record._send_rejection_notification()

            # Mark activity as done
            activities = self.env['mail.activity'].search([
                ('res_id', '=', record.id),
                ('res_model', '=', 'mygate.visitor'),
                ('user_id', '=', self.env.user.id)
            ])
            if activities:
                activities.action_feedback(feedback=f"Visitor {record.name} rejected.")

    def action_mark_arrived(self):
        """Mark visitor as arrived"""
        for record in self:
            # if record.state != 'approved':
            #     raise UserError(_("Only approved visitors can be marked as arrived."))

            record.actual_arrival = fields.Datetime.now()
            record.state = 'completed'
            record.completion_date = fields.Datetime.now()

    def action_cancel(self):
        """Cancel the visitor request"""
        for record in self:
            record.state = 'cancelled'

    def _generate_qr_code(self):
        """Generate QR code for visitor access"""
        try:
            import qrcode
            from io import BytesIO
            import base64

            # Create QR code data
            qr_data = f"""
            Visitor: {self.name}
            Flat: {self.flat_id.name if self.flat_id else ''}
            Access Code: {self.access_code}
            Valid Until: {self.valid_until}
            Purpose: {self.purpose}
            """

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Save to binary field
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            self.qr_code = base64.b64encode(buffered.getvalue())

        except ImportError:
            _logger.warning("QRCode library not installed. Skipping QR code generation.")
        except Exception as e:
            _logger.error(f"Error generating QR code: {e}")

    def _send_approval_notification(self):
        """Send approval notification"""
        try:
            template = self.env.ref('community_management.email_template_visitor_approved')
            template.send_mail(self.id, force_send=True)
        except Exception as e:
            _logger.error(f"Failed to send approval notification: {e}")

    def _send_rejection_notification(self):
        """Send rejection notification"""
        try:
            template = self.env.ref('community_management.email_template_visitor_rejected')
            template.send_mail(self.id, force_send=True)
        except Exception as e:
            _logger.error(f"Failed to send rejection notification: {e}")

    # Cron Jobs
    def _cron_check_expired_visitors(self):
        """Check and expire old visitor requests"""
        expired_visitors = self.search([
            ('state', 'in', ['approved', 'pending']),
            ('valid_until', '<', fields.Datetime.now())
        ])

        for visitor in expired_visitors:
            if visitor.state == 'approved':
                visitor.state = 'completed'
                visitor.completion_date = fields.Datetime.now()
            elif visitor.state == 'pending':
                visitor.state = 'cancelled'

    def _cron_send_reminders(self):
        """Send reminders for upcoming visitors"""
        reminder_time = fields.Datetime.now() + timedelta(hours=1)
        upcoming_visitors = self.search([
            ('state', '=', 'approved'),
            ('expected_arrival', '<=', reminder_time),
            ('expected_arrival', '>', fields.Datetime.now()),
            ('actual_arrival', '=', False)
        ])

        for visitor in upcoming_visitors:
            try:
                template = self.env.ref('community_management.email_template_visitor_reminder')
                template.send_mail(visitor.id, force_send=False)
            except Exception as e:
                _logger.error(f"Failed to send reminder for visitor {visitor.id}: {e}")

