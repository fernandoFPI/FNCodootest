from odoo import fields, models, _
from odoo.exceptions import UserError


class ProjectLifecycleInvoice(models.Model):
    _name = 'project.lifecycle.invoice'
    _description = 'Project Lifecycle Invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    project_id = fields.Many2one(
        'project.lifecycle',
        string='Project',
        required=True,
        ondelete='cascade',
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('in_payment', 'In Payment'),
            ('paid', 'Paid'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )
    submit_date = fields.Date(string='Submitted Date')
    submit_by = fields.Many2one('res.users', string='Submitted By')
    approved_date = fields.Date(string='Approved Date')
    approved_by = fields.Many2one('res.users', string='Approved By')
    due_date = fields.Date(string='Due Date')
    name = fields.Char(string='Invoice Reference', required=True, default='New Invoice')

    def action_mark_in_payment(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Invoice must be in Draft state to mark as In Payment.'))
            rec.submit_date = fields.Date.today()
            rec.submit_by = self.env.user
            rec.state = 'in_payment'

    def action_mark_paid(self):
        for rec in self:
            if rec.state != 'in_payment':
                raise UserError(_('Invoice must be In Payment to mark as Paid.'))
            rec.approved_date = fields.Date.today()
            rec.approved_by = self.env.user
            rec.state = 'paid'
