from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    rent_contract_ids = fields.One2many(
        comodel_name='rent.contract',
        inverse_name='res_partner_id',
        string='Rent Contracts',
    )