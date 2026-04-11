from odoo import api, fields, models


class PoLifecycleItem(models.Model):
    _name = 'po.lifecycle.item'
    _description = 'PO Lifecycle Item'
    _order = 'id asc'

    po_id = fields.Many2one(
        'po.lifecycle', string='PO',
        required=True, ondelete='cascade', index=True,
    )
    product_id = fields.Many2one('product.product', string='Product')
    item_desc = fields.Char(string='Description', required=True)
    item_qty = fields.Float(string='Quantity', required=True, default=1.0)
    item_unit = fields.Many2one('uom.uom', string='Unit of Measure')
    item_note = fields.Text(string='Note')

    # ── Inventory fields ──────────────────────────────────────────────────────
    item_stock_available = fields.Float(string='Stock Available')
    item_stock_need = fields.Float(
        string='Stock Needed', compute='_compute_stock_need', store=True,
    )
    item_stock_note = fields.Text(string='Stock Note')

    # ── Currency helpers (one per currency, required by Monetary fields) ──────
    currency_usd_id = fields.Many2one(
        'res.currency', string='USD',
        default=lambda self: self.env.ref('base.USD', raise_if_not_found=False),
    )
    currency_iqd_id = fields.Many2one(
        'res.currency', string='IQD',
        default=lambda self: self.env.ref('base.IQD', raise_if_not_found=False),
    )
    currency_eur_id = fields.Many2one(
        'res.currency', string='EUR',
        default=lambda self: self.env.ref('base.EUR', raise_if_not_found=False),
    )
    currency_gbp_id = fields.Many2one(
        'res.currency', string='GBP',
        default=lambda self: self.env.ref('base.GBP', raise_if_not_found=False),
    )

    # ── Store prices ──────────────────────────────────────────────────────────
    item_store_price_usd = fields.Monetary(
        string='Store Price (USD)', currency_field='currency_usd_id',
    )
    item_store_price_iqd = fields.Monetary(
        string='Store Price (IQD)', currency_field='currency_iqd_id',
    )
    item_store_price_eur = fields.Monetary(
        string='Store Price (EUR)', currency_field='currency_eur_id',
    )
    item_store_price_gbp = fields.Monetary(
        string='Store Price (GBP)', currency_field='currency_gbp_id',
    )

    # ── Market prices ─────────────────────────────────────────────────────────
    item_price_usd = fields.Monetary(
        string='Market Price (USD)', currency_field='currency_usd_id',
    )
    item_price_iqd = fields.Monetary(
        string='Market Price (IQD)', currency_field='currency_iqd_id',
    )
    item_price_eur = fields.Monetary(
        string='Market Price (EUR)', currency_field='currency_eur_id',
    )
    item_price_gbp = fields.Monetary(
        string='Market Price (GBP)', currency_field='currency_gbp_id',
    )
    item_price_note = fields.Text(string='Price Note')

    selected_currency_id = fields.Many2one(
        'res.currency', string='Selected Currency',
    )

    comment_ids = fields.One2many(
        'po.lifecycle.item.comment', 'item_id', string='Comments',
    )
    submit_date = fields.Datetime(string='Submitted')
    submit_by = fields.Many2one('res.users', string='Submitted By')

    @api.depends('item_qty', 'item_stock_available')
    def _compute_stock_need(self):
        for rec in self:
            rec.item_stock_need = max(
                0.0, (rec.item_qty or 0.0) - (rec.item_stock_available or 0.0)
            )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.item_desc = self.product_id.name
            self.item_unit = self.product_id.uom_po_id or self.product_id.uom_id
