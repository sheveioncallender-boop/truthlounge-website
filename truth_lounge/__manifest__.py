{
    'name': 'Truth Website',
    'version': '19.0.2.1.0',
    'summary': 'Truth Lounge website, reservations and gallery with native Odoo commerce',
    'author': 'Spxcorp Limited', 'license': 'LGPL-3', 'category': 'Website',
    'depends': ['website_sale', 'website_event', 'mail'],
    'data': ['security/security.xml', 'security/ir.model.access.csv', 'views/backend.xml', 'views/website.xml', 'data/setup.xml'],
    'assets': {'web.assets_frontend': ['truth_lounge/static/src/css/website.css']},
    'application': True, 'installable': True,
}
