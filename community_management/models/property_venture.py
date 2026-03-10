from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PropertyVenture(models.Model):
    _name = 'property.venture'
    _description = 'Property Venture / Master Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Adds chatter for tracking

    name = fields.Char(string='Venture Name', required=True, tracking=True)
    location = fields.Char(string='Location / Address', tracking=True)
    total_area = fields.Float(string='Total Area (Acres)', tracking=True)
    active = fields.Boolean(default=True)



    # THE RELATIONSHIP: One venture has many plots
    plot_ids = fields.One2many('property.plot', 'venture_id', string='Farm Lands / Plots')

    # Smart fields to automatically count inventory
    total_plots = fields.Integer(compute='_compute_plot_counts', string='Total Plots')
    available_plots = fields.Integer(compute='_compute_plot_counts', string='Available Plots')

    @api.depends('plot_ids.status')
    def _compute_plot_counts(self):
        """Automatically calculates how many plots exist and how many are still available."""
        for venture in self:
            venture.total_plots = len(venture.plot_ids)
            venture.available_plots = len(venture.plot_ids.filtered(lambda p: p.status == 'available'))
    #

class PropertyPlot(models.Model):
    _name = 'property.plot'
    _description = 'Open Farm Land / Plot'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Plot Number (e.g., A-12)', required=True, tracking=True)

    # THE RELATIONSHIP: This plot belongs to one specific Venture
    venture_id = fields.Many2one('property.venture', string='Venture', required=True, ondelete='cascade', tracking=True)

    # Plot Details
    size = fields.Float(string='Size / Area', required=True, tracking=True)
    uom = fields.Selection([
        ('sq_yards', 'Sq Yards'),
        ('sq_meters', 'Sq Meters'),
        ('guntas', 'Guntas'),
        ('acres', 'Acres')
    ], string='Unit of Measure', default='sq_yards', required=True)

    facing = fields.Selection([
        ('east', 'East'), ('west', 'West'),
        ('north', 'North'), ('south', 'South'),
        ('north_east', 'North-East'), ('north_west', 'North-West'),
        ('south_east', 'South-East'), ('south_west', 'South-West')
    ], string='Facing', tracking=True)

    base_price = fields.Float(string='Base Price', tracking=True)

    # The Sales Lifecycle
    status = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('booked', 'Booked'),
        ('sold', 'Sold')
    ], string='Status', default='available', required=True, tracking=True)

    # Link to the Customer/Member buying the land
    customer_id = fields.Many2one('res.partner', string='Customer / Owner', tracking=True)

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', readonly=True, copy=False)

    # Safety Check: You can't book or sell a plot without attaching a customer!
    @api.constrains('status', 'customer_id')
    def _check_customer_status(self):
        for plot in self:
            if plot.status in ['booked', 'sold'] and not plot.customer_id:
                raise ValidationError(_("You must select a Customer before marking this plot as Booked or Sold."))

    def action_reserve(self):
        """Moves the plot to the Reserved state."""
        for plot in self:
            plot.status = 'reserved'

    def action_book(self):
        """Moves the plot to the Booked state.
        The existing @api.constrains will ensure a customer_id is set."""
        for plot in self:
            plot.status = 'booked'

    def action_create_sale_order(self):
        """Creates a Sale Order for the plot and moves it to the Sold state."""
        self.ensure_one()  # Ensure we are only clicking this on a single record

        if not self.customer_id:
            raise ValidationError(_("You must select a Customer / Owner before creating a Sale Order."))

        # 1. Find or create a generic Product to represent a Plot in the Sale Order
        Product = self.env['product.product']
        product = Product.search([('name', '=', 'Property Plot')], limit=1)
        if not product:
            product = Product.create({
                'name': 'Property Plot',
                'type': 'service',  # 'service' prevents inventory delivery issues for land
                'list_price': 0.0,
            })

        # 2. Create the Sale Order and Line
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer_id.id,
            'origin': self.name,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': f"Venture: {self.venture_id.name} | Plot: {self.name}",
                'product_uom_qty': 1.0,
                'price_unit': self.base_price,
            })]
        })

        # 3. Update the Plot status and link the SO
        self.write({
            'status': 'sold',
            'sale_order_id': sale_order.id
        })

        # 4. Automatically open the newly created Sale Order
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sale Order'),
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }