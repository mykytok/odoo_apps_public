from datetime import date

from odoo import models, fields, api, _
from odoo.tools.misc import format_date


class RentalObject(models.Model):
    """A model for storing Rental Object
                    """

    _name = 'rent.rental.object'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', ]
    _description = 'Rental object'

    name = fields.Char(translate=True)
    active = fields.Boolean(default=True)
    comment = fields.Html(string='Notes')

    rental_object_group_id = fields.Many2one(
        comodel_name='rent.rental.object.group'
    )
    area_size = fields.Float(
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

    guarantee_payment_ids = fields.One2many(
        comodel_name='rent.guarantee.payment',
        inverse_name='rental_object_id',
        string="Guarantee payments",
    )

    insurance_contract_ids = fields.One2many(
        comodel_name='rent.insurance.contract',
        inverse_name='rental_object_id',
        string="Insurance Contracts",
    )

    res_country_id = fields.Many2one(
        comodel_name='res.country',
        string='Country',
        help="Country of location of the rental object."
    )

    @api.depends('contract_ids')
    def _compute_actual_contract_number_date(self):
        for record in self:
            last_contract = self.env['rent.contract'].get_last_rental_object_contract(record.id)
            if last_contract:
                record.actual_contract_number_date = (
                        _("#%(a)s from %(b)s")
                        % {'a': last_contract.number,
                           'b': format_date(env=self.env, value=last_contract.date)})
            else:
                record.actual_contract_number_date = None

    @api.model
    def _aggregate_actual_costs(self, rental_object_id, date_from, date_to):
        """Aggregates actual costs by (year, month) key."""
        actual_costs_map = {}

        # Use self.env, as this is an @api.model method
        actual_costs = self.env['rent.actual.cost'].search([
            ('rental_object_id', '=', rental_object_id),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ])

        for cost in actual_costs:
            month_key = (cost.date.year, cost.date.month)

            if month_key not in actual_costs_map:
                actual_costs_map[month_key] = {
                    'rental_cost': 0.0,
                    'exploitation_cost': 0.0,
                    'marketing_cost': 0.0,
                    'total_cost': 0.0,
                }

            actual_costs_map[month_key]['rental_cost'] += cost.rental_cost
            actual_costs_map[month_key]['exploitation_cost'] += cost.exploitation_cost
            actual_costs_map[month_key]['marketing_cost'] += cost.marketing_cost
            actual_costs_map[month_key]['total_cost'] += cost.total_cost

        return actual_costs_map

    @api.model
    def _aggregate_monthly_revenues(self, rental_object_id, date_from, date_to, model_name):
        """Aggregates actual or planned revenues by (year, month) key, grouped by cost center."""
        revenues_map = {}

        # Use self.env, as this is an @api.model method
        # Search revenues related to cost centers of the rental object
        revenues = self.env[model_name].search([
            ('cost_center_id.rental_object_id', '=', rental_object_id),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ])

        # Aggregate revenues by month and cost center
        for revenue_record in revenues:
            if not revenue_record.date:
                continue

            month_key = (revenue_record.date.year, revenue_record.date.month)

            # Map structure: { (year, month): { cost_center_id: revenue_sum } }
            if month_key not in revenues_map:
                revenues_map[month_key] = {}

            # Use False if cost_center_id is not set (e.g., revenue assigned directly to object)
            cost_center_id = revenue_record.cost_center_id.id or False

            if cost_center_id not in revenues_map[month_key]:
                revenues_map[month_key][cost_center_id] = 0.0

            revenues_map[month_key][cost_center_id] += revenue_record.revenue

        return revenues_map

    @api.model
    def _get_rent_calculation_for_range(self, date_from, date_to):
        """
        Calculates and prepares distributed rent data for each rental object
        to its cost centers for a given date range.

        Returns:
            list[dict]: A list of dictionaries where each dict contains the values
                        ready to be passed to rent.analysis.report.line.create().
        """
        report_data_for_creation = []
        rental_objects = self.env['rent.rental.object'].search([])
        company_currency = self.env.company.currency_id

        for obj in rental_objects:
            active_contracts = self.env['rent.contract']._get_active_contracts_for_object(
                obj, date_from, date_to
            )

            if not active_contracts:
                continue

            significant_dates = self.env['rent.contract']._get_significant_dates(
                date_from, date_to, active_contracts
            )

            # Aggregate actual costs using the helper function
            actual_costs_map = self._aggregate_actual_costs(obj.id, date_from, date_to)

            # Aggregate actual and planned revenues
            actual_revenues_map = self._aggregate_monthly_revenues(
                obj.id, date_from, date_to, 'rent.actual.monthly.revenue'
            )
            planned_revenues_map = self._aggregate_monthly_revenues(
                obj.id, date_from, date_to, 'rent.planned.monthly.revenue'
            )

            cost_centers = obj.cost_center_ids.filtered(lambda cc: cc.area_size > 0)
            total_area = sum(cost_centers.mapped('area_size'))

            for interval_start, interval_end in self.env['rent.contract']._generate_intervals(
                    significant_dates, date_from, date_to
            ):
                effective_contract = self.env['rent.contract']._get_effective_contract(
                    active_contracts, interval_start, interval_end
                )

                # Calculate the total rent for the entire rental object
                monthly_segments = self.env['rent.contract']._calculate_monthly_segments(
                    obj, effective_contract, interval_start, interval_end, company_currency
                )

                amount_fields = [
                    'rental_amount', 'exploitation_amount', 'marketing_amount', 'rent_total',
                    'plan_rental_amount', 'plan_exploitation_amount', 'plan_marketing_amount', 'plan_rent_total',
                    'actual_rental_cost', 'actual_exploitation_cost', 'actual_marketing_cost', 'actual_total_cost',
                    'actual_revenue', 'planned_revenue',
                ]

                for segment in monthly_segments:
                    segment_month = (date.fromisoformat(segment['date_from']).year,
                                     date.fromisoformat(segment['date_from']).month)

                    actual_cost_data = actual_costs_map.get(segment_month)

                    # Apply actual costs proportionally to days in the period (логіка ОК)
                    cost_types = ['rental', 'exploitation', 'marketing', 'total']
                    if actual_cost_data:
                        for cost_type in cost_types:
                            actual_key = f'actual_{cost_type}_cost'
                            cost_key = f'{cost_type}_cost'

                            segment[actual_key] = (actual_cost_data[cost_key]
                                                   * segment['days_in_period']
                                                   / segment['current_month_day_count'])
                    else:
                        for cost_type in cost_types:
                            segment[f'actual_{cost_type}_cost'] = 0.0

                    # Temporary set revenue fields to 0.0 in the segment for 'amount_fields' compliance
                    segment['actual_revenue'] = 0.0
                    segment['planned_revenue'] = 0.0

                    # Get monthly revenue data
                    month_actual_revenues = actual_revenues_map.get(segment_month, {})
                    month_planned_revenues = planned_revenues_map.get(segment_month, {})

                    # Base values common for all cost centers (or for the object itself)
                    base_values = {
                        'rental_object_id': obj.id,
                        'contract_id': segment.get('contract_id'),
                        'date_from': segment['date_from'],
                        'date_to': segment['date_to'],
                        'rental_currency_coef': segment['rental_currency_coef'],
                        'exploitation_currency_coef': segment['exploitation_currency_coef'],
                        'marketing_currency_coef': segment['marketing_currency_coef'],
                        'area_size': segment['area_size'],
                        'indexation_coefficient': segment['indexation_coefficient'],
                    }

                    if cost_centers and total_area > 0:
                        # Distribute to cost centers
                        for cost_center in cost_centers:
                            coefficient = cost_center.area_size / total_area
                            line_values = base_values.copy()

                            # Apply the coefficient to all fields in amount_fields (включаючи планові)
                            for field in amount_fields:
                                if field in ('actual_revenue', 'planned_revenue'):
                                    continue
                                line_values[field] = segment[field] * coefficient

                            # 3. Calculate and apply actual/planned revenues for the specific Cost Center
                            # Actual Revenue (proportional to days in the period)
                            actual_rev_for_cc = month_actual_revenues.get(cost_center.id, 0.0)
                            line_values['actual_revenue'] = (
                                    actual_rev_for_cc
                                    * segment['days_in_period']
                                    / segment['current_month_day_count']
                            ) if segment['current_month_day_count'] else 0.0

                            # Planned Revenue (proportional to days in the period)
                            planned_rev_for_cc = month_planned_revenues.get(cost_center.id, 0.0)
                            line_values['planned_revenue'] = (
                                    planned_rev_for_cc
                                    * segment['days_in_period']
                                    / segment['current_month_day_count']
                            ) if segment['current_month_day_count'] else 0.0

                            line_values['cost_center_id'] = cost_center.id

                            report_data_for_creation.append(line_values)
                    else:
                        # Fallback for objects without cost centers
                        line_values = base_values.copy()

                        # Transfer all amounts without change (включаючи планові)
                        for field in amount_fields:
                            line_values[field] = segment[field]

                        line_values['cost_center_id'] = False  # No cost center
                        report_data_for_creation.append(line_values)

        return report_data_for_creation