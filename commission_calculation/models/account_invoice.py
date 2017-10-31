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
        payments = [aml.date for aml in self.payment_move_line_ids.filtered(
            lambda b: b.journal_id.type in ('bank', 'cash'))]
        return max(payments) if payments else False

    @api.depends('residual', 'payment_ids')
    def _compute_date_last_payment(self):
        invoices = self.filtered(
            lambda a: a.type == 'out_invoice')
        for invoice in invoices:
            invoice.date_last_payment = \
                invoice._date_last_payment()

    date_last_payment = fields.Date(
        store=True,
        compute='_compute_date_last_payment',
        string='Last Payment Date',
        help="Date of the last payment on the invoice")
