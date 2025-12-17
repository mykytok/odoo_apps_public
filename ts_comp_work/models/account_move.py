from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import date


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Fields for defining the billing period (using ts_comp_work prefix)
    ts_comp_work_date_from = fields.Date(string="Work From", copy=False, help="Start date for timesheet search.")
    ts_comp_work_date_to = fields.Date(string="Work To", copy=False, help="End date for timesheet search.")

    # One2many relation to the new detailed timesheet line model (using ts_comp_work prefix)
    ts_comp_work_timesheet_line_ids = fields.One2many(
        'ts_comp_work.timesheet.line',
        'move_id',
        string="Work Detail",
        copy=False
    )

    ts_comp_work_reload_trigger = fields.Boolean(
        string="Reload Trigger",
        default=False,
        copy=False,
        store=False,  # Не зберігаємо його в базі даних
    )

    # Method triggered by the "Fill Work From Timesheets" button
    def action_fill_timesheet_lines(self):
        self.ensure_one()

        if self.move_type != 'out_invoice':
            raise UserError(_("This action is only available for Sales Invoices."))

        if not self.partner_id:
            raise UserError(_("Please specify a customer first."))

        if not self.ts_comp_work_date_from or not self.ts_comp_work_date_to:
            raise UserError(_("Please specify the billing period (Work From / Work To)."))

        # 1. Clear previous detail records
        self.ts_comp_work_timesheet_line_ids.unlink()

        # 2. Search for timesheet records (account.analytic.line)
        domain = [
            ('partner_id', '=', self.partner_id.id),
            ('date', '>=', self.ts_comp_work_date_from),
            ('date', '<=', self.ts_comp_work_date_to),
            # Timesheets with and without project are included
            # TODO: Add filter to exclude timesheets already invoiced
        ]

        timesheet_records = self.env['account.analytic.line'].search(domain)

        if not timesheet_records:
            raise UserError(_("No timesheet records found for this customer and period."))

        # 3. Determine the Ultimate Fallback Product

        # P3: Check Company's Global Default Service
        company_default_product = self.company_id.ts_comp_work_default_service_id

        # P4: Check standard XML ID
        default_product_xml_record = self.env.ref('product.product_product_service_timesheet', raise_if_not_found=False)

        # Establish the ultimate product to use if P1 is not met
        ultimate_default_product = False

        if company_default_product:
            ultimate_default_product = company_default_product
        elif default_product_xml_record:
            ultimate_default_product = default_product_xml_record
        else:
            # P5: Last resort - find any service product (to prevent crashing, but will likely be "Restaurant Expenses" if not configured)
            ultimate_default_product = self.env['product.product'].search([('type', '=', 'service')], limit=1)

        if not ultimate_default_product:
            # This should ideally never happen if at least one service product exists
            raise UserError(_("A default service product must be configured in Company Settings or in system data."))

        # 4. Create new detail lines
        new_lines = []
        for ts in timesheet_records:
            description = f"[{ts.date}] - {ts.name or ''}"

            # Assume the best default product initially (P3 or P4 or P5)
            product_id = ultimate_default_product.id

            # P1: Check if the timesheet has a Project AND that Project is linked to a Sale Line
            if ts.project_id and ts.project_id.sale_line_id:
                sale_line = ts.project_id.sale_line_id
                if sale_line.product_id:
                    product_id = sale_line.product_id.id

            # product_id is now either P1 or the best available default

            new_lines.append((0, 0, {
                'ts_comp_work_description': description,
                'ts_comp_work_quantity': ts.unit_amount,
                'ts_comp_work_original_timesheet_id': ts.id,
                'ts_comp_work_product_id': product_id,
            }))

        # Write new lines to the One2many field
        self.ts_comp_work_timesheet_line_ids = new_lines

        self.ts_comp_work_reload_trigger = not self.ts_comp_work_reload_trigger

        return {'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("%s timesheet records successfully added to the detail table.") % len(
                        timesheet_records),
                    'type': 'success',
                    'sticky': False,
                }
                }

    # Method to create standard invoice lines based on detail table
    def action_create_invoice_lines(self):
        self.ensure_one()

        if not self.ts_comp_work_timesheet_line_ids:
            raise UserError(_("The Work Detail table is empty. Please fill it first."))

        # 1. Prepare data for standard invoice lines
        invoice_lines = []
        # WARNING: [(5, 0, 0)] removes ALL existing lines. Use with caution!

        for line in self.ts_comp_work_timesheet_line_ids:
            invoice_lines.append((0, 0, {
                'product_id': line.ts_comp_work_product_id.id,
                'name': line.ts_comp_work_description,
                'quantity': line.ts_comp_work_quantity,
                # Odoo will automatically populate price_unit, account_id, and tax_ids
            }))

        # 2. Delete all existing lines and add the new ones
        self.invoice_line_ids = [(5, 0, 0)] + invoice_lines

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _("Invoice lines successfully created from the work detail."),
                'type': 'success',
                'sticky': False,
            }
        }