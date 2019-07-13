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
    "version": "11.0.0.0.8",
    "author": "Vauxoo",
    "website": "http://www.vauxoo.com",
    "license": "",
    "depends": [
        "account_invoicing",
        "decimal_precision",
        "mail",
    ],
    "test": [
        "../account/test/account_minimal_test.xml",
    ],
    "demo": [
        "demo/baremo.xml",
        "demo/res_partner.xml",
    ],
    "data": [
        "data/ir_module_category.xml",
        "views/product_view.xml",
        "views/baremo_book_view.xml",
        "views/baremo_matrix_view.xml",
        "views/res_partner_view.xml",
        "views/res_company_view.xml",
        "views/res_users_view.xml",
        "views/baremo_line_view.xml",
        "security/commission_calculation_security.xml",
        "security/ir.model.access.csv",
        "views/commission_template.xml",
        "views/commission_view.xml",
        "views/account_view.xml",
        "views/commission_calculation_menuitem.xml",
    ],
    "installable": True,
    "auto_install": False,
    "pre_init_hook": "pre_init_hook",
}
