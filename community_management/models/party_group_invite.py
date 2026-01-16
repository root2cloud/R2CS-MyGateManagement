from odoo import models, fields, api
from datetime import datetime, timedelta
import uuid
import hashlib

class PartyGroupInvite(models.Model):
    _name = 'party.group.invite'
    _description = 'Party / Group Invite'
    _order = 'create_date desc'

    name = fields.Char('Title', default='Party / Group Invite')
    host_id = fields.Many2one(
        'res.partner', string='Host', required=True,
        default=lambda self: self.env.user.partner_id
    )
    note = fields.Text('Note')

    event_date = fields.Date('Date')
    start_time = fields.Float('Start Time')
    valid_hours = fields.Float('Valid For (hours)', default=8.0)
    location = fields.Char('Location/Venue')
    max_guests = fields.Integer('Max Guests', default=5)
    description = fields.Text('Description')

    token = fields.Char('Token', readonly=True)
    share_link = fields.Char('Share Link', compute='_compute_share_link', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('configured', 'Configured'),
        ('active', 'Active'),
    ], default='draft')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('token'):
                vals['token'] = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:16]
        return super().create(vals_list)

    @api.depends('token')
    def _compute_share_link(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec.token and rec.id:
                rec.share_link = f"{base}/party/invite/{rec.id}/{rec.token}"
            else:
                rec.share_link = False

    def action_set_configured(self):
        self.write({'state': 'configured'})

    def action_activate(self):
        self.write({'state': 'active'})
