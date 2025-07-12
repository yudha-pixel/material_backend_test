from odoo import models, fields, api

class Supplier(models.Model):
    _name = 'supplier.supplier'
    _description = 'Supplier'

    name = fields.Char(string='Supplier Name', required=True)