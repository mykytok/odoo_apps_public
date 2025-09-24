import calendar
from datetime import date, timedelta

from odoo import models, fields, api, _
from odoo.tools.misc import format_date
from odoo.exceptions import ValidationError


class Contract(models.Model):
    """A model for storing Rental Contracts
                    """

    _name = 'rent.contract'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', ]
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

    rent_indexation = fields.Float(
        help="Annual indexation (increase) of rent."
    )
    initial_rent_indexation_date = fields.Date()

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
                self._apply_contract_rates(segment_data, effective_contract,
                                           days_in_segment, current_month_day_count)
                self._convert_to_company_currency(segment_data, effective_contract,
                                                  company_currency, end_of_current_month)
                self._apply_currency_coef(segment_data, effective_contract, end_of_current_month)
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
            'days_in_period': days_in_segment,
            'current_month_day_count': calendar.monthrange(segment_start_date.year,
                                                          segment_start_date.month)[1],
            'contract_id': False,
            'contract_name': 'No Active Contract',
            'area_size': rental_object.area_size,
            'indexation_coefficient': 0.0,
            'rental_currency_coef': 0.0,
            'exploitation_currency_coef': 0.0,
            'marketing_currency_coef': 0.0,
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
            if tax_id.amount_type != 'percent':
                raise ValidationError(_(
                    "Tax '%(tax)s' (ID: %(tax_id)s) has an unsupported amount type '%(amount_type)s'. "
                    "Only 'percent' type taxes are allowed for this calculation."
                ) % {'tax': tax_id.name, 'tax_id': tax_id.id, 'amount_type': tax_id.amount_type})
            return (tax_id.amount / 100) + 1
        return 1

    @api.model
    def _get_rent_indexation_coefficient(self, contract, calc_date):
        """
        Calculates the rent indexation coefficient, applying the first indexation
        immediately on initial_rent_indexation_date and compounding annually thereafter.
        
        Args:
            contract (odoo.models): The contract record.
            calc_date (datetime.date): The date of the current rent calculation segment.

        Returns:
            float: The indexation coefficient, or 1.0 if no indexation applies yet.
        """

        last_day_of_month = calendar.monthrange(calc_date.year, calc_date.month)[1]
        repot_date = date(calc_date.year, calc_date.month, last_day_of_month)


        if not contract.initial_rent_indexation_date or not contract.rent_indexation:
            return 1.0

        initial_date = contract.initial_rent_indexation_date
        indexation_rate = contract.rent_indexation / 100.0
        
        # If the date is before the initial indexation date, no indexation
        if repot_date < initial_date:
            return 1.0

        # Calculate the number of full years passed since the initial date
        years_for_indexation = (repot_date.year - initial_date.year)
        
        # Add 1 to the count if the segment date has reached or passed the anniversary of the initial date
        if (repot_date.month, repot_date.day) >= (initial_date.month, initial_date.day):
            years_for_indexation += 1
            
        # The first year has a coefficient of 1 + indexation_rate
        # Example: initial_date = 2024-05-15, date = 2024-05-16
        # years_for_indexation = (2024-2024) + 1 = 1.
        # So the coefficient is (1 + 0.05)**1 = 1.05
        # Example: initial_date = 2024-05-15, date = 2025-05-16
        # years_for_indexation = (2025-2024) + 1 = 2.
        # So the coefficient is (1 + 0.05)**2 = 1.1025
        
        # Calculate the compound indexation coefficient
        return (1 + indexation_rate) ** years_for_indexation
    
    @api.model
    def _apply_contract_rates(self, segment_data, contract, days_in_segment, current_month_day_count):
        """
        Calculates original amounts for rental, exploitation, and marketing
        based on the effective contract and applies tax indicators.
        """

        rental_object = self.env['rent.rental.object'].browse(segment_data['rental_object_id'])

        rental_tax_indicator = self._apply_tax_indicator(contract.rental_rate_tax_id)

        # Convert date string back to a date object for comparison
        repot_date = date.fromisoformat(segment_data['date_from'])

        # Get the rent indexation coefficient for the current segment date
        indexation_coefficient = self._get_rent_indexation_coefficient(
            contract,
            repot_date
        )
        segment_data['indexation_coefficient'] = indexation_coefficient

        segment_data['original_rental']['amount'] = (
                (contract.rental_rate / current_month_day_count) 
                * days_in_segment 
                * rental_tax_indicator 
                * segment_data['area_size']
                * indexation_coefficient
        )

        exploitation_tax_indicator = self._apply_tax_indicator(contract.exploitation_rate_tax_id)
        segment_data['original_exploitation']['amount'] = (
                (contract.exploitation_rate / current_month_day_count)
                * days_in_segment
                * exploitation_tax_indicator
                * segment_data['area_size']
                * indexation_coefficient
        )

        marketing_tax_indicator = self._apply_tax_indicator(contract.marketing_rate_tax_id)
        segment_data['original_marketing']['amount'] = (
                (contract.marketing_rate / current_month_day_count)
                * days_in_segment 
                * marketing_tax_indicator
                * segment_data['area_size']
                * indexation_coefficient
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
    def _apply_currency_coef(self, segment_data, contract, conversion_date):
        """
        Fills in the currency change coefficient
        from the start of the contract to the current month.
        """
        # Pass the ID of the currency recordset, not the recordset itself
        rental_currency_id = contract.rental_rate_currency_id.id if contract.rental_rate_currency_id else False
        exploitation_currency_id = contract.exploitation_rate_currency_id.id if contract.exploitation_rate_currency_id else False
        marketing_currency_id = contract.marketing_rate_currency_id.id if contract.marketing_rate_currency_id else False

        # Check if currency_id is valid before calling the method
        if rental_currency_id:
            segment_data['rental_currency_coef'] = self._get_currency_coefficient_for_dates(
                rental_currency_id, contract.date, conversion_date
            )
        else:
            segment_data['rental_currency_coef'] = 1.0

        if exploitation_currency_id:
            segment_data['exploitation_currency_coef'] = self._get_currency_coefficient_for_dates(
                exploitation_currency_id, contract.date, conversion_date
            )
        else:
            segment_data['exploitation_currency_coef'] = 1.0

        if marketing_currency_id:
            segment_data['marketing_currency_coef'] = self._get_currency_coefficient_for_dates(
                marketing_currency_id, contract.date, conversion_date
            )
        else:
            segment_data['marketing_currency_coef'] = 1.0

        # The rest of your code for calculations...
        segment_data['rental_amount'] = (
                segment_data['rental_amount'] * segment_data['rental_currency_coef'])
        segment_data['exploitation_amount'] = (
                segment_data['exploitation_amount'] * segment_data['exploitation_currency_coef'])
        segment_data['marketing_amount'] = (
                segment_data['marketing_amount'] * segment_data['marketing_currency_coef'])

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

    @api.model
    def _get_currency_coefficient_for_dates(self, currency_id, date1, date2):
        """
        Retrieves the coefficient of a single currency against the company's currency on two specific dates.

        Args:
            currency_id (int): The ID of the currency to analyze.
            date1 (date): The first date for which to get the rate.
            date2 (date): The second date for which to get the rate.

        Returns:
            float: The currency coefficient, or 1 if the coefficient is less than 1.
        """
        # Get the currency object to analyze and the company's currency
        currency_to_analyze = self.env['res.currency'].browse(currency_id)
        company_currency = self.env.company.currency_id

        # If the currency doesn't exist, or it is the company's currency, the coefficient is 1.0.
        if not currency_to_analyze or currency_to_analyze == company_currency:
            return 1.0

        # Get the rate for the first date: convert 1 unit of the analyzed currency to the company currency
        rate_date1 = currency_to_analyze.with_context(date=date1).inverse_rate

        # Get the rate for the second date
        rate_date2 = currency_to_analyze.with_context(date=date2).inverse_rate

        # Avoid division by zero if the first rate is zero
        if rate_date1 == 0: 
            return 1.0

        # Calculate the currency coefficient
        currency_coefficient = rate_date2 / rate_date1
        
        # Return the coefficient, or 1 if it's less than 1
        if currency_coefficient < 1: 
            return 1.0
            
        return currency_coefficient