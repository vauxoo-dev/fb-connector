# coding: utf-8

from odoo.tests.common import TransactionCase


class TestBaremo(TransactionCase):

    """Tests for Commissions (commission.payment)
    """

    def setUp(self):
        """basic method to define some basic data to be re use in all test cases.
        """
        super(TestBaremo, self).setUp()
        self.company_obj = self.env['res.company']

    def test_basic_baremo(self):
        baremo_id = self.env.ref('commission_calculation.baremo_book_01')
        company = self.env.ref('base.main_company')
        company.baremo_id = baremo_id
        self.assertEquals(baremo_id, company.baremo_id)
        self.assertEquals(baremo_id, company.partner_id.baremo_id)
        return True
