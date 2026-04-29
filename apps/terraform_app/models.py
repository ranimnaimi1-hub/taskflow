# apps/terraform_app/models.py
"""
Terraform App Models - Professional
Gestion des configurations Terraform et des déploiements IaC
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.core.models import BaseModel
from apps.users.models import User
import json
import os


# ============================================================================
# CONFIGURATIONS TERRAFORM
# ============================================================================

class TerraformConfig(BaseModel):
    """
    Configuration Terraform - Gestion des fichiers .tf
    """
    PROVIDER_CHOICES = [
        ('aws', 'Amazon Web Services'),
        ('azure', 'Microsoft Azure'),
        ('gcp', 'Google Cloud Platform'),
        ('openstack', 'OpenStack'),
        ('vmware', 'VMware vSphere'),
        ('proxmox', 'Proxmox VE'),
        ('kubernetes', 'Kubernetes'),
        ('docker', 'Docker'),
        ('custom', 'Custom Provider'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('deprecated', 'Deprecated'),
    ]
    
    name = models.CharField('Name', max_length=200, unique=True, db_index=True)
    description = models.TextField('Description', blank=True)
    
    # Provider
    provider = models.CharField('Provider', max_length=20, choices=PROVIDER_CHOICES, default='custom')
    provider_version = models.CharField('Provider Version', max_length=50, blank=True)
    
    # Fichiers de configuration
    main_tf = models.TextField('main.tf', help_text="Main Terraform configuration", blank=True)
    variables_tf = models.TextField('variables.tf', help_text="Variables definitions", blank=True)
    outputs_tf = models.TextField('outputs.tf', help_text="Outputs definitions", blank=True)
    terraform_tfvars = models.TextField('terraform.tfvars', help_text="Variable values", blank=True)
    
    # Fichiers externes
    config_files = models.JSONField('Config Files', default=dict, blank=True, 
                                   help_text="Additional configuration files (key: filename, value: content)")
    
    # Variables (version structurée)
    variables = models.JSONField('Variables', default=dict, blank=True, 
                                help_text="Structured variables")
    
    # Backend configuration
    backend_type = models.CharField('Backend Type', max_length=50, blank=True,
                                   help_text="e.g., s3, azurerm, gcs, local")
    backend_config = models.JSONField('Backend Config', default=dict, blank=True)
    
    # Versioning
    version = models.CharField('Version', max_length=50, default='1.0.0')
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Statistiques
    apply_count = models.IntegerField('Apply Count', default=0)
    last_apply_status = models.CharField('Last Apply Status', max_length=20, blank=True)
    last_apply_at = models.DateTimeField('Last Apply At', null=True, blank=True)
    
    # ========================================================================
    # RELATIONS OPTIONNELLES AVEC INVENTORY
    # ========================================================================
    
    # Association avec les sites (si la config déploie sur un site spécifique)
    site = models.ForeignKey(
        'inventory.Site', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='terraform_configs',
        help_text="Site où cette configuration est déployée"
    )
    
    # Association avec les clusters (si la config déploie sur un cluster)
    cluster = models.ForeignKey(
        'inventory.Cluster', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='terraform_configs',
        help_text="Cluster où cette configuration est déployée"
    )
    
    # Association avec les tenants (propriétaire de la config)
    tenant = models.ForeignKey(
        'inventory.Tenant', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='terraform_configs',
        help_text="Tenant propriétaire de cette configuration"
    )
    
    # ========================================================================
    
    # Propriétaire
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='terraform_configs'
    )
    
    # Utilisateurs autorisés
    allowed_users = models.ManyToManyField(
        User, 
        related_name='shared_terraform_configs', 
        blank=True,
        help_text="Users allowed to access this configuration"
    )
    
    class Meta:
        db_table = 'terraform_configs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['provider']),
            models.Index(fields=['status']),
            models.Index(fields=['created_by']),
            models.Index(fields=['site']),
            models.Index(fields=['cluster']),
            models.Index(fields=['tenant']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_provider_display()}) v{self.version}"
    
    def save(self, *args, **kwargs):
        # Assurer que les fichiers sont cohérents avec les variables structurées
        if self.variables and not self.variables_tf:
            self.generate_variables_tf()
        super().save(*args, **kwargs)
    
    def generate_variables_tf(self):
        """Génère le contenu de variables.tf à partir des variables structurées"""
        lines = []
        for var_name, var_config in self.variables.items():
            var_type = var_config.get('type', 'string')
            var_description = var_config.get('description', '')
            var_default = var_config.get('default', None)
            
            lines.append(f'variable "{var_name}" {{')
            if var_description:
                lines.append(f'  description = "{var_description}"')
            lines.append(f'  type        = {var_type}')
            if var_default is not None:
                if isinstance(var_default, str):
                    lines.append(f'  default     = "{var_default}"')
                else:
                    lines.append(f'  default     = {var_default}')
            lines.append('}')
            lines.append('')
        
        self.variables_tf = '\n'.join(lines)
    
    def get_full_config(self):
        """Retourne tous les fichiers de configuration"""
        config = {
            'main.tf': self.main_tf,
            'variables.tf': self.variables_tf,
            'outputs.tf': self.outputs_tf,
            'terraform.tfvars': self.terraform_tfvars,
        }
        config.update(self.config_files)
        return config
    
    def validate_config(self):
        """Valide la configuration"""
        errors = []
        
        # Vérifier que main.tf existe
        if not self.main_tf.strip():
            errors.append("main.tf is required")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }


# ============================================================================
# PLANS TERRAFORM
# ============================================================================

class TerraformPlan(BaseModel):
    """
    Terraform Plan - Résultat de terraform plan
    """
    PLAN_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    config = models.ForeignKey(
        TerraformConfig, 
        on_delete=models.CASCADE, 
        related_name='plans'
    )
    
    # Informations du plan
    plan_id = models.CharField('Plan ID', max_length=100, blank=True)
    plan_file = models.FileField('Plan File', upload_to='terraform/plans/', null=True, blank=True)
    plan_json = models.JSONField('Plan JSON', default=dict, blank=True)
    
    # Résumé du plan
    resources_add = models.IntegerField('Resources to Add', default=0)
    resources_change = models.IntegerField('Resources to Change', default=0)
    resources_destroy = models.IntegerField('Resources to Destroy', default=0)
    
    # Métadonnées
    status = models.CharField('Status', max_length=20, choices=PLAN_STATUS_CHOICES, default='pending')
    has_changes = models.BooleanField('Has Changes', default=False)
    
    # Exécution
    executed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='terraform_plans'
    )
    started_at = models.DateTimeField('Started At', null=True, blank=True)
    completed_at = models.DateTimeField('Completed At', null=True, blank=True)
    duration = models.FloatField('Duration (s)', null=True, blank=True)
    
    # Résultats
    stdout = models.TextField('Output', blank=True)
    stderr = models.TextField('Error Output', blank=True)
    return_code = models.IntegerField('Return Code', null=True, blank=True)
    
    class Meta:
        db_table = 'terraform_plans'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['config', '-created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Plan for {self.config.name} - {self.created_at}"
    
    def parse_plan_summary(self):
        """Parse le plan pour extraire le résumé"""
        if self.plan_json:
            try:
                resource_changes = self.plan_json.get('resource_changes', [])
                for change in resource_changes:
                    action = change.get('change', {}).get('actions', [])
                    if 'create' in action:
                        self.resources_add += 1
                    if 'update' in action:
                        self.resources_change += 1
                    if 'delete' in action:
                        self.resources_destroy += 1
                self.has_changes = (self.resources_add + self.resources_change + self.resources_destroy) > 0
                self.save(update_fields=['resources_add', 'resources_change', 'resources_destroy', 'has_changes'])
            except Exception as e:
                pass


# ============================================================================
# APPLICATIONS TERRAFORM
# ============================================================================

class TerraformApply(BaseModel):
    """
    Terraform Apply - Résultat de terraform apply
    """
    APPLY_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    config = models.ForeignKey(
        TerraformConfig, 
        on_delete=models.CASCADE, 
        related_name='applies'
    )
    plan = models.ForeignKey(
        TerraformPlan, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='applies'
    )
    
    # Métadonnées
    apply_id = models.CharField('Apply ID', max_length=100, blank=True)
    status = models.CharField('Status', max_length=20, choices=APPLY_STATUS_CHOICES, default='pending')
    
    # Exécution
    executed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='terraform_applies'
    )
    started_at = models.DateTimeField('Started At', null=True, blank=True)
    completed_at = models.DateTimeField('Completed At', null=True, blank=True)
    duration = models.FloatField('Duration (s)', null=True, blank=True)
    
    # Résultats
    stdout = models.TextField('Output', blank=True)
    stderr = models.TextField('Error Output', blank=True)
    return_code = models.IntegerField('Return Code', null=True, blank=True)
    
    # État après apply
    state_json = models.JSONField('State', default=dict, blank=True)
    outputs = models.JSONField('Outputs', default=dict, blank=True)
    
    class Meta:
        db_table = 'terraform_applies'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['config', '-created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Apply for {self.config.name} - {self.status}"


# ============================================================================
# ÉTATS TERRAFORM
# ============================================================================

class TerraformState(BaseModel):
    """
    Terraform State - Snapshots de l'état
    """
    config = models.ForeignKey(
        TerraformConfig, 
        on_delete=models.CASCADE, 
        related_name='states'
    )
    apply = models.ForeignKey(
        TerraformApply, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='states'
    )
    
    # État
    state_file = models.FileField('State File', upload_to='terraform/states/', null=True, blank=True)
    state_json = models.JSONField('State JSON', default=dict, blank=True)
    
    # Métadonnées
    version = models.IntegerField('Version', default=1)
    lineage = models.CharField('Lineage', max_length=100, blank=True)
    serial = models.IntegerField('Serial', default=0)
    
    # Résumé
    resources_count = models.IntegerField('Resources Count', default=0)
    resources_summary = models.JSONField('Resources Summary', default=dict, blank=True)
    
    # Timestamps
    captured_at = models.DateTimeField('Captured At', auto_now_add=True)
    
    class Meta:
        db_table = 'terraform_states'
        ordering = ['-captured_at']
        unique_together = ['config', 'version']
    
    def __str__(self):
        return f"State for {self.config.name} v{self.version}"
    
    def parse_state(self):
        """Parse l'état pour extraire les informations"""
        if self.state_json:
            resources = []
            try:
                # Parcourir les ressources
                for module in self.state_json.get('modules', []):
                    for resource_name, resource_data in module.get('resources', {}).items():
                        resources.append({
                            'name': resource_name,
                            'type': resource_data.get('type'),
                            'provider': resource_data.get('provider'),
                        })
                
                self.resources_count = len(resources)
                self.resources_summary = {
                    'by_type': {},
                    'by_provider': {}
                }
                
                for r in resources:
                    r_type = r['type']
                    provider = r['provider']
                    
                    if r_type not in self.resources_summary['by_type']:
                        self.resources_summary['by_type'][r_type] = 0
                    self.resources_summary['by_type'][r_type] += 1
                    
                    if provider not in self.resources_summary['by_provider']:
                        self.resources_summary['by_provider'][provider] = 0
                    self.resources_summary['by_provider'][provider] += 1
                
                self.save(update_fields=['resources_count', 'resources_summary'])
            except Exception as e:
                pass


# ============================================================================
# MODULES TERRAFORM
# ============================================================================

class TerraformModule(BaseModel):
    """
    Modules Terraform réutilisables
    """
    SOURCE_CHOICES = [
        ('local', 'Local'),
        ('registry', 'Terraform Registry'),
        ('git', 'Git Repository'),
        ('http', 'HTTP URL'),
    ]
    
    name = models.CharField('Name', max_length=200, unique=True)
    namespace = models.CharField('Namespace', max_length=200, default='local')
    version = models.CharField('Version', max_length=50, default='1.0.0')
    
    # Source
    source = models.CharField('Source', max_length=20, choices=SOURCE_CHOICES, default='local')
    source_url = models.URLField('Source URL', blank=True)
    source_version = models.CharField('Source Version', max_length=100, blank=True)
    
    # Métadonnées
    description = models.TextField('Description', blank=True)
    documentation = models.URLField('Documentation', blank=True)
    
    # Contenu du module
    module_path = models.CharField('Module Path', max_length=500, blank=True)
    readme = models.TextField('README', blank=True)
    
    # Variables d'entrée/sortie
    input_variables = models.JSONField('Input Variables', default=list, blank=True)
    output_variables = models.JSONField('Output Variables', default=list, blank=True)
    
    # Dépendances
    required_providers = models.JSONField('Required Providers', default=dict, blank=True)
    
    # Statistiques
    download_count = models.IntegerField('Download Count', default=0)
    used_in_configs = models.IntegerField('Used in Configs', default=0)
    
    class Meta:
        db_table = 'terraform_modules'
        ordering = ['namespace', 'name']
        unique_together = ['namespace', 'name', 'version']
    
    def __str__(self):
        return f"{self.namespace}/{self.name}:{self.version}"


# ============================================================================
# PROVIDERS TERRAFORM
# ============================================================================

class TerraformProvider(BaseModel):
    """
    Providers Terraform
    """
    name = models.CharField('Name', max_length=100, unique=True)
    version = models.CharField('Version', max_length=50, default='latest')
    source = models.CharField('Source', max_length=200, blank=True)
    
    # Configuration
    config_schema = models.JSONField('Config Schema', default=dict, blank=True)
    default_config = models.JSONField('Default Config', default=dict, blank=True)
    
    # Documentation
    documentation_url = models.URLField('Documentation URL', blank=True)
    
    class Meta:
        db_table = 'terraform_providers'
        ordering = ['name']
    
    def __str__(self):
        return self.name


# ============================================================================
# VARIABLES D'ENVIRONNEMENT
# ============================================================================

class TerraformVariable(BaseModel):
    """
    Variables Terraform (backend)
    """
    config = models.ForeignKey(
        TerraformConfig, 
        on_delete=models.CASCADE, 
        related_name='stored_variables',
        null=True,
        blank=True
    )
    
    name = models.CharField('Name', max_length=200)
    value = models.JSONField('Value', default=dict)
    description = models.TextField('Description', blank=True)
    
    # Sensible (chiffré)
    is_sensitive = models.BooleanField('Is Sensitive', default=False)
    encrypted_value = models.TextField('Encrypted Value', blank=True)
    
    # Environnement
    environment = models.CharField('Environment', max_length=50, blank=True)
    
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='terraform_variables'
    )
    
    class Meta:
        db_table = 'terraform_variables'
        ordering = ['name']
        unique_together = ['config', 'name', 'environment']
    
    def __str__(self):
        return f"{self.name} ({self.environment})"


# ============================================================================
# CREDENTIALS TERRAFORM
# ============================================================================

class TerraformCredential(BaseModel):
    """
    Credentials pour providers Terraform
    """
    CREDENTIAL_TYPE_CHOICES = [
        ('aws', 'AWS Access Key'),
        ('azure', 'Azure Service Principal'),
        ('gcp', 'GCP Service Account'),
        ('ssh', 'SSH Key'),
        ('token', 'API Token'),
        ('custom', 'Custom'),
    ]
    
    name = models.CharField('Name', max_length=200, unique=True)
    provider = models.CharField('Provider', max_length=20, choices=CREDENTIAL_TYPE_CHOICES)
    description = models.TextField('Description', blank=True)
    
    # Credentials (chiffrés)
    access_key = models.CharField('Access Key', max_length=500, blank=True)
    secret_key = models.CharField('Secret Key', max_length=500, blank=True)
    token = models.CharField('Token', max_length=2000, blank=True)
    
    # AWS
    aws_profile = models.CharField('AWS Profile', max_length=100, blank=True)
    aws_region = models.CharField('AWS Region', max_length=50, blank=True)
    
    # Azure
    azure_subscription_id = models.CharField('Subscription ID', max_length=100, blank=True)
    azure_tenant_id = models.CharField('Tenant ID', max_length=100, blank=True)
    azure_client_id = models.CharField('Client ID', max_length=100, blank=True)
    azure_client_secret = models.CharField('Client Secret', max_length=500, blank=True)
    
    # GCP
    gcp_project = models.CharField('GCP Project', max_length=200, blank=True)
    gcp_service_account = models.TextField('Service Account JSON', blank=True)
    
    # SSH
    ssh_user = models.CharField('SSH User', max_length=100, blank=True)
    ssh_private_key = models.TextField('SSH Private Key', blank=True)
    ssh_key_passphrase = models.CharField('Passphrase', max_length=500, blank=True)
    
    # Associations
    configs = models.ManyToManyField(
        TerraformConfig, 
        related_name='credentials', 
        blank=True
    )
    
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='terraform_credentials'
    )
    
    class Meta:
        db_table = 'terraform_credentials'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_provider_display()})"