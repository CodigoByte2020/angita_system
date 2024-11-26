from odoo import api, fields, models


class Producto(models.Model):
    _inherit = 'base.producto'

    categoria_id = fields.Many2one('categoria.producto', required=True, string='Categoría')
    movimiento_ids = fields.One2many('movimientos', 'producto_id')
    stock = fields.Float(string='Stock', compute='_compute_stock', store=True, aggregator=None)  # CHANGE

    @api.depends('movimiento_ids.total')  # REVIEW THIS FUNCTION
    def _compute_stock(self):
        for rec in self:
            product = self.env['movimientos'].search([('producto_id', '=', rec.id)], order='fecha DESC', limit=1)
            rec.update({'stock': product.total})


class CategoriaProducto(models.Model):
    _name = 'categoria.producto'
    _description = 'Categoría de productos'

    name = fields.Char(string='Nombre', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'El Nombre ya existe. !!!'),
    ]
