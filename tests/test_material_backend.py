import json
import unittest
from odoo.tests import common, tagged
from odoo import http
from odoo.tools import mute_logger

@tagged('post_install', '-after_install')
class TestMaterialBackend(common.HttpCase):
    def setUp(self):
        super(TestMaterialBackend, self).setUp()
        self.Material = self.env['material.material']
        self.Supplier = self.env['supplier.supplier']
        
        # Create test supplier
        self.test_supplier = self.Supplier.create({
            'name': 'Test Supplier',
        })
        
        # Test material data
        self.test_material_data = {
            'name': 'Test Material',
            'code': 'TEST001',
            'type': 'fabric',
            'buy_price': 100.0,
            'supplier_id': self.test_supplier.id
        }
    
    def test_001_fetch_material_utility(self):
        """Test the fetch_material utility function"""
        # Test with material_id
        material = self.Material.create(self.test_material_data)
        result = self.url_open('/api/material/', data=json.dumps({}), method='GET').json()
        self.assertEqual(result['status'], 200)
        
        # Test with domain
        domain = [('type', '=', 'fabric')]
        result = self.url_open(
            '/api/material/', 
            data=json.dumps({'type': 'fabric'}), 
            method='GET'
        ).json()
        self.assertEqual(result['status'], 200)
        self.assertTrue(any(m['code'] == 'TEST001' for m in result.get('data', [])))
    
    def test_002_create_material(self):
        """Test material creation"""
        # Authenticate as demo user
        self.authenticate('demo', 'demo')
        
        # Test successful creation
        response = self.url_open(
            '/api/material/create',
            data=json.dumps(self.test_material_data),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['status'], 200)
        self.assertIn('id', result)
        
        # Verify the material was created
        material = self.Material.browse(result['id'])
        self.assertEqual(material.name, self.test_material_data['name'])
        self.assertEqual(material.code, self.test_material_data['code'])
    
    def test_003_update_material(self):
        """Test material update"""
        # Create a material first
        material = self.Material.create(self.test_material_data)
        
        # Test update
        update_data = {
            'name': 'Updated Material',
            'buy_price': 150.0
        }
        response = self.url_open(
            f'/api/material/update?{material.id}',
            data=json.dumps(update_data),
            headers={'Content-Type': 'application/json'},
            method='PUT'
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['status'], 200)
        
        # Verify the update
        material.refresh()
        self.assertEqual(material.name, 'Updated Material')
        self.assertEqual(material.buy_price, 150.0)
    
    def test_004_delete_material(self):
        """Test material deletion"""
        # Create a material first
        material = self.Material.create(self.test_material_data)
        material_id = material.id
        
        # Test deletion
        response = self.url_open(
            f'/api/material/delete{material_id}',
            method='DELETE'
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['status'], 200)
        
        # Verify deletion
        self.assertFalse(self.Material.browse(material_id).exists())
    
    def test_005_unauthorized_access(self):
        """Test unauthorized access to protected endpoints"""
        # Test create material without authentication
        response = self.url_open(
            '/api/material/create',
            data=json.dumps(self.test_material_data),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        self.assertEqual(response.status_code, 200)  # Odoo returns 200 even for auth errors
        result = response.json()
        self.assertEqual(result['status'], 400)  # Should fail with auth error
    
    def test_006_invalid_data_handling(self):
        """Test handling of invalid data"""
        # Test create with invalid data
        invalid_data = self.test_material_data.copy()
        invalid_data['buy_price'] = 'invalid_price'
        
        response = self.url_open(
            '/api/material/create',
            data=json.dumps(invalid_data),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['status'], 400)
        self.assertIn('message', result)