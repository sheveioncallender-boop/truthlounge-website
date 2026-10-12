"""Validate packaging, local XML IDs and the boundary between the two apps."""
import ast
import csv
from pathlib import Path
from lxml import etree

ROOT = Path(__file__).parents[1]
modules = ['truth_lounge', 'truth_kitchen_display', 'truth_demo_menu']
ids = set()
references = []
for module in modules:
    folder = ROOT / module
    manifest = ast.literal_eval((folder / '__manifest__.py').read_text())
    if module != 'truth_demo_menu':
        assert not set(modules) & set(manifest['depends']), 'The two main apps must be independent'
    if module == 'truth_lounge':
        assert not any(x in manifest['depends'] for x in ['pos_restaurant', 'point_of_sale'])
    for path in folder.rglob('*.py'):
        ast.parse(path.read_text(), str(path))
        if path.parent.name in {'models', 'controllers'}:
            tree = ast.parse(path.read_text())
            assert not any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in {
                'action_confirm', '_process_order', 'sync_from_ui', 'action_pos_order_paid', '_action_done'
            } for n in ast.walk(tree)), f'Native-flow override found: {path}'
    for filename in manifest['data']:
        path = folder / filename
        assert path.is_file(), path
        if path.suffix == '.xml':
            tree = etree.parse(str(path))
            for el in tree.xpath('//record[@id] | //template[@id] | //menuitem[@id]'):
                ids.add(f"{module}.{el.get('id')}")
            for el in tree.iter():
                for attr in ['ref', 'parent', 'action', 'inherit_id']:
                    if attr == 'action' and el.tag != 'menuitem':
                        continue
                    ref = el.get(attr)
                    if ref:
                        references.append(ref if '.' in ref else module + '.' + ref)
        else:
            for row in csv.DictReader(path.open()):
                for key, value in row.items():
                    if key.endswith(':id') and value and not value.startswith('model_'):
                        references.append(value if '.' in value else module + '.' + value)
    for assets in manifest.get('assets', {}).values():
        for asset in assets:
            assert (ROOT / asset).is_file(), asset
for ref in references:
    if ref.split('.')[0] in modules and not ref.split('.')[-1].startswith('model_'):
        assert ref in ids, f'Missing XML ID: {ref}'
website_code = '\n'.join(p.read_text() for p in (ROOT / 'truth_lounge').rglob('*')
                         if p.suffix in {'.py', '.xml'} and 'migrations' not in p.parts)
assert 'product.truth_station' not in website_code
assert "_inherit = 'pos.config'" not in website_code
assert 'class TruthTicket' not in website_code
assert (ROOT / 'truth_lounge/static/src/img/truth-brand.jpg').read_bytes() == (ROOT / 'truth_kitchen_display/static/src/img/truth-brand.jpg').read_bytes()
print('PASS: packaging, XML references, Python syntax, independent apps and native-flow boundaries')
