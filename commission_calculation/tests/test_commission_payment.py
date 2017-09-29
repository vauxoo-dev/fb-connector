# coding: utf-8

"""Definition of the module testing cases (unittest)
"""

###############################################################################
#    Module Writen to OpenERP, Open Source Management Solution
#    Copyright (C) Vauxoo (<http://www.vauxoo.com>).
#    All Rights Reserved
###############################################################################
#    Credits:
#    Coded by: Humberto Arocha <hbto@vauxoo.com>
#    Planified by: Humberto Arocha <hbto@vauxoo.com>
#    Audited by: Humberto Arocha <hbto@vauxoo.com>
###############################################################################
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
###############################################################################
import time
from datetime import date, datetime, timedelta
from odoo.tests.common import TransactionCase


class TestCommission(TransactionCase):

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

        self.invoice_id = self.env.ref('commission_calculation.invoice_1')
        company_id.currency_id = self.invoice_id.currency_id
        self.invoice_id.action_invoice_open()
        self.invoice_id.pay_and_reconcile(self.journal_bank_id,
                                          self.invoice_id.amount_total)

        self.cp_brw = self.env.ref('commission_calculation.commission_1')

        date_last_payment = self.invoice_id.date_last_payment
        date_last_payment = datetime.strptime(date_last_payment, "%Y-%m-%d")
        datestop_date = date_last_payment + timedelta(days=1)
        datestop = datetime.strftime(datestop_date, "%Y-%m-%d")
        self.cp_brw.date_stop = datestop

        self.cp_brw.prepare()

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

        self.cp_brw.action_view_payment()
        self.cp_brw.action_view_invoice()
        self.assertEquals(
            self.cp_brw.total_comm, 660,
            'Commission should be 660')

        self.assertEquals(self.cp_brw.state, 'open',
                          'Commission Should be in State "Open"')

        self.assertEquals(len(self.cp_brw.salesman_ids) > 0, True,
                          'There should be at least one computation')
        for cs_brw in self.cp_brw.salesman_ids:
            if not cs_brw.salesman_id:
                continue
            self.assertEquals(cs_brw.salesman_id, demo_id,
                              'Salesman shall be "Demo User"')
            self.assertEquals(cs_brw.comm_total, 660.00,
                              'Wrong Quantity on commission')

        self.cp_brw.validate()
        self.assertEquals(
            self.cp_brw.state, 'done',
            'Commission Should be in State "Done"')

        self.cp_brw.action_draft()
        self.assertEquals(
            self.cp_brw.state, 'draft',
            'Commission Should be in State "Draft"')

        return True

    def test_fix_commission(self):
        self.cp_brw = self.env.ref('commission_calculation.commission_1')

        invoice_2 = self.env.ref('commission_calculation.invoice_2')
        invoice_2.action_invoice_open()
        invoice_2.date_due = invoice_2.date_invoice
        invoice_2.pay_and_reconcile(self.journal_bank_id)

        self.assertEquals(
            self.cp_brw.total_comm, 660,
            'Commission should be 660')
        self.cp_brw.action_draft()
        self.assertEquals(
            self.cp_brw.comm_fix, False,
            'There should be no Commission to Fix')
        self.cp_brw.unknown_salespeople = True
        self.cp_brw.prepare()
        self.cp_brw.action_view_fixlines()
        self.assertEquals(
            self.cp_brw.comm_fix, True,
            'There should be Commissions to Fix')
        self.assertNotEquals(
            self.cp_brw.total_comm, 660,
            'Commission should not be 660')

        no_salesman = [
            comm
            for comm in self.cp_brw.comm_line_ids
            if not comm.salesman_id
        ]

        salesman_id = self.ref('base.user_demo')
        for cl_brw in no_salesman:
            cl_brw.salesman_id = salesman_id

        self.cp_brw.action_recompute()
        self.assertEquals(
            self.cp_brw.comm_fix, False,
            'There should be no Commission to Fix')

        self.cp_brw.validate()
        self.assertEquals(
            self.cp_brw.state, 'done',
            'Commission Should be in State "Done"')

        return True

    def test_aml_commission(self):
        self.cp_brw.action_draft()

        month = str((date.today().month % 12) + 1)
        self.cp_brw.date_start = time.strftime('%Y') + '-' + month + '-01'
        self.cp_brw.date_stop = time.strftime('%Y') + '-' + month + '-28'

        self.cp_brw.unknown_salespeople = True

        aml_ids = self.aml_rec_debit + self.aml_rec_credit
        aml_ids.reconcile()

        self.cp_brw.prepare()

        self.assertEquals(
            self.cp_brw.comm_fix, True,
            'There should be Commissions to Fix')
        self.assertEquals(
            self.cp_brw.total_comm, 0,
            'Commission should be 0')

        no_salesman = [
            comm
            for comm in self.cp_brw.comm_line_ids
            if not comm.salesman_id
        ]

        salesman_id = self.ref('base.user_demo')
        partner_id = self.ref('base.res_partner_12')
        for cl_brw in no_salesman:
            cl_brw.salesman_id = salesman_id
            cl_brw.partner_id = partner_id

        self.cp_brw.action_recompute()

        self.assertEquals(
            self.cp_brw.total_comm, 30,
            'Commission should be 30')

        self.assertEquals(
            self.cp_brw.comm_fix, False,
            'There should be no Commission to Fix')

        self.cp_brw.validate()
        self.assertEquals(
            self.cp_brw.state, 'done',
            'Commission Should be in State "Done"')

        return True

    def test_product_commission(self):
        prod_brw = self.env.ref('product.product_product_4')

        price_ids = self.php_model.search(
            [('product_id', '=', prod_brw.product_tmpl_id.id)])

        self.assertEquals(
            len(price_ids) > 0, True,
            'There should historical prices on product %s' %
            prod_brw.name)

        self.cp_brw = self.env.ref('commission_calculation.commission_1')

        self.cp_brw.action_draft()
        self.assertEquals(
            self.cp_brw.state, 'draft',
            'Commission Should be in State "Draft"')

        self.cp_brw.commission_scope = 'product_invoiced'

        self.cp_brw.prepare()
        self.assertEquals(
            self.cp_brw.state, 'open',
            'Commission Should be in State "Open"')
        self.assertEquals(
            self.cp_brw.total_comm, 300,
            'Commission should be 300')

        self.cp_brw.validate()
        self.assertEquals(
            self.cp_brw.state, 'done',
            'Commission Should be in State "Done"')

        return True

    def test_partial_payment_commission(self):
        self.cp_brw.action_draft()
        self.cp_brw.commission_type = 'partial_payment'
        self.cp_brw.prepare()
        self.assertEquals(
            self.cp_brw.total_comm, 660,
            'Commission should be 660')
        return True

    def test_matrix_commission(self):
        self.cp_brw_2 = self.env.ref('commission_calculation.commission_2')

        invoice_2 = self.env.ref('commission_calculation.invoice_2')
        invoice_2.action_invoice_open()
        invoice_2.pay_and_reconcile(self.journal_bank_id)

        date_last_payment = invoice_2.date_last_payment
        date_last_payment = datetime.strptime(date_last_payment, "%Y-%m-%d")
        datestop_date = date_last_payment + timedelta(days=1)
        datestop = datetime.strftime(datestop_date, "%Y-%m-%d")
        self.cp_brw_2.date_stop = datestop

        self.assertEquals(
            self.cp_brw_2.state, 'draft',
            'Commission Should be in State "Draft"')

        self.cp_brw_2.prepare()
        self.assertEquals(
            self.cp_brw_2.state, 'open',
            'Commission Should be in State "Open"')
        self.assertEquals(
            self.cp_brw_2.salesman_ids[0].comm_voucher_ids[0].commission, 500,
            'Commission should be 500')

        self.assertEquals(
            self.cp_brw_2.total_comm, 500,
            'Commission should be 500')

        return True
