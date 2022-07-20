import statistics
from statistics import mode, mean

from odoo import models, fields, api
from odoo.exceptions import AccessError, UserError, ValidationError


class ItemCardConnectReportWizard(models.TransientModel):
    _name = 'item.card.connect.report.wizard'
    _description = 'Item Card Report'



    from_date = fields.Datetime('From')
    to_date = fields.Datetime('To')
    product_id = fields.Many2one('product.product', string="Product")
    location_id = fields.Many2one('stock.location', string="Locations")



    def get_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form':{'from_date': fields.Date.from_string(self.from_date),
            'to_date': fields.Date.from_string(self.to_date),
            'product_id': self.product_id.id,
            'product_name': self.product_id.name,
            'location_id': self.location_id.id,
            'location_name': self.location_id.name
            },
            
            
        }


        return self.env.ref('item_card_connect.item_card_connect_report').report_action(self, data=data)


class PriceAnalysisReport(models.AbstractModel):
    _name = 'report.item_card_connect.item_card_connect_template'

    @api.model
    def _get_report_values(self, docids, data=None):
        print(":::::::::::::::::::::::::::::::::::")
        from_date = data['form']['from_date']
        to_date = data['form']['to_date']
        product_id = data['form']['product_id']
        product_name = data['form']['product_name']
        location_id = data['form']['location_id']
        location_name = data['form']['location_name']

        docs = []
        open_stock = 0
        if from_date > to_date:
            raise UserError(("You must be enter start date less than end date."))


        move_ids = self.env['stock.move'].search(
            [('date', '<=', to_date), ('date', '>=', from_date),
            ('state', '=', 'done'),('product_id','=',product_id),'|',('location_id','=',location_id),('location_dest_id', '=',location_id)], order='date desc')

        move_open_ids = self.env['stock.move'].search(
            [('date', '<', from_date),
            ('state', '=', 'done'),('product_id','=',product_id),'|',('location_id','=',location_id),('location_dest_id', '=',location_id)], order='date desc')
        receiv_qunt = 0
        issused_qunt = 0
        closing_stock = 0
        if move_open_ids:
            # docs = move_open_ids
            sum_quant = 0.0
            
            for move in move_open_ids:

                quantity = move.product_qty

                sum_quant += quantity
            open_stock = sum_quant

        if move_ids:
            move_type = None
            docs = move_ids
            for move in move_ids:
                quantity = move.product_qty
                location_dest = move.location_dest_id.complete_name
                location_id = move.location_id.name

                if move.location_id.usage not in ('internal', 'transit') and move.location_dest_id.usage in ('internal', 'transit'):
                    move_type = 'incoming'

                elif move.location_id.usage in ('internal', 'transit') and move.location_dest_id.usage not in ('internal', 'transit'):
                    move_type = 'outgoing'

                
                if move_type ==  'incoming':
                    receiv_qunt += quantity
                elif move_type ==  'outgoing':

                    issused_qunt += quantity

            product_r = []
            product_group = self.env['stock.move.line'].read_group([('move_id', 'in',  docs.ids)],['product_id'],['product_id'])
            for rec in product_group:
                in_qty = 0
                out_qty = 0
                in_internal = 0
                balance = 0
                product_id = self.env['product.product'].browse(rec['product_id'][0])
                product = self.env['stock.move.line'].search(rec['__domain'])
                for pro in product:
                    if pro.move_id.picking_type_id.code == 'outgoing':
                        out_qty += pro.qty_done
                    if pro.move_id.picking_type_id.code == 'incoming':
                        in_qty += pro.qty_done
                    if pro.move_id.picking_type_id.code == 'internal':
                        in_internal += pro.qty_done
                    balance = in_qty - out_qty
                product_r.append({'product_name': product_id.name ,'in_qty':in_qty,'out_qty': out_qty,'in_internal':in_internal,'balance':balance})            

        closing_stock = open_stock + receiv_qunt - issused_qunt




        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'from_date': from_date,
            'to_date': to_date,
            'docs':docs,
            'location_id':location_id,
            'location_name':location_name,
            'open_stock':open_stock,
            'receiv_qunt':receiv_qunt,
            'issused_qunt':issused_qunt,
            'product_r': product_r,
            'closing_stock':closing_stock
            }

#     from_date = fields.Date('From', default=fields.Date.today())
#     to_date = fields.Date('To', default=fields.Date.today())
#     location_id = fields.Many2one('stock.location', string="Location Name")

#     def get_report(self):
#         data = {
#             'ids': self.ids,
#             'model': self._name,
#             'form': {
#                 'from_date': fields.Date.from_string(self.from_date),
#                 'to_date': fields.Date.from_string(self.to_date),
#                 'location_id': self.location_id.id,
#                 'location_name': self.location_id.name,
#             },
#         }

#         return self.env.ref('item_card_connect.item_card_connect_report').report_action(self, data=data)


# class PriceAnalysisReport(models.AbstractModel):
#     _name = 'report.item_card_connect.item_card_connect_template'

#     @api.model
#     def _get_report_values(self, docids, data=None):
#         from_date = data['form']['from_date']
#         to_date = data['form']['to_date']
#         location_id = data['form']['location_id']
#         location_name = data['form']['location_name']
#         domain = []
#         open_domain = []

#         domain.append(('date', '>=', from_date))
#         domain.append(('date', '<=', to_date))
#         open_domain.append(('date','<',from_date))


#         move_list = []
#         docs = self.env['stock.move'].search(domain)
#         if docs:
#             for doc in docs:
#                 if doc.location_id.id == location_id or doc.location_dest_id.id == location_id:
#                     move_list.append(doc.id)

#         docs = self.env['stock.move'].search([('id', 'in', move_list)], order="date asc")
#         docs = docs.filtered(lambda qty_done: qty_done.quantity_done > 0)

#         opening_balance = 0.0
#         closing_balance = 0.0
#         # product = self.env['product.product'].search([('id', '=', product_id)], limit=1)
#         # min_qty = int(product.reordering_min_qty)
#         # product_name_ar = product.translation_ar
#         # specification = product.description
#         # unit_name = product.uom_id.name

#         first_doc = self.env['stock.move'].search(open_domain)
#         first_doc = docs.filtered(lambda qty_done: qty_done.quantity_done > 0)
#         first_doc = self.env['stock.move'].search([('id', 'in', first_doc.mapped('id'))], order="date asc", limit=1)

#         last_doc = self.env['stock.move'].search(domain)
#         last_doc = docs.filtered(lambda qty_done: qty_done.quantity_done > 0)
#         last_doc = self.env['stock.move'].search([('id', 'in', last_doc.mapped('id'))], order="date desc", limit=1)

#         if first_doc:
#             opening_balance = first_doc.balance
#         if last_doc:
#             closing_balance = last_doc.balance

#         return {
#             'doc_ids': data['ids'],
#             'doc_model': data['model'],
#             'from_date': from_date,
#             'to_date': to_date,
#             # 'min_qty': min_qty,
#             # 'product_name_ar': product_name_ar,
#             'product_location': location_name,
#             # 'product_name': product_name,
#             # 'specification': specification,
#             # 'unit_name': unit_name,
#             'opening_balance': opening_balance,
#             'closing_balance': closing_balance,
#             'docs': docs,
#         }
