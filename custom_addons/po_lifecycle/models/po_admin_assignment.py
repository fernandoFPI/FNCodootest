from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PoAdminAssignment(models.Model):
    _name = 'po.admin.assignment'
    _description = 'PO Admin Assignment'
    _rec_name = 'user_id'

    user_id = fields.Many2one(
        'res.users', string='User', required=True, index=True
    )
    project_ids = fields.Many2many(
        'project.lifecycle',
        'po_admin_project_rel', 'assignment_id', 'project_id',
        string='Projects this person administers',
    )
    active = fields.Boolean(default=True)
    note = fields.Text(string='Notes')

    def _check_superadmin(self):
        if not self.env.user.has_group('po_lifecycle.group_superadmin'):
            raise UserError(
                _('Only Super Admins can manage PO Admin Assignments.')
            )

    @api.model_create_multi
    def create(self, vals_list):
        self._check_superadmin()
        return super().create(vals_list)

    def write(self, vals):
        self._check_superadmin()
        return super().write(vals)
