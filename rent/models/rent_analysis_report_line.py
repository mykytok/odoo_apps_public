from odoo import models, fields, api
from datetime import date


class RentAnalysisReportLine(models.TransientModel):
    _name = 'rent.analysis.report.line'
    _description = 'Rent Analysis Report Line (Transient)'
    _rec_name = 'rental_object_name'  # Для кращого відображення записів

    rental_object_id = fields.Many2one('rent.rental.object', string='Rental Object', readonly=True)
    rental_object_name = fields.Char(string='Rental Object', readonly=True)

    date_from = fields.Date(string='Report Start Date', readonly=True)
    date_to = fields.Date(string='Report End Date', readonly=True)

    company_currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)

    rental_amount = fields.Monetary(string='Rental Amount', currency_field='company_currency_id', readonly=True)
    exploitation_amount = fields.Monetary(string='Exploitation Amount', currency_field='company_currency_id',
                                          readonly=True)
    marketing_amount = fields.Monetary(string='Marketing Amount', currency_field='company_currency_id', readonly=True)
    rent_total = fields.Monetary(string='Total Rent', currency_field='company_currency_id', readonly=True)

    # group fields for Pivot
    report_year = fields.Integer(string='Year')
    report_month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
        ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'),
        ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')
    ], string='Month')

    report_date = fields.Date(string='Date')

    contract_id = fields.Many2one(comodel_name='rent.contract')