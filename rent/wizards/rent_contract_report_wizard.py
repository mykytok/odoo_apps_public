from odoo import models, fields, api


class ContractReportWizard(models.TransientModel):
    _name = 'rent.contract.report.wizard'
    _description = 'Звіт по об\'єктах оренди'

    # Поля для відображення в списку (List View)
    group_no = fields.Char(string="№ групи")
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
    gp_amount = fields.Monetary(string="Сума ГП", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency')
    gp_guarantee = fields.Char(string="Гарантія")
    is_discounted = fields.Boolean(string="Дисконтування")
    notes = fields.Html(string="Примітки")

    def action_generate_list(self):
        # 1. Очищуємо старі записи поточного користувача
        self.search([]).unlink()

        # 2. Збираємо дані
        rental_objects = self.env['rent.rental.object'].search([])
        wizard_records = []


        for obj in rental_objects:
            contract = obj.contract_ids[:1]  # Беремо актуальний контракт

            gp = obj.main_guarantee_payment_id
            guarantee_type_label = ""
            discounted_value = False
            if gp:
                guarantee_type_label = dict(gp._fields['guarantee_type'].selection).get(gp.guarantee_type, "")
                discounted_value = gp.discounted

            wizard_records.append({
                'group_no': obj.rental_object_group_id.id,
                'partner_id': contract.res_partner_id.id if contract else False,
                'rental_object_group_id': obj.rental_object_group_id.id,
                'rental_object_id': obj.id,
                'contract_type': contract.contract_type if contract else False,
                'contract_number': contract.number if contract else '',
                'contract_date': contract.date if contract else False,
                'act_start_date': contract.act_start_date if contract else False,
                'expiration_date': contract.expiration_date if contract else False,
                'term_months': contract.rental_term_months if contract else 0,
                'gp_amount': obj.gp_amount,
                'currency_id': obj.gp_currency_id.id,
                'gp_guarantee': guarantee_type_label,
                'is_discounted': discounted_value,
                'notes': obj.comment,
            })

        # 3. Створюємо записи в TransientModel
        self.create(wizard_records)

        # 4. Повертаємо Action, який відкриває List View цієї ж моделі
        return {
            'name': 'Зведена таблиця оренди',
            'type': 'ir.actions.act_window',
            'res_model': 'rent.contract.report.wizard',
            'view_mode': 'tree',
            'target': 'current',  # Відкрити в основному вікні
            'domain': [],  # Показуємо всі створені записи
        }