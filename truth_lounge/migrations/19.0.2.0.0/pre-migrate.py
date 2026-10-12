from odoo.exceptions import UserError


def migrate(cr, version):
    cr.execute("SELECT 1 FROM ir_model_data WHERE module = 'truth_lounge' AND name = 'model_truth_ticket'")
    if cr.fetchone():
        raise UserError('Install Truth Kitchen Display first, then upgrade Truth Website (truth_lounge). '
                        'Do not uninstall the original module: this order preserves preparation history and staff access.')
