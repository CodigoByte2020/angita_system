{
    'name': 'Ventas',
    'summary': 'Módulo de Ventas',
    'description': 'Módulo para la gestión de las ventas.',
    'author': 'Contreras Pumamango Gianmarco - gmcontrpuma@gmail.com',
    'website': 'https://github.com/CodigoByte2020',
    'category': 'Tools',
    'version': '18.0.0.0.1',
    'depends': [
        'inventario'
    ],
    'data': [
        # DATA
        'data/ir_sequence_data.xml',
        'data/paperformat.xml',
        'data/data.xml',
        # SECURITY
        'security/ir.model.access.csv',
        # VIEWS
        'views/ventas_menus_views.xml',
        'views/ventas_views.xml',
        'views/cliente_views.xml',
        'views/producto_views.xml',
        # WIZARDS
        'wizards/reporte_venta_wizard_views.xml',
        # REPORTS:
        'reports/reporte_venta.xml',
        'reports/invoice_report.xml'
    ],
    'installable': True,
}
