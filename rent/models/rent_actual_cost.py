from odoo import models, fields, api, _
from odoo.tools.misc import format_date

class RentActualCost(models.Model):
    _name = 'rent.actual.cost'
    _description = 'Actual Rent Costs'

    name = fields.Char(string="Name",
                       compute='_compute_name',)
    rental_object_id = fields.Many2one(
        comodel_name='rent.rental.object',
        string='Rental Object',
        required=True
    )
    date = fields.Date(string='Date', required=True)
    rental_cost = fields.Monetary(
        string='Rental',
        currency_field='company_currency_id',
    )
    exploitation_cost = fields.Monetary(
        string='Exploitation',
        currency_field='company_currency_id',
    )
    marketing_cost = fields.Monetary(
        string='Marketing',
        currency_field='company_currency_id',
    )
    total_cost = fields.Monetary(
        string='Total',
        currency_field='company_currency_id',
        compute='_compute_total_cost',
        store=True,
    )
    company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id,
    )
    
    _sql_constraints = [
        ('unique_date_rental_object',
         'unique(rental_object_id, date)',
         'Actual costs for this rental object already exist for this date.')
    ]

    @api.depends('rental_cost', 'exploitation_cost', 'marketing_cost')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.rental_cost + rec.exploitation_cost + rec.marketing_cost

    @api.depends('rental_object_id')
    @api.depends('date')
    @api.depends('total_cost')
    def _compute_name(self):
        for record in self:
            record.name = ("%s %s %s" %
                           (record.rental_object_id.name,
                            format_date(env=self.env, value=record.date),
                            record.total_cost)
                           )