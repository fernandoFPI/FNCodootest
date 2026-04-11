from odoo import api, fields, models


class ProjectLifecyclePoExt(models.Model):
    _inherit = 'project.lifecycle'

    # ── PO Relations ──────────────────────────────────────────────────────────
    po_position_ids = fields.One2many(
        'po.lifecycle.position', 'project_id', string='PO Roles',
    )
    po_lifecycle_ids = fields.One2many(
        'po.lifecycle', 'project_id', string='PO Lifecycles',
    )
    po_admin_ids = fields.Many2many(
        'res.users', string='PO Admins',
        compute='_compute_po_admin_ids',
    )

    # ── PO Summary ────────────────────────────────────────────────────────────
    po_count = fields.Integer(compute='_compute_po_stats', string='POs')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )
    po_total_committed = fields.Monetary(
        compute='_compute_po_stats', currency_field='currency_id',
        string='Total Committed',
    )

    @api.depends('po_lifecycle_ids')
    def _compute_po_admin_ids(self):
        for project in self:
            assignments = self.env['po.admin.assignment'].search([
                ('project_ids', 'in', project.id),
                ('active', '=', True),
            ])
            project.po_admin_ids = assignments.mapped('user_id')

    @api.depends('po_lifecycle_ids', 'po_lifecycle_ids.state',
                 'po_lifecycle_ids.purchase_order_id')
    def _compute_po_stats(self):
        for project in self:
            active_pos = project.po_lifecycle_ids.filtered(
                lambda p: p.state != '7'
            )
            project.po_count = len(active_pos)
            committed = 0.0
            for po in active_pos:
                if po.purchase_order_id:
                    committed += po.purchase_order_id.amount_total
            project.po_total_committed = committed

    def action_view_all_pos(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'PO Lifecycles',
            'res_model': 'po.lifecycle',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_open_po_cost_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'PO Cost Report',
            'res_model': 'po.cost.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_project_id': self.id},
        }
