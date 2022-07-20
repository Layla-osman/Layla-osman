# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    mobile = fields.Char(related="partner_id.mobile")


class SaleOrderSource(models.Model):
    _name = 'sale.order.source'
    _description = "Sale Order Source"

    name = fields.Char(string="Name")


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_source = fields.Many2one(comodel_name='sale.order.source', string="Sales Source")
    location_id = fields.Many2one(comodel_name='stock.location', string="Source Location")


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_new_picking_values(self):
        result = super(StockMove, self)._get_new_picking_values()
        if len(self.sale_line_id) > 0 and self.sale_line_id.order_id.location_id:
            result['location_id'] = self.sale_line_id.order_id.location_id.id
        return result


class PosSession(models.Model):
    _inherit = 'pos.session'

    # @api.multi
    # def get_z_report_details(self):
    #     payments = {}
    #     total = 0
    #     # start_dates = []; end_dates = []
    #     for session in self:
    #         # if session.start_at: start_dates.append(session.start_at)
    #         # if session.stop_at: end_dates.append(session.stop_at)
    #         for statement in session.statement_ids:
    #             payments.setdefault(statement.journal_id.id, {'amount': 0, 'name': statement.journal_id.name})
    #             payments[statement.journal_id.id]['amount'] += statement.total_entry_encoding
    #     for p in payments:
    #         total += payments[p]['amount']
    #     # start_dates.sort(); end_dates.sort()
    #     # return [payments, total, str(start_dates[0] or ''), str(end_dates[-1] or '')]
    #     start_date = ''; end_date = ''
    #     if self[0].start_at:
    #         start_date = fields.Datetime.to_string(fields.Datetime.context_timestamp(self, self[0].start_at))
    #     if self[0].stop_at:
    #         end_date = fields.Datetime.to_string(fields.Datetime.context_timestamp(self, self[0].stop_at))
    #     return [payments, total, start_date, end_date]

    # separating sales and refund orders
    def get_z_report_details(self):
        payments = {}
        total = 0
        refund_payments = {}
        refund_total = 0
        for session in self:
            for order in session.order_ids:
                if order.amount_total < 0:
                    for statement in order.statement_ids:
                        refund_payments.setdefault(statement.journal_id.id, {'amount': 0, 'name': statement.journal_id.name})
                        refund_payments[statement.journal_id.id]['amount'] += statement.amount
                elif order.amount_total > 0:
                    for statement in order.statement_ids:
                        payments.setdefault(statement.journal_id.id, {'amount': 0, 'name': statement.journal_id.name})
                        payments[statement.journal_id.id]['amount'] += statement.amount
        for p in payments:
            total += payments[p]['amount']
        for p in refund_payments:
            refund_total += refund_payments[p]['amount']

        #     for statement in session.statement_ids:
        #         payments.setdefault(statement.journal_id.id, {'amount': 0, 'name': statement.journal_id.name})
        #         payments[statement.journal_id.id]['amount'] += statement.total_entry_encoding
        # for p in payments:
        #     total += payments[p]['amount']
        start_date = ''; end_date = ''
        if self[0].start_at:
            start_date = fields.Datetime.to_string(fields.Datetime.context_timestamp(self, self[0].start_at))
        if self[0].stop_at:
            end_date = fields.Datetime.to_string(fields.Datetime.context_timestamp(self, self[0].stop_at))
        return [payments, total, start_date, end_date, refund_payments, refund_total]


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    def receipt_calc(self):
        decimals = self.company_id.currency_id.decimal_places
        result = {
            'get_price_before_discount': ('{:.%sf}' % decimals).format(self.price_unit * self.qty, decimals),
            'get_discount_amount': ('{:.%sf}' % decimals).format(self.price_unit * self.qty * self.discount / 100, decimals),
            'get_price_after_discount': ('{:.%sf}' % decimals).format(self.price_subtotal_incl, decimals)
        }
        return result


class PosOrder(models.Model):
    _inherit = 'pos.order'

    bank_trans_no = fields.Char(string="Bank Transaction No.", compute="_compute_bank_trans_no")

    def _compute_bank_trans_no(self):
        for i in self:
            trans = ''
            if len(i.statement_ids) > 0:
                for s in i.statement_ids:
                    if not(s.transaction_id == ''):
                        trans = s.transaction_id
                        break
            i.bank_trans_no = trans

    def receipt_calc(self):
        decimals = self.company_id.currency_id.decimal_places
        result = {
            'get_total_before_discount': ('{:.%sf}' % decimals).format(sum([(l.price_unit * l.qty) for l in self.lines]), decimals),
            'get_total_discount': ('{:.%sf}' % decimals).format(sum([(l.price_unit * l.qty * l.discount / 100) for l in self.lines]), decimals),
            'get_total_with_tax': ('{:.%sf}' % decimals).format(self.amount_total, decimals)
        }
        return result

    def _get_payment_details(self):
        payment_methods = self.env['account.journal'].search([('type', 'in', ['bank', 'cash']), ('currency_id', '=', False)])
        result = {}
        decimals = self.company_id.currency_id.decimal_places
        for p in payment_methods:
            result[p.name] = 0.0
        for p in self.statement_ids:
            result[p.journal_id.name] += p.amount
        for i in result:
            result[i] = ('{:.%sf}' % decimals).format(round(abs(result[i]), decimals))
        return result

    def _payment_fields(self, order, ui_paymentline):
        result = super(PosOrder, self)._payment_fields(order, ui_paymentline)
        result['transaction_id'] = ui_paymentline['transaction_id'] if 'transaction_id' in ui_paymentline else ''
        return result

    def _prepare_bank_statement_line_payment_values(self, data):
        result = super(PosOrder, self)._prepare_bank_statement_line_payment_values(data)
        result['transaction_id'] = data['transaction_id'] if 'transaction_id' in data else ''
        return result


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    bank_trans_no = fields.Char(string="Bank Transaction No.")


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, values, group_id):
        result = super(StockRule, self)._get_stock_move_values(
            product_id, product_qty, product_uom, location_id, name, origin, values, group_id)
        if 'sale_line_id' in values:
            sale_order = self.env['sale.order.line'].browse(values['sale_line_id']).order_id
            if sale_order.location_id.id:
                result['location_id'] = sale_order.location_id.id
        return result


class PosConfig(models.Model):
    _inherit = 'pos.config'

    mobile_no = fields.Char(string="Mobile")