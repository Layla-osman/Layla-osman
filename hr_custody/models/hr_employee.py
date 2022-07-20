# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, datetime, timedelta


class HrCustody(models.Model):
    _inherit = 'hr.employee'

    custody_count = fields.Integer(compute='_custody_count', string='# Custody')
    equipment_count = fields.Integer(compute='_equipment_count', string='# Equipments')
    employee_classification = fields.Selection([('citizen', 'Citizen'), ('non_citizen', 'Non Citizen')],
                                               string='Employee Classification')
    visa_start = fields.Date(string='Residence Start Date', default=datetime.now().strftime('%Y-%m-%d'))
    passport_end_date = fields.Date(string='Passport End Date', default=datetime.now().strftime('%Y-%m-%d'))
    passport_schedule_activity = fields.Boolean(default=False, groups="hr.group_hr_user")

    # count of all custody contracts
    
    def _custody_count(self):
        for each in self:
            custody_ids = self.env['hr.custody'].search([('employee', '=', each.id)])
            if custody_ids:
                each.custody_count = len(custody_ids)

    # count of all custody contracts that are in approved state

    def _equipment_count(self):
        for each in self:
            equipment_obj = self.env['hr.custody'].search([('employee', '=', each.id), ('state', '=', 'approved')])
            equipment_ids = []
            for each1 in equipment_obj:
                if each1.custody_name.id not in equipment_ids:
                    equipment_ids.append(each1.custody_name.id)
            each.equipment_count = len(equipment_ids)

    # smart button action for returning the view of all custody contracts related to the current employee
    
    def custody_view(self):
        for each1 in self:
            custody_obj = self.env['hr.custody'].search([('employee', '=', each1.id)])
            custody_ids = []
            for each in custody_obj:
                custody_ids.append(each.id)
            view_id = self.env.ref('hr_custody.hr_custody_form_view').id
            if custody_ids:
                if len(custody_ids) <= 1:
                    value = {
                        'view_mode': 'form',
                        'res_model': 'hr.custody',
                        'view_id': view_id,
                        'type': 'ir.actions.act_window',
                        'name': _('Custody'),
                        'res_id': custody_ids and custody_ids[0]
                    }
                else:
                    value = {
                        'domain': str([('id', 'in', custody_ids)]),
                        'view_mode': 'tree,form',
                        'res_model': 'hr.custody',
                        'view_id': False,
                        'type': 'ir.actions.act_window',
                        'name': _('Custody'),
                        'res_id': custody_ids
                    }

                return value

    @api.model
    def _cron_check_work_permit_validity(self):
        # Called by a cron
        # Schedule an activity 1 month before the work permit expires
        employees_ids = self.env['hr.employee'].search([("employee_classification", "=", 'non_citizen')])
        for rec in employees_ids:
            today_date = date.today()
            end_date = datetime.strptime(str(rec.visa_expire), '%Y-%m-%d').date()
            rem_days = (end_date - today_date).days
            if rem_days <= 14:
                employees_scheduled = self.env['hr.employee']
                s = "The Employee " + rec.name + " Residence Will End At Date " + end_date
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    note=_(s,
                           employee=rec.name,
                           date=end_date),
                    user_id=self.department_id.manager_id.user_id.id)
                employees_scheduled.write({'work_permit_scheduled_activity': True})

    def check_passport_validity(self):
        employees_ids = self.env['hr.employee'].search([("employee_classification", "=", 'non_citizen')])
        for rec in employees_ids:
            today_date = date.today()
            end_date = datetime.strptime(str(rec.passport_end_date), '%Y-%m-%d').date()
            rem_days = (end_date - today_date).days
            rem_month = rem_days/30
            print(rem_month)
            if rem_month <= 2:
                passport_schedule = self.env['hr.employee']
                s = "The Employee " + rec.name + " Passport Will End At Date " + end_date
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    note=_(s,
                           employee=rec.name,
                           date=end_date),
                    user_id=self.department_id.manager_id.user_id.id)
                passport_schedule.write({'passport_schedule_activity': True})
