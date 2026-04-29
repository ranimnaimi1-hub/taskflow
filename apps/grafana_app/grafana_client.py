"""
Grafana API Client - Professional Implementation
"""
import requests
from django.conf import settings


class GrafanaClient:
    """Grafana API Client"""
    
    def __init__(self, url=None, api_key=None):
        self.url = (url or getattr(settings, 'GRAFANA_URL', 'http://192.168.177.136:3001')).rstrip('/')
        self.api_key = api_key or getattr(settings, 'GRAFANA_API_KEY', '')
        self.headers = {'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'}
    
    def get_health(self):
        """Check Grafana health"""
        try:
            response = requests.get(f'{self.url}/api/health')
            return {'success': response.status_code == 200, 'data': response.json()}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_dashboards(self):
        """Get all dashboards"""
        try:
            response = requests.get(f'{self.url}/api/search?type=dash-db', headers=self.headers)
            if response.status_code == 200:
                return {'success': True, 'dashboards': response.json()}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_dashboard(self, dashboard_uid):
        """Get dashboard by UID"""
        try:
            response = requests.get(f'{self.url}/api/dashboards/uid/{dashboard_uid}', headers=self.headers)
            if response.status_code == 200:
                return {'success': True, 'dashboard': response.json()}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def create_dashboard(self, dashboard_json):
        """Create a new dashboard"""
        try:
            response = requests.post(f'{self.url}/api/dashboards/db', headers=self.headers, json=dashboard_json)
            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_dashboard(self, dashboard_json):
        """Update existing dashboard"""
        try:
            response = requests.post(f'{self.url}/api/dashboards/db', headers=self.headers, json=dashboard_json)
            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_dashboard(self, dashboard_uid):
        """Delete dashboard"""
        try:
            response = requests.delete(f'{self.url}/api/dashboards/uid/{dashboard_uid}', headers=self.headers)
            if response.status_code == 200:
                return {'success': True, 'message': 'Dashboard deleted'}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_datasources(self):
        """Get all datasources"""
        try:
            response = requests.get(f'{self.url}/api/datasources', headers=self.headers)
            if response.status_code == 200:
                return {'success': True, 'datasources': response.json()}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def create_datasource(self, datasource_config):
        """Create new datasource"""
        try:
            response = requests.post(f'{self.url}/api/datasources', headers=self.headers, json=datasource_config)
            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_alerts(self):
        """Get all alerts"""
        try:
            response = requests.get(f'{self.url}/api/alerts', headers=self.headers)
            if response.status_code == 200:
                return {'success': True, 'alerts': response.json()}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_alert(self, alert_id):
        """Get alert by ID"""
        try:
            response = requests.get(f'{self.url}/api/alerts/{alert_id}', headers=self.headers)
            if response.status_code == 200:
                return {'success': True, 'alert': response.json()}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}