from .common import TestRentCommon
from datetime import date, timedelta

class TestRentalObjectSimple(TestRentCommon):

    def test_01_compute_actual_contract_number_date_basic(self):
        """
        Verifies that the computed field displays the most recent contract.
        """
        # Create a rental object
        rental_object = self.RentalObject.create({'name': 'Office 101', 'area_size': 50.0})
        # Assert that the field is empty without any contracts
        self.assertIsNone(rental_object.actual_contract_number_date, "Field should be empty without contracts.")

        # Create the first (older) contract
        self.RentContract.create({
            'rental_object_id': rental_object.id, 'number': 'C001', 'date': date(2024, 1, 1),
            'expiration_date': date(2024, 6, 30), 'contract_type': 'contract', 'rental_rate': 100,
            'rental_rate_currency_id': self.usd_currency.id,
        })
        # Invalidate cache to force re-computation
        rental_object.invalidate_cache(['actual_contract_number_date'])
        # Assert that the field now shows the first contract
        self.assertEqual(rental_object.actual_contract_number_date, '#C001 from Jan 01, 2024',
                         "Field should display C001.")

        # Create a newer contract
        self.RentContract.create({
            'rental_object_id': rental_object.id, 'number': 'C002', 'date': date(2024, 7, 1),
            'expiration_date': date(2024, 12, 31), 'contract_type': 'contract', 'rental_rate': 120,
            'rental_rate_currency_id': self.usd_currency.id,
        })
        # Invalidate cache to force re-computation
        rental_object.invalidate_cache(['actual_contract_number_date'])
        # Assert that the field now shows the newer contract
        self.assertEqual(rental_object.actual_contract_number_date, '#C002 from Jul 01, 2024',
                         "Field should display C002.")