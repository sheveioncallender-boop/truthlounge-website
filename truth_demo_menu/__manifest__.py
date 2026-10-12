{
    'name': 'Truth Demo Menu',
    'version': '19.0.1.1.0',
    'summary': 'Optional sample food and drinks for testing Truth website, POS and preparation screens',
    'description': 'Installs six published demo products with illustrative photos and sample prices. Not the verified Truth menu. Products use the installing company currency and default taxes.',
    'author': 'Spxcorp Limited', 'license': 'LGPL-3', 'category': 'Sales/Point of Sale',
    'depends': ['truth_lounge', 'truth_kitchen_display'],
    'data': ['views/menu.xml', 'data/pos_setup.xml'],
    'post_init_hook': 'post_init_hook',
    'application': True, 'installable': True,
}
