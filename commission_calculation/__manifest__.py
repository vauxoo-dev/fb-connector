# coding: utf-8
##############################################################################
#
# Copyright (c) 2010 Vauxoo C.A. (http://openerp.com.ve/) All Rights Reserved.
#                    Humberto Arocha <humbertoarocha@gmail.com>
#
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
{
    "name": "Salespeople Commission based on Payments",
    "version": "10.0.0.0.8",
    "author": "Vauxoo",
    "category": "Generic Modules/Others",
    "website": "http://www.vauxoo.com",
    "license": "",
    "depends": [
        "base",
        # Product historical price
        "product",
        "decimal_precision",
        "sale",
        "base_action_rule",
        # Commission Payment
        "account",
        "mail",
        "message_post_model",
        "report",
    ],
    "demo": [
        "../account/test/account_minimal_test.xml",
        "demo/baremo.xml",
        "demo/res_partner.xml",
        "demo/account_invoice.xml",
    ],
    "data": [
        # product_historical_price
        "views/product_view.xml",
        "data/product_data.xml",
        "data/action_server_data.xml",
        # Baremo
        "views/baremo_view.xml",
        # Commission Payment
        "security/commission_calculation_security.xml",
        "security/ir.model.access.csv",
        "report/layouts.xml",
        "report/template.xml",
        "data/report_paperformat.xml",
        "data/data.xml",
        "views/commission_report.xml",
        "views/commission_view.xml",
        "views/account_view.xml",
        "views/commission_calculation_menuitem.xml",
    ],
    "installable": True,
    "auto_install": False,
}
