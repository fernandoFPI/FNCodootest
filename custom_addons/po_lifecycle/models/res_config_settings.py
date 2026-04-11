from odoo import api, fields, models


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def _activate_po_currencies(self):
        """Activate USD, IQD, EUR, GBP on module install."""
        for code in ('USD', 'IQD', 'EUR', 'GBP'):
            currency = self.with_context(active_test=False).search(
                [('name', '=', code)], limit=1
            )
            if currency and not currency.active:
                currency.write({'active': True})


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    po_lifecycle_default_vendor_id = fields.Many2one(
        'res.partner',
        string='Default PO Vendor',
        config_parameter='po_lifecycle.default_vendor_id',
    )
    po_lifecycle_primary_currency_id = fields.Many2one(
        'res.currency',
        string='Primary PO Currency',
        config_parameter='po_lifecycle.primary_currency_id',
    )
    po_lifecycle_secondary_currency_id = fields.Many2one(
        'res.currency',
        string='Secondary Display Currency',
        config_parameter='po_lifecycle.secondary_currency_id',
    )
    po_lifecycle_require_dept_approval = fields.Boolean(
        string='Require Department Head Approval',
        config_parameter='po_lifecycle.require_dept_approval',
        default=True,
    )

    def action_manage_po_admins(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'PO Admin Assignments',
            'res_model': 'po.admin.assignment',
            'view_mode': 'list,form',
            'target': 'current',
        }
