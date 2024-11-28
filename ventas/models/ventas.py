from datetime import datetime
from itertools import groupby

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.estructura_base.models.constantes import (
    CONFIRMADO,
    PENDIENTE,
    UTILIZADO,
    CANCELADO,
    STATE_SELECTION
)

TIPO_VENTA_SELECTION = [
    ('contado', 'Contado'),
    ('credito', 'Crédito')
]

TYPE_DOCUMENT_SELECTION = [
    ('invoice', 'Factura'),
    ('ticket', 'Boleta')
]


class Ventas(models.Model):
    _name = 'ventas'
    _description = 'Registro de ventas'

    name = fields.Char(string='Número', default='/', copy=False)
    cliente_id = fields.Many2one('base.persona', string='Cliente', required=True, domain=[('rango_cliente', '=', 1)])
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user.id, string='Responsable', readonly=True)
    tipo_venta = fields.Selection(TIPO_VENTA_SELECTION, default='contado', required=True, string='Tipo de venta')
    fecha = fields.Date(default=fields.Date.today(), readonly=True, string='Fecha')
    amount_untaxed = fields.Float(compute='_compute_total', store=True, string='Ope. Gravadas')
    amount_tax = fields.Float(compute='_compute_total', store=True, string='IGV 18%')
    total = fields.Float(compute='_compute_total', store=True, string='Importe Total')
    comentarios = fields.Text(string='Comentarios')
    detalle_ventas_ids = fields.One2many(
        comodel_name='detalle.ventas',
        inverse_name='venta_id',
        string='Líneas de pedido'
    )
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, string='Moneda')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, string='Compañía')
    type_document = fields.Selection(TYPE_DOCUMENT_SELECTION, default='invoice', string='Tipo de documento')
    state = fields.Selection(STATE_SELECTION, default=PENDIENTE, string='Estado')

    @api.constrains('tipo_venta')
    def _check_tipo_venta(self):
        for rec in self:
            if rec.tipo_venta == 'credito':
                credito = self.env['credito.cliente'].search([('cliente_id', '=', rec.cliente_id.id)])
                if not credito:
                    raise ValidationError(f'El cliente {rec.cliente_id.name} no tiene ningun crédito registrado.')

    @api.depends('detalle_ventas_ids.subtotal')
    def _compute_total(self):
        for move in self:
            total = sum(move.detalle_ventas_ids.mapped('subtotal'))
            model_config_parameter = self.env['ir.config_parameter'].sudo()
            igv_porcentaje = float(model_config_parameter.get_param('igv_key')) / 100.0
            amount_tax = total * igv_porcentaje
            move.update({
                'amount_untaxed': total - amount_tax,
                'amount_tax': total,
                'total': total
            })

    def action_set_confirm(self):
        self.detalle_ventas_ids.mapped(lambda record: record.action_set_confirm())
        self.write({'state': CONFIRMADO})

    def action_set_cancel(self):
        self.detalle_ventas_ids.mapped(lambda record: record.action_set_cancel())
        self.write({'state': CANCELADO})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                company_id = vals.get('company_id', self.env.company.id)
                vals['name'] = self.env['ir.sequence'].with_company(company_id).next_by_code(self._name) or '/'
        return super(Ventas, self).create(vals_list)


class DetalleVentas(models.Model):
    _name = 'detalle.ventas'
    _description = 'Líneas de pedido de ventas'

    venta_id = fields.Many2one('ventas', string='Venta', required=True)
    producto_id = fields.Many2one('base.producto', string='Producto', required=True)
    cantidad = fields.Float(string='Cantidad')
    precio_venta = fields.Float(compute='_compute_precio_venta', string='Precio unitario')
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)
    currency_id = fields.Many2one(related='venta_id.currency_id')
    name_venta = fields.Char(related='venta_id.name')

    @api.depends('producto_id')
    def _compute_precio_venta(self):
        for rec in self:
            sales_price_history_ids = rec.producto_id.sales_price_history_ids.filtered(
                lambda x: x.modified_date <= rec.venta_id.fecha)
            new_price = sales_price_history_ids and sales_price_history_ids.sorted(
                key=lambda x: x.modified_date)[-1].new_price
            rec.update({'precio_venta': new_price})

    @api.depends('cantidad', 'precio_venta')
    def _compute_subtotal(self):
        for rec in self:
            if rec.cantidad and rec.precio_venta:
                rec.update({'subtotal': rec.cantidad * rec.precio_venta})

    def validate_stock(self):
        quantity_product = self.env['movimientos'].search([('producto_id', '=', self.producto_id.id)],
                                                          order='id DESC', limit=1).total
        if self.cantidad > quantity_product:
            raise ValidationError(
                f'La Cantidad solicitada para el Producto {self.producto_id.name} es de {self.cantidad} y esta excede '
                f'su stock actual -> {self.producto_id.stock}\nAsegúrese de tener el inventario actualizado para '
                f'registrar la venta correctamente.')

    def update_validate_stock(self):
        movements_model = self.env['movimientos']
        current_movement = movements_model.search([('detalle_venta_ids', '=', self.id)])
        quantity_product = (movements_model.search([('producto_id', '=', self.producto_id.id)],
                                                   order='create_date DESC', limit=2) - current_movement).total
        if self.cantidad > quantity_product:
            raise ValidationError(
                f'La Cantidad solicitada para el Producto {self.producto_id.name} es de {self.cantidad} y esta excede '
                f'su stock actual -> {self.producto_id.stock}\nAsegúrese de tener el inventario actualizado para '
                f'registrar la venta correctamente.')

    def create_movement(self):
        movements_model = self.env['movimientos']
        last_movement = movements_model.search([('producto_id', '=', self.producto_id.id)], order='id DESC', limit=1)
        movements_model.create({
            'detalle_venta_ids': [(4, self.id, False)],
            'tipo': 'out',
            'user_id': self.venta_id.user_id.id,
            'fecha': datetime.now(),
            'producto_id': self.producto_id.id,
            'cantidad': self.cantidad,
            'total': last_movement.total - self.cantidad,
        })

    def update_movement(self):
        movements_model = self.env['movimientos']
        movement = movements_model.search([('detalle_venta_ids', '=', self.id)])
        last_movement = movements_model.search([('producto_id', '=', self.producto_id.id)],
                                               order='create_date DESC', limit=2) - movement
        movement.update({
            'fecha': datetime.now(),
            'producto_id': self.producto_id,
            'cantidad': self.cantidad,
            'total': last_movement.total - self.cantidad
        })

    def action_set_confirm(self):
        self.ensure_one()
        self.validate_stock()
        self.create_movement()

    def action_set_cancel(self):
        self.ensure_one()
        movements_model = self.env['movimientos']
        last_movement = movements_model.search([('producto_id', '=', self.producto_id.id)], order='id DESC',
                                               limit=1)
        movements_model.create({
            'detalle_venta_ids': [(4, self.id), False],
            'tipo': 'in',
            'user_id': self.venta_id.user_id.id,
            'fecha': datetime.now(),
            'producto_id': self.producto_id.id,
            'cantidad': self.cantidad,
            'total': last_movement.total + self.cantidad,
        })


class Movimientos(models.Model):
    _inherit = 'movimientos'

    detalle_venta_ids = fields.Many2many('detalle.ventas')
