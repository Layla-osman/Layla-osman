
from odoo import models, fields, api, _
from odoo.exceptions import except_orm, Warning
from odoo.exceptions import UserError


class AccountJourna(models.Model):
    _inherit = "account.journal"

    is_petty_cash = fields.Boolean(string='Is Petty Cash')
    limit = fields.Float('Limit')
    min_amount = fields.Float('Min Amount')

    @api.model
    def notify_journal_min_amount(self, domain=None):
        journal_ids = self.search([('is_petty_cash', '!=', False)])
        print('journal_ids',journal_ids)
        for journal in journal_ids:
            print('journal',journal)
            try:
                journal.ensure_one()
                acc_amount = 0.0
                self.env['account.move.line'].check_access_rights('read')

                if not journal.default_account_id:
                    return 0.0, 0
                print('journal.default_account_id',journal.default_account_id)
                domain = (domain or []) + [
                    ('account_id', '=', journal.default_account_id.ids),
                    ('display_type', 'not in', ('line_section', 'line_note')),
                    ('move_id.state', '!=', 'cancel'),
                ]
                query = self.env['account.move.line']._where_calc(domain)
                tables, where_clause, where_params = query.get_sql()

                query = '''
                       SELECT
                           COUNT(account_move_line.id) AS nb_lines,
                           COALESCE(SUM(account_move_line.balance), 0.0),
                           COALESCE(SUM(account_move_line.amount_currency), 0.0)
                       FROM ''' + tables + '''
                       WHERE ''' + where_clause + '''
                   '''
                print('domain',domain)
                company_currency = self.company_id.currency_id
                journal_currency = journal.currency_id if journal.currency_id and journal.currency_id != company_currency else False

                self._cr.execute(query, where_params)
                nb_lines, balance, amount_currency = journal._cr.fetchone()
                print('balance',balance)
                acc_amount = amount_currency if journal_currency else balance
                if acc_amount <= journal.min_amount:
                    print('acc_amount',journal,acc_amount)
                    group = self.env.ref('re_valuation_accounting_customize.petty_cash_access_group').id
                    petty_group_ids = self.env['res.groups'].sudo().search([('id', '=', group)], limit=1)
                    activity_type_id = self.env['mail.activity.type'].sudo().search(
                        [('name', 'like', 'Petty Cash')],
                        limit=1).id
                    model_id = self.env['ir.model'].sudo().search([('model', 'like', 'account.journal')], limit=1).id
                    for user in petty_group_ids.users:
                        value = {
                            'activity_type_id': activity_type_id,
                            'res_id': journal.id,
                            'res_model_id': model_id,
                            'user_id': user.id,
                            'summary': journal.name + 'Limit !!!',
                        }
                        self.env['mail.activity'].sudo().create(value)
            except UserError:
                continue

