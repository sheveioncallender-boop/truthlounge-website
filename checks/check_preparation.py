"""Isolated execution tests for preparation logic without an Odoo database.

The actual module code is loaded against tiny ORM stand-ins. This checks
idempotency, amendments and isolation; it does not replace Odoo integration QA.
"""
import importlib.util
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path

class Error(Exception):
    pass

class FakeFields:
    class Datetime:
        def __new__(cls, *args, **kwargs):
            return None

        @staticmethod
        def now():
            return datetime.now()

    def __getattr__(self, name):
        return lambda *args, **kwargs: None

sys.modules['odoo'] = types.SimpleNamespace(api=types.SimpleNamespace(model=lambda f: f),
    fields=FakeFields(), models=types.SimpleNamespace(Model=object, Constraint=lambda *a: None))
sys.modules['odoo.exceptions'] = types.SimpleNamespace(AccessError=Error, UserError=Error)
spec = importlib.util.spec_from_file_location('truth_kitchen_tested', Path(__file__).parents[1] / 'truth_kitchen_display/models/kitchen.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class Records(list):
    def filtered(self, fn):
        return Records(t for t in self if fn(t))

class Ticket:
    def __init__(self, values):
        self.stage='new'
        self.revision=1
        self.amended=False
        self.cancellation_reason=False
        self.write(values)

    def write(self, values):
        for key, value in values.items():
            if key == 'product_id':
                value = types.SimpleNamespace(id=value)
            # Real Odoo represents empty Char/Text values as False.
            setattr(self, key, False if value == '' else value)

    def __getitem__(self, key):
        return getattr(self, key)

class Store:
    def __init__(self):
        self.tickets=Records()
        self.env=types.SimpleNamespace(cr=types.SimpleNamespace(execute=lambda *a: None))

    def sudo(self):
        return self

    def with_company(self, company):
        return self

    def search(self, domain):
        return Records(t for t in self.tickets if all(getattr(t,key,None)==value for key,operator,value in domain if operator=='='))

    def create(self, values):
        ticket=Ticket(values)
        self.tickets.append(ticket)
        return ticket

class TestMirror(unittest.TestCase):
    def setUp(self):
        self.store=Store()
        self.order=types.SimpleNamespace(id=1, company_id=types.SimpleNamespace(id=1), name='SO001', truth_order_note='', state='sale')
        self.food=types.SimpleNamespace(id=10, display_name='Food', product_tmpl_id=types.SimpleNamespace(truth_station='kitchen'))
        self.drink=types.SimpleNamespace(id=20, display_name='Drink', product_tmpl_id=types.SimpleNamespace(truth_station='bar'))
        self.lines=[types.SimpleNamespace(id=100, product_id=self.food, product_uom_qty=1, name=''), types.SimpleNamespace(id=200, product_id=self.drink, product_uom_qty=1, name='')]

    def sync(self):
        module.TruthTicket._reconcile(self.store, self.order, 'sale', self.lines)
        # Many2one equality in real Odoo compares IDs on records of the same model.
        for ticket in self.store.tickets:
            ticket.product_id = self.food if ticket.product_id.id==10 else self.drink

    def test_repeat_poll_does_not_reopen_blank_note_items(self):
        self.sync()
        self.store.tickets[0].stage='ready'
        self.sync()
        self.assertEqual(len(self.store.tickets), 2)
        self.assertEqual(self.store.tickets[0].stage, 'ready')
        self.assertEqual(self.store.tickets[0].revision, 1)

    def test_amendment_reopens_only_affected_station(self):
        self.sync()
        for ticket in self.store.tickets:
            ticket.stage='completed'
        self.lines[0].product_uom_qty=2
        self.sync()
        self.assertEqual(self.store.tickets[0].stage, 'new')
        self.assertEqual(self.store.tickets[0].quantity, 2)
        self.assertTrue(self.store.tickets[0].amended)
        self.assertEqual(self.store.tickets[1].stage, 'completed')
        self.assertEqual(self.order.state, 'sale')

    def test_removed_item_closes_display_only(self):
        self.sync()
        self.lines.pop()
        self.sync()
        self.assertEqual(self.store.tickets[1].stage, 'cancelled')
        self.assertEqual(self.order.state, 'sale')

    def test_negative_refund_line_does_not_request_preparation(self):
        self.lines[0].product_uom_qty=-1
        self.sync()
        self.assertEqual(len(self.store.tickets), 1)
        self.assertEqual(self.store.tickets[0].station, 'bar')

    def test_unrouted_fee_does_not_request_preparation(self):
        self.food.product_tmpl_id.truth_station=False
        self.sync()
        self.assertEqual(len(self.store.tickets), 1)

if __name__ == '__main__':
    unittest.main(verbosity=2)
