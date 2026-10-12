{
    'name': 'Truth Lounge — Restaurant Experience',
    'version': '19.0.1.0.0',
    'summary': 'Truth website, native ordering, reservations and kitchen/bar displays',
    'author': 'Spxcorp Limited',
    'license': 'LGPL-3',
    'category': 'Point of Sale',
    'depends': ['website_sale', 'website_event', 'pos_restaurant', 'sale_stock', 'purchase_stock', 'mail'],
    'data': ['security/security.xml', 'security/ir.model.access.csv', 'views/backend.xml', 'views/website.xml'],
    'assets': {
        'web.assets_frontend': ['truth_lounge/static/src/css/website.css'],
    },
    'application': True,
    'installable': True,
}
