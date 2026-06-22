from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    bonif_percent = fields.Float(string='Bonificación %', digits=(5, 2), default=0.0)
    discount_percent = fields.Float(string='Descuento %', digits=(5, 2), default=0.0)

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        vals['bonif_percent'] = self.bonif_percent
        vals['discount_percent'] = self.discount_percent
        return vals

    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        moves._sync_bonif_desc_lines()
        return moves
