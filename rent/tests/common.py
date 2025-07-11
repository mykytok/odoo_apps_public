from odoo.tests.common import TransactionCase
from datetime import date

class TestRentCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(
            cls.env.context,
            tracking_disable=True,
            lang='en_US'))
        cls.RentalObject = cls.env['rent.rental.object']
        cls.RentContract = cls.env['rent.contract']
        cls.ResCurrency = cls.env['res.currency']

        cls.usd_currency = cls.ResCurrency.search([('name', '=', 'USD')], limit=1)
        if not cls.usd_currency:
            cls.usd_currency = cls.ResCurrency.create({
                'name': 'USD',
                'symbol': '$',
                'rate_ids': [(0, 0, {'rate': 1.0, 'name': date.today()})],
            })