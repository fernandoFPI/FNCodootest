from odoo import fields, models


class ProjectLifecycleHistory(models.Model):
    _name = 'project.lifecycle.history'
    _description = 'Project Lifecycle History'
    _order = 'date desc'

    project_id = fields.Many2one(
        'project.lifecycle',
        string='Project',
        required=True,
        ondelete='cascade',
    )
    date = fields.Datetime(
        string='Date',
        default=fields.Datetime.now,
        readonly=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user,
        readonly=True,
    )
    description = fields.Char(string='Description', readonly=True)
