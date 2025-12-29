from odoo import http
from odoo.http import request


class PortalSecurityGuards(http.Controller):

    @http.route(['/my/community_management', '/my/community_management/<int:page>'],
                type='http', auth="user", website=True)
    def portal_community_management(self, page=1, **kw):
        # Community Roles
        community_domain = [('community_role', '!=', False),
                            ('community_role', '!=', ''),
                            ('active', '=', True)]
        all_community_members = request.env['res.partner'].sudo().search(community_domain)

        # Security Guards
        security_domain = [('is_security_guard', '=', True), ('active', '=', True)]
        all_security_guards = request.env['res.partner'].sudo().search(security_domain)

        pager = request.website.pager(
            url="/my/community_management",
            total=len(all_community_members) + len(all_security_guards),
            page=page,
            step=12
        )

        offset = pager.get('offset', 0)
        limit = pager.get('limit', 12)

        community_members = all_community_members[offset:offset + limit]
        security_guards = all_security_guards[offset:offset + limit]

        return request.render("community_management.portal_community_management_template", {
            'community_members': all_community_members,
            'security_guards': all_security_guards,
            'pager': pager,
        })

