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

    # Maintenance Items
    maintenance_item_ids = fields.One2many('flat.maintenance.item', 'maintenance_id', string='Maintenance Items')

    # Total Amount
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.user.company_id.currency_id.id
                                  )
    total_amount = fields.Monetary(string='Total Maintenance Amount',
                                   compute='_compute_total_amount',
                                   store=True,

                                   currency_field='currency_id',
                                   tracking=True)

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

    @api.depends('maintenance_item_ids.amount')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(item.amount for item in record.maintenance_item_ids)
    #
    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        """Count all invoices created for this maintenance record"""
        for record in self:
            record.invoice_count = len(record.invoice_ids)

    def action_confirm(self):
        """Confirm maintenance"""
        self.write({'status': 'confirmed'})
    #
    def action_create_maintenance_invoice(self):
        """Create maintenance invoice - Can be created multiple times"""
        self.ensure_one()

        if not self.tenant_id:
            raise ValidationError("Tenant is required to create invoice.")

        if not self.maintenance_item_ids:
            raise ValidationError("Please add at least one maintenance item.")

        if self.total_amount <= 0:
            raise ValidationError("Total maintenance amount must be greater than zero.")

        # Prepare invoice lines
        invoice_lines = []
        for item in self.maintenance_item_ids:
            invoice_lines.append((0, 0, {
                'name': f'{item.get_maintenance_type_name()} - {self.flat_id.name if self.flat_id else ""}',
                'quantity': 1,
                'price_unit': item.amount,
            }))

        # Create invoice
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.tenant_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_origin': f'Maintenance - {self.flat_id.name if self.flat_id else "N/A"}',
            'invoice_line_ids': invoice_lines,
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


class MaintenanceItem(models.Model):
    _name = 'flat.maintenance.item'
    _description = 'Maintenance Item'

    maintenance_id = fields.Many2one('flat.maintenance', string='Maintenance', required=True, ondelete='cascade')

    maintenance_type = fields.Selection([
        ('electricity', 'Electricity Bill'),
        ('water', 'Water Bill'),
        ('gas', 'Gas Bill'),
        ('cleaning', 'Cleaning Charges'),
        ('security', 'Security Charges'),
        ('parking', 'Parking Charges'),
        ('common_area', 'Common Area Maintenance'),
        ('lift', 'Lift Maintenance'),
        ('generator', 'Generator Maintenance'),
        ('waste', 'Waste Management'),
        ('repair', 'Repair & Maintenance'),
        ('other', 'Other')
    ], string='Maintenance Type', required=True)

    currency_id = fields.Many2one('res.currency',
                                  related='maintenance_id.currency_id',
                                  store=True)
    amount = fields.Monetary(string='Amount', required=True,
                             currency_field='currency_id'
                             )

    description = fields.Char(string='Description')

    def get_maintenance_type_name(self):
        """Get display name of maintenance type"""
        type_dict = dict(self._fields['maintenance_type'].selection)
        return type_dict.get(self.maintenance_type, 'Maintenance')
