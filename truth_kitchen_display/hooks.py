"""Move ownership, not business records, from the original combined addon."""
LEGACY_IDS = {
    'model_inherit__truth_ticket__mail_thread',
    'category_truth', 'privilege_truth', 'group_operator', 'group_manager',
    'ticket_company', 'ticket_user', 'ticket_manager', 'ticket_admin',
    'product_form', 'pos_form', 'ticket_list', 'ticket_form', 'action_tickets',
    'action_kitchen', 'menu_truth', 'menu_display', 'menu_tickets', 'menu_products', 'kitchen',
}


def pre_init_hook(env):
    cr = env.cr
    cr.execute("""
        SELECT d.id, d.name FROM ir_model_data d
        WHERE d.module = 'truth_lounge' AND (
            d.name IN %s
            OR (d.model = 'ir.model.constraint' AND d.res_id IN (
                SELECT c.id FROM ir_model_constraint c JOIN ir_model m ON m.id = c.model WHERE m.model = 'truth.ticket'))
            OR (d.model = 'ir.model.relation' AND d.res_id IN (
                SELECT r.id FROM ir_model_relation r JOIN ir_model m ON m.id = r.model WHERE m.model = 'truth.ticket'))
            OR (d.model = 'ir.model' AND d.res_id IN (SELECT id FROM ir_model WHERE model = 'truth.ticket'))
            OR (d.model = 'ir.model.fields' AND d.res_id IN (
                SELECT id FROM ir_model_fields WHERE model = 'truth.ticket'
                OR (model IN ('product.template', 'product.product') AND name = 'truth_station')
                OR (model = 'pos.config' AND name = 'truth_kds_enabled')
                OR (model = 'sale.order' AND name = 'truth_order_note')))
            OR (d.model = 'ir.model.fields.selection' AND d.res_id IN (
                SELECT s.id FROM ir_model_fields_selection s JOIN ir_model_fields f ON f.id = s.field_id
                WHERE f.model = 'truth.ticket' OR (f.model IN ('product.template', 'product.product') AND f.name = 'truth_station')))
        )
    """, [tuple(LEGACY_IDS)])
    for record_id, name in cr.fetchall():
        cr.execute("SELECT id FROM ir_model_data WHERE module = 'truth_kitchen_display' AND name = %s", [name])
        if cr.fetchone():
            from odoo.exceptions import UserError
            raise UserError('Duplicate Truth migration identifier: %s. Contact the module maintainer before upgrading.' % name)
        cr.execute("UPDATE ir_model_data SET module = 'truth_kitchen_display' WHERE id = %s", [record_id])
    # Preserve ownership of ticket table constraints and mail-thread relations.
    for table in ('ir_model_constraint', 'ir_model_relation'):
        cr.execute(f"""UPDATE {table} SET module = (SELECT id FROM ir_module_module WHERE name = 'truth_kitchen_display')
            WHERE module = (SELECT id FROM ir_module_module WHERE name = 'truth_lounge')
            AND model IN (SELECT id FROM ir_model WHERE model = 'truth.ticket')""")
    env.invalidate_all()
    env.registry.clear_cache()


def post_init_hook(env):
    Display = env['truth.display'].sudo()
    # Preserve a previously enabled POS setup; new installations explicitly choose registers.
    configs = env['pos.config'].sudo().search([('truth_kds_enabled', '=', True)])
    companies = configs.company_id | env['truth.ticket'].sudo().search([]).company_id | env.company
    for company in companies:
        if Display.search_count([('company_id', '=', company.id)]):
            continue
        Display.create({'name': 'Truth Kitchen & Bar', 'company_id': company.id,
            'pos_config_ids': [(6, 0, configs.filtered(lambda c: c.company_id == company).ids)],
            'include_website_orders': bool(env['truth.ticket'].sudo().search_count([
                ('company_id', '=', company.id), ('sale_order_id', '!=', False)]))})
