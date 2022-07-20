# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

{
    'name': "Overtime",

    'summary': """
       Calculate and Manage Employee Overtime""",

    'description': """
        Calculate and Manage Employee Overtime
    """,

    'author': "IATL Intellisoft International",
    'website': "http://www.iatl-intellisoft.com",
    'category': 'Generic Modules/Human Resources',
    'version': '15.0.1.0.0',
    'depends': ['hr', 'hr_payroll', 'hr_contract'],
    'data': [
        'security/security_view.xml',
        'security/ir.model.access.csv',
        # 'data/hr_overtime_data.xml',
        'views/hr_conflunce_overtime_view.xml',

    ],
    'images': ['static/description/icon.png'],
    'application': True,
    'auto_install': False,
    'installable': True,
}
