from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaasMasterDashboard(models.TransientModel):
    _name = 'saas.master.dashboard'
    _description = 'SaaS Master Engagement Dashboard'

    # 1. FILTER
    community_id = fields.Many2one('community.management', string='Active Community', required=True)

    # 2. KPI CARDS
    active_notices = fields.Integer()
    total_access_requests = fields.Integer()
    pending_access = fields.Integer()
    total_bookings = fields.Integer()
    pending_bookings = fields.Integer()

    # 3. GRAPHICAL REPORTS (HTML)
    chart_notices = fields.Html()
    chart_bookings = fields.Html()

    # 4. RECENT ACTIVITIES (HTML)
    recent_notices = fields.Html()
    recent_requests = fields.Html()
    recent_bookings = fields.Html()

    @api.onchange('community_id')
    def _compute_dashboard(self):
        if not self.community_id:
            self._reset_dashboard()
            return

        cid = self.community_id.id
        limit = 5

        try:
            # --- AGGREGATE KPIs ---

            # 1. Notice Board Data
            notices = self.env['property.notice.board'].search([('community_id', '=', cid), ('active', '=', True)])
            self.active_notices = len(notices)
            soc_count = len(notices.filtered(lambda n: n.notice_type == 'society'))
            evt_count = len(notices.filtered(lambda n: n.notice_type == 'event'))
            emg_count = len(notices.filtered(lambda n: n.notice_type == 'emergency'))

            # 2. Access Requests Data
            reqs = self.env['resident.access.request'].search([('community_id', '=', cid)])
            self.total_access_requests = len(reqs)
            self.pending_access = len(reqs.filtered(lambda r: r.state == 'pending'))
            app_access = len(reqs.filtered(lambda r: r.state == 'approved'))
            rej_access = len(reqs.filtered(lambda r: r.state == 'rejected'))

            # 3. Amenity Bookings Data
            bookings = self.env['community.amenity.booking'].search([('community_id', '=', cid)])
            self.total_bookings = len(bookings)
            self.pending_bookings = len(bookings.filtered(lambda b: b.state == 'pending'))
            app_bookings = len(bookings.filtered(lambda b: b.state == 'approved'))
            can_bookings = len(bookings.filtered(lambda b: b.state == 'cancelled'))

            # --- GENERATE CSS DISTRIBUTION CHARTS ---

            # Chart: Notice Board Distribution
            tot_n = self.active_notices or 1
            p_soc, p_evt, p_emg = (soc_count / tot_n) * 100, (evt_count / tot_n) * 100, (emg_count / tot_n) * 100

            self.chart_notices = f"""
                <div style="margin-top: 15px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-weight: 700; font-size: 0.85rem; color: #475569;">
                        <span><i class="fa fa-circle" style="color:#3b82f6;"></i> Society ({soc_count})</span>
                        <span><i class="fa fa-circle" style="color:#8b5cf6;"></i> Events ({evt_count})</span>
                        <span><i class="fa fa-circle" style="color:#ef4444;"></i> Emergency ({emg_count})</span>
                    </div>
                    <div style="height: 20px; width: 100%; background: #e2e8f0; border-radius: 10px; overflow: hidden; display: flex; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);">
                        <div style="width: {p_soc}%; background: #3b82f6; transition: 1s ease;"></div>
                        <div style="width: {p_evt}%; background: #8b5cf6; transition: 1s ease;"></div>
                        <div style="width: {p_emg}%; background: #ef4444; transition: 1s ease;"></div>
                    </div>
                </div>
            """

            # Chart: Amenity Bookings Distribution
            tot_b = self.total_bookings or 1
            p_app, p_pen, p_can = (app_bookings / tot_b) * 100, (self.pending_bookings / tot_b) * 100, (
                        can_bookings / tot_b) * 100

            self.chart_bookings = f"""
                <div style="margin-top: 15px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-weight: 700; font-size: 0.85rem; color: #475569;">
                        <span><i class="fa fa-circle" style="color:#10b981;"></i> Approved ({app_bookings})</span>
                        <span><i class="fa fa-circle" style="color:#f59e0b;"></i> Pending ({self.pending_bookings})</span>
                        <span><i class="fa fa-circle" style="color:#94a3b8;"></i> Cancelled ({can_bookings})</span>
                    </div>
                    <div style="height: 20px; width: 100%; background: #e2e8f0; border-radius: 10px; overflow: hidden; display: flex; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);">
                        <div style="width: {p_app}%; background: #10b981; transition: 1s ease;"></div>
                        <div style="width: {p_pen}%; background: #f59e0b; transition: 1s ease;"></div>
                        <div style="width: {p_can}%; background: #94a3b8; transition: 1s ease;"></div>
                    </div>
                </div>
            """

            # --- GENERATE RECENT ACTIVITY FEEDS (App Style) ---
            def get_badge(text, style_type):
                colors = {
                    'pending': ('#fef3c7', '#d97706'), 'approved': ('#d1fae5', '#059669'),
                    'rejected': ('#fee2e2', '#dc2626'), 'cancelled': ('#f1f5f9', '#475569'),
                    'society': ('#dbeafe', '#2563eb'), 'event': ('#f3e8ff', '#7e22ce'),
                    'emergency': ('#fee2e2', '#dc2626')
                }
                bg, txt = colors.get(text.lower(), ('#f1f5f9', '#475569'))
                return f"<span style='background:{bg}; color:{txt}; padding: 4px 10px; border-radius: 20px; font-size: 0.7rem; font-weight: 800; text-transform: uppercase; letter-spacing:0.5px;'>{text}</span>"

            # Recent Notices
            recent_n = self.env['property.notice.board'].search([('community_id', '=', cid)], limit=limit,
                                                                order='create_date desc')
            n_html = "<div style='display:flex; flex-direction:column; gap:12px;'>"
            for n in recent_n:
                n_html += f"<div style='padding: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; display: flex; justify-content: space-between; align-items: center;'><div style='display:flex; flex-direction:column;'><strong style='color:#0f172a; font-size:0.95rem;'>{n.name}</strong><span style='color:#64748b; font-size:0.8rem;'><i class='fa fa-calendar-o'></i> {n.date_start.strftime('%b %d, %Y') if n.date_start else 'Active'}</span></div>{get_badge(n.notice_type, 'notice')}</div>"
            self.recent_notices = n_html + "</div>" if recent_n else "<p class='text-muted'>No recent announcements.</p>"

            # Recent Access Requests
            recent_r = self.env['resident.access.request'].search([('community_id', '=', cid)], limit=limit,
                                                                  order='create_date desc')
            r_html = "<div style='display:flex; flex-direction:column; gap:12px;'>"
            for r in recent_r:
                r_html += f"<div style='padding: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; display: flex; justify-content: space-between; align-items: center;'><div style='display:flex; flex-direction:column;'><strong style='color:#0f172a; font-size:0.95rem;'>{r.name}</strong><span style='color:#64748b; font-size:0.8rem;'><i class='fa fa-home'></i> {r.flat_id.name if r.flat_id else 'Guest Access'}</span></div>{get_badge(r.state, 'request')}</div>"
            self.recent_requests = r_html + "</div>" if recent_r else "<p class='text-muted'>No recent requests.</p>"

            # Recent Amenity Bookings
            recent_b = self.env['community.amenity.booking'].search([('community_id', '=', cid)], limit=limit,
                                                                    order='create_date desc')
            b_html = "<div style='display:flex; flex-direction:column; gap:12px;'>"
            for b in recent_b:
                b_html += f"<div style='padding: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; display: flex; justify-content: space-between; align-items: center;'><div style='display:flex; flex-direction:column;'><strong style='color:#0f172a; font-size:0.95rem;'>{b.amenity_id.name if b.amenity_id else 'Amenity'}</strong><span style='color:#64748b; font-size:0.8rem;'><i class='fa fa-user'></i> {b.partner_id.name if b.partner_id else 'Resident'}</span></div>{get_badge(b.state, 'booking')}</div>"
            self.recent_bookings = b_html + "</div>" if recent_b else "<p class='text-muted'>No recent bookings.</p>"

        except Exception as e:
            _logger.error(f"Error computing SaaS dashboard data: {e}")

    def _reset_dashboard(self):
        self.active_notices = self.total_access_requests = self.pending_access = self.total_bookings = self.pending_bookings = 0
        self.chart_notices = self.chart_bookings = ""
        self.recent_notices = self.recent_requests = self.recent_bookings = "<p class='text-muted'>Select a community to view data.</p>"

    @api.model
    def action_open_dashboard(self):
        dashboard = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Master Engagement Analytics',
            'res_model': 'saas.master.dashboard',
            'res_id': dashboard.id,
            'view_mode': 'form',
            'target': 'inline',
            'flags': {'mode': 'readonly'},
        }

