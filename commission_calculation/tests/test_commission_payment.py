# coding: utf-8

import time
from datetime import date, datetime, timedelta
from .common import Common


class TestCommission(Common):

    """Tests for Commissions (commission.payment)
    """

    def setUp(self):
        """basic method to define some basic data to be re use in all test cases.
        """
        super(TestCommission, self).setUp()
        self.cp_model = self.env['commission.payment']
        self.php_model = self.env['product.historic.price']
        self.aml_model = self.env['account.move.line']
        self.am_model = self.env['account.move']
        self.inv_model = self.env['account.invoice']
        self.prod_model = self.env['product.product']
        self.journal_id = self.env.ref('commission_calculation.sales_journal')
        company_id = self.env.ref('base.main_company')
        self.journal_bank_id = self.env.ref(
            'commission_calculation.bank_journal')
        account_recv_id = self.ref('commission_calculation.a_recv')
        account_sale_id = self.ref('commission_calculation.a_recv')
        account_bnk_id = self.ref('commission_calculation.bnk')

        company_id.currency_id = self.invoice_1.currency_id
        self.invoice_1.action_invoice_open()
        self.invoice_1.pay_and_reconcile(self.journal_bank_id,
                                         self.invoice_1.amount_total)

        self.commission_payment = self.env.ref('commission_calculation.commission_payment_01')

        date_last_payment = self.invoice_1.date_last_payment
        date_last_payment = datetime.strptime(date_last_payment, "%Y-%m-%d")
        datestop_date = date_last_payment + timedelta(days=1)
        datestop = datetime.strftime(datestop_date, "%Y-%m-%d")
        self.commission_payment.date_stop = datestop

        self.commission_payment.prepare()

        vals = {
            'date': time.strftime(
                '%Y-' + str((int(time.strftime('%m')) % 12) + 1) + '-01'),
            'journal_id': self.journal_id.id,
            'name': 'Test move',
            'line_ids': [(0, 0, {
                    'name': 'Receivable - Debit',
                    'account_id': account_recv_id,
                    'debit': 1000.00,
                    'credit': 0.0,
                }), (0, 0, {
                    'name': 'Sale',
                    'account_id': account_sale_id,
                    'debit': 0.0,
                    'credit': 1000.0,
                })],
            'company_id': company_id.id,
        }
        move = self.am_model.create(vals)
        self.aml_rec_debit = self.aml_model.search(
            [('move_id', '=', move.id), ('name', '=', 'Receivable - Debit')])

        vals = {
            'date': time.strftime(
                '%Y-' + str((int(time.strftime('%m')) % 12) + 1) + '-27'),
            'journal_id': self.journal_bank_id.id,
            'name': 'Test move',
            'line_ids': [(0, 0, {
                    'name': 'Bank',
                    'account_id': account_bnk_id,
                    'debit': 1000.00,
                    'credit': 0.0,
                }), (0, 0, {
                    'name': 'Receivable - Credit',
                    'account_id': account_recv_id,
                    'debit': 0.0,
                    'credit': 1000.0,
                })],
            'company_id': company_id.id,
        }
        move = self.am_model.create(vals)

        self.aml_rec_credit = self.aml_model.search(
            [('move_id', '=', move.id),
             ('name', '=', 'Receivable - Credit')])

    def test_basic_commission(self):
        demo_id = self.env.ref('base.user_demo')

        self.commission_payment.action_view_payment()
        self.commission_payment.action_view_invoice()
        self.assertEquals(
            self.commission_payment.total, 660,
            'Commission should be 660')

        self.assertEquals(self.commission_payment.state, 'open',
                          'Commission Should be in State "Open"')

        self.assertEquals(len(self.commission_payment.salesman_ids) > 0, True,
                          'There should be at least one computation')
        for commission in self.commission_payment.salesman_ids:
            if not commission.salesman_id:
                continue
            self.assertEquals(commission.salesman_id, demo_id,
                              'Salesman shall be "Demo User"')
            self.assertEquals(commission.total, 660.00,
                              'Wrong Quantity on commission')

        self.commission_payment.validate()
        self.assertEquals(
            self.commission_payment.state, 'done',
            'Commission Should be in State "Done"')

        self.commission_payment.action_draft()
        self.assertEquals(
            self.commission_payment.state, 'draft',
            'Commission Should be in State "Draft"')

        return True

    def test_fix_commission(self):
        self.commission_payment = self.env.ref('commission_calculation.commission_payment_01')

        self.invoice_2.action_invoice_open()
        self.invoice_2.date_due = self.invoice_2.date_invoice
        self.invoice_2.pay_and_reconcile(self.journal_bank_id)

        self.assertEquals(
            self.commission_payment.total, 660,
            'Commission should be 660')
        self.commission_payment.action_draft()
        self.assertEquals(
            self.commission_payment.comm_fix, False,
            'There should be no Commission to Fix')
        self.commission_payment.unknown_salespeople = True
        self.commission_payment.prepare()
        self.commission_payment.action_view_fixlines()
        self.assertEquals(
            self.commission_payment.comm_fix, True,
            'There should be Commissions to Fix')
        self.assertEquals(
            self.commission_payment.total, 660,
            'Commission should not be 660')

        no_salesman = [
            comm
            for comm in self.commission_payment.line_ids
            if not comm.salesman_id
        ]

        salesman_id = self.ref('base.user_demo')
        for commission_line in no_salesman:
            commission_line.salesman_id = salesman_id

        self.commission_payment.action_recompute()
        self.assertNotEquals(
            self.commission_payment.total, 660,
            'Commission should not be 660')
        self.assertEquals(
            self.commission_payment.comm_fix, False,
            'There should be no Commission to Fix')

        self.commission_payment.validate()
        self.assertEquals(
            self.commission_payment.state, 'done',
            'Commission Should be in State "Done"')

        return True

    def test_aml_commission(self):
        self.commission_payment.action_draft()

        month = str((date.today().month % 12) + 1)
        self.commission_payment.date_start = time.strftime('%Y') + '-' + month + '-01'
        self.commission_payment.date_stop = time.strftime('%Y') + '-' + month + '-28'

        self.commission_payment.unknown_salespeople = True

        aml_ids = self.aml_rec_debit + self.aml_rec_credit
        aml_ids.reconcile()

        self.commission_payment.prepare()

        self.assertEquals(
            self.commission_payment.comm_fix, True,
            'There should be Commissions to Fix')
        self.assertEquals(
            self.commission_payment.total, 0,
            'Commission should be 0')

        no_salesman = [
            comm
            for comm in self.commission_payment.line_ids
            if not comm.salesman_id
        ]

        salesman_id = self.ref('base.user_demo')
        partner_id = self.ref('base.res_partner_12')
        for commission_line in no_salesman:
            commission_line.salesman_id = salesman_id
            commission_line.partner_id = partner_id

        self.commission_payment.action_recompute()

        self.assertEquals(
            self.commission_payment.total, 30,
            'Commission should be 30')

        self.assertEquals(
            self.commission_payment.comm_fix, False,
            'There should be no Commission to Fix')

        self.commission_payment.validate()
        self.assertEquals(
            self.commission_payment.state, 'done',
            'Commission Should be in State "Done"')

        return True

    def test_product_commission(self):
        product = self.env.ref('product.product_product_4')

        price_ids = self.php_model.search(
            [('product_id', '=', product.id)])

        self.assertEquals(
            len(price_ids) > 0, True,
            'There should historical prices on product %s' %
            product.name)

        self.commission_payment = self.env.ref('commission_calculation.commission_payment_01')

        self.commission_payment.action_draft()
        self.assertEquals(
            self.commission_payment.state, 'draft',
            'Commission Should be in State "Draft"')

        self.commission_payment.scope = 'product_invoiced'

        self.commission_payment.prepare()
        self.assertEquals(
            self.commission_payment.state, 'open',
            'Commission Should be in State "Open"')
        self.assertEquals(
            self.commission_payment.total, 300,
            'Commission should be 300')

        self.commission_payment.validate()
        self.assertEquals(
            self.commission_payment.state, 'done',
            'Commission Should be in State "Done"')

        return True

    def test_partial_payment_commission(self):
        self.commission_payment.action_draft()
        self.commission_payment.commission_type = 'partial_payment'
        self.commission_payment.prepare()
        self.assertEquals(
            self.commission_payment.total, 660,
            'Commission should be 660')
        return True

    def test_matrix_commission(self):
        self.commission_payment_2 = self.env.ref('commission_calculation.commission_payment_02')

        self.invoice_2.action_invoice_open()
        self.invoice_2.pay_and_reconcile(self.journal_bank_id)

        date_last_payment = self.invoice_2.date_last_payment
        date_last_payment = datetime.strptime(date_last_payment, "%Y-%m-%d")
        datestop_date = date_last_payment + timedelta(days=1)
        datestop = datetime.strftime(datestop_date, "%Y-%m-%d")
        self.commission_payment_2.date_stop = datestop

        self.assertEquals(
            self.commission_payment_2.state, 'draft',
            'Commission Should be in State "Draft"')

        self.commission_payment_2.prepare()
        self.assertEquals(
            self.commission_payment_2.state, 'open',
            'Commission Should be in State "Open"')
        self.assertEquals(
            self.commission_payment_2.salesman_ids[0].total, 500,
            'Commission should be 500')
        self.assertEquals(
            self.commission_payment_2.salesman_ids[0].currency_amount, 500,
            'Commission should be 500')

        self.assertEquals(
            self.commission_payment_2.total, 500,
            'Commission should be 500')

        return True
