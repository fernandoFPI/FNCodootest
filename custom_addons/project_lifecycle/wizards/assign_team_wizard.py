from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AssignTeamWizard(models.TransientModel):
    _name = 'assign.team.wizard'
    _description = 'Assign Team Wizard'

    project_id = fields.Many2one(
        'project.lifecycle', string='Project', required=True
    )
    technical_member_ids = fields.Many2many(
        'res.users',
        'assign_wizard_technical_rel',
        'wizard_id', 'user_id',
        string='Technical Members',
    )
    commercial_member_ids = fields.Many2many(
        'res.users',
        'assign_wizard_commercial_rel',
        'wizard_id', 'user_id',
        string='Commercial Members',
    )

    @api.constrains('technical_member_ids')
    def _check_technical_limit(self):
        for rec in self:
            if len(rec.technical_member_ids) > 5:
                raise UserError(_('You can assign a maximum of 5 Technical Members.'))

    @api.constrains('commercial_member_ids')
    def _check_commercial_limit(self):
        for rec in self:
            if len(rec.commercial_member_ids) > 4:
                raise UserError(_('You can assign a maximum of 4 Commercial Members.'))

    def action_confirm(self):
        self.ensure_one()
        project = self.project_id
        project.write({
            'technical_member_ids': [(6, 0, self.technical_member_ids.ids)],
            'commercial_member_ids': [(6, 0, self.commercial_member_ids.ids)],
            'state': '1',
        })
        project._log_history('Assign new Tasks')
        project._notify_members()
        return {'type': 'ir.actions.act_window_close'}
