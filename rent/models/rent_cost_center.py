from odoo import models, fields


class CostCenter(models.Model):
    """A model for storing Cost Centers
                    """

    _name = 'rent.cost.center'
    _description = 'Cost center'

    name = fields.Char(translate=True)
    active = fields.Boolean(default=True)
    rental_object_id = fields.Many2one(
        comodel_name='rent.rental.object'
    )
    area_size = fields.Float(
        string='Area size',
        help="Area of the cost center in square meters."
    )
    planned_monthly_revenue_ids = fields.One2many(
        comodel_name='rent.planned.monthly.revenue',
        inverse_name='cost_center_id',
        string='Planned monthly revenue'
    )
    actual_monthly_revenue_ids = fields.One2many(
        comodel_name='rent.actual.monthly.revenue',
        inverse_name='cost_center_id',
        string='Actual monthly revenue'
    )

    def open_planned_monthly_revenue_list(self):
        self.ensure_one()
        return {
            'name': 'Planned monthly revenue',
            'views': [[self.env.ref('rent.view_rent_planned_monthly_revenue_list').id, 'list']],
            'type': 'ir.actions.act_window',
            'res_model': 'rent.planned.monthly.revenue',
            'view_mode': 'list',
            'res_id': False,
            'target': 'self',
            'domain': [('cost_center_id', '=', self.id)],
        }