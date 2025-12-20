from odoo import models, fields, api
from odoo.tools import html2plaintext


class ContractReportWizard(models.TransientModel):
    _name = 'rent.contract.report.wizard'
    _description = 'Звіт по всіх договорах оренди'

    group_no = fields.Integer(string="№ групи", group_operator="max")
    partner_id = fields.Many2one('res.partner', string="Орендодавець")
    rental_object_group_id = fields.Many2one('rent.rental.object.group', string="Група об'єкта")
    rental_object_id = fields.Many2one('rent.rental.object', string="Об'єкт оренди")
    contract_type = fields.Selection([
        ('contract', 'Договір'),
        ('main_additional_agreement', 'Головна додаткова угода'),
        ('additional_agreement', 'Додаткова угода')
    ], string="Тип договору")
    contract_number = fields.Char(string="Номер договору")
    contract_date = fields.Date(string="Дата договору")
    act_start_date = fields.Date(string="Дата початку")
    expiration_date = fields.Date(string="Дата закінчення")
    term_months = fields.Integer(string="Строк, міс")
    gp_amount = fields.Monetary(string="Сума ГП", currency_field='currency_id', group_operator="avg")
    currency_id = fields.Many2one('res.currency')
    gp_guarantee = fields.Char(string="Тип гарантії", group_operator="max")
    is_discounted = fields.Char(string="Дисконтування", group_operator="max")
    notes = fields.Char(string="Примітки", group_operator="max")

    def action_generate_list(self):
        self.search([]).unlink()

        rental_objects = self.env['rent.rental.object'].search([], order='rental_object_group_id, name')
        wizard_records = []

        last_group_id = False
        group_counter = 0

        for obj in rental_objects:
            current_group = obj.rental_object_group_id

            # Логіка визначення номеру групи
            if current_group.id != last_group_id:
                group_counter += 1
                last_group_id = current_group.id
                is_first_obj_in_group = True
            else:
                is_first_obj_in_group = False

            # Підготовка даних об'єкта (те, що раніше було в окремому рядку Рівня 2)
            gp = obj.main_guarantee_payment_id
            guarantee_type_label = dict(gp._fields['guarantee_type'].selection).get(gp.guarantee_type, "") if gp else ""
            is_disc = "Так" if (gp and gp.discounted) else ""
            clean_notes = html2plaintext(obj.comment) if obj.comment else ""

            contracts = obj.contract_ids.sorted(key=lambda r: r.date or fields.Date.today())

            if contracts:
                for index, contract in enumerate(contracts):
                    vals = {
                        'group_no': group_counter,
                        # Дані ГРУПИ: тільки для першого об'єкта в групі і тільки в його першому договорі
                        'rental_object_group_id': current_group.id if (is_first_obj_in_group and index == 0) else False,
                        'partner_id': (current_group.res_partner_id.id if current_group.res_partner_id else False)
                        if (is_first_obj_in_group and index == 0) else False,

                        # Дані ОБ'ЄКТА: тільки в першому договорі цього об'єкта
                        'rental_object_id': obj.id if index == 0 else False,
                        'gp_amount': obj.gp_amount if index == 0 else 0.0,
                        'currency_id': obj.gp_currency_id.id if index == 0 else False,
                        'gp_guarantee': guarantee_type_label if index == 0 else "",
                        'is_discounted': is_disc if index == 0 else "",
                        'notes': clean_notes if index == 0 else "",

                        # Дані ДОГОВОРУ (завжди)
                        'contract_type': contract.contract_type,
                        'contract_number': contract.number,
                        'contract_date': contract.date,
                        'act_start_date': contract.act_start_date,
                        'expiration_date': contract.expiration_date,
                        'term_months': contract.rental_term_months,
                    }
                    wizard_records.append(vals)
            else:
                # Якщо у об'єкта немає договорів, створюємо один рядок з даними об'єкта
                wizard_records.append({
                    'group_no': group_counter,
                    'rental_object_group_id': current_group.id if is_first_obj_in_group else False,
                    'partner_id': (current_group.res_partner_id.id if current_group.res_partner_id else False)
                    if is_first_obj_in_group else False,
                    'rental_object_id': obj.id,
                    'gp_amount': obj.gp_amount,
                    'currency_id': obj.gp_currency_id.id,
                    'gp_guarantee': guarantee_type_label,
                    'is_discounted': is_disc,
                    'notes': clean_notes,
                    'contract_type': False,
                })

        self.create(wizard_records)

        return {
            'name': 'Зведений реєстр договорів',
            'type': 'ir.actions.act_window',
            'res_model': 'rent.contract.report.wizard',
            'view_mode': 'tree',
            'target': 'current',
        }