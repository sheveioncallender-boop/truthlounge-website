from datetime import timedelta
from odoo import fields, http
from odoo.exceptions import UserError
from odoo.http import request


class TruthKitchen(http.Controller):
    @staticmethod
    def _display(display_id):
        request.env['truth.ticket']._require_operator()
        try:
            display_id = int(display_id)
        except (TypeError, ValueError):
            raise UserError('Choose a display from Truth Kitchen Display → Displays.')
        display = request.env['truth.display'].search([
            ('id', '=', display_id), ('company_id', 'in', request.env.companies.ids)], limit=1)
        if not display:
            raise UserError('Display unavailable. Check your company selection and access.')
        return display

    @http.route('/truth/kitchen', type='http', auth='user', methods=['GET'])
    def kitchen_list(self, **kwargs):
        request.env['truth.ticket']._require_operator()
        action = request.env.ref('truth_kitchen_display.action_displays')
        return request.redirect('/odoo/action-%s' % action.id)

    @http.route('/truth/kitchen/<int:display_id>', type='http', auth='user', methods=['GET'])
    def kitchen(self, display_id, **kwargs):
        display = self._display(display_id)
        return request.render('truth_kitchen_display.kitchen', {'display': display,
            'configuration_url': '/odoo/action-%s/%s' % (request.env.ref('truth_kitchen_display.action_displays').id, display.id)})

    @http.route('/truth/kitchen/data', type='jsonrpc', auth='user', methods=['POST'])
    def data(self, display_id=None, **kwargs):
        display = self._display(display_id)
        Ticket = request.env['truth.ticket']
        errors = Ticket._sync_sources(display)
        cutoff = fields.Datetime.now() - timedelta(minutes=display.closed_minutes)
        tickets = Ticket.search(display._ticket_domain() + [
            '|', ('stage', 'not in', ['completed', 'cancelled']), ('write_date', '>=', cutoff)])
        return {'ok': True, 'syncErrors': errors, 'settings': display._client_settings(),
            'canCancel': request.env.user.has_group('truth_kitchen_display.group_manager') or request.env.user.has_group('base.group_system'),
            'tickets': [{'id': t.id, 'reference': t.name, 'source': 'Website' if t.sale_order_id else 'POS',
                'station': t.station, 'product': t.product_name, 'qty': t.quantity, 'note': t.note or '',
                'table': t.table_name or 'Counter', 'stage': t.stage, 'revision': t.revision, 'amended': t.amended,
                'created': fields.Datetime.to_string(t.create_date), 'reason': t.cancellation_reason or '',
                'image': '/web/image/product.product/%s/image_128' % t.product_id.id if t.product_id else ''} for t in tickets]}

    @http.route('/truth/kitchen/step', type='jsonrpc', auth='user', methods=['POST'])
    def step(self, display_id=None, ticket_id=None, revision=None, cancel_reason=None, **kwargs):
        display = self._display(display_id)
        try:
            ticket_id, revision = int(ticket_id), int(revision)
        except (ValueError, TypeError):
            raise UserError('Invalid ticket.')
        ticket = request.env['truth.ticket'].search(display._ticket_domain() + [('id', '=', ticket_id)], limit=1)
        if not ticket:
            raise UserError('Ticket not found on this display.')
        ticket.action_step(revision, cancel_reason)
        return {'ok': True}
