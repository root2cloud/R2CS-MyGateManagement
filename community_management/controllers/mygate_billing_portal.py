from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class PortalDashboard(http.Controller):

    @http.route(['/my/dashboard', '/my/dashboard/page/<int:page>'],
                type='http', auth="user", website=True)
    def portal_dashboard(self, page=1, sortby=None, filterby=None, **kw):
        partner = request.env.user.partner_id

        # Get today's date
        today = fields.Date.today()

        # Fetch invoices
        Invoice = request.env['account.move']
        invoice_domain = [
            ('partner_id', '=', partner.id),
            ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
            ('state', '=', 'posted')
        ]

        # Apply filters - use a different variable name
        filter_options = {
            'all': {'label': 'All Invoices', 'domain': []},
            'paid': {'label': 'Paid', 'domain': [('payment_state', '=', 'paid')]},
            'unpaid': {'label': 'Unpaid', 'domain': [('payment_state', '=', 'not_paid')]},
            'partial': {'label': 'Partially Paid', 'domain': [('payment_state', '=', 'partial')]},
            'overdue': {'label': 'Overdue', 'domain': [
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('invoice_date_due', '<', today)
            ]},
        }

        if filterby and filterby in filter_options:
            invoice_domain += filter_options[filterby]['domain']

        invoice_count = Invoice.search_count(invoice_domain)

        # Pager configuration
        items_per_page = 10
        invoice_pager = portal_pager(
            url="/my/dashboard",
            total=invoice_count,
            page=page,
            step=items_per_page,
            url_args={'sortby': sortby, 'filterby': filterby}
        )

        invoices = Invoice.search(invoice_domain, limit=items_per_page,
                                  offset=invoice_pager['offset'])

        # Calculate statistics
        all_invoices = Invoice.search([
            ('partner_id', '=', partner.id),
            ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
            ('state', '=', 'posted')
        ])

        # Calculate statistics
        invoice_stats = {
            'total': len(all_invoices),
            'paid': len(all_invoices.filtered(lambda inv: inv.payment_state == 'paid')),
            'unpaid': len(all_invoices.filtered(lambda inv: inv.payment_state == 'not_paid')),
            'partial': len(all_invoices.filtered(lambda inv: inv.payment_state == 'partial')),
            'overdue': len(all_invoices.filtered(
                lambda inv: inv.payment_state in ['not_paid', 'partial'] and
                            inv.invoice_date_due and
                            inv.invoice_date_due < today
            )),
        }

        # Calculate amounts
        total_amount = sum(all_invoices.mapped('amount_total')) or 0
        due_amount = sum(all_invoices.filtered(
            lambda inv: inv.payment_state in ['not_paid', 'partial']
        ).mapped('amount_residual')) or 0

        # Get recent activity
        recent_activity = all_invoices.sorted(key='invoice_date', reverse=True)[:5]

        values = {
            'partner': partner,
            'invoices': invoices,
            'recent_activity': recent_activity,
            'invoice_pager': invoice_pager,
            'invoice_stats': invoice_stats,
            'total_amount': total_amount,
            'due_amount': due_amount,
            'page_name': 'dashboard',
            'filter_options': filter_options,
            'filterby': filterby,
            'sortby': sortby,
            'today': today,
        }

        return request.render("community_management.portal_dashboard", values)