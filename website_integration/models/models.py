# -*- coding: utf-8 -*-
import requests, json
from datetime import datetime, timedelta
from odoo import api, fields, models
from odoo.exceptions import UserError

head = {
    'Content-Type': 'application/json',
    # 'Accept': 'application/json',
}


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    website_journal_id = fields.Integer(string="website Journal ID")


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        account_id = False
        payment_term_id = False
        fiscal_position = False
        bank_id = False
        warning = {}
        domain = {}
        company_id = self.company_id.id
        p = self.partner_id if not company_id else self.partner_id.with_context(company_id=company_id)

        if p:
            type = self.type or self.env.context.get('type', 'out_invoice')
            rec_account = p.property_account_receivable_id
            pay_account = p.property_account_payable_id
            if not rec_account and not pay_account:
                action = self.env.ref('account.action_account_config')
                msg = _(
                    'Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))

            if type in ('in_invoice', 'in_refund'):
                account_id = pay_account.id
                payment_term_id = p.property_supplier_payment_term_id.id
            else:
                account_id = rec_account.id
                payment_term_id = p.property_payment_term_id.id

            delivery_partner_id = self.get_delivery_partner_id()
            fiscal_position = p.env['account.fiscal.position'].get_fiscal_position(self.partner_id.id,
                                                                                   delivery_id=delivery_partner_id)

            # If partner has no warning, check its company
            if p.invoice_warn == 'no-message' and p.parent_id:
                p = p.parent_id
            if p.invoice_warn and p.invoice_warn != 'no-message':
                # Block if partner only has warning but parent company is blocked
                if p.invoice_warn != 'block' and p.parent_id and p.parent_id.invoice_warn == 'block':
                    p = p.parent_id
                warning = {
                    'title': _("Warning for %s") % p.name,
                    'message': p.invoice_warn_msg
                }
                if p.invoice_warn == 'block':
                    self.partner_id = False

        self.account_id = account_id
        if payment_term_id:
            self.payment_term_id = payment_term_id
        self.date_due = False
        self.fiscal_position_id = fiscal_position

        if type in ('in_invoice', 'out_refund'):
            bank_ids = p.commercial_partner_id.bank_ids
            bank_id = bank_ids[0].id if bank_ids else False
            self.partner_bank_id = bank_id
            domain = {'partner_bank_id': [('id', 'in', bank_ids.ids)]}
        elif type == 'out_invoice':
            domain = {'partner_bank_id': [('partner_id.ref_company_ids', 'in', [self.company_id.id])]}

        res = {}
        if warning:
            res['warning'] = warning
        if domain:
            res['domain'] = domain
        return res


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    website_product_id = fields.Integer(string="Website Product ID")


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    website_order_id = fields.Integer(string="Website Order ID", readonly=True)

    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        company_id = self.company_id.id
        journal_id = self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal()
        if not journal_id:
            raise UserError(_('Please define an accounting sales journal for this company.'))
        self.partner_id.property_account_receivable_id = self.env['account.account'].sudo().search(
            [('user_type_id.name', '=', 'Receivable'),
             ('company_id', '=', self.company_id.id)], limit=1).id
        self.partner_id.property_account_payable_id = self.env['account.account'].sudo().search(
            [('user_type_id.name', '=', 'Payable'),
             ('company_id', '=', self.company_id.id)], limit=1).id
        invoice_vals = {
            'ref': self.client_order_ref or '',
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.pricelist_id.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'user_id': self.user_id.id,
            'invoice_user_id': self.user_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(
                self.partner_invoice_id.id)).id,
            'partner_bank_id': self.company_id.partner_id.bank_ids[:1].id,
            'journal_id': journal_id.id,  # company comes from the journal
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'payment_reference': self.reference,
            'transaction_ids': [(6, 0, self.transaction_ids.ids)],
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
        }
        return invoice_vals

    def create_website_order(self, data):
        # res_config = self.env['ir.config_parameter'].sudo()
        for i in data:
            order_line = []
            order, customer, products, payment, shipping = i
            for p in products:
                product_id = self.env['product.product']
                # all items compulsorily needs to have a barcode
                if 'barcode' in p:
                    product_id = product_id.search([('barcode', '=', p['barcode'].strip())])
                if not product_id and 'default_code' in p:
                    product_id = product_id.search([('default_code', '=', p['default_code'])])
                if product_id:
                    line_vals = {
                        'product_id': product_id.id,
                        'product_uom_qty': p['product_uom_qty'],
                        'price_unit': p['price_unit'],
                    }
                    order_line.append((0, 0, line_vals))
            if len(shipping):
                line_vals = {
                    'product_id': shipping['product_id'],
                    'product_uom_qty': 1,
                    'price_unit': shipping['price_unit'],
                }
                order_line.append((0, 0, line_vals))
            if order_line:
                partner = self.env['res.partner']
                if customer:
                    found = partner.search([
                        ('name', '=', customer['name']),
                        ('phone', '=', customer['phone'])
                    ], limit=1)
                    if found and not customer['phone'] == '':
                        partner = found
                        found.company_id = False
                        print("found")
                        print(found)
                    else:
                        # TODO skipping for now (commenting it), please work on it later
                        # city_id = self.env['res.country.city'].search([('name', '=', customer['city'])], limit=1)
                        country_id = self.env['res.country'].search([('name', '=', customer['country_id'])], limit=1)
                        # if not city_id:
                        #     city_id.create({'name': customer['city']})
                        property_account_receivable_id = self.env['account.account'].sudo().search(
                            [('user_type_id', '=', 'Receivable'),
                             ('company_id', '=', order['company_id'])], limit=1).id
                        property_account_payable_id = self.env['account.account'].sudo().search(
                            [('user_type_id', '=', 'Payable'),
                             ('company_id', '=', order['company_id'])], limit=1).id
                        print("property_account_receivable_id")
                        print(property_account_receivable_id)
                        print("property_account_payable_id")
                        print(property_account_payable_id)
                        new_customer = self.env['res.partner'].create({
                            'name': customer['name'],
                            'email': customer['email'],
                            'phone': customer['phone'],
                            'street': customer['street'],
                            'street2': customer['street2'],
                            'city': customer['city'],
                            # 'block': customer['block'],
                            # 'street': customer['street'],
                            # 'jaddah': customer['jaddah'],
                            # 'building': customer['building'],
                            # 'floor': customer['floor'],
                            # 'company_id': order['company_id'],
                            'country_id': country_id.id if country_id else False,
                            'property_product_pricelist': self.env['product.pricelist'].sudo().search(
                                [('currency_id', '=', order['currency']),
                                 ('company_id', '=', order['company_id'])], limit=1).id,
                            'property_account_receivable_id': property_account_receivable_id,
                            'property_account_payable_id': property_account_payable_id,

                        })
                        print("new customer")
                        print(new_customer)
                        partner = new_customer
                product_template = self.env['product.template'].search([('name', '=', product_id.name)], limit=1)
                price_list_item = self.env['product.pricelist.item'].search(
                    [('product_tmpl_id', '=', product_template.id)], limit=1)
                price_id = price_list_item.pricelist_id.id
                if not price_id:
                    price_id = order['pricelist_id']
                vals = {
                    'date_order': order['date'],
                    'partner_id': partner.id,
                    'order_line': order_line,
                    'pricelist_id': price_id,
                    'warehouse_id': order['warehouse_id'],
                    'company_id': order['company_id'],
                    'website_order_id': int(order['website_order_id']),
                    'sale_source': self.env.ref('pos_receipt_changes.sale_order_source_website').id
                }
                # currency
                if not order['currency'] == self.env.user.company_id.currency_id.name:
                    currency_id = self.env['res.currency'].search([('name', '=', order['currency'])], limit=1)
                    if currency_id:
                        vals['currency_id'] = currency_id.id
                order = self.create(vals)
                order.action_confirm()
                invoices = self.env['account.move'].browse(order._create_invoices()).id
                print("gggggg")
                print(invoices)
                invoices.invoice_date = str(order.date_order)
                invoices.invoice_date_due = str(order.date_order)
                invoices.action_post()
                register_payments_model = self.env['account.payment']
                ctx = {'active_model': 'account.move', 'active_ids': [invoices[0].id]}

                # TODO work on it
                # TODO what if different currency for sale order and payment
                if payment and order['company_id'].id == 1:
                    # journal_id = self.env['account.journal'].search([('website_journal_id', '=', 2)], limit=1)
                    journal_id = self.env['account.journal'].search([('website_journal_id', '=', 2)], limit=1)
                if payment and order['company_id'].id == 2:
                    # journal_id = self.env['account.journal'].search([('website_journal_id', '=', 46)], limit=1)
                    journal_id = self.env['account.journal'].search([('website_journal_id', '=', 3)], limit=1)
                if journal_id:
                    register_payments = register_payments_model.with_context(ctx).create({
                        'payment_date': fields.Date.today(),
                        'journal_id': journal_id.id,
                        'amount': payment['amount'],
                        'invoice_ids': [(4, invoices[0].id, None)],
                        'payment_type': 'inbound',
                        'partner_type': 'customer',
                        'invoice_ids': False,
                        # 'payment_difference':0.0,
                        'partner_id': partner.id,
                        'currency_id': self.env.user.company_id.currency_id.id,
                        # 'destination_account_id': self.env['account.account'].sudo().search([('user_type_id.name', '=','Receivable'),('company_id', '=', order['company_id'].id)], limit=1).id,
                        'payment_method_id': self.env.ref("account.account_payment_method_manual_in").id,
                    })
                    register_payments.post()
                    register_payments.invoice_ids = invoices.ids
                immediate_obj = self.env['stock.immediate.transfer']
                for picking in order.picking_ids:
                    for m in picking.move_ids_without_package:
                        m.quantity_done = m.product_uom_qty
                    picking.action_confirm()
                    picking._action_done()
                    immediate_rec = immediate_obj.create({'pick_ids': [(4, picking.id)]})
                    immediate_rec.process()

    def create_website_order2(self, data):
        # res_config = self.env['ir.config_parameter'].sudo()

        for i in data:
            order_line = []
            order, customer, products, payment, shipping = i

            for p in products:
                product_id = self.env['product.product']
                # all items compulsorily needs to have a barcode
                if 'barcode' in p:
                    product_id = product_id.search([('barcode', '=', p['barcode'].strip())])
                if not product_id and 'default_code' in p:
                    product_id = product_id.search([('default_code', '=', p['default_code'])])
                if not product_id:
                    product_id = product_id.create({
                        'name': p['name'],
                        'barcode': p['barcode'],
                        'default_code': p['default_code'],
                        'list_price': p['price_unit'],
                        'lst_price': p['price_unit'],
                        'standard_price': p['price_unit'],
                        'price': p['price_unit'],
                        'type': 'product',
                        'cost_method': 'average',
                        'valuation': 'real_time',
                        'available_in_pos': True,
                    })
                if product_id:
                    line_vals = {
                        'product_id': product_id.id,
                        'product_uom_qty': p['product_uom_qty'],
                        'price_unit': p['price_unit'],

                    }
                    order_line.append((0, 0, line_vals))
            if len(shipping):
                line_vals = {
                    'product_id': shipping['product_id'],
                    'product_uom_qty': 1,
                    'price_unit': shipping['price_unit'],
                }
                order_line.append((0, 0, line_vals))
            if order_line:
                partner = self.env['res.partner']
                if customer:
                    found = partner.search([
                        # ('mobile', '=', customer['mobile'])
                        ('phone', '=', customer['phone'])
                    ], limit=1)
                    if found and not customer['phone'] == '':
                        partner = found
                    else:
                        # TODO skipping for now (commenting it), please work on it later
                        # city_id = self.env['res.country.city'].search([('name', '=', customer['city'])], limit=1)
                        country_id = self.env['res.country'].search([('name', '=', customer['country_id'])], limit=1)
                        customer_currency_id = self.env['res.currency'].search([('name', '=', order['currency'])],
                                                                               limit=1)
                        pricelist = self.env['product.pricelist'].sudo().search(
                            [('currency_id', '=', customer_currency_id.id), ('company_id', '=', order['company_id'])],
                            limit=1).id,
                        # if order['website_order_id'] == "11":
                        #     raise UserError(pricelist)
                        # raise UserError(order['company_id'])
                        # if order['company_id'].id == 2:
                        #     print(pricelist, customer_currency_id.name,'Qatar',)
                        # if order['company_id'].id == 1:
                        #     print(pricelist, customer_currency_id.name, 'Kuwait', )
                        # if not city_id:
                        #     city_id.create({'name': customer['city']})
                        new_customer = self.env['res.partner'].sudo().create({
                            'name': customer['name'],
                            'email': customer['email'],
                            'phone': customer['phone'],
                            'street': customer['street'],
                            'street2': customer['street2'],
                            'city': customer['city'],
                            'company_id': order['company_id'],
                            'property_product_pricelist': self.env['product.pricelist'].sudo().search(
                                [('currency_id', '=', customer_currency_id.id),
                                 ('company_id', '=', order['company_id'])], limit=1).id,
                            'property_account_receivable_id': self.env['account.account'].sudo().search(
                                [('user_type_id.name', '=', 'Receivable'), ('company_id', '=', order['company_id'])],
                                limit=1).id,
                            'property_account_payable_id': self.env['account.account'].sudo().search(
                                [('user_type_id.name', '=', 'Payable'), ('company_id', '=', order['company_id'])],
                                limit=1).id,
                            # 'block': customer['block'],
                            # 'street': customer['street'],
                            # 'jaddah': customer['jaddah'],
                            # 'building': customer['building'],
                            # 'floor': customer['floor'],
                            # 'flat': customer['flat'],
                            # 'city': city_id.id,
                            'country_id': country_id.id if country_id else False,
                        })
                        partner = new_customer

                vals = {
                    'date_order': order['date'],
                    'partner_id': partner.id,
                    'order_line': order_line,
                    'pricelist_id': partner.property_product_pricelist.id,
                    'warehouse_id': order['warehouse_id'],
                    'company_id': order['company_id'],
                    'website_order_id': int(order['website_order_id']),
                    'sale_source': self.env.ref('pos_receipt_changes.sale_order_source_website').id
                }

                # currency
                if not order['currency'] == self.env.user.company_id.currency_id.name:
                    currency_id = self.env['res.currency'].search([('name', '=', order['currency'])], limit=1)
                    if currency_id:
                        vals['currency_id'] = currency_id.id
                order = self.sudo().create(vals)
                order.sudo().action_confirm()
                invoice_journal_id = self.env['account.journal'].sudo().search(
                    [('company_id', '=', order['company_id'].id), ('type', '=', 'sale')], limit=1)
                invoices = self.env['account.move'].sudo().browse(order.with_context(journal_id=invoice_journal_id.id,
                                                                                     company_id=order[
                                                                                         'company_id'].id).action_invoice_create())
                # for invoice in invoices.invoice_line_ids:
                #     invoice.company_id = order['company_id'].id
                # invoices.date_invoice = str(order.date_order)
                # invoices.dat e_due = str(order.date_order)
                # invoices.sudo().with_context(company_id=order['company_id'].id,journal_id=invoice_journal_id.id).action_invoice_open()
                # register_payments_model = self.env['account.payment']
                # payment_journal_id = self.env['account.journal'].sudo().search([('company_id', '=', order['company_id'].id), ('website_journal_id','=', 18)], limit=1)
                # ctx = {'active_model': 'account.move', 'active_ids': [invoices[0].id], 'company_id': order['company_id'],'journal_id':payment_journal_id.id}
                # # TODO work on it
                # # TODO what if different currency for sale order and payment
                # if payment:
                #     journal_id = self.env['account.journal'].search([('company_id', '=', order['company_id'].id), ('website_journal_id','=', 18)], limit=1)
                #     if journal_id:
                #         register_payments = register_payments_model.with_context(ctx).with_context(company_id=order['company_id'].id,journal_id=journal_id).sudo().create({
                #             'payment_date': fields.Date.today(),
                #             'journal_id': journal_id.id,
                #             'amount': payment['amount'],
                #             'invoice_ids': [(4, invoices[0].id, None)],
                #             'payment_type': 'inbound',
                #             'partner_type': 'customer',
                #             'partner_id': partner.id,
                #             'payment_method_id': self.env.ref("account.account_payment_method_manual_in").id,
                #             'company_id':order['company_id'],
                #             # 'invoice_ids':False,
                #             # 'destination_account_id':self.env['account.account'].search([('user_type_id.name', '=','Receivable'),('company_id', '=', order['company_id'].id)], limit=1).id,
                #             # 'currency_id':invoices.currency_id.id,
                #         })
                # register_payments.sudo().post()
                immediate_obj = self.env['stock.immediate.transfer']
                for picking in order.picking_ids:
                    for m in picking.move_ids_without_package:
                        m.quantity_done = m.product_uom_qty
                    picking.sudo().action_confirm()
                    picking.sudo().action_done()
                    immediate_rec = immediate_obj.sudo().create({'pick_ids': [(4, picking.id)]})
                    immediate_rec.sudo().process()

    def get_website_order_date(self, company_id):
        # res_config = self.env['ir.config_parameter'].sudo()
        order = self.sudo().search([
            ('website_order_id', '>', 0), ('company_id', '=', company_id),
            ('state', 'in', ('sale', 'done')),
        ], limit=1)
        print('########################',order.name)
        self_in_tz = self.with_context(tz=(self.env.user.tz or 'UTC'))
        if order:
            date_begin = fields.Datetime.from_string(order.date_order + timedelta(seconds=1))
            date_order = fields.Datetime.to_string(
                fields.Datetime.context_timestamp(self_in_tz, date_begin))
            return datetime.strptime(date_order, "%Y-%m-%d %H:%M:%S")
        else:
            dt = fields.Date.today()
            dt = datetime.combine(dt, datetime.min.time())
            return dt

    def _cron_fetch_website_order_k(self, limit):
        company = self.env.user.company_id
        website = company.website_url
        username = company.website_username
        password = company.website_password
        location_id = company.website_location.id
        website_warehouse = company.website_warehouse.id
        url = website + '/api/report/salesreport'
        start_time = self.get_website_order_date(1)
        current_time = fields.Datetime.now()
        self_in_tz = self.with_context(tz=(self.env.user.tz or 'UTC'))
        current_time_in_tz = fields.Datetime.context_timestamp(self_in_tz, current_time)
        print('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@',current_time_in_tz)
        data = {
            # 'auth_token': key,
            'date_from': "2022-02-09 00:00:00",
            'date_to': current_time_in_tz,
        }
        x = requests.get(url=website, params=data, auth=(username, password))
        print('@@@@@@@@@@@@@@@@@@@@@@@@@@',x)
        text = x.text if not (x.text == '') else x.status_code
        result = json.loads(text)

        # error handling for no orders
        if not 'data' in result:
            return True
        data = []
        result = result['data'][:limit]
        # for r in result['data']:
        for r in result:
            # try:
            order = {}
            customer = {}
            products = []
            payment = {}
            shipping = {}

            # shipping/delivery charge
            try:
                charges = float(r['shippingdetail']['shippingcharge'])
                if charges:
                    shipping['price_unit'] = charges
                    shipping_product = self.env['product.product'].search(
                        [('name', '=', r['shippingdetail']['shippingtype'])])
                    if not shipping_product:
                        shipping_product = self.env['product.product'].create({
                            'name': r['shippingdetail']['shippingtype'],
                            'type': 'service',
                            'list_price': charges,
                        })
                    shipping['product_id'] = shipping_product.id
            except Exception as e:
                pass
            order.update({
                'website_order_id': int(r['orderdetail']['orderid']),
                'date': datetime.strptime(r['orderdetail']['orderdate'], "%Y-%m-%d %H:%M:%S") - timedelta(hours=3,
                                                                                                          minutes=0),
                'currency': r['orderdetail']['currency'],
                'location_id': location_id,
                'warehouse_id': 1,
                'company_id': 1,
                'pricelist_id': 1,
                # 'warehouse_id':1,
                # 'company_id': 1,

            })
            # order.update({
            #     'website_order_id': int(r['orderdetail']['orderid']),
            #     'date': datetime.strptime(r['orderdetail']['orderdate'], "%Y-%m-%d %H:%M:%S") - timedelta(hours=3,
            #                                                                                               minutes=0),
            #     'currency': r['orderdetail']['currency'],
            #     'location_id': location_id,
            # })

            r_customer = r['customerdetail']

            customer.update({
                'name': r_customer['name'] or '',
                'email': r_customer['email'] or '',
                'phone': r_customer['mobile'] or '',

                'block': r_customer['block_number'] or '',
                'jaddah': r_customer['avenue_number'] or '',
                'street': r_customer['street_number'] or '',

                'house': r_customer['house_number'] or '',
                'building': r_customer['building_number'] or '',
                'floor': r_customer['floor_number'] or '',
                'flat': r_customer['flat_number'] or '',

                'area': r_customer['areaname'] or '',
                'city': r_customer['city'] or '',

                'country_id': r_customer['country'] or '',
            })

            street1 = ''
            if not customer['street'] == '':
                street1 += 'Street: ' + customer['street'] + ', '
            if not customer['block'] == '':
                street1 += 'Block: ' + customer['block'] + ', '
            if not customer['jaddah'] == '':
                street1 += 'Avenue: ' + customer['jaddah']
            customer['street'] = street1

            street2 = ''
            if not customer['house'] == '':
                street2 += 'House: ' + customer['house'] + ', '
            if not customer['building'] == '':
                street2 += 'Bldg: ' + customer['building'] + ', '
            if not customer['floor'] == '':
                street2 += 'Floor: ' + customer['floor'] + ', '
            if not customer['flat'] == '':
                street2 += 'Flat: ' + customer['flat']
            customer['street2'] = street2

            city = ''
            if not customer['area'] == '':
                city += customer['area']
            if not customer['city'] == '':
                city += ', ' + customer['city']
            customer['city'] = city

            # find the payment matching order id
            r_payment = r['paymentdetail']

            if r_payment:
                payment = {
                    'journal_name': r_payment['paymentmethod'],
                    'journal_id': r_payment['paymentmethodid'],
                    'payment_id': r_payment['paymentid'],
                    'transaction_id': r_payment['tranid'],
                    'payment_date': datetime.strptime(r_payment['paymentdate'], "%Y-%m-%d %H:%M:%S") if r_payment[
                                                                                                            'paymentdate'] is not None else
                    order['date'],
                    'amount': float(r_payment['paidamount']),
                }

            if 'items' in r:
                for p in r['items']:
                    if not (p['barcode'] == ''):
                        # TODO think about category
                        vals = {
                            'product_id': p['productid'],
                            'name': p['productname'],
                            'default_code': p['SKU'],
                            'barcode': p['barcode'],
                            'product_uom_qty': p['orderqty'],
                            'price_unit': p['price'],
                            # 'category_id': p['category_id'],
                        }
                        products.append(vals)
                    gift_list = ['', '2', '3']
                    for g in range(0, len(gift_list)):
                        if not p['giftproduct' + gift_list[g]] == '':
                            vals = {
                                # 'product_id': p['productid'],
                                # 'name': p['productname'],
                                'default_code': p['giftproduct' + gift_list[g]],
                                # 'barcode': p['barcode'],
                                'product_uom_qty': 1,
                                'price_unit': p['giftproduct' + gift_list[g] + 'price'],
                                # 'category_id': p['category_id'],
                            }
                            products.append(vals)
                data.append((order, customer, products, payment, shipping))

        if data:
            self.create_website_order(data)
        return True

    def _cron_fetch_website_order_q(self, limit):
        company = self.env.user.company_id
        website = company.website_url
        username = company.website_username
        password = company.website_password
        location_id = company.website_location.id
        start_time = self.get_website_order_date(2)
        current_time = fields.Datetime.now()
        self_in_tz = self.with_context(tz=(self.env.user.tz or 'UTC'))
        current_time_in_tz = fields.Datetime.context_timestamp(self_in_tz, current_time)
        data = {
            # 'auth_token': key,
            'date_from': "2022-02-09 00:00:00",
            'date_to': current_time_in_tz,
        }
        x = requests.get(url=website, params=data, auth=(username, password))
        text = x.text if not (x.text == '') else x.status_code
        result = json.loads(text)
        # error handling for no orders
        if not 'data' in result:
            return True
        data = []
        result = result['data'][:limit]
        # for r in result['data']:
        for r in result:
            # try:
            order = {}
            customer = {}
            products = []
            payment = {}
            shipping = {}

            # shipping/delivery charge
            try:
                charges = float(r['shippingdetail']['shippingcharge'])
                if charges:
                    shipping['price_unit'] = charges
                    shipping_product = self.env['product.product'].search(
                        [('name', '=', r['shippingdetail']['shippingtype'])])
                    if not shipping_product:
                        shipping_product = self.env['product.product'].create({
                            'name': r['shippingdetail']['shippingtype'],
                            'type': 'service',
                            'list_price': charges,
                        })
                    shipping['product_id'] = shipping_product.id
            except Exception as e:
                pass
            order.update({
                'website_order_id': int(r['orderdetail']['orderid']),
                'date': datetime.strptime(r['orderdetail']['orderdate'], "%Y-%m-%d %H:%M:%S") - timedelta(hours=3,
                                                                                                          minutes=0),
                'currency': r['orderdetail']['currency'],
                'location_id': location_id,
                # 'warehouse_id': 2,
                'pricelist_id': 8,
                'warehouse_id': 2,
                'company_id': 2,

            })
            # order.update({
            #     'website_order_id': int(r['orderdetail']['orderid']),
            #     'date': datetime.strptime(r['orderdetail']['orderdate'], "%Y-%m-%d %H:%M:%S") - timedelta(hours=3,
            #                                                                                               minutes=0),
            #     'currency': r['orderdetail']['currency'],
            #     'location_id': location_id,
            # })

            r_customer = r['customerdetail']

            customer.update({
                'name': r_customer['name'] or '',
                'email': r_customer['email'] or '',
                'phone': r_customer['mobile'] or '',

                'block': r_customer['block_number'] or '',
                'jaddah': r_customer['avenue_number'] or '',
                'street': r_customer['street_number'] or '',

                'house': r_customer['house_number'] or '',
                'building': r_customer['building_number'] or '',
                'floor': r_customer['floor_number'] or '',
                'flat': r_customer['flat_number'] or '',

                'area': r_customer['areaname'] or '',
                'city': r_customer['city'] or '',

                'country_id': r_customer['country'] or '',
            })

            street1 = ''
            if not customer['street'] == '':
                street1 += 'Street: ' + customer['street'] + ', '
            if not customer['block'] == '':
                street1 += 'Block: ' + customer['block'] + ', '
            if not customer['jaddah'] == '':
                street1 += 'Avenue: ' + customer['jaddah']
            customer['street'] = street1

            street2 = ''
            if not customer['house'] == '':
                street2 += 'House: ' + customer['house'] + ', '
            if not customer['building'] == '':
                street2 += 'Bldg: ' + customer['building'] + ', '
            if not customer['floor'] == '':
                street2 += 'Floor: ' + customer['floor'] + ', '
            if not customer['flat'] == '':
                street2 += 'Flat: ' + customer['flat']
            customer['street2'] = street2

            city = ''
            if not customer['area'] == '':
                city += customer['area']
            if not customer['city'] == '':
                city += ', ' + customer['city']
            customer['city'] = city

            # find the payment matching order id
            r_payment = r['paymentdetail']

            if r_payment:
                payment = {
                    'journal_name': r_payment['paymentmethod'],
                    'journal_id': r_payment['paymentmethodid'],
                    'payment_id': r_payment['paymentid'],
                    'transaction_id': r_payment['tranid'],
                    'payment_date': datetime.strptime(r_payment['paymentdate'], "%Y-%m-%d %H:%M:%S") if r_payment[
                                                                                                            'paymentdate'] is not None else
                    order['date'],
                    'amount': float(r_payment['paidamount']),
                }

            if 'items' in r:
                for p in r['items']:
                    if not (p['barcode'] == ''):
                        # TODO think about category
                        vals = {
                            'product_id': p['productid'],
                            'name': p['productname'],
                            'default_code': p['SKU'],
                            'barcode': p['barcode'],
                            'product_uom_qty': p['orderqty'],
                            'price_unit': p['price'],
                            # 'category_id': p['category_id'],
                        }
                        products.append(vals)
                    gift_list = ['', '2', '3']
                    for g in range(0, len(gift_list)):
                        if not p['giftproduct' + gift_list[g]] == '':
                            vals = {
                                # 'product_id': p['productid'],
                                # 'name': p['productname'],
                                'default_code': p['giftproduct' + gift_list[g]],
                                # 'barcode': p['barcode'],
                                'product_uom_qty': 1,
                                'price_unit': p['giftproduct' + gift_list[g] + 'price'],
                                # 'category_id': p['category_id'],
                            }
                            products.append(vals)
                data.append((order, customer, products, payment, shipping))

        if data:
            self.create_website_order(data)
        return True

    def _cron_fetch_website_order(self, limit):
        companies = self.env['res.company'].sudo().search([('website_url', '!=', False)])
        for company in companies:
            print("company")
            print(company.name)
            website = company.website_url
            print(website)
            username = company.website_username
            print(username)
            password = company.website_password
            print(password)
            location_id = company.website_location.id
            website_warehouse = company.website_warehouse.id
            start_time = self.get_website_order_date(company.id)
            print("start_time")
            print(start_time)
            current_time = fields.Datetime.now()
            self_in_tz = self.with_context(tz=(self.env.user.tz or 'UTC'))
            price_id = self.env['product.pricelist'].search(
                [('company_id', '=', company.id), ('name', 'like', 'Public Pricelist')], limit=1)
            current_time_in_tz = fields.Datetime.context_timestamp(self_in_tz, current_time)
            data = {
                'date_from': start_time,
                'date_to': current_time_in_tz,
            }
            print(data)
            x = requests.get(url=website, params=data, auth=(username, password))
            print(x)
            text = x.text if not (x.text == '') else x.status_code
            print(text)
            result = json.loads(text)
            print("result")
            print(result)
            # error handling for no orders
            if not 'data' in result:
                return True
            data = []
            result = result['data'][:limit]
            # for r in result['data']:
            for r in result:
                print("rrr")
                print(r)
                # try:
                order = {}
                customer = {}
                products = []
                payment = {}
                shipping = {}

                # shipping/delivery charge
                try:
                    charges = float(r['shippingdetail']['shippingcharge'])
                    if charges:
                        shipping['price_unit'] = charges
                        shipping_product = self.env['product.product'].sudo().search([('name', '=', 'shipping')])
                        if not shipping_product:
                            product_name = 'shipping'
                            shipping_product = self.env['product.product'].create({
                                'responsible_id': False,
                                'name': product_name,
                                'list_price': charges,
                                'lst_price': charges,
                                'type': 'service',
                            })
                        shipping['product_id'] = shipping_product.id
                except Exception as e:
                    pass
                order.update({
                    'website_order_id': int(r['orderdetail']['orderid']),
                    'date': datetime.strptime(r['orderdetail']['orderdate'], "%Y-%m-%d %H:%M:%S") - timedelta(hours=3,
                                                                                                              minutes=0),
                    'currency': r['orderdetail']['currency'],
                    'location_id': location_id,
                    'warehouse_id': website_warehouse,
                    'pricelist_id': price_id.id,
                    'company_id': company.id,
                })
                r_customer = r['customerdetail']
                customer.update({
                    'name': r_customer['name'] or '',
                    'email': r_customer['email'] or '',
                    'phone': r_customer['mobile'] or '',

                    'block': r_customer['block_number'] or '',
                    'jaddah': r_customer['avenue_number'] or '',
                    'street': r_customer['street_number'] or '',

                    'house': r_customer['house_number'] or '',
                    'building': r_customer['building_number'] or '',
                    'floor': r_customer['floor_number'] or '',
                    'flat': r_customer['flat_number'] or '',

                    'area': r_customer['areaname'] or '',
                    'city': r_customer['city'] or '',

                    'country_id': r_customer['country'] or '',
                })

                street1 = ''
                if not customer['street'] == '':
                    street1 += 'Street: ' + customer['street'] + ', '
                if not customer['block'] == '':
                    street1 += 'Block: ' + customer['block'] + ', '
                if not customer['jaddah'] == '':
                    street1 += 'Avenue: ' + customer['jaddah']
                customer['street'] = street1

                street2 = ''
                if not customer['house'] == '':
                    street2 += 'House: ' + customer['house'] + ', '
                if not customer['building'] == '':
                    street2 += 'Bldg: ' + customer['building'] + ', '
                if not customer['floor'] == '':
                    street2 += 'Floor: ' + customer['floor'] + ', '
                if not customer['flat'] == '':
                    street2 += 'Flat: ' + customer['flat']
                customer['street2'] = street2

                city = ''
                if not customer['area'] == '':
                    city += customer['area']
                if not customer['city'] == '':
                    city += ', ' + customer['city']
                customer['city'] = city

                # find the payment matching order id
                r_payment = r['paymentdetail']

                if r_payment:
                    payment = {
                        'journal_name': r_payment['paymentmethod'],
                        'journal_id': r_payment['paymentmethodid'],
                        'payment_id': r_payment['paymentid'],
                        'transaction_id': r_payment['tranid'],
                        'payment_date': datetime.strptime(r_payment['paymentdate'], "%Y-%m-%d %H:%M:%S") if r_payment[
                                                                                                                'paymentdate'] is not None else
                        order['date'],
                        'amount': float(r_payment['paidamount']),
                        'company_id': company.id,
                    }
                if 'items' in r:
                    for p in r['items']:
                        if not (p['barcode'] == ''):
                            # TODO think about category
                            vals = {
                                'product_id': p['productid'],
                                'name': p['productname'],
                                'default_code': p['SKU'],
                                'barcode': p['barcode'],
                                'product_uom_qty': p['orderqty'],
                                'price_unit': p['price'],
                                # 'category_id': p['category_id'],
                            }
                            products.append(vals)
                        gift_list = ['', '2', '3']
                        for g in range(0, len(gift_list)):
                            if not p['giftproduct' + gift_list[g]] == '':
                                vals = {
                                    # 'product_id': p['productid'],
                                    # 'name': p['productname'],
                                    'default_code': p['giftproduct' + gift_list[g]],
                                    # 'barcode': p['barcode'],
                                    'product_uom_qty': 1,
                                    'price_unit': p['giftproduct' + gift_list[g] + 'price'],
                                    # 'category_id': p['category_id'],
                                }
                                products.append(vals)
                    data.append((order, customer, products, payment, shipping))
            if data:
                self.create_website_order(data)
        return True

    # TODO also manual update in stock location form, and product form
    def _cron_website_update_quantity(self):
        print("in")
        companies = self.env['res.company'].search([('website_url', '!=', False)])
        for company in companies:
            print("her")
            website = company.website_url
            username = company.website_username
            password = company.website_password
            location = company.website_location.id
            website_warehouse = company.website_warehouse.id
            company = company.id
            print("location")
            print(location)
            print("company")
            print(company)
            if not location:
                raise UserError("Please set website location from configuration")
            else:
                location = self.env['stock.location'].browse(location)
            self_in_tz = self.with_context(tz=(self.env.user.tz or 'UTC'))
            current_date = fields.Datetime.now()
            # current_date = fields.Datetime.context_timestamp(self_in_tz, current_date)
            print("current_date")
            print(current_date)
            last_date = self.env['ir.logging'].sudo().search(
                [('dbname', '=', self.env.cr.dbname), ('func', '=', '_cron_website_update_quantity')],
                order='create_date desc', limit=1)
            print("last_date")
            print(last_date)
            if last_date:
                last_date = last_date.create_date
                print("last_date 2")
                print(last_date)
            else:
                last_date = False
            domain = ['|', ('location_dest_id', '=', location.id), ('location_id', '=', location.id),
                      ('state', '=', 'done'),
                      # ('create_date', '<=', fields.Datetime.now())
                      ]
            print("domain")
            print(domain)
            if last_date:
                domain.append(('create_date', '<=', last_date))
                print("domain 2")
                print(domain)
            stock_moves = self.env['stock.move'].search(domain)
            print("stock_moves")
            print(stock_moves)
            # products = [move.product_id for move in stock_moves] + [move.product_id for move in stock_moves2]
            products = [move.product_id for move in stock_moves]
            products = list(dict.fromkeys(products))
            message = str(current_date)
            for p in products:
                print("11111")
                data = {
                    "barcode": p.barcode,
                    "qty": self.env['stock.quant']._get_available_quantity(p, location),
                    "locationid": 1
                }
                x = requests.post(url=website, data=data, auth=(username, password))
                text = x.text if not (x.text == '') else x.status_code
                # result = json.loads(text)
                message += " | (%s) %s" % (p.display_name, text)

            if products:
                print("2222222")
                # db_name = self._cr.dbname
                self.env['ir.logging'].sudo().create({
                    'name': 'Website integration - sync qty',
                    'type': 'server',
                    'level': 'INFO',
                    'dbname': self.env.cr.dbname,
                    'message': message,
                    'func': '_cron_website_update_quantity',
                    'path': '_cron_website_update_quantity',
                    'line': '0',
                })


class Company(models.Model):
    _inherit = 'res.company'

    website_url = fields.Char(string="website admin URL")
    website_username = fields.Char(string="website Username")
    website_password = fields.Char(string="website Password")
    website_location = fields.Many2one(string="Website Location", comodel_name='stock.location')
    website_warehouse = fields.Many2one(string="Website Warehouse", comodel_name='stock.warehouse')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    website_url = fields.Char(string="website URL")
    website_username = fields.Char(string="website Username")
    website_password = fields.Char(string="website Password")
    website_location = fields.Many2one(string="Website Location", comodel_name='stock.location')

    @api.model
    def set_values(self):
        res_config = self.env['ir.config_parameter'].sudo()
        res_config.set_param('website_integration.website_url', self.website_url)
        res_config.set_param('website_integration.website_username', self.website_username)
        res_config.set_param('website_integration.website_password', self.website_password)
        res_config.set_param('website_integration.website_location', self.website_location.id)
        super(ResConfigSettings, self).set_values()

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res_config = self.env['ir.config_parameter'].sudo()
        res['website_url'] = res_config.get_param('website_integration.website_url', default='')
        res['website_username'] = res_config.get_param('website_integration.website_username', default='')
        res['website_password'] = res_config.get_param('website_integration.website_password', default='')
        res['website_location'] = int(res_config.get_param('website_integration.website_location', default=False))
        return res
