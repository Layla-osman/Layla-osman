# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

{
    'name' :'Penalty',
    'summary': """ """,

    'description': """
    """,

    'author': "IATL Intellisoft International",
    'website': "http://www.iatl-intellisoft.com",
    'category': 'Human Resource',

    'depends':['hr','hr_contract','hr_payroll','eos_confluence'],

    'data' : [
        'security/security_view.xml',
        'security/ir.model.access.csv',
        'views/hr_penalty_view.xml',
        # 'report/report.xml',
        'report/penalty_template.xml',
    
    ],

    'installable':True,
    'auto_install':False,
}

