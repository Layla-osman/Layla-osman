# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError, ValidationError


class HrCustody(models.Model):
    """
        Hr custody contract creation model.
        """
    _name = 'hr.custody'
    _description = 'Hr Custody Management'

    def sent(self):
        self.state = 'to_approve'

    def set_to_draft(self):
        self.state = 'draft'

    def approve(self):
        self.state = 'approved'

    @api.depends('employee_id')
    def _compute_name(self):
        employee_name = self.employee_id.name
        if employee_name:
            self.name = "Vacation Sale For" + employee_name

    name = fields.Char(string="Name", compute='_compute_name', readonly=True, store=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True, help="Company",
                                 default=lambda self: self.env.user.company_id)
    date_request = fields.Date(string='Requested Date', required=True, track_visibility='always', readonly=True,
                               help="Requested date",
                               states={'draft': [('readonly', False)]}, default=datetime.now().strftime('%Y-%m-%d'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, readonly=True, help="Employee",
                               default=lambda self: self.env.user.employee_id.id,
                               states={'draft': [('readonly', False)]})
    purpose = fields.Char(string='Reason', track_visibility='always', required=True, readonly=True, help="Reason",
                          states={'draft': [('readonly', False)]})
    custody_name = fields.Many2one('custody.property', string='Property', required=True,
                                   help="Property name",
                                   states={'draft': [('readonly', False)]} )
    notes = fields.Html(string='Notes')
    state = fields.Selection([('draft', 'Draft'), ('to_approve', 'Waiting For Approval'), ('approved', 'Approved'),
                              ], string='Status', default='draft',
                             track_visibility='always')


class HrPropertyName(models.Model):
    """
            Hr property creation model.
            """
    _name = 'custody.property'
    _description = 'Property Name'

    name = fields.Char(string='Property Name', required=True)
