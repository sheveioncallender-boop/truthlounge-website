import base64
from odoo import api, Command, fields, models, tools


class Website(models.Model):
    _inherit = 'website'

    truth_enabled = fields.Boolean('Truth Lounge branding')
    truth_phone = fields.Char('Truth contact number')
    truth_hours = fields.Text('Opening hours')
    truth_address = fields.Char(default='Corner Ariapita Avenue & Belle Smythe Street, Woodbrook, Port of Spain')
    truth_menu_ids = fields.One2many('website.menu', 'truth_website_id')

    def action_setup_truth(self):
        self.ensure_one()
        
        if not self.env.user.has_group('base.group_system'):
            from odoo.exceptions import AccessError
            raise AccessError('Only an administrator may activate website branding.')
        with tools.file_open('truth_lounge/static/src/img/truth-brand.jpg', 'rb') as image:
            logo = base64.b64encode(image.read())
        self.write({
            'truth_enabled': True, 'name': 'Truth Lounge & Restaurant', 'homepage_url': '/truth', 'logo': logo,
            'social_instagram': 'https://www.instagram.com/truthlounge._/',
            'social_facebook': 'https://www.facebook.com/p/TRUTH-Bar-Lounge-61575626877280/',
        })
        entries = [('Home', '/truth'), ('Our Story', '/truth/about'), ('Food & Drinks', '/shop'),
                   ("What’s On", '/event'), ('Private Events', '/truth/private-events'),
                   ('Gallery', '/truth/gallery'), ('Visit', '/truth/visit'), ('Book a Table', '/truth/reserve')]
        # Reuse the native homepage entry when present; keep other existing menus intact.
        home_menu = self.env['website.menu'].search([('website_id', '=', self.id), ('url', '=', '/')], limit=1)
        if home_menu:
            home_menu.write({'url': '/truth'})
        for sequence, (name, url) in enumerate(entries, 10):
            if not self.env['website.menu'].search_count([('website_id', '=', self.id), ('url', '=', url)]):
                self.env['website.menu'].create({'name': name, 'url': url, 'sequence': sequence,
                    'website_id': self.id, 'parent_id': self.menu_id.id, 'truth_website_id': self.id})
        return {'type': 'ir.actions.act_url', 'url': '/truth', 'target': 'self'}


    @api.model
    def _setup_truth_defaults(self):
        """Activate on single-site installs/upgrades; don't guess on multi-site databases."""
        websites = self.sudo().search([])
        target = websites.filtered('truth_enabled')
        if not target and len(websites) == 1:
            target = websites
        for website in target:
            # One-time activation also repairs the original release's missing homepage/logo.
            key = 'truth_lounge.branding_v2.%s' % website.id
            if not self.env['ir.config_parameter'].sudo().get_param(key):
                website.action_setup_truth()
                self.env['ir.config_parameter'].sudo().set_param(key, '1')
        old_managers = self.env.ref('truth_kitchen_display.group_manager', raise_if_not_found=False)
        if old_managers:
            self.env.ref('truth_lounge.group_website_manager').sudo().write({
                'user_ids': [Command.link(user.id) for user in old_managers.all_user_ids]})


class WebsiteMenu(models.Model):
    _inherit = 'website.menu'
    truth_website_id = fields.Many2one('website', ondelete='cascade')


class TruthGallery(models.Model):
    _name = 'truth.gallery'
    _description = 'Truth Gallery Photo'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    image = fields.Image(required=True, max_width=1920, max_height=1920)
    website_id = fields.Many2one('website', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='website_id.company_id', store=True)
    published = fields.Boolean(default=False)
