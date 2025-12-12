from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime
import base64


class FlatTransaction(models.Model):
    _name = 'flat.transaction'
    _description = 'Flat Lease Transaction'
    _rec_name = 'flat_id'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # Property Selection
    building_id = fields.Many2one('building.management', string='Building', required=True, tracking=True)
    floor_id = fields.Many2one('floor.management', string='Floor',
                               domain="[('building_id', '=', building_id)]", required=True, tracking=True)
    flat_id = fields.Many2one('flat.management', string='Flat',
                              domain="[('floor_id', '=', floor_id), ('building_id', '=', building_id)]",
                              required=True, tracking=True)

    # Lease Parties
    lease_owner_id = fields.Many2one('res.partner', string='Lease Owner (Optional)',
                                     help="Person who holds the lease rights. Tenant will still pay the rent.")
    tenant_id = fields.Many2one('res.partner', string='Tenant', required=True,
                                help="Person who lives in the flat and pays rent")

    # Computed field for invoice recipient - ALWAYS Tenant
    invoice_partner_id = fields.Many2one('res.partner', string='Invoice To',
                                         compute='_compute_invoice_partner',
                                         store=True,
                                         help="Always Tenant (who pays the rent)")

    # Lease Details
    rent_price = fields.Monetary(string='Monthly Rent', currency_field='currency_id', required=True)
    security_deposit = fields.Monetary(string='Security Deposit', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.user.company_id.currency_id.id)

    lease_start_date = fields.Date(string='Lease Start Date', required=True, tracking=True)
    lease_end_date = fields.Date(string='Lease End Date', required=True, tracking=True)
    lease_duration_months = fields.Integer(string='Duration (Months)',
                                           compute='_compute_lease_duration',
                                           store=True)

    # Agreement
    agreement_date = fields.Date(string='Agreement Date', default=fields.Date.today)
    agreement_document = fields.Binary(string='Agreement Document')
    agreement_filename = fields.Char(string='Agreement Filename')

    # Status
    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Active'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)

    notes = fields.Text(string='Additional Terms & Conditions')

    # Invoices
    invoice_ids = fields.One2many('account.move', 'transaction_id', string='Invoices')
    invoice_count = fields.Integer(string='Invoice Count', compute='_compute_invoice_count')
    invoiced_months = fields.Text(string='Invoiced Months')
    security_deposit_invoiced = fields.Boolean(string='Security Deposit Invoiced', default=False)

    def action_send_lease_agreement_email(self):
        """Send lease agreement via email to tenant"""
        self.ensure_one()

        if not self.tenant_id.email:
            raise ValidationError("Tenant email address is not configured. Please add tenant email first.")

        # Generate PDF report - Correct way for Odoo 18
        report_action = self.env.ref('community_management.action_report_lease_agreement')
        pdf_content, _ = report_action._render_qweb_pdf(report_action, res_ids=self.ids)

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': f'Lease_Agreement_{self.flat_id.name}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf'
        })

        # Email body
        email_body = f'''
        <div style="font-family: Arial, sans-serif; padding: 20px;">
            <p>Dear {self.tenant_id.name},</p>

            <p>We are pleased to share your lease agreement for <strong>Flat {self.flat_id.name}</strong>.</p>

            <p>Please find the lease agreement document attached to this email for your reference.</p>

            <p>If you have any questions or need assistance, please don't hesitate to contact us.</p>

            <p>Best regards,<br/>
            {self.env.user.name}<br/>
            {self.env.user.company_id.name}</p>
        </div>
        '''

        # Send email
        mail = self.env['mail.mail'].create({
            'subject': f'Lease Agreement - Flat {self.flat_id.name}',
            'email_from': self.env.user.email or self.env.user.company_id.email,
            'email_to': self.tenant_id.email,
            'body_html': email_body,
            'attachment_ids': [(4, attachment.id)],
        })
        mail.send()

        # Log in chatter
        self.message_post(
            body=f"Lease agreement sent to {self.tenant_id.name} ({self.tenant_id.email})",
            subject="Lease Agreement Sent",
            attachment_ids=[attachment.id]
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Email Sent!',
                'message': f'Lease agreement has been sent to {self.tenant_id.email}',
                'type': 'success',
                'sticky': False,
            }
        }
    #
    @api.onchange('building_id')
    def _onchange_building_id(self):
        self.floor_id = False
        self.flat_id = False
        return {'domain': {'floor_id': [('building_id', '=', self.building_id.id)]}}

    @api.onchange('floor_id')
    def _onchange_floor_id(self):
        self.flat_id = False
        return {'domain': {'flat_id': [('floor_id', '=', self.floor_id.id), ('building_id', '=', self.building_id.id)]}}
    #
    @api.depends('tenant_id')
    def _compute_invoice_partner(self):
        """
        Invoice ALWAYS goes to Tenant (who pays the rent)
        Lease Owner is just a reference, doesn't affect billing
        """
        for record in self:
            if record.tenant_id:
                record.invoice_partner_id = record.tenant_id.id
            else:
                record.invoice_partner_id = False
    #
    @api.depends('lease_start_date', 'lease_end_date')
    def _compute_lease_duration(self):
        """Calculate lease duration in months"""
        for record in self:
            if record.lease_start_date and record.lease_end_date:
                delta = record.lease_end_date - record.lease_start_date
                record.lease_duration_months = int(delta.days / 30)
            else:
                record.lease_duration_months = 0
    #
    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids)
    #
    @api.constrains('tenant_id')
    def _check_tenant(self):
        for record in self:
            if not record.tenant_id:
                raise ValidationError("Tenant is required for lease transaction.")

    @api.constrains('rent_price')
    def _check_rent_price(self):
        for record in self:
            if not record.rent_price or record.rent_price <= 0:
                raise ValidationError("Monthly rent must be greater than zero.")

    @api.constrains('lease_start_date', 'lease_end_date')
    def _check_lease_dates(self):
        for record in self:
            if not record.lease_start_date or not record.lease_end_date:
                raise ValidationError("Lease start and end dates are required.")
            if record.lease_end_date <= record.lease_start_date:
                raise ValidationError("Lease end date must be after start date.")
    #
    def action_confirm(self):
        """Activate the lease - Flat becomes occupied"""
        self.ensure_one()

        # Check if flat is already occupied by another active lease
        if self.flat_id.status == 'occupied':
            raise ValidationError(f"Flat {self.flat_id.name} is already occupied by another lease!")

        # Activate lease
        self.write({'status': 'confirmed'})

        # Update flat to occupied with current lease info
        self.flat_id.write({
            'status': 'occupied',
            'tenant_id': self.tenant_id.id,
            'lease_owner_id': self.lease_owner_id.id if self.lease_owner_id else False,
            'rent_price': self.rent_price,
            'lease_start_date': self.lease_start_date,
            'lease_end_date': self.lease_end_date,
        })

        # Log activation
        self.message_post(
            body=f"Lease activated. Flat {self.flat_id.name} is now occupied by {self.tenant_id.name}.",
            subject="Lease Activated"
        )

        return True

    def action_terminate(self):
        """Terminate the lease - Flat becomes available, lease data preserved"""
        self.ensure_one()

        # Change transaction status to terminated
        self.write({'status': 'terminated'})

        # Make flat available (lease data preserved in transaction)
        if self.flat_id:
            self.flat_id.write({'status': 'available'})

        # Log the termination
        self.message_post(
            body=f"Lease terminated. Flat {self.flat_id.name} is now available for new lease.",
            subject="Lease Terminated"
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Lease Terminated!',
                'message': f'Flat {self.flat_id.name} is now available.',
                'type': 'warning',
                'sticky': False,
            }
        }

    def action_cancel(self):
        """Cancel the lease - Flat becomes available"""
        self.ensure_one()

        # Change status to cancelled
        self.write({'status': 'cancelled'})

        # Make flat available
        if self.flat_id:
            self.flat_id.write({'status': 'available'})

        # Log cancellation
        self.message_post(
            body=f"Lease cancelled. Flat {self.flat_id.name} is now available.",
            subject="Lease Cancelled"
        )

        return True

    def action_reset_to_draft(self):
        """Reset to draft"""
        self.write({'status': 'draft'})
    #
    @api.model
    def _cron_expire_leases(self):
        """Scheduled action to auto-expire leases past end date"""
        today = fields.Date.today()

        # Find all active leases past their end date
        expired_leases = self.search([
            ('status', '=', 'confirmed'),
            ('lease_end_date', '<', today)
        ])

        for lease in expired_leases:
            # Mark as expired
            lease.write({'status': 'expired'})

            # Make flat available
            if lease.flat_id:
                lease.flat_id.write({'status': 'available'})

            # Log expiration
            lease.message_post(
                body=f"Lease expired. Flat {lease.flat_id.name} is now available.",
                subject="Lease Expired"
            )
    #
    def _get_current_month_key(self):
        """Get current month in YYYY-MM format"""
        return fields.Date.today().strftime('%Y-%m')

    def _is_month_invoiced(self, month_key):
        """Check if a specific month has been invoiced"""
        if not self.invoiced_months:
            return False
        return month_key in self.invoiced_months.split(',')

    def _mark_month_invoiced(self, month_key):
        """Mark a month as invoiced"""
        if not self.invoiced_months:
            self.invoiced_months = month_key
        elif month_key not in self.invoiced_months:
            self.invoiced_months = f"{self.invoiced_months},{month_key}"
    #
    def action_create_security_deposit_invoice(self):
        """Create invoice for security deposit"""
        self.ensure_one()

        if not self.security_deposit or self.security_deposit <= 0:
            raise ValidationError("Security deposit amount must be greater than zero to create invoice.")

        if self.security_deposit_invoiced:
            raise ValidationError("Security deposit invoice has already been created for this lease.")

        if not self.tenant_id:
            raise ValidationError("Cannot create invoice. Tenant is required.")

        # Invoice description
        description = f'Security Deposit for Lease\n'
        description += f'Property: Flat {self.flat_id.name}, {self.building_id.name}\n'
        if self.lease_owner_id:
            description += f'Lease Owner: {self.lease_owner_id.name}\n'
        description += f'Tenant: {self.tenant_id.name}\n'
        description += f'Lease Period: {self.lease_start_date} to {self.lease_end_date}'

        # Create invoice - to Tenant
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.tenant_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_origin': f'Security Deposit - Lease: {self.flat_id.name}',
            'currency_id': self.currency_id.id,
            'transaction_id': self.id,
            'invoice_line_ids': [(0, 0, {
                'name': description,
                'quantity': 1,
                'price_unit': self.security_deposit,
            })],
        }

        invoice = self.env['account.move'].sudo().create(invoice_vals)

        # Mark security deposit as invoiced
        self.write({'security_deposit_invoiced': True})

        return {
            'type': 'ir.actions.act_window',
            'name': 'Security Deposit Invoice',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_invoice(self):
        """Create monthly rent invoice - ALWAYS to Tenant"""
        self.ensure_one()

        # Check if current month already invoiced
        current_month = self._get_current_month_key()

        # if self._is_month_invoiced(current_month):
        #     raise ValidationError(
        #         f"Rent invoice for {datetime.strptime(current_month, '%Y-%m').strftime('%B %Y')} has already been created!")

        # Invoice ALWAYS goes to Tenant
        if not self.tenant_id:
            raise ValidationError("Cannot create invoice. Tenant is required.")

        # Invoice description
        month_name = datetime.strptime(current_month, '%Y-%m').strftime('%B %Y')

        if self.lease_owner_id:
            # Lease Owner exists, but Tenant pays
            description = f'Monthly Rent for {month_name}\n'
            description += f'Property: Flat {self.flat_id.name}, {self.building_id.name}\n'
            description += f'Lease Owner: {self.lease_owner_id.name}\n'
            description += f'Tenant (Paying): {self.tenant_id.name}'
        else:
            # Direct tenant pays
            description = f'Monthly Rent for {month_name}\n'
            description += f'Property: Flat {self.flat_id.name}, {self.building_id.name}\n'
            description += f'Tenant: {self.tenant_id.name}'

        # Create invoice - ALWAYS to Tenant
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.tenant_id.id,  # ALWAYS Tenant
            'invoice_date': fields.Date.today(),
            'invoice_origin': f'Lease: {self.flat_id.name}',
            'currency_id': self.currency_id.id,
            'transaction_id': self.id,
            'invoice_line_ids': [(0, 0, {
                'name': description,
                'quantity': 1,
                'price_unit': self.rent_price,
            })],
        }

        invoice = self.env['account.move'].sudo().create(invoice_vals)

        # Mark month as invoiced
        self._mark_month_invoiced(current_month)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Rent Invoice',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_invoices(self):
        """View all invoices"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'account.move',
            'domain': [('transaction_id', '=', self.id)],
            'view_mode': 'list,form',
            'target': 'current',
            'context': {'create': False},
        }

    def action_generate_agreement(self):
        """Generate lease agreement PDF"""
        return self.env.ref('community_management.action_report_lease_agreement').report_action(self)


# Extend account.move
class AccountMove(models.Model):
    _inherit = 'account.move'

    transaction_id = fields.Many2one('flat.transaction', string='Lease Transaction', readonly=True)
