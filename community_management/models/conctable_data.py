from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], default='draft', string="Verification Status", tracking=True)

    # 2-Level Approver Fields
    approver_one_id = fields.Many2one('res.users', string="Primary Approver", tracking=True)
    approver_two_id = fields.Many2one('res.users', string="Secondary Approver", tracking=True)

    # Invisible helper to check if current user is an approver
    is_approver = fields.Boolean(compute='_compute_is_approver')

    @api.depends('approver_one_id', 'approver_two_id')
    def _compute_is_approver(self):
        for rec in self:
            # Returns True if current user is either Approver 1 or Approver 2
            rec.is_approver = self.env.user.id in [rec.approver_one_id.id, rec.approver_two_id.id]

    def action_submit(self):
        if not self.approver_one_id or not self.approver_two_id:
            raise UserError(_("Please assign both approvers before submitting."))
        self.state = 'submitted'

    def action_approve(self):
        # You can add logic here if you want both to click,
        # but based on your request, this moves it to 'approved'.
        self.state = 'approved'

    def action_reject(self):
        # Any one of the two clicking this will trigger the 'rejected' state
        self.state = 'rejected'

    def action_reset_to_draft(self):
        self.state = 'draft'