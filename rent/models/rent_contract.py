import calendar
from datetime import date, timedelta

from odoo import models, fields, api, _
from odoo.tools.misc import format_date
from odoo.exceptions import ValidationError


class Contract(models.Model):
    """A model for storing Rental Contracts
                    """

    _name = 'rent.contract'
    _description = 'Contract'

    name = fields.Char(
        compute='_compute_name',
    )
    active = fields.Boolean(default=True)
    rental_object_id = fields.Many2one(
        comodel_name='rent.rental.object',
        string='Rental object'
    )
    number = fields.Char()
    date = fields.Date()
    expiration_date = fields.Date()  # last day of contract
    contract_type = fields.Selection(
        [('contract', 'Contract'),
         ('main_additional_agreement', 'Main additional agreement'),
         ('additional_agreement', 'Additional agreement')],
        string='Type of contract',
        required=True
    )

    # Rental Rate
    rental_rate = fields.Monetary(currency_field='rental_rate_currency_id',
                                  required=True,
                                  help="Rental Rate (Monthly).")
    rental_rate_currency_id = fields.Many2one(
        comodel_name='res.currency',
        required=True,
        default=lambda self: self.env.company.currency_id.id)
    rental_rate_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string='Rental Rate Tax')

    # Exploitation Rate
    exploitation_rate = fields.Monetary(
        currency_field='exploitation_rate_currency_id',
        required=True,
        help="Exploitation Rate (Monthly).")
    exploitation_rate_currency_id = fields.Many2one(
        comodel_name='res.currency',
        required=True,
        default=lambda self: self.env.company.currency_id.id)
    exploitation_rate_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string='Exploitation Rate Tax')

    # Marketing Rate
    marketing_rate = fields.Monetary(
        currency_field='marketing_rate_currency_id',
        required=True,
        help="Marketing Rate (Monthly).")
    marketing_rate_currency_id = fields.Many2one(
        comodel_name='res.currency',
        required=True,
        default=lambda self: self.env.company.currency_id.id)
    marketing_rate_tax_id = fields.Many2one(comodel_name='account.tax')

    res_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner',
        help="The partner associated with this contract."
    )

    @api.depends('rental_object_id.name', 'number', 'date')
    @api.onchange('rental_object_id', 'number', 'date')
    def _compute_name(self):
        for record in self:
            record.name = (_("#%(number)s from %(date)s to %(expiration_date)s (%(rental_object)s)") %
                           {'number': record.number,
                            'date': format_date(env=self.env, value=record.date),
                            'expiration_date': format_date(env=self.env, value=record.expiration_date),
                            'rental_object': record.rental_object_id.name}
                           )

    @api.model
    def get_last_rental_object_contract(self, rental_object_id):
        """
        Finds the last (newest) contract of type 'contract' for a specific rental object.
        This method is for the _compute_actual_contract_number_date on RentalObject.
        """
        return self.search([
            ('rental_object_id', '=', rental_object_id),
            ('contract_type', '=', 'contract'),
            ('active', '=', True)
        ], order='date desc', limit=1)

    @api.model
    def _get_active_contracts_for_object(self, rental_object, date_from, date_to):
        """
        Retrieves all active contracts for a given rental object that intersect with the report range.
        """
        return self.search([
            ('rental_object_id', '=', rental_object.id),
            ('date', '<=', date_to),
            ('expiration_date', '>=', date_from),
            ('active', '=', True),
        ], order='date desc, id desc')

    @api.model
    def _get_significant_dates(self, date_from, date_to, active_contracts):
        """
        Collects all significant dates (contract start/end, report start/end)
        within the report range to define calculation intervals.
        """
        significant_dates = {date_from, date_to + timedelta(days=1)}

        for contract in active_contracts:
            if date_from <= contract.date <= date_to:
                significant_dates.add(contract.date)
            if date_from <= contract.expiration_date < date_to:
                significant_dates.add(contract.expiration_date + timedelta(days=1))

        return sorted(list(significant_dates))

    @api.model
    @staticmethod
    def _generate_intervals(sorted_dates, report_date_from, report_date_to):
        """
        Generates time intervals based on sorted significant dates,
        ensuring they are within the main report range.
        """
        for i in range(len(sorted_dates) - 1):
            interval_start = sorted_dates[i]
            interval_end = sorted_dates[i + 1] - timedelta(days=1)

            current_effective_start = max(interval_start, report_date_from)
            current_effective_end = min(interval_end, report_date_to)

            if current_effective_start <= current_effective_end:
                yield current_effective_start, current_effective_end

    @api.model
    def _get_effective_contract(self, active_contracts, interval_start, interval_end):
        """
        Finds the highest priority contract (newest) that fully covers the given interval.
        """
        for contract in active_contracts:
            if contract.date <= interval_start and contract.expiration_date >= interval_end:
                return contract
        return None

    @api.model
    def _calculate_monthly_segments(self,
                                    rental_object,
                                    effective_contract,
                                    interval_start, interval_end,
                                    company_currency):
        """
        Calculates rent for each monthly segment within a given interval
        based on the effective contract.
        This method is now part of rent.contract and receives rental_object and company_currency
        as arguments, as it needs information from those models.
        """
        monthly_segments_data = []
        temp_segment_start = interval_start

        while temp_segment_start <= interval_end:
            current_month_day_count = calendar.monthrange(temp_segment_start.year,
                                                          temp_segment_start.month)[1]
            end_of_current_month = date(temp_segment_start.year,
                                        temp_segment_start.month,
                                        current_month_day_count)
            segment_actual_end = min(interval_end, end_of_current_month)
            days_in_segment = (segment_actual_end - temp_segment_start).days + 1

            segment_data = self._initialize_segment_data(rental_object,
                                                         temp_segment_start,
                                                         segment_actual_end,
                                                         days_in_segment,
                                                         company_currency)  # Pass company_currency here

            if effective_contract:
                self._apply_contract_rates(segment_data, effective_contract,
                                           days_in_segment, current_month_day_count)
                self._convert_to_company_currency(segment_data, effective_contract,
                                                  company_currency, end_of_current_month)
                self._set_contract_details(segment_data, effective_contract)

            monthly_segments_data.append(segment_data)
            temp_segment_start = segment_actual_end + timedelta(days=1)

        return monthly_segments_data

    @api.model
    def _initialize_segment_data(self, rental_object, segment_start_date, segment_end_date, days_in_segment,
                                 company_currency):
        """
        Initializes a dictionary with default values for a monthly segment.
        Now takes company_currency as an argument.
        """
        return {
            'rental_object_id': rental_object.id,
            'rental_object_name': rental_object.name,
            'date_from': segment_start_date.isoformat(),
            'date_to': segment_end_date.isoformat(),
            'report_date': segment_end_date,
            'days_in_period': days_in_segment,
            'contract_id': False,
            'contract_name': 'No Active Contract',
            'original_rental': {'amount': 0.0, 'currency': '', 'tax': ''},
            'original_exploitation': {'amount': 0.0, 'currency': '', 'tax': ''},
            'original_marketing': {'amount': 0.0, 'currency': '', 'tax': ''},
            'rental_amount': 0.0,
            'exploitation_amount': 0.0,
            'marketing_amount': 0.0,
            'rent_total': 0.0,
            'company_currency_id': company_currency.id,  # Use passed currency
            'company_currency_symbol': company_currency.symbol,
            'company_currency_name': company_currency.name,
        }

    @api.model
    @staticmethod
    def _apply_tax_indicator(tax_id):
        """
        Calculates the tax indicator for a given tax.
        Raises ValidationError if the tax amount type is not 'percent'.
        """
        if tax_id:
            if tax_id.amount_type == 'percent':
                return (tax_id.amount / 100) + 1
            else:
                raise ValidationError(_(
                    "Tax '%(tax)s' (ID: %(tax_id)s) has an unsupported amount type '%(amount_type)s'. "
                    "Only 'percent' type taxes are allowed for this calculation."
                ) % {'tax': tax_id.name, 'tax_id': tax_id.id, 'amount_type': tax_id.amount_type})
        return 1

    @api.model
    def _apply_contract_rates(self, segment_data, contract, days_in_segment, current_month_day_count):
        """
        Calculates original amounts for rental, exploitation, and marketing
        based on the effective contract and applies tax indicators.
        """
        rental_tax_indicator = self._apply_tax_indicator(contract.rental_rate_tax_id)
        segment_data['original_rental']['amount'] = (
                (contract.rental_rate / current_month_day_count) * days_in_segment * rental_tax_indicator
        )

        exploitation_tax_indicator = self._apply_tax_indicator(contract.exploitation_rate_tax_id)
        segment_data['original_exploitation']['amount'] = (
                (contract.exploitation_rate / current_month_day_count)
                * days_in_segment
                * exploitation_tax_indicator
        )

        marketing_tax_indicator = self._apply_tax_indicator(contract.marketing_rate_tax_id)
        segment_data['original_marketing']['amount'] = (
                (contract.marketing_rate / current_month_day_count)
                * days_in_segment * marketing_tax_indicator
        )

    @api.model
    def _convert_to_company_currency(self, segment_data, contract, company_currency, conversion_date):
        """
        Converts calculated segment amounts to the company's main currency.
        """

        def convert_amount(amount, from_currency):
            if from_currency:
                return from_currency.with_context(date=conversion_date)._convert(
                    amount, company_currency, self.env.company, round=True
                )
            return 0.0

        segment_data['rental_amount'] = convert_amount(
            segment_data['original_rental']['amount'], contract.rental_rate_currency_id
        )
        segment_data['exploitation_amount'] = convert_amount(
            segment_data['original_exploitation']['amount'], contract.exploitation_rate_currency_id
        )
        segment_data['marketing_amount'] = convert_amount(
            segment_data['original_marketing']['amount'], contract.marketing_rate_currency_id
        )

        segment_data['rent_total'] = (
                segment_data['rental_amount'] +
                segment_data['exploitation_amount'] +
                segment_data['marketing_amount']
        )

    @api.model
    def _set_contract_details(self, segment_data, contract):
        """
        Sets contract-related details in the segment data.
        """
        segment_data['contract_id'] = contract.id
        segment_data['contract_name'] = contract.name

        segment_data['original_rental']['currency'] = (
            contract.rental_rate_currency_id.symbol) if contract.rental_rate_currency_id else ''
        segment_data['original_exploitation']['currency'] = (
            contract.exploitation_rate_currency_id.symbol) if contract.exploitation_rate_currency_id else ''
        segment_data['original_marketing']['currency'] = (
            contract.marketing_rate_currency_id.symbol) if contract.marketing_rate_currency_id else ''

        segment_data['original_rental']['tax'] = (
            contract.rental_rate_tax_id.name) if contract.rental_rate_tax_id else ''
        segment_data['original_exploitation']['tax'] = (
            contract.exploitation_rate_tax_id.name) if contract.exploitation_rate_tax_id else ''
        segment_data['original_marketing']['tax'] = (
            contract.marketing_rate_tax_id.name) if contract.marketing_rate_tax_id else ''
