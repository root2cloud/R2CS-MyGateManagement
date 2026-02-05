from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'


    corpus_fund_id = fields.Many2one('corpus.fund.invoice', string='Corpus Fund Invoice', readonly=True)


class CorpusFundInvoice(models.Model):
    _name = 'corpus.fund.invoice'
    _description = 'Corpus Fund Invoice'
    _rec_name = 'flat_id'
    _order = 'id desc'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # ------------------------- CORE FIELDS -------------------------
    flat_id = fields.Many2one(
        'flat.management',
        string='Flat',
        required=True
    )
    owner_id = fields.Many2one(
        'res.partner',
        string='Owner',
        related='flat_id.lease_owner_id',
        store=True,
        readonly=True
    )
    building_id = fields.Many2one(
        'building.management',
        string='Building',
        related='flat_id.building_id',
        store=True,
        readonly=True
    )
    floor_id = fields.Many2one(
        'floor.management',
        string='Floor',
        related='flat_id.floor_id',
        store=True,
        readonly=True
    )
    amount = fields.Float(
        string='Corpus Amount',
        required=True
    )
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        readonly=True,
        copy=False
    )

    # Use the same selection as before, but now used for status bar
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('invoiced', 'Invoiced'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
        copy=False
    )

    # Button visibility
    show_generate_invoice = fields.Boolean(
        compute='_compute_button_visibility',
        string="Show Generate Button"
    )
    show_view_invoice = fields.Boolean(
        compute='_compute_button_visibility',
        string="Show View Button"
    )

    @api.depends('state', 'invoice_id')
    def _compute_button_visibility(self):
        for rec in self:
            rec.show_generate_invoice = (rec.state == 'draft' and not rec.invoice_id)
            rec.show_view_invoice = bool(rec.invoice_id)

    # ------------------------- ACTIONS -------------------------
    def action_generate_invoice(self):
        for rec in self:
            if rec.invoice_id or rec.state != 'draft':
                continue

            invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': rec.owner_id.id,
                'invoice_date': fields.Date.context_today(rec),
                'currency_id': self.env.company.currency_id.id,
                'corpus_fund_id': rec.id,  # Link back to corpus fund invoice
                'invoice_line_ids': [(0, 0, {
                    'name': f'Corpus Fund Contribution - Flat {rec.flat_id.name}',
                    'quantity': 1,
                    'price_unit': rec.amount,
                })],
            })

            rec.write({
                'invoice_id': invoice.id,
                'state': 'invoiced'
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Corpus fund invoice generated!',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
            'target': 'current',
        }

    invoice_count = fields.Integer(compute='_compute_invoice_count')

    def _compute_invoice_count(self):
        for r in self:
            r.invoice_count = len(r.invoice_id)

    def action_view_corpus_invoices(self):
        self.ensure_one()
        # Use invoice_id directly instead of corpus_fund_id
        invoice_ids = self.invoice_id.ids

        if not invoice_ids:
            return False

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoice_ids)],
            'context': {
                'default_partner_id': self.owner_id.id,
                'default_move_type': 'out_invoice',
            }
        }

# from odoo import fields, models, api
#
# class CorpusFundInvoice(models.Model):
#     _name = 'corpus.fund.invoice'
#     _description = 'Corpus Fund Invoice'
#     _rec_name = 'flat_id'
#     _order = 'id desc'
#
#     # ------------------------- CORE FIELDS -------------------------
#     flat_id = fields.Many2one(
#         'flat.management',
#         string='Flat',
#         required=True
#     )
#     owner_id = fields.Many2one(
#         'res.partner',
#         string='Owner',
#         related='flat_id.lease_owner_id',
#         store=True,
#         readonly=True
#     )
#     building_id = fields.Many2one(
#         'building.management',
#         string='Building',
#         related='flat_id.building_id',
#         store=True,
#         readonly=True
#     )
#     floor_id = fields.Many2one(
#         'floor.management',
#         string='Floor',
#         related='flat_id.floor_id',
#         store=True,
#         readonly=True
#     )
#     amount = fields.Float(
#         string='Corpus Amount',
#         required=True
#     )
#     invoice_id = fields.Many2one(
#         'account.move',
#         string='Invoice',
#         readonly=True,
#         copy=False
#     )
#
#     # Use the same selection as before, but now used for status bar
#     state = fields.Selection(
#         [
#             ('draft', 'Draft'),
#             ('invoiced', 'Invoiced'),
#         ],
#         string='Status',
#         default='draft',
#         required=True,
#         tracking=True,          # optional: shows in chatter when changed
#         copy=False
#     )
#
#     # Button visibility (still useful if you want conditional logic later)
#     show_generate_invoice = fields.Boolean(
#         compute='_compute_button_visibility',
#         string="Show Generate Button"
#     )
#     show_view_invoice = fields.Boolean(
#         compute='_compute_button_visibility',
#         string="Show View Button"
#     )
#
#     @api.depends('state', 'invoice_id')
#     def _compute_button_visibility(self):
#         for rec in self:
#             rec.show_generate_invoice = (rec.state == 'draft' and not rec.invoice_id)
#             rec.show_view_invoice = bool(rec.invoice_id)
#
#     # ------------------------- ACTIONS -------------------------
#     def action_generate_invoice(self):
#         for rec in self:
#             if rec.invoice_id or rec.state != 'draft':
#                 continue
#
#             invoice = self.env['account.move'].create({
#                 'move_type': 'out_invoice',
#                 'partner_id': rec.owner_id.id,
#                 'invoice_date': fields.Date.context_today(rec),
#                 'currency_id': self.env.company.currency_id.id,
#                 'invoice_line_ids': [(0, 0, {
#                     'name': f'Corpus Fund Contribution - Flat {rec.flat_id.name}',
#                     'quantity': 1,
#                     'price_unit': rec.amount,
#                 })],
#             })
#
#             rec.write({
#                 'invoice_id': invoice.id,
#                 'state': 'invoiced'
#             })
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': 'Success',
#                 'message': 'Corpus fund invoice generated!',
#                 'type': 'success',
#                 'sticky': False,
#             }
#         }
#
#     def action_view_invoice(self):
#         self.ensure_one()
#         if not self.invoice_id:
#             return False
#         return {
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move',
#             'view_mode': 'form',
#             'res_id': self.invoice_id.id,
#             'target': 'current',
#         }
#
#     invoice_count = fields.Integer(compute='_compute_invoice_count')
#
#     def _compute_invoice_count(self):
#         for r in self:
#             r.invoice_count = len(r.invoice_id)
#
#     def action_view_corpus_invoices(self):
#         return {
#             'type': 'ir.actions.act_window',
#             'res_model': 'account.move',
#             'view_mode': 'list,form',
#             'domain': [('corpus_fund_id', '=', self.id)],
#             'context': {
#                 'default_corpus_fund_id': self.id,
#                 'default_move_type': 'out_invoice',
#                 'default_partner_id': self.owner_id.id,
#             }
#         }
