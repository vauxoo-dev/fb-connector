# -*- coding: utf-8 -*-
############################################################################
#    Module Writen For Odoo, Open Source Management Solution
#
#    Copyright (c) 2017 Vauxoo - http://www.vauxoo.com
#    All Rights Reserved.
#    info Vauxoo (info@vauxoo.com)
#    coded by: Yanina Aular <yanina.aular@vauxoo.com>
#    audited by: Humberto Arocha <hbto@vauxoo.com>
############################################################################

from odoo import fields, models


class CommissionTemplate(models.Model):

    _name = 'commission.template'
    _inherit = 'commission.abstract'

    name = fields.Char(
        "Template's name", required=True,
        track_visibility='onchange',
        help="Commission template's name")
