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

    @api.multi
    def _get_historical_price(self):
        product_hist = self.env['product.historic.price']
        for brw in self:
            if brw.list_price != brw.list_price_historical:
                brw.list_price_historical = brw.list_price
                values = {
                    'product_id': brw.id,
                    'name': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'price': brw.list_price,
                }
                product_hist.create(values)

    list_price_historical = fields.Float(
        compute='_get_historical_price',
        # method=True,
        string='Latest Price',
        digits=dp.get_precision('List_Price_Historical'),
        # store={
        #     _inherit: (
        #         lambda self, cr, uid, ids, c={}: ids,
        #         ['list_price'], 50),
        # },
        help="Latest Recorded Historical Value")
    list_price_historical_ids = fields.One2many(
        'product.historic.price',
        'product_id',
        'Historical Prices',
        help='Historical changes '
        'of the sale price of '
        'this product')
    # /!\ HBTO: Is this code still relevant?
    # cost_historical_ids = fields.One2many(
    #     'product.price.history',
    #     'product_template_id',
    #     'Historical Cost',
    #     help='Historical changes '
    #     'in the cost of this product')


class ProductHistoricPrice(models.Model):
    _order = "name desc"
    _name = "product.historic.price"
    _description = "Historical Price List"

    product_id = fields.Many2one(
        'product.template',
        string='Product related to this Price',
        required=True)
    name = fields.Datetime(string='Date', required=True)
    price = fields.Float(
        string='Price', digits=dp.get_precision('Price'))
    product_uom = fields.Many2one(
        'product.uom', string="Supplier UoM",
        help="""Choose here the Unit of Measure in which the prices and
                quantities are expressed below.""")

    # _defaults = {
    #     'name': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    # }
