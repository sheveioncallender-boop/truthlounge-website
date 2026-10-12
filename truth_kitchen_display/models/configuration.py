from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    truth_station = fields.Selection([('kitchen', 'Kitchen'), ('bar', 'Bar')], string='Truth preparation station',
        help='Leave empty for items that do not need preparation. Used for both POS and confirmed website sales.')


class PosConfig(models.Model):
    _inherit = 'pos.config'
    truth_kds_enabled = fields.Boolean('Enable Truth kitchen/bar display', default=False)


class TruthDisplay(models.Model):
    _name = 'truth.display'
    _description = 'Truth Preparation Display Configuration'
    _order = 'name, id'
    _check_company_auto = True

    name = fields.Char(required=True, default='Kitchen & Bar')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    pos_config_ids = fields.Many2many('pos.config', string='Point of Sale', check_company=True,
        help='Only saved orders from these registers appear. Select at least one register for POS orders.')
    category_ids = fields.Many2many('pos.category', string='POS categories',
        help='Leave empty for all categories. Applies to both POS and website products.')
    station = fields.Selection([('all', 'Kitchen & Bar'), ('kitchen', 'Kitchen'), ('bar', 'Bar')], required=True, default='all')
    include_website_orders = fields.Boolean('Include confirmed website orders', default=False,
        help='Requires the native eCommerce app. Includes confirmed orders from websites in this company.')
    refresh_seconds = fields.Integer(default=5)
    late_minutes = fields.Integer('Highlight after (minutes)', default=15)
    closed_minutes = fields.Integer('Keep closed items (minutes)', default=30)
    show_images = fields.Boolean('Product images', default=True)
    sound_enabled = fields.Boolean('Offer sound alerts', default=True)
    sound_volume = fields.Integer('Default volume (%)', default=60)
    repeat_seconds = fields.Integer('Repeat new-item alert (seconds)', default=20,
        help='Set to zero to alert only when a new or amended item arrives. Browsers require Enable sound once.')
    label_new = fields.Char(required=True, default='New')
    label_acknowledged = fields.Char(required=True, default='Acknowledged')
    label_preparing = fields.Char(required=True, default='Preparing')
    label_ready = fields.Char(required=True, default='Ready')
    label_completed = fields.Char(required=True, default='Completed')

    @api.constrains('refresh_seconds', 'late_minutes', 'closed_minutes', 'sound_volume', 'repeat_seconds')
    def _check_settings(self):
        for record in self:
            if not 2 <= record.refresh_seconds <= 60 or not 1 <= record.late_minutes <= 240:
                raise ValidationError('Refresh must be 2–60 seconds and late highlighting 1–240 minutes.')
            if not 1 <= record.closed_minutes <= 1440 or not 0 <= record.sound_volume <= 100 or not 0 <= record.repeat_seconds <= 3600:
                raise ValidationError('Closed retention must be 1–1440 minutes, volume 0–100, and repeat 0–3600 seconds.')

    def action_open_display(self):
        self.ensure_one()
        self.check_access('read')
        return {'type': 'ir.actions.act_url', 'url': '/truth/kitchen/%s' % self.id, 'target': 'new'}

    def _ticket_domain(self):
        self.ensure_one()
        domain = [('company_id', '=', self.company_id.id), '|',
                  ('pos_order_id.config_id', 'in', self.pos_config_ids.ids),
                  ('sale_order_id', '!=', False) if self.include_website_orders else ('id', '=', 0)]
        if self.station != 'all':
            domain.append(('station', '=', self.station))
        if self.category_ids:
            domain.append(('product_id.pos_categ_ids', 'in', self.category_ids.ids))
        return domain

    def _client_settings(self):
        self.ensure_one()
        return {'id': self.id, 'name': self.name, 'station': self.station,
            'refreshSeconds': self.refresh_seconds, 'lateMinutes': self.late_minutes,
            'showImages': self.show_images, 'soundEnabled': self.sound_enabled,
            'volume': self.sound_volume, 'repeatSeconds': self.repeat_seconds,
            'stages': [(code, self['label_' + code]) for code in ('new', 'acknowledged', 'preparing', 'ready', 'completed')] + [('cancelled', 'Dismissed')]}
