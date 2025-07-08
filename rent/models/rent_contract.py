from odoo import models, fields


class Contract(models.Model):
    """A model for storing Rental Contracts
                    """

    _name = 'rent.contract'
    _description = 'Contract'

    name = fields.Char(translate=True)
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
    )
    contract_type = fields.Selection(
        [('contract', 'Contract'),
         ('main_additional_agreement', 'Main additional agreement'),
         ('additional_agreement', 'Additional agreement')],
        string='Type of contract',
        required =True
    )
    rental_rate = fields.Float(
        string='Rental rate'
    )
    rental_rate_currency_id = fields.Many2one(
        comodel_name='res.currency',
    )
    rental_rate_tax_id = fields.Many2one(
        comodel_name='account.tax',
    )
    marketing_rate = fields.Float(
        string='Marketing rate'
    )
    marketing_rate_currency_id = fields.Many2one(
        comodel_name='res.currency',
    )
    marketing_rate_tax_id = fields.Many2one(
        comodel_name='account.tax',
    )
    exploitation_rate = fields.Float(
        string='Exploitation rate'
    )
    exploitation_rate_currency_id = fields.Many2one(
        comodel_name='res.currency',
    )
    exploitation_rate_tax_id = fields.Many2one(
        comodel_name='account.tax',
    )
