"""
Jenkins API Client - Professional Implementation
"""
import requests
from requests.auth import HTTPBasicAuth
from django.conf import settings


class JenkinsClient:
    """Jenkins API Client"""
    
    def __init__(self, url=None, username=None, password=None):
        self.url = (url or getattr(settings, 'JENKINS_URL', 'http://localhost:9090')).rstrip('/')
        self.username = username or getattr(settings, 'JENKINS_USERNAME', 'ranim')
        self.password = password or getattr(settings, 'JENKINS_PASSWORD', '118d4d1e5a476b402e686a38ce3d6eda55')
        self.auth = HTTPBasicAuth(self.username, self.password)
        self.session = requests.Session()
        self.session.auth = self.auth
    
    def get_version(self):
        """Get Jenkins version"""
        try:
            response = self.session.get(f'{self.url}/api/json')
            if response.status_code == 200:
                return {'success': True, 'version': response.headers.get('X-Jenkins', 'Unknown')}
            return {'success': False, 'error': 'Failed to get version'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_jobs(self):
        """Get all jobs"""
        try:
            response = self.session.get(f'{self.url}/api/json?tree=jobs[name,url,color]')
            if response.status_code == 200:
                data = response.json()
                return {'success': True, 'jobs': data.get('jobs', [])}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_job_info(self, job_name):
        """Get job information"""
        try:
            response = self.session.get(f'{self.url}/job/{job_name}/api/json')
            if response.status_code == 200:
                return {'success': True, 'job': response.json()}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def build_job(self, job_name, parameters=None):
        """Trigger job build"""
        try:
            if parameters:
                url = f'{self.url}/job/{job_name}/buildWithParameters'
                response = self.session.post(url, data=parameters)
            else:
                url = f'{self.url}/job/{job_name}/build'
                response = self.session.post(url)
            
            if response.status_code in [200, 201]:
                return {'success': True, 'message': 'Build triggered'}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_build_info(self, job_name, build_number):
        """Get build information"""
        try:
            response = self.session.get(f'{self.url}/job/{job_name}/{build_number}/api/json')
            if response.status_code == 200:
                return {'success': True, 'build': response.json()}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_build_console(self, job_name, build_number):
        """Get build console output"""
        try:
            response = self.session.get(f'{self.url}/job/{job_name}/{build_number}/consoleText')
            if response.status_code == 200:
                return {'success': True, 'console': response.text}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def stop_build(self, job_name, build_number):
        """Stop a running build"""
        try:
            response = self.session.post(f'{self.url}/job/{job_name}/{build_number}/stop')
            if response.status_code == 200:
                return {'success': True, 'message': 'Build stopped'}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_queue(self):
        """Get build queue"""
        try:
            response = self.session.get(f'{self.url}/queue/api/json')
            if response.status_code == 200:
                data = response.json()
                return {'success': True, 'queue': data.get('items', [])}
            return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}