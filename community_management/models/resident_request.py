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

    # Link to flat transaction
    flat_transaction_id = fields.Many2one('flat.transaction', string='Lease Transaction', readonly=True)

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

    def _create_flat_transaction(self, partner):
        """Create flat transaction record with auto-filled details"""
        # Check if transaction already exists
        if self.flat_transaction_id:
            return self.flat_transaction_id

        # Prepare values for flat transaction
        transaction_vals = {
            'building_id': self.building_id.id,
            'floor_id': self.floor_id.id if self.floor_id else False,
            'flat_id': self.flat_id.id,
            'lease_owner_id': self.owner_id.id if self.owner_id else False,
            'tenant_id': partner.id,  # Created partner from approval
            'rent_price': 0.0,  # Default value, can be updated later
            'lease_start_date': self.lease_start_date or fields.Date.today(),
            'lease_end_date': self.lease_end_date or (fields.Date.today() + timedelta(days=365)),  # Default 1 year
            'agreement_date': fields.Date.today(),
            'status': 'draft',  # Will be activated after creation
            'notes': f"Auto-created from resident access request #{self.id}\n" +
                     f"Occupancy Type: {dict(self._fields['occupancy_type'].selection).get(self.occupancy_type)}\n" +
                     f"Submitted: {self.submitted_date}\n" +
                     f"Approved: {fields.Datetime.now()}",
        }

        # Add rental agreement if uploaded
        if self.rental_agreement_datas:
            transaction_vals.update({
                'agreement_document': self.rental_agreement_datas,
                'agreement_filename': self.rental_agreement_filename or f"rental_agreement_{self.name}.pdf",
            })

        # Create the flat transaction
        transaction = self.env['flat.transaction'].create(transaction_vals)

        # Activate the lease transaction
        try:
            transaction.action_confirm()
            transaction.write({'status': 'confirmed'})

            # Link transaction back to this request
            self.flat_transaction_id = transaction.id

            # Log creation
            self.message_post(
                body=f"Lease transaction #{transaction.id} created and activated automatically for Flat {self.flat_id.name}",
                subject="Lease Transaction Created"
            )

            return transaction
        except Exception as e:
            # If activation fails, at least the transaction is created
            self.message_post(
                body=f"Lease transaction #{transaction.id} created but activation failed: {str(e)}",
                subject="Lease Transaction Created (Activation Failed)"
            )
            return transaction

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

        # Create portal user ONLY AFTER APPROVAL
        if not partner.user_ids.filtered(lambda u: u.has_group('base.group_portal')):
            user = self.env['res.users'].create({
                'name': self.name,
                'login': self.email,
                'partner_id': partner.id,
                'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
            })
            self.user_id = user
            user.action_reset_password()  # Sends password setup email
        else:
            # If portal user already exists, link it to the request
            portal_user = partner.user_ids.filtered(lambda u: u.has_group('base.group_portal'))
            if portal_user:
                self.user_id = portal_user[0]

        # Create flat transaction with auto-filled details
        transaction = self._create_flat_transaction(partner)

        # Update request status
        self.write({
            'state': 'approved',
            'partner_id': partner.id,
        })

        # Clear activity and notify
        self.activity_feedback(['mail.mail_activity_data_todo'])

        # Post comprehensive approval message
        owner_name = self.owner_id.name if self.owner_id else 'Not specified'

        approval_message = f"""
        <p><b>APPROVED</b> by {self.env.user.name}</p>
        <ul>
            <li>Portal access granted!</li>
            <li>Portal user created and password reset email sent.</li>
            <li>Lease transaction #{transaction.id} created and activated.</li>
            <li>Flat {self.flat_id.name} is now occupied by {self.name}.</li>
        </ul>
        <p><b>Transaction Details:</b></p>
        <ul>
            <li>Building: {self.building_id.name}</li>
            <li>Flat: {self.flat_id.name}</li>
            <li>Tenant: {self.name}</li>
            <li>Owner: {owner_name}</li>
            <li>Lease Start: {transaction.lease_start_date}</li>
            <li>Lease End: {transaction.lease_end_date}</li>
            <li>Status: {transaction.status}</li>
        </ul>
        """

        self.message_post(body=approval_message)

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
        """Fix for group expansion - Odoo 18.0 requires this signature"""
        # Return all possible states
        return [key for key, value in self._fields['state'].selection]

    def action_view_flat_transaction(self):
        """View the linked flat transaction"""
        self.ensure_one()
        if not self.flat_transaction_id:
            raise ValidationError("No lease transaction linked to this request.")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Lease Transaction',
            'res_model': 'flat.transaction',
            'res_id': self.flat_transaction_id.id,
            'view_mode': 'form',
            'target': 'current',
        }



# from odoo import models, fields, api
# from odoo.exceptions import ValidationError
# from datetime import timedelta
#
#
# class ResidentAccessRequest(models.Model):
#     _name = 'resident.access.request'
#     _description = 'Resident Portal Access Request'
#     _inherit = ['mail.thread', 'mail.activity.mixin']
#     _order = 'submitted_date desc'
#
#     # Requester Details
#     name = fields.Char(string='Requester Name', required=True, tracking=True)
#     phone = fields.Char(string='Phone', required=True)
#     email = fields.Char(string='Email', required=True)
#
#     # Address Hierarchy
#     community_id = fields.Many2one(
#         'community.management',
#         string='Society/Community',
#         required=True,
#         tracking=True
#     )
#     building_id = fields.Many2one(
#         'building.management',
#         string='Building/Block',
#         required=True,
#         domain="[('community_id', '=', community_id)]",
#         tracking=True
#     )
#     floor_id = fields.Many2one(
#         'floor.management',
#         string='Floor',
#         domain="[('building_id', '=', building_id)]",
#         tracking=True
#     )
#     flat_id = fields.Many2one(
#         'flat.management',
#         string='Flat No.',
#         required=True,
#         domain="[('building_id', '=', building_id)]",
#         tracking=True
#     )
#
#     # Occupancy - Only tenant options
#     occupancy_type = fields.Selection([
#         ('renting_alone', 'Renting Alone'),
#         ('renting_with_family', 'Renting with Family'),
#         ('renting_with_flatmates', 'Renting with Flatmates'),
#     ], string='You are', required=True, default='renting_with_family')
#
#     # Additional fields (kept for information only)
#     lease_start_date = fields.Date(string='Lease Start Date')
#     lease_end_date = fields.Date(string='Lease End Date')
#     owner_id = fields.Many2one(
#         'res.partner',
#         string='Owner',
#         help="If you are renting, please select the actual owner of the flat (optional)"
#     )
#
#     # Document Upload
#     rental_agreement_datas = fields.Binary(string='Upload Rental Agreement', attachment=True)
#     rental_agreement_filename = fields.Char(string='Filename')
#
#     # Approver
#     approver_id = fields.Many2one(
#         'res.users',
#         string='Approver',
#         domain="[('share', '=', False)]",
#         tracking=True,
#     )
#
#     # Status & Dates
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('pending', 'Pending Approval'),
#         ('approved', 'Approved'),
#         ('rejected', 'Rejected'),
#     ], string='Status', default='draft', tracking=True, group_expand='_group_states')
#
#     submitted_date = fields.Datetime(string='Submitted On', readonly=True)
#
#     # After Approval
#     partner_id = fields.Many2one('res.partner', string='Resident', readonly=True)
#     user_id = fields.Many2one('res.users', string='Portal User', readonly=True)
#
#     # Link to flat transaction
#     flat_transaction_id = fields.Many2one('flat.transaction', string='Lease Transaction', readonly=True)
#
#     @api.depends('community_id')
#     def _compute_default_approver(self):
#         for rec in self:
#             if rec.community_id and rec.community_id.default_approver_id:
#                 rec.approver_id = rec.community_id.default_approver_id
#             else:
#                 rec.approver_id = self.env['res.users'].search([('share', '=', False)], limit=1)
#
#     @api.onchange('community_id')
#     def _onchange_community_id(self):
#         self.building_id = self.floor_id = self.flat_id = False
#
#     @api.onchange('building_id')
#     def _onchange_building_id(self):
#         self.floor_id = self.flat_id = False
#
#     @api.onchange('floor_id')
#     def _onchange_floor_id(self):
#         self.flat_id = False
#
#     def action_submit(self):
#         self.write({
#             'state': 'pending',
#             'submitted_date': fields.Datetime.now(),
#         })
#
#         self.activity_schedule(
#             activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
#             summary=f"Approve portal access for {self.name} - Flat {self.flat_id.name}",
#             note=f"<p><b>Resident:</b> {self.name}<br/>"
#                  f"<b>Flat:</b> {self.flat_id.name} ({self.building_id.name})<br/>"
#                  f"<b>Community:</b> {self.community_id.name}<br/>"
#                  f"<b>Phone:</b> {self.phone}<br/>"
#                  f"<b>Type:</b> {dict(self._fields['occupancy_type'].selection).get(self.occupancy_type)}</p>",
#             user_id=self.approver_id.id,
#             date_deadline=fields.Date.today() + timedelta(days=3),
#         )
#
#         body = """
#         <div class="alert alert-info">
#             <h4>Access Request Submitted</h4>
#             <p>Assigned to <b>{}</b> for approval.</p>
#         </div>
#         """.format(self.approver_id.name)
#         self.message_post(body=body, message_type='notification', subtype_xmlid='mail.mt_comment')
#         self.message_subscribe(partner_ids=self.approver_id.partner_id.ids)
#
#     def _create_flat_transaction(self, partner):
#         """Create flat transaction record with auto-filled details"""
#         # Check if transaction already exists
#         if self.flat_transaction_id:
#             return self.flat_transaction_id
#
#         # Prepare values for flat transaction
#         transaction_vals = {
#             'building_id': self.building_id.id,
#             'floor_id': self.floor_id.id if self.floor_id else False,
#             'flat_id': self.flat_id.id,
#             'lease_owner_id': self.owner_id.id if self.owner_id else False,
#             'tenant_id': partner.id,  # Created partner from approval
#             'rent_price': 0.0,  # Default value, can be updated later
#             'lease_start_date': self.lease_start_date or fields.Date.today(),
#             'lease_end_date': self.lease_end_date or (fields.Date.today() + timedelta(days=365)),  # Default 1 year
#             'agreement_date': fields.Date.today(),
#             'status': 'draft',  # Will be activated after creation
#             'notes': f"Auto-created from resident access request #{self.id}\n" +
#                      f"Occupancy Type: {dict(self._fields['occupancy_type'].selection).get(self.occupancy_type)}\n" +
#                      f"Submitted: {self.submitted_date}\n" +
#                      f"Approved: {fields.Datetime.now()}",
#         }
#
#         # Add rental agreement if uploaded
#         if self.rental_agreement_datas:
#             transaction_vals.update({
#                 'agreement_document': self.rental_agreement_datas,
#                 'agreement_filename': self.rental_agreement_filename or f"rental_agreement_{self.name}.pdf",
#             })
#
#         # Create the flat transaction
#         transaction = self.env['flat.transaction'].create(transaction_vals)
#
#         # Activate the lease transaction
#         try:
#             transaction.action_confirm()
#             transaction.write({'status': 'confirmed'})
#
#             # Link transaction back to this request
#             self.flat_transaction_id = transaction.id
#
#             # Log creation
#             self.message_post(
#                 body=f"Lease transaction #{transaction.id} created and activated automatically for Flat {self.flat_id.name}",
#                 subject="Lease Transaction Created"
#             )
#
#             return transaction
#         except Exception as e:
#             # If activation fails, at least the transaction is created
#             self.message_post(
#                 body=f"Lease transaction #{transaction.id} created but activation failed: {str(e)}",
#                 subject="Lease Transaction Created (Activation Failed)"
#             )
#             return transaction
#
#     def action_approve(self):
#         self.ensure_one()
#         if self.state != 'pending':
#             raise ValidationError("Only pending requests can be approved.")
#
#         # Find or create partner (resident)
#         partner = self.env['res.partner'].search([('email', '=', self.email)], limit=1)
#         if not partner:
#             partner = self.env['res.partner'].create({
#                 'name': self.name,
#                 'phone': self.phone,
#                 'email': self.email,
#                 'is_company': False,
#             })
#
#         # Create portal user ONLY AFTER APPROVAL
#         if not partner.user_ids.filtered(lambda u: u.has_group('base.group_portal')):
#             user = self.env['res.users'].create({
#                 'name': self.name,
#                 'login': self.email,
#                 'partner_id': partner.id,
#                 'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
#             })
#             self.user_id = user
#             user.action_reset_password()  # Sends password setup email
#         else:
#             # If portal user already exists, link it to the request
#             portal_user = partner.user_ids.filtered(lambda u: u.has_group('base.group_portal'))
#             if portal_user:
#                 self.user_id = portal_user[0]
#
#         # Create flat transaction with auto-filled details
#         transaction = self._create_flat_transaction(partner)
#
#         # Update request status
#         self.write({
#             'state': 'approved',
#             'partner_id': partner.id,
#         })
#
#         # Clear activity and notify
#         self.activity_feedback(['mail.mail_activity_data_todo'])
#
#         # Post comprehensive approval message
#         approval_message = f"""
#         <p><b>APPROVED</b> by {self.env.user.name}</p>
#         <ul>
#             <li>Portal access granted!</li>
#             <li>Portal user created and password reset email sent.</li>
#             <li>Lease transaction #{transaction.id} created and activated.</li>
#             <li>Flat {self.flat_id.name} is now occupied by {self.name}.</li>
#         </ul>
#         <p><b>Transaction Details:</b></p>
#         <ul>
#             <li>Building: {self.building_id.name}</li>
#             <li>Flat: {self.flat_id.name}</li>
#             <li>Tenant: {self.name}</li>
#             <li>Owner: {self.owner_id.name if self.owner_id else 'None'}</li>
#             <li>Lease Start: {transaction.lease_start_date}</li>
#             <li>Lease End: {transaction.lease_end_date}</li>
#             <li>Status: {transaction.status}</li>
#         </ul>
#         """
#
#         self.message_post(body=approval_message)
#
#     def action_reject(self):
#         self.ensure_one()
#         self.write({'state': 'rejected'})
#         self.activity_feedback(['mail.mail_activity_data_todo'])
#         self.message_post(body=f"<p><b>REJECTED</b> by {self.env.user.name}</p>")
#
#     @api.constrains('flat_id', 'state')
#     def _check_flat_availability(self):
#         # Optional: Remove this constraint if you no longer care about flat status
#         # Or keep it if you still want to warn about already occupied flats
#         for rec in self:
#             if rec.state == 'pending' and rec.flat_id and rec.flat_id.status == 'occupied':
#                 raise ValidationError(f"Flat {rec.flat_id.name} is already occupied.")
#
#     def _group_states(self, states, domain, order):
#         """Fix for group expansion - Odoo 18.0 requires this signature"""
#         # Return all possible states
#         return [key for key, value in self._fields['state'].selection]
#
#     def action_view_flat_transaction(self):
#         """View the linked flat transaction"""
#         self.ensure_one()
#         if not self.flat_transaction_id:
#             raise ValidationError("No lease transaction linked to this request.")
#
#         return {
#             'type': 'ir.actions.act_window',
#             'name': 'Lease Transaction',
#             'res_model': 'flat.transaction',
#             'res_id': self.flat_transaction_id.id,
#             'view_mode': 'form',
#             'target': 'current',
#         }
#
#
#
