# coding: utf-8
############################################################################
#    Module Writen For Odoo, Open Source Management Solution
#
#    Copyright (c) 2010 Vauxoo - http://www.vauxoo.com
#    All Rights Reserved.
#    info Vauxoo (info@vauxoo.com)
#    coded by: Humberto Arocha <hbto@vauxoo.com>
#              Nhomar Hernandez <nhomar@vauxoo.com>
#              Yanina Aular <yanina.aular@vauxoo.com>
############################################################################

import time
from odoo import api, fields, models


class ProductProduct(models.Model):

    _inherit = 'product.product'

    list_price_historical_ids = fields.One2many(
        'product.historic.price',
        'product_id',
        'Historical Prices',
        help='Historical changes '
        'of the sale price of '
        'this product')

    matrix_ids = fields.One2many(
        'baremo.matrix', 'product_id',
        'Baremo Matrix', copy=False,
        help="Display all commissions of the product")

    @api.multi
    def _update_historic_price(self):
        for product in self:
            self.env['product.historic.price'].create({
                'product_id': product.id,
                'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
                'price': product.list_price,
                'product_uom': product.uom_id.id})

    @api.model
    def create(self, vals):
        """Update the historical list price"""
        product = super(ProductProduct, self.with_context(
            create_product_product=True)).create(vals)
        product._update_historic_price()
        return product

    @api.multi
    def write(self, values):
        """Update the historical list price"""
        res = super(ProductProduct, self).write(values)
        if 'list_price' in values:
            self._update_historic_price()
        return res
