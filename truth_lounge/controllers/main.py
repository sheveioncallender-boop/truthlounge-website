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
        products = request.env['product.template'].search(request.website.sale_product_domain() + [('is_published', '=', True)], limit=4)
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
