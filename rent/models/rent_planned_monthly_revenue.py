from odoo import models


class PlannedMonthlyRevenue(models.Model):

    _name = 'rent.planned.monthly.revenue'
    _inherit = 'rent.abstract.monthly.revenue'
    _description = 'Planned monthly revenue'