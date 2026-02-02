from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Maintenance(models.Model):
    _name = 'flat.maintenance'
    _description = 'Flat Maintenance'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'tenant_id'

    # Tenant & Property
    tenant_id = fields.Many2one('res.partner', string='Tenant', required=True, tracking=True)
    flat_id = fields.Many2one('flat.management', string='Flat', tracking=True)
    building_id = fields.Many2one('building.management', string='Building', related='flat_id.building_id', store=True)

    # Flat area - needed for area-based calculations
    flat_area = fields.Float(string='Flat Area (sq.ft.)',
                             related='flat_id.area',
                             store=True,
                             tracking=True)

    # Calculation Type: Standard (fixed) or Area Based
    calculation_type = fields.Selection([
        ('standard', 'Standard'),
        ('area_based', 'Area Based'),
    ], string='Calculation Type', default='standard', required=True, tracking=True)

    # For Standard calculation
    standard_amount = fields.Monetary(string='Standard Amount',
                                      currency_field='currency_id',
                                      tracking=True)

    # For Area Based calculation
    area_rate = fields.Float(string='Rate per sq.ft.',
                             help='Rate to multiply with flat area',
                             tracking=True)

    # Total Amount (calculated based on calculation type)
    total_amount = fields.Monetary(string='Total Maintenance Amount',
                                   compute='_compute_total_amount',
                                   store=True,
                                   currency_field='currency_id',
                                   tracking=True)

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.user.company_id.currency_id.id)

    # Multiple Invoices Support
    invoice_ids = fields.Many2many('account.move', string='Invoices', readonly=True, copy=False)
    invoice_count = fields.Integer(string='Invoice Count',
                                   compute='_compute_invoice_count',
                                   store=True)

    # Status
    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string='Status', default='draft', tracking=True)

    notes = fields.Text(string='Notes')

    @api.onchange('tenant_id')
    def _onchange_tenant_id(self):
        """Auto-fill flat when tenant is selected"""
        if self.tenant_id:
            # Find current flat occupied by this tenant
            flat = self.env['flat.management'].search([
                ('tenant_id', '=', self.tenant_id.id),
                ('status', '=', 'occupied')
            ], limit=1)

            if flat:
                self.flat_id = flat.id
            else:
                # Try to find from any transaction
                transaction = self.env['flat.transaction'].search([
                    ('tenant_id', '=', self.tenant_id.id)
                ], order='lease_end_date desc', limit=1)

                if transaction:
                    self.flat_id = transaction.flat_id.id
                else:
                    self.flat_id = False

    @api.depends('calculation_type', 'standard_amount', 'area_rate', 'flat_area')
    def _compute_total_amount(self):
        """Calculate total amount based on calculation type"""
        for record in self:
            if record.calculation_type == 'standard':
                record.total_amount = record.standard_amount
            elif record.calculation_type == 'area_based':
                # Check if we have both area and rate
                if record.flat_area and record.area_rate:
                    record.total_amount = record.flat_area * record.area_rate
                else:
                    record.total_amount = 0.0
            else:
                record.total_amount = 0.0

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        """Count all invoices created for this maintenance record"""
        for record in self:
            record.invoice_count = len(record.invoice_ids)

    def action_confirm(self):
        """Confirm maintenance"""
        self.write({'status': 'confirmed'})

    def action_draft(self):
        """Reset maintenance to draft state"""
        self.write({'status': 'draft'})

    def action_create_maintenance_invoice(self):
        """Create maintenance invoice - Can be created multiple times"""
        self.ensure_one()

        if not self.tenant_id:
            raise ValidationError("Tenant is required to create invoice.")

        if self.total_amount <= 0:
            raise ValidationError("Total maintenance amount must be greater than zero.")

        # Prepare invoice line
        invoice_line_name = ""
        if self.calculation_type == 'standard':
            invoice_line_name = f"Standard Maintenance - {self.flat_id.name if self.flat_id else ''}"
        elif self.calculation_type == 'area_based':
            invoice_line_name = f"Area Based Maintenance ({self.flat_area} sq.ft. × {self.area_rate}) - {self.flat_id.name if self.flat_id else ''}"

        # Create invoice
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.tenant_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_origin': f'Maintenance - {self.flat_id.name if self.flat_id else "N/A"}',
            'invoice_line_ids': [(0, 0, {
                'name': invoice_line_name,
                'quantity': 1,
                'price_unit': self.total_amount,
                'product_id': False,
            })],
        })

        # Link invoice to maintenance record (Many2many - allows multiple)
        self.invoice_ids = [(4, invoice.id)]

        # Log in chatter
        self.message_post(
            body=f"Maintenance invoice {invoice.name} created for amount {self.total_amount}. Total invoices: {self.invoice_count}",
            subject="Maintenance Invoice Created"
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Invoice Created!',
                'message': f'Maintenance invoice {invoice.name} has been created. Total invoices: {self.invoice_count}',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_all_invoices(self):
        """View all invoices created for this maintenance record"""
        self.ensure_one()

        if not self.invoice_ids:
            raise ValidationError("No invoices created yet.")

        return {
            'type': 'ir.actions.act_window',
            'name': f'Maintenance Invoices - {self.tenant_id.name}',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.invoice_ids.ids)],
            'view_mode': 'list,form',
            'target': 'current',
            'context': {'create': False}
        }

    @api.onchange('calculation_type')
    def _onchange_calculation_type(self):
        """Reset fields when calculation type changes"""
        if self.calculation_type == 'standard':
            self.area_rate = 0.0
        elif self.calculation_type == 'area_based':
            self.standard_amount = 0.0

    @api.constrains('calculation_type', 'standard_amount', 'area_rate')
    def _check_amounts(self):
        """Validate that appropriate amount is set based on calculation type"""
        for record in self:
            if record.calculation_type == 'standard' and record.standard_amount <= 0:
                raise ValidationError("Standard amount must be greater than 0 for Standard calculation type.")

            if record.calculation_type == 'area_based' and record.area_rate <= 0:
                raise ValidationError("Area rate must be greater than 0 for Area Based calculation type.")


