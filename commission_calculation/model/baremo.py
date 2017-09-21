# coding: utf-8
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    nhomar.hernandez@netquatro.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import fields, models, api
from odoo.addons import decimal_precision as dp
from openerp import SUPERUSER_ID


class BaremoMatrix(models.Model):

    """
    OpenERP Model : baremo matrix
    """

    _name = 'baremo.matrix'

    baremo_id = fields.Many2one(
        'baremo.book', 'Bareme', required=True)
    user_id = fields.Many2one(
        'res.users', 'Salesman', required=True)
    product_id = fields.Many2one(
        'product.product', 'Product', required=True)

    # _sql_constraints = [
    #     ('baremo_permutation_unique',
    #      'unique(user_id, product_id)',
    #      'Same Salesman & Product can be assigned to only one Baremo')]


class BaremoBook(models.Model):
    _name = 'baremo.book'

    name = fields.Char('Baremo Description',
                        size=64,
                        required=True,
                        readonly=False)
    bar_ids = fields.One2many(
        'baremo', 'baremo_id', 'Emission Days',
        required=False,
        copy=True,
    )
    matrix_ids = fields.One2many(
        'baremo.matrix', 'baremo_id',
        'Baremo Matrix',
        copy=False,
    )


class Baremo(models.Model):

    """OpenERP Model : baremo
    """

    _name = 'baremo'
    _order = "number asc"

    name = fields.Char(
        'Due Days Description', size=64, required=True, readonly=False,
        help="Due days Description")
    number = fields.Integer(
        'Due Days', help="Days since Emission/Due Date", required=True)
    disc_ids = fields.One2many(
        'baremo.discount', 'disc_id', 'Commission per Discount @ Due Days',
        required=False, help="Commission per Discount @ Due Days",
        copy=True,
    )
    baremo_id = fields.Many2one('baremo.book', 'Padre', required=False)
    # _defaults = {
    #     'name': lambda *a: None,
    # }


class BaremoDiscount(models.Model):

    """OpenERP Model : baremo_discount
    """

    _name = 'baremo.discount'
    _order = "porc_disc asc"
    _rec_name = 'porc_disc'
    porc_disc = fields.Float(
        '% Dcto', digits_compute=dp.get_precision('Commission'),
        help="% de Descuento por producto", required=True)
    porc_com = fields.Float(
        '% Com.', digits_compute=dp.get_precision('Commission'),
        help="% de Comision @ porcentaje Descuento", required=True)
    disc_id = fields.Many2one('baremo', 'Baremo', required=False)


class ResParter(models.Model):
    _inherit = "res.partner"
    baremo_id = fields.Many2one('baremo.book', 'Baremo', required=False)


class ResUsers(models.Model):
    _inherit = "res.users"
    matrix_ids = fields.One2many(
        'baremo.matrix', 'user_id',
        'Baremo Matrix',
        copy=False,
    )


class ProductProduct(models.Model):
    _inherit = "product.product"
    matrix_ids = fields.One2many(
        'baremo.matrix', 'product_id',
        'Baremo Matrix',
        copy=False,
    )


class ResCompany(models.Model):
    _inherit = "res.company"
    _description = 'Companies'

    #TODO
    @api.multi
    def _get_baremo_data(self):
        """ Read the 'baremo_id' functional field. """
        part_obj = self.env['res.partner']
        for company in self:
            # result[company.id] = {}.fromkeys(field_names, False)
            if company.partner_id:
                data = part_obj.read(cr, SUPERUSER_ID, [company.partner_id.id],
                                     field_names, context=context)[0]
                for field in field_names:
                    result[company.id][field] = data[field] or False
        return result

    def _set_baremo_data(self, cr, uid, company_id, name, value, arg,
                         context=None):
        """ Write the 'baremo_id' functional field. """
        part_obj = self.env['res.partner']
        company = self.browse(cr, uid, company_id, context=context)
        if company.partner_id:
            part_obj.write(
                cr, uid, company.partner_id.id, {name: value or False},
                context=context)
        return True

    baremo_id = fields.Many2one(
        'baremo.book',
        compute='_get_baremo_data',
        inverse='_set_baremo_data',
        string="Baremo",
        # multi='baremo',
    )
