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

from odoo import fields, models, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import ValidationError


class BaremoMatrix(models.Model):

    _name = 'baremo.matrix'

    baremo_id = fields.Many2one(
        'baremo.book', 'Bareme', required=True)
    user_id = fields.Many2one(
        'res.users', 'Salesman')
    product_id = fields.Many2one(
        'product.product', 'Product', required=True)

    @api.constrains('user_id')
    def _check_salesman_empty(self):
        for line in self:
            if not line.user_id and self.search([('id','!=',self.id), ('user_id','=', False)]):
                raise ValidationError(_('A line of %s already exists for all salesman.') % line.product_id.name)

    _sql_constraints = [
        ('baremo_permutation_unique',
         'unique(user_id, product_id)',
         'Same Salesman & Product can be assigned to only one Baremo')]


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


class BaremoDiscount(models.Model):

    _name = 'baremo.discount'
    _order = "porc_disc asc"
    _rec_name = 'porc_disc'
    porc_disc = fields.Float(
        '% Dcto', digits=dp.get_precision('Commission'),
        help="% de Descuento por producto", required=True)
    porc_com = fields.Float(
        '% Com.', digits=dp.get_precision('Commission'),
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

    @api.depends('partner_id')
    def _compute_baremo_data(self):
        """ Read the 'baremo_id' functional field. """
        for company in self:
            if company.partner_id:
                company.baremo_id = company.partner_id.baremo_id

    @api.multi
    def _inverse_baremo_data(self):
        """ Write the 'baremo_id' functional field. """
        for company in self:
            if company.partner_id:
                company.partner_id.write({'baremo_id': company.baremo_id.id})

    baremo_id = fields.Many2one(
        'baremo.book',
        compute='_compute_baremo_data',
        inverse='_inverse_baremo_data',
        string="Baremo",
    )
