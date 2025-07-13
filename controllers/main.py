from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request, Response
import json

def json_response(success, data=None, error_code=None, error_message=None, request_method=None):
    """
        Function to standardize response
    """

    status_code = 200
    if not success:
        status_code = error_code or 400
    elif request_method and request_method.upper() == 'POST':
        status_code = 201

    payload = {
        'success': success,
        'data': data,
        'status_code': status_code,
        'error': None if success else {
            'code': error_code or status_code,
            'message': error_message
        }
    }

    return payload


def validate_payload(request_obj, data, specs):
    """
        Function to validate input type

        :param request_obj: Request Object of Odoo.
        :param data: Data JSON from request.
        :param specs: Validation specs.
                      Example: {'field': {'type': str, 'is_selection': True}}
        :return: Tuple (boolean, string)
    """
    for field, rules in specs.items():
        if field in data and data[field] is not None:
            expected_type = rules.get('type')
            if not isinstance(data[field], expected_type):
                return False, f"Field '{field}' must be of type '{expected_type}'"

            selection_model = rules.get('is_selection')
            if selection_model:
                is_valid, error_message = validate_selection_field(request_obj, field, data[field])
                if not is_valid:
                    return False, error_message

    return True, None

def validate_selection_field(model_obj, field_name, value_to_check):
    """
        Function to validate selection field

        :param model_obj: Request Object of Odoo
        :param field_name: Field name to validate
        :param value_to_check: Value to validate
    """
    if not value_to_check:
        return True, None

    try:
        field = model_obj.fields_get([field_name])['type']
        valid_values = [value for value, label in field['selection']]
    except KeyError:
        return False, f"Invalid field '{field_name}' in model '{type(model_obj).__name__}'"

    if value_to_check not in valid_values:
        return False, f"Invalid value '{value_to_check}' for field '{field_name}' in model '{type(model_obj).__name__}'"

    return True, None


class MaterialBackendTestController(http.Controller):

    type_specs = {
        'name': {'type':str},
        'code': {'type':(str, int)},
        'type': {'type':str, 'is_selection':True},
        'buy_price': {'type':(int, float)},
        'supplier_id': {'type':int},
    }
    allowed_filter = ['type']

    @http.route('/api/material', type='http', auth='public', methods=['GET'], csrf=False)
    def list_materials(self, **kwargs):
        material_obj = request.env['material.material'].sudo()

        domain = []
        for key in set(kwargs.keys()) & set(self.allowed_filter):
            domain.append((key, '=', kwargs[key]))

        materials = material_obj.search_read(domain, ['id', 'name', 'code', 'type', 'buy_price', 'supplier_id'])
        payload = json_response(True, data=materials)
        return Response(
            json.dumps(payload),
            content_type='application/json',
            status=200
        )

    @http.route('/api/material/create', type='json', auth='public', methods=['POST'], csrf=False)
    def create_material(self, **kwargs):
        data = request.jsonrequest
        if not data:
            return json_response(False, error_code=400, error_message='No data provided')

        material_obj = request.env['material.material'].sudo()

        is_valid, error_message = validate_payload(material_obj, data, self.type_specs)
        if not is_valid:
            return json_response(False, error_code=400, error_message=error_message)

        missing_fields = [data_field for data_field in self.type_specs if data_field not in data]
        if missing_fields:
            return json_response(False,
                                 error_code=400,
                                 error_message=f'missing fields in request: {", ".join(missing_fields)}')

        if not data.get('buy_price'):
            return json_response(False, error_code=400, error_message='Buy price is required and cannot be null')

        if data.get('buy_price') < 100:
            return json_response(False, error_code=400, error_message='Buy price cannot be less than 100')

        supplier_id = data.get('supplier_id')
        supplier_obj = request.env['supplier.supplier'].sudo()
        supplier = supplier_obj.search([('id','=',supplier_id)])

        if not supplier:
            return json_response(False, error_code=404, error_message='Supplier not found')

        try:
            created_material = material_obj.create(data)
            material_data = created_material.read(['id', 'name', 'code', 'type', 'buy_price', 'supplier_id'])
            new_json_response = json_response(True, data=material_data, request_method=request.httprequest.method)
            return new_json_response
        except ValidationError as e:
            return json_response(False, error_code=400, error_message=str(e.args[0]))
        except Exception as e:
            return json_response(False, error_code=500, error_message=f"An unexpected server error occurred: {e}")

    @http.route('/api/material/update/<int:material_id>', type='json', auth='public', methods=['PUT'], csrf=False)
    def update_material(self, material_id, **kwargs):
        material_obj = request.env['material.material'].sudo()
        material = material_obj.search([('id', '=', material_id)])
        if not material:
            return json_response(False, error_code=404, error_message='Material not found')

        data = request.jsonrequest
        if not data:
            return json_response(False, error_code=400, error_message='No data provided')

        is_valid, error_message = validate_payload(material_obj, data, self.type_specs)
        if not is_valid:
            return json_response(False, error_code=400, error_message=error_message)

        if data.get('buy_price') and data.get('buy_price') < 100:
            return json_response(False, error_code=400, error_message='Buy price cannot be less than 100')

        if data.get('supplier_id'):
            supplier_obj = request.env['supplier.supplier'].sudo()
            supplier = supplier_obj.search([('id','=',data.get('supplier_id'))])
            if not supplier:
                return json_response(False, error_code=404, error_message='Supplier not found')

        try:
            material.write(data)
            material_data = material.read(['id', 'name', 'code', 'type', 'buy_price', 'supplier_id'])[0]
            return json_response(True, data=material_data)
        except ValidationError as e:
            return json_response(False, error_code=400, error_message=str(e.args[0]))
        except Exception as e:
            return json_response(False, error_code=500, error_message=f"An unexpected server error occurred: {e}")

    @http.route('/api/material/delete/<int:material_id>', type='http', auth='public', methods=['DELETE'], csrf=False)
    def delete_material(self, material_id, **kwargs):
        material_obj = request.env['material.material'].sudo()
        material = material_obj.search([('id','=',material_id)])
        if not material:
            payload = json_response(False, error_code=404, error_message='Material not found')
            return Response(
                json.dumps(payload),
                content_type='application/json',
                status=404
            )

        try:
            material.unlink()
            payload = json_response(True, data={'message': 'Material deleted successfully'})
            return Response(
                json.dumps(payload),
                content_type='application/json',
                status=200
            )
        except Exception as e:
            payload = json_response(False, error_code=500, error_message=f"An unexpected server error occurred: {e}")
            return Response(
                json.dumps(payload),
                content_type='application/json',
                status=500
            )