# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.exceptions import Warning, ValidationError, _logger, UserError ,except_orm

import time
from babel.dates import format_datetime, format_date
from odoo.osv import expression
from odoo.release import version
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
import warnings


class WizardReturnPicking(models.TransientModel):
    _name = 'wizard.stock.picking'
    _description = 'Picking Wizard'

    test = fields.Boolean('Test')


class ReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"
    _description = 'Return Picking Line'


    test = fields.Boolean('Test')


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'
    _description = 'Return Picking'

    warn_text = fields.Text(readonly=True,compute='sales_returns',)
    gift_warn= fields.Text(readonly=True,)
    test = fields.Boolean('Test')

    @api.depends('product_return_moves')
    def sales_returns(self):
        for rec in self:
            if rec.product_return_moves:
                delivery_date = datetime.strptime(str(rec.picking_id.scheduled_date), '%Y-%m-%d %H:%M:%S').date()
                print("###############################", delivery_date)
                # rec.test = True
                today = fields.Date.today()
                difference = (today - delivery_date).days
                if difference >= 15 :
                    rec.warn_text ="This Sale Order Exceed 15 Days!"
                    rec.test = True
                else:
                    rec.warn_text ="This Sale Order not Exceed 15 Days!"
                    rec.test = False
                if any(move.product_id.detailed_type == 'consu' for move in rec.product_return_moves):
                    rec.gift_warn = "This Sale Contains Gift Product!"
                else:
                    rec.gift_warn = False



class ResPartner(models.Model):
    _inherit = 'res.partner'

    def merge_contacts(self):
            print('##########################')
            duplicate_phone = self.env['res.partner'].search(
                [('phone', '=', self.phone), ('active', '=', True)])
            print('$$$$$$$$$$$$$$$$$$$$$', duplicate_phone)
            if len(duplicate_phone) >1:
                test = test1




    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('phone', '=ilike', name.split(' ')[0] + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    def name_get(self):
        result = []
        for parnter in self:
            if parnter.phone:
                name = parnter.phone + ' ' + parnter.name
            else:
                name = parnter.name
            result.append((parnter.id, name))
        return result



    # def sales_returns(self):
    #     delivery_date = datetime.strptime(str(self.picking_id.scheduled_date), '%Y-%m-%d %H:%M:%S').date()
    #     print("###############################", delivery_date)
    #     self.test = True
    #     today = fields.Date.today()
    #     difference = (today - delivery_date).days
    #     if difference > 15 :
    #
    #         action = self.env.ref('stock.act_stock_return_picking')
    #         # msg = _(
    #         # 'Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
    #         # raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))
    #         view = self.env.ref('ii_sale_custom.view_stock_return_picking_inherit_form')
    #         view_id = view and view.id or False
    #         context = dict(self._context or {})
    #         context['message'] = "let it go"
    #         return {
    #             'name': 'Return Warning',
    #             'view_mode': 'form',
    #             'view_type': 'form',
    #             'res_model': 'wizard.stock.picking',
    #             'type': 'ir.actions.act_window',
    #             'view_id': view.id,
    #             'views': [(view.id, 'form')],
    #             'context': context,
    #             'target': 'new',
    #         }
    #     else:
    #         self.create_returns
    # def check_warning(self):
    #     if self.product_return_moves:
    #         picking = self.picking_id
    #         warning = {}
    #         delivery_date = datetime.strptime(str(self.picking_id.scheduled_date), '%Y-%m-%d %H:%M:%S').date()
    #         print("###############################",delivery_date)
    #         today = fields.Date.today()
    #         difference = (today - delivery_date).days
    #         if difference > 15 :
    #             test = test1
    #             return {
    #                 'effect': {
    #                     'fadeout':'slow',
    #                     'type': 'rainbow_man',
    #                     'message': _("Sale Order Exceed 15 Days !"),
    #                 }
    #             }

        # self.create_returns()

    # def create_returns(self):
    #     if self.product_return_moves:
        # picking = self.picking_id
        #         warning = {}
        #         delivery_date = datetime.strptime(str(self.picking_id.scheduled_date), '%Y-%m-%d %H:%M:%S').date()
        #         print("###############################",delivery_date)
        #         today = fields.Date.today()
        #         difference = (today - delivery_date).days
        #         if difference > 15 :
        #             test = test1
        #             return {
        #                 'effect': {
        #                     'fadeout':'slow',
        #                     'type': 'rainbow_man',
        #                     'message': _("Sale Order Exceed 15 Days !"),
        #                 }
        #             }
        # return super(ReturnPicking, self).create_returns()

    # @api.onchange('product_return_moves')
    # def sales_warning(self):
        # if self.product_return_moves:
        #     picking = self.picking_id
        #     warning = {}
        #     delivery_date = datetime.strptime(str(self.picking_id.scheduled_date), '%Y-%m-%d %H:%M:%S').date()
        #     print("###############################",delivery_date)
        #     today = fields.Date.today()
        #     difference = (today - delivery_date).days
        #     if difference > 15 :
        #         return {
        #             'effect': {
        #                 'fadeout':'slow',
        #                 'type': 'rainbow_man',
        #                 'message': _("Sale Order Exceed 15 Days !"),
        #             }
        #         }

                # view = self.env.ref('ii_sale_custom.view_stock_return_picking_inherit_form')
                # view_id = view and view.id or False
                # context =dict(self._context or {})
                # context['message'] = "let it go"
                # return {
                #     'name': 'Return Warning',
                #     'view_mode': 'form',
                #     'view_type': 'form',
                #     'res_model': 'wizard.stock.picking',
                #     'type': 'ir.actions.act_window',
                #     'view_id': view.id,
                #     'views': [(view.id,'form')],
                #     'context' : context,
                #     # 'res_id': self.id,
                #     'target': 'new',
                # }

    #
    #             # form_view = self.env.ref('ii_sale_custom.view_stock_return_picking_inherit_form')
    #             # return {
    #             #     'name': _('Job'),
    #             #     'res_model': 'stock.return.picking',
    #             #     'res_id': self.id,
    #             #     'views': [(form_view.id, 'form'), ],
    #             #     'type': 'ir.actions.act_window',
    #             #     # 'target': 'inline'
    #             # }
    #
    #             return {
    #                 'name': _('Returned Picking'),
    #                 'view_mode': 'form',
    #                 'res_model': 'wizard.stock.picking',
    #                 'type': 'ir.actions.act_window',
    #                 'target': 'new'
    #             }


