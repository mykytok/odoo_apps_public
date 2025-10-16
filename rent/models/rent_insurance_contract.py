from odoo import models, fields, api
from odoo.tools.misc import format_date


class InsuranceContract(models.Model):
    """A model for storing Insurance Contracts related to a rental object."""

    _name = 'rent.insurance.contract'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', ]
    _description = 'Insurance Contract'

    # Fields required by the user
    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
        help="The computed display name of the insurance contract."
    )
    number = fields.Char(string='Contract Number', required=True)
    date = fields.Date(string='Signing Date', required=True)
    start_date = fields.Date(string='Effective From', required=True)
    end_date = fields.Date(string='Expiration Date', required=True)

    # Relationship field to link to the Rental Object
    rental_object_id = fields.Many2one(
        comodel_name='rent.rental.object',
        string='Rental Object',
        ondelete='cascade',
        required=True  # Забезпечуємо, що договір завжди прив'язаний до об'єкта
    )

    comment = fields.Html(string='Notes')

    @api.depends('number', 'date', 'start_date', 'end_date', 'rental_object_id')
    def _compute_name(self):
        """
        Computes the name based on: [Contract Number] [Signing Date] ([Rental Object])
        """
        for record in self:
            name_parts = []

            # 1. number (with prefix #)
            if record.number:
                name_parts.append(f"#{record.number}")

            # 2. date (Formatted)
            if record.date:
                formatted_date = format_date(record.env, record.date)
                name_parts.append(formatted_date)

            # 3. rental_object_id (Enclosed in parentheses)
            if record.rental_object_id:
                name_parts.append(f"({record.rental_object_id.name})")

            # Join all non-empty parts with a single space
            record.name = " ".join(name_parts)

            if not record.name:
                record.name = "/"