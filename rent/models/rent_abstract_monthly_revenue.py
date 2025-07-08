from datetime import datetime

from odoo import models, fields, api


class AbstractMonthlyRevenue(models.AbstractModel):
    """Abstract person model
                """
    _name = 'rent.abstract.monthly.revenue'
    _description = 'Monthly revenue'

    name = fields.Char(
        compute='_compute_name',
        store=True,
    )
    active = fields.Boolean(default=True)
    cost_center_id = fields.Many2one(
        comodel_name='rent.cost.center',
        string='Cost center'
    )
    date = fields.Date(string='Date')
    revenue = fields.Float(string="Revenue")

    @api.depends('cost_center_id')
    @api.onchange('cost_center_id')
    @api.depends('date')
    @api.onchange('date')
    @api.depends('revenue')
    @api.onchange('revenue')
    def _compute_name(self):
        for record in self:
            record.name = ("%s %s %s" %
                           (record.cost_center_id.name,
                            fields.Date.to_string(record.date),
                            record.revenue)
                           )
