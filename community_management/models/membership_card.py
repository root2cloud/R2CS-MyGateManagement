from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MembershipCardRequest(models.Model):
    _name = 'membership.card.request'
    _description = 'Virtual Membership Card Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    member_id = fields.Many2one('res.partner', string='Member', required=True, tracking=True)

    request_type = fields.Selection([
        ('new', 'New Member'),
        ('reissue', 'Reissue (Lost/Damaged)')
    ], string='Request Type', required=True, default='new', tracking=True)

    reason = fields.Text(string='Reason for Reissue')

    # Designated Approvers (Must be selected during Draft)
    hod_user_id = fields.Many2one('res.users', string="HOD Approver", required=True, tracking=True)
    md_user_id = fields.Many2one('res.users', string="MD Approver", required=True, tracking=True)

    # Boolean flags to track when the designated users actually click Approve
    hod_approved = fields.Boolean(string="HOD Has Approved", default=False, tracking=True)
    md_approved = fields.Boolean(string="MD Has Approved", default=False, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval', 'Waiting for Approvals'),
        ('issued', 'Issued'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', tracking=True)

    can_approve = fields.Boolean(compute='_compute_can_approve')

    @api.depends('state', 'hod_user_id', 'md_user_id', 'hod_approved', 'md_approved')
    @api.depends_context('uid')  # Crucial for checking the currently logged-in user
    def _compute_can_approve(self):
        """Checks if the logged-in user matches the designated approver and hasn't approved yet."""
        for record in self:
            record.can_approve = False
            if record.state == 'waiting_approval':
                # Show button if logged-in user is the HOD and hasn't clicked yet
                if self.env.uid == record.hod_user_id.id and not record.hod_approved:
                    record.can_approve = True

                # Show button if logged-in user is the MD and hasn't clicked yet
                if self.env.uid == record.md_user_id.id and not record.md_approved:
                    record.can_approve = True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('membership.card.request') or _('New')
        return super().create(vals_list)

    def action_submit(self):
        self.write({
            'state': 'waiting_approval',
            'hod_approved': False,
            'md_approved': False
        })

    def action_approve(self):
        """Single button logic that figures out who is clicking it."""
        for record in self:
            if self.env.uid == record.hod_user_id.id and not record.hod_approved:
                record.hod_approved = True
            elif self.env.uid == record.md_user_id.id and not record.md_approved:
                record.md_approved = True
            else:
                raise UserError(_("You are not designated to approve this request, or you have already approved it."))

            # Move to issued only when both boolean flags are True
            if record.hod_approved and record.md_approved:
                record.state = 'issued'

    def action_reject(self):
        """If any designated approver clicks reject, deny the request."""
        if not self.can_approve:
            raise UserError(_("You do not have permission to reject this request."))
        self.write({'state': 'rejected'})


# from odoo import models, fields, api, _
# from odoo.exceptions import UserError
#
#
# class MembershipCardRequest(models.Model):
#     _name = 'membership.card.request'
#     _description = 'Virtual Membership Card Request'
#     _inherit = ['mail.thread', 'mail.activity.mixin']  # For tracking approvals
#
#     name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
#     member_id = fields.Many2one('res.partner', string='Member', required=True, tracking=True)
#
#     request_type = fields.Selection([
#         ('new', 'New Member'),
#         ('reissue', 'Reissue (Lost/Damaged)')
#     ], string='Request Type', required=True, default='new', tracking=True)
#
#     reason = fields.Text(string='Reason for Reissue')
#
#     # 2-Level Authentication States
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('waiting_hod', 'Waiting HOD Approval'),
#         ('waiting_md', 'Waiting MD Approval'),
#         ('issued', 'Issued'),
#         ('rejected', 'Rejected')
#     ], string='Status', default='draft', tracking=True)
#
#     @api.model_create_multi
#     def create(self, vals_list):
#         for vals in vals_list:
#             if vals.get('name', _('New')) == _('New'):
#                 vals['name'] = self.env['ir.sequence'].next_by_code('membership.card.request') or _('New')
#         return super().create(vals_list)
#
#     def action_submit(self):
#         self.write({'state': 'waiting_hod'})
#
#     def action_hod_approve(self):
#         # Additional logic can be added here to verify HOD group in Python if needed
#         self.write({'state': 'waiting_md'})
#
#     def action_md_approve(self):
#         # Logic to trigger Virtual Card Generation (e.g., QWeb Report generation)
#         self.write({'state': 'issued'})
#
#     def action_reject(self):
#         self.write({'state': 'rejected'})