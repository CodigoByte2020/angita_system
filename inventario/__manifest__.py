{
    'name': 'Inventario',
    'summary': 'Módulo de Inventario',
    'description': 'Módulo para gestionar el inventario.',
    'author': 'Contreras Pumamango Gianmarco - gmcontrpuma@gmail.com',
    'website': 'https://github.com/CodigoByte2020',
    'category': 'Tools',
    'version': '18.0.0.0.1',
    'depends': [
        'estructura_base'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/inventario_menus_views.xml',
        'views/inventario_producto_views.xml',
        'views/ajustes_inventario_views.xml',
        'views/movimientos_views.xml'
    ],
    'installable': True,
}
