from odoo import models, fields


class RentalObject(models.Model):
    """A model for storing Rental Object
                    """

    _name = 'rent.rental.object'
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
