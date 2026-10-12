from odoo import Command
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import AccessError, UserError


@tagged('post_install', '-at_install')
class TestTruthNativeFlow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['website'].create({'name': 'Truth Test', 'truth_enabled': True, 'company_id': cls.env.company.id})
        cls.partner = cls.env['res.partner'].create({'name': 'Truth Test Guest'})
        cls.food = cls.env['product.product'].create({'name': 'Test food', 'type': 'service', 'list_price': 40, 'truth_station': 'kitchen'})
        cls.drink = cls.env['product.product'].create({'name': 'Test drink', 'type': 'service', 'list_price': 20, 'truth_station': 'bar'})

    def _order(self):
        return self.env['sale.order'].create({'partner_id': self.partner.id, 'website_id': self.website.id,
            'order_line': [Command.create({'product_id': p.id, 'product_uom_qty': 1}) for p in (self.food, self.drink)]})

    def _tickets(self, order):
        return self.env['truth.ticket'].search([('sale_order_id', '=', order.id)])

    def test_draft_not_sent_and_confirmation_is_native(self):
        order = self._order()
        self.env['truth.ticket']._sync_sources()
        self.assertFalse(self._tickets(order))
        order.action_confirm()
        # No order hook creates preparation records during checkout/confirmation.
        self.assertFalse(self._tickets(order))
        self.env['truth.ticket']._sync_sources()
        self.assertEqual(len(self._tickets(order)), 2)

    def test_poll_is_idempotent_and_stations_are_independent(self):
        order = self._order()
        order.action_confirm()
        Ticket = self.env['truth.ticket']
        Ticket._sync_sources()
        first = self._tickets(order)
        original = [(t.id, t.revision, t.stage) for t in first]
        Ticket._sync_sources()
        self.assertEqual(original, [(t.id, t.revision, t.stage) for t in self._tickets(order)])
        food = first.filtered(lambda t: t.station == 'kitchen')
        drink = first.filtered(lambda t: t.station == 'bar')
        before = (order.state, order.amount_total, order.invoice_status, order.write_date)
        drink.action_step(drink.revision)
        self.assertEqual(food.stage, 'new')
        self.assertEqual(drink.stage, 'acknowledged')
        self.assertEqual(before, (order.state, order.amount_total, order.invoice_status, order.write_date))

    def test_amendment_reopens_completed_preparation(self):
        order = self._order()
        order.action_confirm()
        Ticket = self.env['truth.ticket']
        Ticket._sync_sources()
        ticket = self._tickets(order).filtered(lambda t: t.station == 'kitchen')
        for _ in range(4):
            ticket.action_step(ticket.revision)
        self.assertEqual(ticket.stage, 'completed')
        order.order_line.filtered(lambda l: l.product_id == self.food).product_uom_qty = 2
        Ticket._sync_sources()
        self.assertEqual(ticket.stage, 'new')
        self.assertEqual(ticket.quantity, 2)
        self.assertTrue(ticket.amended)

    def test_stale_screen_cannot_advance_twice(self):
        order = self._order()
        order.action_confirm()
        self.env['truth.ticket']._sync_sources()
        ticket = self._tickets(order)[:1]
        revision = ticket.revision
        ticket.action_step(revision)
        with self.assertRaises(UserError):
            ticket.action_step(revision)

    def test_public_user_cannot_read_or_change_preparation(self):
        order = self._order()
        order.action_confirm()
        self.env['truth.ticket']._sync_sources()
        ticket = self._tickets(order)[:1]
        with self.assertRaises(AccessError):
            ticket.with_user(self.env.ref('base.public_user')).action_step(ticket.revision)

    def test_dismiss_does_not_cancel_source_order(self):
        order = self._order()
        order.action_confirm()
        self.env['truth.ticket']._sync_sources()
        ticket = self._tickets(order)[:1]
        ticket.action_step(ticket.revision, 'Kitchen review required')
        self.assertEqual(ticket.stage, 'cancelled')
        self.assertEqual(order.state, 'sale')
