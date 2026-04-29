# apps/ansible_app/executor.py
"""
Ansible Executor - Professional Implementation amélioré
Execute Ansible playbooks programmatically avec gestion avancée
"""
import subprocess
import json
import tempfile
import os
import yaml
import logging
import shlex
from pathlib import Path
from datetime import datetime
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class AnsibleExecutor:
    """
    Execute Ansible playbooks and commands avec gestion avancée
    """
    
    def __init__(self, playbook=None, inventory=None, execution=None):
        self.playbook = playbook
        self.inventory = inventory
        self.execution = execution
        self.playbooks_dir = getattr(settings, 'ANSIBLE_PLAYBOOKS_DIR', '/tmp/ansible/playbooks')
        self.inventory_dir = getattr(settings, 'ANSIBLE_INVENTORY_DIR', '/tmp/ansible/inventory')
        self.logs_dir = getattr(settings, 'ANSIBLE_LOGS_DIR', '/tmp/ansible/logs')
        
        # Créer les répertoires nécessaires
        os.makedirs(self.playbooks_dir, exist_ok=True)
        os.makedirs(self.inventory_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        
    def execute_playbook(self, playbook_content, inventory_content, extra_vars=None, 
                        check_mode=False, limit=None, tags=None, skip_tags=None,
                        execution_id=None):
        """
        Execute an Ansible playbook avec paramètres avancés
        
        Args:
            playbook_content (str): YAML playbook content
            inventory_content (str): Inventory content
            extra_vars (dict): Extra variables
            check_mode (bool): Run in check mode (dry-run)
            limit (str): Host pattern limit
            tags (list): Tags to run
            skip_tags (list): Tags to skip
            execution_id (str): Execution ID for logging
            
        Returns:
            dict: Execution result
        """
        temp_files = []
        
        try:
            # Create temporary files
            playbook_path = self._create_temp_file(
                playbook_content, 
                prefix=f'playbook_{execution_id}_' if execution_id else 'playbook_', 
                suffix='.yml'
            )
            temp_files.append(playbook_path)
            
            inventory_path = self._create_temp_file(
                inventory_content,
                prefix=f'inventory_{execution_id}_' if execution_id else 'inventory_',
                suffix='.ini'
            )
            temp_files.append(inventory_path)
            
            # Extra vars file
            vars_path = None
            if extra_vars:
                vars_path = self._create_temp_file(
                    yaml.dump(extra_vars),
                    prefix=f'vars_{execution_id}_' if execution_id else 'vars_',
                    suffix='.yml'
                )
                temp_files.append(vars_path)
            
            # Build command
            cmd = [
                'ansible-playbook',
                playbook_path,
                '-i', inventory_path,
                '--timeout', '600',  # 10 minutes
            ]
            
            # Add options
            if extra_vars:
                if vars_path:
                    cmd.extend(['--extra-vars', f'@{vars_path}'])
                else:
                    # IMPORTANT: Convertir en JSON string, pas en liste
                    extra_vars_json = json.dumps(extra_vars)
                    cmd.extend(['--extra-vars', extra_vars_json])
            
            if check_mode:
                cmd.append('--check')
            
            if limit:
                cmd.extend(['--limit', limit])
            
            # Gérer les tags (listes)
            if tags and isinstance(tags, list):
                cmd.extend(['--tags', ','.join(tags)])
            elif tags and isinstance(tags, str):
                cmd.extend(['--tags', tags])
            
            if skip_tags and isinstance(skip_tags, list):
                cmd.extend(['--skip-tags', ','.join(skip_tags)])
            elif skip_tags and isinstance(skip_tags, str):
                cmd.extend(['--skip-tags', skip_tags])
            
            # Verbose output
            cmd.append('-vvv')
            
            # Log file
            log_file = os.path.join(
                self.logs_dir, 
                f"ansible_{execution_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            ) if execution_id else None
            
            logger.info(f"Executing command: {' '.join(shlex.quote(str(arg)) for arg in cmd)}")
            
            # Execute
            if log_file:
                with open(log_file, 'w') as f:
                    f.write(f"Command: {' '.join(cmd)}\n\n")
                    f.flush()
                    
                    result = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=600
                    )
                    
                    f.write("=== STDOUT ===\n")
                    f.write(result.stdout)
                    f.write("\n=== STDERR ===\n")
                    f.write(result.stderr)
            else:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600
                )
            
            # Parse summary
            summary = self._parse_summary(result.stdout)
            host_results = self._parse_host_results(result.stdout)
            
            return {
                'success': result.returncode == 0,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': ' '.join(str(arg) for arg in cmd),  # Convertir tous les args en str
                'summary': summary,
                'host_results': host_results,
                'log_file': log_file
            }
            
        except subprocess.TimeoutExpired:
            logger.error("Execution timeout")
            return {
                'success': False,
                'error': 'Execution timeout (10 minutes)',
                'stdout': '',
                'stderr': 'TimeoutExpired',
                'summary': {},
                'host_results': {}
            }
        except Exception as e:
            logger.exception(f"Execution error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'stdout': '',
                'stderr': str(e),
                'summary': {},
                'host_results': {}
            }
        finally:
            # Cleanup temporary files
            for f in temp_files:
                try:
                    os.unlink(f)
                except:
                    pass
    
    def _create_temp_file(self, content, prefix='tmp_', suffix='.txt'):
        """Crée un fichier temporaire avec le contenu"""
        with tempfile.NamedTemporaryFile(
            mode='w',
            prefix=prefix,
            suffix=suffix,
            delete=False
        ) as f:
            f.write(content)
            return f.name
    
    def _parse_summary(self, output):
        """Parse le summary de l'exécution"""
        summary = {
            'plays': 0,
            'tasks': 0,
            'changed': 0,
            'failed': 0,
            'ok': 0,
            'skipped': 0,
            'unreachable': 0,
            'rescued': 0,
            'ignored': 0
        }
        
        try:
            lines = output.split('\n')
            in_recap = False
            
            for line in lines:
                if 'PLAY RECAP' in line:
                    in_recap = True
                    continue
                
                if in_recap and '=>' in line:
                    # Parse recap line
                    parts = line.split()
                    for part in parts:
                        if ':' in part:
                            key, value = part.split(':')
                            try:
                                if key in summary:
                                    summary[key] += int(value)
                            except:
                                pass
        except Exception as e:
            logger.error(f"Error parsing summary: {e}")
        
        return summary
    
    def _parse_host_results(self, output):
        """Parse les résultats par hôte"""
        host_results = {}
        
        try:
            lines = output.split('\n')
            current_host = None
            current_task = None
            
            for line in lines:
                # Détecter les résultats par hôte
                if 'ok: [' in line or 'changed: [' in line or 'failed: [' in line:
                    import re
                    match = re.search(r'\[(.*?)\]', line)
                    if match:
                        host = match.group(1)
                        if host not in host_results:
                            host_results[host] = {
                                'ok': 0,
                                'changed': 0,
                                'failed': 0,
                                'unreachable': 0,
                                'tasks': []
                            }
                        
                        if 'ok:' in line:
                            host_results[host]['ok'] += 1
                        elif 'changed:' in line:
                            host_results[host]['changed'] += 1
                        elif 'failed:' in line:
                            host_results[host]['failed'] += 1
        except Exception as e:
            logger.error(f"Error parsing host results: {e}")
        
        return host_results