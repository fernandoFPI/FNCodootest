from odoo import api, fields, models, _
from odoo.exceptions import UserError


POSITION_SELECTION = [
    ('4', 'Department Head'),
    ('5', 'Store Keeper'),
    ('6', 'Procurement Officer'),
    ('7', 'Store Pricing / 2nd Procurement'),
]


class PoLifecyclePosition(models.Model):
    _name = 'po.lifecycle.position'
    _description = 'Project PO Position Assignment'
    _rec_name = 'user_id'

    project_id = fields.Many2one(
        'project.lifecycle', string='Project',
        required=True, ondelete='cascade', index=True,
    )
    position_code = fields.Selection(
        POSITION_SELECTION, string='Position', required=True,
    )
    user_id = fields.Many2one(
        'res.users', string='User', required=True,
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Employee',
        compute='_compute_employee_id', store=True,
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_project_position_user',
         'UNIQUE(project_id, position_code, user_id)',
         'A user can only hold the same position once per project.'),
    ]

    @api.depends('user_id')
    def _compute_employee_id(self):
        for rec in self:
            emp = self.env['hr.employee'].search(
                [('user_id', '=', rec.user_id.id)], limit=1
            )
            rec.employee_id = emp

    @api.model
    def get_position_users(self, project_id, position_code):
        """Return res.users recordset for a position on a project."""
        positions = self.search([
            ('project_id', '=', project_id),
            ('position_code', '=', position_code),
            ('active', '=', True),
        ])
        return positions.mapped('user_id')
