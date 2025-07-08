import logging

from odoo import models, fields, api, _
from odoo.tools.misc import format_date

_logger = logging.getLogger(__name__)

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

    @api.depends('contract_ids')
    def _compute_actual_contract_number_date(self):
        for record in self:
            last_contract = self.env['rent.contract'].get_last_rental_object_contract(record.id)
            # last_contract = self._search_last_contract(record.id)
            if last_contract:
                record.actual_contract_number_date = (_("#%s from %s") %
                                                      (last_contract.number,
                                                       format_date(
                                                           env=self.env,
                                                           value=last_contract.date)
                                                       )
                                                      )
            else:
                record.actual_contract_number_date = None

    @api.model
    def _search_last_contract(self, rental_object_id):
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