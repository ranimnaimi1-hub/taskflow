"""
Jenkins App Models - Professional
Gestion des pipelines Jenkins et des builds
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.core.models import BaseModel
from apps.users.models import User
import json


# ============================================================================
# SERVEURS JENKINS
# ============================================================================

class JenkinsServer(BaseModel):
    """Configuration des serveurs Jenkins"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Maintenance'),
    ]
    
    name = models.CharField('Name', max_length=200, unique=True, db_index=True)
    description = models.TextField('Description', blank=True)
    
    # Connexion
    url = models.URLField('Jenkins URL', help_text="e.g., http://jenkins:8080")
    username = models.CharField('Username', max_length=100)
    password = models.CharField('Password', max_length=500)  # À chiffrer
    
    # Configuration
    timeout = models.IntegerField('Timeout (seconds)', default=30,
                                 validators=[MinValueValidator(5), MaxValueValidator(300)])
    max_concurrent_builds = models.IntegerField('Max Concurrent Builds', default=10)
    
    # Statistiques
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='active')
    version = models.CharField('Jenkins Version', max_length=50, blank=True)
    last_sync_at = models.DateTimeField('Last Sync', null=True, blank=True)
    
    # Propriétaire
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='jenkins_servers'
    )
    
    class Meta:
        db_table = 'jenkins_servers'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.url})"
    
    def get_client(self):
        """Retourne un client Jenkins configuré"""
        from .jenkins_client import JenkinsClient
        return JenkinsClient(
            url=self.url,
            username=self.username,
            password=self.password
        )


# ============================================================================
# JOBS / PIPELINES JENKINS
# ============================================================================

class JenkinsJob(BaseModel):
    """Jobs/Pipelines Jenkins"""
    JOB_TYPE_CHOICES = [
        ('freestyle', 'Freestyle'),
        ('pipeline', 'Pipeline'),
        ('multibranch', 'Multi-branch Pipeline'),
        ('folder', 'Folder'),
        ('workflow', 'Workflow'),
    ]
    
    server = models.ForeignKey(
        JenkinsServer, 
        on_delete=models.CASCADE, 
        related_name='jobs'
    )
    
    # Informations du job
    job_id = models.CharField('Job ID', max_length=200, help_text="Jenkins job name")
    name = models.CharField('Name', max_length=200)
    description = models.TextField('Description', blank=True)
    job_type = models.CharField('Type', max_length=50, choices=JOB_TYPE_CHOICES, default='pipeline')
    
    # Configuration
    url = models.URLField('Job URL', blank=True)
    config_xml = models.TextField('Config XML', blank=True, help_text="Job configuration")
    
    # Paramètres
    parameters = models.JSONField('Parameters', default=list, blank=True,
                                 help_text="Build parameters")
    
    # Métadonnées
    color = models.CharField('Color', max_length=50, blank=True, help_text="Jenkins job color")
    health_report = models.JSONField('Health Report', default=dict, blank=True)
    
    # Statistiques
    last_build_number = models.IntegerField('Last Build Number', default=0)
    last_build_status = models.CharField('Last Build Status', max_length=50, blank=True)
    last_build_at = models.DateTimeField('Last Build At', null=True, blank=True)
    build_count = models.IntegerField('Build Count', default=0)
    
    # Synchronisation
    synced_at = models.DateTimeField('Synced At', null=True, blank=True)
    is_active = models.BooleanField('Active', default=True)
    
    class Meta:
        db_table = 'jenkins_jobs'
        ordering = ['server', 'name']
        unique_together = ['server', 'job_id']
        indexes = [
            models.Index(fields=['server', 'job_id']),
            models.Index(fields=['job_type']),
        ]
    
    def __str__(self):
        return f"{self.server.name} - {self.name}"
    
    @property
    def status_badge(self):
        """Retourne le statut sous forme de badge"""
        if self.color == 'blue':
            return 'success'
        elif self.color == 'red':
            return 'danger'
        elif self.color == 'yellow':
            return 'warning'
        elif self.color == 'grey':
            return 'secondary'
        elif self.color == 'disabled':
            return 'dark'
        return 'info'


# ============================================================================
# BUILDS JENKINS
# ============================================================================

class JenkinsBuild(BaseModel):
    """Builds Jenkins"""
    BUILD_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('aborted', 'Aborted'),
        ('unstable', 'Unstable'),
        ('not_built', 'Not Built'),
    ]
    
    job = models.ForeignKey(
        JenkinsJob, 
        on_delete=models.CASCADE, 
        related_name='builds'
    )
    
    # Informations du build
    build_number = models.IntegerField('Build Number')
    status = models.CharField('Status', max_length=20, choices=BUILD_STATUS_CHOICES, default='pending')
    
    # Timing
    started_at = models.DateTimeField('Started At', null=True, blank=True)
    completed_at = models.DateTimeField('Completed At', null=True, blank=True)
    duration = models.FloatField('Duration (s)', null=True, blank=True)
    estimated_duration = models.FloatField('Estimated Duration (s)', null=True, blank=True)
    
    # Résultats
    result = models.CharField('Result', max_length=50, blank=True)
    url = models.URLField('Build URL', blank=True)
    console_output = models.TextField('Console Output', blank=True)
    
    # Paramètres et causes
    parameters = models.JSONField('Parameters', default=dict, blank=True)
    causes = models.JSONField('Causes', default=list, blank=True)
    
    # Métadonnées
    built_by = models.CharField('Built By', max_length=200, blank=True)
    triggered_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='triggered_builds'
    )
    
    # Tests
    test_results = models.JSONField('Test Results', default=dict, blank=True)
    artifacts = models.JSONField('Artifacts', default=list, blank=True)
    
    # Métriques
    metrics = models.JSONField('Metrics', default=dict, blank=True)
    
    class Meta:
        db_table = 'jenkins_builds'
        ordering = ['-build_number']
        unique_together = ['job', 'build_number']
        indexes = [
            models.Index(fields=['job', '-build_number']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.job.name} #{self.build_number} - {self.status}"
    
    def save(self, *args, **kwargs):
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.duration = delta.total_seconds()
        super().save(*args, **kwargs)
    
    @property
    def status_badge(self):
        """Retourne le statut sous forme de badge"""
        colors = {
            'pending': 'warning',
            'running': 'info',
            'completed': 'success',
            'failed': 'danger',
            'aborted': 'secondary',
            'unstable': 'warning',
            'not_built': 'dark',
        }
        return colors.get(self.status, 'secondary')


# ============================================================================
# NŒUDS JENKINS (AGENTS)
# ============================================================================

class JenkinsNode(BaseModel):
    """Nœuds/Agents Jenkins"""
    NODE_TYPE_CHOICES = [
        ('master', 'Master'),
        ('agent', 'Agent'),
        ('cloud', 'Cloud'),
    ]
    
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('disconnected', 'Disconnected'),
    ]
    
    server = models.ForeignKey(
        JenkinsServer, 
        on_delete=models.CASCADE, 
        related_name='nodes'
    )
    
    # Informations du nœud
    node_id = models.CharField('Node ID', max_length=200)
    name = models.CharField('Name', max_length=200)
    node_type = models.CharField('Type', max_length=20, choices=NODE_TYPE_CHOICES, default='agent')
    
    # Configuration
    url = models.URLField('Node URL', blank=True)
    description = models.TextField('Description', blank=True)
    
    # Statut
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='offline')
    offline_reason = models.TextField('Offline Reason', blank=True)
    
    # Capacités
    num_executors = models.IntegerField('Number of Executors', default=2)
    total_memory = models.FloatField('Total Memory (GB)', null=True, blank=True)
    free_memory = models.FloatField('Free Memory (GB)', null=True, blank=True)
    total_disk = models.FloatField('Total Disk (GB)', null=True, blank=True)
    free_disk = models.FloatField('Free Disk (GB)', null=True, blank=True)
    cpu_cores = models.IntegerField('CPU Cores', null=True, blank=True)
    load_average = models.FloatField('Load Average', null=True, blank=True)
    
    # Labels
    labels = models.JSONField('Labels', default=list, blank=True)
    
    # Synchronisation
    synced_at = models.DateTimeField('Synced At', null=True, blank=True)
    
    class Meta:
        db_table = 'jenkins_nodes'
        ordering = ['server', 'name']
        unique_together = ['server', 'node_id']
    
    def __str__(self):
        return f"{self.server.name} - {self.name}"


# ============================================================================
# PLUGINS JENKINS
# ============================================================================

class JenkinsPlugin(BaseModel):
    """Plugins Jenkins"""
    server = models.ForeignKey(
        JenkinsServer, 
        on_delete=models.CASCADE, 
        related_name='plugins'
    )
    
    # Informations du plugin
    plugin_id = models.CharField('Plugin ID', max_length=200)
    name = models.CharField('Name', max_length=200)
    version = models.CharField('Version', max_length=50)
    
    # Métadonnées
    title = models.CharField('Title', max_length=200, blank=True)
    description = models.TextField('Description', blank=True)
    url = models.URLField('Plugin URL', blank=True)
    
    # Statut
    enabled = models.BooleanField('Enabled', default=True)
    has_update = models.BooleanField('Has Update', default=False)
    compatible_version = models.CharField('Compatible Version', max_length=50, blank=True)
    
    # Dépendances
    dependencies = models.JSONField('Dependencies', default=list, blank=True)
    
    # Synchronisation
    installed_at = models.DateTimeField('Installed At', null=True, blank=True)
    updated_at = models.DateTimeField('Updated At', null=True, blank=True)
    
    class Meta:
        db_table = 'jenkins_plugins'
        ordering = ['name']
        unique_together = ['server', 'plugin_id']
    
    def __str__(self):
        return f"{self.name} v{self.version}"


# ============================================================================
# CREDENTIALS JENKINS
# ============================================================================

class JenkinsCredential(BaseModel):
    """Credentials Jenkins"""
    CREDENTIAL_TYPE_CHOICES = [
        ('username_password', 'Username/Password'),
        ('ssh_key', 'SSH Key'),
        ('secret_text', 'Secret Text'),
        ('secret_file', 'Secret File'),
        ('certificate', 'Certificate'),
    ]
    
    server = models.ForeignKey(
        JenkinsServer, 
        on_delete=models.CASCADE, 
        related_name='credentials'
    )
    
    # Informations du credential
    credential_id = models.CharField('Credential ID', max_length=200)
    name = models.CharField('Name', max_length=200)
    credential_type = models.CharField('Type', max_length=50, choices=CREDENTIAL_TYPE_CHOICES)
    description = models.TextField('Description', blank=True)
    
    # Valeurs (chiffrées)
    username = models.CharField('Username', max_length=200, blank=True)
    password = models.CharField('Password', max_length=500, blank=True)
    private_key = models.TextField('Private Key', blank=True)
    passphrase = models.CharField('Passphrase', max_length=500, blank=True)
    secret = models.CharField('Secret', max_length=2000, blank=True)
    
    # Métadonnées
    scope = models.CharField('Scope', max_length=50, default='global',
                            choices=[('global', 'Global'), ('system', 'System')])
    
    # Synchronisation
    synced_at = models.DateTimeField('Synced At', null=True, blank=True)
    
    class Meta:
        db_table = 'jenkins_credentials'
        ordering = ['name']
        unique_together = ['server', 'credential_id']
    
    def __str__(self):
        return f"{self.name} ({self.get_credential_type_display()})"


# ============================================================================
# VUES JENKINS
# ============================================================================

class JenkinsView(BaseModel):
    """Vues Jenkins"""
    server = models.ForeignKey(
        JenkinsServer, 
        on_delete=models.CASCADE, 
        related_name='views'
    )
    
    # Informations de la vue
    view_id = models.CharField('View ID', max_length=200)
    name = models.CharField('Name', max_length=200)
    description = models.TextField('Description', blank=True)
    url = models.URLField('View URL', blank=True)
    
    # Configuration
    view_type = models.CharField('Type', max_length=50, blank=True)
    jobs = models.JSONField('Jobs', default=list, blank=True, help_text="List of job names in this view")
    
    class Meta:
        db_table = 'jenkins_views'
        ordering = ['server', 'name']
        unique_together = ['server', 'view_id']
    
    def __str__(self):
        return f"{self.server.name} - {self.name}"


# ============================================================================
# PIPELINES (POUR LE DASHBOARD)
# ============================================================================

class JenkinsPipeline(BaseModel):
    """Pipelines pour le dashboard"""
    name = models.CharField('Name', max_length=200, unique=True)
    description = models.TextField('Description', blank=True)
    
    # Jobs associés
    jobs = models.ManyToManyField(
        JenkinsJob, 
        related_name='pipelines',
        blank=True
    )
    
    # Configuration
    parameters = models.JSONField('Parameters', default=dict, blank=True)
    environment = models.JSONField('Environment', default=dict, blank=True)
    
    # Pipeline as Code
    pipeline_script = models.TextField('Pipeline Script', blank=True,
                                      help_text="Jenkinsfile content")
    
    # Propriétaire
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='jenkins_pipelines'
    )
    
    class Meta:
        db_table = 'jenkins_pipelines'
        ordering = ['name']
    
    def __str__(self):
        return self.name
