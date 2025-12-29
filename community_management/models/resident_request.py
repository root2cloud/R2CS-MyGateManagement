from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta

class ResidentAccessRequest(models.Model):
    _name = 'resident.access.request'
    _description = 'Resident Portal Access Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'submitted_date desc'

    # Requester Details
    name = fields.Char(string='Requester Name', required=True, tracking=True)
    phone = fields.Char(string='Phone', required=True)
    email = fields.Char(string='Email', required=True)

    # Address Hierarchy
    community_id = fields.Many2one(
        'community.management',
        string='Society/Community',
        required=True,
        tracking=True
    )
    building_id = fields.Many2one(
        'building.management',
        string='Building/Block',
        required=True,
        domain="[('community_id', '=', community_id)]",
        tracking=True
    )
    floor_id = fields.Many2one(
        'floor.management',
        string='Floor',
        domain="[('building_id', '=', building_id)]",
        tracking=True
    )
    flat_id = fields.Many2one(
        'flat.management',
        string='Flat No.',
        required=True,
        domain="[('building_id', '=', building_id)]",
        tracking=True
    )

    # Occupancy - Only tenant options
    occupancy_type = fields.Selection([
        ('renting_alone', 'Renting Alone'),
        ('renting_with_family', 'Renting with Family'),
        ('renting_with_flatmates', 'Renting with Flatmates'),
    ], string='You are', required=True, default='renting_with_family')

    # Additional fields (kept for information only)
    lease_start_date = fields.Date(string='Lease Start Date')
    lease_end_date = fields.Date(string='Lease End Date')
    owner_id = fields.Many2one(
        'res.partner',
        string='Owner',
        help="If you are renting, please select the actual owner of the flat (optional)"
    )

    # Document Upload
    rental_agreement_datas = fields.Binary(string='Upload Rental Agreement', attachment=True)
    rental_agreement_filename = fields.Char(string='Filename')

    # Approver
    approver_id = fields.Many2one(
        'res.users',
        string='Approver',
        domain="[('share', '=', False)]",
        tracking=True,
    )

    # Status & Dates
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True, group_expand='_group_states')

    submitted_date = fields.Datetime(string='Submitted On', readonly=True)

    # After Approval
    partner_id = fields.Many2one('res.partner', string='Resident', readonly=True)
    user_id = fields.Many2one('res.users', string='Portal User', readonly=True)

    @api.depends('community_id')
    def _compute_default_approver(self):
        for rec in self:
            if rec.community_id and rec.community_id.default_approver_id:
                rec.approver_id = rec.community_id.default_approver_id
            else:
                rec.approver_id = self.env['res.users'].search([('share', '=', False)], limit=1)

    @api.onchange('community_id')
    def _onchange_community_id(self):
        self.building_id = self.floor_id = self.flat_id = False

    @api.onchange('building_id')
    def _onchange_building_id(self):
        self.floor_id = self.flat_id = False

    @api.onchange('floor_id')
    def _onchange_floor_id(self):
        self.flat_id = False

    def action_submit(self):
        self.write({
            'state': 'pending',
            'submitted_date': fields.Datetime.now(),
        })

        self.activity_schedule(
            activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
            summary=f"Approve portal access for {self.name} - Flat {self.flat_id.name}",
            note=f"<p><b>Resident:</b> {self.name}<br/>"
                 f"<b>Flat:</b> {self.flat_id.name} ({self.building_id.name})<br/>"
                 f"<b>Community:</b> {self.community_id.name}<br/>"
                 f"<b>Phone:</b> {self.phone}<br/>"
                 f"<b>Type:</b> {dict(self._fields['occupancy_type'].selection).get(self.occupancy_type)}</p>",
            user_id=self.approver_id.id,
            date_deadline=fields.Date.today() + timedelta(days=3),
        )

        body = """
        <div class="alert alert-info">
            <h4>Access Request Submitted</h4>
            <p>Assigned to <b>{}</b> for approval.</p>
        </div>
        """.format(self.approver_id.name)
        self.message_post(body=body, message_type='notification', subtype_xmlid='mail.mt_comment')
        self.message_subscribe(partner_ids=self.approver_id.partner_id.ids)

    def action_approve(self):
        self.ensure_one()
        if self.state != 'pending':
            raise ValidationError("Only pending requests can be approved.")

        # Find or create partner (resident)
        partner = self.env['res.partner'].search([('email', '=', self.email)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': self.name,
                'phone': self.phone,
                'email': self.email,
                'is_company': False,
            })

        # Create portal user if not already exists
        if not partner.user_ids.filtered(lambda u: u.has_group('base.group_portal')):
            user = self.env['res.users'].create({
                'name': self.name,
                'login': self.email,
                'partner_id': partner.id,
                'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
            })
            self.user_id = user
            user.action_reset_password()  # Sends password setup email

        # Update request status
        self.write({
            'state': 'approved',
            'partner_id': partner.id,
        })

        # Clear activity and notify
        self.activity_feedback(['mail.mail_activity_data_todo'])
        self.message_post(body=f"<p><b>APPROVED</b> by {self.env.user.name} - Portal access granted!</p>")

    def action_reject(self):
        self.ensure_one()
        self.write({'state': 'rejected'})
        self.activity_feedback(['mail.mail_activity_data_todo'])
        self.message_post(body=f"<p><b>REJECTED</b> by {self.env.user.name}</p>")

    @api.constrains('flat_id', 'state')
    def _check_flat_availability(self):
        # Optional: Remove this constraint if you no longer care about flat status
        # Or keep it if you still want to warn about already occupied flats
        for rec in self:
            if rec.state == 'pending' and rec.flat_id and rec.flat_id.status == 'occupied':
                raise ValidationError(f"Flat {rec.flat_id.name} is already occupied.")

    def _group_states(self, states, domain, order):
        return self.env['resident.access.request'].fields_get(['state'])['state']['selection']