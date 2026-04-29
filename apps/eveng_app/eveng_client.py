"""
EVE-NG API Client - Professional Implementation
"""
import requests
from django.conf import settings


class EVENGClient:
    """EVE-NG API Client"""
    
    def __init__(self, url=None, username=None, password=None):
        self.url = (url or getattr(settings, 'EVENG_URL', 'http://eveng:80')).rstrip('/')
        self.username = username or getattr(settings, 'EVENG_USERNAME', 'admin')
        self.password = password or getattr(settings, 'EVENG_PASSWORD', 'eve')
        self.session = requests.Session()
        self.cookie = None
    
    def login(self):
        """Login to EVE-NG"""
        try:
            data = {'username': self.username, 'password': self.password}
            response = self.session.post(f'{self.url}/api/auth/login', json=data)
            if response.status_code == 200:
                self.cookie = response.cookies.get('unetlab_session')
                return {'success': True, 'message': 'Logged in'}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_system_status(self):
        """Get system status"""
        try:
            response = self.session.get(f'{self.url}/api/status')
            if response.status_code == 200:
                return {'success': True, 'status': response.json()}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_labs(self):
        """Get all labs"""
        try:
            response = self.session.get(f'{self.url}/api/labs')
            if response.status_code == 200:
                return {'success': True, 'labs': response.json()}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_lab(self, lab_path):
        """Get lab details"""
        try:
            response = self.session.get(f'{self.url}/api/labs/{lab_path}')
            if response.status_code == 200:
                return {'success': True, 'lab': response.json()}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def start_lab(self, lab_path):
        """Start all nodes in lab"""
        try:
            response = self.session.get(f'{self.url}/api/labs/{lab_path}/nodes/start')
            if response.status_code == 200:
                return {'success': True, 'message': 'Lab started'}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def stop_lab(self, lab_path):
        """Stop all nodes in lab"""
        try:
            response = self.session.get(f'{self.url}/api/labs/{lab_path}/nodes/stop')
            if response.status_code == 200:
                return {'success': True, 'message': 'Lab stopped'}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_nodes(self, lab_path):
        """Get all nodes in lab"""
        try:
            response = self.session.get(f'{self.url}/api/labs/{lab_path}/nodes')
            if response.status_code == 200:
                return {'success': True, 'nodes': response.json()}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def start_node(self, lab_path, node_id):
        """Start specific node"""
        try:
            response = self.session.get(f'{self.url}/api/labs/{lab_path}/nodes/{node_id}/start')
            if response.status_code == 200:
                return {'success': True, 'message': 'Node started'}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def stop_node(self, lab_path, node_id):
        """Stop specific node"""
        try:
            response = self.session.get(f'{self.url}/api/labs/{lab_path}/nodes/{node_id}/stop')
            if response.status_code == 200:
                return {'success': True, 'message': 'Node stopped'}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
