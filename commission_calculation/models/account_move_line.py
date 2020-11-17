from odoo import api, fields, models


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    @api.multi
    @api.depends('matched_debit_ids')
    def _compute_reconciling_aml(self):
        aml_obj = self.env[self._name]
        for aml in self.filtered(
                lambda a: a.credit > 0 and
                a.account_id.internal_type == 'receivable' and
                a.journal_id.type in ['bank', 'cash']):
            rec_aml = aml.mapped('matched_debit_ids.debit_move_id').filtered(
                lambda l: l.journal_id.type == 'sale')
            rec_aml = rec_aml[0] if rec_aml else aml_obj
            aml.rec_aml = rec_aml.id
            aml.rec_invoice = rec_aml.invoice_id.id

    @api.depends('matched_credit_ids')
    def _compute_date_last_payment(self):
        for aml in self:
            aml.date_last_payment = self.search([
                ('id', 'in', aml.mapped(
                    'matched_credit_ids.credit_move_id')._ids),
                ('journal_id.type', 'in', ['bank', 'cash']),
                ('account_id.internal_type', '=', 'receivable')],
                limit=1, order='date desc').date

    paid_comm = fields.Boolean('Paid Commission?', readonly=True)
    rec_invoice = fields.Many2one(
        "account.invoice",
        compute='_compute_reconciling_aml',
        store=True,
        string='Reconciling Invoice')
    rec_aml = fields.Many2one(
        "account.move.line",
        compute='_compute_reconciling_aml',
        store=True,
        string='Reconciling Journal Item')
    date_last_payment = fields.Date(
        store=True,
        compute='_compute_date_last_payment',
        string='Last Payment Date')
