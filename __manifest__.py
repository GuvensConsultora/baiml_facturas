{
    "name": "BAIML — Facturas (ajustes PDF)",
    "version": "19.0.1.16.0",
    "author": "Yagüven C.G.",
    "website": "https://yaguven.com",
    "category": "Accounting",
    "summary": "Ajustes PDF facturas: oculta columna Impuestos, fix encabezado II_IM, campos bonif/desc global, lista de precios en factura.",
    "depends": [
        "account",
        "l10n_ar",
        "sale",
    ],
    "data": [
        "data/product_data.xml",
        "views/account_move_view.xml",
        "views/sale_order_view.xml",
        "report/report_invoice_inherit.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
