from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request, Response
import json

def json_response(success, data=None, error_code=None, error_message=None):
    """
        Function to standardize response
    """
    payload = {
        'success': success,
        'data': data,
        'error': None
    }
    status_code = 200

    if not success:
        payload['error'] = {
            'code': error_message,
            'message': error_message
        }
        status_code = error_code

    elif request.httprequest.method == 'POST' and success:
        status_code = 201
    return Response(json.dumps(payload), content_type='application/json', status=status_code)

# function to validate input type
def validate_payload(data, specs):
    """
        Function to validate input type
    """
    for field, expected_type in specs.items():
        if field in data:
            if data[field] is not None and not isinstance(data[field], expected_type):
                type_name = expected_type.__name__
                if isinstance(expected_type, type):
                    type_name = ' or '.join([t.__name__ for t in expected_type])

                return False, f"field '{field}' must be a {type_name}"
    return True, None


class MaterialBackendTestController(http.Controller):

    required_fields = ['name', 'code', 'type', 'buy_price', 'supplier_id']

    @http.route('/api/material/', type='json', auth='public', methods=['GET'], csrf=False)
    def list_materials(self, **kwargs):
        material_type = kwargs.get('type')
        domain = []
        if material_type:
            domain = [('type', '=', material_type)]
        material_obj = request.env['material.material'].sudo()
        materials = material_obj.search_read(domain, ['id', 'name', 'code', 'type', 'buy_price', 'supplier_id'])
        return json_response(True, data=materials)

    @http.route('/api/material/create', type='json', auth='public', methods=['POST'], csrf=False)
    def create_material(self, **kwargs):
        data = request.jsonrequest

        type_specs = {
            'name': str,
            'code': str,
            'type': str,
            'buy_price': (int, float),
            'supplier_id': int,
        }
        is_valid, error_message = validate_payload(data, type_specs)
        if not is_valid:
            return json_response(False, error_code=400, error_message=error_message)

        missing_fields = [data_field for data_field in self.required_fields if data_field not in data]
        if missing_fields:
            return json_response(False, error_code=400, error_message=f'missing fields in request: {", ".join(missing_fields)}')

        supplier_id = data.get('supplier_id')
        supplier_obj = request.env['supplier.supplier'].sudo()
        supplier = supplier_obj.browse(supplier_id)

        if not supplier:
            return json_response(False, error_code=404, error_message='Supplier not found')

        try:
            created_material = request.env['material.material'].sudo().create(data)
            material_data = created_material.read(['id', 'name', 'code', 'type', 'buy_price', 'supplier_id'])
            return json_response(True, data=material_data)
        except Exception as e:
            return json_response(False, error_code=500, error_message=f"An unexpected server error occurred: {e}")

    @http.route('/api/material/update/<int:material_id>', type='json', auth='public', methods=['PUT'], csrf=False)
    def update_material(self, material_id, **kwargs):
        material_obj = request.env['material.material'].sudo()
        material = material_obj.browse(material_id)
        if not material:
            return json_response(False, error_code=404, error_message='Material not found')

        data = request.jsonrequest
        if not data:
            return json_response(False, error_code=400, error_message='No data provided')

        type_specs = {
            'name': str,
            'code': str,
            'type': str,
            'buy_price': (int, float),
            'supplier_id': int,
        }

        is_valid, error_message = validate_payload(data, type_specs)
        if not is_valid:
            return json_response(False, error_code=400, error_message=error_message)

        if data.get('supplier_id'):
            supplier_obj = request.env['supplier.supplier'].sudo()
            supplier = supplier_obj.browse(data.get('supplier_id'))
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

    @http.route('/api/material/delete/<int:material_id>', type='json', auth='public', methods=['DELETE'], csrf=False)
    def delete_material(self, material_id, **kwargs):
        material_obj = request.env['material.material'].sudo()
        material = material_obj.browse(material_id)
        if not material:
            return json_response(False, error_code=404, error_message='Material not found')

        try:
            material.unlink()
            return json_response(True, data={'message': 'Material deleted successfully'})
        except Exception as e:
            return json_response(False, error_code=500, error_message=f"An unexpected server error occurred: {e}")
