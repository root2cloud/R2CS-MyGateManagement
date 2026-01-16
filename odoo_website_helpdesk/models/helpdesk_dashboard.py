# filename: models/helpdesk_dashboard.py
from odoo import models, fields, api

# Define the constants here (they were missing!)
PRIORITIES = [
    ('0', 'Very Low'),
    ('1', 'Low'),
    ('2', 'Normal'),
    ('3', 'High'),
    ('4', 'Very High'),
]

RATING = [
    ('0', 'Very Low'),
    ('1', 'Low'),
    ('2', 'Normal'),
    ('3', 'High'),
    ('4', 'Very High'),
    ('5', 'Extreme High')
]


class HelpdeskDashboard(models.Model):
    _name = 'helpdesk.dashboard'
    _description = 'Helpdesk Management Dashboard'
    _rec_name = 'name'

    name = fields.Char(string='Dashboard Name', default='Helpdesk Overview Dashboard', required=True)
    last_refresh = fields.Datetime(string='Last Refresh', default=fields.Datetime.now)

    # Selection fields for interactive filtering
    team_id = fields.Many2one('team.helpdesk', string='Select Team', tracking=True)
    ticket_id = fields.Many2one('ticket.helpdesk', string='Select Ticket',
                                domain="[('team_id', '=', team_id)]", tracking=True)

    dashboard_html = fields.Html(
        string='Dashboard Content',
        compute='_compute_dashboard_html',
        sanitize=False,
    )

    @api.depends('team_id', 'ticket_id', 'last_refresh')
    def _compute_dashboard_html(self):
        for record in self:
            html_content = """
            <div class="o_dashboard_helpdesk" style="font-family: Arial, sans-serif; padding: 20px; background: linear-gradient(to bottom, #f0f4f8, #ffffff); border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                <h1 style="text-align: center; color: #4a90e2; font-size: 28px; margin-bottom: 20px;">
                    Helpdesk Management Dashboard
                </h1>
                {summary_html}
                {hierarchy_html}
            </div>
            """.strip()

            # Overall Summary
            teams = self.env['team.helpdesk'].search([])
            total_teams = len(teams)
            tickets = self.env['ticket.helpdesk'].search([])
            total_tickets = len(tickets)
            open_tickets = len(tickets.filtered(lambda t: not t.stage_id.closing_stage and not t.stage_id.cancel_stage))
            closed_tickets = len(tickets.filtered(lambda t: t.stage_id.closing_stage))
            cancelled_tickets = len(tickets.filtered(lambda t: t.stage_id.cancel_stage))
            high_priority_tickets = len(tickets.filtered(lambda t: t.priority in ['3', '4']))

            summary_html = f"""
            <div style="margin-bottom: 30px; text-align: center; background: linear-gradient(to right, #4a90e2, #50c878); color: white; padding: 15px; border-radius: 10px;">
                <h2 style="color: white; margin-bottom: 10px;">Overall Summary</h2>
                <p style="font-size: 16px;">
                    Teams: <strong>{total_teams}</strong> | 
                    Tickets: <strong>{total_tickets}</strong> 
                    (<span style="color: #d4f4e2;">Open: {open_tickets}</span> | 
                    <span style="color: #f4d4d4;">Closed: {closed_tickets}</span> | 
                    <span style="color: #ffd4d4;">Cancelled: {cancelled_tickets}</span>) | 
                    High Priority: <strong>{high_priority_tickets}</strong>
                </p>
            </div>
            """

            hierarchy_html = '<h2 style="color: #4a90e2; text-align: center; margin-top: 30px;">Helpdesk View</h2>'

            if not record.team_id:
                # Show all teams
                hierarchy_html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px;">'
                for team in teams.sorted('name'):
                    team_tickets = tickets.filtered(lambda t: t.team_id == team)
                    team_open = len(team_tickets.filtered(lambda t: not t.stage_id.closing_stage and not t.stage_id.cancel_stage))
                    hierarchy_html += f"""
                    <div style="background: linear-gradient(to bottom, #ffffff, #f8f9fc); padding: 18px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: center;">
                        <strong style="font-size: 20px; color: #4a90e2;">{team.name}</strong><br>
                        <small>Lead: {team.team_lead_id.name or '—'} • Members: {len(team.member_ids)}</small><br>
                        <strong>Tickets: {len(team_tickets)} (Open: {team_open})</strong>
                    </div>
                    """
                hierarchy_html += '</div>'

            elif not record.ticket_id:
                # Show tickets in selected team
                team_tickets = tickets.filtered(lambda t: t.team_id == record.team_id).sorted('name')
                hierarchy_html += f'<h3 style="text-align: center; color: #50c878;">Team: {record.team_id.name}</h3>'
                hierarchy_html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px;">'
                for ticket in team_tickets:
                    status = 'Open'
                    if ticket.stage_id.closing_stage:
                        status = 'Closed'
                    elif ticket.stage_id.cancel_stage:
                        status = 'Cancelled'

                    priority_text = dict(PRIORITIES).get(ticket.priority, 'Normal')
                    priority_color = 'red' if ticket.priority in ['3','4'] else '#666'

                    hierarchy_html += f"""
                    <div style="background: white; padding: 18px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                        <strong>{ticket.name}</strong><br>
                        <small>{ticket.subject[:60]}{'...' if len(ticket.subject or '') > 60 else ''}</small><br><br>
                        <span style="background:#e3f2fd; padding:4px 10px; border-radius:15px; font-size:13px;">{status}</span>
                        <span style="color:{priority_color}; margin-left:10px; font-weight:bold;">Priority: {priority_text}</span>
                    </div>
                    """
                hierarchy_html += '</div>'

            else:
                # Detailed ticket view
                ticket = record.ticket_id
                customer = ticket.customer_id
                stage = ticket.stage_id.name or '—'
                priority_text = dict(PRIORITIES).get(ticket.priority, 'N/A')

                hierarchy_html += f'<h3 style="text-align: center; color: #e94e77;">Ticket: {ticket.name} • Team: {ticket.team_id.name}</h3>'
                hierarchy_html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 25px; margin-top: 20px;">'

                hierarchy_html += f"""
                <div style="background:white; padding:20px; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.1);">
                    <h4 style="color:#1cc88a;">Customer</h4>
                    <p><strong>{customer.name or ticket.customer_name or '—'}</strong></p>
                    <p>{ticket.email or customer.email or '—'}</p>
                    <p>{ticket.phone or customer.phone or '—'}</p>
                </div>

                <div style="background:white; padding:20px; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.1);">
                    <h4 style="color:#f6c23e;">Ticket Info</h4>
                    <p><strong>Subject:</strong> {ticket.subject}</p>
                    <p><strong>Stage:</strong> {stage}</p>
                    <p><strong>Priority:</strong> {priority_text}</p>
                    <p><strong>Created:</strong> {ticket.create_date.strftime('%d %b %Y %H:%M') if ticket.create_date else '—'}</p>
                </div>

                <div style="background:white; padding:20px; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.1);">
                    <h4 style="color:#e74a3b;">Quick Stats</h4>
                    <p>Tasks: <strong>{len(ticket.task_ids)}</strong></p>
                    <p>Invoices: <strong>{len(ticket.invoice_ids)}</strong></p>
                    <p>Products: <strong>{len(ticket.product_ids)}</strong></p>
                </div>
                """
                hierarchy_html += '</div>'

            record.dashboard_html = html_content.format(
                summary_html=summary_html,
                hierarchy_html=hierarchy_html
            )

    @api.onchange('team_id')
    def _onchange_team_id(self):
        self.ticket_id = False

    def action_refresh_dashboard(self):
        self.write({'last_refresh': fields.Datetime.now()})
        return True

# # filename: models/helpdesk_dashboard.py
# from odoo import models, fields, api
#
# class HelpdeskDashboard(models.Model):
#     _name = 'helpdesk.dashboard'
#     _description = 'Helpdesk Management Dashboard'
#     _rec_name = 'name'
#
#     name = fields.Char(string='Dashboard Name', default='Helpdesk Overview Dashboard', required=True)
#     last_refresh = fields.Datetime(string='Last Refresh', default=fields.Datetime.now)
#
#     # Selection fields for interactive filtering
#     team_id = fields.Many2one('team.helpdesk', string='Select Team', tracking=True)
#     ticket_id = fields.Many2one('ticket.helpdesk', string='Select Ticket',
#                                 domain="[('team_id', '=', team_id)]", tracking=True)
#
#     dashboard_html = fields.Html(
#         string='Dashboard Content',
#         compute='_compute_dashboard_html',
#         sanitize=False,  # Allow custom styles/scripts if needed, but be careful
#     )
#
#     @api.depends('team_id', 'ticket_id', 'last_refresh')
#     def _compute_dashboard_html(self):
#         for record in self:
#             html_content = """
#             <div class="o_dashboard_helpdesk" style="font-family: Arial, sans-serif; padding: 20px; background: linear-gradient(to bottom, #f0f4f8, #ffffff); border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
#                 <h1 style="text-align: center; color: #4a90e2; font-size: 28px; margin-bottom: 20px;"><i class="fa fa-life-ring" style="margin-right: 10px;"></i>Helpdesk Management Dashboard</h1>
#                 {summary_html}
#                 {hierarchy_html}
#             </div>
#             """.strip()
#
#             # Overall Summary
#             teams = self.env['team.helpdesk'].search([])
#             total_teams = len(teams)
#             tickets = self.env['ticket.helpdesk'].search([])
#             total_tickets = len(tickets)
#             open_tickets = len(tickets.filtered(lambda t: not t.stage_id.closing_stage and not t.stage_id.cancel_stage))
#             closed_tickets = len(tickets.filtered(lambda t: t.stage_id.closing_stage))
#             cancelled_tickets = len(tickets.filtered(lambda t: t.stage_id.cancel_stage))
#             high_priority_tickets = len(tickets.filtered(lambda t: t.priority in ['3', '4']))
#
#             summary_html = f"""
#             <div style="margin-bottom: 30px; text-align: center; background: linear-gradient(to right, #4a90e2, #50c878); color: white; padding: 15px; border-radius: 10px;">
#                 <h2 style="color: white; margin-bottom: 10px;">Overall Summary</h2>
#                 <p style="font-size: 16px;">
#                     <i class="fa fa-users" style="margin-right: 5px;"></i>Teams: <strong>{total_teams}</strong> |
#                     <i class="fa fa-ticket" style="margin-right: 5px;"></i>Tickets: <strong>{total_tickets}</strong>
#                     (<span style="color: #d4f4e2;"><i class="fa fa-folder-open"></i> Open: {open_tickets}</span> |
#                     <span style="color: #f4d4d4;"><i class="fa fa-check-circle"></i> Closed: {closed_tickets}</span> |
#                     <span style="color: #ffd4d4;"><i class="fa fa-times-circle"></i> Cancelled: {cancelled_tickets}</span>) |
#                     <i class="fa fa-exclamation-triangle" style="margin-right: 5px;"></i>High Priority: <strong>{high_priority_tickets}</strong>
#                 </p>
#             </div>
#             """
#
#             # Hierarchy based on selection
#             hierarchy_html = '<h2 style="color: #4a90e2; text-align: center; margin-top: 30px;"><i class="fa fa-sitemap" style="margin-right: 10px;"></i>Helpdesk View</h2>'
#
#             if not record.team_id:
#                 # Show all teams
#                 hierarchy_html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">'
#                 for team in teams.sorted('name'):
#                     team_tickets = tickets.filtered(lambda t: t.team_id == team)
#                     team_open = len(team_tickets.filtered(lambda t: not t.stage_id.closing_stage and not t.stage_id.cancel_stage))
#                     hierarchy_html += f"""
#                     <div style="background: linear-gradient(to bottom, #ffffff, #f0f4f8); padding: 15px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); text-align: center;">
#                         <i class="fa fa-users fa-2x" style="color: #4a90e2; margin-bottom: 10px;"></i>
#                         <strong style="font-size: 18px; color: #333;">{team.name or 'Unnamed'}</strong><br>
#                         <span style="color: #666;">Leader: {team.team_lead_id.name or 'N/A'} | Members: {len(team.member_ids)} | Tickets: {len(team_tickets)} (Open: {team_open})</span>
#                     </div>
#                     """
#                 hierarchy_html += '</div>'
#             elif not record.ticket_id:
#                 # Show tickets in selected team
#                 team = record.team_id
#                 team_tickets = tickets.filtered(lambda t: t.team_id == team).sorted('name')
#                 hierarchy_html += f'<h3 style="text-align: center; color: #50c878;"><i class="fa fa-users" style="margin-right: 5px;"></i>Selected Team: {team.name}</h3>'
#                 hierarchy_html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px;">'
#                 for ticket in team_tickets:
#                     priority_icon = 'fa-star' if ticket.priority in ['3', '4'] else 'fa-star-o'
#                     priority_color = 'red' if ticket.priority in ['3', '4'] else 'green'
#                     status_text = 'Open' if not ticket.stage_id.closing_stage and not ticket.stage_id.cancel_stage else ('Closed' if ticket.stage_id.closing_stage else 'Cancelled')
#                     status_color = 'green' if status_text == 'Open' else ('blue' if status_text == 'Closed' else 'red')
#                     hierarchy_html += f"""
#                     <div style="background: linear-gradient(to bottom, #ffffff, #f0f4f8); padding: 15px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); text-align: center;">
#                         <i class="fa fa-ticket fa-2x" style="color: #50c878; margin-bottom: 10px;"></i>
#                         <strong style="font-size: 18px; color: #333;">{ticket.name or 'Unnamed'}</strong><br>
#                         <span style="color: #666;">Subject: {ticket.subject[:50] + '...' if ticket.subject else 'N/A'}</span><br>
#                         <span style="font-weight: bold; color: {status_color};">{status_text}</span> |
#                         <i class="fa {priority_icon}" style="color: {priority_color};"></i> Priority: {ticket.priority}
#                     </div>
#                     """
#                 hierarchy_html += '</div>'
#             else:
#                 # Show detailed view for selected ticket
#                 ticket = record.ticket_id
#                 customer = ticket.customer_id
#                 stage = ticket.stage_id
#                 priority_text = dict(PRIORITIES).get(ticket.priority, 'N/A')
#                 rating_text = dict(RATING).get(ticket.priority, 'N/A')  # Assuming priority used for rating, adjust if needed
#
#                 hierarchy_html += f'<h3 style="text-align: center; color: #e94e77;"><i class="fa fa-ticket" style="margin-right: 5px;"></i>Selected Ticket: {ticket.name} (in Team: {ticket.team_id.name})</h3>'
#                 hierarchy_html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">'
#
#                 # Customer Card
#                 hierarchy_html += f"""
#                 <div style="background: linear-gradient(to bottom, #ffffff, #f0f4f8); padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
#                     <h4 style="color: #50c878; margin-bottom: 10px;"><i class="fa fa-user" style="margin-right: 5px;"></i>Customer Details</h4>
#                     <p><strong>Name:</strong> {customer.name or 'N/A'}</p>
#                     <p><strong>Email:</strong> {ticket.email or customer.email or 'N/A'}</p>
#                     <p><strong>Phone:</strong> {ticket.phone or customer.phone or 'N/A'}</p>
#                 </div>
#                 """
#
#                 # Ticket Details Card
#                 hierarchy_html += f"""
#                 <div style="background: linear-gradient(to bottom, #ffffff, #f0f4f8); padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
#                     <h4 style="color: #f5a623; margin-bottom: 10px;"><i class="fa fa-info-circle" style="margin-right: 5px;"></i>Ticket Details</h4>
#                     <p><strong>Subject:</strong> {ticket.subject or 'N/A'}</p>
#                     <p><strong>Description:</strong> {ticket.description[:200] + '...' if ticket.description else 'N/A'}</p>
#                     <p><strong>Stage:</strong> {stage.name or 'N/A'}</p>
#                     <p><strong>Priority:</strong> {priority_text}</p>
#                     <p><strong>Rating:</strong> {rating_text}</p>
#                     <p><strong>Created:</strong> {ticket.create_date.strftime('%Y-%m-%d %H:%M') if ticket.create_date else 'N/A'}</p>
#                     <p><strong>Last Replied:</strong> {ticket.replied_date.strftime('%Y-%m-%d %H:%M') if ticket.replied_date else 'N/A'}</p>
#                 </div>
#                 """
#
#                 # Related Items Card
#                 hierarchy_html += f"""
#                 <div style="background: linear-gradient(to bottom, #ffffff, #f0f4f8); padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
#                     <h4 style="color: #e94e77; margin-bottom: 10px;"><i class="fa fa-link" style="margin-right: 5px;"></i>Related Items</h4>
#                     <p><strong>Tasks:</strong> {len(ticket.task_ids)}</p>
#                     <p><strong>Invoices:</strong> {len(ticket.invoice_ids)}</p>
#                     <p><strong>Products:</strong> {', '.join(ticket.product_ids.mapped('name')) or 'None'}</p>
#                     <p><strong>Ticket Type:</strong> {ticket.ticket_type_id.name or 'N/A'}</p>
#                 </div>
#                 """
#
#                 hierarchy_html += '</div>'
#
#             final_html = html_content.format(summary_html=summary_html, hierarchy_html=hierarchy_html)
#             record.dashboard_html = final_html
#
#     @api.onchange('team_id')
#     def _onchange_team_id(self):
#         self.ticket_id = False
#
#     def action_refresh_dashboard(self):
#         self.write({'last_refresh': fields.Datetime.now()})
#         return True