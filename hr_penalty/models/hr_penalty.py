# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

from odoo import api, fields, models, tools, _
from odoo.exceptions import Warning
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, time, timedelta
from odoo.tools.translate import html_translate


class HrPenalty(models.Model):
    _name = "hr.penalty"
    _inherit = ['mail.thread']

    @api.depends('employee_id')
    def _compute_name(self):
        employee_id = self.employee_id
        if employee_id:
            self.name = "Penalty For Employee " + employee_id.name

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        employee_id = self.employee_id.id
        if employee_id:
            penalty_id = self.env['hr.penalty'].search([('employee_id', '=', employee_id)],limit= 1)
            self.last_penalty_id = penalty_id.id

    name = fields.Char(string="Name", compute='_compute_name', readonly=True, store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', )
    violation_id = fields.Many2one('hr.violation', string="violation", tracking=5)
    violation_date = fields.Date(string='Violation Date', default=fields.Date.context_today,
                                 tracking=5)
    amount = fields.Float(string='Amount')
    last_penalty_id = fields.Many2one('hr.penalty', string='last_penalty', ondelete='set null', )
    punishment_type = fields.Selection(selection=[
        ('warning', 'Warning'),
        ('penalty', 'Penalty'),
        ('suspend', 'Suspend'),
        ('terminate', 'Terminate')],  string='Punishment Type',
        default='warning')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approved'),
    ], string="State", default='draft', tracking=5, copy=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    #service_termination_id = fields.Many2one('hr.service.termination', string='Servise Termination Ref')
    confirming_employee_id = fields.Many2one('hr.employee', string='Confirming Employee')
    approving_employee_id = fields.Many2one('hr.employee', string='Approving Employee')
#    mail_track = fields.Many2one('mail.message', string="Mail tracking")

    def action_confirm(self):
        """
        A method to confirm penalty
        """
        self.write({'state': 'confirm'})
        user_id = self.env.user.id
        # 1) Get the employee object
        employee_obj = self.env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
        # Another way of getting the employee
        # resource = self.env['resource.resource'].search([('user_id','=',self.env.user.id)])
        # employee_obj = self.env['hr.employee'].search([('resource_id','=',resource.id)])
        # 2) Get the employee id
        employee_id = employee_obj.id
        # 3) Assign the employee to the related user
        self.confirming_employee_id = employee_id


    def action_approve(self):
        """
        A method to approve penalty
        """
        self.write({'state': 'approve'})


    def unlink(self):
        """
        A method to delete penalty in draft status
        """
        for order in self:
            if order.state not in ('draft',):
                raise UserError(_('You can not delete record not in draft state.'))
        return super(HrPenalty, self).unlink()

    def action_mail_send(self):
        # self.write({'state': 'sent'})

        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('hr_penalty', 'penalty_teamplate_id')[1]
        except ValueError:
            template_id = False

        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'hr.penalty',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'force_email': True
        })

        return {
            'name': _('Penalty Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'target': 'new',
            'context': ctx,
        }


class Employee(models.Model):
    _inherit = 'hr.employee'

    penalty_ids = fields.One2many('hr.penalty', 'employee_id', string='last_penalty',
                                  domain=[('state', '=', 'approve')])
    penalty_count = fields.Integer(compute='_compute_penalty_count', string='Penalty Count')

    def _compute_penalty_count(self):
        """
        A method to count all employees penalty without repetition.
        """
        penalty_data = self.env['hr.penalty'].sudo().read_group([('employee_id', '=', self.id)], ['employee_id'],
                                                                ['employee_id'])
        result = dict((data['employee_id'][0], data['employee_id_count']) for data in penalty_data)
        for employee in self:
            employee.penalty_count = result.get(employee.id, 0)

class HrViolation(models.Model):
    _name = 'hr.violation'

    name = fields.Char('Name')
