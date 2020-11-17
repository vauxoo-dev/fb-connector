from odoo import fields, models


class ResCompany(models.Model):

    _inherit = "res.company"
    _description = 'Companies'

    tax = fields.Float('Default Tax for Commissions')

    baremo_id = fields.Many2one(
        'baremo.book',
        related='partner_id.baremo_id',
        string="Baremo")
