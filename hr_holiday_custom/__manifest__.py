# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

{
    'name' :'Holiday Custom',
    'summary': """ """,

    'description': """
    """,

    'author': "IATL Intellisoft International",
    'website': "http://www.iatl-intellisoft.com",
    'category': 'Human Resource',

    'depends':['hr', 'calendar', 'hr_holidays'],

    'data' : [
        'security/security_view.xml',
        'security/ir.model.access.csv',
        'views/hr_holiday_custom_view.xml',
        # 'report/report.xml',

    ],

    'installable':True,
    'auto_install':False,
}

