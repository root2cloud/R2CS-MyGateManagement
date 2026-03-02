from odoo import models, fields, api
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class RealEstateDashboard(models.TransientModel):
    _name = 'real.estate.dashboard'
    _description = 'Real Estate Dashboard'

    community_id = fields.Many2one('community.management', string='Select Community', required=True)

    # Flat Stats
    total_flats_count = fields.Integer(string="Total Flats")
    occupied_flats_count = fields.Integer(string="Occupied Flats")
    vacant_flats_count = fields.Integer(string="Vacant Flats")
    occupancy_rate = fields.Float(string='Occupancy Rate (%)')

    # Tenant Stats
    active_tenants_count = fields.Integer(string="Active Tenants")
    total_tenants_count = fields.Integer(string="Total Tenants")

    # Maintenance Stats
    total_maintenance_count = fields.Integer(string="Total Maintenance")
    pending_maintenance_count = fields.Integer(string="Pending Maintenance")
    confirmed_maintenance_count = fields.Integer(string="Confirmed Maintenance")
    total_maintenance_amount = fields.Monetary(string="Total Amount")
    collected_amount = fields.Monetary(string="Collected Amount")
    pending_amount = fields.Monetary(string="Pending Amount")

    # Corpus Fund
    total_corpus_fund_count = fields.Integer(string="Total Corpus Fund Invoices")
    draft_corpus_fund_count = fields.Integer(string="Draft Corpus Fund")
    invoiced_corpus_fund_count = fields.Integer(string="Invoiced Corpus Fund")
    total_corpus_fund_amount = fields.Monetary(string="Total Corpus Fund Amount")
    collected_corpus_fund_amount = fields.Monetary(string="Collected Corpus Fund Amount")
    pending_corpus_fund_amount = fields.Monetary(string="Pending Corpus Fund Amount")

    # Event Stats
    total_events_count = fields.Integer(string="Total Events")
    draft_events_count = fields.Integer(string="Draft Events")
    submitted_events_count = fields.Integer(string="Submitted Events")
    approved_events_count = fields.Integer(string="Approved Events")
    total_events_expense = fields.Monetary(string="Total Expense")

    # Demographics
    total_residents_count = fields.Integer()
    total_pets_count = fields.Integer()
    total_vehicles_count = fields.Integer()

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    # --- NEW HTML FIELDS FOR PREMIUM UI ---
    chart_occupancy_html = fields.Html()
    chart_finance_html = fields.Html()
    feed_maintenance_html = fields.Html()
    feed_corpus_html = fields.Html()
    feed_events_html = fields.Html()

    @api.onchange('community_id')
    def _onchange_community_id(self):
        if not self.community_id:
            self.total_flats_count = self.occupied_flats_count = self.vacant_flats_count = self.occupancy_rate = 0
            self.total_maintenance_amount = self.collected_amount = self.pending_amount = 0.0
            self.total_corpus_fund_amount = self.collected_corpus_fund_amount = self.pending_corpus_fund_amount = 0.0
            self.total_events_expense = self.total_events_count = 0
            self.chart_occupancy_html = self.chart_finance_html = ""
            self.feed_maintenance_html = self.feed_corpus_html = self.feed_events_html = "<p class='text-muted'>Select a community.</p>"
            return

        cid = self.community_id.id
        limit = 5

        try:
            # 1. Flats & Occupancy
            flats = self.env['flat.management'].search([('community_id', '=', cid)])
            self.total_flats_count = len(flats)
            self.occupied_flats_count = len(flats.filtered(lambda f: f.status == 'occupied'))
            self.vacant_flats_count = len(flats.filtered(lambda f: f.status == 'available'))
            self.occupancy_rate = (
                        self.occupied_flats_count / self.total_flats_count * 100) if self.total_flats_count else 0.0

            flat_ids = flats.ids
            if flat_ids:
                self.total_residents_count = self.env['family.member'].search_count([('flat_id', 'in', flat_ids)])
                self.total_pets_count = self.env['pet.management'].search_count(
                    [('flat_id', 'in', flat_ids), ('active', '=', True)])
                self.total_vehicles_count = self.env['vehicle.management'].search_count(
                    [('flat_id', 'in', flat_ids), ('active', '=', True)])
            else:
                self.total_residents_count = self.total_pets_count = self.total_vehicles_count = 0

            # 2. Maintenance Analytics
            m_records = self.env['flat.maintenance'].search([('community_id', '=', cid)])
            self.total_maintenance_count = len(m_records)
            self.pending_maintenance_count = len(m_records.filtered(lambda m: m.status == 'draft'))
            self.confirmed_maintenance_count = len(m_records.filtered(lambda m: m.status == 'confirmed'))

            t_inv, c_amt, p_amt = 0.0, 0.0, 0.0
            seen_inv = set()
            for m in m_records:
                for inv in m.invoice_ids:
                    if inv.id in seen_inv: continue
                    seen_inv.add(inv.id)
                    t_inv += inv.amount_total
                    if inv.payment_state == 'paid':
                        c_amt += inv.amount_total
                    elif inv.payment_state == 'partial':
                        c_amt += (inv.amount_total - inv.amount_residual)
                        p_amt += inv.amount_residual
                    else:
                        p_amt += inv.amount_total

            self.total_maintenance_amount = t_inv
            self.collected_amount = c_amt
            self.pending_amount = p_amt

            # 3. Corpus Fund Analytics
            c_records = self.env['corpus.fund.invoice'].search([('community_id', '=', cid)])
            self.total_corpus_fund_count = len(c_records)
            self.draft_corpus_fund_count = len(c_records.filtered(lambda c: c.state == 'draft'))
            self.invoiced_corpus_fund_count = len(c_records.filtered(lambda c: c.state == 'invoiced'))

            t_corp, c_corp, p_corp = 0.0, 0.0, 0.0
            for c in c_records:
                t_corp += c.amount
                if c.invoice_id:
                    inv = c.invoice_id
                    if inv.payment_state == 'paid':
                        c_corp += inv.amount_total
                    elif inv.payment_state == 'partial':
                        c_corp += (inv.amount_total - inv.amount_residual)
                        p_corp += inv.amount_residual
                    else:
                        p_corp += inv.amount_total
                else:
                    p_corp += c.amount

            self.total_corpus_fund_amount = t_corp
            self.collected_corpus_fund_amount = c_corp
            self.pending_corpus_fund_amount = p_corp

            # 4. Events Analytics
            events = self.env['community.festival'].search([('community_id', '=', cid)])
            self.total_events_count = len(events)
            self.draft_events_count = len(events.filtered(lambda e: e.state == 'draft'))
            self.approved_events_count = len(events.filtered(lambda e: e.state == 'approved'))
            self.total_events_expense = sum(events.mapped('total_expense'))

            # --- GENERATE CSS CHARTS ---

            # Occupancy Bar
            occ_pct = self.occupancy_rate
            vac_pct = 100 - occ_pct
            self.chart_occupancy_html = f"""
                <div style="margin-top: 15px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-weight: 700; font-size: 0.85rem; color: #475569;">
                        <span><i class="fa fa-circle text-primary"></i> Occupied ({self.occupied_flats_count})</span>
                        <span><i class="fa fa-circle text-warning"></i> Available ({self.vacant_flats_count})</span>
                    </div>
                    <div style="height: 20px; width: 100%; background: #fef3c7; border-radius: 10px; overflow: hidden; display: flex; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);">
                        <div style="width: {occ_pct}%; background: linear-gradient(90deg, #3b82f6, #60a5fa); transition: 1s ease;"></div>
                    </div>
                </div>
            """

            # Financial Bar (Maintenance)
            m_total = self.collected_amount + self.pending_amount or 1
            m_col_pct = (self.collected_amount / m_total) * 100
            self.chart_finance_html = f"""
                <div style="margin-top: 15px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-weight: 700; font-size: 0.85rem; color: #475569;">
                        <span><i class="fa fa-circle text-success"></i> Collected (₹{int(self.collected_amount):,})</span>
                        <span><i class="fa fa-circle text-danger"></i> Pending (₹{int(self.pending_amount):,})</span>
                    </div>
                    <div style="height: 20px; width: 100%; background: #fee2e2; border-radius: 10px; overflow: hidden; display: flex; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);">
                        <div style="width: {m_col_pct}%; background: linear-gradient(90deg, #10b981, #34d399); transition: 1s ease;"></div>
                    </div>
                </div>
            """

            # --- GENERATE ACTIVITY FEEDS ---
            def get_badge(text, color_type):
                colors = {
                    'draft': ('#f1f5f9', '#475569'), 'confirmed': ('#dbeafe', '#2563eb'),
                    'approved': ('#d1fae5', '#059669'),
                    'invoiced': ('#fef3c7', '#d97706'), 'submitted': ('#f3e8ff', '#7e22ce')
                }
                bg, txt = colors.get(text.lower(), ('#f1f5f9', '#475569'))
                return f"<span style='background:{bg}; color:{txt}; padding: 4px 10px; border-radius: 20px; font-size: 0.7rem; font-weight: 800; text-transform: uppercase;'>{text}</span>"

            # Maintenance Feed
            recent_m = self.env['flat.maintenance'].search([('community_id', '=', cid)], limit=limit,
                                                           order='create_date desc')
            m_html = "<div style='display:flex; flex-direction:column; gap:12px;'>"
            for m in recent_m:
                amt = m.standard_amount if m.calculation_type == 'standard' else (m.flat_area * m.area_rate)
                m_html += f"<div style='padding: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; display: flex; justify-content: space-between; align-items: center;'><div style='display:flex; flex-direction:column;'><strong style='color:#0f172a;'>{m.tenant_id.name}</strong><span style='color:#64748b; font-size:0.8rem;'>{m.flat_id.name if m.flat_id else 'General'} - ₹{amt:,.2f}</span></div>{get_badge(m.status, 'maint')}</div>"
            self.feed_maintenance_html = m_html + "</div>" if recent_m else "<p class='text-muted'>No recent maintenance records.</p>"

            # Corpus Feed
            recent_c = self.env['corpus.fund.invoice'].search([('community_id', '=', cid)], limit=limit,
                                                              order='create_date desc')
            c_html = "<div style='display:flex; flex-direction:column; gap:12px;'>"
            for c in recent_c:
                c_html += f"<div style='padding: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; display: flex; justify-content: space-between; align-items: center;'><div style='display:flex; flex-direction:column;'><strong style='color:#0f172a;'>{c.flat_id.name}</strong><span style='color:#64748b; font-size:0.8rem;'>₹{c.amount:,.2f}</span></div>{get_badge(c.state, 'corpus')}</div>"
            self.feed_corpus_html = c_html + "</div>" if recent_c else "<p class='text-muted'>No recent corpus invoices.</p>"

            # Events Feed
            recent_e = self.env['community.festival'].search([('community_id', '=', cid)], limit=limit,
                                                             order='date_start desc')
            e_html = "<div style='display:flex; flex-direction:column; gap:12px;'>"
            for e in recent_e:
                e_html += f"<div style='padding: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; display: flex; justify-content: space-between; align-items: center;'><div style='display:flex; flex-direction:column;'><strong style='color:#0f172a;'>{e.name}</strong><span style='color:#64748b; font-size:0.8rem;'><i class='fa fa-calendar-o'></i> {e.date_start.strftime('%b %d, %Y') if e.date_start else 'TBD'}</span></div>{get_badge(e.state, 'event')}</div>"
            self.feed_events_html = e_html + "</div>" if recent_e else "<p class='text-muted'>No upcoming events.</p>"

        except Exception as e:
            _logger.error(f"Error computing financial dashboard data: {e}")

    # Standard Actions
    def refresh_dashboard(self):
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_open_maintenance(self):
        return {'type': 'ir.actions.act_window', 'name': 'Maintenance', 'res_model': 'flat.maintenance',
                'view_mode': 'list,form', 'target': 'current'}

    def action_open_corpus_fund(self):
        return {'type': 'ir.actions.act_window', 'name': 'Corpus Fund', 'res_model': 'corpus.fund.invoice',
                'view_mode': 'list,form', 'target': 'current'}

    def action_open_events(self):
        return {'type': 'ir.actions.act_window', 'name': 'Events', 'res_model': 'community.festival',
                'view_mode': 'list,form', 'target': 'current'}

    @api.model
    def action_open_dashboard(self):
        dashboard = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Financial Operations Dashboard',
            'res_model': 'real.estate.dashboard',
            'res_id': dashboard.id,
            'view_mode': 'form',
            'target': 'inline',
            'flags': {'mode': 'readonly'},
        }

