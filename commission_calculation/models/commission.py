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

from __future__ import division
from datetime import datetime, date as dt
import logging

from odoo import _, fields, models, api
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning as UserError

_logger = logging.getLogger(__name__)

# Extra Imports
try:
    from pandas import DataFrame
except ImportError:
    _logger.info('account_currency_tools is declared '
                 ' from addons-vauxoo '
                 ' you will need: sudo pip install pandas')


def t_time(date):
    """Trims time from "%Y-%m-%d %H:%M:%S" to "%Y-%m-%d"
    """
    date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    date = dt(date.year, date.month, date.day)
    return date.strftime("%Y-%m-%d")


class CommissionPayment(models.Model):

    _name = 'commission.payment'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'commission.abstract']

    @api.onchange("template_id")
    def _onchange_template(self):
        if self.template_id:
            self.commission_type = self.template_id.commission_type
            self.scope = self.template_id.scope
            self.policy_date_start = self.template_id.policy_date_start
            self.policy_date_end = self.template_id.policy_date_end
            self.salesman_policy = self.template_id.salesman_policy
            self.baremo_policy = self.template_id.baremo_policy
            self.baremo_id = self.template_id.baremo_id

    name = fields.Char(
        'Concept', required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        help="Commission's description")
    baremo_id = fields.Many2one(
        'baremo.book', 'Baremo', required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange')
    date_start = fields.Date(
        'Start Date', required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        help="The calculation of commissions begins "
        "with this date, including it."
        "Invoices and journal entry in the "
        "date range will be taken into"
        "account in the calculation of "
        "commissions. Start Date <= date <= End Date")
    date_stop = fields.Date(
        'End Date', required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        help="The calculation of commissions ends "
        "with this date, including it."
        "Invoices and journal entry in the "
        "date range will be taken into"
        "account in the calculation of "
        "commissions. Start Date <= date <= End Date")
    total = fields.Float(
        'Total Commission',
        default=0.0,
        digits=dp.get_precision('Commission'),
        readonly=True, states={'write': [('readonly', False)]},
        track_visibility='onchange',
        help="Total commission to paid.")

    line_product_ids = fields.One2many(
        'commission.lines', 'commission_id',
        'Commission per products', readonly=True,
        domain=[('product_id', '!=', False)],
        states={'write': [('readonly', False)]})

    line_invoice_ids = fields.One2many(
        'commission.lines', 'commission_id',
        'Commission per invoices', readonly=True,
        domain=[('product_id', '=', False)],
        states={'write': [('readonly', False)]})

    line_ids = fields.One2many(
        'commission.lines', 'commission_id',
        'Commission per products', readonly=True,
        states={'write': [('readonly', False)]})

    salesman_ids = fields.One2many(
        'commission.salesman', 'commission_id',
        'Salespeople Commissions', readonly=True,
        states={'write': [('readonly', False)]})

    user_ids = fields.Many2many(
        'res.users', 'commission_users',
        'commission_id', 'user_id', 'Salespeople', required=True,
        readonly=True, states={'draft': [('readonly', False)]})

    aml_ids = fields.Many2many(
        'account.move.line', 'commission_aml_rel', 'commission_id',
        'aml_id', 'Journal Items', copy=False, readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')],
        readonly=True,
        default='draft', track_visibility='onchange',
        help="State of the commission document")

    template_id = fields.Many2one(
        'commission.template',
        readonly=True, states={'draft': [('readonly', False)]})

    company_id = fields.Many2one(
        'res.company', readonly=True,
        default=lambda self: self.env.user.company_id.id)

    currency_id = fields.Many2one(
        related='company_id.currency_id',
        store=True, readonly=True,
        help="Currency at which this report will be"
             "expressed. If not selected will be used the "
             "one set in the company")

    exchange_date = fields.Date(
        help="Date of change that will be printed in the"
             " report, with respect to the currency of the"
             "company")

    comm_fix = fields.Boolean('Fix Commissions?')

    unknown_salespeople = fields.Boolean(
        help="If true then if the salespeople in the record does not have a "
             "clear sales person set then this will be computed as unknown if "
             "False then this lines will not be included in the computation")

    @api.multi
    def action_view_fixlines(self):
        """This function returns an action that display existing Commissions of
        given commission payment ids that are required for some details to
        provide a proper computation of commissions.
        """
        result = self.env.ref(
            'commission_calculation.comm_line_fix_act').read()[0]
        # compute the number of payments to display
        cl_ids = self.line_ids.filtered(lambda line: not line.salesman_id)._ids
        # choose the view_mode accordingly
        result['domain'] = [('id', 'in', cl_ids)]
        result['name'] = result['display_name'] = 'Fix commissions'
        return result

    @api.multi
    def action_view_payment(self):
        """This function returns an action that
        display existing Payments of given
        commission payment ids. It can either be
        a in a list or in a form view,
        if there is only one invoice to show.
        """
        result = self.env.ref(
            'commission_calculation.action_account_moves_all_tree').read()[0]
        # choose the view_mode accordingly
        result['domain'] = [('id', 'in', self.aml_ids._ids)]
        return result

    @api.multi
    def action_view_invoice(self):
        """This function returns an action that display existing invoices of given
        commission payment ids. It can either be a in a list or in a form view,
        if there is only one invoice to show.
        """
        result = self.env.ref('account.action_invoice_tree1').read()[0]
        # choose the view_mode accordingly
        invoice_ids = self.line_ids.filtered(
            lambda l: l.line_type == 'ok').mapped('invoice_id')._ids
        result['domain'] = [('id', 'in', invoice_ids)]
        return result

    @api.multi
    def _prepare_aml(self):
        aml_obj = self.env['account.move.line']
        for comm_rec in self:
            date_start = comm_rec.date_start
            date_stop = comm_rec.date_stop

            # In this search we will restrict domain to those Entry Lines
            # coming from a Cash or Bank Journal within the given dates that at
            # least are reconciled against an `receivable item`
            if self.commission_type == 'partial_payment':
                args = [('date', '>=', date_start), ('date', '<=', date_stop),
                        ('journal_id.type', 'in', ('bank', 'cash')),
                        ('rec_aml', '!=', False),
                        ('account_id.internal_type', '=', 'receivable'),
                        ('credit', '>', 0.0), ('paid_comm', '=', False)]
                aml_ids = aml_obj.search(args)
            # We look for all thouse Entry Lines that are fully reconciled,
            # meaning, the `receivable items` are no longer outstanding
            elif self.commission_type == 'fully_paid_invoice':
                args = [
                    ('full_reconcile_id', '!=', False),
                    ('journal_id.type', '=', 'sale'),
                    ('account_id.internal_type', '=', 'receivable'),
                    ('date_last_payment', '>=', date_start),
                    ('date_last_payment', '<=', date_stop),
                    ('debit', '>', 0.0), ]

                aml_ids = aml_obj.search(args).mapped(
                    'matched_credit_ids.credit_move_id').filtered(
                        lambda l: l.journal_id.type in ('bank', 'cash') and
                        l.account_id.internal_type == 'receivable' and
                        not l.paid_comm)
            salesman_aml_ids = aml_ids.filtered(self._check_salesman_policy)
            unknown_aml_ids = aml_obj
            if self.unknown_salespeople:
                unknown_aml_ids = aml_ids.filtered(
                    lambda l: not self._get_salesman_policy(l))
            aml_ids = salesman_aml_ids + unknown_aml_ids
            comm_rec.write({
                'aml_ids': [(6, comm_rec.id, aml_ids._ids)]})
        return True

    @api.model
    def _get_params(
            self, aml, dcto=0.0, partner_id=None, product_id=None):
        res = dict(
            salesman=self._get_salesman_policy(aml),
            policy_date_start=self._get_policy_start_date(aml),
            policy_date_end=self._get_policy_end_date(aml))
        policy_baremo = self._get_policy_baremo(
            aml, partner_id, product_id, res['salesman'])

        def fnc(date):
            return datetime.strptime(date, '%Y-%m-%d')
        res['days'] = (
            fnc(res['policy_date_end']) - fnc(res['policy_date_start'])).days
        params = self._get_rate(res['days'], policy_baremo, dcto)
        res.update(params)
        return res

    @api.model
    def _get_rate(self, days, baremo, dcto=0.0):
        res = dict(bar_day=0.0, bar_dcto_comm=0.0, bardctdsc=0.0)
        day_id = baremo.bar_ids.filtered(lambda l: days <= l.number)
        if not day_id:
            return res
        day_id = day_id[0]
        dcto_id = day_id.disc_ids.filtered(lambda disc: dcto <= disc.porc_disc)
        if not dcto_id:
            res['bar_day'] = day_id.number
            return res
        res['bardctdsc'] = dcto_id[0].porc_disc
        res['bar_dcto_comm'] = dcto_id[0].porc_com
        return res

    @api.model
    def _get_policy_start_date(self, pay_id):
        comm_rec = self
        aml_rec = pay_id.matched_debit_ids.debit_move_id.filtered(
            lambda a: a.journal_id.type == 'sale')
        if not aml_rec:
            return False
        if comm_rec.policy_date_start == 'invoice_emission_date':
            date_field = 'date'
        elif comm_rec.policy_date_start == 'invoice_due_date':
            date_field = 'date_maturity'
        return min(l[date_field] for l in aml_rec)

    @api.model
    def _get_policy_end_date(self, pay_id):
        date = pay_id.date
        if self.policy_date_end == 'last_payment_date':
            date = pay_id.matched_debit_ids.debit_move_id.filtered(
                lambda a: a.journal_id.type == 'sale').invoice_id.\
                date_last_payment or date
        return date

    @api.model
    def _check_salesman_policy(self, aml):
        salesman = self._get_salesman_policy(aml)
        return self._get_saleman(salesman)

    @api.model
    def _get_saleman(self, salesman):
        if not salesman or (salesman not in self.user_ids):
            return False
        return True

    @api.model
    def _get_salesman_policy(self, pay_id):
        rec_aml = pay_id.rec_aml
        rec_invoice = rec_aml.invoice_id
        rp_obj = self.env['res.partner']
        if self.salesman_policy == 'on_invoice':
            return rec_invoice.user_id if rec_invoice else \
                rec_aml.partner_id.user_id
        elif self.salesman_policy == 'on_invoiced_partner':
            return rec_invoice.partner_id.user_id if \
                rec_invoice else rec_aml.partner_id.user_id
        elif self.salesman_policy == 'on_accounting_partner':
            partner = rec_invoice.partner_id if \
                rec_invoice else rec_aml.partner_id
            return rp_obj._find_accounting_partner(partner).user_id
        return self.env['res.users']

    @api.model
    def _get_policy_baremo(
            self, pay_id, partner_id=None, product_id=None, salesman_id=None):
        rec_aml = pay_id.rec_aml
        rec_invoice = rec_aml.invoice_id
        rp_obj = self.env['res.partner']
        if self.baremo_policy == 'onCompany':
            return self.company_id.partner_id.baremo_id
        elif self.baremo_policy == 'onPartner':
            partner_id = partner_id if partner_id else \
                (rec_invoice.partner_id if rec_invoice else rec_aml.partner_id)
            return partner_id.baremo_id
        elif self.baremo_policy == 'onAccountingPartner':
            partner_id = partner_id if partner_id else \
                (rec_invoice.partner_id if rec_invoice else rec_aml.partner_id)
            partner_id = rp_obj._find_accounting_partner(partner_id)
            return partner_id.baremo_id
        elif self.baremo_policy == 'onUser':
            return salesman_id.partner_id.baremo_id
        elif self.baremo_policy == 'onCommission':
            return self.baremo_id
        elif self.baremo_policy == 'onMatrix':
            bm_obj = self.env['baremo.matrix']
            domain = [('product_id', '=', product_id.id), '|',
                      ('user_id', '=', salesman_id.id),
                      ('user_id', '=', False)]
            baremo = bm_obj.search(domain, order="user_id desc", limit=1)
            return baremo.baremo_id or self.baremo_id

    @api.model
    def _get_payment_on_invoice_line(self, pay_id):
        res = []
        prod_prices = self.env['product.historic.price']

        # If it is here it is because it has a valid invoice
        inv_rec = pay_id.rec_invoice

        # Revision de cada linea de factura (productos)
        # Verificar si tiene producto asociado
        for inv_lin in inv_rec.invoice_line_ids.filtered(
                lambda line: line.product_id):

            # DETERMINAR EL PORCENTAJE DE IVA EN LA LINEA (perc_iva)
            # =============================================================
            # =============================================================
            # Determinar si la linea de la factura tiene un impuesto
            # (perc_iva). El impuesto aplicado a una linea es igual a la
            # suma de los impuestos se asume que todos los impuestos son
            # porcentuales
            perc_iva = (sum([
                tax.amount for tax in inv_lin.invoice_line_tax_ids]) * 100
                if inv_lin.invoice_line_tax_ids else 0.0)
            # If it is here is because it has an associated product
            prod_id = inv_lin.product_id.id

            # looking for the historical price (using its ordering criteria)
            price_ids = prod_prices.search([('product_id', '=', prod_id)])
            # look for the historical price
            no_price = True

            for prod_prices_rec in price_ids:
                if inv_rec.date_invoice >= t_time(prod_prices_rec.datetime):
                    list_price = prod_prices_rec.price
                    list_date = prod_prices_rec.datetime
                    no_price = False
                    break

            # If not historic, then take the lst_price from product
            if inv_lin.product_id.lst_price > 0 and no_price:
                list_price = inv_lin.product_id.lst_price
                list_date = self.date_start
                no_price = False

            if not no_price:
                # Get the actual discount in the invoice.
                price_unit = inv_lin.price_unit
                if abs((inv_lin.price_subtotal / inv_lin.quantity) -
                        inv_lin.price_unit) > 0.05:
                    # with this we ensure we are not passing by the discount
                    price_unit = round((inv_lin.price_subtotal /
                                        inv_lin.quantity), 2)

                dcto = round((list_price - price_unit) * 100 / list_price, 1) \
                    if list_price else 0.0

                params = self._get_params(
                    pay_id, dcto=dcto, product_id=inv_lin.product_id)
                salesman = params['salesman']
                policy_date_start = params['policy_date_start']
                policy_date_end = params['policy_date_end']
                bar_day = params['bar_day']
                bar_dcto_comm = params['bar_dcto_comm']
                bardctdsc = params['bardctdsc']
                days = params['days']

                ###############################
                # Computation by product_line #
                ###############################

                penbxlinea = pay_id.credit * (
                    inv_lin.price_subtotal /
                    inv_rec.amount_untaxed)
                fact_sup = 1 - 0.0 / 100 - 0.0 / 100
                fact_inf = 1 + (perc_iva / 100) * (1 - 0.0 / 100) - \
                    0.0 / 100 - 0.0 / 100

                comm_line = penbxlinea * fact_sup * (
                    bar_dcto_comm / 100) / fact_inf

                if pay_id.currency_id and pay_id.amount_currency:
                    payxlinea_curr = pay_id.amount_currency * (
                        inv_lin.price_subtotal /
                        inv_rec.amount_untaxed)

                    currency_amount = (abs(payxlinea_curr) * fact_sup *
                                       (bar_dcto_comm / 100) / fact_inf)
                elif pay_id.currency_id and not pay_id.amount_currency:
                    return True
                else:
                    currency_amount = comm_line

                res.append({
                    'commission_id': self.id,
                    'aml_id': pay_id.id,
                    'am_rec': inv_rec.move_id.id,
                    'name':
                    pay_id.move_id.name and
                    pay_id.move_id.name or '/',
                    'payment_date': pay_id.date,
                    'partner_id': inv_rec.partner_id.id,
                    'invoice_id': inv_rec.id,
                    'salesman_id': salesman and salesman.id,
                    'invoice_payment': pay_id.credit,
                    'invoice_date': inv_rec.date_invoice,
                    'date_start': policy_date_start,
                    'date_stop': policy_date_end,
                    'days': days,
                    'inv_subtotal': inv_rec.amount_untaxed,
                    'product_id': inv_lin.product_id.id,
                    'price_unit': price_unit,
                    'price_subtotal': inv_lin.price_subtotal,
                    'price_list': list_price,
                    'price_date': list_date,
                    'perc_iva': perc_iva,
                    'rate_item': dcto,
                    'rate_number': bardctdsc,
                    'timespan': bar_day,
                    'baremo': bar_dcto_comm,
                    'amount': comm_line,
                    'currency_amount': currency_amount,
                    'currency_id': inv_rec.currency_id and
                    inv_rec.currency_id.id or
                    inv_rec.company_id.currency_id.id,
                    'line_type': 'ok',
                    })
            else:
                # If we do not have a price to compare to we mark the line to
                #  audit what to do, no change the invoice is an important part
                # on the process.
                res.append({
                    'name': inv_lin.name,
                    'commission_id': self.id,
                    'product_id': inv_lin.product_id.id,
                    'payment_date': inv_rec.date_invoice,
                    'invoice_id': inv_rec.id,
                    'line_type': 'no_price',
                    })

        # Marking the line as "no_product" in order to know the ones to review
        # the fact of the delicated processs of change an invoice line we
        # prefer simply inform.
        for inv_lin in inv_rec.invoice_line_ids\
                .filtered(lambda line: not line.product_id):
            res.append({
                'name': inv_lin.name,
                'invoice_id': inv_rec.id,
                'commission_id': self.id,
                'line_type': 'no_product',
                'aml_id': pay_id.id})
        return res

    @api.model
    def _get_payment_on_invoice(self, aml):
        res = []
        params = self._get_params(aml)
        salesman = params['salesman']
        policy_date_start = params['policy_date_start']
        policy_date_end = params['policy_date_end']
        bar_day = params['bar_day']
        bar_dcto_comm = params['bar_dcto_comm']
        bardctdsc = params['bardctdsc']
        days = params['days']

        # If it is here it is because this actually have an invoice
        invoice = aml.rec_invoice

        # Get the VAT percentage (perc_iva)
        # =================================
        # =================================
        perc_iva = (invoice.amount_total / invoice.amount_untaxed - 1) * 100

        #################################
        # Compute Commission by Invoice #
        #################################

        penbxlinea = aml.credit
        fact_sup = 1 - 0.0 / 100 - 0.0 / 100
        fact_inf = 1 + (perc_iva / 100) * (1 - 0.0 / 100) - \
            0.0 / 100 - 0.0 / 100

        comm_line = penbxlinea * fact_sup * (
            bar_dcto_comm / 100) / fact_inf

        currency_amount = comm_line
        if aml.currency_id and aml.amount_currency:
            currency_amount = abs(aml.amount_currency) * fact_sup * (
                bar_dcto_comm / 100) / fact_inf
        elif aml.currency_id and not aml.amount_currency:
            return True

        res.append({
            'commission_id': self.id,
            'aml_id': aml.id,
            'am_rec': invoice.move_id.id,
            'invoice_id': invoice.id,
            'name': aml.move_id.name and aml.move_id.name or '/',
            'payment_date': aml.date,
            'partner_id': invoice.partner_id.id,
            'salesman_id': salesman and salesman.id,
            'invoice_payment': aml.credit,
            'invoice_date': invoice.date_invoice,
            'date_start': policy_date_start,
            'date_stop': policy_date_end,
            'days': days,
            'inv_subtotal': invoice.amount_untaxed,
            'perc_iva': perc_iva,
            'rate_number': bardctdsc,
            'timespan': bar_day,
            'baremo': bar_dcto_comm,
            'amount': comm_line,
            'currency_amount': currency_amount,
            'currency_id': invoice.currency_id and
            invoice.currency_id.id or invoice.company_id.currency_id.id,
            'line_type': 'ok',
        })

        return res

    @api.model
    def _get_payment_on_aml(self, aml):

        res = []

        params = self._get_params(aml)
        policy_date_start = params['policy_date_start']
        policy_date_end = params['policy_date_end']
        bar_day = params['bar_day']
        bar_dcto_comm = params['bar_dcto_comm']
        bardctdsc = params['bardctdsc']
        days = params['days']

        res.append({
            'commission_id': self.id,
            'aml_id': aml.id,
            'am_rec': aml.rec_aml.move_id.id,
            'invoice_id': aml.rec_aml.invoice_id.id,
            'name': aml.move_id.name and aml.move_id.name or '/',
            'payment_date': aml.date,
            'partner_id': aml.partner_id.id,
            'salesman_id': None,
            'invoice_payment': aml.credit,
            'invoice_date': aml.rec_aml.date,
            'date_start': policy_date_start,
            'date_stop': policy_date_end,
            'days': days,
            'inv_subtotal': None,
            'perc_iva': None,
            'rate_number': bardctdsc,
            'timespan': bar_day,
            'baremo': bar_dcto_comm,
            'amount': 0.0,
            'currency_amount': None,
            'currency_id': aml.currency_id and
            aml.currency_id.id or aml.company_id.currency_id.id,
            'line_type': 'ok',
            })

        return res

    @api.model
    def _get_payment(self):
        res = []
        salesman_aml_ids = self.aml_ids.filtered(self._check_salesman_policy)
        if self.scope == 'product_invoiced':
            for aml in salesman_aml_ids.filtered('rec_invoice'):
                res.extend(
                    self._get_payment_on_invoice_line(aml))
        elif self.scope == 'whole_invoice':
            for aml in salesman_aml_ids.filtered('rec_invoice'):
                res.extend(self._get_payment_on_invoice(aml))
        for aml in salesman_aml_ids.filtered(lambda l: not l.rec_invoice):
            res.extend(self._get_payment_on_aml(aml))

        if not self.unknown_salespeople:
            return res
        # Recording aml with unknown salesman
        for aml in self.aml_ids.filtered(
                lambda l: not self._get_salesman_policy(l)):
            res.extend(self._get_payment_on_aml(aml))
        return res

    @api.multi
    def _post_processing(self):
        salesman_ids = self.env['commission.salesman']
        comm_line_obj = self.env['commission.lines']

        # We group by salesman here to be used easiest

        cl_fields = ['id', 'salesman_id', 'currency_id', 'amount',
                     'currency_amount', 'invoice_id', 'salespeople_id']

        for commission in self:
            # Erasing what was previously set as Commission per Salesman
            commission.salesman_ids.unlink()

            # Pick all salesman and sum all their commissions
            # Order in a tree all the commissions lines
            cl_ids = commission.line_ids.filtered(
                lambda comm: comm.line_type in ('ok', 'exception')).read(
                    cl_fields, load=None)
            if not cl_ids:
                continue
            cl_data = DataFrame(cl_ids).set_index('id')
            cl_data_grouped = cl_data.groupby(['salesman_id', 'currency_id'])

            cl_data_agg = cl_data_grouped.sum()
            sale_comm_data = cl_data_agg.to_dict()
            sale_comm_cl = cl_data_grouped.groups

            sale_comm = sale_comm_data.get('amount')
            sale_comm_curr = sale_comm_data.get('currency_amount')
            for key, value in sale_comm.items():
                salesman_id, currency_id = key
                vendor_id = salesman_ids.create({
                    'commission_id': commission.id,
                    'salesman_id': salesman_id,
                    'currency_id': currency_id,
                    'total': value,
                    'currency_amount': sale_comm_curr[key],
                    'company_id': commission.company_id.id,
                })
                # transform from numpy.int64 to int
                commline_ids = [
                    int(item) for item in sale_comm_cl[key].tolist()]
                comm_line_reg = comm_line_obj.browse(commline_ids)
                comm_line_reg.write({'salespeople_id': vendor_id.id})
            commission.write({
                'total': cl_data.sum().get('amount'),
                'comm_fix': not all(
                    cl_data.groupby('salesman_id').groups.keys()),
            })
            commission.line_ids.filtered(
                lambda comm: not comm.salesman_id and not comm.line_type)\
                .write({'line_type': 'exception'})

        return True

    @api.multi
    def _create_lines(self, res):
        self.ensure_one()
        self.write({'line_ids': [(0, 0, l) for l in res]})

    @api.multi
    def prepare(self):
        """Prepare the commission lines and basically do 3 things:

        - journal_id.type in ('cash', 'bank'): which means just money on banks.
        - state == 'valid' : which means the line is actually valid.
        - paid_comm: it has not been taken for another commission before.
        """
        if self.baremo_policy == 'onMatrix' and \
                self.scope != 'product_invoiced':
            raise UserError(
                _('Baremo on Matrix only applies on Invoiced Products'))
        self.clear()
        self._prepare_aml()
        res = self._get_payment()
        self._create_lines(res)
        self._post_processing()
        self.write({'state': 'open'})
        return True

    @api.multi
    def _recompute_commission(self):
        self.mapped('salesman_ids')\
            .filtered(lambda comm_salesman: not comm_salesman.salesman_id)\
            .mapped('line_ids')._recompute_commission()
        return True

    @api.multi
    def action_recompute(self):
        self._recompute_commission()
        self._post_processing()
        return True

    @api.multi
    def action_draft_from_done(self):
        self.aml_ids.write({'paid_comm': False})
        self.action_draft()

    @api.multi
    def action_draft(self):
        self.clear()
        self.write({'state': 'draft', 'total': 0.0})
        return True

    @api.multi
    def clear(self):
        """Deletes all associated record from Commission Payment
        """
        for commission in self:
            commission.line_ids.unlink()
            commission.salesman_ids.unlink()
            commission.write(
                {'aml_ids': [(3, aml.id) for aml in commission.aml_ids]})

    @api.multi
    def validate(self):
        """When validate we mark explicitly the payments related to this
        commission as paid_comm.
        """
        for commission in self:
            payments = commission.aml_ids.filtered('paid_comm')
            if not payments and not commission.comm_fix:
                commission.aml_ids.write({'paid_comm': True})
                commission.write({'state': 'done'})
                continue
            message = _('Please check these payments that were paid before '
                        'this validation, you will not be able to validate '
                        'this commission:') + '<br/>' + \
                '<br/>'.join(payments.mapped('name'))
            commission.message_post(
                subject='Not validated commissions. Wrong payments',
                body=message)
        return True


class CommissionLines(models.Model):

    _name = 'commission.lines'
    _order = 'payment_date'

    commission_id = fields.Many2one(
        'commission.payment', required=True)
    name = fields.Char('Transaction', required=True)
    payment_date = fields.Date()
    aml_id = fields.Many2one('account.move.line', 'Entry Line')
    am_rec = fields.Many2one('account.move', 'Reconciling Entry')
    invoice_id = fields.Many2one(
        "account.invoice",
        readonly=True,
        string='Reconciling Invoice')
    partner_id = fields.Many2one('res.partner')
    salesman_id = fields.Many2one('res.users')
    salespeople_id = fields.Many2one(
        'commission.salesman', 'Salespeople Commission')
    # TODO: may be a leated is enought with aml_id
    invoice_payment = fields.Float(
        'Pay. to Doc.', digits=dp.get_precision('Commission'),
        help='Credit of the aml related')
    invoice_date = fields.Date(
        'Accounting date',
        help='This is the date of the document related, if invoice the '
             'invoice date if journal item the effective date')
    date_start = fields.Date(
        'Start Date', readonly=True,
        help="The result of the 'Computation begins on' "
             "decision in the commission")
    date_stop = fields.Date(
        'End Date', readonly=True,
        help="The result of the 'Computation ends on' decision in the "
             "commission")
    days = fields.Float(
        'Comm. Days', digits=dp.get_precision('Commission'),
        help="The difference between computation "
             "begins on and the date on the line")

    inv_subtotal = fields.Float(
        'SubTot. Doc.', digits=dp.get_precision('Commission'))

    product_id = fields.Many2one('product.product')
    price_unit = fields.Float(
        'Price. Unit.',
        digits=dp.get_precision('Commission'))
    price_subtotal = fields.Float(
        'SubTot. Product',
        digits=dp.get_precision('Commission'))

    price_list = fields.Float(
        digits=dp.get_precision('Commission'))
    price_date = fields.Date('List Date')

    perc_iva = fields.Float(
        'Tax (%)', digits=dp.get_precision('Commission'))

    rate_item = fields.Float(
        'Disc. (%)', digits=dp.get_precision('Commission'))

    rate_number = fields.Float(
        'B./Rate (%)', digits=dp.get_precision('Commission'))
    timespan = fields.Float(
        'B./Days', digits=dp.get_precision('Commission'))
    baremo = fields.Float(
        'B./%Comm.', digits=dp.get_precision('Commission'))
    amount = fields.Float(
        digits=dp.get_precision('Commission'),
        help="Amount on the company currency")
    currency_amount = fields.Float(
        digits=dp.get_precision('Commission'),
        help="Amount on the currency of the payment itself")
    currency_id = fields.Many2one('res.currency')

    line_type = fields.Selection(
        [('no_product', 'W/o Product'), ('no_price', 'W/o Price'),
         ('exception', 'Exception'), ('ok', 'Ok')], default='ok')

    # This method can be the one we can actually use to compute the value of
    # each line to fetch the commissions
    @api.multi
    def _recompute_commission(self):
        for line in self:
            commission = line.commission_id

            aml = line.aml_id

            params = commission._get_params(aml)
            policy_date_start = params['policy_date_start']
            policy_date_end = params['policy_date_end']
            bar_day = params['bar_day']
            bar_dcto_comm = params['bar_dcto_comm']
            bardctdsc = params['bardctdsc']
            days = params['days']

            ######################
            # Actual computation #
            ######################

            # Right now I have not figure out a way to know how much was taxed
            perc_iva = commission.company_id.tax

            penbxlinea = aml.credit
            fact_sup = 1 - 0.0 / 100 - 0.0 / 100
            fact_inf = 1 + (perc_iva / 100) * (1 - 0.0 / 100) - \
                0.0 / 100 - 0.0 / 100

            comm_line = penbxlinea * fact_sup * (
                bar_dcto_comm / 100) / fact_inf

            if aml.currency_id and aml.amount_currency:
                currency_amount = abs(aml.amount_currency) * \
                    fact_sup * (bar_dcto_comm / 100) / fact_inf
            elif aml.currency_id and not aml.amount_currency:
                return True
            else:
                currency_amount = comm_line

            # Generar las lineas de comision por cada factura
            line.write({
                'payment_date': aml.date,
                'invoice_payment': aml.credit,
                'invoice_date': aml.rec_aml.date,
                'date_start': policy_date_start,
                'date_stop': policy_date_end,
                'days': days,
                'inv_subtotal': (aml.rec_aml.debit / (1 + perc_iva / 100)),
                'perc_iva': perc_iva,
                'rate_number': bardctdsc,
                'timespan': bar_day,
                'baremo': bar_dcto_comm,
                'amount': comm_line,
                'currency_amount': currency_amount,
                'currency_id': aml.currency_id and
                aml.currency_id.id or
                aml.company_id.currency_id.id,
            })
        return True


class CommissionSalesman(models.Model):

    _name = 'commission.salesman'
    _rec_name = 'salesman_id'

    commission_id = fields.Many2one(
        'commission.payment', readonly=True)
    salesman_id = fields.Many2one(
        'res.users', readonly=True)
    total = fields.Float(
        'Commission Amount',
        digits=dp.get_precision('Commission'), readonly=True)
    line_ids = fields.One2many(
        'commission.lines',
        'salespeople_id', 'Salespeople Commission Details')
    currency_id = fields.Many2one('res.currency', readonly=True)
    currency_amount = fields.Float(
        digits=dp.get_precision('Commission'), readonly=True)
    company_id = fields.Many2one(
        'res.company', readonly=True,
        help=('Currency at which this report will be \
                expressed. If not selected will be used the \
                one set in the company'))
