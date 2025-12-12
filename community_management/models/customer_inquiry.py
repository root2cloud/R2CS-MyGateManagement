from odoo import models, fields

class CustomerInquiry(models.Model):
    _name = 'customer.inquiry'
    _description = 'Customer General Inquiry'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    name = fields.Char(related='partner_id.name', string='Customer Name', store=True, readonly=True)
    email = fields.Char(related='partner_id.email', string='Email', store=True, readonly=True)
    phone = fields.Char(related='partner_id.phone', string='Phone', store=True, readonly=True)
    subject = fields.Char(string='Subject', required=True)
    message = fields.Text(string='Message')
    inquiry_date = fields.Datetime(string='Inquiry Date', default=fields.Datetime.now)
    status = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed')
    ], string='Status', default='new')

    def action_in_progress(self):
        self.write({'status': 'in_progress'})

    def action_resolved(self):
        self.write({'status': 'resolved'})

    def action_closed(self):
        self.write({'status': 'closed'})

    def action_reset_to_new(self):
        self.write({'status': 'new'})
