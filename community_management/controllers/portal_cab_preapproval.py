# controllers/portal_cab_preapproval.py

from odoo import http
from odoo.http import request


class PortalCabPreapproval(http.Controller):

    @http.route(
        ['/my/cab/preapproval', '/my/cab/preapproval/<int:pre_id>'],
        type='http', auth='user', website=True, methods=['GET', 'POST'], csrf=False
    )
    def portal_cab_preapproval(self, pre_id=None, **post):
        """Main portal entry for cab pre-approvals (Once / Frequently)."""
        partner = request.env.user.partner_id
        Pre = request.env['cab.preapproval'].sudo()
        pre = Pre.browse(pre_id) if pre_id else False

        # Handle form submit (Once or Frequently)
        if request.httprequest.method == 'POST':
            mode = post.get('mode', 'once')

            vals = {
                'resident_id': partner.id,
                'mode': mode,
            }

            # Common: last 4 digits of vehicle number (for both modes)
            vehicle_last4 = (post.get('vehicle_last4') or '').strip()
            if vehicle_last4:
                vals['vehicle_last4'] = vehicle_last4

            if mode == 'once':
                # Once: today + X hours
                vals['once_valid_hours'] = int(post.get('once_valid_hours') or 1)
            else:
                # Frequently: days, validity, time slot, entries, company
                vals['freq_days'] = post.get('freq_days') or 'all'
                vals['freq_validity'] = post.get('freq_validity') or '6m'

                # Convert time strings ("HH:MM") to float hours
                t_from = post.get('freq_time_from') or '00:00'
                t_to = post.get('freq_time_to') or '23:59'
                h1, m1 = t_from.split(':')
                h2, m2 = t_to.split(':')
                vals['freq_time_from'] = int(h1) + int(m1) / 60.0
                vals['freq_time_to'] = int(h2) + int(m2) / 60.0

                vals['entries_per_day'] = post.get('entries_per_day') or 'one'
                vals['company_name'] = post.get('company_name') or False

            # Create or update record
            if pre and pre.exists():
                pre.write(vals)
            else:
                pre = Pre.create(vals)

            # Compute window + activate
            pre.action_activate()
            return request.redirect('/my/cab/preapproval/%s' % pre.id)

        # GET: list + optional detail
        pres = Pre.search([('resident_id', '=', partner.id)], order='id desc')
        if not pre_id or not pre.exists():
            pre = False

        values = {
            'pre': pre,    # current selection (or False)
            'pres': pres,  # all approvals for this resident
        }
        return request.render('community_management.portal_cab_preapproval', values)
