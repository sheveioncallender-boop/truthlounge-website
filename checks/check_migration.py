"""Exercise the real ownership-transfer SQL on a small in-memory metadata fixture.

This is not an Odoo/PostgreSQL install test; it checks migration scope and identity.
"""
import importlib.util
import sqlite3
import types
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('truth_hooks', Path(__file__).parents[1] / 'truth_kitchen_display/hooks.py')
hooks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hooks)


class Cursor:
    def __init__(self, db):
        self.db = db

    def execute(self, sql, params=()):
        # Expand psycopg's tuple adaptation for SQLite's equivalent IN expression.
        args = []
        for value in params:
            if isinstance(value, tuple):
                sql = sql.replace('%s', '(' + ','.join('?' for _ in value) + ')', 1)
                args.extend(value)
            else:
                sql = sql.replace('%s', '?', 1)
                args.append(value)
        self.result = self.db.execute(sql, args)

    def fetchall(self):
        return self.result.fetchall()

    def fetchone(self):
        return self.result.fetchone()


class TestOwnershipTransfer(unittest.TestCase):
    def test_ticket_identity_and_website_ownership_survive(self):
        db = sqlite3.connect(':memory:')
        db.executescript('''
            CREATE TABLE ir_module_module (id INTEGER, name TEXT);
            INSERT INTO ir_module_module VALUES (1,'truth_lounge'),(2,'truth_kitchen_display');
            CREATE TABLE ir_model (id INTEGER, model TEXT);
            INSERT INTO ir_model VALUES (10,'truth.ticket'),(11,'truth.booking');
            CREATE TABLE ir_model_fields (id INTEGER, model TEXT, name TEXT);
            INSERT INTO ir_model_fields VALUES (20,'truth.ticket','stage'),(21,'product.template','truth_station'),
                (22,'website','truth_enabled'),(23,'sale.order','truth_order_note');
            CREATE TABLE ir_model_fields_selection (id INTEGER, field_id INTEGER);
            INSERT INTO ir_model_fields_selection VALUES (30,20),(31,21);
            CREATE TABLE ir_model_constraint (id INTEGER, model INTEGER, module INTEGER);
            INSERT INTO ir_model_constraint VALUES (40,10,1),(41,11,1);
            CREATE TABLE ir_model_relation (id INTEGER, model INTEGER, module INTEGER);
            INSERT INTO ir_model_relation VALUES (50,10,1);
            CREATE TABLE ir_model_data (id INTEGER PRIMARY KEY, module TEXT, name TEXT, model TEXT, res_id INTEGER);
            CREATE TABLE truth_ticket (id INTEGER, source_key TEXT, stage TEXT, revision INTEGER);
            INSERT INTO truth_ticket VALUES (7,'pos:1:2:kitchen','ready',4);
        ''')
        rows = [('model_truth_ticket','ir.model',10),('model_truth_booking','ir.model',11),
            ('field_truth_ticket__stage','ir.model.fields',20),('field_product_template__truth_station','ir.model.fields',21),
            ('field_website__truth_enabled','ir.model.fields',22),('field_sale_order__truth_order_note','ir.model.fields',23),
            ('selection__truth_ticket__stage__ready','ir.model.fields.selection',30),
            ('selection__product_template__truth_station__bar','ir.model.fields.selection',31),
            ('constraint_truth_ticket_source_unique','ir.model.constraint',40),
            ('relation_truth_ticket','ir.model.relation',50),('group_manager','res.groups',60),
            ('menu_truth','ir.ui.menu',70),('website_form','ir.ui.view',80)]
        db.executemany('INSERT INTO ir_model_data(module,name,model,res_id) VALUES (?,?,?,?)', [('truth_lounge', *r) for r in rows])
        env = types.SimpleNamespace(cr=Cursor(db), invalidate_all=lambda: None, registry=types.SimpleNamespace(clear_cache=lambda: None))
        hooks.pre_init_hook(env)
        ownership = dict(db.execute('SELECT name,module FROM ir_model_data'))
        for name, _, _ in rows:
            expected = 'truth_lounge' if name in {'model_truth_booking','field_website__truth_enabled','website_form'} else 'truth_kitchen_display'
            self.assertEqual(ownership[name], expected, name)
        self.assertEqual(db.execute('SELECT * FROM truth_ticket').fetchall(), [(7,'pos:1:2:kitchen','ready',4)])
        self.assertEqual(db.execute('SELECT module FROM ir_model_constraint ORDER BY id').fetchall(), [(2,),(1,)])
        self.assertEqual(db.execute('SELECT module FROM ir_model_relation').fetchone(), (2,))
        # A second invocation is a no-op.
        hooks.pre_init_hook(env)
        self.assertEqual(dict(db.execute('SELECT name,module FROM ir_model_data')), ownership)


if __name__ == '__main__':
    unittest.main(verbosity=2)
