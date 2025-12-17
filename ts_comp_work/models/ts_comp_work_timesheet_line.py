from odoo import fields, models


class TsCompWorkTimesheetLine(models.Model):
    _name = 'ts_comp_work.timesheet.line'
    _description = 'Detailed Work Line for Invoice'

    move_id = fields.Many2one('account.move', string="Invoice", required=True, ondelete='cascade')

    # Custom fields with ts_comp_work prefix
    ts_comp_work_original_timesheet_id = fields.Many2one('account.analytic.line', string="Original Timesheet Record",
                                                         ondelete='set null')
    ts_comp_work_description = fields.Text(string="Work Description", required=True)
    ts_comp_work_quantity = fields.Float(string="Quantity (Hrs)", required=True)
    ts_comp_work_product_id = fields.Many2one('product.product', string="Service Product", required=True,
                                              domain=[('type', '=', 'service')])