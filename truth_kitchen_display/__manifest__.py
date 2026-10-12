{
    'name': 'Truth Kitchen Display',
    'version': '19.0.2.0.0',
    'summary': 'Configurable kitchen and bar screens, independent of the Truth website',
    'author': 'Spxcorp Limited', 'license': 'LGPL-3', 'category': 'Point of Sale',
    'depends': ['pos_restaurant', 'sale', 'mail'],
    'data': ['security/security.xml', 'security/ir.model.access.csv', 'views/display.xml', 'views/backend.xml', 'views/kitchen.xml'],
    'pre_init_hook': 'pre_init_hook', 'post_init_hook': 'post_init_hook',
    'application': True, 'installable': True,
}
