# visiting_help_portal.py
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class VisitingHelpPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'visiting_help_count' in counters:
            values['visiting_help_count'] = request.env['community.visiting.help.entry'].search_count([
                ('tenant_id', '=', request.env.user.partner_id.id)
            ])
        return values


class VisitingHelpController(http.Controller):

    @http.route('/my/visiting-help', type='http', auth="user", website=True)
    def my_visiting_help_entries(self, **kw):
        entries = request.env['community.visiting.help.entry'].search([
            ('tenant_id', '=', request.env.user.partner_id.id)
        ], order='create_date desc')

        categories = request.env['community.visiting.help.category'].search([
            ('active', '=', True)
        ])

        week_days = request.env['community.week.day'].search([])

        values = {
            'entries': entries,
            'categories': categories,
            'week_days': week_days,
            'page_name': 'visiting_help',
        }
        return request.render('community_management.visiting_help_portal_my_entries', values)

    @http.route('/my/visiting-help/entry/<int:entry_id>', type='http', auth="user", website=True)
    def visiting_help_entry_detail(self, entry_id, **kw):
        entry = request.env['community.visiting.help.entry'].browse(entry_id)
        if not entry.exists() or entry.tenant_id != request.env.user.partner_id:
            return request.redirect('/my/visiting-help')

        values = {
            'entry': entry,
            'page_name': 'visiting_help_detail',
        }
        return request.render('community_management.visiting_help_portal_entry_detail', values)

    @http.route('/my/visiting-help/entry/create', type='http', auth="user", website=True, methods=['POST'], csrf=True)
    def create_visiting_help_entry(self, **post):
        if post:
            try:
                # Prepare data for creation
                entry_data = {
                    'tenant_id': request.env.user.partner_id.id,
                    'category_id': int(post.get('category_id')),
                    'entry_type': post.get('entry_type'),
                    'company_name': post.get('company_name', False) or False,
                }

                if post.get('entry_type') == 'once':
                    entry_data.update({
                        'visit_date': post.get('visit_date'),
                        'start_time': float(post.get('start_time', 0)),
                        'valid_for': post.get('valid_for'),
                    })
                else:
                    # For frequent visits - handle checkbox list
                    day_ids = post.getlist('day_ids') if 'day_ids' in post else []
                    if day_ids and isinstance(day_ids, list):
                        entry_data['day_ids'] = [(6, 0, [int(d) for d in day_ids])]
                    elif day_ids:
                        entry_data['day_ids'] = [(6, 0, [int(day_ids)])]

                    entry_data.update({
                        'validity': post.get('validity'),
                        'time_from': float(post.get('time_from', 0)),
                        'time_to': float(post.get('time_to', 0)),
                        'entries_per_day': post.get('entries_per_day'),
                    })

                # Create the entry
                request.env['community.visiting.help.entry'].create(entry_data)

                # Show success message
                return request.redirect('/my/visiting-help?success=1')
            except Exception as e:
                # Log error and show error message
                _logger.error("Error creating visiting help entry: %s", str(e))
                return request.redirect('/my/visiting-help?error=1')

        return request.redirect('/my/visiting-help')