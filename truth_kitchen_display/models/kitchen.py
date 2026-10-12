import logging
from datetime import timedelta
from odoo import api, fields, models

_logger = logging.getLogger(__name__)
from odoo.exceptions import AccessError, UserError

STAGES = [('new', 'New'), ('acknowledged', 'Acknowledged'), ('preparing', 'Preparing'),
          ('ready', 'Ready'), ('completed', 'Completed'), ('cancelled', 'Cancelled')]
NEXT = dict(zip([s[0] for s in STAGES[:4]], [s[0] for s in STAGES[1:5]]))


class TruthTicket(models.Model):
    _name = 'truth.ticket'
    _description = 'Truth Preparation Item'
    _inherit = ['mail.thread']
    _order = 'create_date, id'

    name = fields.Char(required=True, readonly=True)
    source_key = fields.Char(required=True, readonly=True, index=True)
    company_id = fields.Many2one('res.company', required=True, readonly=True, index=True)
    pos_order_id = fields.Many2one('pos.order', readonly=True, ondelete='set null')
    sale_order_id = fields.Many2one('sale.order', readonly=True, ondelete='set null')
    station = fields.Selection([('kitchen', 'Kitchen'), ('bar', 'Bar')], required=True, readonly=True, index=True)
    product_id = fields.Many2one('product.product', readonly=True, ondelete='set null')
    product_name = fields.Char(readonly=True)
    quantity = fields.Float(readonly=True)
    note = fields.Text(readonly=True)
    table_name = fields.Char(readonly=True)
    stage = fields.Selection(STAGES, default='new', required=True, tracking=True, index=True)
    revision = fields.Integer(default=1, readonly=True)
    amended = fields.Boolean(readonly=True)
    cancellation_reason = fields.Char(readonly=True, tracking=True)
    handled_by = fields.Many2one('res.users', readonly=True)
    handled_at = fields.Datetime(readonly=True)

    _source_unique = models.Constraint('UNIQUE(source_key)', 'This preparation item already exists.')

    def _require_operator(self):
        if not (self.env.user.has_group('truth_kitchen_display.group_operator') or self.env.user.has_group('base.group_system')):
            raise AccessError('You do not have access to the Truth preparation display.')
        self.check_access('read')
        if any(t.company_id not in self.env.companies for t in self):
            raise AccessError('This ticket belongs to another company.')

    def action_step(self, expected_revision, cancel_reason=None):
        self.ensure_one()
        self._require_operator()
        self.env.cr.execute('SELECT id FROM truth_ticket WHERE id = %s FOR UPDATE', [self.id])
        self.invalidate_recordset()
        if self.revision != expected_revision:
            raise UserError('This item changed on another screen. Refresh and try again.')
        if cancel_reason is not None:
            if not (self.env.user.has_group('truth_kitchen_display.group_manager') or self.env.user.has_group('base.group_system')):
                raise AccessError('A Truth manager must cancel preparation items.')
            reason = str(cancel_reason).strip()[:240]
            if not reason or self.stage in ('completed', 'cancelled'):
                raise UserError('Enter a reason for an active item.')
            values = {'stage': 'cancelled', 'cancellation_reason': reason}
        else:
            if self.stage not in NEXT:
                raise UserError('This item is already closed.')
            values = {'stage': NEXT[self.stage], 'amended': False}
        values.update(revision=self.revision + 1, handled_by=self.env.uid, handled_at=fields.Datetime.now())
        self.sudo().write(values)
        return True

    @api.model
    def _reconcile(self, order, source, lines):
        # Only called by the display poller; clients cannot call private ORM methods.
        # Serialize only display synchronization, never lock or write native order rows.
        self.env.cr.execute('SELECT pg_advisory_xact_lock(%s, %s)', [7901 if source == 'pos' else 7902, order.id])
        Ticket = self.sudo().with_company(order.company_id)
        field = 'pos_order_id' if source == 'pos' else 'sale_order_id'
        existing = Ticket.search([(field, '=', order.id)])
        by_key = {t.source_key: t for t in existing}
        current_keys = set()
        for line in lines:
            product = line.product_id
            station = product.product_tmpl_id.truth_station
            qty = line.qty if source == 'pos' else line.product_uom_qty
            if not station or qty <= 0:
                continue
            key = '%s:%s:%s:%s' % (source, order.id, line.id, station)
            current_keys.add(key)
            note = '\n'.join(filter(None, [
                (line.customer_note or '') if source == 'pos' else line.name,
                (order.general_customer_note or '') if source == 'pos' else order.truth_order_note,
            ]))
            values = {'name': (order.pos_reference if source == 'pos' else order.name) or str(order.id),
                'source_key': key, field: order.id, 'company_id': order.company_id.id,
                'station': station, 'product_id': product.id, 'product_name': product.display_name,
                'quantity': qty, 'note': note,
                'table_name': order.table_id.display_name if source == 'pos' and order.table_id else ('Counter' if source == 'pos' else 'Website')}
            ticket = by_key.get(key)
            if not ticket:
                Ticket.create(values)
            elif ticket.product_id != product or any((ticket[k] or '') != (values[k] or '') for k in ('quantity', 'note', 'product_name')):
                # Resurface amendments; never silently reuse an already-prepared ticket.
                values.update(stage='new', revision=ticket.revision + 1, amended=True, cancellation_reason=False)
                ticket.write(values)
            elif ticket.table_name != values['table_name']:
                ticket.write({'table_name': values['table_name'], 'revision': ticket.revision + 1})
        for ticket in existing.filtered(lambda t: t.source_key not in current_keys and t.stage not in ('cancelled', 'completed')):
            ticket.write({'stage': 'cancelled', 'cancellation_reason': 'Removed or reassigned in the source order',
                          'revision': ticket.revision + 1})

    @api.model
    def _cancel_source(self, order, source):
        field = 'pos_order_id' if source == 'pos' else 'sale_order_id'
        for ticket in self.sudo().search([(field, '=', order.id), ('stage', 'not in', ['cancelled', 'completed'])]):
            ticket.write({'stage': 'cancelled', 'cancellation_reason': 'Source order cancelled', 'revision': ticket.revision + 1})


    @api.model
    def _sync_sources(self, display):
        """Ohana-style polling: read native orders; write only display tickets.

        No POS, checkout, payment, stock or accounting lifecycle overrides.
        A failure here does not participate in the cashier's transaction.
        """
        self._require_operator()
        display.ensure_one()
        display.check_access('read')
        companies = [display.company_id.id]
        cutoff = fields.Datetime.now() - timedelta(days=2)
        Ticket = self.sudo()
        open_tickets = Ticket.search(display._ticket_domain() + [('stage', 'not in', ['completed', 'cancelled'])])
        POS = self.env['pos.order'].sudo()
        Sale = self.env['sale.order'].sudo()
        pos_orders = POS.search([('company_id', 'in', companies), ('config_id', 'in', display.pos_config_ids.ids), ('date_order', '>=', cutoff)])
        pos_orders |= open_tickets.pos_order_id
        sales = Sale.browse()
        if display.include_website_orders and 'website_id' in Sale._fields:
            sales = Sale.search([('company_id', 'in', companies), ('website_id', '!=', False), ('state', '=', 'sale'), ('date_order', '>=', cutoff)])
        sales |= open_tickets.sale_order_id
        errors = 0
        for source, orders in [('pos', pos_orders), ('sale', sales)]:
            for order in orders:
                try:
                    with self.env.cr.savepoint():
                        if order.state == 'cancel':
                            Ticket._cancel_source(order, source)
                        elif source == 'pos':
                            Ticket._reconcile(order, source, order.lines)
                        elif order.state == 'sale':
                            Ticket._reconcile(order, source, order.order_line.filtered(lambda l: not l.display_type))
                        else:
                            Ticket._cancel_source(order, source)
                except Exception:
                    errors += 1
                    _logger.exception('Truth display could not mirror %s order %s', source, order.id)
        for ticket in open_tickets.filtered(lambda t: not t.pos_order_id and not t.sale_order_id):
            ticket.write({'stage': 'cancelled', 'cancellation_reason': 'Source order removed', 'revision': ticket.revision + 1})
        return errors
