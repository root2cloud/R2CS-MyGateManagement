from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class TenantRequest(models.Model):
    _name = 'tenant.request'
    _description = 'Tenant Registration Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Request Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    partner_name = fields.Char(string='Full Name', required=True)
    partner_mobile = fields.Char(string='Mobile')
    partner_email = fields.Char(string='Email')

    country_id = fields.Many2one('res.country', string='Country', required=True)
    state_id = fields.Many2one('res.country.state', string='State', domain="[('country_id','=',country_id)]")
    community_id = fields.Many2one('community.management', string='Community', required=True,
                                   domain="[('country_id','=',country_id),('state_id','=',state_id)]")
    building_id = fields.Many2one('building.management', string='Building', domain="[('community_id','=',community_id)]")
    floor_id = fields.Many2one('floor.management', string='Floor', domain="[('building_id','=',building_id)]")
    flat_id = fields.Many2one('flat.management', string='Flat', domain="[('floor_id','=',floor_id)]")

    agreement = fields.Binary(string='Agreement Document')
    agreement_filename = fields.Char(string='Agreement Filename')

    requested_by_id = fields.Many2one('res.partner', string='Requested By')
    user_id = fields.Many2one('res.users', string='Requested User')

    approver_id = fields.Many2one('res.users', string='Approver')
    approver_ids = fields.Many2many('res.users', 'tenant_req_approver_rel', 'req_id', 'user_id', string='Approvers')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', tracking=True)

    create_portal_user = fields.Boolean(string='Create Portal User on Approve', default=True)

    date_request = fields.Datetime(string='Request Date', default=fields.Datetime.now)

    # @api.model
    # def create(self, vals):
    #     if vals.get('name', 'New') == 'New':
    #         seq = self.env['ir.sequence'].next_by_code('tenant.request.seq') or 'TR/0000'
    #         vals['name'] = seq
    #     return super().create(vals)
    #
    # def action_submit(self):
    #     self.write({'state': 'pending'})
    #     # notify approvers
    #     template = self.env.ref('community_tenant_registration.email_template_tenant_request_to_approver', raise_if_not_found=False)
    #     for rec in self:
    #         if rec.approver_ids and template:
    #             template.with_context(lang=rec.requested_by_id.lang).send_mail(rec.id, force_send=False)
    #     return True
    #
    # def action_approve(self):
    #     for rec in self:
    #         rec._approve_request()
    #         rec.state = 'approved'
    #     return True
    #
    # def action_reject(self):
    #     self.write({'state': 'rejected'})
    #     return True
    #
    # def _approve_request(self):
    #     # Create or attach partner and portal user
    #     for rec in self:
    #         partner = None
    #         if rec.requested_by_id:
    #             partner = rec.requested_by_id
    #         else:
    #             partner_vals = {
    #                 'name': rec.partner_name,
    #                 'email': rec.partner_email,
    #                 'phone': rec.partner_mobile,
    #             }
    #             partner = self.env['res.partner'].create(partner_vals)
    #             rec.requested_by_id = partner.id
    #
    #         if rec.create_portal_user:
    #             # create portal user
    #             portal_group = self.env.ref('portal.group_portal', raise_if_not_found=False)
    #             groups = [(6, 0, [portal_group.id])] if portal_group else []
    #             user = self.env['res.users'].sudo().create({
    #                 'name': partner.name,
    #                 'login': rec.partner_email or partner.name,
    #                 'partner_id': partner.id,
    #                 'groups_id': groups
    #             })
    #             rec.user_id = user.id
    #             # send portal access email
    #             template = self.env.ref('community_tenant_registration.email_template_portal_access', raise_if_not_found=False)
    #             if template:
    #                 template.with_context(user_id=user.id).send_mail(rec.id, force_send=False)

    @api.onchange('country_id')
    def _onchange_country(self):
        self.state_id = False
        return {'domain': {'state_id': [('country_id', '=', self.country_id.id)]}}

    @api.onchange('community_id')
    def _onchange_community(self):
        self.building_id = False
        return {'domain': {'building_id': [('community_id', '=', self.community_id.id)]}}

    @api.onchange('building_id')
    def _onchange_building(self):
        self.floor_id = False
        return {'domain': {'floor_id': [('building_id', '=', self.building_id.id)]}}

    @api.onchange('floor_id')
    def _onchange_floor(self):
        self.flat_id = False
        return {'domain': {'flat_id': [('floor_id', '=', self.floor_id.id)]}}
