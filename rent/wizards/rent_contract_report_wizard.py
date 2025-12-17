from odoo import models, fields, api
from odoo.tools import html2plaintext


class ContractReportWizard(models.TransientModel):
    _name = 'rent.contract.report.wizard'
    _description = 'Звіт по всіх договорах оренди'

    group_no = fields.Integer(string="№ групи", group_operator="max")
    partner_id = fields.Many2one('res.partner', string="Орендар")
    rental_object_group_id = fields.Many2one('rent.rental.object.group', string="Група об'єкта")
    rental_object_id = fields.Many2one('rent.rental.object', string="Об'єкт оренди")
    contract_type = fields.Selection([
        ('contract', 'Contract'),
        ('main_additional_agreement', 'Main additional agreement'),
        ('additional_agreement', 'Additional agreement')
    ], string="Тип договору")
    contract_number = fields.Char(string="Номер договору")
    contract_date = fields.Date(string="Дата договору")
    act_start_date = fields.Date(string="Дата початку")
    expiration_date = fields.Date(string="Дата закінчення")
    term_months = fields.Integer(string="Строк, міс")
    gp_amount = fields.Monetary(string="Сума ГП", currency_field='currency_id', group_operator="avg")
    currency_id = fields.Many2one('res.currency')
    gp_guarantee = fields.Char(string="Тип гарантії", group_operator="max")
    is_discounted = fields.Boolean(string="Дисконтування", group_operator="bool_and")
    notes = fields.Char(string="Примітки", group_operator="max")

    def action_generate_list(self):
        self.search([]).unlink()

        rental_objects = self.env['rent.rental.object'].search([], order='rental_object_group_id, name')
        wizard_records = []
        obj_counter = 1

        for obj in rental_objects:
            # Отримуємо дані об'єкта
            gp = obj.main_guarantee_payment_id
            guarantee_type_label = dict(gp._fields['guarantee_type'].selection).get(gp.guarantee_type, "") if gp else ""
            is_disc = gp.discounted if gp else False
            clean_notes = html2plaintext(obj.comment) if obj.comment else ""

            # --- РЯДОК 1: Тільки дані об'єкта (Заголовок) ---
            wizard_records.append({
                'group_no': obj_counter,
                'rental_object_group_id': obj.rental_object_group_id.id,
                'rental_object_id': obj.id,
                'gp_amount': obj.gp_amount,
                'currency_id': obj.gp_currency_id.id,
                'gp_guarantee': guarantee_type_label,
                'is_discounted': is_disc,
                'notes': clean_notes,
                # Поля договору залишаємо порожніми
                'partner_id': False,
                'contract_number': False,
            })

            # --- НАСТУПНІ РЯДКИ: Деталі договорів ---
            contracts = obj.contract_ids.sorted(key=lambda r: r.date or fields.Date.today())
            for contract in contracts:
                wizard_records.append({
                    'group_no': obj_counter,
                    'rental_object_group_id': obj.rental_object_group_id.id,
                    'rental_object_id': obj.id,
                    # Дані договору
                    'partner_id': contract.res_partner_id.id,
                    'contract_type': contract.contract_type,
                    'contract_number': contract.number,
                    'contract_date': contract.date,
                    'act_start_date': contract.act_start_date,
                    'expiration_date': contract.expiration_date,
                    'term_months': contract.rental_term_months,
                    # Очищуємо дані об'єкта, щоб вони не дублювалися в Excel/списку
                    'gp_amount': 0.0,
                    'gp_guarantee': "",
                    'is_discounted': False,
                    'notes': "",
                })

            obj_counter += 1

        self.create(wizard_records)

        return {
            'name': 'Зведена таблиця оренди',
            'type': 'ir.actions.act_window',
            'res_model': 'rent.contract.report.wizard',
            'view_mode': 'tree',
            'target': 'current',
            'context': {'search_default_group_by_object': 0}  # Вимикаємо групування за замовчуванням
        }
    # def action_generate_list(self):
    #     self.search([]).unlink()
    #
    #     # Отримуємо всі об'єкти оренди
    #     rental_objects = self.env['rent.rental.object'].search([], order='rental_object_group_id, name')
    #     wizard_records = []
    #
    #     obj_counter = 1
    #
    #     for obj in rental_objects:
    #         # Отримуємо ВСІ договори об'єкта та сортуємо їх по даті
    #         # Використовуємо sorted() для сортування recordset
    #         contracts = obj.contract_ids.sorted(key=lambda r: r.date or fields.Date.today())
    #
    #         gp = obj.main_guarantee_payment_id
    #         guarantee_type_label = dict(gp._fields['guarantee_type'].selection).get(gp.guarantee_type, "") if gp else ""
    #         is_disc = gp.discounted if gp else False
    #
    #         clean_notes = html2plaintext(obj.comment) if obj.comment else ""
    #
    #         # Якщо у об'єкта є договори - створюємо рядок для кожного
    #         if contracts:
    #             for contract in contracts:
    #                 wizard_records.append({
    #                     'group_no': obj_counter,
    #                     'partner_id': contract.res_partner_id.id,
    #                     'rental_object_group_id': obj.rental_object_group_id.id,
    #                     'rental_object_id': obj.id,
    #                     'contract_type': contract.contract_type,
    #                     'contract_number': contract.number,
    #                     'contract_date': contract.date,
    #                     'act_start_date': contract.act_start_date,
    #                     'expiration_date': contract.expiration_date,
    #                     'term_months': contract.rental_term_months,
    #                     'gp_amount': obj.gp_amount,
    #                     'currency_id': obj.gp_currency_id.id,
    #                     'gp_guarantee': guarantee_type_label,
    #                     'is_discounted': is_disc,
    #                     'notes': clean_notes,
    #                 })
    #         else:
    #             # Якщо договорів взагалі немає, але об'єкт треба показати у звіті (опціонально)
    #             wizard_records.append({
    #                 'group_no': obj_counter,
    #                 'rental_object_group_id': obj.rental_object_group_id.id,
    #                 'rental_object_id': obj.id,
    #                 'gp_amount': obj.gp_amount,
    #                 'currency_id': obj.gp_currency_id.id,
    #                 'gp_guarantee': guarantee_type_label,
    #                 'is_discounted': is_disc,
    #                 'notes': clean_notes,
    #             })
    #         obj_counter += 1
    #
    #     self.create(wizard_records)
    #
    #     return {
    #         'name': 'Зведена таблиця договорів',
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'rent.contract.report.wizard',
    #         'view_mode': 'tree',
    #         'target': 'current',
    #     }