from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    truth_order_note = fields.Text('Preparation notes')
