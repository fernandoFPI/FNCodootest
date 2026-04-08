from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, timedelta


class ProjectLifecycle(models.Model):
    _name = 'project.lifecycle'
    _description = 'Project Lifecycle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    # ── Core fields ──────────────────────────────────────────────────────────
    name = fields.Char(string='Project Name', required=True, tracking=True)
    ref_number = fields.Char(
        string='Reference', readonly=True, copy=False, index=True
    )
    state = fields.Selection(
        selection=[
            ('0', 'Pending'),
            ('1', 'Ongoing'),
            ('5', 'Canceled'),
            ('6', 'On Hold'),
            ('2', 'Submitted'),
            ('3', 'Approved'),
            ('7', 'Invoicing'),
            ('4', 'Complete'),
            ('8', 'Canceled After Approval'),
        ],
        string='Status',
        required=True,
        default='0',
        tracking=True,
    )
    creator_id = fields.Many2one(
        'res.users', string='Created By', default=lambda self: self.env.user
    )

    # ── Team fields ───────────────────────────────────────────────────────────
    technical_member_ids = fields.Many2many(
        'res.users',
        'project_lifecycle_technical_rel',
        'lifecycle_id', 'user_id',
        string='Technical Members',
    )
    commercial_member_ids = fields.Many2many(
        'res.users',
        'project_lifecycle_commercial_rel',
        'lifecycle_id', 'user_id',
        string='Commercial Members',
    )
    members_submitted = fields.Boolean(default=False)

    # ── Date fields ───────────────────────────────────────────────────────────
    submit_date = fields.Date(string='Submission Date', tracking=True)
    approval_date = fields.Date(string='Approval Date', tracking=True)
    invoicing_date = fields.Date(string='Invoicing Date', tracking=True)
    complete_date = fields.Date(string='Completion Date', tracking=True)
    cancel_date = fields.Date(string='Cancellation Date', tracking=True)
    cancel_reason = fields.Text(string='Cancellation Reason')

    # ── Relational fields ─────────────────────────────────────────────────────
    history_ids = fields.One2many(
        'project.lifecycle.history', 'project_id', string='History'
    )
    invoice_ids = fields.One2many(
        'project.lifecycle.invoice', 'project_id', string='Invoices'
    )

    # ── SQL constraints ───────────────────────────────────────────────────────
    _sql_constraints = [
        ('ref_number_uniq', 'UNIQUE(ref_number)',
         'The reference number must be unique.'),
    ]

    # ── ORM overrides ─────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record.ref_number = f'BA-{record.id}-{date.today().year}'
            # Send "project created" email to creator
            template = self.env.ref(
                'project_lifecycle.email_template_project_created',
                raise_if_not_found=False,
            )
            if template and record.creator_id:
                template.send_mail(record.id, force_send=True)
        return records

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _log_history(self, description):
        self.env['project.lifecycle.history'].create({
            'project_id': self.id,
            'user_id': self.env.uid,
            'description': description,
        })

    def _is_admin(self):
        return self.env.user.has_group('project_lifecycle.group_admin')

    def _is_finance(self):
        return self.env.user.has_group('project_lifecycle.group_finance')

    def _is_approver(self):
        return self.env.user.has_group('project_lifecycle.group_approver')

    def _notify_members(self):
        """Send team-assigned email to all technical and commercial members."""
        template = self.env.ref(
            'project_lifecycle.email_template_team_assigned',
            raise_if_not_found=False,
        )
        if template:
            template.send_mail(self.id, force_send=True)

    # ── Transition: Pending → On Hold ─────────────────────────────────────────
    def action_on_hold(self):
        for rec in self:
            if not rec._is_admin():
                raise UserError(_('Only administrators can put a project on hold.'))
            rec.state = '6'
            rec._log_history('Project put on hold')

    # ── Transition: On Hold → Ongoing ─────────────────────────────────────────
    def action_reactivate(self):
        for rec in self:
            if not rec._is_admin():
                raise UserError(_('Only administrators can reactivate a project.'))
            rec.state = '1'
            rec.members_submitted = False
            rec._log_history('Reactivate this project')

    # ── Transition: Submitted → Revise ────────────────────────────────────────
    def action_revise_from_submitted(self):
        for rec in self:
            if not rec._is_admin():
                raise UserError(_('Only administrators can revise a project.'))
            rec.members_submitted = False
            rec._log_history('Revise the project')
            # state stays at '2'

    # ── Transition: Approved → Revise back to Submitted ───────────────────────
    def action_revise_from_approved(self):
        for rec in self:
            if not rec._is_admin():
                raise UserError(_('Only administrators can revise a project.'))
            rec.state = '2'
            rec.members_submitted = False
            rec._log_history('Revise the project')

    # ── Wizard launchers ──────────────────────────────────────────────────────
    def action_open_assign_team_wizard(self):
        self.ensure_one()
        if not self._is_admin():
            raise UserError(_('Only administrators can assign team members.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assign Team'),
            'res_model': 'assign.team.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_project_id': self.id},
        }

    def action_open_submit_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Submit Project'),
            'res_model': 'transition.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.id,
                'default_wizard_type': 'submit',
            },
        }

    def action_open_approve_wizard(self):
        self.ensure_one()
        if not (self._is_admin() or self._is_approver()):
            raise UserError(_('You do not have permission to approve this project.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approve Project'),
            'res_model': 'transition.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.id,
                'default_wizard_type': 'approve',
            },
        }

    def action_open_invoicing_wizard(self):
        self.ensure_one()
        if not (self._is_admin() or self._is_finance()):
            raise UserError(_('Only administrators or finance members can move to invoicing.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Move to Invoicing'),
            'res_model': 'transition.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.id,
                'default_wizard_type': 'invoicing',
            },
        }

    def action_open_complete_wizard(self):
        self.ensure_one()
        if not (self._is_admin() or self._is_finance()):
            raise UserError(_('Only administrators or finance members can mark a project complete.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Mark Complete'),
            'res_model': 'transition.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.id,
                'default_wizard_type': 'complete',
            },
        }

    def action_open_cancel_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cancel Project'),
            'res_model': 'transition.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.id,
                'default_wizard_type': 'cancel',
            },
        }

    # ── Cron job ──────────────────────────────────────────────────────────────
    @api.model
    def cron_email_reminders(self):
        today = date.today()
        invoicing_projects = self.search([('state', '=', '7')])

        tmpl_no_invoice = self.env.ref(
            'project_lifecycle.email_template_no_invoice', raise_if_not_found=False
        )
        tmpl_14 = self.env.ref(
            'project_lifecycle.email_template_invoice_due_14', raise_if_not_found=False
        )
        tmpl_7 = self.env.ref(
            'project_lifecycle.email_template_invoice_due_7', raise_if_not_found=False
        )

        for project in invoicing_projects:
            invoices = project.invoice_ids

            # Rule 1: No invoice linked at all
            if not invoices and tmpl_no_invoice:
                tmpl_no_invoice.send_mail(project.id, force_send=True)
                continue

            # Rules 2 & 3: Check due dates
            for inv in invoices.filtered(lambda i: i.due_date and i.state != 'paid'):
                days_until_due = (inv.due_date - today).days
                if days_until_due == 14 and tmpl_14:
                    tmpl_14.send_mail(project.id, force_send=True)
                elif days_until_due == 7 and tmpl_7:
                    tmpl_7.send_mail(project.id, force_send=True)

    def action_open_cancel_after_approval_wizard(self):
        self.ensure_one()
        # Strict server-side check — even if called via RPC
        if not self._is_admin():
            raise UserError(
                _('Only administrators can cancel a project after approval.')
            )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cancel After Approval'),
            'res_model': 'transition.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.id,
                'default_wizard_type': 'cancel_after_approval',
            },
        }
