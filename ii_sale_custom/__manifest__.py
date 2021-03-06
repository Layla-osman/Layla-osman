# -*- coding: utf-8 -*-
###################################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2021-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#    Authors: Avinash Nk, Jesni Banu (<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################
{
    'name': 'Sale Customization',
    'version': '15.0.1.0.0',
    'summary': """Sales Customization""",
    'description': 'Sales Customization',
    'live_test_url': 'https://www.youtube.com/watch?v=keh3ttj9kws&feature=youtu.be',
    'category': 'Generic Modules/Sales',
    'author': 'IATL-intellisoft',
    'company': 'IATL-intellisoft',
    'maintainer': 'IATL-intellisoft',
    'depends': ['sale','stock','account'],
    'data': [
        # 'security/ir.model.access.csv',
        #'security/custody_security.xml',
        # 'views/wizard_return_view.xml',
        'data/partner_merge_cron.xml',
        # 'views/hr_employee_view.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
