from odoo import api, fields, models, _


class PoCostReportWizard(models.TransientModel):
    _name = 'po.cost.report.wizard'
    _description = 'PO Cost Report Wizard'

    project_id = fields.Many2one('project.project', string='Project')
    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')
    currency_display = fields.Selection(
        [('USD', 'USD'), ('IQD', 'IQD'), ('EUR', 'EUR'), ('GBP', 'GBP')],
        string='Display Currency', default='USD',
    )
    state_filter = fields.Many2many(
        'ir.model.fields.selection',
        string='Filter by Status',
    )

    def _get_domain(self):
        domain = [('state', '!=', '7')]
        if self.project_id:
            domain.append(('project_id', '=', self.project_id.id))
        if self.date_from:
            domain.append(('open_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('open_date', '<=', self.date_to))
        return domain

    def action_generate(self):
        self.ensure_one()
        domain = self._get_domain()
        pos = self.env['po.lifecycle'].search(domain)

        return {
            'type': 'ir.actions.act_window',
            'name': _('PO Cost Report'),
            'res_model': 'po.lifecycle',
            'view_mode': 'list,form',
            'domain': [('id', 'in', pos.ids)],
            'context': {
                'search_default_group_project': 1,
            },
        }

    def action_print_report(self):
        self.ensure_one()
        domain = self._get_domain()
        pos = self.env['po.lifecycle'].search(domain)
        return self.env.ref(
            'po_lifecycle.action_report_po_cost'
        ).report_action(pos)
