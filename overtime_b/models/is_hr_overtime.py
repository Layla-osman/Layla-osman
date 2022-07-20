from datetime import datetime
from dateutil import relativedelta
import time

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_round, float_is_zero


class HrOvertime(models.Model):
    _name = 'hr.overtime'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('overtime_date')
    def _compute_name(self):
        overtime_date = self.overtime_date
        if overtime_date:
            self.name = "OverTime for Day " + str(overtime_date)

    name = fields.Char(string="Name",compute='_compute_name', readonly=True, store=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, readonly=True)
    is_working_day = fields.Boolean(string="Working Day")
    is_holiday = fields.Boolean(string="Holiday Day")
    is_official_vacation = fields.Boolean(string="Official Vacation")
    overtime_date = fields.Date(string="Date", required=True)
    hours = fields.Integer(string="Hours", required=True)
    comment = fields.Text(string="Comments")
    employee_account = fields.Many2one('account.account', string="Debit Account")
    overtime_account = fields.Many2one('account.account', string="Credit Account")
    analytic_debit_account_id = fields.Many2one('account.analytic.account',
                                                # related='department_id.analytic_debit_account_id', readonly=True,
                                                string="Analytic Account")
    journal_id = fields.Many2one('account.journal', string="Journal")
    move_id = fields.Many2one('account.move', string="Journal Entry", readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approved'),
        ('paid', 'Paid'),
    ], string="State", default='draft', track_visibility='onchange', copy=False, )
    overtime_line_ids = fields.One2many('overtime.line', 'overtime_line_id', string='Employees')
    amount = fields.Float(string="Total Amount", compute='_get_amount')

    def _get_amount(self):
        for rec in self:
            total_amount = 0
            for overtime in rec.overtime_line_ids:
                if overtime.amount:
                    total_amount += overtime.amount
            rec.amount = total_amount

    @api.constrains('is_working_day', 'is_holiday', 'is_official_vacation')
    def determine_overtime_day(self):
        for rec in self:
            if not rec.is_working_day:
                if not rec.is_holiday:
                    if not rec.is_official_vacation:
                        raise Warning(
                            _("Please determine work day of overtime is it work day or holiday day or Eid day!"))
            if not rec.is_holiday:
                if not rec.is_working_day:
                    if not rec.is_official_vacation:
                        raise Warning(
                            _("Please determine work day of overtime is it work day or holiday day or Eid day!"))
            if not rec.is_official_vacation:
                if not rec.is_working_day:
                    if not rec.is_holiday:
                        raise Warning(
                            _("Please determine work day of overtime is it work day or holiday day or Eid day!"))

    def hr_validate(self):
        for rec in self:
            rec.state = 'approve'

    def action_paid(self):
        for rec in self:
            rec.state = 'paid'

    def unlink(self):
        if any(self.filtered(lambda hr_overtime: hr_overtime.state not in ('draft', 'refuse'))):
            raise UserError(_('You cannot delete a Overtime which is not draft or refused!'))
        return super(HrOvertime, self).unlink()

    import datetime

    def finance_validate(self):
        precision = self.env['decimal.precision'].precision_get('Payroll')
        for overtime in self:
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            overtime_request_date = overtime.overtime_date
            amount = overtime.amount
            overtime_name = overtime.name
            journal_id = overtime.journal_id.id
            move_dict = {
                'narration': overtime_name,
                'ref': '/',
                'journal_id': journal_id,
                'date': overtime_request_date,
            }
            debit_line = (0, 0, {
                'name': overtime_name,
                'partner_id': False,
                'account_id': overtime.employee_account.id,
                'journal_id': journal_id,
                'date': overtime_request_date,
                'debit': amount > 0.0 and amount or 0.0,
                'credit': amount < 0.0 and -amount or 0.0,
                'analytic_account_id': overtime.analytic_debit_account_id.id,
                'tax_line_id': 0.0,
            })
            line_ids.append(debit_line)
            debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']
            credit_line = (0, 0, {
                'name': overtime_name,
                'partner_id': False,
                'account_id': overtime.overtime_account.id,
                'journal_id': journal_id,
                'date': overtime_request_date,
                'debit': amount < 0.0 and -amount or 0.0,
                'credit': amount > 0.0 and amount or 0.0,
                'analytic_account_id': False,
                'tax_line_id': 0.0,
            })
            line_ids.append(credit_line)
            credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
            if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                acc_journal_credit = overtime.journal_id.default_credit_account_id.id
                if not acc_journal_credit:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                        overtime.journal_id.name))
                adjust_credit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_journal_credit,
                    'journal_id': journal_id,
                    'date': overtime_request_date,
                    'debit': 0.0,
                    'credit': debit_sum - credit_sum,
                })
                line_ids.append(adjust_credit)

            elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                acc_journal_deit = overtime.journal_id.default_debit_account_id.id
                if not acc_journal_deit:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                        overtime.journal_id.name))
                adjust_debit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_journal_deit,
                    'journal_id': journal_id,
                    'date': overtime_request_date,
                    'debit': credit_sum - debit_sum,
                    'credit': 0.0,
                })
                line_ids.append(adjust_debit)
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            overtime.write({'move_id': move.id, 'overtime_date': overtime_request_date})
            move.post()
        self.state = 'paid'

    def overtime_reset(self):
        for rec in self:
            rec.state = 'draft'

    def overtime_refuse(self):
        for rec in self:
            rec.state = 'refuse'

    @api.constrains('hour')
    def _total_hour_limit(self):
        for rec in self:
            if rec.hour <= 0.0:
                raise Warning(_("Overtime hours mut be greater than 0 please check it!"))


class OvertimeLine(models.Model):
    _name = 'overtime.line'

    name = fields.Many2one('hr.employee', string="Employee", required=True)
    overtime_line_id = fields.Many2one('hr.overtime', string="Overtime")
    department_id = fields.Many2one('hr.department', related="name.department_id", readonly=True,
                                    string="Department")
    employee_salary = fields.Float(string="Employee Salary")
    amount = fields.Float(string="Overtime Amount", compute='_get_amount')

    @api.onchange('name')
    def _onchange_employee_d(self):
        if self.name:
            self.employee_salary = self.name.contract_id.wage

    def _get_amount(self):
        for overtime in self:
            employee_salary = overtime.employee_salary
            if employee_salary:
                contract_hours = overtime.name.contract_id.resource_calendar_id.full_time_required_hours
                overtime_amount = 0
                if overtime.overtime_line_id.hours:
                    overtime_hour = overtime.overtime_line_id.hours
                    if contract_hours:
                        hour_rate = employee_salary/contract_hours
                        if overtime.overtime_line_id.is_working_day:
                            overtime_amount = hour_rate + (hour_rate * 0.25)
                        if overtime.overtime_line_id.is_holiday:
                            overtime_amount = hour_rate + (hour_rate * 0.50)
                        if overtime.overtime_line_id.is_official_vacation:
                            overtime_amount = hour_rate * 2
                        overtime.amount = overtime_amount * overtime_hour

