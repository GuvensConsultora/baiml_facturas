import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Limpia artefactos huérfanos del feature de bonificación (removido en 1.19).

    Al renombrar la vista de factura y eliminar la de venta, y quitar el campo
    `bonif_percent`, la limpieza automática de Odoo NO eliminó las vistas viejas ni
    la metadata del campo (no puede borrar un campo mientras una vista lo referencia,
    y esas vistas quedaron huérfanas). Resultado: el form de factura/venta rompía en
    el cliente con «"account.move"."bonif_percent" field is undefined».

    Se eliminan explícitamente, en orden: primero las vistas, luego el campo.
    Idempotente: si ya no existen, no hace nada.
    """
    if not version:
        return

    # 1) Vistas huérfanas que aún referencian bonif_percent (causa del crash Owl).
    cr.execute("""
        SELECT res_id FROM ir_model_data
         WHERE module = 'baiml_facturas' AND model = 'ir.ui.view'
           AND name IN ('view_move_bonif_desc', 'view_sale_order_bonif_desc')
    """)
    view_ids = [r[0] for r in cr.fetchall()]
    if view_ids:
        cr.execute("DELETE FROM ir_ui_view WHERE id IN %s", (tuple(view_ids),))
        cr.execute("""
            DELETE FROM ir_model_data
             WHERE module = 'baiml_facturas' AND model = 'ir.ui.view'
               AND name IN ('view_move_bonif_desc', 'view_sale_order_bonif_desc')
        """)
        _logger.info("baiml_facturas: %s vista(s) huérfana(s) bonif_percent eliminadas", len(view_ids))

    # 2) Metadata del campo bonif_percent (account.move / sale.order / statement.line).
    cr.execute("""
        SELECT id FROM ir_model_fields
         WHERE name = 'bonif_percent'
           AND model IN ('account.move', 'sale.order', 'account.bank.statement.line')
    """)
    field_ids = [r[0] for r in cr.fetchall()]
    if field_ids:
        cr.execute("DELETE FROM ir_default WHERE field_id IN %s", (tuple(field_ids),))
        cr.execute("DELETE FROM ir_model_data WHERE model = 'ir.model.fields' AND res_id IN %s", (tuple(field_ids),))
        cr.execute("DELETE FROM ir_model_fields WHERE id IN %s", (tuple(field_ids),))
        _logger.info("baiml_facturas: metadata de %s campo(s) bonif_percent eliminada", len(field_ids))
