from odoo import models, fields, api
from odoo.tools.misc import format_date


class GuaranteePayment(models.Model):
    """A model for storing Guarantee Payments
                    """

    _name = 'rent.guarantee.payment'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', ]
    _description = 'Guarantee payment'
    name = fields.Char(compute='_compute_name',
                       store = True
                       )
    active = fields.Boolean(default=True)
    comment = fields.Html(string='Notes')
    rental_object_id = fields.Many2one(
        comodel_name='rent.rental.object'
    )
    sum = fields.Monetary(
        currency_field='currency_id',
        required=True
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        required=True,
        default=lambda self: self.env.company.currency_id.id
    )
    guarantee_type = fields.Selection(
        [('guarantee_payment', 'Guarantee payment'),
         ('bank_guarantee', 'Bank guarantee')],
        string='Type of guarantee',
        required=True
    )
    number = fields.Char()
    date = fields.Date()
    expiration_date = fields.Date()
    vat = fields.Boolean(
        default=True,
        string='VAT'
    )
    discounted = fields.Boolean(
        default=True,
    )

    @api.depends('guarantee_type', 'sum', 'currency_id', 'number', 'date', 'rental_object_id')
    def _compute_name(self):
        """
        Computes the name of the guarantee payment record based on the formula:
        [guarantee_type] [sum] [currency_id] [number] [date] [(rental_object_id)]
        Skips any field that is empty.
        """
        for record in self:
            name_parts = []

            # 1. guarantee_type (Selection label)
            if record.guarantee_type:
                # Get the display label for the Selection field
                type_label = dict(record._fields['guarantee_type'].selection).get(record.guarantee_type)
                if type_label:
                    name_parts.append(type_label)

            # 2. sum and currency_id (Formatted currency)
            if record.sum and record.currency_id:
                # Use Odoo's currency formatter for correct symbol and position
                formatted_sum = record.currency_id.with_context(lang=self.env.user.lang or 'en_US').format(record.sum)
                name_parts.append(formatted_sum)

            # 3. number
            if record.number:
                name_parts.append(f"#{record.number}")

            # 4. date (Formatted)
            if record.date:
                # Use Odoo's format_date tool for locale-aware date formatting
                formatted_date = format_date(self.env, record.date)
                name_parts.append(formatted_date)

            # 5. rental_object_id (Enclosed in parentheses)
            if record.rental_object_id:
                name_parts.append(f"({record.rental_object_id.name})")

            # Join all non-empty parts with a single space
            record.name = " ".join(name_parts)

            # Fallback for when all fields are empty
            if not record.name:
                record.name = "/"