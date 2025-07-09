from odoo import models, fields, api, _
from odoo.tools.misc import format_date


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
        string = 'Rental object'
    )
    number = fields.Char(
        translate=True,
        string='Number')
    date = fields.Date(
        string='Date'
    )
    expiration_date = fields.Date(
        string='Expiration date'
    ) # last day of contract
    contract_type = fields.Selection(
        [('contract', 'Contract'),
         ('main_additional_agreement', 'Main additional agreement'),
         ('additional_agreement', 'Additional agreement')],
        string='Type of contract',
        required =True
    )

    # Rental Rate
    rental_rate = fields.Monetary(string='Rental Rate (Monthly)',
                                  currency_field='rental_rate_currency_id',
                                  required=True)
    rental_rate_currency_id = fields.Many2one(comodel_name='res.currency',
                                              string='Rental Rate Currency',
                                              default=lambda self: self.env.company.currency_id.id)
    rental_rate_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string='Rental Rate Tax')

    # Exploitation Rate
    exploitation_rate = fields.Monetary(string='Exploitation Rate (Monthly)',
                                        currency_field='exploitation_rate_currency_id',
                                        required=True)
    exploitation_rate_currency_id = fields.Many2one(comodel_name='res.currency',
                                                    string='Exploitation Rate Currency',
                                                    default=lambda self: self.env.company.currency_id.id)
    exploitation_rate_tax_id = fields.Many2one(comodel_name='account.tax',
                                               string='Exploitation Rate Tax')

    # Marketing Rate
    marketing_rate = fields.Monetary(string='Marketing Rate (Monthly)',
                                     currency_field='marketing_rate_currency_id',
                                     required=True)
    marketing_rate_currency_id = fields.Many2one(comodel_name='res.currency',
                                                 string='Marketing Rate Currency',
                                                 default=lambda self: self.env.company.currency_id.id)
    marketing_rate_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string='Marketing Rate Tax')

    @api.depends('rental_object_id')
    @api.depends('number')
    @api.depends('date')
    @api.onchange('rental_object_id')
    @api.onchange('number')
    @api.onchange('date')
    def _compute_name(self):
        for record in self:
            record.name = (_("#%s from %s (%s)") %
                           (record.number,
                            format_date(env=self.env, value=record.date),
                            record.rental_object_id.name)
                           )

    @api.model
    def get_last_rental_object_contract(self, rental_object_id):
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
