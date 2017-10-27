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

from odoo import api, fields, models
import time
import odoo.addons.decimal_precision as dp


class ProductProduct(models.Model):

    _inherit = 'product.product'

    @api.depends('list_price')
    def _compute_historical_price(self):
        for product in self.filtered(lambda a: a.list_price != a.list_price_historical):
            product.list_price_historical = product.list_price

    list_price_historical = fields.Float(
        compute='_compute_historical_price',
        string='Latest Price',
        digits=dp.get_precision('List_Price_Historical'),
        help="Latest Recorded Historical Value")
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
        for record in self:
            price_obj = self.env['product.historic.price']
            historic_price = price_obj.search(
                [('product_id', '=', record.id)],
                order='datetime desc',
                limit=1)
            if (historic_price and historic_price.price != record.list_price) \
                    or not historic_price:
                price_obj.create({
                    'product_id': record.id,
                    'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'price': record.list_price,
                    'product_uom': record.uom_id.id})
