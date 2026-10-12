import base64
from markupsafe import escape
from odoo import Command, tools
from odoo.exceptions import UserError
from .catalog import PRODUCTS


def _record(env, key, model, values):
    """Keep stable external IDs and never reset products edited after installation."""
    existing = env.ref('truth_demo_menu.' + key, raise_if_not_found=False)
    if existing and existing.exists():
        return existing
    record = env[model].create(values)
    env['ir.model.data'].create({'module': 'truth_demo_menu', 'name': key,
        'model': model, 'res_id': record.id, 'noupdate': True})
    return record


def post_init_hook(env):
    company = env.company
    websites = env['website'].search([('truth_enabled', '=', True), ('company_id', '=', company.id)])
    if len(websites) != 1:
        raise UserError('Truth Demo Menu needs exactly one Truth-branded website in the active company. '
                        'Activate the intended website under Truth Website → Website Branding, then install this optional demo module.')
    website = websites
    env = env(context={**env.context, 'allowed_company_ids': [company.id], 'website_id': website.id})
    # Fail clearly instead of duplicating a manually created demo reference.
    for item in PRODUCTS:
        reference = 'TRUTH-DEMO-' + item['key'].upper()
        if not env.ref('truth_demo_menu.product_' + item['key'], raise_if_not_found=False):
            if env['product.template'].with_context(active_test=False).search_count([('default_code', '=', reference)]):
                raise UserError('A product already uses %s. Resolve that duplicate reference before installing the demo menu.' % reference)
    internal = _record(env, 'category_internal', 'product.category', {'name': 'Truth Demo Menu'})
    public, pos = {}, {}
    for station, name in [('kitchen', 'Food'), ('bar', 'Drinks')]:
        public[station] = _record(env, 'category_web_' + station, 'product.public.category', {
            'name': name, 'website_id': website.id})
        pos[station] = _record(env, 'category_pos_' + station, 'pos.category', {'name': 'Truth Demo · ' + name})
    for index, item in enumerate(PRODUCTS):
        with tools.file_open(item['image'], 'rb') as image:
            image_data = base64.b64encode(image.read())
        _record(env, 'product_' + item['key'], 'product.template', {
            'name': item['name'], 'default_code': 'TRUTH-DEMO-' + item['key'].upper(),
            'company_id': company.id, 'website_id': website.id, 'categ_id': internal.id,
            'type': 'consu', 'is_storable': False, 'sale_ok': True, 'purchase_ok': False,
            'list_price': item['price'], 'invoice_policy': 'order',
            'available_in_pos': True, 'is_published': True, 'website_sequence': 100 + index,
            'truth_station': item['station'], 'image_1920': image_data,
            'public_categ_ids': [Command.set(public[item['station']].ids)],
            'pos_categ_ids': [Command.set(pos[item['station']].ids)],
            'description': 'DEMO PRODUCT — illustrative menu, photo and price for testing. Not verified Truth menu data.',
            'description_sale': item['description'],
            'website_description': '<p>%s</p>' % escape(item['description']),
        })
    # No stock quantities, BOMs, taxes, fiscal positions, payments, orders or POS settings are changed.
