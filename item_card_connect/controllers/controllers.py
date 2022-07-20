# -*- coding: utf-8 -*-
# from odoo import http


# class ItemCardConnect(http.Controller):
#     @http.route('/item_card_connect/item_card_connect/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/item_card_connect/item_card_connect/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('item_card_connect.listing', {
#             'root': '/item_card_connect/item_card_connect',
#             'objects': http.request.env['item_card_connect.item_card_connect'].search([]),
#         })

#     @http.route('/item_card_connect/item_card_connect/objects/<model("item_card_connect.item_card_connect"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('item_card_connect.object', {
#             'object': obj
#         })
