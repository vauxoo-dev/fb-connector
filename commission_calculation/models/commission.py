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
import datetime
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
    date = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    date = datetime.date(date.year, date.month, date.day)
    return date.strftime("%Y-%m-%d")


class CommissionPayment(models.Model):

    _name = 'commission.payment'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'commission.abstract']

    @api.onchange("template_id")
    def _onchange_commission_template(self):
        if self.template_id:
            self.commission_type = self.template_id.commission_type
            self.scope = self.template_id.scope
            self.policy_date_start = self.template_id.policy_date_start
            self.policy_date_end = self.template_id.policy_date_end
            self.salesman_policy = self.template_id.salesman_policy
            self.baremo_policy = self.template_id.baremo_policy
            self.baremo_id = self.template_id.baremo_id

    @api.model
    def _get_default_company(self):
        return self.env['res.users']._get_company()

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

    invoice_ids = fields.Many2many(
        'account.invoice', 'commission_account_invoice', 'commission_id',
        'invoice_id', 'Invoices', readonly=True,
        states={'draft': [('readonly', False)]})

    aml_ids = fields.Many2many(
        'account.move.line', 'commission_aml_rel', 'commission_id',
        'aml_id', 'Journal Items', copy=False, readonly=True)

    invoice_affected_ids = fields.One2many(
        'commission.invoice', 'commission_id', readonly=True,
        states={'write': [('readonly', False)]})

    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')],
        'State', readonly=True,
        default='draft', track_visibility='onchange',
        help="State of the commission document")

    template_id = fields.Many2one(
        'commission.template',
        readonly=True, states={'draft': [('readonly', False)]})

    company_id = fields.Many2one(
        'res.company', readonly=True, default=_get_default_company)

    currency_id = fields.Many2one(
        related='company_id.currency_id',
        store=True, readonly=True,
        help="Currency at which this report will be"
             "expressed. If not selected will be used the "
             "one set in the company")

    exchange_date = fields.Date(
        'Exchange Date',
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
        result = self.env.ref('commission_calculation.comm_line_fix_act').read()[0]
        # compute the number of payments to display
        cl_ids = []
        for cp_rec in self:
            cl_ids += [cl_rec.id for cs_rec in cp_rec.salesman_ids
                       if not cs_rec.salesman_id
                       for cl_rec in cs_rec.line_ids
                       ]
        # choose the view_mode accordingly
        cl_ids_len = len(cl_ids)
        if cl_ids_len > 0:
            result['domain'] = "[('id','in',[" + ','.join(
                [str(cl_id) for cl_id in cl_ids]
            ) + "])]"
        else:
            result['domain'] = "[('id','in',[])]"
        title = 'Fix commissions'
        result['name'] = title
        result['display_name'] = title
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
            'commission_calculation'
            '.action_account_moves_all_tree').read()[0]
        # compute the number of payments to display
        aml_ids = self.mapped('aml_ids.id')
        # choose the view_mode accordingly
        result['domain'] = "[('id','in',[])]"
        if len(aml_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % aml_ids
        return result

    @api.multi
    def action_view_invoice(self):
        """This function returns an action that display existing invoices of given
        commission payment ids. It can either be a in a list or in a form view,
        if there is only one invoice to show.
        """
        result = self.env.ref(
            'account.action_invoice_tree1').read()[0]
        # compute the number of invoices to display
        inv_ids = self.mapped('invoice_ids.id')
        # choose the view_mode accordingly
        result['domain'] = "[('id','in',[])]"
        if len(inv_ids) >= 1:
            result['domain'] = "[('id','in',%s)]" % inv_ids
        return result

    @api.multi
    def _prepare_based_on_payments(self):
        aml_obj = self.env['account.move.line']
        for comm_rec in self:
            date_start = comm_rec.date_start
            date_stop = comm_rec.date_stop
            # In this search we will restrict domain to those Entry Lines
            # coming from a Cash or Bank Journal within the given dates
            args = [('date', '>=', date_start),
                    ('date', '<=', date_stop),
                    ('journal_id.type', 'in', ('bank', 'cash')),
                    ('credit', '>', 0.0),
                    ('paid_comm', '=', False),
                    ]
            aml_ids = aml_obj.search(args)
            inv_ids = \
                aml_ids.mapped('matched_debit_ids.debit_move_id').filtered(
                    lambda a: a.journal_id.type == 'sale').mapped('invoice_id')
            comm_rec.write({
                'aml_ids': [(6, comm_rec.id, aml_ids._ids)],
                'invoice_ids': [(6, comm_rec.id, inv_ids._ids)],
            })
        return True

    @api.multi
    def _prepare_based_on_invoices(self):
        inv_obj = self.env['account.invoice']
        aml_obj = self.env['account.move.line']
        for comm_rec in self:
            comm_rec.write({'aml_ids': []})
            date_start = comm_rec.date_start
            date_stop = comm_rec.date_stop
            # En esta busqueda restringimos que la factura de cliente
            # se haya pagado
            invoice_ids = inv_obj.search([
                ('state', '=', 'paid'),
                ('type', '=', 'out_invoice'),
            ])
            # En esta busqueda restringimos que la factura de cliente
            # este dentro de la fecha estipulada, se hace de esta manera
            # porque date_last_payment es un campo calculado no almacenable
            # y no se permite usarlo dentro de un search, y si el campo
            # se hace almacenable entonces no se recalcula de forma correcta
            # /!\ NOTE: Let us make a TODO in order to allow us in the future
            # to make the date_last_payment a searchable field.
            invoice_ids_2 = []
            for current_invoice in invoice_ids:
                date_payment = current_invoice._date_last_payment()
                if date_payment and date_payment >= date_start and date_payment <= date_stop:
                    invoice_ids_2.append(current_invoice.id)
            comm_rec.write({
                'invoice_ids': [(6, comm_rec.id, invoice_ids_2)]})
            aml_ids = [aml_rec.id for inv_rec in comm_rec.invoice_ids
                       for aml_rec in inv_rec.payment_move_line_ids
                       if aml_rec.journal_id.type in ('bank', 'cash')
                       ]
            aml_ids2 = aml_obj.search([
                ('full_reconcile_id', '!=', False),
                ('journal_id.type', '=', 'sale'),
            ])
            # En esta busqueda restringimos que los aml
            # este dentro de la fecha estipulada, se hace de esta manera
            # porque date_last_payment es un campo calculado no almacenable
            # y no se permite usarlo dentro de un search, y si el campo
            # se hace almacenable entonces no se recalcula de forma correcta
            aml_ids_2 = []
            for current_aml in aml_ids2:
                date_payment = current_aml._date_last_payment()
                if date_payment and date_payment >= date_start and date_payment <= date_stop:
                    aml_ids_2.append(current_aml.id)
            aml_ids2 = aml_ids_2
            aml_ids2 = aml_obj.search([
                ('full_reconcile_id', '!=', False),
                ('journal_id.type', 'in', ('bank', 'cash')),
                ('rec_aml', 'in', aml_ids2)
            ])
            aml_ids2 = aml_ids2.mapped('id')
            aml_ids = list(set(aml_ids + aml_ids2))
            comm_rec.write({'aml_ids': [(6, comm_rec.id, aml_ids)]})
        return True

    @api.model
    def _compute_commission_rate(self, payment_date, invoice_date,
                                 dcto=0.0, baremo=None):
        commission = self
        # Determinar dias entre la emision de la factura del producto y el pago
        # del mismo
        payment_date = datetime.datetime.strptime(payment_date, '%Y-%m-%d')
        invoice_date = datetime.datetime.strptime(invoice_date, '%Y-%m-%d')
        emission_days = (payment_date - invoice_date).days

        # Teniendose dias y descuento por producto se procede a buscar en el
        # baremo el correspondiente valor de comision para el producto en
        # cuestion. se entra con el numero de dias

        # Esta busqueda devuelve los dias ordenadados de menor a mayor dia, de
        # acuerdo con lo estipulado que se ordenaria en el modulo baremo
        bar_day_ids = (baremo.bar_ids if baremo else
                       commission.baremo_id.bar_ids)

        no_days = True
        no_dcto = True
        # Se busca que el baremo tenga un rango que cubra a emision_days
        day_id = bar_day_ids.filtered(lambda day_number: emission_days <= day_number.number)[0]
        if day_id:
            bar_day = day_id.number
            no_days = False
            no_dcto = True
            # Se busca que el baremo tenga un rango para el valor de
            # descuento en producto
            for dcto_id in day_id.disc_ids.filtered(lambda disc: dcto <= disc.porc_disc):
                bardctdsc = dcto_id.porc_disc
                bar_dcto_comm = dcto_id.porc_com
                no_dcto = False

        if (not no_days) and no_dcto:
            bar_dcto_comm = 0.0
            bardctdsc = 0.0

        # Si emission_days no es cubierto por ningun rango del baremo diremos
        # entonces que la comision es cero (0) %
        elif no_days and no_dcto:
            # Diremos que los dias de baremo es menos uno (-1) cuando los dias
            # de emision no esten dentro del rango del baremo
            bar_day = '0.0'
            bardctdsc = 0.0
            bar_dcto_comm = 0.0

        res = dict(
            bar_day=bar_day,
            bar_dcto_comm=bar_dcto_comm,
            bardctdsc=bardctdsc,
            emission_days=emission_days)
        return res

    @api.model
    def _compute_commission_policy_start_date(self, pay_id):
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
    def _compute_commission_policy_end_date(self, pay_id):
        comm_rec = self
        aml_rec = pay_id
        date = aml_rec.date
        if comm_rec.policy_date_end == 'last_payment_date':
            date = aml_rec.matched_debit_ids.debit_move_id.filtered(
                lambda a: a.journal_id.type == 'sale').invoice_id.\
                date_last_payment or date
        return date

    @api.model
    def _compute_commission_saleman(self, salesman_rec):
        if not salesman_rec:
            return None
        comm_rec = self
        user_ids = [usr_rec.id for usr_rec in comm_rec.user_ids]
        if not user_ids:
            return salesman_rec
        if salesman_rec.id not in user_ids:
            return None
        return salesman_rec

    @api.model
    def _compute_salesman_policy(self, pay_id, salesman_id=None):
        if salesman_id:
            return salesman_id
        rp_obj = self.env['res.partner']
        comm_rec = self
        aml_rec = pay_id
        res = None
        if aml_rec.rec_invoice:
            if comm_rec.salesman_policy == 'on_invoice':
                res = aml_rec.rec_invoice.user_id
            elif comm_rec.salesman_policy == \
                    'on_invoiced_partner':
                res = aml_rec.rec_invoice.partner_id.user_id
            elif comm_rec.salesman_policy == \
                    'on_accounting_partner':
                res = rp_obj._find_accounting_partner(
                    aml_rec.rec_invoice.partner_id).user_id
        else:
            if comm_rec.salesman_policy in \
                    ('on_invoiced_partner', 'on_invoice'):
                res = aml_rec.rec_aml.partner_id.user_id
            elif comm_rec.salesman_policy == \
                    'on_accounting_partner':
                res = rp_obj._find_accounting_partner(
                    aml_rec.rec_aml.partner_id).user_id

        return res

    @api.model
    def _compute_commission_matrix_policy(self, product_id, salesman_id):
        bm_obj = self.env['baremo.matrix']

        domain = [('product_id', '=', product_id.id)]
        res = bm_obj.search(domain + [('user_id', '=', salesman_id.id)], limit=1)
        baremo = res if res else bm_obj.search(domain + [('user_id', '=', False)], limit=1)

        if baremo:
            return baremo.baremo_id

        return self.baremo_id

    @api.model
    def _compute_commission_policy_baremo(self, pay_id, partner_id=None,
                                          salesman_id=None):
        partner_id = partner_id or None
        rp_obj = self.env['res.partner']
        comm_rec = self
        aml_rec = pay_id
        res = None
        if comm_rec.baremo_policy == 'onCompany':
            partner_id = comm_rec.company_id.partner_id
        elif comm_rec.baremo_policy == 'onPartner':
            if aml_rec.rec_invoice:
                partner_id = partner_id or aml_rec.rec_invoice.partner_id
            else:
                partner_id = partner_id or aml_rec.rec_aml.partner_id
        elif comm_rec.baremo_policy == 'onAccountingPartner':
            if aml_rec.rec_invoice:
                partner_id = partner_id or aml_rec.rec_invoice.partner_id
            else:
                partner_id = partner_id or aml_rec.rec_aml.partner_id
            partner_id = rp_obj._find_accounting_partner(partner_id)
        elif comm_rec.baremo_policy == 'onUser':
            partner_id = self._compute_salesman_policy(
                pay_id, salesman_id=salesman_id).partner_id
        elif comm_rec.baremo_policy == 'onCommission':
            res = comm_rec.baremo_id
        # Fall back to baremo in Commission
        if partner_id:
            res = partner_id.baremo_id
        else:
            res = comm_rec.baremo_id
        return res

    def _compute_commission_payment_on_invoice_line(self, aml_rec):
        comm_rec = self

        prod_prices = self.env['product.historic.price']
        line_ids = self.env['commission.lines']

        if not aml_rec.credit:
            return True

        # Retrieve Partner's Salesman
        salesman = self._compute_salesman_policy(aml_rec)
        salesman_ok = self._compute_commission_saleman(salesman)

        if not salesman_ok and not (comm_rec.unknown_salespeople and not salesman):
            return True

        policy_date_start = \
            self._compute_commission_policy_start_date(aml_rec)

        policy_date_end = \
            self._compute_commission_policy_end_date(aml_rec)

        # Si esta aqui dentro es porque esta linea tiene una id valida
        # de una factura.
        inv_rec = aml_rec.rec_invoice
        baremo_policy = comm_rec.baremo_policy
        # /!\ NOTE: Retrieve here the fallback commission baremo policy
        if not baremo_policy == 'onMatrix':
            commission_policy_baremo = \
                self._compute_commission_policy_baremo(aml_rec)

        # Revision de cada linea de factura (productos)
        # Verificar si tiene producto asociado
        for inv_lin in inv_rec.invoice_line_ids.filtered(lambda line: line.product_id):

            # DETERMINAR EL PORCENTAJE DE IVA EN LA LINEA (perc_iva)
            # =============================================================
            # =============================================================
            # Determinar si la linea de la factura tiene un impuesto
            # (perc_iva). El impuesto aplicado a una linea es igual a la
            # suma de los impuestos se asume que todos los impuestos son
            # porcentuales
            perc_iva = (sum([tax.amount for tax in
                                inv_lin.invoice_line_tax_ids]) * 100
                        if inv_lin.invoice_line_tax_ids else 0.0)
            # Si esta aqui es porque hay un producto asociado
            prod_id = inv_lin.product_id.id

            # se obtienen las listas de precio, vienen ordenadas
            # por defecto, de acuerdo al objeto product.historic de
            # mayor a menor fecha
            price_ids = prod_prices.search(
                [('product_id', '=', prod_id)])
            # Buscar Precio Historico de Venta de este producto @
            # la fecha de facturacion
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
                list_date = comm_rec.date_start
                no_price = False

            if not no_price:
                # Determinar cuanto fue el
                # descuento en este producto en
                # aquel momento de la venta
                if abs((inv_lin.price_subtotal / inv_lin.quantity) -
                        inv_lin.price_unit) > 0.05:
                    # con esto se asegura que no se esta pasando
                    # por alto el descuento en linea
                    price_unit = round((inv_lin.price_subtotal /
                                        inv_lin.quantity), 2)
                else:
                    price_unit = inv_lin.price_unit
                dcto = 0.0
                if list_price:
                    dcto = round((list_price - price_unit) * 100 /
                                    list_price, 1)
                rate_item = dcto

                if baremo_policy == 'onMatrix':
                    commission_policy_baremo = \
                        self._compute_commission_matrix_policy(
                            inv_lin.product_id, salesman)

                # CHECK: If no commission policy is passed why it retrieves
                # values
                commission_params = comm_rec._compute_commission_rate(
                    policy_date_end,
                    policy_date_start, dcto=0.0,
                    baremo=commission_policy_baremo)

                bar_day = commission_params['bar_day']
                bar_dcto_comm = commission_params['bar_dcto_comm']
                bardctdsc = commission_params['bardctdsc']
                emission_days = commission_params['emission_days']

                #############################################
                # CALCULO DE COMISION POR LINEA DE PRODUCTO #
                #############################################

                penbxlinea = aml_rec.credit * (
                    inv_lin.price_subtotal /
                    inv_rec.amount_untaxed)
                fact_sup = 1 - 0.0 / 100 - 0.0 / 100
                fact_inf = 1 + (perc_iva / 100) * (1 - 0.0 / 100) - \
                    0.0 / 100 - 0.0 / 100

                comm_line = penbxlinea * fact_sup * (
                    bar_dcto_comm / 100) / fact_inf

                if aml_rec.currency_id and aml_rec.amount_currency:
                    payxlinea_curr = aml_rec.amount_currency * (
                        inv_lin.price_subtotal /
                        inv_rec.amount_untaxed)

                    currency_amount = (abs(payxlinea_curr) * fact_sup *
                                            (bar_dcto_comm / 100) /
                                            fact_inf)
                elif aml_rec.currency_id and not aml_rec.amount_currency:
                    return True
                else:
                    currency_amount = comm_line

                # Generar las lineas de comision por cada producto
                line_ids.create({
                    'commission_id': comm_rec.id,
                    'aml_id': aml_rec.id,
                    'am_rec': inv_rec.move_id.id,
                    'name':
                    aml_rec.move_id.name and
                    aml_rec.move_id.name or '/',
                    'payment_date': aml_rec.date,
                    'partner_id': inv_rec.partner_id.id,
                    'salesman_id': salesman and salesman.id,
                    'invoice_payment': aml_rec.credit,
                    'invoice_date': inv_rec.date_invoice,
                    'date_start': policy_date_start,
                    'date_stop': policy_date_end,
                    'days': emission_days,
                    'inv_subtotal': inv_rec.amount_untaxed,
                    'product_id': inv_lin.product_id.id,
                    'price_unit': price_unit,
                    'price_subtotal': inv_lin.price_subtotal,
                    'price_list': list_price,
                    'price_date': list_date,
                    'perc_iva': perc_iva,
                    'rate_item': rate_item,
                    'rate_number': bardctdsc,
                    'timespan': bar_day,
                    'baremo': bar_dcto_comm,
                    'commission_amount': comm_line,
                    'currency_amount': currency_amount,
                    'currency_id': inv_rec.currency_id and
                    inv_rec.currency_id.id or
                    inv_rec.company_id.currency_id.id,
                    'line_type': 'ok',
                    })

            else:
                # Se genera un lista de tuplas con las lineas,
                # productos y sus correspondientes fechas en las
                # cuales no aparece precio de lista, luego al final
                # se escriben los valores en la correspondiente
                # bitacora para su inspeccion. ~ #~ print 'No hubo
                # precio de lista para la fecha estipulada, hay que
                # generar el precio en este producto \n'
                line_ids.create({
                    'name': inv_lin.name,
                    'commission_id': comm_rec.id,
                    'product_id': inv_lin.product_id.id,
                    'payment_date': inv_rec.date_invoice,
                    'line_type': 'no_price',
                    })

        # cuando una linea no tiene product_id asociado se
        # escribe en una tabla para alertar al operador sobre
        # esta parte no llego a un acuerdo de si se podria
        # permitir al operador cambiar las lineas de la factura
        # puesto que es un asunto muy delicado.
        for inv_lin in inv_rec.invoice_line_ids.filtered(lambda line: not line.product_id):
            line_ids.create({
                'name': inv_lin.name,
                'commission_id': comm_rec.id,
                'line_type': 'no_product',
                'aml_id': aml_rec.id,
                })
        return True

    @api.model
    def _compute_commission_payment_on_invoice(self, aml):
        commission = self

        line_ids = self.env['commission.lines']

        if not aml.credit:
            return True

        # Retrieve Partner's Salesman
        salesman = self._compute_salesman_policy(aml)
        salesman_ok = self._compute_commission_saleman(salesman)

        if not salesman_ok:
            if not (commission.unknown_salespeople and not salesman):
                return True

        policy_date_start = \
            self._compute_commission_policy_start_date(aml)

        policy_date_end = \
            self._compute_commission_policy_end_date(aml)

        # Si esta aqui dentro es porque esta linea tiene una id valida
        # de una factura.
        invoice = aml.matched_debit_ids.debit_move_id.filtered(
            lambda a: a.journal_id.type == 'sale').invoice_id

        # DETERMINAR EL PORCENTAJE DE IVA EN LA FACTUR (perc_iva)
        # =======================================================
        # =======================================================
        perc_iva = (invoice.amount_total / invoice.amount_untaxed - 1) * 100

        commission_policy_baremo = \
            self._compute_commission_policy_baremo(aml)

        commission_params = commission._compute_commission_rate(
            policy_date_end,
            policy_date_start, dcto=0.0,
            baremo=commission_policy_baremo)

        bar_day = commission_params['bar_day']
        bar_dcto_comm = commission_params['bar_dcto_comm']
        bardctdsc = commission_params['bardctdsc']
        emission_days = commission_params['emission_days']

        ###################################
        # CALCULO DE COMISION POR FACTURA #
        ###################################

        penbxlinea = aml.credit
        fact_sup = 1 - 0.0 / 100 - 0.0 / 100
        fact_inf = 1 + (perc_iva / 100) * (1 - 0.0 / 100) - \
            0.0 / 100 - 0.0 / 100

        comm_line = penbxlinea * fact_sup * (
            bar_dcto_comm / 100) / fact_inf

        if aml.currency_id and aml.amount_currency:
            currency_amount = abs(aml.amount_currency) * fact_sup * (
                bar_dcto_comm / 100) / fact_inf
        elif aml.currency_id and not aml.amount_currency:
            return True
        else:
            currency_amount = comm_line

        # Generar las lineas de comision por cada factura
        line_ids.create({
            'commission_id': commission.id,
            'aml_id': aml.id,
            'am_rec': invoice.move_id.id,
            'name':
            aml.move_id.name and
            aml.move_id.name or '/',
            'payment_date': aml.date,
            'partner_id': invoice.partner_id.id,
            'salesman_id': salesman and salesman.id,
            'invoice_payment': aml.credit,
            'invoice_date': invoice.date_invoice,
            'date_start': policy_date_start,
            'date_stop': policy_date_end,
            'days': emission_days,
            'inv_subtotal': invoice.amount_untaxed,
            'perc_iva': perc_iva,
            'rate_number': bardctdsc,
            'timespan': bar_day,
            'baremo': bar_dcto_comm,
            'commission_amount': comm_line,
            'currency_amount': currency_amount,
            'currency_id': invoice.currency_id and
            invoice.currency_id.id or invoice.company_id.currency_id.id,
            'line_type': 'ok',
        })

        return True

    @api.model
    def _compute_commission_payment_on_aml(self, aml):
        commission = self

        if not commission.unknown_salespeople:
            return True

        line_ids = self.env['commission.lines']

        if not aml.credit:
            return True

        policy_date_start = \
            self._compute_commission_policy_start_date(aml)

        policy_date_end = \
            self._compute_commission_policy_end_date(aml)

        commission_policy_baremo = \
            self._compute_commission_policy_baremo(aml)

        commission_params = commission._compute_commission_rate(
            policy_date_end,
            policy_date_start, dcto=0.0,
            baremo=commission_policy_baremo)

        bar_day = commission_params['bar_day']
        bar_dcto_comm = commission_params['bar_dcto_comm']
        bardctdsc = commission_params['bardctdsc']
        emission_days = commission_params['emission_days']

        # Generar las lineas de comision por cada factura
        line_ids.create({
            'commission_id': commission.id,
            'aml_id': aml.id,
            'am_rec': aml.rec_aml.move_id.id,
            'name': aml.move_id.name and aml.move_id.name or '/',
            'payment_date': aml.date,
            'partner_id': aml.partner_id.id,
            'salesman_id': None,
            'invoice_payment': aml.credit,
            'invoice_date': aml.rec_aml.date,
            'date_start': policy_date_start,
            'date_stop': policy_date_end,
            'days': emission_days,
            'inv_subtotal': None,
            'perc_iva': None,
            'rate_number': bardctdsc,
            'timespan': bar_day,
            'baremo': bar_dcto_comm,
            'commission_amount': 0.0,
            'currency_amount': None,
            'currency_id': aml.currency_id and
            aml.currency_id.id or aml.company_id.currency_id.id,
            'line_type': 'ok',
            })

        return True

    @api.model
    def _compute_commission_payment(self, aml):
        commission = self
        if commission.scope == 'product_invoiced':
            self._compute_commission_payment_on_invoice_line(aml)
        elif commission.scope == 'whole_invoice':
            self._compute_commission_payment_on_invoice(aml)

        return True

    @api.multi
    def _commission_based_on_payments(self):
        for commission in self:

            payment_ids = self.env['account.move.line']
            uninvoice_payment_ids = self.env['account.move.line']
            # Read each Journal Entry Line
            for aml in commission.aml_ids.filtered(
                    lambda a: not a.paid_comm):

                # Verificar si esta linea tiene factura
                if not aml.matched_debit_ids.debit_move_id.filtered(
                        lambda a: a.journal_id.type == 'sale').invoice_id:
                    # TODO: Here we have to deal with the lines that comes from
                    # another system
                    uninvoice_payment_ids |= aml
                    continue

                payment_ids |= aml

            for pay_id in payment_ids:
                # se procede con la preparacion de las comisiones.
                commission._compute_commission_payment(pay_id)

            for aml_id in uninvoice_payment_ids:
                # se procede con la preparacion de las comisiones.
                commission._compute_commission_payment_on_aml(aml_id)

        return True

    @api.multi
    def _post_processing(self):
        salesman_ids = self.env['commission.salesman']
        comm_line_obj = self.env['commission.lines']
        invoice_affected_ids = self.env['commission.invoice']

        # se procede a agrupar las comisiones por
        # vendedor para mayor facilidad de uso

        cl_fields = ['id', 'salesman_id', 'currency_id', 'commission_amount',
                     'currency_amount', 'invoice_id', 'salespeople_id']

        for commission in self:
            # Erasing what was previously set as Commission per Salesman
            commission.salesman_ids.unlink()
            commission.invoice_affected_ids.unlink()

            # recoge todos los vendedores y suma el total de sus comisiones
            sale_comm = {}
            # ordena en un arbol todas las lineas de comisiones de producto
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

            sale_comm = sale_comm_data.get('commission_amount')
            sale_comm_curr = sale_comm_data.get('currency_amount')
            for key, value in sale_comm.items():
                salesman_id, currency_id = key
                vendor_id = salesman_ids.create({
                    'commission_id': commission.id,
                    'salesman_id': salesman_id,
                    'currency_id': currency_id,
                    'total': value,
                    'currency_amount': sale_comm_curr[key],
                })
                # transform from numpy.int64 to int
                commline_ids = [int(item) for item in sale_comm_cl[key].tolist()]
                comm_line_reg = comm_line_obj.browse(commline_ids)
                comm_line_reg.write({'salespeople_id': vendor_id.id})
            commission.write({
                'total': cl_data.sum().get('commission_amount'),
                'comm_fix': not all(
                    cl_data.groupby('salesman_id').groups.keys()),
            })
            commission.line_ids.filtered(
                lambda comm: not comm.salesman_id and not comm.line_type).write(
                    {'line_type': 'exception'})

            cl_ids = commission.line_ids.read(cl_fields, load=None)
            cl_data = DataFrame(cl_ids).set_index('id')
            vc_group = cl_data.groupby([
                                        'invoice_id']).groups

            for key, values in vc_group.items():
                invoice_id = int(key)
                invoice_id = invoice_affected_ids.create({
                    'commission_id': commission.id,
                    'invoice_id': invoice_id})
                commline_ids = [int(item) for item in values.tolist()]
                comm_line_reg = comm_line_obj.browse(commline_ids)
                comm_line_reg.write({'invoice_commission_id': invoice_id.id})

        return True

    @api.multi
    def prepare(self):
        """Este metodo recorre los elementos de lineas de asiento y verifica al
        menos tres (3) caracteristicas primordiales para continuar con los
        mismos: estas caracteristicas son:
        - journal_id.type in ('cash', 'bank'): quiere decir que la linea es de
        un deposito bancario (aqui aun no se ha considerado el trato que se le
        da a los cheques devueltos).
        - state == 'valid' : quiere decir que la linea ya se ha contabilizado y
        que esta cuadrado el asiento, condicion necesaria pero no suficiente.
        - paid_comm: que la linea aun no se ha considerado para una comision.

        Si estas tres (3) condiciones se cumplen entonces se puede proceder a
        realizar la revision de las lineas de pago.


        @param cr: cursor to database
        @param uid: id of current user
        @param ids: list of record ids to be process
        @param context: context arguments, like lang, time zone

        @return: return a result
        """
        if self.baremo_policy == 'onMatrix' and \
                self.scope != 'product_invoiced':
            raise UserError(
                _('Baremo on Matrix only applies on Invoiced Products'))
        # Desvincular lineas existentes, si las hubiere
        self.clear()
        if self.commission_type == 'partial_payment':
            self._prepare_based_on_payments()
        elif self.commission_type == 'fully_paid_invoice':
            self._prepare_based_on_invoices()

        self._commission_based_on_payments()
        self._post_processing()

        self.write({'state': 'open'})
        return True

    @api.model
    def _recompute_commission(self):
        for commission in self:
            for commission in commission.salesman_ids:
                if commission.salesman_id:
                    continue
                for commission_line in commission.line_ids:
                    commission_line._recompute_commission()
        return True

    @api.model
    def action_recompute(self):

        self._recompute_commission()
        self._post_processing()
        return True

    def action_draft(self):
        self.clear()
        self.write({'state': 'draft', 'total': 0.0})
        self.aml_ids.write({'paid_comm': False})
        return True

    def clear(self):
        """Deletes all associated record from Commission Payment
        """
        for commission in self:
            commission.line_ids.unlink()
            commission.salesman_ids.unlink()
            commission.invoice_affected_ids.unlink()
            commission.write(
                {'aml_ids': [(3, aml.id) for aml in commission.aml_ids],
                 'invoice_ids': [
                     (3, invoice.id) for invoice in commission.invoice_ids]})

    @api.multi
    def validate(self):
        """When validate we mark explicitly the payments related to this
        commission as paid_comm.
        :return:
        """
        self.ensure_one()
        payments = self.aml_ids.filtered('paid_comm')
        if not payments and not self.comm_fix:
            self.aml_ids.write({'paid_comm': True})
            self.write({'state': 'done'})
            return True
        message = _('Please check these payments that were paid before '
                    'this validation, you will not be able to validate '
                    'this commission:') + '<br/>' + \
            '<br/>'.join(payments.mapped('name'))
        self.message_post(subject='Not validated commissions. Wrong payments',
                          body=message)
        return True


class CommissionLines(models.Model):

    _name = 'commission.lines'
    _order = 'payment_date'

    @api.model
    def create(self, values):
        result = super(CommissionLines, self).create(values)
        result.write({
            'invoice_id': result.aml_id.rec_invoice.id,
        })
        return result

    @api.model
    def write(self, values):
        result = super(CommissionLines, self).write(values)
        if 'aml_id' in values:
            aml_id = values.get('aml_id')
            self.invoice_id = self.env['account.move.line'].browse(aml_id).rec_invoice.id
        return result

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
    commission_amount = fields.Float(
        digits=dp.get_precision('Commission'),
        help="Amount on the company currency")
    currency_amount = fields.Float(
        digits=dp.get_precision('Commission'),
        help="Amount on the currency of the payment itself")
    currency_id = fields.Many2one('res.currency')

    invoice_commission_id = fields.Many2one('commission.invoice')
    line_type = fields.Selection(
        [('no_product', 'W/o Product'), ('no_price', 'W/o Price'),
         ('exception', 'Exception'), ('ok', 'Ok')], default='ok')

    @api.multi
    def _recompute_commission(self):
        for commission_line in self:
            commission = commission_line.commission_id

            aml = commission_line.aml_id
            if not aml.credit:
                return True

            policy_date_start = \
                commission._compute_commission_policy_start_date(aml)

            policy_date_end = \
                commission._compute_commission_policy_end_date(aml)

            commission_policy_baremo = \
                commission._compute_commission_policy_baremo(
                    aml, partner_id=commission_line.partner_id,
                    salesman_id=commission_line.salesman_id)

            commission_params = commission._compute_commission_rate(
                policy_date_end,
                policy_date_start, dcto=0.0,
                baremo=commission_policy_baremo)

            bar_day = commission_params['bar_day']
            bar_dcto_comm = commission_params['bar_dcto_comm']
            bardctdsc = commission_params['bardctdsc']
            emission_days = commission_params['emission_days']

            ###############################
            # CALCULO DE COMISION POR AML #
            ###############################

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
            commission_line.write({
                'payment_date': aml.date,
                'invoice_payment': aml.credit,
                'invoice_date': aml.rec_aml.date,
                'date_start': policy_date_start,
                'date_stop': policy_date_end,
                'days': emission_days,
                'inv_subtotal': (aml.rec_aml.debit / (1 + perc_iva / 100)),
                'perc_iva': perc_iva,
                'rate_number': bardctdsc,
                'timespan': bar_day,
                'baremo': bar_dcto_comm,
                'commission_amount': comm_line,
                'currency_amount': currency_amount,
                'currency_id': aml.currency_id and
                aml.currency_id.id or
                aml.company_id.currency_id.id,
            })
        return True


class CommissionSalesman(models.Model):

    _name = 'commission.salesman'
    _rec_name = 'salesman_id'

    @api.model
    def create(self, values):
        result = super(CommissionSalesman, self).create(values)
        result.write({
            'company_id': result.commission_id.company_id.id,
        })
        return result

    @api.model
    def write(self, values):
        result = super(CommissionSalesman, self).write(values)
        if 'commission_id' in values:
            commission_id = values.get('commission_id')
            self.company_id = self.env['commission.payment'].browse(commission_id).company_id.id
        return result

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


class CommissionInvoice(models.Model):

    _name = 'commission.invoice'
    _order = 'invoice_id'

    @api.multi
    def _compute_commission(self):
        for commission in self:
            commission.commission = sum(
                [commission_line.commission_amount for commission_line in commission.line_ids])

    name = fields.Char('Comment')
    commission_id = fields.Many2one('commission.payment')
    invoice_id = fields.Many2one('account.invoice')
    line_ids = fields.One2many(
        'commission.lines',
        'invoice_commission_id', 'Commission by products')
    invoice_payment = fields.Float(
        digits=dp.get_precision('Commission'))
    commission_amount = fields.Float(
        compute='_compute_commission',
        digits=dp.get_precision('Commission'))
