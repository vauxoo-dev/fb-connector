# coding: utf-8

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

COMMISSION_STATES = [
    ('draft', 'Draft'),
    ('open', 'In Progress'),
    ('done', 'Done'),
    ('cancel', 'Cancelled'),
]

COMMISSION_TYPES = [
    ('partial_payment', 'Partial Payments'),
    ('fully_paid_invoice', 'Fully Paid Invoices'),
]

COMMISSION_SALESMAN_POLICY = [
    ('on_invoice', 'Invoice'),
    ('on_invoiced_partner', 'Partner'),
    ('on_accounting_partner', 'Commercial Entity'),
]

COMMISSION_SCOPES = [
    ('whole_invoice', 'Whole Invoice'),
    ('product_invoiced', 'Invoiced Products '),
]

COMMISSION_POLICY_DATE_START = [
    ('invoice_emission_date', 'Emission Date'),
    ('invoice_due_date', 'Due Date'),
]

COMMISSION_POLICY_DATE_END = [
    ('last_payment_date', 'Last Payment on Invoice'),
    ('date_on_payment', 'Date of Payment'),
]

COMMISSION_POLICY_BAREMO = [
    ('onCompany', 'Company'),
    ('onPartner', 'Partner'),
    ('onAccountingPartner', 'Commercial Entity'),
    ('onUser', 'Salespeople'),
    ('onMatrix', 'Baremo Matrix'),
    ('onCommission', 'Document'),
]


def t_time(date):
    """Trims time from "%Y-%m-%d %H:%M:%S" to "%Y-%m-%d"
    """
    date = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    date = datetime.date(date.year, date.month, date.day)
    return date.strftime("%Y-%m-%d")


class CommissionPayment(models.Model):

    """OpenERP Model : commission_payment
    """

    _name = 'commission.payment'
    _inherit = ['mail.thread']
    _description = __doc__

    @api.model
    def _get_default_company(self):
        company_id = self.env['res.users']._get_company()
        if not company_id:
            raise UserError(
                _('There is no default company for the current user!'))
        return company_id

    name = fields.Char(
        'Commission Concept', size=256, required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        help="Commission's description",
    )
    baremo_id = fields.Many2one(
        'baremo.book', 'Baremo', required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='onchange',
    )
    date_start = fields.Date(
        'Start Date', required=True,
        track_visibility='onchange',
        help="The calculation of commissions begins "
        "with this date, including it."
        "Invoices and journal entry in the "
        "date range will be taken into"
        "account in the calculation of "
        "commissions. Start Date <= date <= End Date"
    )
    date_stop = fields.Date(
        'End Date', required=True,
        track_visibility='onchange',
        help="The calculation of commissions ends "
        "with this date, including it."
        "Invoices and journal entry in the "
        "date range will be taken into"
        "account in the calculation of "
        "commissions. Start Date <= date <= End Date"
    )
    total_comm = fields.Float(
        'Total Commission',
        default=0.0,
        digits=dp.get_precision('Commission'),
        readonly=True, states={'write': [('readonly', False)]},
        track_visibility='onchange',
        help="Total commission to paid."
    )

    sale_noids = fields.One2many(
        'commission.sale.noid', 'commission_id',
        'Articulos sin asociacion', readonly=True,
        states={'write': [('readonly', False)]})

    noprice_ids = fields.One2many(
        'commission.noprice', 'commission_id',
        'Productos sin precio de lista historico', readonly=True,
        states={'write': [('readonly', False)]})

    comm_line_product_ids = fields.One2many(
        'commission.lines', 'commission_id',
        'Commission per products', readonly=True,
        domain=[('product_id', '!=', False)],
        states={'write': [('readonly', False)]})

    comm_line_invoice_ids = fields.One2many(
        'commission.lines', 'commission_id',
        'Commission per invoices', readonly=True,
        domain=[('product_id', '=', False)],
        states={'write': [('readonly', False)]})

    comm_line_ids = fields.One2many(
        'commission.lines', 'commission_id',
        'Comision por productos', readonly=True,
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
        'aml_id', 'Journal Items', readonly=True,
    )

    comm_voucher_ids = fields.One2many(
        'commission.voucher',
        'commission_id', 'Vouchers afectados en esta comision',
        readonly=True, states={'write': [('readonly', False)]})

    comm_invoice_ids = fields.One2many(
        'commission.invoice',
        'commission_id', 'Facturas afectadas en esta comision',
        readonly=True, states={'write': [('readonly', False)]})

    state = fields.Selection(
        COMMISSION_STATES, 'Estado', readonly=True,
        default='draft',
        track_visibility='onchange',
        help="State of the commission document",
    )

    commission_type = fields.Selection(
        COMMISSION_TYPES,
        string='Basis', required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        help="* Fully Paid Invoices: Sales commissions will be paid when the "
        "invoice is fully paid.\n"
        "* Partial Payments: Sales commissions will "
        "be partially paid, for each"
        " payment made to the invoice, a commission "
        "is calculated.",
    )

    commission_scope = fields.Selection(
        COMMISSION_SCOPES,
        string='Scope', required=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        help="* Full invoice: Commission payment based on invoice. "
        "The commission is calculated on the subtotal of the invoice, "
        "not including taxes. \n"
        "* Products invoiced: Payment of commission based on the "
        "products. The commission is calculated on each line of the "
        "invoice, not including taxes. You must specify by product "
        "how much commission will be paid. \n"
        "Note: Commissions are paid without taxes."
    )

    commission_policy_date_start = fields.Selection(
        COMMISSION_POLICY_DATE_START,
        string='Start Date Computation Policy', required=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        help="* Date of emission: The commission payment calculation begins "
        "on the date of emission of the invoice. That is, from the date of "
        "emission of the invoice, begins the count of days to know what "
        "percentage of commission will be the vendor. \n"
        "* Due date: The commission payment calculation starts on "
        "the invoice due date. That is, from the date of expiration "
        "of the invoice, begins the count of days to know what percentage"
        " of commission will be the vendor. \n"
        " Example:\n"
        "- If the customer pays in 0 days or less, "
        "you will get 7% commission. \n"
        "- If the customer pays in 20 days or less, "
        "you will get 5% commission. \n"
        "- Date of emission: July 13, 2017. \n"
        "- Date of last payment: July 26, 2017. \n"
        "- Due date: August 12, 2017. \n"
        "If the commission payment calculation is chosen as of "
        "the emission Date, the vendor will receive a 5% commission, since "
        "the payment date was 13 days AFTER the date of emission. That "
        "is, paid before 20 days. \n"
        "If the commission payment calculation is chosen from "
        "the Due Date, the vendor will get a 7% commission, since the "
        "payment date was 24 days BEFORE the expiration date. That is,"
        " paid before 20 days. \n"
    )

    commission_policy_date_end = fields.Selection(
        COMMISSION_POLICY_DATE_END,
        string='End Date Computation Policy', required=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        help="* Last payment on invoice: The commission will be "
        "calculated based on the date of the last payment "
        "(ie the date on which the invoice is paid in full). "
        "That is, although there are payments in the invoice "
        "that were made in a range where the vendor would earn "
        "a 7% commission, it will only be taken into account "
        "the last payment date for all payments, and if the "
        "last payment is in a commission rate of 1%, then the "
        "commission for all payments will be based on 1%. "
        "That is, the worst commission is used and this "
        "forces the vendors to convince the customer to "
        "pay the bill in full as quickly as possible.\n"
        "* Payment date: The commission will be calculated based "
        "on the date of each payment. If there are payments in "
        "different commission ranges, for example, payment #1 "
        "has 7% commission, payment #2 has %5 commission and "
        "payment #3 has 1% commission. Then you would pay "
        "commission which corresponds to the percentage of "
        "the amount of the payment."
    )

    commission_salesman_policy = fields.Selection(
        COMMISSION_SALESMAN_POLICY,
        string='Salesman Policy', required=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        help="* Invoice: The one on the invoice. The one that serves "
        "the person.\n"
        "* Partner: In the invoice partner tab or in the account "
        "move line. Partner assigned to the entity to which I am "
        "invoicing. That is, each customer has their assigned "
        "salesperson.\n"
        "* Commercial entity: The parent of the partner on the "
        "invoice. The customer handles the whole group. Serves "
        "if you have a group of vendors."
    )

    commission_baremo_policy = fields.Selection(
        COMMISSION_POLICY_BAREMO,
        string='Baremo Policy', required=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
        track_visibility='onchange',
        help="- Company: use the baremo configured in the company.\n"
        "- Partner: Use the baremo by partner, ie the baremo "
        "configured for the partner \n"
        "- Business entity: Use the partner's parent baremo. "
        "That is the baremo configured for a group of clients.\n"
        "- Vendor: Use the baremo set up for the seller.\n"
        "- Baremo matrix: Use the baremo specified. When it comes "
        "to paying commissions on product lines.\n"
        "- Document: Select a baremo by hand for everything\n"
    )

    company_id = fields.Many2one(
        'res.company', 'Company',
        readonly=True, default=_get_default_company)

    currency_id = fields.Many2one(
        related='company_id.currency_id',
        store=True, string='Currency', readonly=True,
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
        'Allow Unknown Salespeople?')

    @api.multi
    def action_view_fixlines(self):
        """This function returns an action that display existing Commissions of
        given commission payment ids that are required for some details to
        provide a proper computation of commissions.
        """
        result = self.env.ref(
            'commission_calculation'
            '.comm_line_fix_act').read()[0]
        # compute the number of payments to display
        cl_ids = []
        for cp_brw in self:
            cl_ids += [cl_brw.id for cs_brw in cp_brw.salesman_ids
                       if not cs_brw.salesman_id
                       for cl_brw in cs_brw.comm_lines_ids
                       ]
        # choose the view_mode accordingly
        cl_ids_len = len(cl_ids)
        if cl_ids_len > 0:
            result['domain'] = "[('id','in',[" + ','.join(
                [str(cl_id) for cl_id in cl_ids]
            ) + "])]"
        else:
            result['domain'] = "[('id','in',[])]"
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

        for comm_brw in self:
            date_start = comm_brw.date_start
            date_stop = comm_brw.date_stop

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
            comm_brw.write({
                'aml_ids': [(6, comm_brw.id, aml_ids._ids)],
                'invoice_ids': [(6, comm_brw.id, inv_ids._ids)],
            })

        return True

    @api.multi
    def _prepare_based_on_invoices(self):
        inv_obj = self.env['account.invoice']
        aml_obj = self.env['account.move.line']

        for comm_brw in self:
            comm_brw.write({'aml_ids': []})
            date_start = comm_brw.date_start
            date_stop = comm_brw.date_stop

            # En esta busqueda restringimos que la factura de cliente se haya
            # pagado y que  este dentro de la fecha estipulada
            invoice_ids = inv_obj.search([
                ('state', '=', 'paid'),
                ('type', '=', 'out_invoice'),
                # ('date_last_payment', '>=', date_start),
                # ('date_last_payment', '<=', date_stop)
            ])
            invoice_ids_2 = []
            for current_invoice in invoice_ids:
                date_payment = current_invoice._date_last_payment()
                if date_payment >= date_start and date_payment <= date_stop:
                    invoice_ids_2.append(current_invoice.id)

            comm_brw.write({
                'invoice_ids': [(6, comm_brw.id, invoice_ids_2)]})
            aml_ids = [aml_brw.id for inv_brw in comm_brw.invoice_ids
                       for aml_brw in inv_brw.payment_move_line_ids
                       if aml_brw.journal_id.type in ('bank', 'cash')
                       ]

            aml_ids2 = aml_obj.search([
                ('full_reconcile_id', '!=', False),
                ('journal_id.type', '=', 'sale'),
                # ('date_last_payment', '>=', date_start),
                # ('date_last_payment', '<=', date_stop)
            ])
            aml_ids_2 = []
            for current_aml in aml_ids2:
                date_payment = current_aml._date_last_payment()
                if date_payment >= date_start and date_payment <= date_stop:
                    aml_ids_2.append(current_aml.id)

            aml_ids2 = aml_ids_2
            aml_ids2 = aml_obj.search([
                ('full_reconcile_id', '!=', False),
                ('journal_id.type', 'in', ('bank', 'cash')),
                ('rec_aml', 'in', aml_ids2)
            ])
            aml_ids2 = aml_ids2.mapped('id')

            aml_ids = list(set(aml_ids + aml_ids2))
            comm_brw.write({'aml_ids': [(6, comm_brw.id, aml_ids)]})

        return True

    @api.model
    def _compute_commission_rate(self, pay_date, inv_date,
                                 dcto=0.0, bar_brw=None):
        comm_brw = self
        # Determinar dias entre la emision de la factura del producto y el pago
        # del mismo
        pay_date = datetime.datetime.strptime(pay_date, '%Y-%m-%d')
        inv_date = datetime.datetime.strptime(inv_date, '%Y-%m-%d')
        emission_days = (pay_date - inv_date).days

        # Teniendose dias y descuento por producto se procede a buscar en el
        # baremo el correspondiente valor de comision para el producto en
        # cuestion. se entra con el numero de dias

        # Esta busqueda devuelve los dias ordenadados de menor a mayor dia, de
        # acuerdo con lo estipulado que se ordenaria en el modulo baremo
        bar_day_ids = (bar_brw.bar_ids if bar_brw else
                       comm_brw.baremo_id.bar_ids)

        no_days = True
        no_dcto = True
        for day_id in bar_day_ids:
            # Se busca que el baremo tenga un rango que cubra a emision_days
            if emission_days <= day_id.number:
                bar_day = day_id.number
                no_days = False
                no_dcto = True
                for dcto_id in day_id.disc_ids:
                    # Se busca que el baremo tenga un rango para el valor de
                    # descuento en producto
                    if dcto <= dcto_id.porc_disc:
                        bardctdsc = dcto_id.porc_disc
                        bar_dcto_comm = dcto_id.porc_com
                        no_dcto = False
                        break
                break

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
            emission_days=emission_days,
        )
        return res

    @api.model
    def _compute_commission_policy_start_date(self, pay_id):
        comm_brw = self
        aml_brw = pay_id.matched_debit_ids.debit_move_id.filtered(
            lambda a: a.journal_id.type == 'sale')
        if not aml_brw:
            return False
        if comm_brw.commission_policy_date_start == 'invoice_emission_date':
            date_field = 'date'
        elif comm_brw.commission_policy_date_start == 'invoice_due_date':
            date_field = 'date_maturity'
        return min(l[date_field] for l in aml_brw)

    @api.model
    def _compute_commission_policy_end_date(self, pay_id):
        comm_brw = self
        aml_brw = pay_id
        date = aml_brw.date
        if comm_brw.commission_policy_date_end == 'last_payment_date':
            date = aml_brw.matched_debit_ids.debit_move_id.filtered(
                lambda a: a.journal_id.type == 'sale').invoice_id.\
                date_last_payment or date
        return date

    @api.model
    def _compute_commission_saleman(self, salesman_brw):
        if not salesman_brw:
            return None
        comm_brw = self
        user_ids = [usr_brw.id for usr_brw in comm_brw.user_ids]
        if not user_ids:
            return salesman_brw
        if salesman_brw.id not in user_ids:
            return None
        return salesman_brw

    @api.model
    def _compute_commission_salesman_policy(self, pay_id, salesman_id=None):
        if salesman_id:
            return salesman_id
        rp_obj = self.env['res.partner']
        comm_brw = self
        aml_brw = pay_id
        res = None
        if aml_brw.rec_invoice:
            if comm_brw.commission_salesman_policy == 'on_invoice':
                res = aml_brw.rec_invoice.user_id
            elif comm_brw.commission_salesman_policy == \
                    'on_invoiced_partner':
                res = aml_brw.rec_invoice.partner_id.user_id
            elif comm_brw.commission_salesman_policy == \
                    'on_accounting_partner':
                res = rp_obj._find_accounting_partner(
                    aml_brw.rec_invoice.partner_id).user_id
        else:
            if comm_brw.commission_salesman_policy in \
                    ('on_invoiced_partner', 'on_invoice'):
                res = aml_brw.rec_aml.partner_id.user_id
            elif comm_brw.commission_salesman_policy == \
                    'on_accounting_partner':
                res = rp_obj._find_accounting_partner(
                    aml_brw.rec_aml.partner_id).user_id

        return res

    @api.model
    def _compute_commission_matrix_policy(self, product_id, salesman_id):
        bm_obj = self.env['baremo.matrix']
        res = bm_obj.search([
            ('product_id', '=', product_id.id),
            ('user_id', '=', salesman_id.id),
        ], limit=1)
        if res:
            return res.baremo_id

        return self.baremo_id

    @api.model
    def _compute_commission_policy_baremo(self, pay_id, partner_id=None,
                                          salesman_id=None):
        partner_id = partner_id or None
        rp_obj = self.env['res.partner']
        comm_brw = self
        aml_brw = pay_id
        res = None
        if comm_brw.commission_baremo_policy == 'onCompany':
            partner_id = comm_brw.company_id.partner_id
        elif comm_brw.commission_baremo_policy == 'onPartner':
            if aml_brw.rec_invoice:
                partner_id = partner_id or aml_brw.rec_invoice.partner_id
            else:
                partner_id = partner_id or aml_brw.rec_aml.partner_id
        elif comm_brw.commission_baremo_policy == 'onAccountingPartner':
            if aml_brw.rec_invoice:
                partner_id = partner_id or aml_brw.rec_invoice.partner_id
            else:
                partner_id = partner_id or aml_brw.rec_aml.partner_id
            partner_id = rp_obj._find_accounting_partner(partner_id)
        elif comm_brw.commission_baremo_policy == 'onUser':
            partner_id = self._compute_commission_salesman_policy(
                pay_id, salesman_id=salesman_id).partner_id
        elif comm_brw.commission_baremo_policy == 'onCommission':
            res = comm_brw.baremo_id
        # Fall back to baremo in Commission
        if partner_id:
            res = partner_id.baremo_id
        else:
            res = comm_brw.baremo_id
        return res

    def _compute_commission_payment_on_invoice_line(self, pay_id):
        comm_brw = self

        prod_prices = self.env['product.historic.price']
        sale_noids = self.env['commission.sale.noid']
        noprice_ids = self.env['commission.noprice']
        comm_line_ids = self.env['commission.lines']

        aml_brw = pay_id
        if not aml_brw.credit:
            return True

        # Retrieve Partner's Salesman
        salesman = self._compute_commission_salesman_policy(aml_brw)
        salesman_ok = self._compute_commission_saleman(salesman)

        if not salesman_ok:
            if not (comm_brw.unknown_salespeople and not salesman):
                return True

        commission_policy_date_start = \
            self._compute_commission_policy_start_date(aml_brw)

        commission_policy_date_end = \
            self._compute_commission_policy_end_date(aml_brw)

        # Si esta aqui dentro es porque esta linea tiene una id valida
        # de una factura.
        inv_brw = aml_brw.rec_invoice
        commission_baremo_policy = comm_brw.commission_baremo_policy
        # /!\ NOTE: Retrieve here the fallback commission baremo policy
        if not commission_baremo_policy == 'onMatrix':
            commission_policy_baremo = \
                self._compute_commission_policy_baremo(aml_brw)

        # Revision de cada linea de factura (productos)
        for inv_lin in inv_brw.invoice_line_ids:

            # Verificar si tiene producto asociado
            if inv_lin.product_id:
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
                prod_id = inv_lin.product_id.product_tmpl_id.id
                # se obtienen las listas de precio, vienen ordenadas
                # por defecto, de acuerdo al objeto product.historic de
                # mayor a menor fecha
                price_ids = prod_prices.search(
                    [('product_id', '=', prod_id)])
                # Buscar Precio Historico de Venta de este producto @
                # la fecha de facturacion
                no_price = True

                for prod_prices_brw in price_ids:
                    if inv_brw.date_invoice >= t_time(prod_prices_brw.name):
                        list_price = prod_prices_brw.price
                        list_date = prod_prices_brw.name
                        no_price = False
                        break
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

                    if commission_baremo_policy == 'onMatrix':
                        commission_policy_baremo = \
                            self._compute_commission_matrix_policy(
                                inv_lin.product_id, salesman)

                    # CHECK: If no commission policy is passed why it retrieves
                    # values
                    commission_params = comm_brw._compute_commission_rate(
                        commission_policy_date_end,
                        commission_policy_date_start, dcto=0.0,
                        bar_brw=commission_policy_baremo)

                    bar_day = commission_params['bar_day']
                    bar_dcto_comm = commission_params['bar_dcto_comm']
                    bardctdsc = commission_params['bardctdsc']
                    emission_days = commission_params['emission_days']

                    #############################################
                    # CALCULO DE COMISION POR LINEA DE PRODUCTO #
                    #############################################

                    penbxlinea = aml_brw.credit * (
                        inv_lin.price_subtotal /
                        inv_brw.amount_untaxed)
                    fact_sup = 1 - 0.0 / 100 - 0.0 / 100
                    fact_inf = 1 + (perc_iva / 100) * (1 - 0.0 / 100) - \
                        0.0 / 100 - 0.0 / 100

                    comm_line = penbxlinea * fact_sup * (
                        bar_dcto_comm / 100) / fact_inf

                    if aml_brw.currency_id and aml_brw.amount_currency:
                        payxlinea_curr = aml_brw.amount_currency * (
                            inv_lin.price_subtotal /
                            inv_brw.amount_untaxed)

                        commission_currency = (abs(payxlinea_curr) * fact_sup *
                                               (bar_dcto_comm / 100) /
                                               fact_inf)
                    elif aml_brw.currency_id and not aml_brw.amount_currency:
                        return True
                    else:
                        commission_currency = comm_line

                    # Generar las lineas de comision por cada producto
                    comm_line_ids.create({
                        'commission_id': comm_brw.id,
                        'aml_id': aml_brw.id,
                        'am_rec': inv_brw.move_id.id,
                        'name':
                        aml_brw.move_id.name and
                        aml_brw.move_id.name or '/',
                        'pay_date': aml_brw.date,
                        'pay_off': aml_brw.credit,
                        'partner_id': inv_brw.partner_id.id,
                        'salesman_id': salesman and salesman.id,
                        'pay_inv': aml_brw.credit,
                        'inv_date': inv_brw.date_invoice,
                        'date_start': commission_policy_date_start,
                        'date_stop': commission_policy_date_end,
                        'days': emission_days,
                        'inv_subtotal': inv_brw.amount_untaxed,
                        'product_id': inv_lin.product_id.id,
                        'price_unit': price_unit,
                        'price_subtotal': inv_lin.price_subtotal,
                        'price_list': list_price,
                        'price_date': list_date,
                        'perc_iva': perc_iva,
                        'rate_item': rate_item,
                        'rate_number': bardctdsc,
                        'timespan': bar_day,
                        'baremo_comm': bar_dcto_comm,
                        'commission': comm_line,
                        'commission_currency': commission_currency,
                        'currency_id': inv_brw.currency_id and
                        inv_brw.currency_id.id or
                        inv_brw.company_id.currency_id.id,
                        })

                else:
                    # Se genera un lista de tuplas con las lineas,
                    # productos y sus correspondientes fechas en las
                    # cuales no aparece precio de lista, luego al final
                    # se escriben los valores en la correspondiente
                    # bitacora para su inspeccion. ~ #~ print 'No hubo
                    # precio de lista para la fecha estipulada, hay que
                    # generar el precio en este producto \n'
                    noprice_ids.create({'commission_id': comm_brw.id,
                                        'product_id': prod_id,
                                        'date': inv_brw.date_invoice,
                                        'invoice_num':
                                        inv_brw.number})
            else:
                # cuando una linea no tiene product_id asociado se
                # escribe en una tabla para alertar al operador sobre
                # esta parte no llego a un acuerdo de si se podria
                # permitir al operador cambiar las lineas de la factura
                # puesto que es un asunto muy delicado.
                sale_noids.create({'commission_id': comm_brw.id,
                                   'inv_line_id': inv_lin.id})
        return True

    @api.model
    def _compute_commission_payment_on_invoice(self, aml_brw):
        comm_brw = self

        comm_line_ids = self.env['commission.lines']

        if not aml_brw.credit:
            return True

        # Retrieve Partner's Salesman
        salesman = self._compute_commission_salesman_policy(aml_brw)
        salesman_ok = self._compute_commission_saleman(salesman)

        if not salesman_ok:
            if not (comm_brw.unknown_salespeople and not salesman):
                return True

        commission_policy_date_start = \
            self._compute_commission_policy_start_date(aml_brw)

        commission_policy_date_end = \
            self._compute_commission_policy_end_date(aml_brw)

        # Si esta aqui dentro es porque esta linea tiene una id valida
        # de una factura.
        inv_brw = aml_brw.matched_debit_ids.debit_move_id.filtered(
            lambda a: a.journal_id.type == 'sale').invoice_id

        # DETERMINAR EL PORCENTAJE DE IVA EN LA FACTUR (perc_iva)
        # =======================================================
        # =======================================================
        perc_iva = (inv_brw.amount_total / inv_brw.amount_untaxed - 1) * 100

        commission_policy_baremo = \
            self._compute_commission_policy_baremo(aml_brw)

        commission_params = comm_brw._compute_commission_rate(
            commission_policy_date_end,
            commission_policy_date_start, dcto=0.0,
            bar_brw=commission_policy_baremo)

        bar_day = commission_params['bar_day']
        bar_dcto_comm = commission_params['bar_dcto_comm']
        bardctdsc = commission_params['bardctdsc']
        emission_days = commission_params['emission_days']

        ###################################
        # CALCULO DE COMISION POR FACTURA #
        ###################################

        penbxlinea = aml_brw.credit
        fact_sup = 1 - 0.0 / 100 - 0.0 / 100
        fact_inf = 1 + (perc_iva / 100) * (1 - 0.0 / 100) - \
            0.0 / 100 - 0.0 / 100

        comm_line = penbxlinea * fact_sup * (
            bar_dcto_comm / 100) / fact_inf

        if aml_brw.currency_id and aml_brw.amount_currency:
            commission_currency = abs(aml_brw.amount_currency) * fact_sup * (
                bar_dcto_comm / 100) / fact_inf
        elif aml_brw.currency_id and not aml_brw.amount_currency:
            return True
        else:
            commission_currency = comm_line

        # Generar las lineas de comision por cada factura
        comm_line_ids.create({
            'commission_id': comm_brw.id,
            'aml_id': aml_brw.id,
            'am_rec': inv_brw.move_id.id,
            'name':
            aml_brw.move_id.name and
            aml_brw.move_id.name or '/',
            'pay_date': aml_brw.date,
            'pay_off': aml_brw.credit,
            'partner_id': inv_brw.partner_id.id,
            'salesman_id': salesman and salesman.id,
            'pay_inv': aml_brw.credit,
            'inv_date': inv_brw.date_invoice,
            'date_start': commission_policy_date_start,
            'date_stop': commission_policy_date_end,
            'days': emission_days,
            'inv_subtotal': inv_brw.amount_untaxed,
            'perc_iva': perc_iva,
            'rate_number': bardctdsc,
            'timespan': bar_day,
            'baremo_comm': bar_dcto_comm,
            'commission': comm_line,
            'commission_currency': commission_currency,
            'currency_id': inv_brw.currency_id and
            inv_brw.currency_id.id or inv_brw.company_id.currency_id.id,
        })

        return True

    @api.model
    def _compute_commission_payment_on_aml(self, aml_brw):
        comm_brw = self

        if not comm_brw.unknown_salespeople:
            return True

        comm_line_ids = self.env['commission.lines']

        if not aml_brw.credit:
            return True

        commission_policy_date_start = \
            self._compute_commission_policy_start_date(aml_brw)

        commission_policy_date_end = \
            self._compute_commission_policy_end_date(aml_brw)

        commission_policy_baremo = \
            self._compute_commission_policy_baremo(aml_brw)

        commission_params = comm_brw._compute_commission_rate(
            commission_policy_date_end,
            commission_policy_date_start, dcto=0.0,
            bar_brw=commission_policy_baremo)

        bar_day = commission_params['bar_day']
        bar_dcto_comm = commission_params['bar_dcto_comm']
        bardctdsc = commission_params['bardctdsc']
        emission_days = commission_params['emission_days']

        # Generar las lineas de comision por cada factura
        comm_line_ids.create({
            'commission_id': comm_brw.id,
            'aml_id': aml_brw.id,
            'am_rec': aml_brw.rec_aml.move_id.id,
            'name': aml_brw.move_id.name and aml_brw.move_id.name or '/',
            'pay_date': aml_brw.date,
            'pay_off': aml_brw.credit,
            'partner_id': aml_brw.partner_id.id,
            'salesman_id': None,
            'pay_inv': aml_brw.credit,
            'inv_date': aml_brw.rec_aml.date,
            'date_start': commission_policy_date_start,
            'date_stop': commission_policy_date_end,
            'days': emission_days,
            'inv_subtotal': None,
            'perc_iva': None,
            'rate_number': bardctdsc,
            'timespan': bar_day,
            'baremo_comm': bar_dcto_comm,
            'commission': 0.0,
            'commission_currency': None,
            'currency_id': aml_brw.currency_id and
            aml_brw.currency_id.id or aml_brw.company_id.currency_id.id,
            })

        return True

    @api.model
    def _compute_commission_payment(self, aml_brw):
        comm_brw = self
        if comm_brw.commission_scope == 'product_invoiced':
            self._compute_commission_payment_on_invoice_line(aml_brw)
        elif comm_brw.commission_scope == 'whole_invoice':
            self._compute_commission_payment_on_invoice(aml_brw)

        return True

    @api.multi
    def _commission_based_on_payments(self):
        for comm_brw in self:

            payment_ids = self.env['account.move.line']
            uninvoice_payment_ids = self.env['account.move.line']
            # Read each Journal Entry Line
            for aml_brw in comm_brw.aml_ids.filtered(
                    lambda a: not a.paid_comm):

                # Verificar si esta linea tiene factura
                if not aml_brw.matched_debit_ids.debit_move_id.filtered(
                        lambda a: a.journal_id.type == 'sale').invoice_id:
                    # TODO: Here we have to deal with the lines that comes from
                    # another system
                    uninvoice_payment_ids |= aml_brw
                    continue

                payment_ids |= aml_brw

            for pay_id in payment_ids:
                # se procede con la preparacion de las comisiones.
                comm_brw._compute_commission_payment(pay_id)

            for aml_id in uninvoice_payment_ids:
                # se procede con la preparacion de las comisiones.
                comm_brw._compute_commission_payment_on_aml(aml_id)

        return True

    @api.multi
    def _post_processing(self):
        salesman_ids = self.env['commission.salesman']
        comm_line_obj = self.env['commission.lines']
        comm_voucher_ids = self.env['commission.voucher']
        comm_invoice_ids = self.env['commission.invoice']

        # habiendo recorrido todos los vouchers, mostrado todos los elementos
        # que necesitan correccion se procede a agrupar las comisiones por
        # vendedor para mayor facilidad de uso

        cl_fields = ['id', 'salesman_id', 'currency_id', 'commission',
                     'commission_currency', 'am_id', 'invoice_id',
                     'comm_salespeople_id', 'comm_voucher_id']

        for commission in self:
            # Erasing what was previously set as Commission per Salesman
            commission.salesman_ids.unlink()
            commission.comm_invoice_ids.unlink()
            commission.comm_voucher_ids.unlink()

            # recoge todos los vendedores y suma el total de sus comisiones
            sale_comm = {}
            # ordena en un arbol todas las lineas de comisiones de producto
            cl_ids = commission.comm_line_ids.read(cl_fields, load=None)
            if not cl_ids:
                continue

            cl_data = DataFrame(cl_ids).set_index('id')
            cl_data_grouped = cl_data.groupby(['salesman_id', 'currency_id'])

            cl_data_agg = cl_data_grouped.sum()
            sale_comm_data = cl_data_agg.to_dict()
            sale_comm_cl = cl_data_grouped.groups

            sale_comm = sale_comm_data.get('commission')
            sale_comm_curr = sale_comm_data.get('commission_currency')
            for key, value in sale_comm.iteritems():
                salesman_id, currency_id = key
                vendor_id = salesman_ids.create({
                    'commission_id': commission.id,
                    'salesman_id': salesman_id,
                    'currency_id': currency_id,
                    'comm_total': value,
                    'comm_total_currency': sale_comm_curr[key],
                })
                comm_line_reg = comm_line_obj.browse(
                    sale_comm_cl[key].tolist())
                comm_line_reg.write({'comm_salespeople_id': vendor_id.id})
            commission.write({
                'total_comm': cl_data.sum().get('commission'),
                'comm_fix': not all(
                    cl_data.groupby('salesman_id').groups.keys()),
            })

            cl_ids = commission.comm_line_ids.read(cl_fields, load=None)
            cl_data = DataFrame(cl_ids).set_index('id')
            vc_group = cl_data.groupby(['comm_salespeople_id', 'am_id']).groups

            for key, values in vc_group.iteritems():
                comm_salespeople_id, am_id = key
                comm_voucher_id = comm_voucher_ids.create({
                    'commission_id': commission.id,
                    'comm_sale_id': comm_salespeople_id,
                    'am_id': am_id, })
                comm_line_reg = comm_line_obj.browse(values.tolist())
                comm_line_reg.write({'comm_voucher_id': comm_voucher_id.id})

            cl_ids = commission.comm_line_ids.read(cl_fields, load=None)
            cl_data = DataFrame(cl_ids).set_index('id')
            vc_group = cl_data.groupby(['comm_voucher_id',
                                        'invoice_id']).groups

            for key, values in vc_group.iteritems():
                comm_voucher_id, invoice_id = key
                comm_invoice_id = comm_invoice_ids.create({
                    'commission_id': commission.id,
                    'comm_voucher_id': comm_voucher_id,
                    'invoice_id': invoice_id})
                comm_line_reg = comm_line_obj.browse(values.tolist())
                comm_line_reg.write({'comm_invoice_id': comm_invoice_id.id})

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
        if self.commission_baremo_policy == 'onMatrix' and \
                self.commission_scope != 'product_invoiced':
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
        for comm_brw in self:
            for cs_brw in comm_brw.salesman_ids:
                if cs_brw.salesman_id:
                    continue
                for cl_brw in cs_brw.comm_lines_ids:
                    cl_brw._recompute_commission()
        return True

    @api.model
    def action_recompute(self):

        self._recompute_commission()
        self._post_processing()
        return True

    def action_draft(self):
        self.clear()
        self.write({'state': 'draft', 'total_comm': 0.0})
        return True

    def clear(self):
        """Deletes all associated record from Commission Payment
        """
        for comm_brw in self:
            comm_brw.sale_noids.unlink()
            comm_brw.noprice_ids.unlink()
            comm_brw.comm_line_ids.unlink()
            comm_brw.salesman_ids.unlink()
            comm_brw.comm_voucher_ids.unlink()
            comm_brw.comm_invoice_ids.unlink()
            comm_brw.write(
                {'aml_ids': [(3, aml_brw.id) for aml_brw in comm_brw.aml_ids],
                 'invoice_ids': [
                     (3, inv_brw.id) for inv_brw in comm_brw.invoice_ids]})

    @api.multi
    def validate(self):
        # escribir en el aml el estado buleano de paid_comm a True para indicar
        # que ya esta comision se esta pagando
        # TODO: prior to write anything here paid_comm field has to be check
        # first if any of the line has being paid arise a warning
        for comm_brw in self:
            if comm_brw.comm_fix:
                raise UserError(_('There are items to fix'))

        # TODO: write the real list of payments and invoices that were taken
        # into account
        self.write({'state': 'done', })
        return True


class CommissionSaleNoid(models.Model):

    """Commission Payment : commission_sale_noid
    """

    _name = 'commission.sale.noid'

    name = fields.Char('Comentario', size=256, default=None)
    commission_id = fields.Many2one('commission.payment', 'Comision')
    inv_line_id = fields.Many2one(
        'account.invoice.line', 'Descripcion de Articulo')


class CommissionNoprice(models.Model):

    """Commission Payment : commission_sale_noid
    """

    _name = 'commission.noprice'
    _order = 'product_id'

    name = fields.Char('Comentario', size=256, default=None)
    commission_id = fields.Many2one('commission.payment', 'Comision')
    product_id = fields.Many2one('product.product', 'Producto')
    date = fields.Date('Date')
    invoice_num = fields.Char('Invoice Number', size=256)


class CommissionLines(models.Model):

    """Commission Payment : commission_lines
    """

    _name = 'commission.lines'
    _order = 'pay_date'

    commission_id = fields.Many2one(
        'commission.payment', 'Commission Document', required=True)
    name = fields.Char('Transaccion', size=256, required=True)
    pay_date = fields.Date('Payment Date', required=True)
    pay_off = fields.Float(
        'Pago',
        digits=dp.get_precision('Commission'))

    aml_id = fields.Many2one('account.move.line', 'Entry Line')
    am_rec = fields.Many2one('account.move', 'Reconciling Entry')
    am_id = fields.Many2one(
        related='aml_id.move_id', store=True, readonly=True,
        string='Journal Entry')

    invoice_id = fields.Many2one(
        related='aml_id.rec_invoice', store=True, readonly=True,
        string='Reconciling Invoice')
    partner_id = fields.Many2one('res.partner', 'Partner')
    salesman_id = fields.Many2one('res.users', 'Salesman',
                                  required=False)
    comm_salespeople_id = fields.Many2one(
        'commission.salesman', 'Salespeople Commission', required=False)
    comm_voucher_id = fields.Many2one(
        'commission.voucher', 'Voucher Commission', required=False)
    pay_inv = fields.Float(
        'Pay. to Doc.',
        digits=dp.get_precision('Commission'))

    inv_date = fields.Date('Invoice Date')
    date_start = fields.Date(
        'Start Date', required=False, readonly=True,
    )
    date_stop = fields.Date(
        'End Date', required=False, readonly=True,
    )
    days = fields.Float(
        'Comm. Days',
        digits=dp.get_precision('Commission'))

    inv_subtotal = fields.Float(
        'SubTot. Doc.',
        digits=dp.get_precision('Commission'))

    product_id = fields.Many2one('product.product', 'Product')
    price_unit = fields.Float(
        'Prec. Unit.',
        digits=dp.get_precision('Commission'))
    price_subtotal = fields.Float(
        'SubTot. Product',
        digits=dp.get_precision('Commission'))

    price_list = fields.Float(
        'Price List',
        digits=dp.get_precision('Commission'))
    price_date = fields.Date('List Date')

    perc_iva = fields.Float(
        'Tax (%)',
        digits=dp.get_precision('Commission'))

    rate_item = fields.Float(
        'Dsct. (%)',
        digits=dp.get_precision('Commission'))

    rate_number = fields.Float(
        'B./Rate (%)',
        digits=dp.get_precision('Commission'))
    timespan = fields.Float(
        'B./Days',
        digits=dp.get_precision('Commission'))
    baremo_comm = fields.Float(
        'B./%Comm.',
        digits=dp.get_precision('Commission'))
    commission = fields.Float(
        'Commission Amount',
        digits=dp.get_precision('Commission'))
    commission_currency = fields.Float(
        'Currency Amount',
        digits=dp.get_precision('Commission'))
    currency_id = fields.Many2one('res.currency', 'Currency')

    @api.multi
    def _recompute_commission(self):
        for commission_line in self:
            comm_brw = commission_line.commission_id

            aml_brw = commission_line.aml_id
            if not aml_brw.credit:
                return True

            commission_policy_date_start = \
                comm_brw._compute_commission_policy_start_date(aml_brw)

            commission_policy_date_end = \
                comm_brw._compute_commission_policy_end_date(aml_brw)

            commission_policy_baremo = \
                comm_brw._compute_commission_policy_baremo(
                    aml_brw, partner_id=commission_line.partner_id,
                    salesman_id=commission_line.salesman_id)

            commission_params = comm_brw._compute_commission_rate(
                commission_policy_date_end,
                commission_policy_date_start, dcto=0.0,
                bar_brw=commission_policy_baremo)

            bar_day = commission_params['bar_day']
            bar_dcto_comm = commission_params['bar_dcto_comm']
            bardctdsc = commission_params['bardctdsc']
            emission_days = commission_params['emission_days']

            ###############################
            # CALCULO DE COMISION POR AML #
            ###############################

            # Right now I have not figure out a way to know how much was taxed
            perc_iva = comm_brw.company_id.comm_tax

            penbxlinea = aml_brw.credit
            fact_sup = 1 - 0.0 / 100 - 0.0 / 100
            fact_inf = 1 + (perc_iva / 100) * (1 - 0.0 / 100) - \
                0.0 / 100 - 0.0 / 100

            comm_line = penbxlinea * fact_sup * (
                bar_dcto_comm / 100) / fact_inf

            if aml_brw.currency_id and aml_brw.amount_currency:
                commission_currency = abs(aml_brw.amount_currency) * \
                    fact_sup * (bar_dcto_comm / 100) / fact_inf
            elif aml_brw.currency_id and not aml_brw.amount_currency:
                return True
            else:
                commission_currency = comm_line

            # Generar las lineas de comision por cada factura
            commission_line.write({
                'pay_date': aml_brw.date,
                'pay_off': aml_brw.credit,
                'pay_inv': aml_brw.credit,
                'inv_date': aml_brw.rec_aml.date,
                'date_start': commission_policy_date_start,
                'date_stop': commission_policy_date_end,
                'days': emission_days,
                'inv_subtotal': (aml_brw.rec_aml.debit / (1 + perc_iva / 100)),
                'perc_iva': perc_iva,
                'rate_number': bardctdsc,
                'timespan': bar_day,
                'baremo_comm': bar_dcto_comm,
                'commission': comm_line,
                'commission_currency': commission_currency,
                'currency_id': aml_brw.currency_id and
                aml_brw.currency_id.id or
                aml_brw.company_id.currency_id.id,
            })
        return True


class CommissionSalesman(models.Model):

    """Commission Payment : commission_salesman
    """

    _name = 'commission.salesman'
    _rec_name = 'salesman_id'

    commission_id = fields.Many2one(
        'commission.payment', 'Commission Document', readonly=True)
    salesman_id = fields.Many2one(
        'res.users', 'Salesman', required=False, readonly=True)
    comm_total = fields.Float(
        'Commission Amount',
        digits=dp.get_precision('Commission'), readonly=True)
    comm_voucher_ids = fields.One2many(
        'commission.voucher',
        'comm_sale_id', 'Vouchers Affected in this commission',
        required=False)
    comm_lines_ids = fields.One2many(
        'commission.lines',
        'comm_salespeople_id', 'Salespeople Commission Details',
        required=False)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)
    comm_total_currency = fields.Float(
        'Currency Amount',
        digits=dp.get_precision('Commission'), readonly=True)
    company_id = fields.Many2one(
        related='commission_id.company_id', store=True, readonly=True,
        string='Company',
        help=('Currency at which this report will be \
                expressed. If not selected will be used the \
                one set in the company'))


class CommissionVoucher(models.Model):

    """Commission Payment : commission_voucher
    """

    _name = 'commission.voucher'
    _order = 'date'
    _rec_name = 'am_id'

    @api.multi
    def _compute_commission(self):
        for brw in self:
            brw.commission = sum(
                [ci_brw.commission for ci_brw in brw.comm_invoice_ids])

    commission_id = fields.Many2one('commission.payment', 'Commission')
    comm_sale_id = fields.Many2one('commission.salesman', 'Salesman')
    am_id = fields.Many2one('account.move', 'Journal Entry')
    comm_invoice_ids = fields.One2many(
        'commission.invoice',
        'comm_voucher_id', 'Facturas afectadas en esta comision',
        required=False)
    date = fields.Date(
        related='am_id.date', store=True, readonly=True, string='Date')
    commission = fields.Float(
        compute='_compute_commission',
        string='Commission Amount',
        digits=dp.get_precision('Commission'))


class CommissionInvoice(models.Model):

    """Commission Payment : commission_invoice
    """

    _name = 'commission.invoice'
    _order = 'invoice_id'

    @api.multi
    def _compute_commission(self):
        for brw in self:
            brw.commission = sum(
                [cl_brw.commission for cl_brw in brw.comm_line_ids])

    name = fields.Char('Comentario', size=256)
    commission_id = fields.Many2one('commission.payment', 'Comision')
    comm_voucher_id = fields.Many2one('commission.voucher', 'Voucher')
    invoice_id = fields.Many2one('account.invoice', 'Factura')
    comm_line_ids = fields.One2many(
        'commission.lines',
        'comm_invoice_id', 'Comision por productos', required=False)
    pay_inv = fields.Float(
        'Abono Fact.',
        digits=dp.get_precision('Commission'))
    commission = fields.Float(
        compute='_compute_commission',
        string='Commission Amount',
        digits=dp.get_precision('Commission'))


class CommissionLines2(models.Model):

    """Commission Payment : commission_lines_2
    """

    _inherit = 'commission.lines'

    comm_invoice_id = fields.Many2one('commission.invoice',
                                      'Invoice Commission')


class ResCompany(models.Model):
    _inherit = "res.company"
    _description = 'Companies'

    comm_tax = fields.Float('Default Tax for Commissions')
