from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RentAnalysisWizard(models.TransientModel):
    _name = 'rent.analysis.wizard'
    _description = 'Rent Analysis Report Wizard'

    date_from = fields.Date(required=True,
                            default=lambda
                                self: date.today().replace(day=1))
    date_to = fields.Date(required=True,
                          default=lambda
                              self: date.today()
                                    + relativedelta(months=1, day=1)
                                    - timedelta(days=1)
                          )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise ValidationError(_("Start Date cannot be after End Date."))

    def action_generate_rent_analysis_report(self):
        """
        Generates rent analysis data by calling the calculation method
        and performs bulk creation of the transient report lines.
        """
        self.ensure_one()

        # 1. Get structured data ready for bulk creation
        report_results = self.env['rent.rental.object']._get_rent_calculation_for_range(
            self.date_from, self.date_to
        )

        # 2. Add fixed fields (like currency) before bulk creation
        company_currency_id = self.env.company.currency_id.id

        # Add company_currency_id to each dictionary
        for obj_data in report_results:
            obj_data['company_currency_id'] = company_currency_id

        # 3. Bulk creation of transient report lines
        # This is more efficient than individual .create() calls.
        report_lines = self.env['rent.analysis.report.line'].create(report_results)

        report_line_ids = report_lines.ids

        # 4. Return the Action to display the report
        return {
            'name': 'Rent Analysis',
            'type': 'ir.actions.act_window',
            'res_model': 'rent.analysis.report.line',
            'view_mode': 'pivot,graph,list',
            'domain': [('id', 'in', report_line_ids)],
            'target': 'current',
        }