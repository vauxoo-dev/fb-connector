from odoo import fields, models


class ResUsers(models.Model):

    _inherit = "res.users"

    matrix_ids = fields.One2many(
        'baremo.matrix', 'user_id',
        'Baremo Matrix', copy=False,
        help="Display all commissions of the user")
