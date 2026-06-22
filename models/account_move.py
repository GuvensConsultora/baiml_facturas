from odoo import api, fields, models

BONIF_CODE = 'BONIF_BAIML'
DESC_CODE = 'DESC_BAIML'  # legacy — se limpia si existe


class AccountMove(models.Model):
    _inherit = 'account.move'

    bonif_percent = fields.Float(string='Bonificación %', digits=(5, 2), default=0.0)
    discount_percent = fields.Float(string='Descuento %', digits=(5, 2), default=0.0)
    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Lista de precios',
        domain="[('currency_id', '=', currency_id)]",
    )

    def _get_special_product(self, default_code):
        return self.env['product.product'].search(
            [('default_code', '=', default_code)], limit=1
        )

    def _get_iva21_tax(self):
        return self.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', 21.0),
            ('amount_type', '=', 'percent'),
            ('company_id', '=', self.company_id.id),
            ('active', '=', True),
        ], limit=1)

    def _base_amount(self):
        """Importe bruto: price_unit × quantity, sin descuento, sin línea de bonif."""
        return sum(
            l.price_unit * l.quantity
            for l in self.invoice_line_ids
            if l.display_type == 'product'
            and l.product_id.default_code != BONIF_CODE
        )

    def _sync_bonif_desc_lines(self):
        for move in self:
            if move.move_type not in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
                continue

            # Desc % → campo discount en cada línea de producto
            for line in move.invoice_line_ids:
                if line.display_type != 'product':
                    continue
                if line.product_id.default_code == BONIF_CODE:
                    continue
                if line.discount != move.discount_percent:
                    line.discount = move.discount_percent

            # Limpiar líneas DESC_BAIML legacy si existen
            move.invoice_line_ids.filtered(
                lambda l: l.product_id.default_code == DESC_CODE
            ).unlink()

            # Bonif % → línea negativa sobre el importe bruto
            base = move._base_amount()
            bonif_amount = round(base * move.bonif_percent / 100, 2)

            existing_bonif = move.invoice_line_ids.filtered(
                lambda l: l.product_id.default_code == BONIF_CODE
            )
            if move.bonif_percent == 0:
                existing_bonif.unlink()
                continue

            product = move._get_special_product(BONIF_CODE)
            if not product:
                continue

            iva21 = move._get_iva21_tax()
            tax_cmd = [(6, 0, iva21.ids)] if iva21 else [(5, 0, 0)]

            vals = {
                'name': f'Bonificación {move.bonif_percent:.4g}%',
                'product_id': product.id,
                'quantity': 1,
                'price_unit': -bonif_amount,
                'tax_ids': tax_cmd,
            }
            if existing_bonif:
                existing_bonif.write(vals)
            else:
                move.invoice_line_ids = [(0, 0, vals)]

    @api.onchange('bonif_percent', 'discount_percent')
    def _onchange_bonif_discount(self):
        self._sync_bonif_desc_lines()

    def action_apply_pricelist(self):
        special = {BONIF_CODE, DESC_CODE}
        for move in self:
            if not move.pricelist_id or move.state != 'draft':
                continue
            for line in move.invoice_line_ids.filtered(
                lambda l: l.display_type == 'product'
                    and l.product_id
                    and l.product_id.default_code not in special
            ):
                price = move.pricelist_id._get_product_price(
                    line.product_id,
                    line.quantity or 1.0,
                    currency=move.currency_id,
                    date=move.invoice_date or fields.Date.today(),
                )
                line.price_unit = price
            move._sync_bonif_desc_lines()
