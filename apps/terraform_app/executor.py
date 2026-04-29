"""
Terraform Executor - Professional Implementation
Execute Terraform commands programmatically
"""
import subprocess
import json
import os
from pathlib import Path
from django.conf import settings


class TerraformExecutor:
    """
    Execute Terraform commands
    """
    
    def __init__(self, working_dir=None):
        self.working_dir = working_dir or getattr(settings, 'TERRAFORM_WORKDIR', '/opt/terraform')
        self.ensure_working_dir()
    
    def ensure_working_dir(self):
        """Ensure working directory exists"""
        Path(self.working_dir).mkdir(parents=True, exist_ok=True)
    
    def init(self, config_dir):
        """
        Initialize Terraform working directory
        
        Args:
            config_dir (str): Directory containing .tf files
            
        Returns:
            dict: Init result
        """
        try:
            cmd = ['terraform', 'init', '-no-color']
            result = subprocess.run(
                cmd,
                cwd=config_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def plan(self, config_dir, var_file=None, out_file=None):
        """
        Create execution plan
        
        Args:
            config_dir (str): Directory containing .tf files
            var_file (str): Path to variables file
            out_file (str): Path to save plan
            
        Returns:
            dict: Plan result
        """
        try:
            cmd = ['terraform', 'plan', '-no-color', '-detailed-exitcode']
            
            if var_file:
                cmd.extend(['-var-file', var_file])
            
            if out_file:
                cmd.extend(['-out', out_file])
            
            result = subprocess.run(
                cmd,
                cwd=config_dir,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            # Exit codes: 0=no changes, 1=error, 2=changes present
            return {
                'success': result.returncode in [0, 2],
                'has_changes': result.returncode == 2,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def apply(self, config_dir, plan_file=None, auto_approve=False):
        """
        Apply Terraform configuration
        
        Args:
            config_dir (str): Directory containing .tf files
            plan_file (str): Path to saved plan file
            auto_approve (bool): Skip approval prompt
            
        Returns:
            dict: Apply result
        """
        try:
            cmd = ['terraform', 'apply', '-no-color']
            
            if auto_approve:
                cmd.append('-auto-approve')
            
            if plan_file:
                cmd.append(plan_file)
            
            result = subprocess.run(
                cmd,
                cwd=config_dir,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def destroy(self, config_dir, auto_approve=False):
        """
        Destroy Terraform-managed infrastructure
        
        Args:
            config_dir (str): Directory containing .tf files
            auto_approve (bool): Skip approval prompt
            
        Returns:
            dict: Destroy result
        """
        try:
            cmd = ['terraform', 'destroy', '-no-color']
            
            if auto_approve:
                cmd.append('-auto-approve')
            
            result = subprocess.run(
                cmd,
                cwd=config_dir,
                capture_output=True,
                text=True,
                timeout=1800
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate(self, config_dir):
        """
        Validate Terraform configuration
        
        Args:
            config_dir (str): Directory containing .tf files
            
        Returns:
            dict: Validation result
        """
        try:
            cmd = ['terraform', 'validate', '-json']
            result = subprocess.run(
                cmd,
                cwd=config_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            validation_output = json.loads(result.stdout) if result.stdout else {}
            
            return {
                'valid': validation_output.get('valid', False),
                'diagnostics': validation_output.get('diagnostics', []),
                'stdout': result.stdout
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
    
    def show_state(self, config_dir):
        """
        Show current state
        
        Args:
            config_dir (str): Directory containing .tf files
            
        Returns:
            dict: State information
        """
        try:
            cmd = ['terraform', 'show', '-json']
            result = subprocess.run(
                cmd,
                cwd=config_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                state = json.loads(result.stdout) if result.stdout else {}
                return {
                    'success': True,
                    'state': state
                }
            else:
                return {
                    'success': False,
                    'error': result.stderr
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def output(self, config_dir, name=None):
        """
        Get output values
        
        Args:
            config_dir (str): Directory containing .tf files
            name (str): Specific output name (optional)
            
        Returns:
            dict: Output values
        """
        try:
            cmd = ['terraform', 'output', '-json']
            if name:
                cmd.append(name)
            
            result = subprocess.run(
                cmd,
                cwd=config_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                outputs = json.loads(result.stdout) if result.stdout else {}
                return {
                    'success': True,
                    'outputs': outputs
                }
            else:
                return {
                    'success': False,
                    'error': result.stderr
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def format_check(self, config_dir):
        """
        Check if files are properly formatted
        
        Args:
            config_dir (str): Directory containing .tf files
            
        Returns:
            dict: Format check result
        """
        try:
            cmd = ['terraform', 'fmt', '-check', '-recursive']
            result = subprocess.run(
                cmd,
                cwd=config_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                'formatted': result.returncode == 0,
                'files_to_format': result.stdout.split('\n') if result.stdout else []
            }
        except Exception as e:
            return {
                'formatted': False,
                'error': str(e)
            }
