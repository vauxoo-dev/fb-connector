from odoo import fields, models


class CommissionTemplate(models.Model):

    _name = 'commission.template'
    _inherit = 'commission.abstract'

    name = fields.Char(
        "Template's name", required=True,
        track_visibility='onchange',
        help="Commission template's name")
