# coding: utf-8
############################################################################
#    Module Writen For Odoo, Open Source Management Solution
#
#    Copyright (c) 2010 Vauxoo - http://www.vauxoo.com
#    All Rights Reserved.
#    info Vauxoo (info@vauxoo.com)
#    coded by: Humberto Arocha <hbto@vauxoo.com>
#              Yanina Aular <yanina.aular@vauxoo.com>
############################################################################

from odoo import api, fields, models


class AccountInvoice(models.Model):

    _inherit = "account.invoice"

    @api.depends('residual', 'payment_ids')
    def _compute_date_last_payment(self):
        for invoice in self.filtered(lambda a: a.type == 'out_invoice'):
            invoice.date_last_payment = invoice.payment_move_line_ids.search([
                ('id', 'in', invoice.payment_move_line_ids.ids),
                ('journal_id.type', 'in', ('bank', 'cash'))],
                limit=1, order='date desc').date

    date_last_payment = fields.Date(
        store=True,
        compute='_compute_date_last_payment',
        string='Last Payment Date',
        help="Date of the last payment on the customer invoice")
