#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#    Description: Custody Clearance                                          #
#    Author: IntelliSoft Software                                            #
#    Date: Aug 2015 -  Till Now                                              #
##############################################################################

from odoo import models, fields, api, _
from datetime import datetime
from . import amount_to_ar
from odoo.exceptions import Warning, ValidationError, _logger, UserError ,except_orm


################################
# add custody clearance approval
class custody_clearance(models.Model):
    _name = 'custody.clearance'
    _description = 'A model for tracking custody clearance.'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'clearance_no'

    def _default_employee(self):
        test2 = self.env['hr.employee'].check_access_rights('read')
        print('test',test2)
        return self.env.context.get('default_employee_id') or self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)

    def _default_partner(self):
        test = self.env['res.partner'].check_access_rights('read')
        print('test',test)
        return self.env.context.get('default_partner_id') or self.env['res.partner'].search(
            [('id', '=', self._default_employee().sudo().address_home_id.id)], limit=1)

    clearance_no = fields.Char('Clearance No.', help='Auto-generated Clearance No. for custody clearances')
    name = fields.Char('Details', compute='_get_description', store=True, readonly=True)
    cc_date = fields.Date('Date',default=fields.Date.context_today)
    requester = fields.Char('Beneficiary', required=True, default=lambda self: self.env.user.name)

    approval_id = fields.Many2one('finance.approval','Approval Reference')
    clearance_amount_new = fields.Float(compute='approval_reference',string='Requested Amount',store=True,)
    clearance_amount = fields.Float('Requested Amount',required=True)
    clearance_currency = fields.Many2one('res.currency', 'Currency',
                                         default=lambda self: self.env.user.company_id.currency_id)
    difference_amount = fields.Float('Difference Amount', readonly=True)
    clearance_amount_words = fields.Char(string='Amount in Words', readonly=True, default=False, copy=False,
                                         compute='_compute_text', translate=True)
    reason = fields.Char('Reason')
    state = fields.Selection([('draft', 'Request'),
                              ('fm_app', 'Accounting Manager Approval'),
                              ('validate', 'Validated'),
                              ('cleared', 'Cleared')],
                             string='Custody Clearance Status', default='draft', tracking=True)
    journal_id = fields.Many2one('account.journal', 'Bank/Cash Journal',
                                 help='Payment journal.',
                                 domain=[('type', 'in', ['bank', 'cash'])])
    clearance_journal_id = fields.Many2one('account.journal', 'Clearance Journal', help='Clearance Journal')
    cr_account = fields.Many2one('account.account', string="Credit Account")
    difference_move_id = fields.Many2one('account.move', 'Difference Currency Journal Entry', readonly=True, copy=False)
    move_id = fields.Many2one('account.move', 'Clearance Journal Entry', readonly=True, copy=False)
    move2_id = fields.Many2one('account.move', 'Payment/Receipt Journal Entry', readonly=True, copy=False )
    mn_remarks = fields.Text('Manager Remarks')
    auditor_remarks = fields.Text('Reviewer Remarks')
    fm_remarks = fields.Text('Finance Man. Remarks')
    view_remarks = fields.Text('View Remarks', readonly=True, compute='_get_remarks', store=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    manager_app_id = fields.Many2one('res.users', string='Approve Manager')
    dp_app_id = fields.Many2one('res.users', string='Department Manager Approve ')
    hr_app_id = fields.Many2one('res.users', string='HR Manager Approve ')
    fc_app_id = fields.Many2one('res.users', string='Approve FC')
    gm_app_id = fields.Many2one('res.users', string="Financial  Approval By")
    general_manager_id = fields.Many2one('res.users', string="GM Approval By")
    manager_id = fields.Many2one('res.users', string='Manager')
    au_app_id = fields.Many2one('res.users', string="Reviewer Approval By")
    fm_app_id = fields.Many2one('res.users', string="Financial Approval By")
    at_app_id = fields.Many2one('res.users', string="Validated By")

    # add company_id to allow this module to support multi-company
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)
    # link with finance approval
    # finance_approval_id = fields.Many2one('finance.approval', 'Finance Approval No.')
    # clearance lines
    custody_clearance_line_ids = fields.One2many('custody.clearance.line', 'custody_clearance_id',
                                                 string='Clearance Details')

    department_id = fields.Many2one('hr.department','Department')
    employee_id = fields.Many2one("hr.employee", string="Requester", required=False,default=_default_employee ,tracking=True)

    f_limit = fields.Float('Finance Manager Limit', default=lambda self: self.env.user.company_id.f_limit)
    request_type = fields.Selection([('related_ex', 'Staff Related Expenses'),('bus_related_ex', 'Pure Business Related Expenses')],string='Request Type', default='related_ex', required=True)
    request_amount_doa = fields.Float('Requested Amount',compute='get_doa_amount')
    analytic_account = fields.Many2one('account.analytic.account', string='Analytic Account/Cost Center')
    partner_id = fields.Many2one('res.partner', string='Supplier/Beneficiary',default=_default_partner)

    @api.depends('clearance_amount','clearance_currency')
    def get_doa_amount(self):
        for rec in self:
            rec.request_amount_doa = 0.0
            rec.request_amount_doa = rec.clearance_currency._convert(rec.clearance_amount, rec.env.user.company_id.doa_currency, rec.env.user.company_id,rec.cc_date)

    @api.onchange('approval_id')
    def onchange_finance_approval_id(self):
        if self.approval_id:
            self.clearance_currency = self.approval_id.request_currency.id
            # print self.approval_id.request_amount
            self.clearance_amount = self.approval_id.request_amount
            self.employee_id = self.approval_id.employee_id.id
            self.department_id = self.approval_id.department_id.id
            self.cr_account = self.approval_id.exp_account.id

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        self.manager_id = self.department_id.manager_id.user_id

    @api.depends('approval_id',)
    def approval_reference(self):
        approve_obj = self.env['finance.approval'].search([('id', '=',self.approval_id.id),
                                                           ('state','=','validate')])
        custody_obj = self.env['custody.clearance'].search([('approval_id','=',self.approval_id.id),
                                                            ('state','=', 'validate')])
        # raise ValidationError(approve_obj)
        result = 0
        if not approve_obj:
            self.clearance_amount_new = approve_obj.request_amount

        if not custody_obj:
            self.clearance_amount_new = approve_obj.request_amount
        if approve_obj:
            for i in approve_obj:
                f = i.request_amount
                for c in custody_obj:
                    result += c.clearance_amount
                self.clearance_amount_new = f - result

    # Generate name of custody automatically
    @api.depends('clearance_no', 'requester', 'clearance_amount')
    def _get_description(self):
        self.name = (self.clearance_no and ("Clearance No: " + str(self.clearance_no)) or " ") + "/" + (
                self.requester and ("Requester: " + self.requester) or " ") + "/" \
                    + (self.clearance_amount and ("Clearance Amount: " + str(self.clearance_amount)) or " ") + "/" + (
                            self.reason and ("Reason: " + self.reason) or " ")

    # # Return clearance amount in words
    # @api.depends('clearance_amount', 'clearance_currency')
    # def _compute_text(self):
    #     self.clearance_amount_words = amount_to_ar.amount_to_text_ar(self.clearance_amount,
    #                                                                  self.clearance_currency.narration_ar_un,
    #                                                                  self.clearance_currency.narration_ar_cn)

    # Return request amount in words
    @api.depends('clearance_amount', 'clearance_currency')
    def _compute_text(self):
        from . import money_to_text_en
        for r in self:
            r.clearance_amount_words = money_to_text_en.amount_to_text(r.clearance_amount,
                                                                     r.clearance_currency.name)

    # Generate remarks
    @api.depends('mn_remarks', 'auditor_remarks', 'fm_remarks')
    def _get_remarks(self):
        self.view_remarks = (self.mn_remarks and ("Manager Remarks: " + str(self.mn_remarks)) or " ") + "\n\n" + (
                self.auditor_remarks and ("Reviewer Remarks: " + str(self.auditor_remarks)) or " ") + "\n\n" + (
                                    self.fm_remarks and ("Financial Man. Remarks: " + self.fm_remarks) or " ")

    # overriding default get
    @api.model
    def default_get(self, fields):
        res = super(custody_clearance, self).default_get(fields)
        # get manager user id
        manager = self.env['res.users'].search([('id', '=', self.env.user.id)], limit=1).approval_manager.id
        if manager:
            res.update({'manager_id': manager})
        return res

    # overriding create to save number with commit
    @api.model
    def create(self, vals):
        res = super(custody_clearance, self).create(vals)
        # get custody clearance sequence no.
        next_seq = self.env['ir.sequence'].get('custody.clearance.sequence')
        res.update({'clearance_no': next_seq})
        return res

    # added to allow for submit approval
    def action_sent(self):
        # schedule activity for finance manager to approve
        # get Direct manager group
        if self.employee_id.user_id.id == self.department_id.manager_id.user_id.id:
            print('1')
            if self.request_type == 'bus_related_ex':
                fm_group_id = self.env.ref("is_accounting_approval.general_manager_access_group").id
                self.manager_app_id = self.env.user.id
            else:
                fm_group_id = self.env.ref("is_accounting_approval.hr_manager_access_group").id
            user_ids = self.env['res.users'].search([("groups_id", "=", fm_group_id)])
            # schedule activity for Direct managers(s) to approve
            print('user_ids',user_ids)
            for fm in user_ids:
                vals = {
                    'activity_type_id': self.env['mail.activity.type'].sudo().search(
                        [('name', 'like', 'Custody Clearance')],
                        limit=1).id,
                    'res_id': self.id,
                    # 'finance_id': self.id,
                    'res_model_id': self.env['ir.model'].sudo().search([('model', 'like', 'custody.clearance')],
                                                                       limit=1).id,
                    'user_id': fm.id or 1,
                    'summary': self.name,
                }
                print('vals', vals)

                # add lines
                self.env['mail.activity'].sudo().create(vals)
        else:
            fm_group_id = self.env.ref("is_accounting_approval.db_manager_access_group").id
            # first of all get all Direct managers / advisors
            user_ids = self.env['res.users'].search(
                [("groups_id", "=", fm_group_id)])
            # schedule activity for Direct managers(s) to approve
            for fm in user_ids:
                if fm.id == self.department_id.manager_id.user_id.id :
                    vals = {
                        'activity_type_id': self.env['mail.activity.type'].sudo().search(
                            [('name', 'like', 'Custody Clearance')],
                            limit=1).id,
                        'res_id': self.id,
                        # 'finance_id': self.id,
                        'res_model_id': self.env['ir.model'].sudo().search([('model', 'like', 'custody.clearance')],
                                                                           limit=1).id,
                        'user_id': fm.id or 1,
                        'summary': self.name,
                    }

                    # add lines
                    self.env['mail.activity'].sudo().create(vals)
            # change state
        self.state = 'fm_app'
        self.env['mail.activity'].search([('user_id', '=', self.env.uid), ('res_id', '=', self.id)]).action_done()
        self.user_id = self.env.user.id
        return True

    # added to allow for Accountant approval
    def accountant_approval(self):
        self.activity_ids.unlink()
        # schedule activity for finance manager to approve
        # get Direct manager group
        print('doa',self.request_amount_doa)
        fm_group_id = self.env.ref("is_accounting_approval.validator_access_group").id

        # first of all get all Direct managers / advisors
        user_ids = self.env['res.users'].search([("groups_id", "=", fm_group_id)])

        # schedule activity for Direct managers(s) to approve
        for fm in user_ids:
            vals = {
                'activity_type_id': self.env['mail.activity.type'].sudo().search(
                    [('name', 'like', 'Custody Clearance')],
                    limit=1).id,
                'res_id': self.id,
                # 'finance_id': self.id,
                'res_model_id': self.env['ir.model'].sudo().search([('model', 'like', 'custody.clearance')],
                                                                   limit=1).id,
                'user_id': fm.id,
                'summary': self.name,
            }

            # add lines
            self.env['mail.activity'].sudo().create(vals)
        # change state
        self.state = 'validate'
        self.env['mail.activity'].search([('user_id', '=', self.env.uid), ('res_id', '=', self.id)]).action_done()
        self.fc_app_id = self.env.user.id
        return True

    # reject custody approval
    def reject(self):
        self.state = 'reject'

        # Update footer message
        message_obj = self.env['mail.message']
        message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
        msg_id = self.message_post(body=message)

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("You can not delete a record not in draft state!"))
        return super(custody_clearance, self).unlink()

    # validate, i.e. post to account moves
    @api.model
    def get_currency(self, line=None, total=None):
        if total:
            return total / self.clearance_currency.rate
        if self.clearance_currency != self.env.user.company_id.currency_id:
            return line.amount / self.clearance_currency.rate
        else:
            return line.amount

    # schedule activity to accountant to validate
    def schedule_fm(self):
        # get accountant/validator group
        at_group_id = self.env['res.groups'].sudo().search([('name', 'like', 'Validator')], limit=1).id

        # first of all get all finance managers / advisors
        self.env.cr.execute('''SELECT uid FROM res_groups_users_rel WHERE gid = %s order by uid''' % (at_group_id))

        # schedule activity for advisors(s) to validate
        for at in list(filter(lambda x: (
                self.env['res.users'].sudo().search([('id', '=', x)]).company_id == self.company_id),
                              self.env.cr.fetchall())):
            vals = {
                'activity_type_id': self.env['mail.activity.type'].sudo().search([('name', 'like', 'Custody Clearance')],
                                                                                 limit=1).id,
                'res_id': self.id,
                'res_model_id': self.env['ir.model'].sudo().search([('model', 'like', 'custody.clearance')], limit=1).id,
                'user_id': at[0] or 1,
                'summary': self.name,
            }

            # add lines
            self.env['mail.activity'].sudo().create(vals)

    def validate_diffrence(self):
        if self.cr_account != self.approval_id.exp_account:
            raise ValidationError(_("Clearance Credit Account Must be the same as the  Approval Credit Account"))
        if self.clearance_currency != self.env.user.company_id.currency_id:
            clear_amount = self.clearance_currency._convert(self.clearance_amount, self.env.user.company_id.currency_id,self.env.user.company_id,fields.Date.context_today(self))
            approval_amount = self.approval_id.move_id.amount_total_signed
            print('clear_amount',clear_amount,approval_amount)
            if approval_amount > clear_amount:
                amount = approval_amount - clear_amount
                temp_move_line_db = {'move_id': self.difference_move_id.id,
                                     'name': self.clearance_no + ": Entry of Curreny difference",
                                     'account_id': self.env.user.company_id.expense_currency_exchange_account_id.id,
                                     'partner_id': self.partner_id.id,
                                     'debit': amount,
                                     'company_id': self.company_id.id,
                                     }
                # add credit entry
                temp_move_line_cr = {'move_id': self.difference_move_id.id,
                                     'name': self.clearance_no + ": Entry of Curreny difference",
                                     'account_id': self.cr_account.id,
                                     'partner_id': self.partner_id.id,
                                     'analytic_account_id': self.analytic_account.id,
                                     'credit': amount,
                                     'company_id': self.company_id.id,
                                     }
                account_move_vals = {'journal_id': self.env.user.company_id.currency_exchange_journal_id.id,
                                     'date': fields.Date.context_today(self),
                                     'ref': self.clearance_no,
                                     'company_id': self.company_id.id,
                                     'line_ids': [(0, 0, temp_move_line_db), (0, 0, temp_move_line_cr)]
                                     }
                self.difference_move_id = self.env['account.move'].create(account_move_vals)

            elif approval_amount < clear_amount:
                amount = clear_amount - approval_amount
                temp_move_line_db = {'move_id': self.difference_move_id.id,
                                     'name': self.clearance_no + ": Entry of Curreny difference",
                                     'account_id': self.cr_account.id,
                                     'analytic_account_id': self.analytic_account.id,
                                     'partner_id': self.partner_id.id,
                                     'debit': amount,
                                     'company_id': self.company_id.id,
                                     }
                # add credit entry
                temp_move_line_cr = {'move_id': self.difference_move_id.id,
                                     'name': self.clearance_no + ": Entry of Curreny difference",
                                     'account_id': self.env.user.company_id.income_currency_exchange_account_id.id,
                                     'credit': amount,
                                     'partner_id': self.partner_id.id,
                                     'company_id': self.company_id.id,
                                     }
                account_move_vals = {'journal_id': self.env.user.company_id.currency_exchange_journal_id.id,
                                     'date': fields.Date.context_today(self),
                                     'ref': self.clearance_no,
                                     'company_id': self.company_id.id,
                                     'line_ids': [(0, 0, temp_move_line_db), (0, 0, temp_move_line_cr)]
                                     }
                self.difference_move_id = self.env['account.move'].create(account_move_vals)

    # validate and check difference
    def validate(self):
        if not self.clearance_journal_id:
            raise Warning(_("Clearance journal must be selected!"))
        if not self.journal_id:
            raise Warning(_("Payment journal must be selected!"))
        if not self.cr_account:
            raise Warning(_("Credit account must be selected!"))

        #################
        # clearance part #
        #################
        # account move entry
        db_total = 0
        entries = []
        print("x")
        for line in self.custody_clearance_line_ids:
            print("y")
            if not line.exp_account:
                raise ValidationError(_("Please select account!"))

            debit_val = {
                'move_id': self.move_id.id,
                'name': line.name,
                'account_id': line.exp_account.id,
                'debit': line.amount,
                'partner_id': self.partner_id.id,
                'analytic_account_id': line.analytic_account.id or self.analytic_account.id,
                'currency_id': (self.clearance_currency != self.env.user.company_id.currency_id)
                               and self.clearance_currency.id or None,
                'amount_currency': (self.clearance_currency != self.env.user.company_id.currency_id) and line.amount
                                   or None,
                'company_id': self.company_id.id,
            }
            entries.append((0, 0, debit_val))
            db_total += line.amount
            print(entries, '####################')
            print(line.amount)


        # create credit entry which is total of debit
        print("z")
        credit_val = {
            'move_id': self.move_id.id,
            'name': db_total,
            # 'account_id': self.approval_id.journal_id.default_credit_account_id.id,
            'account_id': self.cr_account.id,
            'partner_id': self.partner_id.id,
            'credit':  self.clearance_amount,
            'currency_id': (self.clearance_currency != self.env.user.company_id.currency_id)
                           and self.clearance_currency.id or None,
            'amount_currency': (self.clearance_currency != self.env.user.company_id.currency_id) and -(db_total)
                               or None,
            'company_id': self.company_id.id,
        }
        entries.append((0, 0, credit_val))
        print("t")
        print("oooooooooooooooooooooo", credit_val)
        vals = {
            'journal_id': self.clearance_journal_id.id,
            'date': fields.Date.context_today(self),
            # 'customer_name': self.requester,
            'ref': self.clearance_no,
            'company_id': self.company_id.id,
            'line_ids': entries,
        }
        print("o")
        # self.move_id = self.env['account.move'].create(vals)

        ##################
        # difference part#
        ##################
        # get difference
        self.difference_amount = self.clearance_amount - db_total
        print("w")
        print("test")
        if self.difference_amount == 0:
            print("1")
            # Change state if all went well!
            self.schedule_fm()
            self.state = 'cleared'
            self.at_app_id = self.env.user.id
            self.move_id = self.env['account.move'].create(vals)

            # Update footer message
            message_obj = self.env['mail.message']
            message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
            msg_id = self.message_post(body=message)
            self.env['mail.activity'].search([('user_id', '=', self.env.uid), ('res_id', '=', self.id)]).action_done()
        # difference greater
        elif self.difference_amount > 0:
            print("2")
            # account move entry
            if self.clearance_currency == self.env.user.company_id.currency_id:
                temp_move_line_db = {
                    'move_id': self.move2_id.id,
                    'name': self.name + ": Receipt of difference",
                    'account_id': self.journal_id.default_account_id.id,
                    'partner_id': self.partner_id.id,
                    'debit': self.difference_amount,
                    'company_id': self.company_id.id,
                }
                # add credit entry
                temp_move_line_cr = {'move_id': self.move2_id.id,
                                     'name': self.name + ": Receipt of difference",
                                     'account_id': self.cr_account.id,
                                     'partner_id': self.partner_id.id,
                                     'credit': self.difference_amount,
                                     'company_id': self.company_id.id,
                                     }
                account_move_vals = {'journal_id': self.journal_id.id,
                                     'date': fields.Date.context_today(self),
                                     'ref': self.clearance_no,
                                     # 'customer_name': self.requester,
                                     'company_id': self.company_id.id,
                                     'line_ids': [(0, 0, temp_move_line_db), (0, 0, temp_move_line_cr)]
                                     }
                self.move2_id = self.env['account.move'].create(account_move_vals)

                # Change state if all went well!
                self.schedule_fm()
                self.state = 'cleared'
                self.at_app_id = self.env.user.id

                # Update footer message
                message_obj = self.env['mail.message']
                message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
                msg_id = self.message_post(body=message)
                self.env['mail.activity'].search([('user_id', '=', self.env.uid), ('res_id', '=', self.id)]).action_done()
            elif self.clearance_currency != self.env.user.company_id.currency_id:
                temp_move_line_db = {'move_id': self.move2_id.id,
                                     'name': self.name + ": Receipt of difference",
                                     'account_id': self.journal_id.default_account_id.id,
                                     'currency_id': self.clearance_currency.id,
                                     'partner_id': self.partner_id.id,
                                     'amount_currency': self.difference_amount,
                                     'debit': self.clearance_currency._convert(self.difference_amount, self.env.user.company_id.currency_id, self.env.user.company_id, fields.Date.context_today(self)),
                                     'company_id': self.company_id.id,
                                     }
                # add credit entry
                temp_move_line_cr = {'move_id': self.move2_id.id,
                                     'name': self.name + ": Receipt of difference",
                                     'account_id': self.cr_account.id,
                                     'currency_id': self.clearance_currency.id,
                                     'partner_id': self.partner_id.id,
                                     'amount_currency': -self.difference_amount,
                                     'credit': self.clearance_currency._convert(self.difference_amount, self.env.user.company_id.currency_id, self.env.user.company_id, fields.Date.context_today(self)),
                                     'company_id': self.company_id.id,
                                     }
                account_move_vals = {'journal_id': self.journal_id.id,
                                     'date': fields.Date.context_today(self),
                                     'ref': self.clearance_no,
                                     # 'customer_name': self.requester,
                                     'company_id': self.company_id.id,
                                     'line_ids': [(0, 0, temp_move_line_db), (0, 0, temp_move_line_cr)]
                                     }

                self.move2_id = self.env['account.move'].create(account_move_vals)

                # Change state if all went well!
                self.schedule_fm()
                self.state = 'cleared'
                self.at_app_id = self.env.user.id

                # Update footer message
                message_obj = self.env['mail.message']
                message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
                msg_id = self.message_post(body=message)
                self.env['mail.activity'].search([('user_id', '=', self.env.uid), ('res_id', '=', self.id)]).action_done()
            else:
                raise Warning(_("An issue was faced when validating difference!"))
        # difference less
        elif self.difference_amount < 0:
            print("3")
            # account move entry
            if self.clearance_currency == self.env.user.company_id.currency_id:
                temp_move_line_db = {'move_id': self.move2_id.id,
                                     'name': self.name + ": Payment of difference",
                                     'account_id': self.cr_account.id,
                                     'analytic_account_id': self.analytic_account.id,
                                     'partner_id': self.partner_id.id,
                                     'debit': abs(self.difference_amount),
                                     'company_id': self.company_id.id,
                                     }
                # add credit entry
                temp_move_line_cr = {'move_id': self.move2_id.id,
                                     'name': self.name + ": Payment of difference",
                                     'account_id': self.journal_id.default_credit_account_id.id,
                                     'partner_id': self.partner_id.id,
                                     'credit': abs(self.difference_amount),
                                     'company_id': self.company_id.id,
                                     }

                account_move_vals = {'journal_id': self.journal_id.id,
                                     'date': fields.Date.context_today(self),
                                     'ref': self.clearance_no,
                                     # 'customer_name': self.requester,
                                     'company_id': self.company_id.id,
                                     'line_ids': [(0, 0, temp_move_line_db), (0, 0, temp_move_line_cr)]
                                     }
                self.move2_id = self.env['account.move'].create(account_move_vals)

                # Change state if all went well!
                self.schedule_fm()
                self.state = 'cleared'
                self.at_app_id = self.env.user.id

                # Update footer message
                message_obj = self.env['mail.message']
                message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
                msg_id = self.message_post(body=message)
                self.env['mail.activity'].search([('user_id', '=', self.env.uid), ('res_id', '=', self.id)]).action_done()
            elif self.clearance_currency != self.env.user.company_id.currency_id:
                temp_move_line_db = {'move_id': self.move2_id.id,
                                     'name': self.name + ": Payment of difference",
                                     'account_id': self.cr_account.id,
                                     'partner_id': self.partner_id.id,
                                     'currency_id': self.clearance_currency.id,
                                     'amount_currency': abs(self.difference_amount),
                                     'analytic_account_id': self.analytic_account.id,
                                     'debit': self.clearance_currency._convert(abs(self.difference_amount), self.env.user.company_id.currency_id, self.env.user.company_id, fields.Date.context_today(self)),
                                     'company_id': self.company_id.id,
                                     }
                # add credit entry
                temp_move_line_cr = {'move_id': self.move2_id.id,
                                     'name': self.name + ": Payment of difference",
                                     'account_id': self.journal_id.default_account_id.id,
                                     'partner_id': self.partner_id.id,
                                     'currency_id': self.clearance_currency.id,
                                     'amount_currency': -(abs(self.difference_amount)),
                                     'credit': self.clearance_currency._convert(abs(self.difference_amount), self.env.user.company_id.currency_id, self.env.user.company_id, fields.Date.context_today(self)),
                                     'company_id': self.company_id.id,
                                     }
                account_move_vals = {'journal_id': self.journal_id.id,
                                     'date': fields.Date.context_today(self),
                                     # 'customer_name': self.requester,
                                     'ref': self.clearance_no,
                                     'company_id': self.company_id.id,
                                     'line_ids': [(0, 0, temp_move_line_db), (0, 0, temp_move_line_cr)]
                                     }
                self.move2_id = self.env['account.move'].create(account_move_vals)

                # Change state if all went well!
                self.schedule_fm()
                self.state = 'cleared'
                self.at_app_id = self.env.user.id
                # Update footer message
                message_obj = self.env['mail.message']
                message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
                msg_id = self.message_post(body=message)
                self.env['mail.activity'].search([('user_id', '=', self.env.uid), ('res_id', '=', self.id)]).action_done()
        else:
            raise Warning(_("An issue was faced when validating!"))
        self.validate_diffrence()
        # Update footer message
        message_obj = self.env['mail.message']
        message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
        msg_id = self.message_post(body=message)

        self.move_id.post()
        if self.move2_id:
            self.move2_id.post()

    def set_to_draft(self):
        self.state = 'draft'
        self.au_app_id = None
        self.dp_app_id = None
        self.hr_app_id = None
        self.fm_app_id = None
        self.gm_app_id = None
        self.at_app_id = None

        # Update footer message
        message_obj = self.env['mail.message']
        message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
        msg_id = self.message_post(body=message)

    def cancel_button(self):
        self.move_id.button_cancel()
        if self.move2_id:
            self.move2_id.button_cancel()
        self.state = 'reject'


################################################
# Custody clearance line model
class custody_clearance_line(models.Model):
    _name = 'custody.clearance.line'
    _description = 'Custody clearance details.'

    custody_clearance_id = fields.Many2one('custody.clearance', string='Custody Clearance', ondelete="cascade")
    name = fields.Char('Narration', required=True)
    amount = fields.Float('Amount', required=True)
    notes = fields.Char('Notes')
    exp_account = fields.Many2one('account.account', string="Expense or Debit Account")
    analytic_account = fields.Many2one('account.analytic.account', string='Analytic Account/Cost Center')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)
