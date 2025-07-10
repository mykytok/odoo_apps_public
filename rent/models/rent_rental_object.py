import logging

from odoo import models, fields, api, _
from odoo.tools.misc import format_date

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import calendar

_logger = logging.getLogger(__name__)

class RentalObject(models.Model):
    """A model for storing Rental Object
                    """

    _name = 'rent.rental.object'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', ]
    _description = 'Rental object'

    name = fields.Char(translate=True)
    active = fields.Boolean(default=True)
    rental_object_group_id = fields.Many2one(
        comodel_name='rent.rental.object.group'
    )
    area_size = fields.Float(
        string='Area size',
        help="Area of the rental property in square meters."
    )
    contract_ids = fields.One2many(
        comodel_name='rent.contract',
        inverse_name='rental_object_id',
        string="Contracts",
    )
    cost_center_ids = fields.One2many(
        comodel_name='rent.cost.center',
        inverse_name='rental_object_id',
        string="Cost centers",
    )

    actual_contract_number_date = fields.Char(
        compute='_compute_actual_contract_number_date',
        compute_sudo=True,
        store=True,
        string="Actual contract",
    )

    @api.depends('contract_ids')
    def _compute_actual_contract_number_date(self):
        for record in self:
            last_contract = self.env['rent.contract'].get_last_rental_object_contract(record.id)
            # last_contract = self._search_last_contract(record.id)
            if last_contract:
                record.actual_contract_number_date = (_("#%s from %s") %
                                                      (last_contract.number,
                                                       format_date(
                                                           env=self.env,
                                                           value=last_contract.date)
                                                       )
                                                      )
            else:
                record.actual_contract_number_date = None

    @api.model
    def _search_last_contract(self, rental_object_id):
        rec = self.env['rent.contract'].search(
            domain=[
                ('rental_object_id', '=', rental_object_id),
                ('contract_type', '=', 'contract')
            ],
            order='date desc',
            limit=1
        )
        if rec:
            return rec[0]
        return False

    @api.model
    def _get_rent_calculation_for_range(self, date_from, date_to):
        """
        Calculates the rent for each rental object for a given date range,
        considering three types of rates (rental, exploitation, marketing) from contracts.
        Rates are calculated proportionally for periods within the range.
        Periods of rates are determined by the newest active contract.
        If a newer contract ends, an older still active contract takes over.
        All amounts are converted to the company's main currency at the end-of-month rate
        for the respective month the period falls into.

        Args:
            date_from (date): The start date of the report period.
            date_to (date): The end date of the report period.

        Returns:
            list[dict]: A list of dictionaries, where each dictionary represents
                        the rent calculation for a rental object, including
                        a breakdown by **monthly segments** with their converted rates,
                        and totals in company currency for the entire range.
        """
        rent_calculations_by_month = []
        rental_objects = self.env['rent.rental.object'].search([])  # Correct search for rental objects

        company_currency = self.env.company.currency_id

        for obj in rental_objects:
            # Get all contracts for the current rental object that intersect with the report range.
            active_contracts = self.env['rent.contract'].search([
                ('rental_object_id', '=', obj.id),
                ('date', '<=', date_to),
                ('expiration_date', '>=', date_from),
                ('active', '=', True),
            ], order='date desc, id desc')

            # --- Step 1: Collect all significant dates within the report range ---
            significant_dates = {date_from, date_to + timedelta(days=1)}

            for contract in active_contracts:
                if contract.date <= date_to and contract.date >= date_from:
                    significant_dates.add(contract.date)
                # Note: `expiration_date` is inclusive, so we add day+1 to make interval exclusive end
                if contract.expiration_date >= date_from and contract.expiration_date < date_to:
                    significant_dates.add(contract.expiration_date + timedelta(days=1))

            sorted_dates = sorted(list(significant_dates))

            # --- Step 2: Iterate through the intervals defined by significant dates ---
            for i in range(len(sorted_dates) - 1):
                interval_start = sorted_dates[i]
                interval_end = sorted_dates[i + 1] - timedelta(days=1)

                # Ensure the interval is within the report range
                current_effective_start = max(interval_start, date_from)
                current_effective_end = min(interval_end, date_to)

                if current_effective_start > current_effective_end:
                    continue

                # Find the highest priority contract active for this effective interval
                effective_contract = None
                for contract in active_contracts:
                    # Check if the contract fully covers the current effective interval
                    if contract.date <= current_effective_start and contract.expiration_date >= current_effective_end:
                        effective_contract = contract
                        break

                temp_segment_start = current_effective_start
                while temp_segment_start <= current_effective_end:
                    current_month_day_count = calendar.monthrange(temp_segment_start.year, temp_segment_start.month)[1]
                    end_of_current_month = date(temp_segment_start.year, temp_segment_start.month,
                                                current_month_day_count)

                    # The end date for this monthly segment
                    segment_actual_end = min(current_effective_end, end_of_current_month)

                    days_in_segment = (segment_actual_end - temp_segment_start).days + 1

                    # Initialize amounts for this specific monthly segment
                    segment_rental_amount = 0.0
                    segment_exploitation_amount = 0.0
                    segment_marketing_amount = 0.0

                    segment_rental_amount_company_currency = 0.0
                    segment_exploitation_amount_company_currency = 0.0
                    segment_marketing_amount_company_currency = 0.0
                    segment_total_amount_company_currency = 0.0

                    segment_currency_rental_symbol = company_currency.symbol
                    segment_currency_exploitation_symbol = company_currency.symbol
                    segment_currency_marketing_symbol = company_currency.symbol

                    segment_tax_rental_name = ''
                    segment_tax_exploitation_name = ''
                    segment_tax_marketing_name = ''

                    segment_contract_id = False
                    segment_contract_name = 'No Active Contract'

                    if effective_contract:
                        segment_contract_id = effective_contract.id
                        segment_contract_name = effective_contract.name

                        rental_tax_indicator = (effective_contract.rental_rate_tax_id.amount / 100) + 1 \
                            if effective_contract.rental_rate_tax_id and effective_contract.rental_rate_tax_id.amount_type == 'percent' \
                            else 1
                        segment_rental_amount = (
                                (effective_contract.rental_rate / current_month_day_count) * days_in_segment
                                * rental_tax_indicator)

                        exploitation_tax_indicator = (effective_contract.exploitation_rate_tax_id.amount / 100) + 1 \
                            if effective_contract.exploitation_rate_tax_id and effective_contract.exploitation_rate_tax_id.amount_type == 'percent' \
                            else 1
                        segment_exploitation_amount = (
                                (effective_contract.exploitation_rate / current_month_day_count) * days_in_segment
                                * exploitation_tax_indicator)

                        marketing_tax_indicator = (effective_contract.marketing_rate_tax_id.amount / 100) + 1 \
                            if effective_contract.marketing_rate_tax_id and effective_contract.marketing_rate_tax_id.amount_type == 'percent' \
                            else 1
                        segment_marketing_amount = (
                                (effective_contract.marketing_rate / current_month_day_count) * days_in_segment
                                * marketing_tax_indicator)

                        # Convert amounts for this segment to company currency at end-of-month rate
                        # Use the last day of the segment's month for conversion rate
                        conversion_date = date(temp_segment_start.year, temp_segment_start.month,
                                               current_month_day_count)

                        segment_rental_amount_company_currency = effective_contract.rental_rate_currency_id.with_context(
                            date=conversion_date)._convert(
                            segment_rental_amount, company_currency, self.env.company, round=True
                        ) if effective_contract.rental_rate_currency_id else 0.0

                        segment_exploitation_amount_company_currency = effective_contract.exploitation_rate_currency_id.with_context(
                            date=conversion_date)._convert(
                            segment_exploitation_amount, company_currency, self.env.company, round=True
                        ) if effective_contract.exploitation_rate_currency_id else 0.0

                        segment_marketing_amount_company_currency = effective_contract.marketing_rate_currency_id.with_context(
                            date=conversion_date)._convert(
                            segment_marketing_amount, company_currency, self.env.company, round=True
                        ) if effective_contract.marketing_rate_currency_id else 0.0

                        segment_total_amount_company_currency = (segment_rental_amount_company_currency
                                                                 + segment_exploitation_amount_company_currency
                                                                 + segment_marketing_amount_company_currency)

                        segment_currency_rental_symbol = effective_contract.rental_rate_currency_id.symbol if effective_contract.rental_rate_currency_id else ''
                        segment_currency_exploitation_symbol = effective_contract.exploitation_rate_currency_id.symbol if effective_contract.exploitation_rate_currency_id else ''
                        segment_currency_marketing_symbol = effective_contract.marketing_rate_currency_id.symbol if effective_contract.marketing_rate_currency_id else ''

                        segment_tax_rental_name = effective_contract.rental_rate_tax_id.name if effective_contract.rental_rate_tax_id else ''
                        segment_tax_exploitation_name = effective_contract.exploitation_rate_tax_id.name if effective_contract.exploitation_rate_tax_id else ''
                        segment_tax_marketing_name = effective_contract.marketing_rate_tax_id.name if effective_contract.marketing_rate_tax_id else ''

                    # Append this monthly segment to the main list
                    rent_calculations_by_month.append({
                        'rental_object_id': obj.id,
                        'rental_object_name': obj.name,
                        'date_from': temp_segment_start.isoformat(),  # This segment's start date
                        'date_to': segment_actual_end.isoformat(),  # This segment's end date
                        'report_year': temp_segment_start.year,
                        'report_month': str(temp_segment_start.month),
                        'report_date': end_of_current_month,
                        'days_in_period': days_in_segment,
                        'contract_id': segment_contract_id,
                        'contract_name': segment_contract_name,

                        # Original amounts for the segment
                        'original_rental': {'amount': segment_rental_amount, 'currency': segment_currency_rental_symbol,
                                            'tax': segment_tax_rental_name},
                        'original_exploitation': {'amount': segment_exploitation_amount,
                                                  'currency': segment_currency_exploitation_symbol,
                                                  'tax': segment_tax_exploitation_name},
                        'original_marketing': {'amount': segment_marketing_amount,
                                               'currency': segment_currency_marketing_symbol,
                                               'tax': segment_tax_marketing_name},

                        # Converted amounts for the segment
                        'rental_amount': segment_rental_amount_company_currency,
                        'exploitation_amount': segment_exploitation_amount_company_currency,
                        'marketing_amount': segment_marketing_amount_company_currency,
                        'rent_total': segment_total_amount_company_currency,  # Total for this segment

                        'company_currency_id': company_currency.id,
                        'company_currency_symbol': company_currency.symbol,
                        'company_currency_name': company_currency.name,
                    })

                    # Move to the start of the next segment (next day after current segment ends)
                    temp_segment_start = segment_actual_end + timedelta(days=1)

        return rent_calculations_by_month
