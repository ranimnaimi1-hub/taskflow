# apps/ansible_app/validators.py
"""
Ansible App Validators - Validation des playbooks et inventaires
"""
import yaml
import json
import re


def validate_playbook_content(content):
    """
    Valide la syntaxe YAML d'un playbook Ansible
    
    Args:
        content (str): Contenu YAML du playbook
        
    Returns:
        dict: Résultat de la validation avec 'valid' et 'message'
    """
    if not content or not content.strip():
        return {
            'valid': False,
            'message': 'Playbook content is empty'
        }
    
    try:
        # Vérifier la syntaxe YAML
        data = yaml.safe_load(content)
        
        if data is None:
            return {
                'valid': False,
                'message': 'Playbook content is empty or invalid YAML'
            }
        
        # Un playbook doit être une liste
        if not isinstance(data, list):
            return {
                'valid': False,
                'message': 'Playbook must be a list of plays'
            }
        
        if len(data) == 0:
            return {
                'valid': False,
                'message': 'Playbook must contain at least one play'
            }
        
        # Valider chaque play
        for i, play in enumerate(data):
            if not isinstance(play, dict):
                return {
                    'valid': False,
                    'message': f'Play at index {i} must be a dictionary'
                }
            
            # Vérifier les champs obligatoires
            if 'name' not in play:
                # Le nom n'est pas obligatoire mais recommandé
                pass
            
            if 'hosts' not in play:
                return {
                    'valid': False,
                    'message': f'Play at index {i} missing required field "hosts"'
                }
            
            # Vérifier qu'il y a des tâches ou des rôles
            has_tasks = 'tasks' in play and play['tasks']
            has_roles = 'roles' in play and play['roles']
            
            if not has_tasks and not has_roles:
                return {
                    'valid': False,
                    'message': f'Play at index {i} must contain either "tasks" or "roles"'
                }
            
            # Vérifier les tâches si présentes
            if has_tasks and not isinstance(play['tasks'], list):
                return {
                    'valid': False,
                    'message': f'Play at index {i}: "tasks" must be a list'
                }
            
            # Vérifier les rôles si présents
            if has_roles and not isinstance(play['roles'], list):
                return {
                    'valid': False,
                    'message': f'Play at index {i}: "roles" must be a list'
                }
        
        return {
            'valid': True,
            'message': 'Playbook has valid YAML syntax and structure'
        }
        
    except yaml.YAMLError as e:
        return {
            'valid': False,
            'message': f'YAML syntax error: {str(e)}'
        }
    except Exception as e:
        return {
            'valid': False,
            'message': f'Validation error: {str(e)}'
        }


def validate_inventory_content(content, format='ini'):
    """
    Valide le contenu d'un inventaire Ansible
    
    Args:
        content (str): Contenu de l'inventaire
        format (str): Format de l'inventaire ('ini', 'yaml', 'json')
        
    Returns:
        dict: Résultat de la validation avec 'valid' et 'message'
    """
    if not content or not content.strip():
        return {
            'valid': False,
            'message': 'Inventory content is empty'
        }
    
    if format == 'yaml' or format == 'yml':
        return _validate_yaml_inventory(content)
    elif format == 'json':
        return _validate_json_inventory(content)
    else:  # INI par défaut
        return _validate_ini_inventory(content)


def _validate_yaml_inventory(content):
    """Valide un inventaire au format YAML"""
    try:
        data = yaml.safe_load(content)
        
        if data is None:
            return {
                'valid': False,
                'message': 'YAML inventory is empty'
            }
        
        # Un inventaire YAML peut être un dict (groupes) ou une liste (hosts)
        if not isinstance(data, (dict, list)):
            return {
                'valid': False,
                'message': 'YAML inventory must be a dictionary or list'
            }
        
        # Si c'est un dict, vérifier la structure des groupes
        if isinstance(data, dict):
            for group_name, group_content in data.items():
                if not isinstance(group_content, dict):
                    # Peut être une simple liste d'hôtes
                    if not isinstance(group_content, list):
                        return {
                            'valid': False,
                            'message': f'Group "{group_name}" content must be a dictionary or list'
                        }
        
        return {
            'valid': True,
            'message': 'YAML inventory has valid syntax'
        }
        
    except yaml.YAMLError as e:
        return {
            'valid': False,
            'message': f'YAML syntax error: {str(e)}'
        }


def _validate_json_inventory(content):
    """Valide un inventaire au format JSON"""
    try:
        data = json.loads(content)
        
        # Un inventaire JSON peut être un dict (groupes) ou une liste (hosts)
        if not isinstance(data, (dict, list)):
            return {
                'valid': False,
                'message': 'JSON inventory must be a dictionary or list'
            }
        
        return {
            'valid': True,
            'message': 'JSON inventory has valid syntax'
        }
        
    except json.JSONDecodeError as e:
        return {
            'valid': False,
            'message': f'JSON syntax error: {str(e)}'
        }


def _validate_ini_inventory(content):
    """Valide un inventaire au format INI"""
    lines = content.split('\n')
    in_group = False
    current_group = None
    line_num = 0
    
    for line in lines:
        line_num += 1
        line = line.strip()
        
        # Ignorer les commentaires et lignes vides
        if not line or line.startswith(';') or line.startswith('#'):
            continue
        
        # Détection des groupes [group]
        if line.startswith('[') and line.endswith(']'):
            group_name = line[1:-1].strip()
            if not group_name:
                return {
                    'valid': False,
                    'message': f'Line {line_num}: Empty group name'
                }
            in_group = True
            current_group = group_name
            continue
        
        # Lignes d'hôtes
        if in_group:
            # Format: hostname ansible_host=ip ansible_user=user
            parts = line.split()
            if len(parts) == 0:
                continue
            
            hostname = parts[0]
            if not re.match(r'^[a-zA-Z0-9\.\-_]+$', hostname):
                # Ce n'est pas grave, les hostnames peuvent avoir des caractères spéciaux
                pass
            
            # Vérifier les variables
            for part in parts[1:]:
                if '=' not in part:
                    return {
                        'valid': False,
                        'message': f'Line {line_num}: Invalid variable format "{part}", expected key=value'
                    }
        else:
            # Lignes hors groupe (devrait être après un groupe)
            return {
                'valid': False,
                'message': f'Line {line_num}: Host definition outside of any group'
            }
    
    return {
        'valid': True,
        'message': 'INI inventory has valid syntax'
    }


def validate_host_pattern(pattern):
    """
    Valide un pattern d'hôtes Ansible
    
    Args:
        pattern (str): Pattern d'hôtes (ex: "webservers", "db*", "all:!prod")
        
    Returns:
        bool: True si valide
    """
    if not pattern:
        return True
    
    # Patterns Ansible acceptés
    # - simple: webservers
    # - wildcard: web*
    # - regex: ~web\d+
    # - exclusion: all:!prod
    # - intersection: webservers:&staging
    
    # Vérifier les caractères autorisés
    allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789*?!:&;,.@_-~')
    
    for char in pattern:
        if char not in allowed_chars and not char.isspace():
            return False
    
    return True


def validate_ansible_module(module_name):
    """
    Valide un nom de module Ansible
    
    Args:
        module_name (str): Nom du module (ex: "ping", "copy", "command")
        
    Returns:
        bool: True si valide
    """
    if not module_name:
        return False
    
    # Un nom de module Ansible doit être alphanumérique avec underscores
    return bool(re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', module_name))


def validate_extra_vars(vars_dict):
    """
    Valide des variables supplémentaires
    
    Args:
        vars_dict (dict): Dictionnaire de variables
        
    Returns:
        dict: Résultat de la validation
    """
    if not isinstance(vars_dict, dict):
        return {
            'valid': False,
            'message': 'Extra vars must be a dictionary'
        }
    
    # Vérifier les clés (doivent être des strings)
    for key in vars_dict.keys():
        if not isinstance(key, str):
            return {
                'valid': False,
                'message': f'Variable key "{key}" must be a string'
            }
        
        if not key.isidentifier():
            return {
                'valid': False,
                'message': f'Variable key "{key}" is not a valid identifier'
            }
    
    return {
        'valid': True,
        'message': 'Extra vars are valid'
    }


def sanitize_playbook_name(name):
    """
    Nettoie un nom de playbook pour le système de fichiers
    
    Args:
        name (str): Nom du playbook
        
    Returns:
        str: Nom nettoyé
    """
    # Remplacer les caractères non alphanumériques par des underscores
    import re
    sanitized = re.sub(r'[^a-zA-Z0-9\-_]', '_', name)
    # Éviter les doubles underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Supprimer les underscores au début et à la fin
    return sanitized.strip('_')


def validate_yaml_file(file_content):
    """
    Valide un fichier YAML générique
    
    Args:
        file_content (str): Contenu du fichier
        
    Returns:
        dict: Résultat de la validation
    """
    try:
        yaml.safe_load(file_content)
        return {
            'valid': True,
            'message': 'Valid YAML file'
        }
    except yaml.YAMLError as e:
        return {
            'valid': False,
            'message': f'Invalid YAML: {str(e)}'
        }


def validate_json_file(file_content):
    """
    Valide un fichier JSON générique
    
    Args:
        file_content (str): Contenu du fichier
        
    Returns:
        dict: Résultat de la validation
    """
    try:
        json.loads(file_content)
        return {
            'valid': True,
            'message': 'Valid JSON file'
        }
    except json.JSONDecodeError as e:
        return {
            'valid': False,
            'message': f'Invalid JSON: {str(e)}'
        }