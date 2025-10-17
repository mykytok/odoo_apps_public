from odoo import models, fields, api


class RentAnalysisReportLine(models.TransientModel):
    _name = 'rent.analysis.report.line'
    _description = 'Rent Analysis Report Line (Transient)'

    rental_object_id = fields.Many2one(
        comodel_name='rent.rental.object',
        string='Rental Object',
        readonly=True)
    
    cost_center_id = fields.Many2one(
        comodel_name='rent.cost.center',
        string='Cost Center',
        readonly=True)

    company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency', 
        readonly=True,
        default=lambda self: self.env.company.currency_id.id,
    )

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

    date_from = fields.Date(string='Date from')
    date_to = fields.Date(string='Date to')

    contract_id = fields.Many2one(comodel_name='rent.contract')

    area_size = fields.Float(
        help="Area of the rental property in square meters."
    )

    indexation_coefficient = fields.Float(
        help="Annual indexation (increase) of rent."
    )

    rental_currency_coef = fields.Float(
        string='Rental currency coefficient',
        help="Currency change coefficient from the start of the contract to the current month."
    )
    exploitation_currency_coef = fields.Float(
        string='Exploitation currency coefficient',
        help="Currency change coefficient from the start of the contract to the current month."
    )
    marketing_currency_coef = fields.Float(
        string='Marketing currency coefficient',
        help="Currency change coefficient from the start of the contract to the current month."
    )

    actual_rental_cost = fields.Monetary(
        string='Actual Rental Cost',
        currency_field='company_currency_id',
        readonly=True
    )
    actual_exploitation_cost = fields.Monetary(
        string='Actual Exploitation Cost',
        currency_field='company_currency_id',
        readonly=True
    )
    actual_marketing_cost = fields.Monetary(
        string='Actual Marketing Cost',
        currency_field='company_currency_id',
        readonly=True
    )
    actual_total_cost = fields.Monetary(
        string='Actual Total Cost',
        currency_field='company_currency_id',
        readonly=True
    )

    delta_rental = fields.Monetary(
        string='Delta Rental',
        currency_field='company_currency_id',
        compute='_compute_delta_costs',
        store=True,  # Store the value for better pivot/graph performance
    )
    delta_exploitation = fields.Monetary(
        string='Delta Exploitation',
        currency_field='company_currency_id',
        compute='_compute_delta_costs',
        store=True,
    )
    delta_marketing = fields.Monetary(
        string='Delta Marketing',
        currency_field='company_currency_id',
        compute='_compute_delta_costs',
        store=True,
    )
    delta_total = fields.Monetary(
        string='Delta Total',
        currency_field='company_currency_id',
        compute='_compute_delta_costs',
        store=True,
    )

    # Plan Amount Fields
    plan_rental_amount = fields.Monetary(
        string='Plan Rental Amount',
        currency_field='company_currency_id',
        readonly=True)
    plan_exploitation_amount = fields.Monetary(
        string='Plan Exploitation Amount',
        currency_field='company_currency_id',
        readonly=True)
    plan_marketing_amount = fields.Monetary(
        string='Plan Marketing Amount',
        currency_field='company_currency_id',
        readonly=True)
    plan_rent_total = fields.Monetary(
        string='Plan Total Rent',
        currency_field='company_currency_id',
        readonly=True)


    @api.depends('rental_amount', 'actual_rental_cost',
                 'exploitation_amount', 'actual_exploitation_cost',
                 'marketing_amount', 'actual_marketing_cost',
                 'rent_total', 'actual_total_cost')
    def _compute_delta_costs(self):
        """Computes the delta between the planned amount and the actual cost."""
        # Field pairs: (planned_amount, actual_cost, delta)
        fields_map = [
            ('rental_amount', 'actual_rental_cost', 'delta_rental'),
            ('exploitation_amount', 'actual_exploitation_cost', 'delta_exploitation'),
            ('marketing_amount', 'actual_marketing_cost', 'delta_marketing'),
            ('rent_total', 'actual_total_cost', 'delta_total'),
        ]

        for rec in self:
            for amount_field, cost_field, delta_field in fields_map:
                # Delta = Planned Amount - Actual Cost
                rec[delta_field] = rec[amount_field] - rec[cost_field]