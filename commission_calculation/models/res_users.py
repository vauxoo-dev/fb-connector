# coding: utf-8
############################################################################
#    Module Writen For Odoo, Open Source Management Solution
#
#    Copyright (c) 2017 Vauxoo - http://www.vauxoo.com
#    All Rights Reserved.
#    info Vauxoo (info@vauxoo.com)
#    coded by: Yanina Aular <yanina.aular@vauxoo.com>
############################################################################

from odoo import fields, models


class ResUsers(models.Model):

    _inherit = "res.users"

    matrix_ids = fields.One2many(
        'baremo.matrix', 'user_id',
        'Baremo Matrix', copy=False,
        help="Display all commissions of the user")
