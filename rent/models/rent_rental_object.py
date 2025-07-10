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
                        a breakdown by effective periods with their converted rates,
                        and totals in company currency for the entire range.
        """
        rent_calculations = []
        rental_objects = self.search([])

        company_currency = self.env.company.currency_id

        for obj in rental_objects:
            effective_periods_breakdown = []

            # Totals for the current rental object in company currency for the entire range
            total_rental_amount_company_currency = 0.0
            total_exploitation_amount_company_currency = 0.0
            total_marketing_amount_company_currency = 0.0
            total_rent_all_types_company_currency = 0.0

            # Get all contracts for the current rental object that intersect with the report range.
            active_contracts = self.env['rent.contract'].search([
                ('rental_object_id', '=', obj.id),
                ('date', '<=', date_to),
                ('expiration_date', '>=', date_from),
            ], order='date desc, id desc')

            # --- Step 1: Collect all significant dates within the report range ---
            significant_dates = {date_from, date_to + timedelta(days=1)}

            for contract in active_contracts:
                if contract.date <= date_to and contract.date >= date_from:
                    significant_dates.add(contract.date)
                if contract.expiration_date >= date_from and contract.expiration_date < date_to:
                    significant_dates.add(contract.expiration_date + timedelta(days=1))

            sorted_dates = sorted(list(significant_dates))

            # --- Step 2: Iterate through the intervals defined by significant dates ---
            for i in range(len(sorted_dates) - 1):
                interval_start = sorted_dates[i]
                interval_end = sorted_dates[i + 1] - timedelta(days=1)

                # Ensure the interval is within the report range
                current_interval_start = max(interval_start, date_from)
                current_interval_end = min(interval_end, date_to)

                if current_interval_start > current_interval_end:
                    continue

                # Find the highest priority contract active for this interval
                effective_contract = None
                for contract in active_contracts:
                    # Check if the contract fully covers the current effective interval
                    if contract.date <= current_interval_start and contract.expiration_date >= current_interval_end:
                        effective_contract = contract
                        break

                # Default values if no contract applies to this period
                period_rental_amount = 0.0
                period_exploitation_amount = 0.0
                period_marketing_amount = 0.0

                # Converted amounts for report
                period_rental_amount_company_currency = 0.0
                period_exploitation_amount_company_currency = 0.0
                period_marketing_amount_company_currency = 0.0
                period_total_amount_company_currency = 0.0

                period_currency_rental_symbol = company_currency.symbol
                period_currency_exploitation_symbol = company_currency.symbol
                period_currency_marketing_symbol = company_currency.symbol

                period_tax_rental_name = ''
                period_tax_exploitation_name = ''
                period_tax_marketing_name = ''

                period_contract_id = False
                period_contract_name = 'No Active Contract'

                if effective_contract:
                    days_in_period = (current_interval_end - current_interval_start).days + 1

                    # Determine the month for which the daily rate is calculated
                    # This is crucial because monthly rates are divided by days in *that* month.
                    # For simplicity, we'll use the month of the interval's start date.
                    # If an interval spans multiple months, this approach would need refinement
                    # (e.g., splitting the interval by month boundaries).
                    # For a single monthly rate application, this is usually sufficient.

                    # For accurate prorating across months within one period, it's safer to break down
                    # a given interval into sub-intervals that fall within a single calendar month.
                    # This ensures correct `days_in_month` is used for each part.

                    # Let's refine this to handle multi-month intervals correctly for prorating
                    temp_start = current_interval_start
                    while temp_start <= current_interval_end:
                        current_month_day_count = calendar.monthrange(temp_start.year, temp_start.month)[1]

                        # Determine the end of the current month segment within the interval
                        end_of_current_month = date(temp_start.year, temp_start.month, current_month_day_count)
                        segment_end = min(current_interval_end, end_of_current_month)

                        days_in_segment = (segment_end - temp_start).days + 1

                        # Calculate proportional amounts for this segment
                        rental_tax_indicator = effective_contract.rental_rate_tax_id.amount / 100 \
                            if effective_contract.rental_rate_tax_id.amount_type == 'percent' \
                            else 1
                        segment_rental_amount = (
                                (effective_contract.rental_rate / current_month_day_count) * days_in_segment
                                * rental_tax_indicator)
                        exploitation_tax_indicator = effective_contract.exploitation_rate_tax_id.amount / 100 \
                            if effective_contract.exploitation_rate_tax_id.amount_type == 'percent' \
                            else 1
                        segment_exploitation_amount = (
                                (effective_contract.exploitation_rate / current_month_day_count) * days_in_segment
                                * exploitation_tax_indicator)
                        marketing_tax_indicator = effective_contract.marketing_rate_tax_id.amount / 100 \
                            if effective_contract.marketing_rate_tax_id.amount_type == 'percent' \
                            else 1
                        segment_marketing_amount = (
                                (effective_contract.marketing_rate / current_month_day_count) * days_in_segment
                                *marketing_tax_indicator)

                        # Accumulate total original amounts for the full period
                        period_rental_amount += segment_rental_amount
                        period_exploitation_amount += segment_exploitation_amount
                        period_marketing_amount += segment_marketing_amount

                        # Convert amounts for this segment to company currency at end-of-month rate
                        conversion_date = date(temp_start.year, temp_start.month,
                                               current_month_day_count)  # End of segment's month

                        segment_rental_cc = effective_contract.rental_rate_currency_id.with_context(
                            date=conversion_date)._convert(
                            segment_rental_amount, company_currency, self.env.company, round=True
                        )
                        segment_exploitation_cc = effective_contract.exploitation_rate_currency_id.with_context(
                            date=conversion_date)._convert(
                            segment_exploitation_amount, company_currency, self.env.company, round=True
                        )
                        segment_marketing_cc = effective_contract.marketing_rate_currency_id.with_context(
                            date=conversion_date)._convert(
                            segment_marketing_amount, company_currency, self.env.company, round=True
                        )

                        # Accumulate total converted amounts for the full period
                        period_rental_amount_company_currency += segment_rental_cc
                        period_exploitation_amount_company_currency += segment_exploitation_cc
                        period_marketing_amount_company_currency += segment_marketing_cc
                        period_total_amount_company_currency += (
                                    segment_rental_cc + segment_exploitation_cc + segment_marketing_cc)

                        temp_start = segment_end + timedelta(days=1)

                    # Set common period details from the effective contract
                    period_currency_rental_symbol = effective_contract.rental_rate_currency_id.symbol
                    period_currency_exploitation_symbol = effective_contract.exploitation_rate_currency_id.symbol
                    period_currency_marketing_symbol = effective_contract.marketing_rate_currency_id.symbol

                    period_tax_rental_name = effective_contract.rental_rate_tax_id.name if effective_contract.rental_rate_tax_id else ''
                    period_tax_exploitation_name = effective_contract.exploitation_rate_tax_id.name if effective_contract.exploitation_rate_tax_id else ''
                    period_tax_marketing_name = effective_contract.marketing_rate_tax_id.name if effective_contract.marketing_rate_tax_id else ''

                    period_contract_id = effective_contract.id
                    period_contract_name = effective_contract.name

                effective_periods_breakdown.append({
                    'start_date': current_interval_start.isoformat(),
                    'end_date': current_interval_end.isoformat(),
                    'days_in_period': (current_interval_end - current_interval_start).days + 1,
                    'contract_details': {
                        'id': period_contract_id,
                        'name': period_contract_name,
                    },
                    # Original amounts (accumulated from segments within the period)
                    'original_rental': {'amount': period_rental_amount, 'currency': period_currency_rental_symbol,
                                        'tax': period_tax_rental_name},
                    'original_exploitation': {'amount': period_exploitation_amount,
                                              'currency': period_currency_exploitation_symbol,
                                              'tax': period_tax_exploitation_name},
                    'original_marketing': {'amount': period_marketing_amount,
                                           'currency': period_currency_marketing_symbol,
                                           'tax': period_tax_marketing_name},

                    # Converted amounts (accumulated from segments within the period)
                    'rental_company_currency': period_rental_amount_company_currency,
                    'exploitation_company_currency': period_exploitation_amount_company_currency,
                    'marketing_company_currency': period_marketing_amount_company_currency,
                    'total_period_company_currency': period_total_amount_company_currency,
                })

                # Accumulate totals for the rental object in company currency for the entire range
                total_rental_amount_company_currency += period_rental_amount_company_currency
                total_exploitation_amount_company_currency += period_exploitation_amount_company_currency
                total_marketing_amount_company_currency += period_marketing_amount_company_currency
                total_rent_all_types_company_currency += period_total_amount_company_currency

            rent_calculations.append({
                'rental_object_id': obj.id,
                'rental_object_name': obj.name,
                'report_date_from': date_from.isoformat(),
                'report_date_to': date_to.isoformat(),
                'company_currency_symbol': company_currency.symbol,
                'company_currency_name': company_currency.name,

                'total_rental_amount_company_currency': total_rental_amount_company_currency,
                'total_exploitation_amount_company_currency': total_exploitation_amount_company_currency,
                'total_marketing_amount_company_currency': total_marketing_amount_company_currency,
                'total_rent_all_types_company_currency': total_rent_all_types_company_currency,

                'effective_periods_breakdown': effective_periods_breakdown,
            })
        return rent_calculations