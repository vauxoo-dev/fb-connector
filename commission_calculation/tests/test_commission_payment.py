import time
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError
from .common import Common


class TestCommission(Common):

    def setUp(self):
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

        self.commission_payment = self.env.ref(
            'commission_calculation.commission_payment_01')

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

        commissions = self.commission_payment.salesman_ids\
            .filtered('salesman_id')
        self.assertEquals(commissions.mapped('salesman_id'), demo_id,
                          'Salesman shall be "Demo User"')
        self.assertEquals(commissions.mapped('total'), [660.00],
                          'Wrong Quantity on commission')

        self.commission_payment.validate()
        self.assertEquals(
            self.commission_payment.state, 'done',
            'Commission Should be in State "Done"')

        self.commission_payment.action_draft_from_done()
        self.assertEquals(
            self.commission_payment.state, 'draft',
            'Commission Should be in State "Draft"')

        duplicated_commission = self.commission_payment.copy()

        self.commission_payment.prepare()
        duplicated_commission.prepare()

        self.assertEquals(
            duplicated_commission.total, 660,
            'Commission should be 660')

        self.commission_payment.validate()
        duplicated_commission.validate()

        self.assertEquals(
            self.commission_payment.state, 'done')
        self.assertEquals(
            duplicated_commission.state, 'open')

        duplicated_commission.prepare()

        self.assertEquals(
            duplicated_commission.total, 0.0,
            'Commission should be 0.0')

        duplicated_commission.validate()

        self.assertEquals(
            duplicated_commission.state, 'done')

        return True

    def test_template_commission(self):
        self.commission_payment = self.env.ref(
            'commission_calculation.commission_payment_01')
        baremo_1 = self.env.ref(
            'commission_calculation.baremo_book_01')

        template_obj = self.env['commission.template']
        template = template_obj.create({
            'name': 'Test 1',
            'commission_type': 'partial_payment',
            'scope': 'product_invoiced',
            'policy_date_start': 'invoice_due_date',
            'policy_date_end': 'date_on_payment',
            'salesman_policy': 'on_accounting_partner',
            'baremo_policy': 'onUser',
            'baremo_id': baremo_1.id,
        })

        self.assertEquals(self.commission_payment.commission_type,
                          'fully_paid_invoice')
        self.commission_payment.template_id = template
        self.commission_payment._onchange_template()
        self.assertEquals(self.commission_payment.commission_type,
                          'partial_payment')
        self.assertEquals(self.commission_payment.scope,
                          'product_invoiced')

    def test_policy_baremo(self):
        # onCompany
        self.commission_payment.baremo_policy = 'onCompany'
        self.commission_payment.policy_date_start = 'invoice_emission_date'
        self.commission_payment.prepare()

        # onPartner
        self.commission_payment.write({'baremo_policy': 'onPartner'})
        self.commission_payment.policy_date_end = 'date_on_payment'
        self.commission_payment.prepare()

        # onAccountingPartner
        self.commission_payment.write({'baremo_policy': 'onAccountingPartner'})
        self.commission_payment.salesman_policy = 'on_accounting_partner'
        self.commission_payment.prepare()

        # onUser
        self.commission_payment.write({'baremo_policy': 'onUser'})
        self.commission_payment.prepare()

        # onCommission
        self.commission_payment.write({'baremo_policy': 'onCommission'})
        self.commission_payment.prepare()

    def test_fix_commission(self):
        self.commission_payment = self.env.ref(
            'commission_calculation.commission_payment_01')

        self.invoice_2.action_invoice_open()
        self.invoice_2.date_due = self.invoice_2.date_invoice
        self.invoice_2.pay_and_reconcile(self.journal_bank_id)

        self.assertEquals(
            self.commission_payment.total, 660,
            'Commission should be 660')
        self.assertEquals(
            self.commission_payment.comm_fix, False,
            'There should be no Commission to Fix')
        self.commission_payment.action_draft_from_done()

        self.commission_payment.prepare()
        self.commission_payment.action_view_fixlines()
        self.assertEquals(
            self.commission_payment.comm_fix, True,
            'There should be Commissions to Fix')
        self.assertEquals(
            self.commission_payment.total, 660,
            'Commission should not be 660')

        salesman_id = self.ref('base.user_demo')
        self.commission_payment.line_ids\
            .filtered(lambda line: not line.salesman_id)\
            .write({'salesman_id': salesman_id})

        self.commission_payment.action_recompute()
        self.assertEquals(
            self.commission_payment.total, 675,
            'Commission should not be 675')
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
        self.commission_payment.date_start = \
            time.strftime('%Y') + '-' + month + '-01'
        self.commission_payment.date_stop = \
            time.strftime('%Y') + '-' + month + '-28'

        aml_ids = self.aml_rec_debit + self.aml_rec_credit
        aml_ids.reconcile()

        self.commission_payment.prepare()

        self.assertEquals(
            self.commission_payment.comm_fix, True,
            'There should be Commissions to Fix')
        self.assertEquals(
            self.commission_payment.total, 0,
            'Commission should be 0')

        salesman_id = self.ref('base.user_demo')
        self.commission_payment.line_ids\
            .filtered(lambda line: not line.salesman_id)\
            .write({'salesman_id': salesman_id})

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

        self.commission_payment = self.env.ref(
            'commission_calculation.commission_payment_01')

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
        self.commission_payment.action_draft_from_done()
        self.commission_payment.commission_type = 'partial_payment'
        self.commission_payment.prepare()
        self.assertEquals(
            self.commission_payment.total, 660,
            'Commission should be 660')
        return True

    def test_matrix_commission(self):
        self.commission_payment_2 = self.env.ref(
            'commission_calculation.commission_payment_02')

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

        self.commission_payment_2.action_draft_from_done()
        self.commission_payment_2.baremo_policy = 'onMatrix'
        self.commission_payment_2.scope = 'whole_invoice'

        error = 'Baremo on Matrix only applies on Invoiced Products'
        with self.assertRaisesRegexp(UserError, error):
            self.commission_payment_2.prepare()

        return True
