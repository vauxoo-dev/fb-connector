# coding: utf-8
###########################################################################
#    Module Writen to OpenERP, Open Source Management Solution
#    Copyright (C) OpenERP Venezuela (<http://openerp.com.ve>).
#    All Rights Reserved
# Credits######################################################
#    Coded by: Vauxoo C.A.
#    Planified by: Nhomar Hernandez
#    Audited by: Vauxoo C.A.
#############################################################################
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##########################################################################
from odoo import api, fields, models

import odoo.addons.decimal_precision as dp
import time


class ProductHistorical(models.Model):

    """product_historical
    """
    _inherit = 'product.template'

    @api.depends('list_price')
    def _compute_historical_price(self):
        product_historic = self.env['product.historic.price']
        for product_template in self:
            if product_template.list_price != \
                    product_template.list_price_historical:
                product_template.list_price_historical = \
                    product_template.list_price
                values = {
                    'product_id': product_template.id,
                    'name': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'price': product_template.list_price,
                }
                product_historic.create(values)

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
        product_hist = self.env['product.historic.price']
        for product in self.filtered(lambda a: a.standard_price != a.cost_historical):
            product.cost_historical = product.standard_price
            product_hist.create({
                'product_id': product.id,
                'name': time.strftime('%Y-%m-%d %H:%M:%S'),
                'price': product.standard_price,
            })

    cost_historical = fields.Float(
        compute=_get_historical_cost,
        string=' Latest Cost',
        digits_compute=dp.get_precision('Cost_Historical'),
        help="Latest Recorded Historical Cost")


class ProductHistoricPrice(models.Model):
    _order = "name desc"
    _name = "product.historic.price"
    _description = "Historical Price List"

    product_id = fields.Many2one(
        'product.template',
        string='Product related to this Price',
        required=True)
    name = fields.Datetime(string='Date', required=True,
                           default=fields.Datetime.now)
    price = fields.Float(
        string='Price', digits=dp.get_precision('Price'))
    product_uom = fields.Many2one(
        'product.uom', string="Supplier UoM",
        help="""Choose here the Unit of Measure in which the prices and
                quantities are expressed below.""")
