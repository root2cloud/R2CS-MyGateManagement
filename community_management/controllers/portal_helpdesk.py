from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class PortalHelpdesk(CustomerPortal):

    # ---------------------------- #
    #  Portal Menu: Helpdesk Teams
    # ---------------------------- #
    @http.route(['/my/helpdesk'], type='http', auth='user', website=True)
    def portal_helpdesk_teams(self, **kwargs):
        teams = request.env['custom.helpdesk.team'].sudo().search([('active', '=', True)])
        return request.render('community_management.portal_helpdesk_team_list', {
            'teams': teams,
        })

    # ---------------------------- #
    #  Raise Ticket Page
    # ---------------------------- #
    @http.route(['/my/helpdesk/<int:team_id>/raise'], type='http', auth='user', website=True)
    def portal_raise_ticket(self, team_id, **kwargs):
        team = request.env['custom.helpdesk.team'].sudo().browse(team_id)
        return request.render('community_management.portal_raise_ticket_form', {
            'team': team,
        })

    # ---------------------------- #
    #  Submit Ticket
    # ---------------------------- #
    @http.route(['/my/helpdesk/submit'], type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def portal_submit_ticket(self, **post):
        name = post.get('name', '').strip()
        description = post.get('description', '').strip()
        team_id = int(post.get('team_id'))

        # Validation
        if not name:
            return request.render('community_management.portal_raise_ticket_form', {
                'team': request.env['custom.helpdesk.team'].sudo().browse(team_id),
                'error': "Ticket subject cannot be empty.",
            })

        if not description:
            return request.render('community_management.portal_raise_ticket_form', {
                'team': request.env['custom.helpdesk.team'].sudo().browse(team_id),
                'error': "Description is required.",
            })

        # ⭐ NEW — Read uploaded image
        image_file = request.httprequest.files.get('image')
        image_data = False
        if image_file:
            image_data = image_file.read()

        # Create ticket
        request.env['custom.helpdesk.ticket'].sudo().create({
            'name': name,
            'description': description,
            'team_id': team_id,
            'tenant_id': request.env.user.partner_id.id,
            'image': image_data,  # ⭐ ADD HERE
        })

        return request.redirect('/my/helpdesk/thank-you')

    # ---------------------------- #
    #  Thank You Page
    # ---------------------------- #
    @http.route(['/my/helpdesk/thank-you'], type='http', auth='user', website=True)
    def portal_ticket_thank_you(self, **kwargs):
        return request.render('community_management.portal_ticket_thank_you')

    # ---------------------------- #
    #  View Tickets
    # ---------------------------- #
    @http.route(['/my/helpdesk/<int:team_id>/tickets'], type='http', auth='user', website=True)
    def portal_view_team_tickets(self, team_id, **kwargs):
        partner = request.env.user.partner_id
        tickets = request.env['custom.helpdesk.ticket'].sudo().search([
            ('team_id', '=', team_id),
            ('tenant_id', '=', partner.id)
        ])
        team = request.env['custom.helpdesk.team'].sudo().browse(team_id)
        return request.render('community_management.portal_ticket_list', {
            'tickets': tickets,
            'team': team,
        })
