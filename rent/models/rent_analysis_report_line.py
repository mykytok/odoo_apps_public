from odoo import models, fields


class RentAnalysisReportLine(models.TransientModel):
    _name = 'rent.analysis.report.line'
    _description = 'Rent Analysis Report Line (Transient)'

    rental_object_id = fields.Many2one(
        comodel_name='rent.rental.object',
        string='Rental Object',
        readonly=True)
    
    cost_center_id = fields.Many2one(
        comodel_name='rent.cost.center',
        string='Cost Center',
        readonly=True)

    company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency', readonly=True)

    rental_amount = fields.Monetary(currency_field='company_currency_id',
                                    readonly=True)
    exploitation_amount = fields.Monetary(currency_field='company_currency_id',
                                          readonly=True)
    marketing_amount = fields.Monetary(currency_field='company_currency_id',
                                       readonly=True)
    rent_total = fields.Monetary(
        string='Total Rent',
        currency_field='company_currency_id',
        readonly=True)

    date_from = fields.Date(string='Date from')
    date_to = fields.Date(string='Date to')

    contract_id = fields.Many2one(comodel_name='rent.contract')

    rental_currency_coef = fields.Float(
        string='Rental currency coefficient',
        help="Currency change coefficient from the start of the contract to the current month."
    )
    exploitation_currency_coef = fields.Float(
        string='Exploitation currency coefficient',
        help="Currency change coefficient from the start of the contract to the current month."
    )
    marketing_currency_coef = fields.Float(
        string='Marketing currency coefficient',
        help="Currency change coefficient from the start of the contract to the current month."
    )