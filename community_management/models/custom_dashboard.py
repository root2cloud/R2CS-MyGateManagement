# File: custom_dashboard.py
from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class CustomDashboard(models.TransientModel):
    _name = 'custom.dashboard'
    _description = 'Custom Management Dashboard'

    # Customer Inquiry Stats
    total_inquiries = fields.Integer(string=" Total Inquiries", compute="_compute_dashboard_data")
    new_inquiries = fields.Integer(string=" New Inquiries", compute="_compute_dashboard_data")
    in_progress_inquiries = fields.Integer(string=" In Progress", compute="_compute_dashboard_data")
    resolved_inquiries = fields.Integer(string=" Resolved", compute="_compute_dashboard_data")
    closed_inquiries = fields.Integer(string=" Closed", compute="_compute_dashboard_data")

    # Resident Access Request Stats
    total_access_requests = fields.Integer(string=" Total Requests", compute="_compute_dashboard_data")
    draft_requests = fields.Integer(string=" Draft", compute="_compute_dashboard_data")
    pending_requests = fields.Integer(string=" Pending", compute="_compute_dashboard_data")
    approved_requests = fields.Integer(string=" Approved", compute="_compute_dashboard_data")
    rejected_requests = fields.Integer(string=" Rejected", compute="_compute_dashboard_data")

    # Community Post Stats
    total_posts = fields.Integer(string=" Total Posts", compute="_compute_dashboard_data")
    active_posts = fields.Integer(string=" Active Posts", compute="_compute_dashboard_data")
    total_likes = fields.Integer(string=" Total Likes", compute="_compute_dashboard_data")
    total_comments = fields.Integer(string=" Total Comments", compute="_compute_dashboard_data")
    total_views = fields.Integer(string=" Total Views", compute="_compute_dashboard_data")

    # Amenity Booking Stats
    total_bookings = fields.Integer(string=" Total Bookings", compute="_compute_dashboard_data")
    pending_bookings = fields.Integer(string=" Pending", compute="_compute_dashboard_data")
    approved_bookings = fields.Integer(string=" Approved", compute="_compute_dashboard_data")
    cancelled_bookings = fields.Integer(string=" Cancelled", compute="_compute_dashboard_data")
    free_amenities = fields.Integer(string=" Free Amenities", compute="_compute_dashboard_data")
    paid_amenities = fields.Integer(string=" Paid Amenities", compute="_compute_dashboard_data")

    # Notice Board Stats
    total_notices = fields.Integer(string=" Total Notices", compute="_compute_dashboard_data")
    society_notices = fields.Integer(string=" Society", compute="_compute_dashboard_data")
    event_notices = fields.Integer(string=" Event", compute="_compute_dashboard_data")
    emergency_notices = fields.Integer(string=" Emergency", compute="_compute_dashboard_data")
    promotion_notices = fields.Integer(string=" Promotion", compute="_compute_dashboard_data")
    active_notices = fields.Integer(string=" Active Notices", compute="_compute_dashboard_data")

    # Recent Data
    recent_inquiries = fields.Html(string="Recent Inquiries", compute="_compute_recent_data")
    recent_requests = fields.Html(string="Recent Requests", compute="_compute_recent_data")
    recent_posts = fields.Html(string="Recent Posts", compute="_compute_recent_data")
    recent_bookings = fields.Html(string="Recent Bookings", compute="_compute_recent_data")
    recent_notices = fields.Html(string="Recent Notices", compute="_compute_recent_data")

    @api.depends()
    def _compute_dashboard_data(self):
        """Compute all dashboard statistics"""
        for dashboard in self:
            try:
                # Customer Inquiry Stats
                inquiry_obj = self.env['customer.inquiry']
                dashboard.total_inquiries = inquiry_obj.search_count([])

                # Manually count statuses instead of using read_group
                dashboard.new_inquiries = inquiry_obj.search_count([('status', '=', 'new')])
                dashboard.in_progress_inquiries = inquiry_obj.search_count([('status', '=', 'in_progress')])
                dashboard.resolved_inquiries = inquiry_obj.search_count([('status', '=', 'resolved')])
                dashboard.closed_inquiries = inquiry_obj.search_count([('status', '=', 'closed')])

                # Resident Access Request Stats
                request_obj = self.env['resident.access.request']
                dashboard.total_access_requests = request_obj.search_count([])

                # Manually count states to avoid read_group issues
                dashboard.draft_requests = request_obj.search_count([('state', '=', 'draft')])
                dashboard.pending_requests = request_obj.search_count([('state', '=', 'pending')])
                dashboard.approved_requests = request_obj.search_count([('state', '=', 'approved')])
                dashboard.rejected_requests = request_obj.search_count([('state', '=', 'rejected')])

                # Community Post Stats
                post_obj = self.env['community.post']
                dashboard.total_posts = post_obj.search_count([])
                dashboard.active_posts = post_obj.search_count([('active', '=', True)])

                like_obj = self.env['community.post.like']
                dashboard.total_likes = like_obj.search_count([])

                comment_obj = self.env['community.post.comment']
                dashboard.total_comments = comment_obj.search_count([('active', '=', True)])

                view_obj = self.env['community.post.view']
                dashboard.total_views = view_obj.search_count([])

                # Amenity Booking Stats
                booking_obj = self.env['community.amenity.booking']
                dashboard.total_bookings = booking_obj.search_count([])

                # Manually count booking states
                dashboard.pending_bookings = booking_obj.search_count([('state', '=', 'pending')])
                dashboard.approved_bookings = booking_obj.search_count([('state', '=', 'approved')])
                dashboard.cancelled_bookings = booking_obj.search_count([('state', '=', 'cancelled')])

                amenity_obj = self.env['community.amenity']
                dashboard.free_amenities = amenity_obj.search_count(
                    [('amenity_type', '=', 'free'), ('active', '=', True)])
                dashboard.paid_amenities = amenity_obj.search_count(
                    [('amenity_type', '=', 'paid'), ('active', '=', True)])

                # Notice Board Stats
                notice_obj = self.env['property.notice.board']
                dashboard.total_notices = notice_obj.search_count([])
                dashboard.active_notices = notice_obj.search_count([('active', '=', True)])

                # Manually count notice types
                dashboard.society_notices = notice_obj.search_count([('notice_type', '=', 'society')])
                dashboard.event_notices = notice_obj.search_count([('notice_type', '=', 'event')])
                dashboard.emergency_notices = notice_obj.search_count([('notice_type', '=', 'emergency')])
                dashboard.promotion_notices = notice_obj.search_count([('notice_type', '=', 'promotion')])

            except Exception as e:
                # Log error but don't crash the dashboard
                _logger.error(f"Error computing dashboard data: {e}")
                # Set default values
                dashboard.total_inquiries = 0
                dashboard.new_inquiries = 0
                dashboard.in_progress_inquiries = 0
                dashboard.resolved_inquiries = 0
                dashboard.closed_inquiries = 0
                dashboard.total_access_requests = 0
                dashboard.draft_requests = 0
                dashboard.pending_requests = 0
                dashboard.approved_requests = 0
                dashboard.rejected_requests = 0
                dashboard.total_posts = 0
                dashboard.active_posts = 0
                dashboard.total_likes = 0
                dashboard.total_comments = 0
                dashboard.total_views = 0
                dashboard.total_bookings = 0
                dashboard.pending_bookings = 0
                dashboard.approved_bookings = 0
                dashboard.cancelled_bookings = 0
                dashboard.free_amenities = 0
                dashboard.paid_amenities = 0
                dashboard.total_notices = 0
                dashboard.society_notices = 0
                dashboard.event_notices = 0
                dashboard.emergency_notices = 0
                dashboard.promotion_notices = 0
                dashboard.active_notices = 0

    @api.depends()
    def _compute_recent_data(self):
        """Compute recent data for display"""
        for dashboard in self:
            try:
                limit = 5

                # Recent Inquiries (last 30 days)
                recent_inquiries = self.env['customer.inquiry'].search([
                    ('inquiry_date', '>=', fields.Datetime.now() - timedelta(days=30))
                ], limit=limit, order='inquiry_date desc')

                inquiry_list = []
                for inquiry in recent_inquiries:
                    status_color = {
                        'new': 'text-primary',
                        'in_progress': 'text-warning',
                        'resolved': 'text-success',
                        'closed': 'text-secondary'
                    }.get(inquiry.status, '')
                    inquiry_list.append(
                        f"• {inquiry.name}: {inquiry.subject} <span class='{status_color}'>({inquiry.status})</span>")
                dashboard.recent_inquiries = "<br/>".join(inquiry_list) if inquiry_list else "No recent inquiries"

                # Recent Access Requests
                recent_requests = self.env['resident.access.request'].search([], limit=limit, order='create_date desc')
                request_list = []
                for request in recent_requests:
                    state_color = {
                        'draft': 'text-secondary',
                        'pending': 'text-warning',
                        'approved': 'text-success',
                        'rejected': 'text-danger'
                    }.get(request.state, '')
                    request_list.append(
                        f"• {request.name} - {request.flat_id.name if request.flat_id else 'N/A'} <span class='{state_color}'>({request.state})</span>")
                dashboard.recent_requests = "<br/>".join(request_list) if request_list else "No recent requests"

                # Recent Posts
                recent_posts = self.env['community.post'].search([
                    ('active', '=', True)
                ], limit=limit, order='create_date desc')
                post_list = []
                for post in recent_posts:
                    post_list.append(f"• {post.name} - 👍 {post.like_count} 💬 {post.comment_count}")
                dashboard.recent_posts = "<br/>".join(post_list) if post_list else "No recent posts"

                # Recent Bookings (future bookings)
                recent_bookings = self.env['community.amenity.booking'].search([
                    ('booking_date', '>=', fields.Date.today())
                ], limit=limit, order='booking_date asc')
                booking_list = []
                for booking in recent_bookings:
                    state_color = {
                        'pending': 'text-warning',
                        'approved': 'text-success',
                        'cancelled': 'text-danger'
                    }.get(booking.state, '')
                    booking_list.append(
                        f"• {booking.amenity_id.name if booking.amenity_id else 'N/A'} - {booking.booking_date} <span class='{state_color}'>({booking.state})</span>")
                dashboard.recent_bookings = "<br/>".join(booking_list) if booking_list else "No upcoming bookings"

                # Recent Notices (active and upcoming)
                recent_notices = self.env['property.notice.board'].search([
                    ('active', '=', True)
                ], limit=limit, order='date_start desc')
                notice_list = []
                for notice in recent_notices:
                    type_color = {
                        'society': 'text-primary',
                        'event': 'text-success',
                        'emergency': 'text-danger',
                        'promotion': 'text-warning'
                    }.get(notice.notice_type, '')
                    notice_list.append(f"• {notice.name} <span class='{type_color}'>({notice.notice_type})</span>")
                dashboard.recent_notices = "<br/>".join(notice_list) if notice_list else "No active notices"

            except Exception as e:
                # Log error but don't crash the dashboard
                _logger.error(f"Error computing recent data: {e}")
                dashboard.recent_inquiries = "Error loading data"
                dashboard.recent_requests = "Error loading data"
                dashboard.recent_posts = "Error loading data"
                dashboard.recent_bookings = "Error loading data"
                dashboard.recent_notices = "Error loading data"

    def action_refresh_dashboard(self):
        """Refresh dashboard data"""
        # Clear cache and recompute
        self._invalidate_cache()
        self._compute_dashboard_data()
        self._compute_recent_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_open_inquiries(self):
        """Open Customer Inquiries"""
        return {
            'name': 'Customer Inquiries',
            'type': 'ir.actions.act_window',
            'res_model': 'customer.inquiry',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [],
        }

    def action_open_access_requests(self):
        """Open Resident Access Requests"""
        return {
            'name': 'Resident Access Requests',
            'type': 'ir.actions.act_window',
            'res_model': 'resident.access.request',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [],
        }

    def action_open_community_posts(self):
        """Open Community Posts"""
        return {
            'name': 'Community Posts',
            'type': 'ir.actions.act_window',
            'res_model': 'community.post',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [],
        }

    def action_open_amenity_bookings(self):
        """Open Amenity Bookings"""
        return {
            'name': 'Amenity Bookings',
            'type': 'ir.actions.act_window',
            'res_model': 'community.amenity.booking',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [],
        }

    def action_open_notice_board(self):
        """Open Notice Board"""
        return {
            'name': 'Notice Board',
            'type': 'ir.actions.act_window',
            'res_model': 'property.notice.board',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [],
        }

    @api.model
    def action_open_dashboard(self):
        """Open dashboard action - creates a new transient record"""
        # Create a new transient record
        dashboard = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Custom Management Dashboard',
            'res_model': 'custom.dashboard',
            'res_id': dashboard.id,
            'view_mode': 'form',
            'target': 'current',
            'flags': {'mode': 'readonly'},
        }