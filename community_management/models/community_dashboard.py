from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class CommunityDashboard(models.TransientModel):
    _name = 'community.dashboard'
    _description = 'Property Explorer Dashboard'

    # Interactive Selectors
    community_id = fields.Many2one('community.management', string='Community')
    building_id = fields.Many2one('building.management', string='Building',
                                  domain="[('community_id', '=', community_id)]")
    floor_id = fields.Many2one('floor.management', string='Floor', domain="[('building_id', '=', building_id)]")
    flat_id = fields.Many2one('flat.management', string='Flat', domain="[('floor_id', '=', floor_id)]")

    # KPIs
    kpi_buildings = fields.Integer(string="Total Buildings")
    kpi_floors = fields.Integer(string="Total Floors")
    kpi_flats = fields.Integer(string="Total Flats")
    kpi_occupied = fields.Integer(string="Occupied Flats")
    occupancy_rate = fields.Float(string="Occupancy Rate (%)")

    # Dynamic UI Elements
    explorer_html = fields.Html(string='Explorer Content')

    @api.onchange('community_id')
    def _onchange_community(self):
        self.building_id = self.floor_id = self.flat_id = False
        self._compute_explorer_data()

    @api.onchange('building_id')
    def _onchange_building(self):
        self.floor_id = self.flat_id = False
        self._compute_explorer_data()

    @api.onchange('floor_id')
    def _onchange_floor(self):
        self.flat_id = False
        self._compute_explorer_data()

    @api.onchange('flat_id')
    def _onchange_flat(self):
        self._compute_explorer_data()

    def _compute_explorer_data(self):
        if not self.community_id:
            self.kpi_buildings = self.kpi_floors = self.kpi_flats = self.kpi_occupied = 0
            self.occupancy_rate = 0.0
            self.explorer_html = "<div style='text-align:center; padding: 50px; color: #94a3b8;'><i class='fa fa-map-o fa-4x mb-3'></i><h2>Select a Community to begin exploring.</h2></div>"
            return

        cid = self.community_id.id

        # Base Data
        buildings = self.env['building.management'].search([('community_id', '=', cid)])
        floors = self.env['floor.management'].search([('building_id', 'in', buildings.ids)])
        flats = self.env['flat.management'].search([('community_id', '=', cid)])

        # Calculate KPIs based on the current drill-down level
        if self.building_id:
            flats = flats.filtered(lambda f: f.building_id.id == self.building_id.id)
            floors = floors.filtered(lambda f: f.building_id.id == self.building_id.id)
        if self.floor_id:
            flats = flats.filtered(lambda f: f.floor_id.id == self.floor_id.id)

        self.kpi_buildings = len(buildings)
        self.kpi_floors = len(floors)
        self.kpi_flats = len(flats)
        self.kpi_occupied = len(flats.filtered(lambda f: f.status == 'occupied'))
        self.occupancy_rate = (self.kpi_occupied / self.kpi_flats * 100) if self.kpi_flats else 0.0

        # Build Premium HTML Explorer
        html_output = ""

        # SCENARIO 1: A specific FLAT is selected (Show Lease/Tenant Details)
        if self.flat_id:
            f = self.flat_id
            status_color = "#10b981" if f.status == 'occupied' else "#f59e0b"

            html_output += f"""
            <div style="background: white; border-radius: 20px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; display: flex; gap: 30px;">
                <div style="flex: 1; border-right: 2px dashed #e2e8f0; padding-right: 30px;">
                    <div style="display:inline-block; padding: 8px 16px; background: {status_color}20; color: {status_color}; border-radius: 20px; font-weight: 800; font-size: 0.8rem; text-transform: uppercase; margin-bottom: 15px;">{f.status}</div>
                    <h1 style="font-size: 3rem; font-weight: 900; color: #0f172a; margin: 0;"><i class="fa fa-home text-primary"></i> {f.name}</h1>
                    <p style="color: #64748b; font-size: 1.1rem; font-weight: 600; margin-top: 5px;">{f.building_id.name} • {f.floor_id.name} • {f.flat_type_id.name if f.flat_type_id else 'Standard'}</p>
                    <div style="margin-top: 30px; display: flex; gap: 15px;">
                        <div style="background: #f8fafc; padding: 15px 20px; border-radius: 12px; border: 1px solid #e2e8f0;">
                            <span style="display:block; color: #64748b; font-size: 0.8rem; font-weight: 700; text-transform:uppercase;">Area Size</span>
                            <span style="display:block; color: #0f172a; font-size: 1.2rem; font-weight: 800;">{f.area} <small>sq.ft</small></span>
                        </div>
                    </div>
                </div>
            """

            # Lease Info
            transactions = self.env['flat.transaction'].search([('flat_id', '=', f.id)], order='id desc', limit=1)
            if transactions:
                t = transactions[0]
                html_output += f"""
                <div style="flex: 1.5; padding-left: 10px;">
                    <h3 style="color: #0f172a; font-weight: 800; margin-bottom: 20px;"><i class="fa fa-file-text-o text-success mr-2"></i> Active Lease Details</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <div><small style="color:#64748b; font-weight:700; text-transform:uppercase;">Tenant Name</small><br/><strong style="font-size:1.1rem; color:#0f172a;">{t.tenant_id.name}</strong></div>
                        <div><small style="color:#64748b; font-weight:700; text-transform:uppercase;">Lease Owner</small><br/><strong style="font-size:1.1rem; color:#0f172a;">{t.lease_owner_id.name if t.lease_owner_id else 'Direct'}</strong></div>
                        <div><small style="color:#64748b; font-weight:700; text-transform:uppercase;">Monthly Rent</small><br/><strong style="font-size:1.1rem; color:#10b981;">₹{t.rent_price:,.2f}</strong></div>
                        <div><small style="color:#64748b; font-weight:700; text-transform:uppercase;">Security Deposit</small><br/><strong style="font-size:1.1rem; color:#3b82f6;">₹{t.security_deposit:,.2f}</strong></div>
                        <div><small style="color:#64748b; font-weight:700; text-transform:uppercase;">Lease Duration</small><br/><strong style="font-size:1.1rem; color:#0f172a;">{t.lease_start_date.strftime('%b %Y')} - {t.lease_end_date.strftime('%b %Y')}</strong></div>
                        <div><small style="color:#64748b; font-weight:700; text-transform:uppercase;">Contract Status</small><br/><strong style="font-size:1.1rem; color:#f59e0b;">{t.status.upper()}</strong></div>
                    </div>
                </div>
                """
            else:
                html_output += "<div style='flex: 1.5; display:flex; align-items:center; justify-content:center;'><p style='color:#94a3b8; font-weight:600; font-size:1.2rem;'><i class='fa fa-folder-open-o'></i> No active lease history found.</p></div>"

            html_output += "</div>"

        # SCENARIO 2: Viewing Multiple Flats/Floors
        else:
            html_output += "<h3 style='color: #0f172a; font-weight: 800; margin-bottom: 20px;'><i class='fa fa-th-large text-primary'></i> Property Grid View</h3>"
            html_output += "<div style='display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px;'>"

            for flat in flats[:20]:  # Show top 20 to prevent lag
                status_bg = "#d1fae5" if flat.status == 'occupied' else "#fef3c7"
                status_txt = "#059669" if flat.status == 'occupied' else "#d97706"
                html_output += f"""
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 20px; text-align: center; transition: transform 0.2s; box-shadow: 0 4px 6px rgba(0,0,0,0.02);">
                    <div style="display:inline-block; padding: 4px 12px; background: {status_bg}; color: {status_txt}; border-radius: 15px; font-weight: 800; font-size: 0.7rem; text-transform: uppercase; margin-bottom: 15px;">{flat.status}</div>
                    <h2 style="margin: 0; font-weight: 900; color: #1e293b; font-size: 1.8rem;">{flat.name}</h2>
                    <p style="color: #64748b; font-weight: 600; font-size: 0.9rem; margin: 5px 0 15px 0;">{flat.building_id.name} • {flat.floor_id.name}</p>
                    <div style="border-top: 1px solid #f1f5f9; padding-top: 15px; display: flex; justify-content: space-around;">
                        <span style="color: #94a3b8; font-size: 0.8rem; font-weight:700;"><i class="fa fa-square-o"></i> {flat.area} sq.ft</span>
                        <span style="color: #94a3b8; font-size: 0.8rem; font-weight:700;"><i class="fa fa-bed"></i> {flat.flat_type_id.name if flat.flat_type_id else 'N/A'}</span>
                    </div>
                </div>
                """
            html_output += "</div>"
            if len(flats) > 20:
                html_output += f"<p style='text-align:center; margin-top:20px; color:#64748b; font-weight:700;'>+ {len(flats) - 20} more flats hidden. Use filters to narrow down.</p>"

        self.explorer_html = html_output

    @api.model
    def action_open_dashboard(self):
        dashboard = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Property Explorer',
            'res_model': 'community.dashboard',
            'res_id': dashboard.id,
            'view_mode': 'form',
            'target': 'inline',
            'flags': {'mode': 'readonly'},
        }

