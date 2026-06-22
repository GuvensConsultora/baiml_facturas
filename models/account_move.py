from odoo import api, fields, models

BONIF_CODE = 'BONIF_BAIML'
DESC_CODE = 'DESC_BAIML'


class AccountMove(models.Model):
    _inherit = 'account.move'

    bonif_percent = fields.Float(string='Bonificación %', digits=(5, 2), default=0.0)
    discount_percent = fields.Float(string='Descuento %', digits=(5, 2), default=0.0)

    def _get_special_product(self, default_code):
        return self.env['product.product'].search(
            [('default_code', '=', default_code)], limit=1
        )

    def _base_amount(self):
        special = {BONIF_CODE, DESC_CODE}
        return sum(
            l.price_subtotal
            for l in self.invoice_line_ids
            if l.product_id.default_code not in special
            and l.display_type == 'product'
        )

    def _sync_bonif_desc_lines(self):
        for move in self:
            if move.move_type not in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
                continue

            base = move._base_amount()
            bonif_amount = round(base * move.bonif_percent / 100, 2)
            after_bonif = base - bonif_amount
            desc_amount = round(after_bonif * move.discount_percent / 100, 2)

            for code, pct, amount, label in [
                (BONIF_CODE, move.bonif_percent, bonif_amount, 'Bonificación'),
                (DESC_CODE, move.discount_percent, desc_amount, 'Descuento comercial'),
            ]:
                existing = move.invoice_line_ids.filtered(
                    lambda l, c=code: l.product_id.default_code == c
                )
                if pct == 0:
                    existing.unlink()
                    continue

                product = move._get_special_product(code)
                if not product:
                    continue

                vals = {
                    'name': f'{label} {pct:.4g}%',
                    'product_id': product.id,
                    'quantity': 1,
                    'price_unit': -amount,
                    'tax_ids': [(5, 0, 0)],
                }
                if existing:
                    existing.write(vals)
                else:
                    move.invoice_line_ids = [(0, 0, vals)]

    @api.onchange('bonif_percent', 'discount_percent')
    def _onchange_bonif_discount(self):
        self._sync_bonif_desc_lines()
