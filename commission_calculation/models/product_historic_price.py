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

from odoo import fields, models
import odoo.addons.decimal_precision as dp


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
    price = fields.Float(digits=dp.get_precision('Price'))
    product_uom = fields.Many2one(
        'product.uom', string="Supplier UoM",
        help="""Choose here the Unit of Measure in which the prices and
                quantities are expressed below.""")
