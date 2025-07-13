import json
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestMaterialApi(HttpCase):
    """Test cases for Material API endpoints"""

    def setUp(self):
        super(TestMaterialApi, self).setUp()
        self.Material = self.env['material.material'].sudo()
        self.Supplier = self.env['supplier.supplier'].sudo()

        # Create test supplier
        self.supplier = self.Supplier.create({
            'name': 'Test Supplier'
        })

        # Test material data
        self.test_material_data = {
            'name': 'Test Material',
            'code': 'TEST001',
            'type': 'fabric',
            'buy_price': 100.0,
            'supplier_id': self.supplier.id
        }

        # Base URL
        self.base_url = 'http://127.0.0.1:8069/api/material/'

    def _make_request(self, method, endpoint, data=None, headers=None):
        """Helper method to make HTTP requests"""
        url = f"{self.base_url}{endpoint}".rstrip('/')

        if method == 'GET':
            return self.url_open(url, headers=headers)

        elif method == 'POST':
            if headers is None:
                headers = {'Content-Type': 'application/json'}
            return self.url_open(url, data=json.dumps(data), headers=headers)

        elif method == 'PUT':
            if headers is None:
                headers = {'Content-Type': 'application/json'}
            return self.opener.put(url, data=json.dumps(data), headers=headers)

        elif method == 'DELETE':
            return self.opener.delete(url, headers=headers)

    def test_01_create_material_success(self):
        """Test creating a material with valid data returns 201 and creates record in DB"""
        # Verify no materials exist before test
        self.assertEqual(self.Material.search_count([]), 0,
                         "Test should start with no materials in DB")

        # Make the request
        response = self._make_request('POST', 'create', self.test_material_data)

        # Verify response status
        self.assertEqual(response.status_code, 200,
                         f"Expected status code 200 but got {response.status_code}")

        # Parse and verify response structure
        response_data = response.json()
        self.assertIn('result', response_data, "Response missing 'result' key")

        result_data = response_data['result']
        self.assertTrue(result_data['success'], "Expected success to be True")
        self.assertEqual(result_data['status_code'], 201,
                         f"Expected status_code 201 but got {result_data['status_code']}")

        # Verify response data
        self.assertIn('data', result_data, "Response missing 'data' key")
        self.assertIsInstance(result_data['data'], list, "Expected data to be a list")
        self.assertEqual(len(result_data['data']), 1, "Expected exactly one material in response")

        record_data = result_data['data'][0]

        # Verify all fields match what was sent
        for field, expected_value in self.test_material_data.items():
            self.assertIn(field, record_data, f"Missing field '{field}' in response")
            field_record_data = record_data[field]
            new_record_data = field_record_data[0] if isinstance(field_record_data, list) else field_record_data
            self.assertEqual(new_record_data, expected_value,
                             f"Field '{field}' value doesn't match")

        # Verify ID is returned and is an integer
        self.assertIn('id', record_data, "Response missing 'id' field")
        self.assertIsInstance(record_data['id'], int, "ID should be an integer")

        # Verify record exists in database
        material = self.Material.search([('id','=',record_data['id'])]).exists()
        self.assertTrue(material.exists(), "Material not found in database")

        # Verify only one record was created
        self.assertEqual(self.Material.search_count([]), 1,
                         "Expected exactly one material in database")

    def test_02_create_material_missing_required_field(self):
        """Test creating a material with missing required fields should not create a record"""
        for required_field in ['name', 'code', 'type', 'buy_price', 'supplier_id']:
            with self.subTest(field=required_field):
                initial_count = self.Material.search_count([])

                invalid_data = self.test_material_data.copy()
                del invalid_data[required_field]

                response = self._make_request('POST', 'create', invalid_data)
                self.assertEqual(response.status_code, 200)

                response_data = response.json()
                self.assertIn('result', response_data)
                result_data = response_data['result']

                self.assertFalse(result_data['success'])
                self.assertEqual(result_data['status_code'], 400)
                self.assertIn('missing fields', result_data['error']['message'].lower())

                final_count = self.Material.search_count([])
                self.assertEqual(initial_count, final_count,
                                 f"Material should not be created when '{required_field}' is missing.")

    def test_03_create_material_invalid_buy_price(self):
        """Test creating a material with invalid buy price should not create a record"""
        test_cases = [
            (-100.0, "negative price"),
            (99.99, "price below minimum"),
            ("not_a_number", "invalid data type"),
            (None, "null price")
        ]

        for price, description in test_cases:
            with self.subTest(description=description):
                initial_count = self.Material.search_count([])

                invalid_data = self.test_material_data.copy()
                invalid_data['buy_price'] = price

                response = self._make_request('POST', 'create', invalid_data)
                self.assertIn(response.status_code, [200, 500])

                response_data = response.json()
                self.assertFalse(response_data['result']['success'])
                self.assertIn(response_data['result']['status_code'], [400, 500])

                final_count = self.Material.search_count([])
                self.assertEqual(initial_count, final_count,
                                 f"Material should not be created for invalid price: {description}")

    def test_04_get_all_materials_success(self):
        """Test retrieving all materials"""
        materials = []
        for i in range(3):
            material_data = self.test_material_data.copy()
            material_data['code'] = f'TEST{i:03d}'
            material = self.Material.create(material_data)
            materials.append(material)

        response = self._make_request('GET', '')
        self.assertEqual(response.status_code, 200)
        response_data = response.json()

        self.assertTrue(response_data['success'])
        self.assertEqual(len(response_data['data']), 3)

        # Verify all created materials are in the response
        response_codes = {m['code'] for m in response_data['data']}
        for material in materials:
            self.assertIn(material.code, response_codes)

    def test_05_get_materials_with_valid_filter(self):
        """Test retrieving materials with valid filter"""
        material_types = ['fabric', 'leather', 'cotton']
        for mat_type in material_types:
            material_data = self.test_material_data.copy()
            material_data['type'] = mat_type
            material_data['code'] = f'TEST-{mat_type}'
            self.Material.create(material_data)

        for mat_type in material_types:
            with self.subTest(material_type=mat_type):
                response = self._make_request('GET', f'?type={mat_type}')
                self.assertEqual(response.status_code, 200)
                response_data = response.json()

                self.assertTrue(response_data['success'])
                self.assertGreater(len(response_data['data']), 0)
                for material in response_data['data']:
                    self.assertEqual(material['type'], mat_type)

    def test_06_update_material_success(self):
        """Test updating a material with valid data"""
        material = self.Material.create(self.test_material_data)

        update_data = {
            'name': 'Updated Material Name',
            'code': 'UPDATED-001',
            'type': 'leather',
            'buy_price': 150.0,
            'supplier_id': self.supplier.id
        }

        response = self._make_request('PUT', f'update/{material.id}', update_data)
        self.assertEqual(response.status_code, 200)
        response_data = response.json()

        self.assertTrue(response_data['result']['success'])
        self.assertEqual(response_data['result']['status_code'], 200)

        # Verify the update in database
        material.refresh()

        self.assertEqual(material.name, update_data['name'])
        self.assertEqual(material.code, update_data['code'])
        self.assertEqual(material.type, update_data['type'])
        self.assertEqual(material.buy_price, update_data['buy_price'])

    def test_07_update_material_not_found(self):
        """Test updating a non-existent material"""
        response = self._make_request('PUT', 'update/999999', {'name': 'Test'})
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertFalse(response_data['result']['success'])
        self.assertEqual(response_data['result']['status_code'], 404)
        self.assertIn('material not found', response_data['result']['error']['message'].lower())

    def test_08_delete_material_success(self):
        """Test deleting an existing material"""
        material = self.Material.create(self.test_material_data)

        self.assertTrue(self.Material.search([('id', '=', material.id)]))
        response = self._make_request('DELETE', f'delete/{material.id}')
        self.assertEqual(response.status_code, 200)
        response_data = response.json()

        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['status_code'], 200)
        self.assertEqual(response_data['data']['message'], 'Material deleted successfully')

        # Verify deletion
        self.assertFalse(self.Material.search([('id', '=', material.id)]))

    def test_09_delete_material_not_found(self):
        """Test deleting a non-existent material"""
        response = self._make_request('DELETE', 'delete/999999')
        self.assertEqual(response.status_code, 404)
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('material not found', response_data['error']['message'].lower())

    def tearDown(self):
        """Clean up after each test"""
        self.Material.search([]).unlink()
        self.Supplier.search([]).unlink()
        super(TestMaterialApi, self).tearDown()