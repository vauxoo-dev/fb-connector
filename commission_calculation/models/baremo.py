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
from odoo.tools.safe_eval import safe_eval


class BaremoBook(models.Model):

    _name = 'baremo.book'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Baremo Description', required=True)
    bar_ids = fields.One2many(
        'baremo.line', 'baremo_id', 'Emission Days')
    matrix_ids = fields.One2many(
        'baremo.matrix', 'baremo_id',
        'Baremo Matrix', copy=False)

    @api.multi
    def action_view_matrix(self):
        self.ensure_one()
        result = self.env.ref(
            'commission_calculation.baremo_matrix_action2').read()[0]
        result['domain'] = [('baremo_id', 'in', [self.id])]
        ctx = safe_eval(result['context'])
        ctx.update({'default_baremo_id': self.id})
        result['context'] = ctx
        return result


class BaremoLine(models.Model):

    _name = 'baremo.line'
    _order = "number asc"

    name = fields.Char(
        'Description', required=True, help="Due days Description")
    number = fields.Integer(
        'Due Days', required=True, help="Days since Emission/Due Date")
    disc_ids = fields.One2many(
        'baremo.discount', 'disc_id', 'Commission per Discount @ Due Days')
    baremo_id = fields.Many2one('baremo.book')


class BaremoMatrix(models.Model):

    _name = 'baremo.matrix'

    baremo_id = fields.Many2one(
        'baremo.book', required=True)
    user_id = fields.Many2one('res.users', 'Salesman')
    product_id = fields.Many2one(
        'product.product', required=True, ondelete='cascade')

    @api.constrains('user_id', 'baremo_id', 'product_id')
    def _check_salesman_empty(self):
        """ A line with empty user is a general rule which indicates that the
        rule of that product applies to all salesman. This method avoids to
        create two o more general rules apply to a same product in all baremo
        matrixes.
        As stated by Postgresql Documentation: https://goo.gl/jpiVir
        In general, a unique constraint is violated if there is more than one
        row in the table where the values of all of the columns included in the
        constraint are equal. However, `two null values are never considered
        equal in this comparison`. That means even in the presence of a unique
        constraint it is possible to `store duplicate rows` that contain a null
        value in at least one of the constrained columns. This behavior
        conforms to the SQL standard, but we have heard that other SQL
        databases might not follow this rule. So be careful when developing
        applications that are intended to be portable.
        """
        self.ensure_one()
        if len(self.search([
                ('product_id', '=', self.product_id.id),
                ('user_id', '=', self.user_id.id)])) == 1:
            return True
        msg = _('There are already baremos with the following settings: \n')
        for matrix in self.search([
                ('product_id', '=', self.product_id.id),
                ('user_id', '=', self.user_id.id)]) - self:
            msg += 'Product: %s, Baremo: %s, Salesman: %s\n' % (
                matrix.product_id.name, matrix.baremo_id.name,
                matrix.user_id.name or _('All Salesmen'))
        msg += _('While you are creating this one:\n')
        for matrix in self:
            msg += 'Product: %s, Baremo: %s, Salesman: %s\n' % (
                matrix.product_id.name, matrix.baremo_id.name,
                matrix.user_id.name or _('All Salesmen'))
        raise ValidationError(msg)


class BaremoDiscount(models.Model):

    _name = 'baremo.discount'
    _order = "porc_disc asc"

    porc_disc = fields.Float(
        '% Disc.', digits=dp.get_precision('Commission'),
        required=True, help="Percent discount per product")
    porc_com = fields.Float(
        '% Comm.', digits=dp.get_precision('Commission'),
        required=True, help="Percent commission @ Percent discount")
    disc_id = fields.Many2one('baremo.line', 'Baremo')
