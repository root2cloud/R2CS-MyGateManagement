# File: child_exit_permission_controllers.py
from odoo import http
from odoo.http import request
import json
from datetime import datetime, timedelta
import random


class ChildExitPermissionController(http.Controller):

    # ====================
    # PORTAL/WEBSITE ROUTES
    # ====================

    @http.route('/my/child-exit-permissions', type='http', auth='user', website=True)
    def portal_my_permissions(self, **kwargs):
        """Portal page for parents to view their child exit permissions"""
        # Get permissions for this parent
        permissions = request.env['child.exit.permission'].search([
            ('tenant_id', '=', request.env.user.partner_id.id)
        ], order='create_date desc')

        values = {
            'permissions': permissions,
            'page_name': 'child_exit_permissions',
            'user': request.env.user,
        }
        return request.render('community_management.portal_my_child_exit_permissions', values)

    @http.route('/my/child-exit-permissions/<int:permission_id>', type='http', auth='user', website=True)
    def portal_permission_detail(self, permission_id, **kwargs):
        """Portal page for specific permission details"""
        permission = request.env['child.exit.permission'].browse(permission_id)

        # Check access rights
        if not permission._portal_can_access():
            return request.redirect('/my/child-exit-permissions')

        values = {
            'permission': permission,
            'page_name': 'child_exit_permission_detail',
            'user': request.env.user,
        }
        return request.render('community_management.portal_child_exit_permission_detail', values)

    @http.route('/my/child-exit-permissions/create', type='http', auth='user', website=True)
    def portal_create_permission(self, **kwargs):
        """Portal page to create new permission"""
        from datetime import datetime

        # Get children for this parent
        children = request.env['family.member'].search([
            ('tenant_id', '=', request.env.user.partner_id.id),
            ('member_type', '=', 'child')
        ])

        values = {
            'children': children,
            'page_name': 'create_child_exit_permission',
            'user': request.env.user,
            'today_date': datetime.now().strftime('%Y-%m-%d'),  # Pass today's date
            'current_time': datetime.now().strftime('%H:%M'),  # Pass current time
        }
        return request.render('community_management.portal_create_child_exit_permission', values)

    # ====================
    # TRADITIONAL FORM SUBMISSION (CSRF Protected)
    # ====================

    @http.route('/my/child-exit-permissions/create/submit', type='http', auth='user', methods=['POST'], website=True,
                csrf=True)
    def portal_create_permission_submit(self, **post):
        """Traditional form submission handler with CSRF protection"""
        try:
            child_id = post.get('child_id')
            duration = post.get('duration')
            purpose = post.get('purpose')
            exit_date = post.get('exit_date')
            exit_time = post.get('exit_time')

            # Validate required fields
            if not child_id:
                return request.redirect('/my/child-exit-permissions/create?error=Please select a child')

            if not duration:
                return request.redirect('/my/child-exit-permissions/create?error=Please select duration')

            if not purpose or purpose.strip() == '':
                return request.redirect('/my/child-exit-permissions/create?error=Please enter purpose/reason')

            if not exit_date:
                return request.redirect('/my/child-exit-permissions/create?error=Please select exit date')

            if not exit_time:
                return request.redirect('/my/child-exit-permissions/create?error=Please select exit time')

            # Get child record
            child = request.env['family.member'].browse(int(child_id))
            if not child.exists():
                return request.redirect('/my/child-exit-permissions/create?error=Child not found')

            # Check if user has permission for this child
            if child.tenant_id.id != request.env.user.partner_id.id:
                return request.redirect(
                    '/my/child-exit-permissions/create?error=You do not have permission for this child')

            # Parse exit datetime
            try:
                exit_datetime_str = f"{exit_date} {exit_time}"
                allowed_exit_time = datetime.strptime(exit_datetime_str, '%Y-%m-%d %H:%M')

                # Validate exit time is not in the past
                current_time = datetime.now()
                if allowed_exit_time < current_time:
                    return request.redirect('/my/child-exit-permissions/create?error=Exit time cannot be in the past')

            except ValueError:
                return request.redirect('/my/child-exit-permissions/create?error=Invalid date/time format')

            # Calculate valid until based on duration
            duration_hours = int(duration)
            valid_until = allowed_exit_time + timedelta(hours=duration_hours)

            # Generate access code
            access_code = str(random.randint(100000, 999999))

            # Create permission record
            permission = request.env['child.exit.permission'].create({
                'child_id': child.id,
                'tenant_id': child.tenant_id.id,
                'flat_id': child.tenant_id.flat_id.id if child.tenant_id.flat_id else False,
                'duration_hours': str(duration_hours),
                'custom_duration_hours': duration_hours,
                'allowed_exit_time': allowed_exit_time,
                'valid_until': valid_until,
                'purpose': purpose.strip(),
                'access_code': access_code,
                'state': 'active',
            })

            # Return success message with access code
            success_msg = f"Permission created successfully! Access Code: {access_code}"
            return request.redirect(f'/my/child-exit-permissions?success={success_msg}')

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error creating permission: {error_details}")
            return request.redirect(f'/my/child-exit-permissions/create?error={str(e)}')

    # ====================
    # JSON API ROUTES (for AJAX if needed)
    # ====================

    @http.route('/api/child-exit/create-permission', type='json', auth='user', methods=['POST'])
    def api_create_permission(self, child_id=None, duration='2', purpose='', exit_date=None, exit_time=None, **kwargs):
        """API to create exit permission from portal"""
        try:
            # Validate required fields
            if not child_id:
                return {
                    'success': False,
                    'error': 'Please select a child'
                }

            if not duration:
                return {
                    'success': False,
                    'error': 'Please select duration'
                }

            if not purpose or purpose.strip() == '':
                return {
                    'success': False,
                    'error': 'Please enter purpose/reason'
                }

            if not exit_date:
                return {
                    'success': False,
                    'error': 'Please select exit date'
                }

            if not exit_time:
                return {
                    'success': False,
                    'error': 'Please select exit time'
                }

            # Get child record
            child = request.env['family.member'].browse(int(child_id))
            if not child.exists():
                return {
                    'success': False,
                    'error': 'Child not found'
                }

            # Check if user has permission for this child
            if child.tenant_id.id != request.env.user.partner_id.id:
                return {
                    'success': False,
                    'error': 'You do not have permission for this child'
                }

            # Parse exit datetime
            try:
                exit_datetime_str = f"{exit_date} {exit_time}"
                allowed_exit_time = datetime.strptime(exit_datetime_str, '%Y-%m-%d %H:%M')

                # Validate exit time is not in the past
                current_time = datetime.now()
                if allowed_exit_time < current_time:
                    return {
                        'success': False,
                        'error': 'Exit time cannot be in the past'
                    }

            except ValueError:
                return {
                    'success': False,
                    'error': 'Invalid date/time format'
                }

            # Calculate valid until based on duration
            duration_hours = int(duration)
            valid_until = allowed_exit_time + timedelta(hours=duration_hours)

            # Generate access code
            access_code = str(random.randint(100000, 999999))

            # Create permission record
            permission = request.env['child.exit.permission'].create({
                'child_id': child.id,
                'tenant_id': child.tenant_id.id,
                'flat_id': child.flat_id.id if child.flat_id else False,
                'duration_hours': str(duration_hours),
                'custom_duration_hours': duration_hours,
                'allowed_exit_time': allowed_exit_time,
                'valid_until': valid_until,
                'purpose': purpose.strip(),
                'access_code': access_code,
                'state': 'active',
            })

            # Return success response
            return {
                'success': True,
                'data': {
                    'id': permission.id,
                    'access_code': permission.access_code,
                    'child_name': permission.child_id.name,
                    'child_age': permission.child_age,
                    'allowed_exit_time': permission.allowed_exit_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'valid_until': permission.valid_until.strftime('%Y-%m-%d %H:%M:%S'),
                    'purpose': permission.purpose,
                    'duration': permission.duration_hours
                }
            }

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"API Error creating permission: {error_details}")
            return {
                'success': False,
                'error': str(e)
            }

    # ====================
    # SECURITY/API ROUTES
    # ====================

    @http.route('/api/child-exit/verify/<string:access_code>', type='http', auth='public', methods=['GET'], csrf=False)
    def api_verify_permission(self, access_code, **kwargs):
        """Public API to verify a permission by access code (for security guards)"""
        try:
            permission = request.env['child.exit.permission'].search([
                ('access_code', '=', access_code),
                ('state', '=', 'active')
            ], limit=1)

            if permission:
                response = {
                    'success': True,
                    'data': {
                        'child_name': permission.child_id.name,
                        'child_age': permission.child_age,
                        'parent_name': permission.tenant_id.name,
                        'flat_number': permission.flat_id.name if permission.flat_id else 'N/A',
                        'allowed_exit_time': permission.allowed_exit_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'valid_until': permission.valid_until.strftime('%Y-%m-%d %H:%M:%S'),
                        'time_remaining': permission.time_remaining,
                        'purpose': permission.purpose,
                        'permission_id': permission.id
                    }
                }
                return json.dumps(response)
            else:
                return json.dumps({
                    'success': False,
                    'error': 'Permission not found or expired'
                })

        except Exception as e:
            return json.dumps({
                'success': False,
                'error': str(e)
            })

    @http.route('/api/child-exit/mark-exited/<string:access_code>', type='json', auth='public', methods=['POST'],
                csrf=False)
    def api_mark_exited(self, access_code, **kwargs):
        """API to mark child as exited"""
        try:
            permission = request.env['child.exit.permission'].search([
                ('access_code', '=', access_code),
                ('state', '=', 'active')
            ], limit=1)

            if permission:
                permission.action_mark_exited()
                return {
                    'success': True,
                    'message': f'{permission.child_id.name} marked as exited'
                }
            else:
                return {
                    'success': False,
                    'error': 'Permission not found'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/child-exit/mark-returned/<string:access_code>', type='json', auth='public', methods=['POST'],
                csrf=False)
    def api_mark_returned(self, access_code, **kwargs):
        """API to mark child as returned"""
        try:
            permission = request.env['child.exit.permission'].search([
                ('access_code', '=', access_code),
                ('state', '=', 'used')
            ], limit=1)

            if permission:
                permission.action_mark_returned()
                return {
                    'success': True,
                    'message': f'{permission.child_id.name} marked as returned'
                }
            else:
                return {
                    'success': False,
                    'error': 'Permission not found or not exited yet'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    # ====================
    # DASHBOARD/QUICK ACTIONS
    # ====================

    @http.route('/api/child-exit/quick-create', type='json', auth='user', methods=['POST'])
    def api_quick_create(self, **kwargs):
        """Quick create permission from dashboard - For backward compatibility"""
        # This redirects to the main create API
        return self.api_create_permission(**kwargs)

    @http.route('/widget/child-exit/active-permissions', type='json', auth='user')
    def widget_active_permissions(self, **kwargs):
        """Get active permissions for dashboard widget"""
        try:
            domain = [('state', '=', 'active'), ('is_active_now', '=', True)]

            # If portal user, only show their permissions
            if request.env.user.has_group('base.group_portal'):
                domain.append(('tenant_id', '=', request.env.user.partner_id.id))

            permissions = request.env['child.exit.permission'].search(domain, limit=10)

            data = []
            for perm in permissions:
                data.append({
                    'id': perm.id,
                    'child_name': perm.child_id.name,
                    'child_age': perm.child_age,
                    'time_remaining': perm.time_remaining,
                    'access_code': perm.access_code,
                    'allowed_exit_time': perm.allowed_exit_time.strftime('%I:%M %p') if perm.allowed_exit_time else '',
                    'valid_until': perm.valid_until.strftime('%I:%M %p') if perm.valid_until else '',
                    'purpose': perm.purpose[:50] + '...' if len(perm.purpose) > 50 else perm.purpose
                })

            return {
                'success': True,
                'data': data
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    # ====================
    # SECURITY GUARD INTERFACE
    # ====================

    @http.route('/security/child-exit/verify', type='http', auth='user', website=True)
    def security_verify_interface(self, **kwargs):
        """Security guard interface to verify permissions"""
        values = {
            'page_name': 'security_child_exit_verify',
            'user': request.env.user,
        }
        return request.render('community_management.security_child_exit_verify', values)

