from odoo import models


class PlannedMonthlyRevenue(models.Model):

    _name = 'rent.planned.monthly.revenue'
    _inherit = 'rent.abstract.monthly.revenue'
    _description = 'Planned monthly revenue'

    def open_planned_monthly_revenue_list(self):
        self.ensure_one()
        if not self.env.context.get('active_ids'):
            return None

        active_ids = (self.env['rent.planned.monthly.revenue']
                      .browse(self.env.context.get('active_ids')))
        if not active_ids:
            return None

        return {
            'name': 'Planned monthly revenue',
            'views': [[self.env.ref('rent.view_rent_planned_monthly_revenue_list').id, 'list']],
            'type': 'ir.actions.act_window',
            'res_model': 'rent.planned.monthly.revenue',
            'view_mode': 'list',
            'res_id': False,
            'target': 'self',
            'domain': [('cost_center_id', '=', active_ids.mapped('id'))],
        }
