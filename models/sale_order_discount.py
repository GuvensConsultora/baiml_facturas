from odoo import fields, models


class SaleOrderDiscount(models.TransientModel):
    _inherit = 'sale.order.discount'

    # BAIML: quitar la opción "En todas las líneas" (sol_discount) del wizard
    # de descuento para evitar que un operador modifique por error el precio de
    # todas las líneas. Quedan solo Descuento global e Importe fijo.
    discount_type = fields.Selection(
        selection=[
            ('so_discount', 'Descuento global'),
            ('amount', 'Importe fijo'),
        ],
        default='so_discount',
        required=True,
    )
