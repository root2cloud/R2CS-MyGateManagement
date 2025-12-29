from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class CommunityFestival(models.Model):
    _name = 'community.festival'
    _description = 'Community Festival / Event'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Festival/Event Name', required=True)
    community_id = fields.Many2one('community.management', string='Community', required=True)
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date')
    description = fields.Text(string='Description')

    expense_account_id = fields.Many2one(
        'account.account', string='Expense Account', required=True,
        domain="[('account_type', '=', 'expense')]"
    )
    approver_id = fields.Many2one('res.partner', string='Approver', tracking=True)

    expense_ids = fields.One2many('community.expense.line', 'festival_id', string='Expense Lines')
    total_expense = fields.Float(string='Total Amount',
                                 compute='_compute_total_expense',
                                 store=True)
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted for Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    @api.depends('expense_ids.amount')
    def _compute_total_expense(self):
        for festival in self:
            festival.total_expense = sum(festival.expense_ids.mapped('amount'))

    # Submit for Approval
    def action_submit(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError("Only draft records can be submitted.")
        if not self.approver_id:
            raise ValidationError("Please select an Approver before submitting.")
        if self.total_expense <= 0:
            raise ValidationError("Add at least one expense line with amount.")
        self.state = 'submitted'

    # Approve (only visible to approver)
    def action_approve(self):
        self.ensure_one()
        if self.state != 'submitted':
            raise UserError("Only submitted records can be approved.")
        if self.env.user.partner_id != self.approver_id:
            raise UserError("Only the assigned approver can approve this festival expense.")
        self._create_journal_entry()
        self.state = 'approved'

    # Reject (only visible to approver)
    def action_reject(self):
        self.ensure_one()
        if self.state != 'submitted':
            raise UserError("Only submitted records can be rejected.")
        if self.env.user.partner_id != self.approver_id:
            raise UserError("Only the assigned approver can reject this festival expense.")
        self.state = 'rejected'

    # Set to Draft
    def action_set_to_draft(self):
        self.ensure_one()
        if self.state in ('approved', 'rejected'):
            self.move_id.button_cancel()
            self.move_id.unlink()
        self.state = 'draft'

    # Private method to create journal entry
    def _create_journal_entry(self):
        if self.move_id:
            raise UserError("Journal entry already created.")

        journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
        if not journal:
            raise UserError("No bank journal found. Please configure one.")
        if not journal.default_account_id:
            raise UserError("Default account not set in the bank journal.")

        move = self.env['account.move'].create({
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'ref': f"{self.name} - Festival Expenses",
            'line_ids': [
                (0, 0, {
                    'name': self.name,
                    'account_id': self.expense_account_id.id,
                    'debit': self.total_expense,
                }),
                (0, 0, {
                    'name': self.name,
                    'account_id': journal.default_account_id.id,
                    'credit': self.total_expense,
                }),
            ]
        })
        move.action_post()
        self.move_id = move



class CommunityExpenseLine(models.Model):
    _name = 'community.expense.line'
    _description = 'Festival Expense Line'

    festival_id = fields.Many2one('community.festival', required=True, ondelete='cascade')
    community_id = fields.Many2one(related='festival_id.community_id', store=True, readonly=True)
    name = fields.Char(string='Description', required=True)
    amount = fields.Float(string='Amount', required=True)