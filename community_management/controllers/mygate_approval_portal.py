from odoo import http, fields
from odoo.http import request, Response
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
import logging
import qrcode
from io import BytesIO
import base64

_logger = logging.getLogger(__name__)


class MyGatePortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super()._prepare_portal_layout_values()
        # Get current user
        user = request.env.user

        # Find the tenant/partner associated with this user
        partner = user.partner_id

        # Get all visitors for flats where this partner is the tenant
        domain = [
            ('tenant_id', '=', partner.id),
            ('state', '=', 'pending')
        ]

        values['pending_visitors_count'] = request.env['mygate.visitor'].search_count(domain)
        return values

    @http.route(['/my/visitors', '/my/visitors/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_visitors(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        Visitor = request.env['mygate.visitor']

        # Get current user's partner
        user = request.env.user
        partner = user.partner_id

        # Domain for current user's visitors - based on tenant (partner)
        domain = [('tenant_id', '=', partner.id)]

        # Handle state filter from URL
        state_filter = kw.get('state')
        if state_filter:
            if state_filter == 'pending':
                domain.append(('state', '=', 'pending'))
            elif state_filter == 'approved':
                domain.append(('state', '=', 'approved'))
            elif state_filter == 'completed':
                domain.append(('state', 'in', ['completed', 'rejected', 'cancelled']))

        # Search visitors
        searchbar_sortings = {
            'date': {'label': 'Newest', 'order': 'create_date desc'},
            'name': {'label': 'Name', 'order': 'name asc'},
            'arrival': {'label': 'Arrival Time', 'order': 'expected_arrival asc'},
        }

        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # Count for pager
        visitor_count = Visitor.search_count(domain)

        # Pager
        pager = portal_pager(
            url="/my/visitors",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'state': state_filter},
            total=visitor_count,
            page=page,
            step=self._items_per_page
        )

        # Get visitors
        visitors = Visitor.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        # Group visitors by status (only if no filter applied)
        pending_visitors = visitors.filtered(lambda v: v.state == 'pending')
        approved_visitors = visitors.filtered(lambda v: v.state == 'approved')
        history_visitors = visitors.filtered(lambda v: v.state in ['completed', 'rejected', 'cancelled'])

        values.update({
            'visitors': visitors,
            'pending_visitors': pending_visitors,
            'approved_visitors': approved_visitors,
            'history_visitors': history_visitors,
            'page_name': 'visitors',
            'default_url': '/my/visitors',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'today': fields.Date.today(),
            'active_filter': state_filter,  # Add this to track active filter
        })

        return request.render("community_management.portal_my_visitors", values)



    @http.route(['/my/visitors/<int:visitor_id>'], type='http', auth="user", website=True)
    def portal_visitor_detail(self, visitor_id, access_token=None, **kw):
        try:
            visitor_sudo = self._document_check_access('mygate.visitor', visitor_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my/visitors')

        # Generate QR code if not exists
        if visitor_sudo.state == 'approved' and not visitor_sudo.qr_code:
            visitor_sudo._generate_qr_code()

        values = {
            'visitor': visitor_sudo,
            'page_name': 'visitor_detail',
        }
        return request.render("community_management.portal_visitor_detail", values)

    @http.route(['/my/visitors/<int:visitor_id>/approve'], type='http', auth="user", website=True)
    def portal_approve_visitor(self, visitor_id, **kw):
        try:
            visitor_sudo = self._document_check_access('mygate.visitor', visitor_id)
        except (AccessError, MissingError):
            return request.redirect('/my/visitors')

        try:
            visitor_sudo.action_approve()
            # Send success message
            request.env['bus.bus']._sendone(
                request.env.user.partner_id,
                'web.notify',
                {
                    'type': 'success',
                    'title': 'Success!',
                    'message': 'Visitor has been approved successfully.',
                }
            )
        except Exception as e:
            _logger.error(f"Error approving visitor: {e}")
            request.env['bus.bus']._sendone(
                request.env.user.partner_id,
                'web.notify',
                {
                    'type': 'danger',
                    'title': 'Error!',
                    'message': 'Failed to approve visitor.',
                }
            )

        return request.redirect('/my/visitors')

    @http.route(['/my/visitors/<int:visitor_id>/reject'], type='http', auth="user", website=True)
    def portal_reject_visitor(self, visitor_id, **kw):
        try:
            visitor_sudo = self._document_check_access('mygate.visitor', visitor_id)
        except (AccessError, MissingError):
            return request.redirect('/my/visitors')

        try:
            visitor_sudo.action_reject()
            # Send success message
            request.env['bus.bus']._sendone(
                request.env.user.partner_id,
                'web.notify',
                {
                    'type': 'success',
                    'title': 'Success!',
                    'message': 'Visitor has been rejected successfully.',
                }
            )
        except Exception as e:
            _logger.error(f"Error rejecting visitor: {e}")
            request.env['bus.bus']._sendone(
                request.env.user.partner_id,
                'web.notify',
                {
                    'type': 'danger',
                    'title': 'Error!',
                    'message': 'Failed to reject visitor.',
                }
            )

        return request.redirect('/my/visitors')

    @http.route(['/mygate/create'], type='http', auth="public", website=True, csrf=False)
    def portal_create_visitor(self, **post):
        """Public endpoint for gate security to create visitor requests"""
        if request.httprequest.method == 'POST':
            try:
                flat_number = post.get('flat_number')
                visitor_name = post.get('visitor_name')
                mobile = post.get('mobile')
                company = post.get('company')

                if not all([flat_number, visitor_name, mobile]):
                    return request.render("community_management.mygate_create_error", {
                        'error': 'Please fill all required fields'
                    })

                # Get flat from flat number
                flat = request.env['flat.management'].search([
                    ('name', '=', flat_number),
                    ('status', '=', 'occupied')
                ], limit=1)

                if not flat:
                    return request.render("community_management.mygate_create_error", {
                        'error': 'Flat not found or not occupied'
                    })

                # Create visitor record
                visitor = request.env['mygate.visitor'].sudo().create({
                    'name': visitor_name,
                    'mobile': mobile,
                    'company': company,
                    'flat_id': flat.id,
                    'visitor_type': post.get('visitor_type', 'guest'),
                    'purpose': post.get('purpose', ''),
                    'vehicle_number': post.get('vehicle_number', ''),
                    'visitor_count': int(post.get('visitor_count', 1)),
                    'expected_arrival': post.get('expected_arrival') or fields.Datetime.now(),
                    'security_guard_id': request.env.user.id if request.env.user and request.env.user.has_group(
                        'community_management.group_community_security_guard') else False,
                })
                image_data = post.get('visitor_image')
                if image_data:
                    # Handle base64 image upload (remove data:image/... prefix if present)
                    visitor['visitor_image'] = image_data.split(',')[1] if ',' in image_data else image_data

                # Create visitor record
                visitor = request.env['mygate.visitor'].sudo().create(visitor)

                # Confirm the request - this will send notification to tenant
                visitor.action_confirm_request()

                return request.redirect(f'/mygate/success/{visitor.access_code}')

            except Exception as e:
                _logger.error(f"Error creating visitor: {e}")
                return request.render("community_management.mygate_create_error", {
                    'error': str(e)
                })

        # GET request - show form
        values = {
            'visitor_types': [
                {'id': 'guest', 'name': 'Guest', 'icon': 'fa-user'},
                {'id': 'delivery', 'name': 'Delivery', 'icon': 'fa-truck'},
                {'id': 'service', 'name': 'Service Provider', 'icon': 'fa-wrench'},
                {'id': 'cab', 'name': 'Cab/Taxi', 'icon': 'fa-taxi'},
                {'id': 'other', 'name': 'Other', 'icon': 'fa-question'},
            ]
        }

        return request.render("community_management.mygate_create_form", values)

    @http.route(['/mygate/success/<string:access_code>'], type='http', auth="public", website=True)
    def portal_visitor_success(self, access_code, **kw):
        visitor = request.env['mygate.visitor'].sudo().search([
            ('access_code', '=', access_code)
        ], limit=1)

        if not visitor:
            return request.redirect('/mygate/create')

        values = {
            'visitor': visitor,
            'access_code': access_code,
        }
        return request.render("community_management.mygate_success_page", values)

    @http.route(['/mygate/qr/<string:access_code>'], type='http', auth="public")
    def generate_qr_code(self, access_code, **kwargs):
        """Generate QR code image"""
        try:
            visitor = request.env['mygate.visitor'].sudo().search([
                ('access_code', '=', access_code)
            ], limit=1)

            if not visitor:
                return Response("Visitor not found", status=404)

            # Generate QR code
            qr_data = f"VISITOR:{visitor.name}:{visitor.access_code}:{visitor.flat_id.name}"
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="#2c3e50", back_color="white")

            # Save to response
            buffered = BytesIO()
            img.save(buffered, format="PNG")

            return Response(
                buffered.getvalue(),
                mimetype='image/png',
                headers=[('Cache-Control', 'no-cache, no-store, must-revalidate'),
                         ('Pragma', 'no-cache'),
                         ('Expires', '0')]
            )

        except Exception as e:
            _logger.error(f"Error generating QR code: {e}")
            return Response("Error generating QR code", status=500)

    @http.route(['/mygate/verify'], type='http', auth="public", website=True, csrf=False)
    def verify_access_code(self, **post):
        """Verify access code at gate"""
        access_code = post.get('access_code')
        if not access_code:
            return request.render("community_management.mygate_verify_form", {})

        visitor = request.env['mygate.visitor'].sudo().search([
            ('access_code', '=', access_code),
            ('state', '=', 'approved'),
        ], limit=1)

        current_time = fields.Datetime.now()
        is_valid = visitor and visitor.valid_until and visitor.valid_until >= current_time

        values = {
            'visitor': visitor,
            'is_valid': is_valid,
            'access_code': access_code,
            'current_time': current_time,
        }

        return request.render("community_management.mygate_verify_result", values)