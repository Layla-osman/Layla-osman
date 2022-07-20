# -*- coding: utf-8 -*-
{
    'name': "Website Integration",

    'summary': """
        UNO Digital website e-commerce integration
    """,

    'description': """
* website url, username, password in system parameters
* map journals to payment method ID in website
* enter start date manually for initial fetching
* set website location in configuration
    """,

    'author': "CorpTech",
    'website': "http://corptech.tech",

    'category': 'Website/Website',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'sale',
        'account',
        'stock',
        'point_of_sale',
    ],

    # always loaded
    'data': [
        #'data/data.xml',
        'views/views.xml',
    ],
}
