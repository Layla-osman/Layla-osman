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


class HrHolidayCustom(models.Model):
    _name = "hr.holiday.custom"
    _inherit = ['mail.thread']

    @api.depends('employee_id')
    def _compute_name(self):
        employee_name = self.employee_id.name
        if employee_name:
            self.name = "Vacation Sale For" + employee_name

    name = fields.Char(string="Name",compute='_compute_name', readonly=True, store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', )
    date = fields.Date(string='Date', default=fields.Date.context_today,
                                 tracking=5)
    reason = fields.Text(string='Reason')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('mg_confirm', 'Manager Confirm'),
        ('em_confirm', 'Employee Confirm'),
        ('refuse', 'Employee Refuse'),
        ('approve', 'Approved'),
    ], string="State", default='draft', tracking=5, copy=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    def action_mg_approve(self):
        """
        A method to confirm penalty
        """
        self.write({'state': 'em_confirm'})

    def action_em_approve(self):
        """
        A method to approve penalty
        """
        self.write({'state': 'approve'})

    def action_refuse(self):
        """
        A method to approve penalty
        """
        self.write({'state': 'refuse'})

    def unlink(self):
        """
        A method to delete penalty in draft status
        """
        for order in self:
            if order.state not in ('draft',):
                raise UserError(_('You can not delete record not in draft state.'))
        return super(HrHolidayCustom, self).unlink()
