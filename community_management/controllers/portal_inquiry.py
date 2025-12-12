from odoo import http
from odoo.http import request


class CustomerInquiryController(http.Controller):

    @http.route(['/inquiry'], type='http', auth='public', website=True)
    def inquiry_form(self):
        partner = request.env.user.partner_id if request.env.user.id != request.env.ref('base.public_user').id else None

        values = {
            'partner': partner,
        }
        return request.render('community_management.inquiry_form_template', values)

    @http.route(['/inquiry/submit'], type='http', auth='public', website=True, methods=['POST'])
    def submit_inquiry(self, **post):
        # If portal user logged in, ignore inputs and use their partner record
        if request.env.user.id != request.env.ref('base.public_user').id:
            partner = request.env.user.partner_id
        else:
            partner = request.env['res.partner'].sudo().search([('email', '=', post.get('email'))], limit=1)
            if not partner:
                partner = request.env['res.partner'].sudo().create({
                    'name': post.get('name'),
                    'email': post.get('email'),
                    'phone': post.get('phone'),
                })

        vals = {
            'partner_id': partner.id,
            'subject': post.get('subject'),
            'message': post.get('message'),
        }
        request.env['customer.inquiry'].sudo().create(vals)
        return request.redirect('/inquiry?success=1')
