#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#    Description: Accounting Approval                                        #
#    Author: IntelliSoft Software                                            #
#    Date: Aug 2015 -  Till Now                                              #
##############################################################################


from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import Warning, ValidationError, _logger, UserError
from odoo.tools.float_utils import float_compare, float_round, float_is_zero



########################################




#####################################
# add financial approval
class FinanceApproval(models.Model):
    _name = 'finance.approval'
    _description = 'A model for tracking finance approvals.'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'approval_no'

    def _default_employee(self):
        return self.env.context.get('default_employee_id') or self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)

    def _default_partner(self):
        test = self.env['res.partner'].check_access_rights('read')
        print('test',test)
        return self.env.context.get('default_partner_id') or self.env['res.partner'].search(
            [('id', '=', self._default_employee().sudo().address_home_id.id)], limit=1)

    approval_no = fields.Char('Approval No.', help='Auto-generated Approval No. for finance approvals')
    activity_ids = fields.One2many('mail.activity', 'finance_id', 'Activity')
    name = fields.Char('Details', compute='_get_description', store=True, readonly=True)
    fa_date = fields.Date('Date', default=fields.Date.context_today, readonly=True)
    requester = fields.Char('Beneficiary', required=True, default=lambda self: self.env.user.name)
    beneficiary = fields.Many2one('res.partner', 'Beneficiary')
    request_amount = fields.Float('Requested Amount', required=True)
    request_currency = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id)
    request_amount_doa = fields.Float('Requested Amount',compute='get_doa_amount')
    request_amount_words = fields.Char(string='Amount in Words', readonly=True, default=False, copy=False,
                                       compute='_compute_text', translate=True)
    employee_id = fields.Many2one("hr.employee", string="Requester", required=False,default=_default_employee ,tracking=True)
    department_id = fields.Many2one("hr.department", string="Department", related='employee_id.department_id', readonly=False, store=True)
    reason = fields.Char('Reason', required=True)
    state = fields.Selection([('draft', 'Request'),
                              ('gm_app', 'General Manager'),
                              ('fm_app', 'Accountant'),
                              ('au_app', 'To validate'),
                              ('reject', 'Rejected'),
                              ('validate', 'Validated'),
                              ('cleared', 'Cleared')],
                             string='Finance Approval Status', default='draft', tracking=True)
    exp_account = fields.Many2one('account.account', string="Expense or Debit Account")
    request_type = fields.Selection([('related_ex', 'Staff Related Expenses'),('bus_related_ex', 'Pure Business Related Expenses')],string='Request Type', default='related_ex', required=True)
    payment_method = fields.Selection(
        selection=[('cash', 'Cash'), ('cheque', 'Cheque'), ('transfer', 'Transfer'),
                   ('trust', 'Trust'), ('other', 'Other')], string='Payment Method')
    payment_method_name = fields.Many2one('account.payment.method')
    pa_name = fields.Char(related="payment_method_name.name")
    journal_id = fields.Many2one('account.journal', 'Bank/Cash Journal',
                                 help='Payment journal.',
                                 domain="[('type', 'in', ['bank', 'cash'])]")
    bank_journal_id = fields.Many2one('account.journal', 'Check bank Journal',
                                      help='Payment journal.',
                                      domain=[('type', '=', 'bank')])
    move_id = fields.Many2one('account.move', 'Journal Entry', readonly=True)
    mn_remarks = fields.Text('Manager Remarks')
    auditor_remarks = fields.Text('Reviewer Remarks')
    fm_remarks = fields.Text('Finance Man. Remarks')
    gm_remarks = fields.Text('General Man. Remarks')
    view_remarks = fields.Text('View Remarks', readonly=True, compute='_get_remarks', store=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    manager_app_id = fields.Many2one('res.users', string='Approve Manager')
    partner_id = fields.Many2one('res.partner', string='Supplier/Beneficiary',default=_default_partner)
    au_app_id = fields.Many2one('res.users', string="Manager Approval By")
    fm_app_id = fields.Many2one('res.users', string="Reviewer Approval By")
    gm_app_id = fields.Many2one('res.users', string="Financial  Approval By")
    general_manager_id = fields.Many2one('res.users', string="GM Approval By")
    at_app_id = fields.Many2one('res.users', string="Validated By")
    # add company_id to allow this module to support multi-company
    company_id = fields.Many2one('res.company', string="Company")
    # adding analytic account
    analytic_account = fields.Many2one('account.analytic.account', string='Analytic Account/Cost Center')

    check_date = fields.Date('Check Date')
    Account_No = fields.Char('Account Number')
    Bank_id = fields.Many2one(related='journal_id.bank_id')
    Check_no = fields.Char('Check Number')
    # checks_id = fields.Many2one('check.safe', 'chq Ref')
    finance_approval_line_ids = fields.One2many('finance.approval.line', 'finance_id',
                                                string='Finance Approval Details')
    custody = fields.Boolean(string='Custody')

    is_petty_cash = fields.Boolean(string='Is Petty Cash')
    limit = fields.Float(related='journal_id.limit')
    acc_approval_amount = fields.Float('Acc Approval Amount')

    @api.depends('request_amount','request_currency')
    def get_doa_amount(self):
        for rec in self:
            rec.request_amount_doa = 0.0
            rec.request_amount_doa = rec.request_currency._convert(rec.request_amount, rec.env.user.company_id.doa_currency, rec.env.user.company_id,fields.Date.context_today(self))

    # Generate name of approval automatically
    @api.depends('approval_no', 'requester', 'beneficiary')
    # @api.onchange('approval_no', 'requester', 'beneficiary')
    def _get_description(self):
        self.name = (self.approval_no and ("Approval No: " + str(self.approval_no)) or " ") + "/" + (
                self.requester and ("Requester: " + self.requester) or " ") + "/" \
                    + (self.beneficiary and ("Beneficiary: " + self.beneficiary) or " ") + "/" + (
                            self.reason and ("Reason: " + self.reason) or " ")

    # Return request amount in words
    @api.depends('request_amount', 'request_currency')
    def _compute_text(self):
        from . import money_to_text_en
        for r in self:
            r.request_amount_words = ''
            r.request_amount_words = money_to_text_en.amount_to_text(r.request_amount,
                                                                     r.request_currency.name)

    # Generate name of approval automatically
    @api.depends('mn_remarks', 'auditor_remarks', 'fm_remarks', 'gm_remarks')
    # @api.onchange('mn_remarks', 'auditor_remarks', 'fm_remarks', 'gm_remarks')
    def _get_remarks(self):
        for rec in self :
            rec.view_remarks = (rec.mn_remarks and ("Manager Remarks: " + str(rec.mn_remarks)) or " ") + "\n\n" + (
                    rec.auditor_remarks and ("Account Manager Remarks: " + str(rec.auditor_remarks)) or " ") + "\n\n" + (
                                        rec.fm_remarks and ("Financial Man. Remarks: " + rec.fm_remarks) or " ") + "\n\n" + (
                                        rec.gm_remarks and ("General Man. Remarks: " + rec.gm_remarks) or " ")


    @api.model
    def create(self, vals):
        res = super(FinanceApproval, self).create(vals)
        # get finance approval sequence no.
        next_seq = self.env['ir.sequence'].get('finance.approval.sequence')
        res.update({'approval_no': next_seq})
        return res

    # added to allow for submit approval
    def action_sent(self):
        self.state = 'gm_app'
        return True

    # general GM approval
    def gm_approval(self):
        self.state = 'fm_app'
        return True

    # added to allow for audit approval
    def action_to_audit(self):
        self.state = 'au_app'
        return True

    # added to allow for Accountant approval
    def accountant_approval(self):
        self.activity_ids.unlink()
        line_ids = []
        for x in self.finance_approval_line_ids:
            # if x.pa_name == 'Checks':
            #     print(x, "####")
            line = (0, 0, {
                'name': x.name,
                'account_id': x.exp_account.id,
                'analytic_account_id': x.analytic_account_id.id,
                'amount': x.amount,

            })
            line_ids.append(line)

        # dictionary['account_ids'] = line_ids
        # check_obj = self.env['check.safe']
        if not self.exp_account and self.custody == True:
            raise ValidationError(_("Expense or debit account must be selected!"))

        if not self.journal_id and not self.bank_journal_id:
            raise ValidationError(_("Journal must be selected!"))
        # if self.is_petty_cash == False:
        # account move entry
        if self.request_currency == self.env.user.company_id.currency_id:
            # corresponding details in account_move_line
            # if self.pa_name in ('Journal Entry', 'Manual', 'كاش', 'قيد'):
            self.move_id = self.env['account.move'].create(self.move_without_check())
            self.move_id.post()
            self.state = 'validate'
            # self.mn_app_id = self.env.user.id
            # Update footer message
            message_obj = self.env['mail.message']
            message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
            msg_id = self.message_post(body=message)
        elif self.request_currency != self.env.user.company_id.currency_id:
            if self.finance_approval_line_ids:
                total_am = 0
                entrys = []
                for line1 in self.finance_approval_line_ids:
                    if not line1.exp_account:
                        raise ValidationError(_("Expense or debit account must be selected!"))
                    total_am += self.request_currency._convert(line1.amount, self.env.user.company_id.currency_id,
                                                               self.env.user.company_id,
                                                               fields.Date.context_today(self))

                    debit_vals = {
                        'move_id': self.move_id.id,
                        'name': self.approval_no + '/' + str(line1.name),
                        'partner_id': self.partner_id.id,
                        'account_id': line1.exp_account.id,
                        'analytic_account_id': line1.analytic_account_id.id,
                        'debit': self.request_currency._convert(line1.amount, self.env.user.company_id.currency_id,
                                                                self.env.user.company_id,
                                                                fields.Date.context_today(self)),
                        'currency_id': self.request_currency.id,
                        'amount_currency': line1.amount,
                        'company_id': self.company_id.id,
                    }
                    entrys.append((0, 0, debit_vals))
                total = '%.2f' % total_am
                credit_val = {'move_id': self.move_id.id,
                              'name': self.approval_no + '/' + str(self.reason),
                              'partner_id': self.partner_id.id,
                              'account_id': self.journal_id.default_account_id.id,
                              'credit': total_am,
                              'currency_id': self.request_currency.id,
                              'amount_currency': - self.request_amount,
                              'company_id': self.company_id.id,
                              }
                entrys.append((0, 0, credit_val))
                print('entrys', entrys)
                vals = {
                    'journal_id': self.journal_id.id,
                    'date': fields.Date.context_today(self),
                    'ref': self.approval_no + '/' + str(self.reason),
                    'company_id': self.company_id.id,
                    'line_ids': entrys
                }
            else:
                # total_am += self.request_amount
                if not self.exp_account:
                    raise ValidationError(_("Expense or debit account must be selected!"))
                debit_val = {
                    'move_id': self.move_id.id,
                    'name': self.approval_no + '/' + str(self.reason),
                    'partner_id': self.partner_id.id,
                    'account_id': self.exp_account.id,
                    'analytic_account_id': self.analytic_account.id,
                    'debit': self.request_currency._convert(self.request_amount, self.env.user.company_id.currency_id,
                                                            self.env.user.company_id, fields.Date.context_today(self)),
                    'currency_id': self.request_currency.id,
                    'amount_currency': self.request_amount,
                    'company_id': self.company_id.id,
                }
                credit_val = {'move_id': self.move_id.id,
                              'name': self.approval_no + '/' + str(self.reason),
                              'partner_id': self.partner_id.id,
                              'account_id': self.journal_id.default_account_id.id,
                              'credit': self.request_currency._convert(self.request_amount,
                                                                       self.env.user.company_id.currency_id,
                                                                       self.env.user.company_id, fields.Date.today()),
                              'currency_id': self.request_currency.id,
                              'amount_currency': -self.request_amount,
                              'company_id': self.company_id.id,
                              }
                vals = {
                    'journal_id': self.journal_id.id,
                    'date': fields.Date.context_today(self),
                    'ref': self.approval_no + '/' + str(self.reason),
                    'company_id': self.company_id.id,
                    'line_ids': [(0, 0, debit_val), (0, 0, credit_val)]
                }
            # add lines
            self.move_id = self.env['account.move'].create(vals)
            self.move_id.post()
            self.state = 'validate'
            # self.env['mail.activity'].search([('user_id', '=', self.env.uid), ('res_id', '=', self.id)]).action_done()
            self.at_app_id = self.env.user.id
        else:
            raise ValidationError(_("An issue was faced when validating!"))

        # Update footer message
        message_obj = self.env['mail.message']
        message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
        msg_id = self.message_post(body=message)
        self.env['mail.activity'].search([('user_id', '=', self.env.uid), ('res_id', '=', self.id)]).action_done()
        # else:
        # acc_approval_amount = self._get_acc_approval_amount()
        # if not  self.finance_approval_line_ids:
        #     raise ValidationError(_("Please select account!"))
        if self.acc_approval_amount - self.request_amount < self.limit and self.journal_id.is_petty_cash:
            raise ValidationError(_("Petty Cash Limit !!!!"))
        self.state = 'validate'
        self.at_app_id = self.env.user.id
        return True

    def cancel_button(self):
        self.move_id.button_cancel()
        self.move_id.unlink()
        self.state = 'draft'

    # reject finance approval
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
        return super(FinanceApproval, self).unlink()

    def move_without_check(self):
        entrys = []
        if self.finance_approval_line_ids:
            total = 0.0
            for line1 in self.finance_approval_line_ids:
                if not line1.exp_account:
                    raise ValidationError(_("Please select account!"))
                total += line1.amount
                debit_val = {
                    'name': self.approval_no + '/' + str(line1.name),
                    'partner_id': line1.partner_id.id,
                    'account_id': line1.exp_account.id,
                    'debit': line1.amount,
                    'analytic_account_id': line1.analytic_account_id.id,
                    'company_id': self.company_id.id,
                }
                # print "debit val", debit_val
                entrys.append((0, 0, debit_val))
            credit_vals = {
                'name': self.approval_no + '/' + self.reason,
                'partner_id': self.partner_id.id,
                'account_id': self.journal_id.id,
                'credit': total,
                'company_id': self.company_id.id,
            }
        else:
            if not self.exp_account:
                raise ValidationError(_("Please select account!"))
            debit_val = {
                'name': self.approval_no + '/' + self.reason,
                'partner_id': self.partner_id.id,
                'account_id': self.exp_account.id,
                'debit': self.request_amount,
                'analytic_account_id': self.analytic_account.id,
                'company_id': self.company_id.id,
            }
            # print "debit val", debit_val
            entrys.append((0, 0, debit_val))

            credit_vals = {
                'name': self.approval_no + '/' + self.reason,
                'partner_id': self.partner_id.id,
                'account_id': self.journal_id.default_account_id.id,
                'credit': self.request_amount,
                'company_id': self.company_id.id,
            }
        print('entrys')
        entrys.append((0, 0, credit_vals))
        vals = {
            'journal_id': self.journal_id.id,
            'date': fields.Date.context_today(self),
            'ref': self.approval_no + '/' + str(self.reason),
            'company_id': self.company_id.id,
            'line_ids': entrys
        }
        print('vals',vals)
        return vals

    def validate(self):
        self.activity_ids.unlink()
        line_ids = []
        for x in self.finance_approval_line_ids:
            # if x.pa_name == 'Checks':
            #     print(x, "####")
            line = (0, 0, {
                'name': x.name,
                'account_id': x.exp_account.id,
                'analytic_account_id': x.analytic_account_id.id,
                'amount': x.amount,

            })
            line_ids.append(line)

        # dictionary['account_ids'] = line_ids
        # check_obj = self.env['check.safe']
        if not self.exp_account and self.custody == True:
            raise ValidationError(_("Expense or debit account must be selected!"))

        if not self.journal_id and not self.bank_journal_id:
            raise ValidationError(_("Journal must be selected!"))
    # if self.is_petty_cash == False:
    # account move entry
        if self.request_currency == self.env.user.company_id.currency_id:
            # corresponding details in account_move_line
            # if self.pa_name in ('Journal Entry', 'Manual', 'كاش', 'قيد'):
            self.move_id = self.env['account.move'].create(self.move_without_check())
            self.move_id.post()
            self.state = 'validate'
            # self.mn_app_id = self.env.user.id
            # Update footer message
            message_obj = self.env['mail.message']
            message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
            msg_id = self.message_post(body=message)
        elif self.request_currency != self.env.user.company_id.currency_id:
            if self.finance_approval_line_ids:
                total_am = 0
                entrys = []
                for line1 in self.finance_approval_line_ids:
                    if not line1.exp_account:
                        raise ValidationError(_("Expense or debit account must be selected!"))
                    total_am += self.request_currency._convert(line1.amount, self.env.user.company_id.currency_id, self.env.user.company_id,fields.Date.context_today(self))

                    debit_vals = {
                        'move_id': self.move_id.id,
                        'name': self.approval_no + '/' + str(line1.name),
                        'partner_id': self.partner_id.id,
                        'account_id': line1.exp_account.id,
                        'analytic_account_id': line1.analytic_account_id.id,
                        'debit': self.request_currency._convert(line1.amount, self.env.user.company_id.currency_id, self.env.user.company_id,fields.Date.context_today(self)),
                        'currency_id': self.request_currency.id,
                        'amount_currency': line1.amount,
                        'company_id': self.company_id.id,
                    }
                    entrys.append((0, 0, debit_vals))
                total = '%.2f' % total_am
                credit_val = {'move_id': self.move_id.id,
                              'name': self.approval_no + '/' + str(self.reason),
                              'partner_id': self.partner_id.id,
                              'account_id': self.journal_id.default_account_id.id,
                              'credit': total_am,
                              'currency_id': self.request_currency.id,
                              'amount_currency': - self.request_amount,
                              'company_id': self.company_id.id,
                              }
                entrys.append((0, 0, credit_val))
                print('entrys',entrys)
                vals = {
                    'journal_id': self.journal_id.id,
                    'date': fields.Date.context_today(self),
                    'ref': self.approval_no + '/' + str(self.reason),
                    'company_id': self.company_id.id,
                    'line_ids': entrys
                }
            else:
                # total_am += self.request_amount
                if not self.exp_account:
                    raise ValidationError(_("Expense or debit account must be selected!"))
                debit_val = {
                    'move_id': self.move_id.id,
                    'name': self.approval_no + '/' + str(self.reason),
                    'partner_id': self.partner_id.id,
                    'account_id': self.exp_account.id,
                    'analytic_account_id': self.analytic_account.id,
                    'debit': self.request_currency._convert(self.request_amount, self.env.user.company_id.currency_id, self.env.user.company_id, fields.Date.context_today(self)),
                    'currency_id': self.request_currency.id,
                    'amount_currency': self.request_amount,
                    'company_id': self.company_id.id,
                }
                credit_val = {'move_id': self.move_id.id,
                              'name': self.approval_no + '/' + str(self.reason),
                              'partner_id': self.partner_id.id,
                              'account_id': self.journal_id.default_account_id.id,
                              'credit': self.request_currency._convert(self.request_amount, self.env.user.company_id.currency_id, self.env.user.company_id, fields.Date.today()),
                              'currency_id': self.request_currency.id,
                              'amount_currency': -self.request_amount,
                              'company_id': self.company_id.id,
                              }
                vals = {
                    'journal_id': self.journal_id.id,
                    'date': fields.Date.context_today(self),
                    'ref': self.approval_no + '/' + str(self.reason),
                    'company_id': self.company_id.id,
                    'line_ids': [(0, 0, debit_val), (0, 0, credit_val)]
                }
            # add lines
            self.move_id = self.env['account.move'].create(vals)
            self.move_id.post()
            self.state = 'validate'
            # self.env['mail.activity'].search([('user_id', '=', self.env.uid), ('res_id', '=', self.id)]).action_done()
            self.at_app_id = self.env.user.id
        else:
            raise ValidationError(_("An issue was faced when validating!"))

        # Update footer message
        message_obj = self.env['mail.message']
        message = _("State Changed  Confirm -> <em>%s</em>.") % (self.state)
        msg_id = self.message_post(body=message)
        self.env['mail.activity'].search([('user_id', '=', self.env.uid), ('res_id', '=', self.id)]).action_done()
        # else:
        # acc_approval_amount = self._get_acc_approval_amount()
        # if not  self.finance_approval_line_ids:
        #     raise ValidationError(_("Please select account!"))
        if self.acc_approval_amount - self.request_amount < self.limit and self.journal_id.is_petty_cash:
            raise ValidationError(_("Petty Cash Limit !!!!"))
        self.state = 'validate'
        self.at_app_id = self.env.user.id

    def set_to_draft(self):
        self.state = 'draft'
        # self.mn_app_id = None
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


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    finance_id = fields.Many2one('finance.approval', string='Activity')


class FinanceApprovalLine(models.Model):
    _name = 'finance.approval.line'
    _description = 'Finance Approval details.'

    finance_id = fields.Many2one('finance.approval', string='Finance Approval', ondelete="cascade")
    name = fields.Char('Narration', required=True)
    amount = fields.Float('Amount', required=True)
    notes = fields.Char('Notes')
    exp_account = fields.Many2one('account.account', string="Expense or Debit Account")
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    partner_id = fields.Many2one('res.partner', string='Partner')
    payment_method_name = fields.Many2one('account.payment.method')
    pa_name = fields.Char(related="payment_method_name.name")
