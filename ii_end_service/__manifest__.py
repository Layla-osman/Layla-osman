# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

{
    'name': "End of Service Custom",

    'author': "IATL Intellisoft International",
    'website': "http://www.iatl-intellisoft.com",
    'category': 'Human Resource',

    # any module necessary for this one to work correctly
    'depends': ['hr', 'hr_payroll',  'hr_contract', 'hr_holidays'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'data/data.xml',
        # 'data/service_termination_template.xml',
        'views/view_hr_service_termination_inherit.xml',
        'views/hr_payslip.xml',
    ],
    'application': True,
    'auto_install': False,
    'installable': True,

}
