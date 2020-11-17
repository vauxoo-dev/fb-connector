from odoo import fields, models


class ResPartner(models.Model):

    _inherit = "res.partner"

    baremo_id = fields.Many2one('baremo.book', 'Baremo')
