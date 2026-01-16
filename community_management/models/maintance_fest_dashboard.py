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
    total_maintenance_amount = fields.Monetary(string="Total Amount", compute='_compute_stats')
    collected_amount = fields.Monetary(string="Collected Amount", compute='_compute_stats')
    pending_amount = fields.Monetary(string="Pending Amount", compute='_compute_stats')

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
            # Tenant Stats
            # tenants = self.env['res.partner'].search_count([
            #     ('is_company', '=', False),
            #     ('customer_rank', '>', 0)
            # ])
            # record.total_tenants_count = tenants
            record.total_tenants_count = self.env['flat.management'].search_count([
                ('status', '!=', 'occupied')
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

            # Maintenance Stats
            record.total_maintenance_count = self.env['flat.maintenance'].search_count([])
            record.pending_maintenance_count = self.env['flat.maintenance'].search_count([
                ('status', '=', 'draft')
            ])
            record.confirmed_maintenance_count = self.env['flat.maintenance'].search_count([
                ('status', '=', 'confirmed')
            ])

            # Maintenance Amounts
            maintenance_records = self.env['flat.maintenance'].search([])
            record.total_maintenance_amount = sum(rec.total_amount for rec in maintenance_records)

            draft_records = self.env['flat.maintenance'].search([('status', '=', 'draft')])
            record.pending_amount = sum(rec.total_amount for rec in draft_records)
            record.collected_amount = record.total_maintenance_amount - record.pending_amount

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