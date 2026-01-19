# File: community_access_dashboard.py
from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class CommunityAccessDashboard(models.TransientModel):
    _name = 'community.access.dashboard'
    _description = 'Community Access & Guest Management Dashboard'

    # =====================
    # STATISTICS FIELDS
    # =====================

    # Visitor Request Stats (Added before Cab Approvals)
    total_visitor_requests = fields.Integer(string=" Total Visitor Requests", compute="_compute_dashboard_data")
    pending_visitor_requests = fields.Integer(string=" Pending Visitor Requests", compute="_compute_dashboard_data")
    approved_visitor_requests = fields.Integer(string=" Approved Visitors", compute="_compute_dashboard_data")
    completed_visitor_requests = fields.Integer(string=" Completed Visits", compute="_compute_dashboard_data")
    today_visitor_requests = fields.Integer(string=" Today's Visitors", compute="_compute_dashboard_data")

    # Cab Pre-Approval Stats
    total_cab_approvals = fields.Integer(string=" Total Cab Approvals", compute="_compute_dashboard_data")
    active_cab_approvals = fields.Integer(string=" Active Cab Approvals", compute="_compute_dashboard_data")
    once_cab_approvals = fields.Integer(string=" One-Time Cabs", compute="_compute_dashboard_data")
    frequent_cab_approvals = fields.Integer(string=" Frequent Cabs", compute="_compute_dashboard_data")

    # Delivery Pass Stats
    total_delivery_passes = fields.Integer(string=" Total Delivery Passes", compute="_compute_dashboard_data")
    active_delivery_passes = fields.Integer(string=" Active Delivery Passes", compute="_compute_dashboard_data")
    surprise_deliveries = fields.Integer(string=" Surprise Deliveries", compute="_compute_dashboard_data")
    gate_leave_deliveries = fields.Integer(string=" Leave at Gate", compute="_compute_dashboard_data")

    # Guest Invite Stats
    total_guest_invites = fields.Integer(string=" Total Guest Invites", compute="_compute_dashboard_data")
    active_guest_invites = fields.Integer(string=" Active Guest Invites", compute="_compute_dashboard_data")
    once_guest_invites = fields.Integer(string=" One-Time Guests", compute="_compute_dashboard_data")
    frequent_guest_invites = fields.Integer(string=" Frequent Guests", compute="_compute_dashboard_data")
    total_guests = fields.Integer(string=" Total Guests Count", compute="_compute_dashboard_data")

    # Party/Group Invite Stats
    total_party_invites = fields.Integer(string=" Party Invites", compute="_compute_dashboard_data")
    active_party_invites = fields.Integer(string=" Active Parties", compute="_compute_dashboard_data")
    upcoming_parties = fields.Integer(string=" Upcoming Parties", compute="_compute_dashboard_data")

    # Child
    # Exit
    # Permission
    # Stats
    total_child_exit_permissions = fields.Integer(string=" Total Exit Permissions", compute="_compute_dashboard_data")
    active_child_exit_permissions = fields.Integer(string=" Active Permissions", compute="_compute_dashboard_data")
    expired_child_exit_permissions = fields.Integer(string=" Expired Permissions", compute="_compute_dashboard_data")
    today_exit_permissions = fields.Integer(string=" Today's Permissions", compute="_compute_dashboard_data")

    # Visiting Help Stats
    total_visiting_help = fields.Integer(string=" Visiting Help", compute="_compute_dashboard_data")
    active_visiting_help = fields.Integer(string=" Active Help", compute="_compute_dashboard_data")
    once_visiting_help = fields.Integer(string=" One-Time Help", compute="_compute_dashboard_data")
    frequent_visiting_help = fields.Integer(string=" Frequent Help", compute="_compute_dashboard_data")

    # =====================
    # RECENT ACTIVITY FIELDS
    # =====================

    recent_visitor_requests = fields.Html(string="Recent Visitor Requests", compute="_compute_recent_data")
    recent_cab_approvals = fields.Html(string="Recent Cab Approvals", compute="_compute_recent_data")
    recent_delivery_passes = fields.Html(string="Recent Delivery Passes", compute="_compute_recent_data")
    recent_guest_invites = fields.Html(string="Recent Guest Invites", compute="_compute_recent_data")
    recent_party_invites = fields.Html(string="Recent Party Invites", compute="_compute_recent_data")
    recent_child_exit_permissions = fields.Html(string="Recent Exit Permissions", compute="_compute_recent_data")
    recent_visiting_help = fields.Html(string="Recent Visiting Help", compute="_compute_recent_data")

    # =====================
    # COMPUTE METHODS
    # =====================

    @api.depends()
    def _compute_dashboard_data(self):
        """Compute all dashboard statistics"""
        for dashboard in self:
            try:

                # Visitor Request Stats (Added before Cab Approvals)
                visitor_obj = self.env['mygate.visitor']
                dashboard.total_visitor_requests = visitor_obj.search_count([])
                dashboard.pending_visitor_requests = visitor_obj.search_count([('state', '=', 'pending')])
                dashboard.approved_visitor_requests = visitor_obj.search_count([('state', '=', 'approved')])
                dashboard.completed_visitor_requests = visitor_obj.search_count([('state', '=', 'completed')])

                # Today's visitors (expected arrival is today)
                today = fields.Date.today()
                tomorrow = today + timedelta(days=1)
                today_visitors = visitor_obj.search_count([
                    ('expected_arrival', '>=', fields.Datetime.to_string(today)),
                    ('expected_arrival', '<', fields.Datetime.to_string(tomorrow)),
                    ('state', 'in', ['pending', 'approved'])
                ])
                dashboard.today_visitor_requests = today_visitors

                # Cab Pre-Approval Stats
                cab_obj = self.env['cab.preapproval']
                dashboard.total_cab_approvals = cab_obj.search_count([])
                dashboard.active_cab_approvals = cab_obj.search_count([('state', '=', 'active')])
                dashboard.once_cab_approvals = cab_obj.search_count([('mode', '=', 'once')])
                dashboard.frequent_cab_approvals = cab_obj.search_count([('mode', '=', 'frequent')])

                # Delivery Pass Stats
                delivery_obj = self.env['community.delivery.pass']
                dashboard.total_delivery_passes = delivery_obj.search_count([])
                dashboard.active_delivery_passes = delivery_obj.search_count([('state', '=', 'active')])
                dashboard.surprise_deliveries = delivery_obj.search_count([('is_surprise', '=', True)])
                dashboard.gate_leave_deliveries = delivery_obj.search_count([('allow_leave_at_gate', '=', True)])

                # Guest Invite Stats
                guest_obj = self.env['guest.invite']
                dashboard.total_guest_invites = guest_obj.search_count([])
                dashboard.active_guest_invites = guest_obj.search_count([('state', '=', 'active')])
                dashboard.once_guest_invites = guest_obj.search_count([('invite_type', '=', 'once')])
                dashboard.frequent_guest_invites = guest_obj.search_count([('invite_type', '=', 'frequent')])

                # Total guests count
                guest_line_obj = self.env['guest.invite.line']
                dashboard.total_guests = guest_line_obj.search_count([])

                # Party/Group Invite Stats
                party_obj = self.env['party.group.invite']
                dashboard.total_party_invites = party_obj.search_count([])
                dashboard.active_party_invites = party_obj.search_count([('state', '=', 'active')])

                # Upcoming parties (next 7 days)
                today = fields.Date.today()
                next_week = today + timedelta(days=7)
                upcoming = party_obj.search_count([
                    ('event_date', '>=', today),
                    ('event_date', '<=', next_week),
                    ('state', 'in', ['configured', 'active'])
                ])
                dashboard.upcoming_parties = upcoming

                # CHILD EXIT PERMISSION STATS
                # =====================
                child_exit_obj = self.env['child.exit.permission']
                dashboard.total_child_exit_permissions = child_exit_obj.search_count([])
                dashboard.active_child_exit_permissions = child_exit_obj.search_count([('state', '=', 'active')])
                dashboard.expired_child_exit_permissions = child_exit_obj.search_count([('state', '=', 'expired')])

                # Today's permissions (created today)
                today_start = fields.Datetime.to_string(today)
                today_end = fields.Datetime.to_string(today + timedelta(days=1))
                today_exits = child_exit_obj.search_count([
                    ('create_date', '>=', today_start),
                    ('create_date', '<', today_end)
                ])
                dashboard.today_exit_permissions = today_exits

                # Visiting Help Stats
                help_obj = self.env['community.visiting.help.entry']
                dashboard.total_visiting_help = help_obj.search_count([])
                dashboard.active_visiting_help = help_obj.search_count([('state', '=', 'active')])
                dashboard.once_visiting_help = help_obj.search_count([('entry_type', '=', 'once')])
                dashboard.frequent_visiting_help = help_obj.search_count([('entry_type', '=', 'frequent')])

            except Exception as e:
                _logger.error(f"Error computing dashboard data: {e}")
                # Set default values
                dashboard.total_visitor_requests = 0
                dashboard.pending_visitor_requests = 0
                dashboard.approved_visitor_requests = 0
                dashboard.completed_visitor_requests = 0
                dashboard.today_visitor_requests = 0
                dashboard.total_cab_approvals = 0
                dashboard.active_cab_approvals = 0
                dashboard.once_cab_approvals = 0
                dashboard.frequent_cab_approvals = 0
                dashboard.total_delivery_passes = 0
                dashboard.active_delivery_passes = 0
                dashboard.surprise_deliveries = 0
                dashboard.gate_leave_deliveries = 0
                dashboard.total_guest_invites = 0
                dashboard.active_guest_invites = 0
                dashboard.once_guest_invites = 0
                dashboard.frequent_guest_invites = 0
                dashboard.total_guests = 0
                dashboard.total_party_invites = 0
                dashboard.active_party_invites = 0
                dashboard.upcoming_parties = 0
                dashboard.total_visiting_help = 0
                dashboard.active_visiting_help = 0
                dashboard.once_visiting_help = 0
                dashboard.frequent_visiting_help = 0
                dashboard.total_child_exit_permissions = 0
                dashboard.active_child_exit_permissions = 0
                dashboard.expired_child_exit_permissions = 0
                dashboard.today_exit_permissions = 0

    @api.depends()
    def _compute_recent_data(self):
        """Compute recent activity data"""
        for dashboard in self:
            try:
                limit = 5
                # Recent Visitor Requests (Added before Cab Approvals)
                recent_visitors = self.env['mygate.visitor'].search(
                    [], limit=limit, order='create_date desc'
                )
                visitor_list = []
                for visitor in recent_visitors:
                    state_color = {
                        'pending': 'text-warning',
                        'approved': 'text-success',
                        'rejected': 'text-danger',
                        'cancelled': 'text-muted',
                        'completed': 'text-info'
                    }.get(visitor.state, 'text-muted')

                    # Format visitor type with icon
                    visitor_type_icon = {
                        'guest': '👤',
                        'delivery': '🚚',
                        'service': '🔧',
                        'cab': '🚕',
                        'other': '📋'
                    }.get(visitor.visitor_type, '📋')

                    visitor_list.append(
                        f"• {visitor_type_icon} {visitor.name} - "
                        f"{visitor.flat_id.name if visitor.flat_id else 'N/A'} - "
                        f"<span class='{state_color}'>({visitor.state})</span>"
                    )
                dashboard.recent_visitor_requests = "<br/>".join(
                    visitor_list) if visitor_list else "No recent visitor requests"

                # Recent Cab Approvals
                recent_cabs = self.env['cab.preapproval'].search(
                    [], limit=limit, order='create_date desc'
                )
                cab_list = []
                for cab in recent_cabs:
                    mode_color = 'text-primary' if cab.mode == 'once' else 'text-warning'
                    state_color = {
                        'draft': 'text-secondary',
                        'active': 'text-success',
                        'expired': 'text-muted',
                        'cancelled': 'text-danger'
                    }.get(cab.state, 'text-muted')
                    cab_list.append(
                        f"• {cab.resident_id.name or 'N/A'} - <span class='{mode_color}'>{cab.mode}</span> "
                        f"<span class='{state_color}'>({cab.state})</span>"
                    )
                dashboard.recent_cab_approvals = "<br/>".join(cab_list) if cab_list else "No recent cab approvals"

                # Recent Delivery Passes
                recent_deliveries = self.env['community.delivery.pass'].search(
                    [], limit=limit, order='create_date desc'
                )
                delivery_list = []
                for delivery in recent_deliveries:
                    surprise = "🎁" if delivery.is_surprise else ""
                    gate = "🏠" if delivery.allow_leave_at_gate else ""
                    delivery_list.append(
                        f"• {delivery.resident_id.name or 'N/A'} {surprise} {gate}"
                    )
                dashboard.recent_delivery_passes = "<br/>".join(
                    delivery_list) if delivery_list else "No recent delivery passes"

                # Recent Guest Invites
                recent_guests = self.env['guest.invite'].search(
                    [], limit=limit, order='create_date desc'
                )
                guest_list = []
                for guest in recent_guests:
                    otp = f"🔐 {guest.otpcode}" if guest.otpcode else "🔐 N/A"
                    guest_count = len(guest.guest_line_ids)
                    guests = f"👥 {guest_count}" if guest_count > 0 else ""
                    guest_list.append(
                        f"• {guest.resident_id.name or 'N/A'} {otp} {guests}"
                    )
                dashboard.recent_guest_invites = "<br/>".join(guest_list) if guest_list else "No recent guest invites"

                # Recent Party Invites
                recent_parties = self.env['party.group.invite'].search(
                    [], limit=limit, order='create_date desc'
                )
                party_list = []
                for party in recent_parties:
                    date_str = f"📅 {party.event_date}" if party.event_date else ""
                    location = f"📍 {party.location[:15]}..." if party.location else ""
                    party_list.append(
                        f"• {party.host_id.name or 'N/A'} {date_str} {location}"
                    )
                dashboard.recent_party_invites = "<br/>".join(party_list) if party_list else "No recent party invites"

                # RECENT CHILD EXIT PERMISSIONS
                # =====================
                recent_exits = self.env['child.exit.permission'].search(
                    [], limit=limit, order='create_date desc'
                )
                exit_list = []
                for exit_perm in recent_exits:
                    state_color = {
                        'draft': 'text-secondary',
                        'active': 'text-success',
                        'expired': 'text-muted',
                        'used': 'text-info',
                        'cancelled': 'text-danger'
                    }.get(exit_perm.state, 'text-muted')

                    time_icon = "⏰" if exit_perm.is_active_now else "✅" if exit_perm.state == 'expired' else "📋"
                    child_icon = "👶" if exit_perm.child_age and exit_perm.child_age < 12 else "🧒"

                    exit_list.append(
                        f"• {child_icon} {exit_perm.child_id.name or 'N/A'} - "
                        f"{exit_perm.tenant_id.name or 'N/A'} - "
                        f"<span class='{state_color}'>{time_icon} ({exit_perm.state})</span>"
                    )
                dashboard.recent_child_exit_permissions = "<br/>".join(
                    exit_list) if exit_list else "No recent exit permissions"

                # Recent Visiting Help
                recent_help = self.env['community.visiting.help.entry'].search(
                    [], limit=limit, order='create_date desc'
                )
                help_list = []
                for help in recent_help:
                    category = help.category_id.name or "N/A"
                    help_list.append(
                        f"• {help.tenant_id.name or 'N/A'} - {category}"
                    )
                dashboard.recent_visiting_help = "<br/>".join(help_list) if help_list else "No recent visiting help"

            except Exception as e:
                _logger.error(f"Error computing recent data: {e}")
                dashboard.recent_visitor_requests = "Error loading data"
                dashboard.recent_cab_approvals = "Error loading data"
                dashboard.recent_delivery_passes = "Error loading data"
                dashboard.recent_guest_invites = "Error loading data"
                dashboard.recent_party_invites = "Error loading data"
                dashboard.recent_child_exit_permissions = "Error loading data"
                dashboard.recent_visiting_help = "Error loading data"

    # =====================
    # ACTION METHODS
    # =====================

    def action_refresh_dashboard(self):
        """Refresh dashboard data"""
        self._invalidate_cache()
        self._compute_dashboard_data()
        self._compute_recent_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_open_visitor_requests(self):
        """Open Visitor Requests"""
        return {
            'name': 'Visitor Requests',
            'type': 'ir.actions.act_window',
            'res_model': 'mygate.visitor',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [],
        }

    def action_open_cab_approvals(self):
        """Open Cab Pre-Approvals"""
        return {
            'name': 'Cab Pre-Approvals',
            'type': 'ir.actions.act_window',
            'res_model': 'cab.preapproval',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [],
        }

    def action_open_delivery_passes(self):
        """Open Delivery Passes"""
        return {
            'name': 'Delivery Passes',
            'type': 'ir.actions.act_window',
            'res_model': 'community.delivery.pass',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [],
        }

    def action_open_guest_invites(self):
        """Open Guest Invites"""
        return {
            'name': 'Guest Invites',
            'type': 'ir.actions.act_window',
            'res_model': 'guest.invite',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [],
        }

    def action_open_party_invites(self):
        """Open Party Invites"""
        return {
            'name': 'Party Invites',
            'type': 'ir.actions.act_window',
            'res_model': 'party.group.invite',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [],
        }

    # Add this action method after action_open_party_invites
    def action_open_child_exit_permissions(self):
        """Open Child Exit Permissions"""
        return {
            'name': 'Child Exit Permissions',
            'type': 'ir.actions.act_window',
            'res_model': 'child.exit.permission',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [],
        }

    def action_open_visiting_help(self):
        """Open Visiting Help"""
        return {
            'name': 'Visiting Help',
            'type': 'ir.actions.act_window',
            'res_model': 'community.visiting.help.entry',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [],
        }

    @api.model
    def action_open_dashboard(self):
        """Open dashboard action"""
        dashboard = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Community Access Dashboard',
            'res_model': 'community.access.dashboard',
            'res_id': dashboard.id,
            'view_mode': 'form',
            'target': 'current',
            'flags': {'mode': 'readonly'},
        }
