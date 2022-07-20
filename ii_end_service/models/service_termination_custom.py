# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

from odoo import models, fields, api, _
from datetime import datetime, time, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError


class ServiceTerminationCustom(models.Model):
    _name = 'service.termination.custom'

    @api.depends('employee_id')
    def _compute_name(self):
        employee_id = self.employee_id
        if employee_id:
            self.name = "End Of Service For Employee " + employee_id.name

    name = fields.Char(string="Name",compute='_compute_name', readonly=True, store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True,
                                    related='employee_id.department_id', store=True)
    date_join = fields.Date('Date of Join', related='employee_id.contract_id.date_start')
    state = fields.Selection(
        [('draft', 'Draft'), ('approve', 'Approve'),
         ('done', 'Done')
         ]
                             , string="State", default='draft', track_visibility='onchange', copy=False,)
    termination_date = fields.Date('Termination Date', default=fields.date.today(), required=True)
    experience_years = fields.Char(compute='get_years_of_service', string='Experience years')
    wage = fields.Monetary(related='employee_id.contract_id.wage', tracking=True, string='Salary')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id,
                                  string='Currency')
    total_receivables = fields.Float(compute='compute_total', string='Total amount', store=True)
    leave_balance = fields.Float(related='employee_id.remaining_leaves', string='Leave balance', tracking=True)
    leave_amount = fields.Float(compute='compute_leave_amount', string='Leave amount')
    other_deduction = fields.Float('Other Deduction')
    other_allowances = fields.Float('Other Allowances')
    payslip_ids = fields.One2many('hr.payslip', 'termination_id')

    @api.depends('termination_date', 'date_join')
    def get_years_of_service(self):
        # calculate number of working years from his/her signing contract
        experience = ''
        for rec in self:
            if rec.date_join:
                str_now = datetime.strptime(str(rec.termination_date), '%Y-%m-%d').date()
                date_start = datetime.strptime(str(rec.date_join), '%Y-%m-%d').date()
                total_days = (str_now - date_start).days
                employee_years = int(total_days / 365)
                total_days = total_days - 365 * employee_years
                employee_months = int(12 * total_days / 365)
                employee_days = int(0.5 + total_days - 365 * employee_months / 12)
                experience = str(employee_years) + 'Year(s)' + str(employee_months) + 'Month(s)' + str(
                    employee_days) + 'day(s)'
            rec.experience_years = experience

    @api.depends('wage', 'leave_balance')
    def compute_leave_amount(self):
        # ?????????????
        for lev in self:
            # print("++++++++++++++++++++")
            lev.leave_amount = 0.0
            if lev.leave_balance > 0:
                result = lev.wage / 30 * lev.leave_balance
                lev.leave_amount = result

    # total = salary + leave_amount + other_allowances - other_deduction
    @api.depends('termination_date', 'date_join', 'other_allowances', 'leave_amount')
    def compute_total(self):
        for too in self:
            str_now = datetime.strptime(str(too.termination_date), '%Y-%m-%d').date()
            if too.date_join:
                date_start = datetime.strptime(str(too.date_join), '%Y-%m-%d').date()
                total_days = (str_now - date_start).days
                employee_years = int(total_days / 365)
                salary = (too.wage / 26) * 36
                if employee_years < 3:
                    salary = 0
                elif employee_years > 3 and employee_years < 5 :
                    salary = salary/2
                elif employee_years > 5 and employee_years < 10 :
                    salary = (salary *2)/3
                elif employee_years >= 10 :
                    salary = salary
                total = salary + too.leave_amount + too.other_allowances - too.other_deduction
                too.total_receivables = total

    def action_approve(self):
        """
        A method to approve service termination
        """
        for rec in self:
            payslip_vals = {
                'name': _('Service Termination Slip of %s ') % (rec.employee_id.name),
                'employee_id': rec.employee_id.id,
                'contract_id': rec.employee_id.contract_id.id,
                'struct_id': rec.employee_id.contract_id.structure_type_id.id,
                'type': 'service_termination',
                'termination_id': self.id}
            payslip = self.env['hr.payslip'].create(payslip_vals)
            payslip.sudo().compute_sheet()
            for slip in rec.payslip_ids:
                for line in slip.line_ids:
                    lines = {
                        'slip_id': payslip.line_ids.slip_id.id,
                        'salary_rule_id': line.salary_rule_id.id,
                        'name': line.salary_rule_id.name,
                        'code': line.salary_rule_id.code,
                        'category_id': line.salary_rule_id.category_id.id,
                        'employee_id': rec.employee_id.id,
                        'contract_id': rec.employee_id.contract_id.id,
                        'amount': rec.total_receivables,
                        'total': rec.total_receivables}
                    payslip.env['hr.payslip.line'].create(lines)
            rec.write({'state': 'approve'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_done(self):
        """
        A method to set service termination done.
        """
        for rec in self:
            rec.write({'state': 'done'})
            rec.employee_id.contract_id.write(
                {'date_end': rec.termination_date})
            rec.employee_id.contract_id.write(
                {'state': 'close'})
            rec.employee_id.job_id.write({'employee_ids': [(3, rec.employee_id.id)]})

