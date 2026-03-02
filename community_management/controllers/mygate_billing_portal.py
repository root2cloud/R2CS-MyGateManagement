from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class MyGateBillingPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'invoice_count' in counters:
            partner = request.env.user.partner_id
            invoice_count = request.env['account.move'].search_count([
                ('move_type', '=', 'out_invoice'),
                ('partner_id', '=', partner.id),
                ('state', '=', 'posted')
            ])
            values['invoice_count'] = invoice_count
        return values

    @http.route(['/my/bills', '/my/bills/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_bills(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        AccountMove = request.env['account.move']

        domain = [
            ('move_type', '=', 'out_invoice'),
            ('partner_id', '=', partner.id),
            ('state', '=', 'posted')
        ]

        searchbar_sortings = {
            'date': {'label': 'Date', 'order': 'invoice_date desc'},
            'name': {'label': 'Reference', 'order': 'name desc'},
            'state': {'label': 'Status', 'order': 'state'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        invoice_count = AccountMove.search_count(domain)

        pager = portal_pager(
            url="/my/bills",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=invoice_count,
            page=page,
            step=self._items_per_page
        )

        invoices = AccountMove.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        # Separating Paid vs Unpaid for the dashboard
        unpaid_invoices = request.env['account.move'].sudo().search(
            domain + [('payment_state', 'in', ['not_paid', 'partial'])])
        paid_invoices = request.env['account.move'].sudo().search(
            domain + [('payment_state', 'in', ['paid', 'in_payment', 'reversed'])])

        # CRASH FIX: Calculate Overdue Invoices to satisfy Odoo's native breadcrumb logic
        today = fields.Date.today()
        overdue_invoice_count = len(
            unpaid_invoices.filtered(lambda inv: inv.invoice_date_due and inv.invoice_date_due < today))

        total_due = sum((inv.amount_residual or 0.0) for inv in unpaid_invoices)
        total_paid = sum((inv.amount_total or 0.0) for inv in paid_invoices)

        values.update({
            'date': date_begin,
            'invoices': invoices,
            'unpaid_invoices': unpaid_invoices,
            'paid_invoices': paid_invoices,
            'total_due': total_due,
            'total_paid': total_paid,
            'page_name': 'invoice',
            'overdue_invoice_count': overdue_invoice_count,  # Fixes the NoneType Error
            'filterby': filterby or 'all',  # Fixes the Filterby Error
            'pager': pager,
            'default_url': '/my/bills',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })

        return request.render("community_management.portal_dashboard", values)