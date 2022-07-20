# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class ProductTemplate(models.Model):
    """"""
    _inherit = 'product.template'

    translation_ar = fields.Char("Product Arabic Translation", compute='get_ar_trans')

    def get_ar_trans(self):
        for rec in self:
            rec.translation_ar = ''
            trans_value = self.env['ir.translation'].search([('src', '=', rec.name), ('lang', '=', 'ar_001')],limit=1)
            rec.translation_ar = trans_value.value


class StockMove(models.Model):
    """"""
    _inherit = 'stock.move'

    balance = fields.Float(string='Balance', compute='_get_balance')

    def _get_balance(self):
        for rec in self:
            in_qty = 0.0
            out_qty = 0.0
            rec.balance = 0.0
            in_moves = self.env['stock.move'].search([('product_id', '=', rec.product_id.id),
                                                   ('date', '<=', rec.date), ('location_dest_id.usage', '=', 'internal')])
            out_moves = self.env['stock.move'].search([('product_id', '=', rec.product_id.id),
                                                      ('date', '<=', rec.date), ('location_dest_id.usage', '!=', 'internal')])
            in_qty = sum(in_move.quantity_done for in_move in in_moves)
            out_qty = sum(out_move.quantity_done for out_move in out_moves)
            rec.balance = in_qty - out_qty

