# coding: utf-8
from odoo import api, fields, models


class AccountInvoice(models.Model):

    _inherit = "account.invoice"

    date_last_payment = fields.Function(
        _date_last_payment, string='Last Payment Date', type="date",
        store={
            _inherit: (lambda s, c, u, ids, cx: ids,
                        ['residual', 'payment_ids'], 15),
        })

    def _date_last_payment(self, cr, uid, ids, fieldname, arg, context=None):
        res = {}.fromkeys(ids, None)
        context = context or {}
        for inv_brw in self.browse(cr, uid, ids, context=context):
            if inv_brw.type != 'out_invoice':
                continue
            date_last_payment = inv_brw.date_last_payment
            for aml_brw in inv_brw.payment_ids:
                if aml_brw.journal_id.type in ('bank', 'cash'):
                    date_last_payment = aml_brw.date > date_last_payment and \
                        aml_brw.date or date_last_payment

            res[inv_brw.id] = date_last_payment
        return res
