# coding: utf-8
############################################################################
#    Module Writen For Odoo, Open Source Management Solution
#
#    Copyright (c) 2010 Vauxoo - http://www.vauxoo.com
#    All Rights Reserved.
#    info Vauxoo (info@vauxoo.com)
#    coded by: Yanina Aular <yanina.aular@vauxoo.com>
############################################################################

from odoo import fields, models


class ResPartner(models.Model):

    _inherit = "res.partner"

    baremo_id = fields.Many2one('baremo.book', 'Baremo')
