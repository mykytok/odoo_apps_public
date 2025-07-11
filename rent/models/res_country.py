from odoo import models, fields, api


class ResCountry(models.Model):
    _inherit = "res.country"

    rent_rental_object_ids = fields.One2many(
        comodel_name='rent.rental.object',
        inverse_name='res_country_id',
        string='Rental Objects',
    )