#######################################################################
#    IntelliSoft Software                                             #
#    Copyright (C) 2017 (<http://intellisoft.sd>) all rights reserved.#
#######################################################################

{
    'name': 'QMSD Custody Clearance',
    'author': 'IntelliSoft Software',
    'website': 'http://www.intellisoft.sd',
    'description': "A module that allows for custody clearance. Migrated to Odoo 13.",
    'depends': ['account', 'is_accounting_approval','hr'],
    'category': 'Accounting',
    'data': [
        'security/security_view.xml',
        'security/ir.model.access.csv',
        'views/clearance_sequence.xml',
        'views/clearance_approval_view.xml',
        'views/report_clearance_approval.xml',
        'views/reports_registration.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
