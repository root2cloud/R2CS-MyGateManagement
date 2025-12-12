# models.py
from odoo import models, fields, api

class CustomHelpdeskTag(models.Model):
    _name = 'custom.helpdesk.tag'
    _description = 'Custom Helpdesk Tag'

    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer(string='Color Index')


class CustomHelpdeskTeam(models.Model):
    _name = 'custom.helpdesk.team'
    _description = 'Custom Helpdesk Team'

    name = fields.Char(string='Team Name', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)

    # *** SAFE ACTION (NO XML ACTION ID REQUIRED) ***
    def action_raise_ticket(self):
        self.ensure_one()
        return {
            'name': 'New Ticket',
            'type': 'ir.actions.act_window',
            'res_model': 'custom.helpdesk.ticket',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_team_id': self.id},
        }

    def action_view_tickets(self):
        self.ensure_one()
        return {
            'name': f'{self.name} - Tickets',
            'type': 'ir.actions.act_window',
            'res_model': 'custom.helpdesk.ticket',
            'view_mode': 'list,form',
            'domain': [('team_id', '=', self.id)],
            'target': 'current',
        }


class CustomHelpdeskTicket(models.Model):
    _name = 'custom.helpdesk.ticket'
    _description = 'Custom Helpdesk Ticket'

    name = fields.Char(string='Ticket Subject', required=True)
    description = fields.Text(string='Description')
    team_id = fields.Many2one('custom.helpdesk.team', string='Team', required=True)
    tenant_id = fields.Many2one('res.partner', string='Tenant', required=True)
    assigned_to = fields.Many2one('res.partner', string='Assigned To')
    date_close = fields.Datetime(string='Closed Date')

    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Medium'), ('2', 'High'), ('3', 'Very High')
    ], default='0', string='Priority')

    tag_ids = fields.Many2many('custom.helpdesk.tag', string='Tags')
    image = fields.Binary(string="Issue Image")

    stage = fields.Selection([
        ('new', 'New'), ('open', 'Open'), ('pending', 'Pending'),
        ('done', 'Done'), ('cancelled', 'Cancelled')
    ], string='Stage', default='new', tracking=True)

    date_open = fields.Datetime(string='Opened', default=fields.Datetime.now)

    # Status button actions
    def action_set_open(self):
        self.write({'stage': 'open'})

    def action_set_pending(self):
        self.write({'stage': 'pending'})

    def action_set_done(self):
        self.write({'stage': 'done', 'date_close': fields.Datetime.now()})

    def action_set_cancelled(self):
        self.write({'stage': 'cancelled'})

    def action_reset_new(self):
        self.write({'stage': 'new', 'date_close': False})
