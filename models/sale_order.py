from odoo import api, fields, models

BONIF_CODE = 'BONIF_BAIML'


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

    def _get_bonif_product(self):
        return self.env['product.product'].search(
            [('default_code', '=', BONIF_CODE)], limit=1
        )

    def _get_iva21_tax(self):
        return self.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', 21.0),
            ('amount_type', '=', 'percent'),
            ('company_id', '=', self.company_id.id),
            ('active', '=', True),
        ], limit=1)

    def _so_base_amount(self):
        return sum(
            l.price_unit * l.product_uom_qty
            for l in self.order_line
            if l.product_id.default_code != BONIF_CODE
        )

    def _sync_bonif_desc_so_lines(self):
        for order in self:
            # Desc % → campo discount en cada línea de producto
            for line in order.order_line:
                if line.product_id.default_code == BONIF_CODE:
                    continue
                if line.discount != order.discount_percent:
                    line.discount = order.discount_percent

            # Bonif % → línea negativa sobre importe bruto
            base = order._so_base_amount()
            bonif_amount = round(base * order.bonif_percent / 100, 2)

            existing = order.order_line.filtered(
                lambda l: l.product_id.default_code == BONIF_CODE
            )
            if order.bonif_percent == 0:
                existing.unlink()
                continue

            product = order._get_bonif_product()
            if not product:
                continue

            iva21 = order._get_iva21_tax()
            tax_cmd = [(6, 0, iva21.ids)] if iva21 else [(5, 0, 0)]

            vals = {
                'name': f'Bonificación {order.bonif_percent:.4g}%',
                'product_id': product.id,
                'product_uom_qty': 1,
                'price_unit': -bonif_amount,
                'discount': 0,
                'tax_id': tax_cmd,
            }
            if existing:
                existing.write(vals)
            else:
                order.order_line = [(0, 0, vals)]

    @api.onchange('bonif_percent', 'discount_percent')
    def _onchange_bonif_discount_so(self):
        self._sync_bonif_desc_so_lines()
