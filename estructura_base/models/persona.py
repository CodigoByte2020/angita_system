import logging
import re
import requests
from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

TIPO_DOCUMENTO_SELECTION = [
    ('dni', 'Documento nacional de identidad'),
    ('ruc', 'Registro único de contribuyentes')
]

dni_validator = re.compile(r'^\d{8}$')
ce_validator = re.compile(r'^\d{9}$')
ruc_validator = re.compile(r'^\d{11}$')
email_re = re.compile(r"""([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63})""")


class Persona(models.Model):
    _name = 'base.persona'
    _description = 'Clientes y Proveedores'

    name = fields.Char(string='Nombre')
    tipo_documento = fields.Selection(TIPO_DOCUMENTO_SELECTION, string='Tipo de Documento', required=True)
    numero_documento = fields.Char(string='Número de documento', required=True)
    direccion = fields.Text(string='Dirección')
    celular = fields.Char(string='Celular')
    email = fields.Char(string='Email')
    rango_cliente = fields.Integer(default=0)
    rango_proveedor = fields.Integer(default=0)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    estado = fields.Char(string='Estado')
    condicion = fields.Char(string='Condición')

    _sql_constraints = [
        ('name_uniq', 'unique(numero_documento)', 'Ya existe un Cliente con el Número de documento ingresado. !!!'),
    ]

    @api.model_create_multi  # CHANGE
    def create(self, vals_list):
        self.consult_data(vals_list)
        return super(Persona, self).create(vals_list)

    @api.onchange('tipo_documento')
    def _onchange_tipo_documento(self):
        if self.tipo_documento:
            return {'value': {'numero_documento': False}}

    @api.onchange('numero_documento')
    def _onchange_numero_documento(self):
        if self.numero_documento:
            if self.tipo_documento == 'dni' and not dni_validator.match(self.numero_documento):
                raise ValidationError('El Número de documento debe tener 8 números.')
            elif self.tipo_documento == 'ruc' and not ruc_validator.match(self.numero_documento):
                raise ValidationError('El Número de documento debe tener 11 números.')

    @api.onchange('email')
    def _onchange_email(self):
        if self.email and not email_re.match(self.email):
            return {
                'warning': {'title': 'ERROR', 'message': 'Formato de Email no válido. !!!'},
                'value': {'email': False}
            }

    @api.depends('name', 'numero_documento')  # CHANGE
    def _compute_display_name(self):
        for persona in self:
            persona.display_name = f'{persona.name} - {persona.numero_documento}'

    def consult_data(self, values):
        """
        Método para consultar datos de las personas en la siguiente url https://apis.net.pe/
        :param values: parámetros para consultar en la url
        :type values: dict
        :return: No retorna ningún valor
        :rtype: None
        """
        tipo_documento = values.get("tipo_documento", self.tipo_documento)
        numero_documento = values.get("numero_documento", self.numero_documento)
        url = f'https://api.apis.net.pe/v1/{tipo_documento}'
        args = {'numero': numero_documento}
        # TRY: CÓDIGO SUCEPTIBLE A ERROR
        try:
            response = requests.get(url=url, params=args)
        # CAPTURAMOS LA EXEPCIÓN
        except requests.exceptions.RequestException as exception:
            _logger.info(f'*********************** LA CONEXIÓN FALLO *********************** {exception}')
            raise ValidationError('La conexión falló al consultar los datos. !!!')
        # SI NO OCURRE NINGUNA EXEPCIÓN
        else:
            if response.status_code == 200:
                response_json = response.json()
                nombre = response_json.get('nombre', '')
                direccion = response_json.get('direccion', '')
                provincia = response_json.get('provincia', '')
                estado = response_json.get('estado', '')
                condicion = response_json.get('condicion', '')
                values.update({
                    'name': nombre,
                    'direccion': direccion and provincia and f'{direccion} {provincia} - PERÚ',
                    'estado': estado,
                    'condicion': condicion
                })
            elif response.status_code == 422:
                raise ValidationError(f'El Número de documento {numero_documento} no cumple con las reglas de '
                                      f'validación')
            elif response.status_code == 404:
                raise ValidationError(f'El Número de documento {numero_documento} no existe')

    def get_type_document_report(self):
        type_document = dict(self._fields['tipo_documento'].selection)
        for key, value in type_document.items():
            if key == self.tipo_documento:
                return key.upper()

    def write(self, values):
        self.consult_data(values)
        return super(Persona, self).write(values)
