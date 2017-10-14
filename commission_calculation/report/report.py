# coding: utf-8
############################################################################
#    Module Writen For Odoo, Open Source Management Solution
#
#    Copyright (c) 2010 Vauxoo - http://www.vauxoo.com
#    All Rights Reserved.
#    info Vauxoo (info@vauxoo.com)
#    coded by: Humberto Arocha <hbto@vauxoo.com>
############################################################################


import time

from odoo import models
from odoo.report import report_sxw


class CommParser(report_sxw.rml_parse):
    _name = 'ifrs.parser'

    def __init__(self, cr, uid, name, context=None):
        super(CommParser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
        })
        self.context = context

    def set_context(self, objects, data, ids, report_type=None):
        # This is a way of capturing objects as depicted in
        # odoo/addons/account/report/account_balance.py
        new_ids = ids
        return super(CommParser, self).set_context(objects, data, new_ids,
                                                   report_type=report_type)


class IfrsPortraitPdfReport(models.AbstractModel):

    # _name = `report.` + `report_name`
    # report_name="commission_calculation.comm_salespeople_template"
    _name = 'report.commission_calculation.comm_salespeople_template'

    # this inheritance will allow to render this particular report
    _inherit = 'report.abstract_report'
    _template = 'commission_calculation.comm_salespeople_template'
    _wrapped_report_class = CommParser
