from odoo import api, models

# Opción del wizard nativo de descuento que BAIML no quiere ofrecer al operador:
# "On All Order Lines" (aplica el % a TODAS las líneas → riesgo de dedazo).
HIDDEN_DISCOUNT_TYPE = 'sol_discount'


class SaleOrderDiscount(models.TransientModel):
    _inherit = 'sale.order.discount'

    # No se redefine el campo `discount_type` (eso dispara "overrides existing
    # selection; use selection_add instead" y rompe el registry). En su lugar se
    # filtra la opción SOLO a nivel UI vía fields_get: el campo nativo conserva
    # las tres opciones como válidas (no se rompe la lógica del core), pero el
    # radio muestra únicamente Descuento global e Importe fijo.
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        sel = res.get('discount_type', {}).get('selection')
        if sel:
            res['discount_type']['selection'] = [
                opt for opt in sel if opt[0] != HIDDEN_DISCOUNT_TYPE
            ]
        return res

    # El default nativo es 'sol_discount' (la opción que ocultamos). Si llega ese
    # valor, arrancamos en 'so_discount' (Descuento global) para que el radio abra
    # con una opción visible seleccionada.
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if res.get('discount_type') == HIDDEN_DISCOUNT_TYPE:
            res['discount_type'] = 'so_discount'
        return res
