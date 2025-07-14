from odoo import models, fields


class RentAnalysisReportLine(models.TransientModel):
    _name = 'rent.analysis.report.line'
    _description = 'Rent Analysis Report Line (Transient)'

    rental_object_id = fields.Many2one(
        comodel_name='rent.rental.object',
        string='Rental Object',
        readonly=True)

    date_from = fields.Date(string='Report Start Date', readonly=True)
    date_to = fields.Date(string='Report End Date', readonly=True)

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

    report_date = fields.Date(string='Date')

    contract_id = fields.Many2one(comodel_name='rent.contract')
