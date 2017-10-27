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

    name = fields.Char('Due Days Description', required=True, help="Due days Description")
    number = fields.Integer('Due Days', required=True, help="Days since Emission/Due Date")
    disc_ids = fields.One2many('baremo.discount', 'disc_id',
                               'Commission per Discount @ Due Days',
                               help="Commission per Discount @ Due Days")
    baremo_id = fields.Many2one('baremo.book', 'Parent')


class BaremoMatrix(models.Model):

    _name = 'baremo.matrix'

    baremo_id = fields.Many2one(
        'baremo.book', 'Baremo', required=True)
    user_id = fields.Many2one('res.users', 'Salesman')
    product_id = fields.Many2one(
        'product.product', 'Product', required=True)

    @api.constrains('user_id')
    def _check_salesman_empty(self):
        """ A line with empty user is a general rule which
        indicates that the rule of that product applies to all
        salesman. This method avoids to create two o more general
        rules apply to a same product in all baremo matrixes.
        """
        for line in self:
            if not line.user_id and self.search(
                [('product_id', '!=', self.product_id.id),
                 ('user_id', '=', False)]):
                raise ValidationError(
                    _('A line of %s already exists for all salesman.')
                    % line.product_id.name)

    # Just this constraints avoid create two o more rules apply to
    # a same product and user and not take into account when the user
    # is empty.
    _sql_constraints = [
        ('baremo_permutation_unique',
         'unique(user_id, product_id)',
         'Same Salesman & Product can be assigned to only one Baremo')]


class BaremoDiscount(models.Model):

    _name = 'baremo.discount'
    _order = "porc_disc asc"
    _rec_name = 'porc_disc'

    porc_disc = fields.Float('% Disc.', digits=dp.get_precision('Commission'),
                             required=True,
                             help="Percent discount per product")
    porc_com = fields.Float('% Comm.', digits=dp.get_precision('Commission'),
                            required=True,
                            help="Percent commission @ Percent discount")
    disc_id = fields.Many2one('baremo.line', 'Baremo')
