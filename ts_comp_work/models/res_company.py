from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    # Custom field to define a default service product for the entire company
    ts_comp_work_default_service_id = fields.Many2one(
        'product.product',
        string="Default Billing Service (Timesheets)",
        domain=[('type', '=', 'service')],
        help="Global service product to use for timesheets when no project/sale link and no customer default are set."
    )