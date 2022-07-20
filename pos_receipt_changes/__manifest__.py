# -*- coding: utf-8 -*-
{
    'name': "PoS Receipt Changes",

    'author': "Corptech",
    'website': "http://corptech.tech",

    'category': 'Point of Sale',
    'version': '0.1',

    'depends': [
        'point_of_sale',
        'sale_stock',
        'account', 'analytic',
    ],

    'data': [
        'data/data.xml',

        'security/ir.model.access.csv',

        'views/views.xml',
        'views/templates.xml',
    ],

    'assets': {
        'point_of_sale.assets': [
            'pos_receipt_changes/static/src/js/GiftScreen.js',
            'pos_receipt_changes/static/src/js/GiftTemplate.js',
            'pos_receipt_changes/static/src/js/ArabicTemplate.js',
            'pos_receipt_changes/static/src/js/ReceiptTemplate.js',
            'pos_receipt_changes/static/src/js/changes.js',
        ],
        'web.assets_qweb': [
            'pos_receipt_changes/static/src/xml/**/*',
        ],

    },

    }

