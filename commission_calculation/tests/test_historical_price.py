# coding: utf-8
import time
from odoo.tests.common import TransactionCase


class TestHistoricalPrice(TransactionCase):

    def setUp(self):
        super(TestHistoricalPrice, self).setUp()
        self.product = self.env['product.product']
        self.h_price = self.env['product.historic.price']
        self.h_cost = self.env['product.price.history']
        self.product_id = None

    def test_create_product(self):
        # Creating a product
        self.product_id = self.product.create({'name': 'Product Test',
                                               'list_price': 25,
                                               'standard_price': 15})
        # Checking if the historical was created correctly
        h_price = self.h_price.search([
            ('product_id', '=', self.product_id.id)])
        h_cost = self.h_cost.search([('product_id', '=', self.product_id.id)])
        self.assertTrue(h_price and h_cost,
                        "The historical were not properly created")
        price = h_price.price
        cost = h_cost.cost
        self.assertTrue(price == 25,
                        "The sale price was properly saved")
        self.assertTrue(cost == 15,
                        "The cost was properly saved")

    def test_write_product(self):
        # Updating the product
        self.test_create_product()
        # The historical depends of date of create, the sleep is needed to
        # avoid that the first historical had the same date than the second
        # historical in the self.product is
        time.sleep(2)
        self.product_id.write({'list_price': 40, 'standard_price': 18})
        # Checking if the historical was changed correctly
        h_price = self.h_price.search(
            [('product_id', '=', self.product_id.id)],
            order='datetime desc', limit=1)
        h_cost = self.h_cost.search([('product_id', '=', self.product_id.id)],
                                    order='datetime desc', limit=1)

        self.assertTrue(h_price and h_cost,
                        "The historical does not exist")
        price = h_price.price
        cost = h_cost.cost
        self.assertTrue(price == 40,
                        "The sale price was not properly changed")
        self.assertTrue(cost == 18,
                        "The cost was not properly changed")
