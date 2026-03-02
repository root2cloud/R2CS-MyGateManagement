# File: saas_dashboard.py
from odoo import models, fields, api
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class SaasMasterDashboard(models.TransientModel):
    _name = 'saas.master.dashboard'
    _description = 'SaaS Master Analytics Dashboard'

    # 1. FILTER
    community_id = fields.Many2one('community.management', string='Active Community', required=True)

    # 2. KPI CARDS
    total_flats = fields.Integer()
    occupied_flats = fields.Integer()
    vacant_flats = fields.Integer()
    total_residents = fields.Integer()
    visitors_today = fields.Integer()
    pending_approvals = fields.Integer()
    open_complaints = fields.Integer()  # Mapped to pending access/help requests
    maintenance_due = fields.Float()
    maintenance_collected = fields.Float()

    # 3. GRAPHICAL REPORTS (HTML)
    chart_occupancy = fields.Html()
    chart_financial = fields.Html()
    chart_amenities = fields.Html()

    # 4. RECENT ACTIVITIES (HTML)
    recent_visitors = fields.Html()
    recent_requests = fields.Html()
    recent_payments = fields.Html()

    @api.onchange('community_id')
    def _compute_dashboard(self):
        if not self.community_id:
            self._reset_dashboard()
            return

        cid = self.community_id.id
        today = fields.Date.today()

        try:
            # --- AGGREGATE KPIs ---
            # Flats & Residents
            flats = self.env['flat.management'].search([('community_id', '=', cid)])
            self.total_flats = len(flats)
            self.occupied_flats = len(flats.filtered(lambda f: f.status == 'occupied'))
            self.vacant_flats = len(flats.filtered(lambda f: f.status == 'available'))

            flat_ids = flats.ids
            if flat_ids:
                self.total_residents = self.env['family.member'].search_count([('flat_id', 'in', flat_ids)])
                self.visitors_today = self.env['mygate.visitor'].search_count(
                    [('flat_id', 'in', flat_ids), ('expected_date', '=', today)])
            else:
                self.total_residents = self.visitors_today = 0

            # Requests & Approvals
            self.pending_approvals = self.env['resident.access.request'].search_count(
                [('community_id', '=', cid), ('state', '=', 'pending')])
            self.open_complaints = self.env['community.amenity.booking'].search_count(
                [('community_id', '=', cid), ('state', '=', 'pending')])

            # Financials (Maintenance & Corpus)
            m_records = self.env['flat.maintenance'].search([('community_id', '=', cid)])
            c_amt, p_amt = 0.0, 0.0
            seen_inv = set()
            for m in m_records:
                for inv in m.invoice_ids:
                    if inv.id in seen_inv: continue
                    seen_inv.add(inv.id)
                    if inv.payment_state == 'paid':
                        c_amt += inv.amount_total
                    elif inv.payment_state == 'partial':
                        c_amt += (inv.amount_total - inv.amount_residual)
                        p_amt += inv.amount_residual
                    else:
                        p_amt += inv.amount_total

            self.maintenance_collected = c_amt
            self.maintenance_due = p_amt

            # --- GENERATE CSS CHARTS ---
            # 1. Occupancy Stacked Bar
            occ_pct = (self.occupied_flats / self.total_flats * 100) if self.total_flats else 0
            vac_pct = 100 - occ_pct
            self.chart_occupancy = f"""
                <div style="margin-top: 15px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-weight: bold; color: #475569;">
                        <span><i class="fa fa-circle text-success"></i> Occupied ({self.occupied_flats})</span>
                        <span><i class="fa fa-circle text-warning"></i> Vacant ({self.vacant_flats})</span>
                    </div>
                    <div style="height: 24px; width: 100%; background: #fef08a; border-radius: 12px; overflow: hidden; display: flex; box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="width: {occ_pct}%; background: linear-gradient(90deg, #10b981, #34d399); height: 100%; transition: width 1s ease-in-out;"></div>
                    </div>
                </div>
            """

            # 2. Financial Collection Bar
            total_fin = self.maintenance_collected + self.maintenance_due
            col_pct = (self.maintenance_collected / total_fin * 100) if total_fin else 0
            self.chart_financial = f"""
                <div style="margin-top: 15px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-weight: bold; color: #475569;">
                        <span><i class="fa fa-circle text-primary"></i> Collected</span>
                        <span><i class="fa fa-circle text-danger"></i> Due</span>
                    </div>
                    <div style="height: 24px; width: 100%; background: #fca5a5; border-radius: 12px; overflow: hidden; display: flex; box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="width: {col_pct}%; background: linear-gradient(90deg, #3b82f6, #60a5fa); height: 100%; transition: width 1s ease-in-out;"></div>
                    </div>
                </div>
            """

            # --- GENERATE RECENT ACTIVITY TABLES ---
            def make_badge(text, color):
                colors = {'pending': '#f59e0b', 'approved': '#10b981', 'paid': '#3b82f6', 'rejected': '#ef4444'}
                bg = colors.get(text.lower(), '#64748b')
                return f"<span style='background: {bg}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; text-transform: uppercase;'>{text}</span>"

            # Visitors
            vis = self.env['mygate.visitor'].search([('flat_id', 'in', flat_ids)], limit=4, order='create_date desc')
            v_html = "<table style='width: 100%; border-collapse: collapse;'>"
            for v in vis:
                v_html += f"<tr style='border-bottom: 1px solid #f1f5f9;'><td style='padding: 12px 0; font-weight: 600; color: #1e293b;'>{v.name}</td><td style='color: #64748b;'>{v.flat_id.name if v.flat_id else ''}</td><td style='text-align: right;'>{make_badge(v.state, v.state)}</td></tr>"
            self.recent_visitors = v_html + "</table>" if vis else "<p class='text-muted'>No recent visitors.</p>"

            # Requests
            reqs = self.env['resident.access.request'].search([('community_id', '=', cid)], limit=4,
                                                              order='create_date desc')
            r_html = "<table style='width: 100%; border-collapse: collapse;'>"
            for r in reqs:
                r_html += f"<tr style='border-bottom: 1px solid #f1f5f9;'><td style='padding: 12px 0; font-weight: 600; color: #1e293b;'>{r.name}</td><td style='color: #64748b;'>{r.flat_id.name if r.flat_id else 'General'}</td><td style='text-align: right;'>{make_badge(r.state, r.state)}</td></tr>"
            self.recent_requests = r_html + "</table>" if reqs else "<p class='text-muted'>No recent requests.</p>"

        except Exception as e:
            _logger.error(f"Error computing SaaS dashboard data: {e}")

    def _reset_dashboard(self):
        self.total_flats = self.occupied_flats = self.vacant_flats = self.total_residents = self.visitors_today = 0
        self.pending_approvals = self.open_complaints = 0
        self.maintenance_due = self.maintenance_collected = 0.0
        self.chart_occupancy = self.chart_financial = self.chart_amenities = ""
        self.recent_visitors = self.recent_requests = self.recent_payments = "<p class='text-muted'>Select a community to view data.</p>"

    @api.model
    def action_open_dashboard(self):
        dashboard = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Master Analytics',
            'res_model': 'saas.master.dashboard',
            'res_id': dashboard.id,
            'view_mode': 'form',
            'target': 'inline',  # Full screen SaaS feel
            'flags': {'mode': 'readonly'},
        }