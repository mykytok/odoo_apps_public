from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # The field must be explicitly defined here and related to the company_id field
    # The 'readonly=False' ensures it can be written back to the company record
    ts_comp_work_default_service_id = fields.Many2one(
        'product.product',
        related='company_id.ts_comp_work_default_service_id',
        string="Default Billing Service (Timesheets)",
        readonly=False
    )