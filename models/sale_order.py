from odoo import api, fields, models

BONIF_CODE = 'BONIF_BAIML'


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    bonif_percent = fields.Float(string='Bonificación %', digits=(5, 2), default=0.0)

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        vals['bonif_percent'] = self.bonif_percent
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
        if self.env.context.get('_syncing_bonif'):
            return
        self = self.with_context(_syncing_bonif=True)

        for order in self:
            base = order._so_base_amount()
            bonif_amount = round(base * order.bonif_percent / 100, 2)

            existing = order.order_line.filtered(
                lambda l: l.product_id.default_code == BONIF_CODE
            )

            if existing:
                if order.bonif_percent == 0:
                    order.order_line = [(2, e.id, 0) for e in existing]
                else:
                    existing[0].name = f'Bonificación {order.bonif_percent:.4g}%'
                    existing[0].price_unit = -bonif_amount
            elif order.bonif_percent > 0:
                product = order._get_bonif_product()
                if not product:
                    continue
                iva21 = order._get_iva21_tax()
                tax_cmd = [(6, 0, iva21.ids)] if iva21 else [(5, 0, 0)]
                order.order_line = [(0, 0, {
                    'name': f'Bonificación {order.bonif_percent:.4g}%',
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'price_unit': -bonif_amount,
                    'discount': 0,
                    'tax_ids': tax_cmd,
                })]

    # Hook nativo: excluir la línea de bonificación del recálculo de precios por
    # lista. Sin esto, action_update_prices la pisaría a 0 (su producto tiene
    # list_price=0) usando force_price_recomputation.
    def _get_update_prices_lines(self):
        lines = super()._get_update_prices_lines()
        return lines.filtered(lambda l: l.product_id.default_code != BONIF_CODE)

    # Hook nativo interno de "Actualizar precios": tras recalcular las líneas
    # normales (y resetear su discount a 0), reaplicamos desc % y recalculamos
    # el monto de la bonificación sobre la nueva base. Todo en la misma
    # transacción → automático, sin botón extra.
    def _recompute_prices(self):
        super()._recompute_prices()
        self.filtered(lambda o: o.bonif_percent)._sync_bonif_desc_so_lines()

    @api.onchange('bonif_percent')
    def _onchange_bonif_so(self):
        self._sync_bonif_desc_so_lines()
