# -*- coding: utf-8 -*-
############################################################################
#    Module Writen For Odoo, Open Source Management Solution
#
#    Copyright (c) 2017 Vauxoo - http://www.vauxoo.com
#    All Rights Reserved.
#    info Vauxoo (info@vauxoo.com)
#    coded by: Yanina Aular <yanina.aular@vauxoo.com>
#    audited by: Humberto Arocha <hbto@vauxoo.com>
############################################################################

from odoo import fields, models


class CommissionAbstract(models.AbstractModel):

    _name = 'commission.abstract'

    commission_type = fields.Selection([
        ('partial_payment', 'Partial Payments'),
        ('fully_paid_invoice', 'Fully Paid Invoices')],
        default='partial_payment', string='Basis',
        required=True, track_visibility='onchange',
        help="* Fully Paid Invoices: Sales commissions will be paid when the "
        "invoice is fully paid.\n"
        "* Partial Payments: Sales commissions will "
        "be partially paid, for each"
        " payment made to the invoice, a commission "
        "is calculated.")

    scope = fields.Selection([
        ('whole_invoice', 'Whole Invoice'),
        ('product_invoiced', 'Invoiced Products')],
        default='whole_invoice', string='Scope', track_visibility='onchange',
        help="* Full invoice: Commission payment based on invoice. "
        "The commission is calculated on the subtotal of the invoice, "
        "not including taxes. \n"
        "* Products invoiced: Payment of commission based on the "
        "products. The commission is calculated on each line of the "
        "invoice, not including taxes. You must specify by product "
        "how much commission will be paid. \n"
        "Note: Commissions are paid without taxes.")

    policy_date_start = fields.Selection([
        ('invoice_emission_date', 'Emission Date'),
        ('invoice_due_date', 'Due Date')],
        default='invoice_emission_date', track_visibility='onchange',
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
        " paid before 20 days. \n")

    policy_date_end = fields.Selection([
        ('last_payment_date', 'Last Payment on Invoice'),
        ('date_on_payment', 'Date of Payment')],
        default='last_payment_date', track_visibility='onchange',
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
        "the amount of the payment.")

    salesman_policy = fields.Selection([
        ('on_invoice', 'Invoice'),
        ('on_invoiced_partner', 'Partner'),
        ('on_accounting_partner', 'Commercial Entity')],
        track_visibility='onchange',
        help="* Invoice: The one on the invoice. The one that serves "
        "the person.\n"
        "* Partner: In the invoice partner tab or in the account "
        "move line. Partner assigned to the entity to which I am "
        "invoicing. That is, each customer has their assigned "
        "salesperson.\n"
        "* Commercial entity: The parent of the partner on the "
        "invoice. The customer handles the whole group. Serves "
        "if you have a group of vendors.")

    baremo_policy = fields.Selection([
        ('onCompany', 'Company'),
        ('onPartner', 'Partner'),
        ('onAccountingPartner', 'Commercial Entity'),
        ('onUser', 'Salespeople'),
        ('onMatrix', 'Baremo Matrix'),
        ('onCommission', 'This Document')],
        default='onCompany', string='Baremo Policy', track_visibility='onchange',
        help="- Company: use the baremo configured in the company.\n"
        "- Partner: Use the baremo by partner, ie the baremo "
        "configured for the partner \n"
        "- Business entity: Use the partner's parent baremo. "
        "That is the baremo configured for a group of clients.\n"
        "- Vendor: Use the baremo set up for the seller.\n"
        "- Baremo matrix: Use the baremo specified. When it comes "
        "to paying commissions on product lines.\n"
        "- This Document: Select a baremo by hand for everything\n")

    baremo_id = fields.Many2one(
        'baremo.book', required=True, track_visibility='onchange')
