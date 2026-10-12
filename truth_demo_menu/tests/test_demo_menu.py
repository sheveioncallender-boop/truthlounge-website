from odoo.tests import TransactionCase, tagged
from ..catalog import PRODUCTS
from ..hooks import post_init_hook


@tagged('post_install', '-at_install')
class TestTruthDemoMenu(TransactionCase):
    def test_products_have_images_and_both_native_sales_channels(self):
        for item in PRODUCTS:
            product = self.env.ref('truth_demo_menu.product_' + item['key'])
            self.assertTrue(product.image_1920)
            self.assertTrue(product.is_published)
            self.assertTrue(product.available_in_pos)
            self.assertEqual(product.truth_station, item['station'])
            self.assertEqual(product.company_id, product.website_id.company_id)
            self.assertFalse(product.is_storable)
            self.assertTrue(product.public_categ_ids)
            self.assertTrue(product.pos_categ_ids)

    def test_repeat_setup_preserves_edited_product_and_no_duplicates(self):
        product = self.env.ref('truth_demo_menu.product_burger')
        product.write({'list_price': 71.0})
        records = self.env['product.template'].search([('default_code', '=like', 'TRUTH-DEMO-%')])
        post_init_hook(self.env)
        self.assertEqual(records, self.env['product.template'].search([('default_code', '=like', 'TRUTH-DEMO-%')]))
        self.assertEqual(product.list_price, 71.0)
