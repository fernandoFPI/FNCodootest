from odoo import api, fields, models, _
from odoo.exceptions import UserError

STATE_LABELS = {
    '0': 'Opening', '1': 'Checking Inventory', '9': 'Store Pricing',
    '2': 'Market Pricing', '22': 'Checking Price', '3': 'Review',
    '4': 'Need Approval', '10': 'Need Dept Approval',
    '8': 'Approved', '5': 'Completed', '7': 'Deleted',
}


class PoLifecycle(models.Model):
    _name = 'po.lifecycle'
    _description = 'PO Lifecycle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    # ── Core ──────────────────────────────────────────────────────────────────
    name = fields.Char(string='Title', required=True, tracking=True)
    po_number = fields.Char(string='PO Number', readonly=True, copy=False, index=True)
    project_id = fields.Many2one(
        'project.lifecycle', string='Project', required=True, tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner', string='Vendor', tracking=True,
    )
    priority = fields.Selection(
        [('0', 'Standard'), ('1', 'Emergency')],
        string='Priority', default='0', tracking=True,
    )
    deadline = fields.Date(string='Deadline')
    open_date = fields.Date(string='Opened On', default=fields.Date.today)

    # ── Currencies ────────────────────────────────────────────────────────────
    po_currency_id = fields.Many2one(
        'res.currency', string='PO Currency',
        default=lambda self: self.env.company.currency_id,
    )
    currency_usd_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.ref('base.USD', raise_if_not_found=False),
    )
    currency_iqd_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.ref('base.IQD', raise_if_not_found=False),
    )
    currency_eur_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.ref('base.EUR', raise_if_not_found=False),
    )
    currency_gbp_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.ref('base.GBP', raise_if_not_found=False),
    )

    # ── State ─────────────────────────────────────────────────────────────────
    state = fields.Selection(
        selection=[
            ('0', 'Opening'),
            ('1', 'Checking Inventory'),
            ('9', 'Store Pricing'),
            ('2', 'Market Pricing'),
            ('22', 'Checking Price'),
            ('3', 'Review'),
            ('4', 'Need Approval'),
            ('10', 'Need Dept Approval'),
            ('8', 'Approved'),
            ('5', 'Completed'),
            ('7', 'Deleted'),
        ],
        string='Status', default='0', required=True, tracking=True,
    )

    # ── Transition timestamps ─────────────────────────────────────────────────
    submit_date = fields.Date(readonly=True, tracking=True)
    checking_inventory_date = fields.Date(readonly=True, tracking=True)
    store_pricing_date = fields.Date(readonly=True, tracking=True)
    pricing_date = fields.Date(readonly=True, tracking=True)
    price_check_date = fields.Date(readonly=True, tracking=True)
    review_date = fields.Date(readonly=True, tracking=True)
    approved_date = fields.Date(readonly=True, tracking=True)
    complete_date = fields.Date(readonly=True, tracking=True)
    deleted_date = fields.Date(readonly=True, tracking=True)

    # ── Transition actors ─────────────────────────────────────────────────────
    submit_by = fields.Many2one('res.users', readonly=True)
    store_keeper_by = fields.Many2one('res.users', readonly=True)
    store_price_by = fields.Many2one('res.users', readonly=True)
    procurement_by = fields.Many2one('res.users', readonly=True)
    procurement_l2_by = fields.Many2one('res.users', readonly=True)
    assigned_dept_head_id = fields.Many2one('res.users', string='Assigned Dept Head')
    approved_by = fields.Many2one('res.users', readonly=True)
    completed_by = fields.Many2one('res.users', readonly=True)

    # ── Relations ─────────────────────────────────────────────────────────────
    item_ids = fields.One2many('po.lifecycle.item', 'po_id', string='Items')
    history_ids = fields.One2many('po.lifecycle.history', 'po_id', string='History')

    # ── Linked Purchase Order (native purchase module) ────────────────────────
    purchase_order_id = fields.Many2one(
        'purchase.order', string='Linked PO', readonly=True, copy=False,
    )
    purchase_order_state = fields.Selection(
        related='purchase_order_id.state', string='PO Status', readonly=True,
    )

    # ── Currency totals (computed from items) ─────────────────────────────────
    po_total_usd = fields.Monetary(
        compute='_compute_po_totals', currency_field='currency_usd_id',
        string='Total (USD)',
    )
    po_total_iqd = fields.Monetary(
        compute='_compute_po_totals', currency_field='currency_iqd_id',
        string='Total (IQD)',
    )
    po_total_eur = fields.Monetary(
        compute='_compute_po_totals', currency_field='currency_eur_id',
        string='Total (EUR)',
    )
    po_total_gbp = fields.Monetary(
        compute='_compute_po_totals', currency_field='currency_gbp_id',
        string='Total (GBP)',
    )

    # ── Compute methods ───────────────────────────────────────────────────────
    @api.depends('item_ids.item_price_usd', 'item_ids.item_price_iqd',
                 'item_ids.item_price_eur', 'item_ids.item_price_gbp',
                 'item_ids.item_qty')
    def _compute_po_totals(self):
        for rec in self:
            rec.po_total_usd = sum(i.item_price_usd * i.item_qty for i in rec.item_ids)
            rec.po_total_iqd = sum(i.item_price_iqd * i.item_qty for i in rec.item_ids)
            rec.po_total_eur = sum(i.item_price_eur * i.item_qty for i in rec.item_ids)
            rec.po_total_gbp = sum(i.item_price_gbp * i.item_qty for i in rec.item_ids)

    # ── ORM ───────────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('po_number'):
                vals['po_number'] = self.env['ir.sequence'].next_by_code(
                    'po.lifecycle'
                ) or 'New'
        return super().create(vals_list)

    # ── Auth helpers ──────────────────────────────────────────────────────────
    def _is_superadmin(self):
        return self.env.user.has_group('po_lifecycle.group_superadmin')

    def _is_po_admin_for_project(self):
        assignment = self.env['po.admin.assignment'].search([
            ('user_id', '=', self.env.uid),
            ('project_ids', 'in', self.project_id.id),
            ('active', '=', True),
        ], limit=1)
        return bool(assignment)

    def _check_position(self, position_code):
        if self._is_superadmin():
            return True
        users = self.env['po.lifecycle.position'].get_position_users(
            self.project_id.id, position_code
        )
        if self.env.user not in users:
            from odoo.addons.po_lifecycle.models.po_lifecycle_position import POSITION_SELECTION
            label = dict(POSITION_SELECTION).get(position_code, position_code)
            raise UserError(
                _('Only users with role "%s" on this project can perform this action.') % label
            )
        return True

    def _log_history(self, description, state_from=None, state_to=None):
        self.env['po.lifecycle.history'].create({
            'po_id': self.id,
            'user_id': self.env.uid,
            'description': description,
            'state_from': STATE_LABELS.get(state_from, state_from or ''),
            'state_to': STATE_LABELS.get(state_to, state_to or ''),
        })
        self.message_post(body=description)

    # ── Transitions ───────────────────────────────────────────────────────────
    def action_submit_to_inventory(self):
        for rec in self:
            if rec.state != '0':
                raise UserError(_('PO must be in Opening state.'))
            if not (rec.create_uid == self.env.user
                    or rec._is_po_admin_for_project()
                    or rec._is_superadmin()):
                raise UserError(_('You are not authorised to submit this PO.'))
            old = rec.state
            rec.write({'state': '1', 'submit_date': fields.Date.today(),
                       'submit_by': self.env.uid})
            rec._log_history('Submitted for Inventory Check', old, '1')

    def action_submit_to_store_pricing(self):
        for rec in self:
            if rec.state != '1':
                raise UserError(_('PO must be in Checking Inventory state.'))
            rec._check_position('5')
            old = rec.state
            rec.write({'state': '9', 'checking_inventory_date': fields.Date.today(),
                       'store_keeper_by': self.env.uid})
            rec._log_history('Inventory checked → Store Pricing', old, '9')

    def action_submit_to_market_pricing(self):
        for rec in self:
            if rec.state != '9':
                raise UserError(_('PO must be in Store Pricing state.'))
            rec._check_position('7')
            old = rec.state
            rec.write({'state': '2', 'store_pricing_date': fields.Date.today(),
                       'store_price_by': self.env.uid})
            rec._log_history('Store Pricing complete → Market Pricing', old, '2')

    def action_submit_to_price_check(self):
        for rec in self:
            if rec.state != '2':
                raise UserError(_('PO must be in Market Pricing state.'))
            rec._check_position('6')
            old = rec.state
            rec.write({'state': '22', 'pricing_date': fields.Date.today(),
                       'procurement_by': self.env.uid})
            rec._log_history('Submitted for Price Verification', old, '22')

    def action_submit_to_review(self):
        for rec in self:
            if rec.state != '22':
                raise UserError(_('PO must be in Checking Price state.'))
            rec._check_position('7')
            old = rec.state
            rec.write({'state': '3', 'price_check_date': fields.Date.today(),
                       'procurement_l2_by': self.env.uid})
            rec._log_history('Price verified → Review', old, '3')

    def action_reject_to_market_pricing(self):
        for rec in self:
            if rec.state != '3':
                raise UserError(_('PO must be in Review state.'))
            if not (rec.create_uid == self.env.user
                    or rec._is_po_admin_for_project()
                    or rec._is_superadmin()):
                raise UserError(_('Not authorised.'))
            old = rec.state
            rec.write({'state': '2'})
            rec._log_history('Rejected → back to Market Pricing', old, '2')

    def action_reject_to_store_pricing(self):
        for rec in self:
            if rec.state != '3':
                raise UserError(_('PO must be in Review state.'))
            if not (rec.create_uid == self.env.user
                    or rec._is_po_admin_for_project()
                    or rec._is_superadmin()):
                raise UserError(_('Not authorised.'))
            old = rec.state
            rec.write({'state': '9'})
            rec._log_history('Rejected → back to Store Pricing', old, '9')

    def action_request_approval(self):
        for rec in self:
            if rec.state != '3':
                raise UserError(_('PO must be in Review state.'))
            if not (rec.create_uid == self.env.user
                    or rec._is_po_admin_for_project()
                    or rec._is_superadmin()):
                raise UserError(_('Not authorised.'))
            old = rec.state
            rec.write({'state': '4', 'review_date': fields.Date.today()})
            rec._log_history('Requested Approval', old, '4')

    def action_reject_to_review(self):
        for rec in self:
            if rec.state not in ('4', '10'):
                raise UserError(_('PO must be in an approval state.'))
            if not (rec._is_po_admin_for_project()
                    or rec._is_superadmin()
                    or self.env.user == rec.assigned_dept_head_id):
                raise UserError(_('Not authorised to reject this PO.'))
            old = rec.state
            rec.write({'state': '3'})
            rec._log_history('Rejected → back to Review', old, '3')

    def action_assign_to_dept(self):
        self.ensure_one()
        if self.state != '4':
            raise UserError(_('PO must be in Need Approval state.'))
        if not (self._is_po_admin_for_project() or self._is_superadmin()):
            raise UserError(_('Only PO Admins can assign to dept head.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assign to Department Head'),
            'res_model': 'assign.dept.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_po_id': self.id},
        }

    def action_admin_approve(self):
        for rec in self:
            if rec.state != '4':
                raise UserError(_('PO must be in Need Approval state.'))
            if not (rec._is_po_admin_for_project() or rec._is_superadmin()):
                raise UserError(_('Only PO Admins or Super Admins can approve this PO.'))
            old = rec.state
            rec.write({'state': '8', 'approved_date': fields.Date.today(),
                       'approved_by': self.env.uid})
            rec._log_history('Approved by Admin', old, '8')
            rec._create_linked_purchase_order()

    def action_dept_approve(self):
        for rec in self:
            if rec.state != '10':
                raise UserError(_('PO must be in Need Dept Approval state.'))
            if self.env.user != rec.assigned_dept_head_id:
                raise UserError(_('Only the assigned Department Head can approve this PO.'))
            old = rec.state
            rec.write({'state': '8', 'approved_date': fields.Date.today(),
                       'approved_by': self.env.uid})
            rec._log_history('Approved by Dept Head', old, '8')
            rec._create_linked_purchase_order()

    def action_mark_complete(self):
        for rec in self:
            if rec.state != '8':
                raise UserError(_('PO must be Approved to mark complete.'))
            if not (rec.create_uid == self.env.user
                    or rec._is_po_admin_for_project()
                    or rec._is_superadmin()):
                raise UserError(_('Not authorised.'))
            old = rec.state
            rec.write({'state': '5', 'complete_date': fields.Date.today(),
                       'completed_by': self.env.uid})
            rec._log_history('Marked as Completed', old, '5')
            rec._confirm_purchase_order()

    def action_delete_po(self):
        for rec in self:
            if rec.state not in ('0', '1'):
                raise UserError(_('PO can only be deleted from Opening or Inventory state.'))
            if not (rec.create_uid == self.env.user or rec._is_superadmin()):
                raise UserError(_('Only the creator or Super Admin can delete a PO.'))
            old = rec.state
            rec.write({'state': '7', 'deleted_date': fields.Date.today()})
            rec._log_history('PO Deleted', old, '7')

    def action_view_purchase_order(self):
        self.ensure_one()
        if not self.purchase_order_id:
            raise UserError(_('No linked purchase order.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': self.purchase_order_id.id,
        }

    # ── Purchase Order integration ────────────────────────────────────────────
    def _get_generic_product(self):
        product = self.env['product.product'].search(
            [('name', '=', 'Miscellaneous Purchase'),
             ('can_be_purchased', '=', True)], limit=1
        )
        if not product:
            product = self.env['product.product'].create({
                'name': 'Miscellaneous Purchase',
                'type': 'service',
                'can_be_purchased': True,
            })
        return product

    def _create_linked_purchase_order(self):
        self.ensure_one()
        if self.purchase_order_id:
            return

        vendor = self.partner_id
        if not vendor:
            param = self.env['ir.config_parameter'].sudo().get_param(
                'po_lifecycle.default_vendor_id'
            )
            if param:
                vendor = self.env['res.partner'].browse(int(param))
        if not vendor:
            raise UserError(
                _('Please set a Vendor on the PO or configure a default vendor '
                  'in PO Lifecycle settings before approving.')
            )

        po = self.env['purchase.order'].create({
            'partner_id': vendor.id,
            'currency_id': self.po_currency_id.id,
            'date_order': fields.Datetime.now(),
            'origin': self.po_number,
            'notes': self.name,
            'company_id': self.env.company.id,
        })

        generic_product = None
        default_uom = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)

        for item in self.item_ids:
            cur_name = (item.selected_currency_id.name
                        or (self.po_currency_id.name if self.po_currency_id else 'USD'))
            price_map = {
                'USD': item.item_price_usd,
                'IQD': item.item_price_iqd,
                'EUR': item.item_price_eur,
                'GBP': item.item_price_gbp,
            }
            price_unit = price_map.get(cur_name, item.item_price_usd or 0.0)

            product = item.product_id
            if not product:
                if generic_product is None:
                    generic_product = self._get_generic_product()
                product = generic_product

            line_vals = {
                'order_id': po.id,
                'name': item.item_desc,
                'product_id': product.id,
                'product_qty': item.item_qty,
                'product_uom': (item.item_unit or default_uom).id,
                'price_unit': price_unit,
            }
            self.env['purchase.order.line'].create(line_vals)

        self.purchase_order_id = po
        self.message_post(
            body=_('Linked Purchase Order created: %s') % po.name
        )

    def _confirm_purchase_order(self):
        self.ensure_one()
        if self.purchase_order_id and self.purchase_order_id.state == 'draft':
            self.purchase_order_id.button_confirm()
