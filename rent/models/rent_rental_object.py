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
    def _get_rent_calculation_for_range(self, date_from, date_to):
        """
        Calculates and distributes rent data for each rental object
        to its cost centers for a given date range.
        """
        distributed_report_data = []
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
                
                # Distribute the calculated rent to cost centers
                cost_centers = obj.cost_center_ids.filtered(lambda cc: cc.area_size > 0)
                total_area = sum(cost_centers.mapped('area_size'))
                
                for segment in monthly_segments:
                    if cost_centers and total_area > 0:
                        for cost_center in cost_centers:
                            # Create a new data dictionary for each cost center
                            segment_with_cc = segment.copy()
                            coefficient = cost_center.area_size / total_area
                            
                            # Apply the coefficient to the amounts
                            segment_with_cc['rental_amount'] *= coefficient
                            segment_with_cc['exploitation_amount'] *= coefficient
                            segment_with_cc['marketing_amount'] *= coefficient
                            segment_with_cc['rent_total'] *= coefficient
                            
                            # Link to the cost center
                            segment_with_cc['cost_center_id'] = cost_center.id
                            
                            distributed_report_data.append(segment_with_cc)
                    else:
                        # Fallback for objects without cost centers: add a single line for the object
                        segment['cost_center_id'] = False # No cost center
                        distributed_report_data.append(segment)

        return distributed_report_data
    # @api.model
    # def _get_rent_calculation_for_range(self, date_from, date_to):
    #     """
    #     Calculates the rent for each rental object for a given date range.
    #     Most of the calculation logic is delegated to the 'rent.contract' model.
    #     """
    #     rent_calculations_by_month = []
    #     rental_objects = self.env['rent.rental.object'].search([])
    #     company_currency = self.env.company.currency_id

    #     for obj in rental_objects:
    #         active_contracts = self.env['rent.contract']._get_active_contracts_for_object(
    #             obj, date_from, date_to
    #         )

    #         if len(active_contracts) == 0: continue

    #         significant_dates = self.env['rent.contract']._get_significant_dates(
    #             date_from, date_to, active_contracts
    #         )

    #         for interval_start, interval_end in self.env['rent.contract']._generate_intervals(
    #                 significant_dates, date_from, date_to
    #         ):
    #             effective_contract = self.env['rent.contract']._get_effective_contract(
    #                 active_contracts, interval_start, interval_end
    #             )

    #             monthly_segments = self.env['rent.contract']._calculate_monthly_segments(
    #                 obj, effective_contract, interval_start, interval_end, company_currency
    #             )
    #             rent_calculations_by_month.extend(monthly_segments)

    #     return rent_calculations_by_month
