# coding: utf-8
from odoo import api, fields, models


class AccountInvoice(models.Model):

    _inherit = "account.invoice"

    date_last_payment = fields.Date(
        compute='_date_last_payment',
        string='Last Payment Date',
        # store={
        #     _inherit: (lambda s, c, u, ids, cx: ids,
        #                 ['residual', 'payment_ids'], 15),
        # }
    )

    @api.multi
    def _date_last_payment(self):
        for inv_brw in self:
            if inv_brw.type != 'out_invoice':
                continue
            date_last_payment = inv_brw.date_last_payment
            for aml_brw in inv_brw.payment_ids:
                if aml_brw.journal_id.type in ('bank', 'cash'):
                    date_last_payment = aml_brw.date > date_last_payment and \
                        aml_brw.date or date_last_payment
            inv_brw.date_last_payment = date_last_payment
