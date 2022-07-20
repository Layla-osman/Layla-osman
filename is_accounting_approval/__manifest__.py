#######################################################################
#    IntelliSoft Software                                             #
#    Copyright (C) 2017 (<http://intellisoft.sd>) all rights reserved.#
#######################################################################

{
    'name': 'QMSD IntelliSoft Accounting Approval',
    'author': 'IntelliSoft Software',
    'website': 'http://www.intellisoft.sd',
    'description': "A module that customizes the accounting module. Migrated to Odoo 15.",
    'depends': ['hr', 'account'],
    'category': 'Accounting',
    'data': [
        'security/security_view.xml',
        'security/ir.model.access.csv',
        'data/load.xml',
        'views/approval_sequence.xml',
        'views/res_users_view.xml',
        'views/res_currency_view.xml',
        'views/account_voucher_view.xml',
        'views/finance_approval_view.xml',
        'views/reports_registration.xml',
        'views/report_finance_approval.xml',
        'views/account_journal.xml',
        'views/finance_approval.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
