from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TransitionWizard(models.TransientModel):
    """
    Reusable wizard for all date/reason-based transitions.
    wizard_type controls which transition is executed.
    """
    _name = 'transition.wizard'
    _description = 'Project Lifecycle Transition Wizard'

    project_id = fields.Many2one(
        'project.lifecycle', string='Project', required=True
    )
    wizard_type = fields.Selection(
        selection=[
            ('submit', 'Submit'),
            ('approve', 'Approve'),
            ('invoicing', 'Move to Invoicing'),
            ('complete', 'Mark Complete'),
            ('cancel', 'Cancel'),
            ('cancel_after_approval', 'Cancel After Approval'),
        ],
        string='Wizard Type',
        required=True,
    )

    # Date fields — shown conditionally in the view
    transition_date = fields.Date(string='Date')
    cancel_reason = fields.Text(string='Cancellation Reason')

    @api.constrains('transition_date', 'cancel_reason', 'wizard_type')
    def _check_required_fields(self):
        for rec in self:
            if rec.wizard_type in ('submit', 'approve', 'invoicing', 'complete'):
                if not rec.transition_date:
                    raise UserError(_('Please provide a date before proceeding.'))
            if rec.wizard_type in ('cancel', 'cancel_after_approval'):
                if not rec.cancel_reason:
                    raise UserError(_('Please provide a cancellation reason.'))

    def action_confirm(self):
        self.ensure_one()
        project = self.project_id
        wtype = self.wizard_type

        if wtype == 'submit':
            project.write({
                'state': '2',
                'submit_date': self.transition_date,
                'members_submitted': True,
            })
            project._log_history(
                f'Submit the project (submission date: {self.transition_date})'
            )

        elif wtype == 'approve':
            if not (project._is_admin() or project._is_approver()):
                raise UserError(_('You do not have permission to approve this project.'))
            project.write({
                'state': '3',
                'approval_date': self.transition_date,
            })
            project._log_history(
                f'Change project Status to Approved (approval date: {self.transition_date})'
            )

        elif wtype == 'invoicing':
            if not (project._is_admin() or project._is_finance()):
                raise UserError(_('Only administrators or finance members can move to invoicing.'))
            project.write({
                'state': '7',
                'invoicing_date': self.transition_date,
            })
            project._log_history('Moved to invoicing')

        elif wtype == 'complete':
            if not (project._is_admin() or project._is_finance()):
                raise UserError(_('Only administrators or finance members can mark a project complete.'))
            project.write({
                'state': '4',
                'complete_date': self.transition_date,
            })
            project._log_history('Marked as completed')

        elif wtype == 'cancel':
            project.write({
                'state': '5',
                'cancel_date': fields.Date.today(),
                'cancel_reason': self.cancel_reason,
                'members_submitted': True,
            })
            project._log_history('Canceled')

        elif wtype == 'cancel_after_approval':
            # Double-check at Python level — defense against RPC calls
            if not project._is_admin():
                raise UserError(
                    _('Only administrators can cancel a project after approval.')
                )
            project.write({
                'state': '8',
                'cancel_date': self.transition_date or fields.Date.today(),
                'cancel_reason': self.cancel_reason,
            })
            project._log_history('Project canceled after approval')

        return {'type': 'ir.actions.act_window_close'}
