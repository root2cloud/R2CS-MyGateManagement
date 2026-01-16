# File: community_management/controllers/notice_board_portal.py
from odoo import http
from odoo.http import request
from datetime import datetime

class NoticeBoardPortal(http.Controller):

    @http.route('/my/notices', type='http', auth='user', website=True)
    def portal_notices(self, **kw):
        partner = request.env.user.partner_id

        notices = request.env['property.notice.board'].sudo().search([
            ('active', '=', True),
            '|',
                ('target_group_ids', '=', False),
                ('target_group_ids', 'in', partner.ids),
        ], order='create_date desc')

        last_viewed = partner.last_notice_viewed or datetime(1900, 1, 1)

        values = {
            'notices': notices,           # real records
            'last_viewed': last_viewed,   # for comparison in template
            'has_new': any(n.create_date > last_viewed for n in notices),
        }

        # Mark all as read
        partner.sudo().write({'last_notice_viewed': datetime.now()})

        return request.render('community_management.portal_notice_boards', values)