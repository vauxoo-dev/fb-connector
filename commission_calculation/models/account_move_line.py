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

# TODO the query does not including the reconcile_partial, please add it
QUERY_REC_AML = '''
SELECT aml_id, id
FROM
    (SELECT
        l.id AS aml_id
        , l.full_reconcile_id AS p_reconcile_id
    FROM account_move_line l
    INNER JOIN account_journal j ON l.journal_id = j.id
    INNER JOIN account_account a ON l.account_id = a.id
    WHERE
        l.credit != 0.0
        AND a.user_type_id = 1
        AND j.type IN ('cash', 'bank')
        AND (l.full_reconcile_id IS NOT NULL)
    ) AS PAY_VIEW,
    (SELECT
        l.id
        , l.full_reconcile_id AS i_reconcile_id
    FROM account_move_line l
    INNER JOIN account_account a ON l.account_id = a.id
    INNER JOIN account_journal j ON l.journal_id = j.id
    WHERE
        l.debit != 0.0
        AND a.user_type_id = 1
        AND j.type IN ('sale')
        AND (l.full_reconcile_id IS NOT NULL)
    ) AS INV_VIEW
WHERE
    (p_reconcile_id = i_reconcile_id)
'''

# TODO the query does not including the reconcile_partial, please add it
QUERY_REC_INVOICE = '''
SELECT id, invoice_id
FROM
    (SELECT
        l.id
        , l.full_reconcile_id AS p_reconcile_id
    FROM account_move_line l
    INNER JOIN account_journal j ON l.journal_id = j.id
    INNER JOIN account_account a ON l.account_id = a.id
    WHERE
        l.credit != 0.0
        AND a.user_type_id = 1
        AND j.type IN ('cash', 'bank')
        AND (l.full_reconcile_id IS NOT NULL)
    ) AS PAY_VIEW,
    (SELECT
        i.id AS invoice_id
        , l.full_reconcile_id AS i_reconcile_id
    FROM account_move_line l
    INNER JOIN account_invoice i ON l.move_id = i.move_id
    INNER JOIN account_account a ON l.account_id = a.id
    INNER JOIN account_journal j ON l.journal_id = j.id
    WHERE
        l.debit != 0.0
        AND a.user_type_id = 1
        AND j.type IN ('sale')
        AND (l.full_reconcile_id IS NOT NULL)
    ) AS INV_VIEW
WHERE
    (p_reconcile_id = i_reconcile_id)
'''


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    @api.multi
    def _compute_reconciling_aml(self):
        for aml in self:
            aml.rec_aml = False
        sub_query = 'AND aml_id IN (%s)' % ', '.join(
            [str(idx) for idx in self.mapped('id')])
        self.env.cr.execute(QUERY_REC_AML + sub_query)
        rex = self.env.cr.fetchall()
        for aml_id, rec_aml in rex:
            aml = self.browse(aml_id)
            aml.rec_aml = rec_aml

    def _search_rec_aml(self, operator, value):
        if operator not in ('<>', '=', '!=', 'in'):
            return []

        if not isinstance(value, (float, int)) and \
                isinstance(value, list) and not all(
                    isinstance(item, int) for item in value):
            return []

        qu1, qu2 = [], []
        if operator != 'in':
            if value is False and operator == '=':
                qu1.append('(id IS NULL)')
            elif value is False and operator in ('!=', '<>'):
                qu1.append('(id IS NOT NULL)')
            else:
                qu1.append('(id %s %s)' % (operator, '%s'))
                qu2.append(value)
        elif operator == 'in':
            value_len = len(value)
            if value_len > 0:
                qu1.append(' (id IN (%s))' % (
                    ','.join(['%s'] * len(value))))
                qu2 += value
            else:
                qu1.append(' (False)')

        if qu1:
            qu1 = ' AND' + ' AND'.join(qu1)
        else:
            qu1 = ''

        self.env.cr.execute(QUERY_REC_AML + qu1, qu2)
        res = self.env.cr.fetchall()
        if not res:
            return [('id', '=', '0')]
        return [('id', 'in', [x[0] for x in res])]

    @api.multi
    def _compute_reconciling_invoice(self):
        for aml in self:
            aml.rec_invoice = False
        sub_query = 'AND id IN (%s)' % ', '.join(
            [str(xxx) for xxx in self.mapped('id')])
        self.env.cr.execute(QUERY_REC_INVOICE + sub_query)
        rex = self.env.cr.fetchall()

        for aml_id, inv_id in rex:
            aml = self.browse(aml_id)
            aml.rec_invoice = inv_id

    def _search_rec_invoice(self, operator, value):
        if operator not in ('<>', '=', '!=', 'in'):
            return []

        if not isinstance(value, (float, int)) and \
                isinstance(value, list) and not \
                all(isinstance(item, int) for item in value):
            return []

        qu1, qu2 = [], []
        if operator != 'in':
            if value is False and operator == '=':
                qu1.append('(id IS NULL)')
            elif value is False and operator in ('!=', '<>'):
                qu1.append('(id IS NOT NULL)')
            else:
                qu1.append('(id %s %s)' % (operator, '%s'))
                qu2.append(value)
        elif operator == 'in':
            value_len = len(value)
            if value_len > 0:
                qu1.append(' (id IN (%s))' % (
                    ','.join(['%s'] * len(value))))
                qu2 += value
            else:
                qu1.append(' (False)')

        if qu1:
            qu1 = ' AND' + ' AND'.join(qu1)
        else:
            qu1 = ''

        self.env.cr.execute(QUERY_REC_INVOICE + qu1, qu2)
        res = self.env.cr.fetchall()
        if not res:
            return [('id', '=', '0')]
        return [('id', 'in', [x[0] for x in res])]

    @api.model
    def _date_last_payment(self):
        if self.rec_aml:
            return ''
        if self.full_reconcile_id:
            rec_selfs = self.full_reconcile_id.reconciled_line_ids
        elif self.matched_credit_ids or self.matched_debit_ids:
            rec_selfs = self.matched_credit_ids.debit_move_id
            rec_selfs += self.matched_credit_ids.credit_move_id
            rec_selfs += self.matched_debit_ids.debit_move_id
            rec_selfs += self.matched_debit_ids.credit_move_id
        else:
            return ''
        date_last_payment = self.date_last_payment
        for rself in rec_selfs:
            if self.id == rself.id:
                return date_last_payment
            date_last_payment = rself.date if rself.date > date_last_payment \
                else date_last_payment
        return date_last_payment

    @api.depends('full_reconcile_id', 'matched_debit_ids',
                 'matched_credit_ids', 'move_id.ref')
    def _compute_date_last_payment(self):
        for aml_brw in self._get_aml_related_date():
            aml_brw.date_last_payment = \
                aml_brw._date_last_payment()

    @api.model
    def _get_aml_related_date(self):
        res = self.env['account.move.line']
        receivable = self.env.ref('account.data_account_type_receivable')
        for aml_brw in self:
            if aml_brw.account_id.user_type_id != receivable:
                continue
            if aml_brw.journal_id.type not in ('bank', 'cash'):
                continue
            if aml_brw.credit == 0.0:
                continue
            if aml_brw.rec_aml:
                res += aml_brw.rec_aml
            res += aml_brw
        return res

    paid_comm = fields.Boolean('Paid Commission?', default=False)
    rec_invoice = fields.Many2one(
        "account.invoice",
        compute='_compute_reconciling_invoice',
        search='_search_rec_invoice',
        string='Reconciling Invoice',
    )
    rec_aml = fields.Many2one(
        "account.move.line",
        compute='_compute_reconciling_aml',
        search='_search_rec_aml',
        string='Reconciling Journal Item',
    )
    date_last_payment = fields.Date(
        compute='_compute_date_last_payment',
        string='Last Payment Date',
    )
