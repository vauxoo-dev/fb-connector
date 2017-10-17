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
        string="Baremo")
