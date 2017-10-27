# coding: utf-8
############################################################################
#    Module Writen For Odoo, Open Source Management Solution
#
#    Copyright (c) 2017 Vauxoo - http://www.vauxoo.com
#    All Rights Reserved.
#    info Vauxoo (info@vauxoo.com)
#    coded by: Humberto Arocha <hbto@vauxoo.com>
#              Yanina Aular <yanina.aular@vauxoo.com>
#    audited by: Humberto Arocha <hbto@vauxoo.com>
############################################################################

from odoo import api, fields, models


class ResCompany(models.Model):

    _inherit = "res.company"
    _description = 'Companies'

    tax = fields.Float('Default Tax for Commissions')

    baremo_id = fields.Many2one(
        'baremo.book',
        related='partner_id.baremo_id',
        string="Baremo")
