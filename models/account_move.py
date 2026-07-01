from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Lista de precios',
        domain="[('currency_id', '=', currency_id)]",
    )

    def action_apply_pricelist(self):
        for move in self:
            if not move.pricelist_id or move.state != 'draft':
                continue
            for line in move.invoice_line_ids.filtered(
                lambda l: l.display_type == 'product' and l.product_id
            ):
                line.price_unit = move.pricelist_id._get_product_price(
                    line.product_id,
                    line.quantity or 1.0,
                    currency=move.currency_id,
                    date=move.invoice_date or fields.Date.today(),
                )
