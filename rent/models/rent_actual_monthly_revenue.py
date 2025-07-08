from odoo import models


class ActualMonthlyRevenue(models.Model):

    _name = 'rent.actual.monthly.revenue'
    _inherit = 'rent.abstract.monthly.revenue'
    _description = 'Actual monthly revenue'
    