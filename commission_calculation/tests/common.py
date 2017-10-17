# coding: utf-8
############################################################################
#    Module Writen For Odoo, Open Source Management Solution
#
#    Copyright (c) 2017 Vauxoo - http://www.vauxoo.com
#    All Rights Reserved.
#    info Vauxoo (info@vauxoo.com)
#    coded by: Yanina Aular <yanina.aular@vauxoo.com>
############################################################################

import time
from odoo.tests.common import TransactionCase


class Common(TransactionCase):

    def setUp(self):
        super(Common, self).setUp()
        self.account_obj = self.env['account.invoice']
        self.account_line_obj = self.env['account.invoice.line']

        self.invoice_1 = self.account_obj.create({
            'currency_id': self.ref('base.EUR'),
            'company_id': self.ref('base.main_company'),
            'journal_id': self.ref('commission_calculation.sales_journal'),
            'state': 'draft',
            'type': 'out_invoice',
            'account_id': self.ref('commission_calculation.a_recv'),
            'partner_id': self.ref('base.res_partner_12'),
            'date_invoice': time.strftime('%Y-%m-01'),
            'user_id': self.ref('base.user_root'),
        })

        self.account_line_obj.create({
            'name': 'Vauxoo Specialities',
            'invoice_id': self.invoice_1.id,
            'price_unit': 2000,
            'quantity': 5,
            'account_id': self.ref('commission_calculation.a_sale'),
            'product_id': self.ref('product.product_product_4'),
        })

        self.account_line_obj.create({
            'name': 'Vauxoo Consultancy',
            'invoice_id': self.invoice_1.id,
            'price_unit': 4000,
            'quantity': 3,
            'account_id': self.ref('commission_calculation.a_sale'),
        })

        self.invoice_2 = self.account_obj.create({
            'name': 'Test invoice 1',
            'currency_id': self.ref('base.EUR'),
            'company_id': self.ref('base.main_company'),
            'journal_id': self.ref('commission_calculation.sales_journal'),
            'state': 'draft',
            'type': 'out_invoice',
            'account_id': self.ref('commission_calculation.a_recv'),
            'partner_id': self.ref('base.res_partner_1'),
            'date_invoice': time.strftime('%Y-%m-01'),
            'user_id': self.ref('base.user_root'),
        })

        self.account_line_obj.create({
            'name': 'Basic formation with Dvorak',
            'invoice_id': self.invoice_2.id,
            'price_unit': 500,
            'quantity': 1,
            'account_id': self.ref('commission_calculation.a_sale'),
        })
