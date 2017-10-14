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
    cost_historical_ids = fields.One2many(
        'product.price.history',
        'product_id',
        'Historical Cost',
        help='Historical changes '
        'in the cost of this product')

    @api.depends('standard_price')
    def _get_historical_cost(self):
        for product in self.filtered(lambda a: a.standard_price != a.cost_historical):
            product.cost_historical = product.standard_price

    cost_historical = fields.Float(
        compute=_get_historical_cost,
        string=' Latest Cost',
        digits_compute=dp.get_precision('Cost_Historical'),
        help="Latest Recorded Historical Cost")


class ProductHistoricPrice(models.Model):
    _name = "product.historic.price"
    _rec_name = 'datetime'
    _order = "datetime desc"
    _description = "Historical Price List"

    product_id = fields.Many2one(
        'product.product',
        string='Product related to this Price',
        required=True)
    datetime = fields.Datetime(string='Date', required=True,
                               default=fields.Datetime.now)
    price = fields.Float(
        string='Price', digits=dp.get_precision('Price'))
    product_uom = fields.Many2one(
        'product.uom', string="Supplier UoM",
        help="""Choose here the Unit of Measure in which the prices and
                quantities are expressed below.""")
