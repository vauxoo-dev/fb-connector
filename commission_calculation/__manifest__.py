# coding: utf-8
############################################################################
#    Module Writen For Odoo, Open Source Management Solution
#
#    Copyright (c) 2010 Vauxoo - http://www.vauxoo.com
#    All Rights Reserved.
#    info Vauxoo (info@vauxoo.com)
#    coded by: Humberto Arocha <humberto@vauxoo.com>
############################################################################

{
    "name": "Commission based on Payments",
    "version": "10.0.0.0.8",
    "author": "Vauxoo",
    "website": "http://www.vauxoo.com",
    "license": "",
    "depends": [
        "product",
        "decimal_precision",
        "sale",
        "base_action_rule",
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
        "data/data.xml",
        "security/commission_calculation_security.xml",
        "security/ir.model.access.csv",
        "report/layouts.xml",
        "report/template.xml",
        "data/report_paperformat.xml",
        "views/commission_template.xml",
        "views/commission_report.xml",
        "views/commission_view.xml",
        "views/account_view.xml",
        "views/commission_calculation_menuitem.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": True,
}
