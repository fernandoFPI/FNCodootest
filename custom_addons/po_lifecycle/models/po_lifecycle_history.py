from odoo import fields, models


class PoLifecycleHistory(models.Model):
    _name = 'po.lifecycle.history'
    _description = 'PO Lifecycle History'
    _order = 'date desc'

    po_id = fields.Many2one(
        'po.lifecycle', string='PO', required=True, ondelete='cascade',
    )
    date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    user_id = fields.Many2one(
        'res.users', string='User',
        default=lambda self: self.env.user, readonly=True,
    )
    description = fields.Char(readonly=True)
    state_from = fields.Char(string='From State', readonly=True)
    state_to = fields.Char(string='To State', readonly=True)
