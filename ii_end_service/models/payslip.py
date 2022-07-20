# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

from odoo import models, fields, api, _, tools
from odoo.exceptions import Warning, RedirectWarning
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import babel.dates

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    type = fields.Selection([('service_termination', 'Service Termination'), ('salary', 'Salary')], default='salary')
    termination_id = fields.Many2one('service.termination.custom', string='Termination')

    def onchange_employee_id(self, date_from, date_to, employee_id=False, contract_id=False):
        # inherit to change payslip name in case of type 'Service Termination'
        res = super(HrPayslip, self).onchange_employee_id(date_from, date_to, employee_id, contract_id)
        if self.type == 'service_termination':
            name = _('Service Termination Slip of %s for %s') % (employee.name)
            res['value'].update({
                'name': name,
            })
        return res

    def action_payslip_done(self):
        #inherit to change payslip to done and service termination to done
        res = super(HrPayslip, self.sudo()).action_payslip_done()
        for rec in self:
            if rec.termination_id:
                rec.termination_id.action_done()
        return res
