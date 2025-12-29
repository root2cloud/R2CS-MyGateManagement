from odoo import http
from odoo.http import request


class PortalDeliveryPass(http.Controller):

    @http.route(
        ['/my/delivery-pass', '/my/delivery-pass/<int:pass_id>'],
        type='http',
        auth='user',
        website=True,
        methods=['GET', 'POST'],
        csrf=False,
    )
    def portal_delivery_pass(self, pass_id=None, **post):
        DeliveryPass = request.env['community.delivery.pass'].sudo()
        partner = request.env.user.partner_id
        current = False

        if pass_id:
            current = DeliveryPass.search(
                [('id', '=', pass_id), ('resident_id', '=', partner.id)],
                limit=1,
            )

        if request.httprequest.method == 'POST':
            mode = post.get('mode') or 'once'
            is_surprise = bool(post.get('is_surprise'))

            vals = {
                'resident_id': partner.id,
                'mode': mode,
                'is_surprise': is_surprise,
                'allow_leave_at_gate': not is_surprise,
                'company_name': post.get('company_name') or False,
            }

            if mode == 'once':
                vals['once_date'] = post.get('once_date') or False
                start_time = post.get('once_start_time') or '00:00'
                h, m = start_time.split(':')
                vals['once_start_time'] = int(h) + int(m) / 60.0
                vals['once_valid_hours'] = post.get('once_valid_hours') or '1'

            elif mode == 'frequent':
                vals['freq_days'] = post.get('freq_days') or 'all'

                t_from = post.get('freq_time_from') or '00:00'
                t_to = post.get('freq_time_to') or '23:59'
                h1, m1 = t_from.split(':')
                h2, m2 = t_to.split(':')

                vals['freq_time_from'] = int(h1) + int(m1) / 60.0
                vals['freq_time_to'] = int(h2) + int(m2) / 60.0
                vals['freq_validity'] = post.get('freq_validity') or '6m'
                vals['entries_per_day'] = post.get('entries_per_day') or 'one'

            new_pass = DeliveryPass.create(vals)
            return request.redirect('/my/delivery-pass/%s' % new_pass.id)

        passes = DeliveryPass.search(
            [('resident_id', '=', partner.id)],
            order='id desc',
        )
        if not current or not current.exists():
            current = passes[:1]

        values = {
            'current': current,
            'passes': passes,
        }
        return request.render('community_management.portal_delivery_pass', values)

# from odoo import http
# from odoo.http import request
#
#
# class PortalDeliveryPass(http.Controller):
#
#     @http.route(
#         ['/my/delivery-pass', '/my/delivery-pass/<int:pass_id>'],
#         type='http',
#         auth='user',
#         website=True,
#         methods=['GET', 'POST'],
#         csrf=False,
#     )
#     def portal_delivery_pass(self, pass_id=None, **post):
#         DeliveryPass = request.env['community.delivery.pass'].sudo()
#         partner = request.env.user.partner_id
#         current = False
#
#         if pass_id:
#             current = DeliveryPass.search(
#                 [('id', '=', pass_id), ('resident_id', '=', partner.id)],
#                 limit=1,
#             )
#
#         # POST – create new pass
#         if request.httprequest.method == 'POST':
#             mode = post.get('mode') or 'once'
#             is_surprise = bool(post.get('is_surprise'))
#
#             vals = {
#                 'resident_id': partner.id,
#                 'mode': mode,
#                 'is_surprise': is_surprise,
#                 'allow_leave_at_gate': not is_surprise,
#                 'company_name': post.get('company_name') or False,
#             }
#
#             if mode == 'once':
#                 vals['once_date'] = post.get('once_date') or False
#                 start_time = post.get('once_start_time') or '00:00'
#                 h, m = start_time.split(':')
#                 vals['once_start_time'] = int(h) + int(m) / 60.0
#                 vals['once_valid_hours'] = post.get('once_valid_hours') or '1'
#
#             elif mode == 'frequent':
#                 vals['freq_days'] = post.get('freq_days') or 'all'
#
#                 t_from = post.get('freq_time_from') or '00:00'
#                 t_to = post.get('freq_time_to') or '23:59'
#                 h1, m1 = t_from.split(':')
#                 h2, m2 = t_to.split(':')
#
#                 vals['freq_time_from'] = int(h1) + int(m1) / 60.0
#                 vals['freq_time_to'] = int(h2) + int(m2) / 60.0
#
#                 vals['freq_validity'] = post.get('freq_validity') or '6m'
#                 vals['entries_per_day'] = post.get('entries_per_day') or 'one'
#
#             new_pass = DeliveryPass.create(vals)
#             return request.redirect('/my/delivery-pass/%s' % new_pass.id)
#
#         # GET – list + (optional) detail
#         passes = DeliveryPass.search(
#             [('resident_id', '=', partner.id)],
#             order='id desc',
#         )
#
#         if not current or not current.exists():
#             current = passes[:1]
#
#         values = {
#             'current': current,
#             'passes': passes,
#         }
#         return request.render('community_management.portal_delivery_pass', values)
