from odoo import api, Command, models
from .catalog import PRODUCTS


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _truth_enable_demo_pos_products(self):
        """Repair only the module's six sample products, without recreating them."""
        products = self.sudo().browse()
        for item in PRODUCTS:
            product = self.env.ref('truth_demo_menu.product_' + item['key'], raise_if_not_found=False)
            if product and product.exists():
                products |= product.sudo()
        pending = products.filtered(lambda p: not p.active or not p.sale_ok or not p.available_in_pos)
        if pending:
            pending.write({'active': True, 'sale_ok': True, 'available_in_pos': True})
        # Add demo categories to existing restricted POS menus in the same company.
        # Retain every category already selected and keep native category restrictions enabled.
        for company in products.company_id:
            categories = products.filtered(lambda p: p.company_id == company).pos_categ_ids
            configs = self.env['pos.config'].sudo().search([
                ('company_id', '=', company.id), ('limit_categories', '=', True)])
            for config in configs:
                missing = categories - config.iface_available_categ_ids
                if missing:
                    config.write({'iface_available_categ_ids': [Command.link(cat.id) for cat in missing]})
        return True
