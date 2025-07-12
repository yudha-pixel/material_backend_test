from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Material(models.Model):
    _name = 'material.material'
    _description = 'Material'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    type = fields.Selection([('fabric', 'Fabric'), ('leather', 'Leather'), ('cotton','Cotton')],
                            string='Type', required=True)
    buy_price = fields.Float(string='Buy Price', required=True)
    supplier_id = fields.Many2one('supplier.supplier', string='Supplier', required=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Code must be unique')
    ]

    @api.constrains('buy_price')
    def _check_buy_price(self):
        for record in self:
            if record.buy_price < 100:
                raise ValidationError('Buy price cannot be less than 100')