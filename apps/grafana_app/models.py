"""
Grafana App Models - Professional
Gestion des dashboards, datasources et alertes Grafana
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.core.models import BaseModel
from apps.users.models import User
import json


# ============================================================================
# SERVEURS GRAFANA
# ============================================================================

class GrafanaServer(BaseModel):
    """Configuration des serveurs Grafana"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Maintenance'),
    ]
    
    name = models.CharField('Name', max_length=200, unique=True, db_index=True)
    description = models.TextField('Description', blank=True)
    
    # Connexion
    url = models.URLField('Grafana URL', help_text="e.g., http://grafana:3000")
    api_key = models.CharField('API Key', max_length=500, blank=True)
    username = models.CharField('Username', max_length=100, blank=True)
    password = models.CharField('Password', max_length=500, blank=True)
    
    # Configuration
    timeout = models.IntegerField('Timeout (seconds)', default=30,
                                 validators=[MinValueValidator(5), MaxValueValidator(300)])
    
    # Statistiques
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='active')
    version = models.CharField('Grafana Version', max_length=50, blank=True)
    last_sync_at = models.DateTimeField('Last Sync', null=True, blank=True)
    
    # Propriétaire
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='grafana_servers'
    )
    
    class Meta:
        db_table = 'grafana_servers'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.url})"
    
    def get_client(self):
        """Retourne un client Grafana configuré"""
        from .grafana_client import GrafanaClient
        return GrafanaClient(
            url=self.url,
            api_key=self.api_key
        )


# ============================================================================
# DASHBOARDS GRAFANA
# ============================================================================

class GrafanaDashboard(BaseModel):
    """Dashboards Grafana"""
    
    server = models.ForeignKey(
        GrafanaServer, 
        on_delete=models.CASCADE, 
        related_name='dashboards'
    )
    
    # Informations du dashboard
    dashboard_uid = models.CharField('Dashboard UID', max_length=200, db_index=True)
    title = models.CharField('Title', max_length=200)
    description = models.TextField('Description', blank=True)
    
    # Configuration
    dashboard_json = models.JSONField('Dashboard JSON', default=dict, blank=True)
    version = models.IntegerField('Version', default=1)
    
    # Métadonnées
    url = models.URLField('Dashboard URL', blank=True)
    slug = models.CharField('Slug', max_length=200, blank=True)
    
    # Tags
    tags = models.JSONField('Tags', default=list, blank=True)
    
    # Synchronisation
    synced_at = models.DateTimeField('Synced At', null=True, blank=True)
    is_active = models.BooleanField('Active', default=True)
    
    # Propriétaire
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='grafana_dashboards'
    )
    
    class Meta:
        db_table = 'grafana_dashboards'
        ordering = ['server', 'title']
        unique_together = ['server', 'dashboard_uid']
        indexes = [
            models.Index(fields=['server', 'dashboard_uid']),
        ]
    
    def __str__(self):
        return f"{self.server.name} - {self.title}"
    
    @property
    def folder_title(self):
        """Titre du dossier parent"""
        if self.dashboard_json:
            return self.dashboard_json.get('meta', {}).get('folderTitle', 'General')
        return 'General'


# ============================================================================
# DATASOURCES GRAFANA
# ============================================================================

class GrafanaDatasource(BaseModel):
    """Sources de données Grafana"""
    DATASOURCE_TYPE_CHOICES = [
        ('prometheus', 'Prometheus'),
        ('graphite', 'Graphite'),
        ('influxdb', 'InfluxDB'),
        ('elasticsearch', 'Elasticsearch'),
        ('mysql', 'MySQL'),
        ('postgresql', 'PostgreSQL'),
        ('cloudwatch', 'CloudWatch'),
        ('azure', 'Azure Monitor'),
        ('stackdriver', 'Google Stackdriver'),
        ('loki', 'Loki'),
        ('tempo', 'Tempo'),
        ('jaeger', 'Jaeger'),
        ('other', 'Other'),
    ]
    
    server = models.ForeignKey(
        GrafanaServer, 
        on_delete=models.CASCADE, 
        related_name='datasources'
    )
    
    # Informations de la datasource
    datasource_uid = models.CharField('Datasource UID', max_length=200, db_index=True)
    name = models.CharField('Name', max_length=200)
    type = models.CharField('Type', max_length=50, choices=DATASOURCE_TYPE_CHOICES)
    
    # Configuration
    url = models.URLField('URL', blank=True)
    access = models.CharField('Access', max_length=50, default='proxy',
                             choices=[('direct', 'Direct'), ('proxy', 'Proxy')])
    is_default = models.BooleanField('Is Default', default=False)
    
    # Authentification
    basic_auth = models.BooleanField('Basic Auth', default=False)
    basic_auth_user = models.CharField('Basic Auth User', max_length=200, blank=True)
    basic_auth_password = models.CharField('Basic Auth Password', max_length=500, blank=True)
    
    with_credentials = models.BooleanField('With Credentials', default=False)
    
    # Configuration JSON
    json_data = models.JSONField('JSON Data', default=dict, blank=True)
    secure_json_data = models.JSONField('Secure JSON Data', default=dict, blank=True)
    
    # Métadonnées
    version = models.IntegerField('Version', default=1)
    read_only = models.BooleanField('Read Only', default=False)
    
    # Synchronisation
    synced_at = models.DateTimeField('Synced At', null=True, blank=True)
    is_active = models.BooleanField('Active', default=True)
    
    class Meta:
        db_table = 'grafana_datasources'
        ordering = ['server', 'name']
        unique_together = ['server', 'datasource_uid']
        indexes = [
            models.Index(fields=['server', 'type']),
        ]
    
    def __str__(self):
        return f"{self.server.name} - {self.name} ({self.get_type_display()})"


# ============================================================================
# ALERTES GRAFANA
# ============================================================================

class GrafanaAlert(BaseModel):
    """Alertes Grafana"""
    ALERT_STATE_CHOICES = [
        ('pending', 'Pending'),
        ('firing', 'Firing'),
        ('resolved', 'Resolved'),
        ('paused', 'Paused'),
        ('unknown', 'Unknown'),
    ]
    
    SEVERITY_CHOICES = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('info', 'Info'),
    ]
    
    server = models.ForeignKey(
        GrafanaServer, 
        on_delete=models.CASCADE, 
        related_name='alerts'
    )
    dashboard = models.ForeignKey(
        GrafanaDashboard, 
        on_delete=models.CASCADE, 
        related_name='alerts',
        null=True,
        blank=True
    )
    datasource = models.ForeignKey(
        GrafanaDatasource, 
        on_delete=models.CASCADE, 
        related_name='alerts',
        null=True,
        blank=True
    )
    
    # Informations de l'alerte
    alert_id = models.IntegerField('Alert ID', db_index=True)
    name = models.CharField('Name', max_length=200)
    message = models.TextField('Message', blank=True)
    
    # État
    state = models.CharField('State', max_length=20, choices=ALERT_STATE_CHOICES, default='pending')
    severity = models.CharField('Severity', max_length=20, choices=SEVERITY_CHOICES, default='medium')
    
    # Timing
    created = models.DateTimeField('Created', null=True, blank=True)
    updated = models.DateTimeField('Updated', null=True, blank=True)
    new_state_date = models.DateTimeField('New State Date', null=True, blank=True)
    
    # Valeurs
    eval_data = models.JSONField('Evaluation Data', default=dict, blank=True)
    execution_error = models.TextField('Execution Error', blank=True)
    
    # URL
    url = models.URLField('Alert URL', blank=True)
    
    # Synchronisation
    synced_at = models.DateTimeField('Synced At', null=True, blank=True)
    
    class Meta:
        db_table = 'grafana_alerts'
        ordering = ['-new_state_date']
        unique_together = ['server', 'alert_id']
        indexes = [
            models.Index(fields=['server', 'state']),
            models.Index(fields=['severity']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_state_display()}"


# ============================================================================
# ORGANISATIONS GRAFANA
# ============================================================================

class GrafanaOrganization(BaseModel):
    """Organisations Grafana"""
    server = models.ForeignKey(
        GrafanaServer, 
        on_delete=models.CASCADE, 
        related_name='organizations'
    )
    
    org_id = models.IntegerField('Organization ID')
    name = models.CharField('Name', max_length=200)
    
    # Métadonnées
    address = models.JSONField('Address', default=dict, blank=True)
    
    # Synchronisation
    synced_at = models.DateTimeField('Synced At', null=True, blank=True)
    
    class Meta:
        db_table = 'grafana_organizations'
        ordering = ['server', 'name']
        unique_together = ['server', 'org_id']
    
    def __str__(self):
        return f"{self.server.name} - {self.name}"


# ============================================================================
# UTILISATEURS GRAFANA
# ============================================================================

class GrafanaUser(BaseModel):
    """Utilisateurs Grafana"""
    server = models.ForeignKey(
        GrafanaServer, 
        on_delete=models.CASCADE, 
        related_name='users'
    )
    organization = models.ForeignKey(
        GrafanaOrganization, 
        on_delete=models.CASCADE, 
        related_name='users',
        null=True,
        blank=True
    )
    
    user_id = models.IntegerField('User ID')
    email = models.EmailField('Email')
    name = models.CharField('Name', max_length=200, blank=True)
    login = models.CharField('Login', max_length=200)
    
    # Rôle
    role = models.CharField('Role', max_length=50, default='Viewer',
                           choices=[('Admin', 'Admin'), ('Editor', 'Editor'), ('Viewer', 'Viewer')])
    
    # Statut
    is_disabled = models.BooleanField('Disabled', default=False)
    is_active = models.BooleanField('Active', default=True)
    
    # Métadonnées
    avatar_url = models.URLField('Avatar URL', blank=True)
    last_seen_at = models.DateTimeField('Last Seen', null=True, blank=True)
    
    # Synchronisation
    synced_at = models.DateTimeField('Synced At', null=True, blank=True)
    
    class Meta:
        db_table = 'grafana_users'
        ordering = ['server', 'email']
        unique_together = ['server', 'user_id']
        indexes = [
            models.Index(fields=['server', 'email']),
        ]
    
    def __str__(self):
        return f"{self.email} ({self.role})"


# ============================================================================
# FOLDERS GRAFANA
# ============================================================================

class GrafanaFolder(BaseModel):
    """Dossiers Grafana"""
    server = models.ForeignKey(
        GrafanaServer, 
        on_delete=models.CASCADE, 
        related_name='folders'
    )
    
    folder_uid = models.CharField('Folder UID', max_length=200)
    title = models.CharField('Title', max_length=200)
    
    # Métadonnées
    url = models.URLField('Folder URL', blank=True)
    version = models.IntegerField('Version', default=1)
    
    # Synchronisation
    synced_at = models.DateTimeField('Synced At', null=True, blank=True)
    
    class Meta:
        db_table = 'grafana_folders'
        ordering = ['server', 'title']
        unique_together = ['server', 'folder_uid']
    
    def __str__(self):
        return f"{self.server.name} - {self.title}"


# ============================================================================
# PANELS GRAFANA
# ============================================================================

class GrafanaPanel(BaseModel):
    """Panels dans les dashboards"""
    dashboard = models.ForeignKey(
        GrafanaDashboard, 
        on_delete=models.CASCADE, 
        related_name='panels'
    )
    
    panel_id = models.IntegerField('Panel ID')
    title = models.CharField('Title', max_length=200, blank=True)
    type = models.CharField('Type', max_length=100, blank=True)
    
    # Configuration
    panel_json = models.JSONField('Panel JSON', default=dict, blank=True)
    grid_pos = models.JSONField('Grid Position', default=dict, blank=True)
    targets = models.JSONField('Targets', default=list, blank=True)
    
    # Métadonnées
    description = models.TextField('Description', blank=True)
    
    class Meta:
        db_table = 'grafana_panels'
        ordering = ['dashboard', 'panel_id']
        unique_together = ['dashboard', 'panel_id']
    
    def __str__(self):
        return f"{self.dashboard.title} - {self.title or f'Panel {self.panel_id}'}"


# ============================================================================
# SNAPSHOTS GRAFANA
# ============================================================================

class GrafanaSnapshot(BaseModel):
    """Snapshots de dashboards"""
    server = models.ForeignKey(
        GrafanaServer, 
        on_delete=models.CASCADE, 
        related_name='snapshots'
    )
    dashboard = models.ForeignKey(
        GrafanaDashboard, 
        on_delete=models.CASCADE, 
        related_name='snapshots',
        null=True,
        blank=True
    )
    
    snapshot_key = models.CharField('Snapshot Key', max_length=200, unique=True)
    snapshot_url = models.URLField('Snapshot URL')
    snapshot_json = models.JSONField('Snapshot JSON', default=dict, blank=True)
    
    # Métadonnées
    name = models.CharField('Name', max_length=200, blank=True)
    expires_at = models.DateTimeField('Expires At', null=True, blank=True)
    created_by = models.CharField('Created By', max_length=200, blank=True)
    
    class Meta:
        db_table = 'grafana_snapshots'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name or self.snapshot_key


# ============================================================================
# TEAMS GRAFANA
# ============================================================================

class GrafanaTeam(BaseModel):
    """Teams Grafana"""
    server = models.ForeignKey(
        GrafanaServer, 
        on_delete=models.CASCADE, 
        related_name='teams'
    )
    organization = models.ForeignKey(
        GrafanaOrganization, 
        on_delete=models.CASCADE, 
        related_name='teams',
        null=True,
        blank=True
    )
    
    team_id = models.IntegerField('Team ID')
    name = models.CharField('Name', max_length=200)
    email = models.EmailField('Email', blank=True)
    
    # Métadonnées
    member_count = models.IntegerField('Member Count', default=0)
    permission = models.IntegerField('Permission', default=0)
    
    # Synchronisation
    synced_at = models.DateTimeField('Synced At', null=True, blank=True)
    
    class Meta:
        db_table = 'grafana_teams'
        ordering = ['server', 'name']
        unique_together = ['server', 'team_id']
    
    def __str__(self):
        return f"{self.server.name} - {self.name}"
