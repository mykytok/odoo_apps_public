from odoo import models, fields


class ResCurrency(models.Model):
    _inherit = "res.currency"

    rent_plan_currency_id = fields.Many2one(
        comodel_name='res.currency',  # Посилання на саму себе
        string='Планова Валюта',
    )