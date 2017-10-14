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

    @api.model
    def _date_last_payment(self):
        payments = [aml_brw.date for aml_brw in
        self.payment_move_line_ids.filtered(
            lambda b: b.journal_id.type in ('bank', 'cash'))]
        return max(payments) if payments else False

    @api.depends('residual', 'payment_ids')
    def _compute_date_last_payment(self):
        invoices = self.filtered(
            lambda a: a.type == 'out_invoice')
        for inv_brw in invoices:
            inv_brw.date_last_payment = \
                inv_brw._date_last_payment()

    date_last_payment = fields.Date(
        compute='_compute_date_last_payment',
        string='Last Payment Date',
    )
