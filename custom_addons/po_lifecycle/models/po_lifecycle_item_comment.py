from odoo import fields, models


class PoLifecycleItemComment(models.Model):
    _name = 'po.lifecycle.item.comment'
    _description = 'PO Item Comment'
    _order = 'comment_date desc'

    item_id = fields.Many2one(
        'po.lifecycle.item', string='Item',
        required=True, ondelete='cascade',
    )
    comment = fields.Text(string='Comment', required=True)
    comment_by = fields.Many2one(
        'res.users', string='By',
        default=lambda self: self.env.user,
    )
    comment_date = fields.Datetime(
        string='Date', default=fields.Datetime.now,
    )
