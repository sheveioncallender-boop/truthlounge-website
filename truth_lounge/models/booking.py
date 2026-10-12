from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TruthBooking(models.Model):
    _name = 'truth.booking'
    _description = 'Truth Reservation Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'requested_at desc, id desc'

    name = fields.Char('Guest name', required=True, tracking=True)
    email = fields.Char(required=True)
    phone = fields.Char(required=True)
    kind = fields.Selection([('table', 'Table reservation'), ('event', 'Private event')], default='table', required=True)
    requested_at = fields.Datetime(required=True)
    guests = fields.Integer(default=2, required=True)
    note = fields.Text()
    website_id = fields.Many2one('website', required=True)
    company_id = fields.Many2one(related='website_id.company_id', store=True, index=True)
    state = fields.Selection([('new', 'New'), ('contacted', 'Contacted'), ('confirmed', 'Confirmed'), ('cancelled', 'Cancelled')], default='new', required=True, tracking=True)
    assigned_to = fields.Many2one('res.users', tracking=True)

    @api.constrains('guests')
    def _check_guests(self):
        if any(not 1 <= b.guests <= 500 for b in self):
            raise ValidationError('Guest count must be between 1 and 500.')
