# filename: models/community_dashboard.py
from odoo import models, fields, api

class CommunityDashboard(models.Model):
    _name = 'community.dashboard'
    _description = 'Community Management Dashboard'
    _rec_name = 'name'

    name = fields.Char(string='Dashboard Name', default='Community Overview Dashboard', required=True)
    last_refresh = fields.Datetime(string='Last Refresh', default=fields.Datetime.now)

    # Selection fields for interactive filtering
    community_id = fields.Many2one('community.management', string='Select Community', tracking=True)
    building_id = fields.Many2one('building.management', string='Select Building',
                                  domain="[('community_id', '=', community_id)]", tracking=True)
    floor_id = fields.Many2one('floor.management', string='Select Floor',
                               domain="[('building_id', '=', building_id)]", tracking=True)
    flat_id = fields.Many2one('flat.management', string='Select Flat',
                              domain="[('floor_id', '=', floor_id)]", tracking=True)

    dashboard_html = fields.Html(
        string='Dashboard Content',
        compute='_compute_dashboard_html',
        sanitize=False,  # Allow custom styles/scripts if needed, but be careful
    )

    @api.depends('community_id', 'building_id', 'floor_id', 'flat_id', 'last_refresh')
    def _compute_dashboard_html(self):
        for record in self:
            html_content = """
            <div class="o_dashboard_community" style="font-family: Arial, sans-serif; padding: 20px; background: linear-gradient(to bottom, #f0f4f8, #ffffff); border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                <h1 style="text-align: center; color: #4a90e2; font-size: 28px; margin-bottom: 20px;"><i class="fa fa-dashboard" style="margin-right: 10px;"></i>Community Management Dashboard</h1>
                {summary_html}
                {hierarchy_html}
            </div>
            """.strip()

            # Overall Summary
            communities = self.env['community.management'].search([])
            total_communities = len(communities)
            total_buildings = sum(comm.building_count for comm in communities)
            total_floors = sum(comm.floor_count for comm in communities)
            total_flats = sum(comm.flat_count for comm in communities)
            all_flats = self.env['flat.management'].search([])
            available_flats = len(all_flats.filtered(lambda f: f.status == 'available'))
            occupied_flats = total_flats - available_flats

            summary_html = f"""
            <div style="margin-bottom: 30px; text-align: center; background: linear-gradient(to right, #4a90e2, #50c878); color: white; padding: 15px; border-radius: 10px;">
                <h2 style="color: white; margin-bottom: 10px;">Overall Summary</h2>
                <p style="font-size: 16px;">
                    <i class="fa fa-globe" style="margin-right: 5px;"></i>Communities: <strong>{total_communities}</strong> | 
                    <i class="fa fa-building" style="margin-right: 5px;"></i>Buildings: <strong>{total_buildings}</strong> | 
                    <i class="fa fa-layer-group" style="margin-right: 5px;"></i>Floors: <strong>{total_floors}</strong> | 
                    <i class="fa fa-home" style="margin-right: 5px;"></i>Flats: <strong>{total_flats}</strong> 
                    (<span style="color: #d4f4e2;"><i class="fa fa-check-circle"></i> Available: {available_flats}</span> | 
                    <span style="color: #f4d4d4;"><i class="fa fa-times-circle"></i> Occupied: {occupied_flats}</span>)
                </p>
            </div>
            """

            # Hierarchy based on selection
            hierarchy_html = '<h2 style="color: #4a90e2; text-align: center; margin-top: 30px;"><i class="fa fa-sitemap" style="margin-right: 10px;"></i>Hierarchy View</h2>'

            if not record.community_id:
                # Show all communities
                hierarchy_html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">'
                for comm in communities.sorted('name'):
                    hierarchy_html += f"""
                    <div style="background: linear-gradient(to bottom, #ffffff, #f0f4f8); padding: 15px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); text-align: center;">
                        <i class="fa fa-globe fa-2x" style="color: #4a90e2; margin-bottom: 10px;"></i>
                        <strong style="font-size: 18px; color: #333;">{comm.name or 'Unnamed'}</strong><br>
                        <span style="color: #666;">Buildings: {comm.building_count} | Floors: {comm.floor_count} | Flats: {comm.flat_count}</span>
                    </div>
                    """
                hierarchy_html += '</div>'
            elif not record.building_id:
                # Show buildings in selected community
                community = record.community_id
                buildings = community.building_ids.sorted('name')
                hierarchy_html += f'<h3 style="text-align: center; color: #50c878;"><i class="fa fa-globe" style="margin-right: 5px;"></i>Selected Community: {community.name}</h3>'
                hierarchy_html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">'
                for building in buildings:
                    hierarchy_html += f"""
                    <div style="background: linear-gradient(to bottom, #ffffff, #f0f4f8); padding: 15px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); text-align: center;">
                        <i class="fa fa-building fa-2x" style="color: #50c878; margin-bottom: 10px;"></i>
                        <strong style="font-size: 18px; color: #333;">{building.name or 'Unnamed'}</strong><br>
                        <span style="color: #666;">Floors: {len(building.floor_ids)}</span>
                    </div>
                    """
                hierarchy_html += '</div>'
            elif not record.floor_id:
                # Show floors in selected building
                building = record.building_id
                floors = building.floor_ids.sorted('name')
                hierarchy_html += f'<h3 style="text-align: center; color: #f5a623;"><i class="fa fa-building" style="margin-right: 5px;"></i>Selected Building: {building.name} (in {building.community_id.name})</h3>'
                hierarchy_html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">'
                for floor in floors:
                    hierarchy_html += f"""
                    <div style="background: linear-gradient(to bottom, #ffffff, #f0f4f8); padding: 15px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); text-align: center;">
                        <i class="fa fa-layer-group fa-2x" style="color: #f5a623; margin-bottom: 10px;"></i>
                        <strong style="font-size: 18px; color: #333;">{floor.name or 'Unnamed'}</strong><br>
                        <span style="color: #666;">Flats: {floor.flat_count}</span>
                    </div>
                    """
                hierarchy_html += '</div>'
            elif not record.flat_id:
                # Show flats in selected floor with status
                floor = record.floor_id
                flats = floor.flat_ids.sorted('name')
                available = len(flats.filtered(lambda f: f.status == 'available'))
                occupied = len(flats) - available
                hierarchy_html += f'<h3 style="text-align: center; color: #e94e77;"><i class="fa fa-layer-group" style="margin-right: 5px;"></i>Selected Floor: {floor.name} (in {floor.building_id.name}, {floor.building_id.community_id.name})</h3>'
                hierarchy_html += f'<p style="text-align: center; font-size: 16px; margin-bottom: 20px;"><span style="color: green;"><i class="fa fa-check-circle"></i> Available: {available}</span> | <span style="color: red;"><i class="fa fa-times-circle"></i> Occupied: {occupied}</span></p>'
                hierarchy_html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">'
                for flat in flats:
                    status_text = 'Available' if flat.status == 'available' else 'Occupied'
                    status_color = '#d4f4e2' if flat.status == 'available' else '#f4d4d4'
                    status_icon = 'fa-check-circle' if flat.status == 'available' else 'fa-times-circle'
                    text_color = 'green' if flat.status == 'available' else 'red'
                    hierarchy_html += f"""
                    <div style="background: {status_color}; padding: 15px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); text-align: center;">
                        <i class="fa fa-home fa-2x" style="color: {text_color}; margin-bottom: 10px;"></i>
                        <strong style="font-size: 16px; color: #333;">{flat.name or 'Unnamed'}</strong><br>
                        <span style="font-weight: bold; color: {text_color};"><i class="fa {status_icon}"></i> {status_text}</span>
                    </div>
                    """
                hierarchy_html += '</div>'
            else:
                # Show detailed helpdesk view for selected flat, including tenant, owner, and transaction details
                flat = record.flat_id
                tenant = flat.tenant_id
                lease_owner = flat.lease_owner_id
                transaction = flat.transaction_ids.filtered(lambda t: t.status in ['draft', 'confirmed'])[:1]  # Get active or draft transaction

                # Lease details
                lease_status = transaction.status if transaction else 'No Active Transaction'
                rent_price = f"{transaction.currency_id.symbol} {transaction.rent_price:.2f}" if transaction else 'N/A'
                security_deposit = f"{transaction.currency_id.symbol} {transaction.security_deposit:.2f}" if transaction else 'N/A'
                lease_start = transaction.lease_start_date.strftime('%Y-%m-%d') if transaction and transaction.lease_start_date else 'N/A'
                lease_end = transaction.lease_end_date.strftime('%Y-%m-%d') if transaction and transaction.lease_end_date else 'N/A'
                duration_months = transaction.lease_duration_months if transaction else 'N/A'
                invoice_count = transaction.invoice_count if transaction else 0
                security_invoiced = 'Yes' if transaction and transaction.security_deposit_invoiced else 'No'
                security_color = 'green' if transaction and transaction.security_deposit_invoiced else 'red'
                invoiced_months = transaction.invoiced_months if transaction else 'None'
                notes = transaction.notes if transaction else 'No notes'

                hierarchy_html += f'<h3 style="text-align: center; color: #4a90e2;"><i class="fa fa-home" style="margin-right: 5px;"></i>Selected Flat: {flat.name} (Status: {flat.status.capitalize()})</h3>'
                hierarchy_html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">'

                # Tenant Card
                hierarchy_html += f"""
                <div style="background: linear-gradient(to bottom, #ffffff, #f0f4f8); padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                    <h4 style="color: #50c878; margin-bottom: 10px;"><i class="fa fa-user" style="margin-right: 5px;"></i>Tenant Details</h4>
                    <p><strong>Name:</strong> {tenant.name or 'N/A'}</p>
                    <p><strong>Email:</strong> {tenant.email or 'N/A'}</p>
                    <p><strong>Phone:</strong> {tenant.phone or 'N/A'}</p>
                    <p><strong>Aadhar:</strong> {tenant.aadhar_number or 'N/A'}</p>
                </div>
                """

                # Lease Owner Card
                hierarchy_html += f"""
                <div style="background: linear-gradient(to bottom, #ffffff, #f0f4f8); padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                    <h4 style="color: #f5a623; margin-bottom: 10px;"><i class="fa fa-user-tie" style="margin-right: 5px;"></i>Lease Owner Details</h4>
                    <p><strong>Name:</strong> {lease_owner.name or 'N/A'}</p>
                    <p><strong>Email:</strong> {lease_owner.email or 'N/A'}</p>
                    <p><strong>Phone:</strong> {lease_owner.phone or 'N/A'}</p>
                </div>
                """

                # Transaction Details Card
                hierarchy_html += f"""
                <div style="background: linear-gradient(to bottom, #ffffff, #f0f4f8); padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                    <h4 style="color: #e94e77; margin-bottom: 10px;"><i class="fa fa-file-contract" style="margin-right: 5px;"></i>Lease Transaction Details</h4>
                    <p><strong>Status:</strong> {lease_status.capitalize()}</p>
                    <p><strong>Monthly Rent:</strong> {rent_price}</p>
                    <p><strong>Security Deposit:</strong> {security_deposit} (<span style="color: {security_color};">Invoiced: {security_invoiced}</span>)</p>
                    <p><strong>Lease Period:</strong> {lease_start} to {lease_end} ({duration_months} months)</p>
                    <p><strong>Invoices Count:</strong> {invoice_count}</p>
                    <p><strong>Invoiced Months:</strong> {invoiced_months or 'None'}</p>
                    <p><strong>Notes:</strong> {notes}</p>
                </div>
                """

                hierarchy_html += '</div>'

            final_html = html_content.format(summary_html=summary_html, hierarchy_html=hierarchy_html)
            record.dashboard_html = final_html

    @api.onchange('community_id')
    def _onchange_community_id(self):
        self.building_id = False
        self.floor_id = False
        self.flat_id = False

    @api.onchange('building_id')
    def _onchange_building_id(self):
        self.floor_id = False
        self.flat_id = False

    @api.onchange('floor_id')
    def _onchange_floor_id(self):
        self.flat_id = False

    def action_refresh_dashboard(self):
        self.write({'last_refresh': fields.Datetime.now()})
        return True