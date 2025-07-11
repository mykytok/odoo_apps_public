from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import calendar  # Ensure calendar is imported if used in _get_rent_calculation_for_range


class RentAnalysisWizard(models.TransientModel):
    _name = 'rent.analysis.wizard'
    _description = 'Rent Analysis Report Wizard'

    date_from = fields.Date(string='Date From', required=True, default=lambda self: date.today().replace(day=1))
    date_to = fields.Date(string='Date To', required=True,
                          default=lambda self: date.today() + relativedelta(months=1, day=1) - timedelta(days=1))

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise ValidationError("Start Date cannot be after End Date.")

    def action_generate_rent_analysis_report(self):
        """
        Generates rent analysis data in a transient model and opens a view.
        """
        self.ensure_one()

        report_results = self.env['rent.rental.object']._get_rent_calculation_for_range(
            self.date_from, self.date_to
        )

        report_line_ids = []
        company_currency = self.env.company.currency_id  # Отримуємо об'єкт валюти

        for obj_data in report_results:
            report_line_ids.append(self.env['rent.analysis.report.line'].create({
                'rental_object_id': obj_data['rental_object_id'],
                'rental_object_name': obj_data['rental_object_name'],
                'date_from': obj_data['date_from'],
                'date_to': obj_data['date_to'],
                'report_date': obj_data['report_date'],
                'company_currency_id': company_currency.id,  # Передаємо ID валюти
                'rental_amount': obj_data['rental_amount'],
                'exploitation_amount': obj_data['exploitation_amount'],
                'marketing_amount': obj_data['marketing_amount'],
                'rent_total': obj_data['rent_total'],
                'contract_id': obj_data['contract_id'],
            }).id)

        return {
            'name': 'Rent Analysis',
            'type': 'ir.actions.act_window',
            'res_model': 'rent.analysis.report.line',
            'view_mode': 'pivot,graph',
            'domain': [('id', 'in', report_line_ids)],
            'target': 'current',
            'context': {
                'search_default_rental_object_id': 1,
                'group_by': ['rental_object_id'],
                'measures': ['rent_total'],
            }
        }