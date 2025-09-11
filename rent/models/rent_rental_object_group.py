from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RentalObjectGroup(models.Model):
    """A model for storing Rental object group
                    """

    _name = 'rent.rental.object.group'
    _description = 'Rental object group'

    name = fields.Char(translate=True)
    active = fields.Boolean(default=True)
    parent_id = fields.Many2one(
        comodel_name='rent.rental.object.group',
        string='Parent rental object group',
        index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    child_id = fields.One2many(
        comodel_name='rent.rental.object.group',
        inverse_name='parent_id',
        string='Child rental object groups'
    )

    @api.constrains('parent_id')
    def _check_parent_id_not_self(self):
        for record in self:
            if record.parent_id and record.parent_id.id == record.id:
                raise ValidationError(_("You cannot set a rental object group as its own parent."))
