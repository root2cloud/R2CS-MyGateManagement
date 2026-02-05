# dashboard.py
from odoo import models, fields, api, _


class RealEstateDashboard(models.TransientModel):
    _name = 'real.estate.dashboard'
    _description = 'Real Estate Dashboard'

    # Tenant Stats
    active_tenants_count = fields.Integer(string=" Active Tenants", compute='_compute_stats')
    total_tenants_count = fields.Integer(string=" Total Tenants", compute='_compute_stats')

    # Flat Stats
    occupied_flats_count = fields.Integer(string=" Occupied Flats", compute='_compute_stats')
    vacant_flats_count = fields.Integer(string=" Vacant Flats", compute='_compute_stats')

    # Maintenance Stats
    total_maintenance_count = fields.Integer(string=" Total Maintenance", compute='_compute_stats')
    pending_maintenance_count = fields.Integer(string=" Pending Maintenance", compute='_compute_stats')
    confirmed_maintenance_count = fields.Integer(string=" Confirmed Maintenance", compute='_compute_stats')
    total_maintenance_amount = fields.Monetary(string=" Total Amount", compute='_compute_stats')
    collected_amount = fields.Monetary(string=" Collected Amount", compute='_compute_stats')
    pending_amount = fields.Monetary(string=" Pending Amount", compute='_compute_stats')

    # curpus fund

    total_corpus_fund_count = fields.Integer(string=" Total Corpus Fund Invoices", compute='_compute_stats')
    draft_corpus_fund_count = fields.Integer(string=" Draft Corpus Fund", compute='_compute_stats')
    invoiced_corpus_fund_count = fields.Integer(string=" Invoiced Corpus Fund", compute='_compute_stats')
    total_corpus_fund_amount = fields.Monetary(string=" Total Corpus Fund Amount", compute='_compute_stats')
    collected_corpus_fund_amount = fields.Monetary(string=" Collected Corpus Fund Amount", compute='_compute_stats')
    pending_corpus_fund_amount = fields.Monetary(string=" Pending Corpus Fund Amount", compute='_compute_stats')

    # Event Stats
    total_events_count = fields.Integer(string=" Total Events", compute='_compute_stats')
    draft_events_count = fields.Integer(string=" Draft Events", compute='_compute_stats')
    submitted_events_count = fields.Integer(string=" Submitted Events", compute='_compute_stats')
    approved_events_count = fields.Integer(string=" Approved Events", compute='_compute_stats')
    total_events_expense = fields.Monetary(string="Total Expense", compute='_compute_stats')

    # Resident Stats
    total_residents_count = fields.Integer(string=" Total Residents", compute='_compute_stats')
    adult_residents_count = fields.Integer(string=" Adult Residents", compute='_compute_stats')
    child_residents_count = fields.Integer(string=" Child Residents", compute='_compute_stats')

    # Pet Stats
    total_pets_count = fields.Integer(string=" Total Pets", compute='_compute_stats')
    dog_count = fields.Integer(string=" Dogs", compute='_compute_stats')
    cat_count = fields.Integer(string=" Cats", compute='_compute_stats')
    other_pets_count = fields.Integer(string=" Other Pets", compute='_compute_stats')

    # Vehicle Stats
    total_vehicles_count = fields.Integer(string=" Total Vehicles", compute='_compute_stats')
    car_count = fields.Integer(string=" Cars", compute='_compute_stats')
    motorcycle_count = fields.Integer(string=" Motorcycles", compute='_compute_stats')
    other_vehicles_count = fields.Integer(string=" Other Vehicles", compute='_compute_stats')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    def _compute_stats(self):
        """Compute all dashboard statistics"""
        for record in self:

            record.total_tenants_count = self.env['flat.transaction'].search_count([
                ('status', 'in', ['draft', 'confirmed', 'expired', 'terminated', 'cancelled'])
            ])

            record.active_tenants_count = self.env['flat.management'].search_count([
                ('status', '=', 'occupied')
            ])

            # Flat Stats
            record.occupied_flats_count = self.env['flat.management'].search_count([
                ('status', '=', 'occupied')
            ])
            record.vacant_flats_count = self.env['flat.management'].search_count([
                ('status', '=', 'available')
            ])
            # Maintenance Stats (keep as is)
            record.total_maintenance_count = self.env['flat.maintenance'].search_count([])
            record.pending_maintenance_count = self.env['flat.maintenance'].search_count([
                ('status', '=', 'draft')
            ])
            record.confirmed_maintenance_count = self.env['flat.maintenance'].search_count([
                ('status', '=', 'confirmed')
            ])

            # CORRECTED: Maintenance Amounts based on INVOICES only
            total_invoiced_amount = 0.0  # Sum of all invoice amounts
            collected_amount = 0.0  # Sum of PAID invoice amounts
            pending_amount = 0.0  # Sum of UNPAID invoice amounts

            # Get all maintenance records
            maintenance_records = self.env['flat.maintenance'].search([])

            # Track invoices we've already counted (to avoid duplicates)
            processed_invoices = set()

            for maintenance in maintenance_records:
                # Check each invoice for this maintenance
                for invoice in maintenance.invoice_ids:
                    # Skip if we already processed this invoice
                    if invoice.id in processed_invoices:
                        continue

                    processed_invoices.add(invoice.id)

                    # Add to total invoiced amount (all invoices)
                    total_invoiced_amount += invoice.amount_total

                    # Check payment status
                    if invoice.payment_state == 'paid':
                        # Invoice is fully PAID
                        collected_amount += invoice.amount_total
                    elif invoice.payment_state in ['not_paid', 'partial']:
                        # Invoice is NOT PAID or PARTIALLY PAID
                        if invoice.payment_state == 'partial':
                            # For partial payments: paid portion to collected, unpaid to pending
                            paid_amount = invoice.amount_total - invoice.amount_residual
                            collected_amount += paid_amount
                            pending_amount += invoice.amount_residual
                        else:  # not_paid
                            pending_amount += invoice.amount_total
                    elif invoice.state == 'draft':
                        # Invoice is still draft
                        pending_amount += invoice.amount_total

            # Set the computed values
            record.total_maintenance_amount = total_invoiced_amount  # Total of all invoices
            record.collected_amount = collected_amount  # Total paid amount
            record.pending_amount = pending_amount  # Total unpaid amount

            # NEW: Corpus Fund Statistics
            record.total_corpus_fund_count = self.env['corpus.fund.invoice'].search_count([])
            record.draft_corpus_fund_count = self.env['corpus.fund.invoice'].search_count([
                ('state', '=', 'draft')
            ])
            record.invoiced_corpus_fund_count = self.env['corpus.fund.invoice'].search_count([
                ('state', '=', 'invoiced')
            ])

            # Corpus Fund Amounts
            total_corpus_fund_amount = 0.0
            collected_corpus_fund_amount = 0.0
            pending_corpus_fund_amount = 0.0

            # Get all corpus fund invoices
            corpus_fund_records = self.env['corpus.fund.invoice'].search([])

            for corpus in corpus_fund_records:
                total_corpus_fund_amount += corpus.amount

                # Check if invoice exists and its payment status
                if corpus.invoice_id:
                    invoice = corpus.invoice_id
                    if invoice.payment_state == 'paid':
                        collected_corpus_fund_amount += invoice.amount_total
                    elif invoice.payment_state in ['not_paid', 'partial']:
                        if invoice.payment_state == 'partial':
                            paid_amount = invoice.amount_total - invoice.amount_residual
                            collected_corpus_fund_amount += paid_amount
                            pending_corpus_fund_amount += invoice.amount_residual
                        else:  # not_paid
                            pending_corpus_fund_amount += invoice.amount_total
                    elif invoice.state == 'draft':
                        pending_corpus_fund_amount += invoice.amount_total
                else:
                    # No invoice created yet, amount is pending
                    pending_corpus_fund_amount += corpus.amount

            # Set corpus fund values
            record.total_corpus_fund_amount = total_corpus_fund_amount
            record.collected_corpus_fund_amount = collected_corpus_fund_amount
            record.pending_corpus_fund_amount = pending_corpus_fund_amount

            # Event Stats
            record.total_events_count = self.env['community.festival'].search_count([])
            record.draft_events_count = self.env['community.festival'].search_count([
                ('state', '=', 'draft')
            ])
            record.submitted_events_count = self.env['community.festival'].search_count([
                ('state', '=', 'submitted')
            ])
            record.approved_events_count = self.env['community.festival'].search_count([
                ('state', '=', 'approved')
            ])

            event_records = self.env['community.festival'].search([])
            record.total_events_expense = sum(rec.total_expense for rec in event_records)

            # Resident Stats
            record.total_residents_count = self.env['family.member'].search_count([])
            record.adult_residents_count = self.env['family.member'].search_count([
                ('member_type', '=', 'adult')
            ])
            record.child_residents_count = self.env['family.member'].search_count([
                ('member_type', '=', 'child')
            ])

            # Pet Stats
            record.total_pets_count = self.env['pet.management'].search_count([
                ('active', '=', True)
            ])
            record.dog_count = self.env['pet.management'].search_count([
                ('pet_type', '=', 'dog'),
                ('active', '=', True)
            ])
            record.cat_count = self.env['pet.management'].search_count([
                ('pet_type', '=', 'cat'),
                ('active', '=', True)
            ])
            record.other_pets_count = record.total_pets_count - record.dog_count - record.cat_count

            # Vehicle Stats
            record.total_vehicles_count = self.env['vehicle.management'].search_count([
                ('active', '=', True)
            ])
            record.car_count = self.env['vehicle.management'].search_count([
                ('vehicle_type', '=', 'car'),
                ('active', '=', True)
            ])
            record.motorcycle_count = self.env['vehicle.management'].search_count([
                ('vehicle_type', '=', 'motorcycle'),
                ('active', '=', True)
            ])
            record.other_vehicles_count = record.total_vehicles_count - record.car_count - record.motorcycle_count

    def refresh_dashboard(self):
        """Refresh dashboard data"""
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_open_maintenance(self):
        """Open maintenance list view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Maintenance',
            'res_model': 'flat.maintenance',
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_open_corpus_fund(self):
        """Open corpus fund list view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Corpus Fund Invoices',
            'res_model': 'corpus.fund.invoice',
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_open_events(self):
        """Open events list view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Community Events',
            'res_model': 'community.festival',
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_open_residents(self):
        """Open residents list view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Family Members',
            'res_model': 'family.member',
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_open_pets(self):
        """Open pets list view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pets',
            'res_model': 'pet.management',
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_open_vehicles(self):
        """Open vehicles list view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vehicles',
            'res_model': 'vehicle.management',
            'view_mode': 'list,form',
            'target': 'current',
        }
