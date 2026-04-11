from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AssignDeptWizard(models.TransientModel):
    _name = 'assign.dept.wizard'
    _description = 'Assign Department Head Wizard'

    po_id = fields.Many2one('po.lifecycle', string='PO', required=True)
    dept_head_id = fields.Many2one(
        'res.users', string='Department Head', required=True,
    )
    dept_head_domain = fields.Many2many(
        'res.users', compute='_compute_dept_head_domain',
    )
    note = fields.Text(string='Note')

    @api.depends('po_id')
    def _compute_dept_head_domain(self):
        for rec in self:
            if rec.po_id:
                users = self.env['po.lifecycle.position'].get_position_users(
                    rec.po_id.project_id.id, '4'
                )
                rec.dept_head_domain = users
            else:
                rec.dept_head_domain = self.env['res.users']

    def action_confirm(self):
        self.ensure_one()
        po = self.po_id
        if po.state != '4':
            raise UserError(_('PO must be in Need Approval state.'))
        po.write({
            'assigned_dept_head_id': self.dept_head_id.id,
            'state': '10',
        })
        po._log_history(
            _('Assigned to Dept Head: %s') % self.dept_head_id.name,
            '4', '10',
        )
        # Notify the dept head
        po.message_post(
            body=_('You have been assigned as Department Head approver for this PO.'),
            partner_ids=[self.dept_head_id.partner_id.id],
        )
        return {'type': 'ir.actions.act_window_close'}
