# -*- coding: utf-8 -*-
# Copyright (c) 2018 Alexander Ezquevo <alexander@acysos.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Pos Warning',
    'version': '15.0',
    'author': 'IATL-intellisoft',
    "website": "www.acysos.com",
    'contributors': ['Alexander Ezquevo <alexander@acysos.com>', ],
    "license": "AGPL-3",
    'depends': ['point_of_sale', 'sale'
    ],
    'assets': {
        'point_of_sale.assets': [
            'pos_warning/static/src/js/main.js'
        ]
    },
    # "data": ["views/pos_templates.xml",
    # ],
    'images': ['static/description/banner.jpg'],
    'installable': True,


}
