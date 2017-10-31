# coding: utf-8

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestBaremo(TransactionCase):

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

    def test_baremo_matrix(self):
        baremo_id = self.env.ref('commission_calculation.baremo_book_01')
        ipad = self.env.ref('product.product_product_4')
        matrix_obj = self.env['baremo.matrix']

        matrix_obj.create({
            'baremo_id': baremo_id.id,
            'user_id': False,
            'product_id': ipad.id,
        })

        error = 'There are already baremos with the following settings.*'
        with self.assertRaisesRegexp(ValidationError, error):
            matrix_obj.create({
                'baremo_id': baremo_id.id,
                'user_id': False,
                'product_id': ipad.id,
            })

        with self.assertRaisesRegexp(ValidationError, error):
            matrix_obj.create({
                'baremo_id': baremo_id.id,
                'user_id': self.ref('base.user_root'),
                'product_id': ipad.id,
            })

    def test_baremo_action_view_matrix(self):
        baremo_1 = self.env.ref('commission_calculation.baremo_book_01')
        result = baremo_1.action_view_matrix()

        self.assertEquals(result['domain'],
                          [('baremo_id', 'in', [baremo_1.id])])

        baremo_2 = self.env.ref('commission_calculation.baremo_book_02')
        result = baremo_2.action_view_matrix()

        self.assertEquals(result['domain'],
                          [('baremo_id', 'in', [baremo_2.id])])
