import re
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from odoo import fields, http
from odoo.exceptions import UserError
from odoo.http import request


class TruthWebsite(http.Controller):
    def _page(self, template, **values):
        if not request.website.truth_enabled:
            return request.not_found()
        return request.render('truth_lounge.' + template, values)

    @http.route('/truth', type='http', auth='public', website=True, sitemap=True)
    def home(self, **kwargs):
        products = request.env['product.template'].search(request.website.sale_product_domain() + [('truth_station', '!=', False)], limit=4)
        return self._page('home', products=products)

    @http.route('/truth/about', type='http', auth='public', website=True, sitemap=True)
    def about(self, **kwargs):
        return self._page('about')

    @http.route('/truth/private-events', type='http', auth='public', website=True, sitemap=True)
    def events(self, **kwargs):
        return self._page('private_events')

    @http.route('/truth/gallery', type='http', auth='public', website=True, sitemap=True)
    def gallery(self, **kwargs):
        photos = request.env['truth.gallery'].sudo().search([('website_id', '=', request.website.id), ('published', '=', True)])
        return self._page('gallery', photos=photos)

    @http.route('/truth/photo/<int:photo_id>', type='http', auth='public', website=True)
    def photo(self, photo_id, **kwargs):
        record = request.env['truth.gallery'].sudo().search([('id', '=', photo_id), ('website_id', '=', request.website.id), ('published', '=', True)], limit=1)
        if not record or not request.website.truth_enabled:
            return request.not_found()
        return request.env['ir.binary']._get_stream_from(record, 'image').get_response()

    @http.route('/truth/visit', type='http', auth='public', website=True, sitemap=True)
    def visit(self, **kwargs):
        return self._page('visit')

    @http.route('/truth/reserve', type='http', auth='public', website=True, sitemap=True, methods=['GET'])
    def reserve(self, **kwargs):
        return self._page('reserve', error=False, values={}, submitted=False)

    @http.route('/truth/reserve/submit', type='http', auth='public', website=True, methods=['POST'])
    def submit(self, **post):
        if not request.website.truth_enabled:
            return request.not_found()
        clean = lambda key, limit: str(post.get(key, '')).strip()[:limit]
        values = {k: clean(k, n) for k, n in [('name', 120), ('email', 180), ('phone', 40), ('note', 2000), ('kind', 20), ('requested_at', 30), ('guests', 4)]}
        error = None
        if post.get('company_url'):
            return self._page('reserve', error=False, values={}, submitted=True)
        if time.time() - request.session.get('truth_booking_last', 0) < 30:
            error = 'Please wait a moment before sending another request.'
        try:
            local = datetime.fromisoformat(values['requested_at'])
            if local.tzinfo is not None:
                raise ValueError()
            requested = local.replace(tzinfo=ZoneInfo('America/Port_of_Spain')).astimezone(timezone.utc).replace(tzinfo=None)
            guests = int(values['guests'])
            if not 1 <= guests <= 500 or requested < fields.Datetime.now():
                raise ValueError()
        except (ValueError, TypeError):
            error = 'Choose a future date/time and a guest count between 1 and 500.'
        if len(values['name']) < 2 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', values['email']) or len(values['phone']) < 7:
            error = 'Enter your name, valid email, and phone number.'
        if values['kind'] not in ('table', 'event'):
            error = 'Choose a table reservation or private event.'
        if error:
            return self._page('reserve', error=error, values=values, submitted=False)
        request.env['truth.booking'].sudo().create({**{k: values[k] for k in ('name', 'email', 'phone', 'note', 'kind')},
            'website_id': request.website.id, 'requested_at': requested, 'guests': guests})
        request.session['truth_booking_last'] = time.time()
        return self._page('reserve', error=False, values={}, submitted=True)


class TruthKitchen(http.Controller):
    @staticmethod
    def _check():
        request.env['truth.ticket']._require_operator()

    @http.route('/truth/kitchen', type='http', auth='user', methods=['GET'])
    def kitchen(self, **kwargs):
        self._check()
        return request.render('truth_lounge.kitchen')

    @http.route('/truth/kitchen/data', type='jsonrpc', auth='user', methods=['POST'])
    def data(self, **kwargs):
        self._check()
        Ticket = request.env['truth.ticket']
        errors = Ticket._sync_sources()
        cutoff = fields.Datetime.now() - timedelta(minutes=30)
        tickets = Ticket.search([('company_id', 'in', request.env.companies.ids), '|', ('stage', 'not in', ['completed', 'cancelled']), ('write_date', '>=', cutoff)])
        return {'ok': True, 'syncErrors': errors, 'canCancel': request.env.user.has_group('truth_lounge.group_manager') or request.env.user.has_group('base.group_system'),
            'tickets': [{'id': t.id, 'reference': t.name, 'source': 'Website' if t.sale_order_id else 'POS',
                'station': t.station, 'product': t.product_name, 'qty': t.quantity, 'note': t.note or '',
                'table': t.table_name or 'Counter', 'stage': t.stage, 'revision': t.revision, 'amended': t.amended,
                'created': fields.Datetime.to_string(t.create_date), 'reason': t.cancellation_reason or '',
                'image': '/web/image/product.product/%s/image_128' % t.product_id.id if t.product_id else ''} for t in tickets]}

    @http.route('/truth/kitchen/step', type='jsonrpc', auth='user', methods=['POST'])
    def step(self, ticket_id=None, revision=None, cancel_reason=None, **kwargs):
        self._check()
        try:
            ticket_id, revision = int(ticket_id), int(revision)
        except (ValueError, TypeError):
            raise UserError('Invalid ticket.')
        ticket = request.env['truth.ticket'].search([('id', '=', ticket_id), ('company_id', 'in', request.env.companies.ids)], limit=1)
        if not ticket:
            raise UserError('Ticket not found.')
        ticket.action_step(revision, cancel_reason)
        return {'ok': True}
