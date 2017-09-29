# coding: utf-8
from odoo import api, fields, models


class AccountInvoice(models.Model):

    _inherit = "account.invoice"

    @api.model
    def _date_last_payment(self):
        return max(
            aml_brw.date for aml_brw in
            self.payment_move_line_ids.filtered(
                lambda b: b.journal_id.type in ('bank', 'cash')))

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
