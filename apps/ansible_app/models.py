# apps/ansible_app/models.py
"""
Ansible App Models - Ultra Professional
Gestion des playbooks, inventaires et exécutions Ansible
Avec intégration complète à l'application inventory
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.core.models import BaseModel
from apps.users.models import User
from apps.inventory.models import Device, Site, Tenant, Cluster, VirtualMachine
import yaml


# ============================================================================
# INVENTAIRES ANSIBLE
# ============================================================================

class AnsibleInventory(BaseModel):
    """
    Inventaire Ansible - Gestion des hôtes et groupes
    Peut être statique (fichier) ou dynamique (basé sur inventory)
    """
    INVENTORY_TYPE_CHOICES = [
        ('static', 'Static - Fichier manuel'),
        ('dynamic', 'Dynamic - Basé sur inventory'),
        ('file', 'File Based - Fichier externe'),
        ('script', 'Script - Script externe'),
    ]
    
    FORMAT_CHOICES = [
        ('ini', 'INI Format'),
        ('yaml', 'YAML Format'),
        ('json', 'JSON Format'),
    ]
    
    name = models.CharField('Name', max_length=200, unique=True, db_index=True)
    description = models.TextField('Description', blank=True)
    inventory_type = models.CharField('Type', max_length=20, choices=INVENTORY_TYPE_CHOICES, default='static')
    format = models.CharField('Format', max_length=10, choices=FORMAT_CHOICES, default='ini')
    
    # Contenu pour inventaire statique
    content = models.TextField('Content', blank=True, help_text="Inventory content in INI/YAML/JSON format")
    variables = models.JSONField('Variables', default=dict, blank=True, help_text="Global variables")
    
    # Sources dynamiques
    source_script = models.CharField('Source Script', max_length=500, blank=True, 
                                    help_text="Path to dynamic inventory script")
    source_url = models.URLField('Source URL', blank=True, help_text="URL for dynamic inventory")
    
    # ========================================================================
    # ASSOCIATIONS AVEC INVENTORY
    # ========================================================================
    
    # Relations avec les modèles inventory
    devices = models.ManyToManyField(
        Device, 
        related_name='ansible_inventories', 
        blank=True,
        help_text="Devices à inclure dans l'inventaire"
    )
    
    sites = models.ManyToManyField(
        Site, 
        related_name='ansible_inventories', 
        blank=True,
        help_text="Sites à inclure dans l'inventaire (tous les devices du site)"
    )
    
    clusters = models.ManyToManyField(
        Cluster, 
        related_name='ansible_inventories', 
        blank=True,
        help_text="Clusters à inclure dans l'inventaire"
    )
    
    tenants = models.ManyToManyField(
        Tenant, 
        related_name='ansible_inventories', 
        blank=True,
        help_text="Tenants à inclure dans l'inventaire"
    )
    
    # Filtres avancés
    device_filters = models.JSONField(
        'Device Filters', 
        default=dict, 
        blank=True,
        help_text="Filtres JSON pour sélectionner dynamiquement les devices"
    )
    
    # Métadonnées
    vars_file = models.FileField('Variables File', upload_to='ansible/vars/', null=True, blank=True)
    is_active = models.BooleanField('Active', default=True)
    
    # Propriétaire
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='ansible_inventories'
    )
    
    class Meta:
        db_table = 'ansible_inventories'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['inventory_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_inventory_type_display()})"
    
    def clean(self):
        """Validation du contenu"""
        if self.inventory_type == 'static' and not self.content and not self.devices.exists():
            raise ValidationError('Static inventory requires either content or associated devices')
        
        if self.inventory_type == 'dynamic' and not (self.source_script or self.source_url) and not self.device_filters:
            raise ValidationError('Dynamic inventory requires source script/URL or device filters')
    
    def generate_inventory_content(self):
        """
        Génère le contenu de l'inventaire basé sur les associations
        """
        if self.inventory_type == 'static' and self.content:
            return self.content
        
        # Construction dynamique à partir des devices
        lines = []
        
        # Variables globales
        if self.variables:
            lines.append("[all:vars]")
            for key, value in self.variables.items():
                lines.append(f"{key}={value}")
            lines.append("")
        
        # Récupérer tous les devices concernés
        devices = self._get_devices()
        
        if not devices:
            return ""
        
        # Grouper par site
        sites = devices.values_list('site__name', flat=True).distinct()
        
        for site_name in sites:
            if site_name:
                group_name = site_name.lower().replace(' ', '_')
                lines.append(f"[{group_name}]")
                
                site_devices = devices.filter(site__name=site_name)
                for device in site_devices:
                    # Format: hostname ansible_host=ip ansible_user=user
                    vars_list = [f"ansible_host={device.management_ip}"]
                    if device.username:
                        vars_list.append(f"ansible_user={device.username}")
                    if device.ssh_port != 22:
                        vars_list.append(f"ansible_port={device.ssh_port}")
                    
                    line = f"{device.hostname} {' '.join(vars_list)}"
                    lines.append(line)
                lines.append("")
        
        # Grouper par type
        lines.append("[network_devices]")
        network_devices = devices.filter(device_type__device_class__in=['router', 'switch', 'firewall'])
        for device in network_devices:
            lines.append(device.hostname)
        lines.append("")
        
        lines.append("[servers]")
        servers = devices.filter(device_type__device_class='server')
        for device in servers:
            lines.append(device.hostname)
        lines.append("")
        
        return "\n".join(lines)
    
    def _get_devices(self):
        """Récupère tous les devices selon les associations"""
        devices = Device.objects.none()
        
        # Devices directs
        if self.devices.exists():
            devices = devices.union(self.devices.all())
        
        # Devices par site
        if self.sites.exists():
            site_devices = Device.objects.filter(site__in=self.sites.all())
            devices = devices.union(site_devices)
        
        # Devices par cluster
        if self.clusters.exists():
            cluster_devices = Device.objects.filter(clusters__in=self.clusters.all())
            devices = devices.union(cluster_devices)
        
        # Devices par tenant
        if self.tenants.exists():
            tenant_devices = Device.objects.filter(tenant__in=self.tenants.all())
            devices = devices.union(tenant_devices)
        
        # Appliquer les filtres
        if self.device_filters:
            try:
                devices = devices.filter(**self.device_filters)
            except:
                pass
        
        return devices.distinct()
    
    def get_hosts_count(self):
        """Nombre d'hôtes dans l'inventaire"""
        if self.inventory_type == 'static' and self.content:
            # Parser simple pour compter les hôtes
            lines = self.content.split('\n')
            count = 0
            for line in lines:
                line = line.strip()
                if line and not line.startswith('[') and not line.startswith(';') and not line.startswith('#'):
                    if 'ansible_host' in line or (not '=' in line and not line.startswith('[')):
                        count += 1
            return count
        return self._get_devices().count()
    
    def sync_from_inventory(self):
        """Synchronise l'inventaire avec les devices associés"""
        if self.inventory_type != 'static':
            self.content = self.generate_inventory_content()
            self.save(update_fields=['content'])


# ============================================================================
# PLAYBOOKS ANSIBLE
# ============================================================================

class Playbook(BaseModel):
    """Playbook Ansible - Automatisation des tâches"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('deprecated', 'Deprecated'),
    ]
    
    VISIBILITY_CHOICES = [
        ('private', 'Private - Only me'),
        ('team', 'Team - My team'),
        ('shared', 'Shared - Specific users'),
        ('public', 'Public - Everyone'),
    ]
    
    name = models.CharField('Name', max_length=200, unique=True, db_index=True)
    description = models.TextField('Description', blank=True)
    
    # Contenu
    content = models.TextField('Content', help_text="YAML playbook content")
    requirements = models.JSONField('Requirements', default=list, blank=True, 
                                   help_text="Required collections/roles")
    
    # Fichiers
    playbook_file = models.FileField('Playbook File', upload_to='ansible/playbooks/', null=True, blank=True)
    vars_file = models.FileField('Variables File', upload_to='ansible/vars/', null=True, blank=True)
    
    # ========================================================================
    # ASSOCIATIONS
    # ========================================================================
    
    inventory = models.ForeignKey(
        AnsibleInventory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='playbooks'
    )
    
    default_inventory = models.ForeignKey(
        AnsibleInventory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='default_for_playbooks',
        help_text="Default inventory to use if none specified"
    )
    
    # Configuration
    timeout = models.IntegerField('Timeout (seconds)', default=3600, 
                                 validators=[MinValueValidator(60), MaxValueValidator(86400)])
    forks = models.IntegerField('Forks', default=5, 
                               validators=[MinValueValidator(1), MaxValueValidator(100)])
    
    # ⚠️ REMPLACÉ ArrayField par JSONField
    tags = models.JSONField('Tags', default=list, blank=True)
    
    # Statut
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='draft')
    visibility = models.CharField('Visibility', max_length=20, choices=VISIBILITY_CHOICES, default='private')
    version = models.CharField('Version', max_length=50, default='1.0.0')
    
    # Statistiques
    execution_count = models.IntegerField('Execution Count', default=0)
    success_count = models.IntegerField('Success Count', default=0)
    failure_count = models.IntegerField('Failure Count', default=0)
    avg_duration = models.FloatField('Average Duration (s)', null=True, blank=True)
    
    # Propriétaire
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_playbooks'
    )
    
    # Utilisateurs autorisés (pour visibility='shared')
    allowed_users = models.ManyToManyField(
        User, 
        related_name='shared_playbooks', 
        blank=True,
        help_text="Users allowed to access this playbook when visibility is 'shared'"
    )
    
    class Meta:
        db_table = 'ansible_playbooks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['status']),
            models.Index(fields=['visibility']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"{self.name} v{self.version}"
    
    @property
    def success_rate(self):
        """Taux de succès du playbook"""
        if self.execution_count == 0:
            return 0
        return round((self.success_count / self.execution_count) * 100, 2)
    
    @property
    def last_execution(self):
        """Dernière exécution"""
        return self.executions.order_by('-created_at').first()
    
    def update_stats(self, success, duration):
        """Met à jour les statistiques après exécution"""
        self.execution_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        
        # Mise à jour de la durée moyenne
        if self.avg_duration:
            self.avg_duration = (self.avg_duration * (self.execution_count - 1) + duration) / self.execution_count
        else:
            self.avg_duration = duration
        
        self.save(update_fields=['execution_count', 'success_count', 'failure_count', 'avg_duration'])
    
    def validate_yaml(self):
        """Valide la syntaxe YAML du playbook"""
        try:
            yaml.safe_load(self.content)
            return True, "Valid YAML"
        except yaml.YAMLError as e:
            return False, str(e)


# ============================================================================
# EXÉCUTIONS DE PLAYBOOKS
# ============================================================================

class PlaybookExecution(BaseModel):
    """Exécution de playbook - Historique et résultats"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('timeout', 'Timeout'),
    ]
    
    playbook = models.ForeignKey(Playbook, on_delete=models.CASCADE, related_name='executions')
    inventory = models.ForeignKey(
        AnsibleInventory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='executions'
    )
    
    # ========================================================================
    # INVENTORY SNAPSHOT (pour traçabilité)
    # ========================================================================
    inventory_snapshot = models.JSONField(
        'Inventory Snapshot', 
        default=dict, 
        blank=True,
        help_text="Snapshot of inventory at execution time"
    )
    
    # Configuration d'exécution
    extra_vars = models.JSONField('Extra Variables', default=dict, blank=True)
    limit = models.CharField('Limit', max_length=500, blank=True, help_text="Host pattern limit")
    
    # ⚠️ REMPLACÉ ArrayField par JSONField
    tags = models.JSONField('Tags', default=list, blank=True)
    skip_tags = models.JSONField('Skip Tags', default=list, blank=True)
    
    check_mode = models.BooleanField('Check Mode', default=False, help_text="Dry run")
    diff_mode = models.BooleanField('Diff Mode', default=False)
    
    # Statut
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Résultats
    output = models.TextField('Output', blank=True)
    error_output = models.TextField('Error Output', blank=True)
    summary = models.JSONField('Summary', default=dict, blank=True)
    facts = models.JSONField('Facts', default=dict, blank=True)
    
    # Métriques
    started_at = models.DateTimeField('Started At', null=True, blank=True)
    completed_at = models.DateTimeField('Completed At', null=True, blank=True)
    duration = models.FloatField('Duration (s)', null=True, blank=True)
    
    # Exécuteur
    executed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='playbook_executions'
    )
    execution_host = models.CharField('Execution Host', max_length=255, blank=True)
    
    # Métadonnées
    command = models.TextField('Command', blank=True)
    return_code = models.IntegerField('Return Code', null=True, blank=True)
    
    # ========================================================================
    # RÉSULTATS PAR HÔTE
    # ========================================================================
    host_results = models.JSONField('Host Results', default=dict, blank=True)
    
    class Meta:
        db_table = 'ansible_playbook_executions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['playbook', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['executed_by']),
        ]
    
    def __str__(self):
        return f"{self.playbook.name} - {self.status} - {self.created_at}"
    
    def save(self, *args, **kwargs):
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.duration = delta.total_seconds()
        super().save(*args, **kwargs)
    
    def take_inventory_snapshot(self):
        """Prend un snapshot de l'inventaire utilisé"""
        if self.inventory:
            self.inventory_snapshot = {
                'id': str(self.inventory.id),
                'name': self.inventory.name,
                'type': self.inventory.inventory_type,
                'hosts_count': self.inventory.get_hosts_count(),
                'content': self.inventory.generate_inventory_content(),
                'variables': self.inventory.variables,
            }
            self.save(update_fields=['inventory_snapshot'])


# ============================================================================
# PLANIFICATIONS DE PLAYBOOKS
# ============================================================================

class PlaybookSchedule(BaseModel):
    """Planification d'exécution de playbook"""
    SCHEDULE_TYPE_CHOICES = [
        ('once', 'Once'),
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('cron', 'Cron Expression'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    name = models.CharField('Name', max_length=200)
    playbook = models.ForeignKey(Playbook, on_delete=models.CASCADE, related_name='schedules')
    inventory = models.ForeignKey(
        AnsibleInventory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='schedules'
    )
    
    # Configuration de planification
    schedule_type = models.CharField('Type', max_length=20, choices=SCHEDULE_TYPE_CHOICES)
    cron_expression = models.CharField('Cron Expression', max_length=100, blank=True)
    
    # Timing
    start_date = models.DateTimeField('Start Date')
    end_date = models.DateTimeField('End Date', null=True, blank=True)
    last_run = models.DateTimeField('Last Run', null=True, blank=True)
    next_run = models.DateTimeField('Next Run', null=True, blank=True)
    
    # Configuration d'exécution
    extra_vars = models.JSONField('Extra Variables', default=dict, blank=True)
    limit = models.CharField('Limit', max_length=500, blank=True)
    
    # ⚠️ REMPLACÉ ArrayField par JSONField
    tags = models.JSONField('Tags', default=list, blank=True)
    
    check_mode = models.BooleanField('Check Mode', default=False)
    
    # Statut
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Notifications
    notify_on_success = models.BooleanField('Notify on Success', default=False)
    notify_on_failure = models.BooleanField('Notify on Failure', default=True)
    
    # ⚠️ REMPLACÉ ArrayField par JSONField
    notification_emails = models.JSONField('Notification Emails', default=list, blank=True)
    
    # Métadonnées
    execution_count = models.IntegerField('Execution Count', default=0)
    last_execution = models.ForeignKey(
        PlaybookExecution, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='+'
    )
    
    # Propriétaire
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='playbook_schedules'
    )
    
    class Meta:
        db_table = 'ansible_playbook_schedules'
        ordering = ['next_run']
        indexes = [
            models.Index(fields=['status', 'next_run']),
            models.Index(fields=['playbook']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_schedule_type_display()}"
    
    def clean(self):
        """Validation personnalisée"""
        if self.schedule_type == 'cron' and not self.cron_expression:
            raise ValidationError({'cron_expression': 'Cron expression required'})
        
        if self.end_date and self.end_date <= self.start_date:
            raise ValidationError({'end_date': 'End date must be after start date'})
    
    def calculate_next_run(self):
        """Calcule la prochaine date d'exécution"""
        from dateutil.relativedelta import relativedelta
        from croniter import croniter
        import datetime
        
        now = timezone.now()
        base = self.last_run or self.start_date
        
        if base < now:
            base = now
        
        if self.schedule_type == 'once':
            return self.start_date if self.start_date > now else None
            
        elif self.schedule_type == 'hourly':
            return base + relativedelta(hours=1)
            
        elif self.schedule_type == 'daily':
            return base + relativedelta(days=1)
            
        elif self.schedule_type == 'weekly':
            return base + relativedelta(weeks=1)
            
        elif self.schedule_type == 'monthly':
            return base + relativedelta(months=1)
            
        elif self.schedule_type == 'cron' and self.cron_expression:
            cron = croniter(self.cron_expression, base)
            return cron.get_next(datetime.datetime)
        
        return None


# ============================================================================
# RÔLES ANSIBLE
# ============================================================================

class AnsibleRole(BaseModel):
    """Rôles Ansible réutilisables"""
    SOURCE_CHOICES = [
        ('local', 'Local'),
        ('galaxy', 'Ansible Galaxy'),
        ('git', 'Git Repository'),
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
    license = models.CharField('License', max_length=100, blank=True)
    
    # Fichiers
    role_path = models.CharField('Role Path', max_length=500, blank=True)
    readme = models.TextField('README', blank=True)
    
    # Dépendances
    dependencies = models.JSONField('Dependencies', default=list, blank=True)
    
    # ========================================================================
    # ASSOCIATIONS
    # ========================================================================
    playbooks = models.ManyToManyField(
        Playbook, 
        related_name='roles', 
        blank=True,
        help_text="Playbooks that use this role"
    )
    
    # Statistiques
    download_count = models.IntegerField('Download Count', default=0)
    used_in_playbooks = models.IntegerField('Used in Playbooks', default=0)
    
    class Meta:
        db_table = 'ansible_roles'
        ordering = ['namespace', 'name']
        unique_together = ['namespace', 'name', 'version']
    
    def __str__(self):
        return f"{self.namespace}.{self.name}:{self.version}"


# ============================================================================
# COLLECTIONS ANSIBLE
# ============================================================================

class AnsibleCollection(BaseModel):
    """Collections Ansible"""
    name = models.CharField('Name', max_length=200, unique=True)
    namespace = models.CharField('Namespace', max_length=200)
    version = models.CharField('Version', max_length=50)
    
    description = models.TextField('Description', blank=True)
    documentation = models.URLField('Documentation', blank=True)
    
    # Dépendances
    dependencies = models.JSONField('Dependencies', default=list, blank=True)
    
    # Installation
    installed_path = models.CharField('Installed Path', max_length=500, blank=True)
    installed_at = models.DateTimeField('Installed At', null=True, blank=True)
    
    # ========================================================================
    # ASSOCIATIONS
    # ========================================================================
    playbooks = models.ManyToManyField(
        Playbook, 
        related_name='collections', 
        blank=True,
        help_text="Playbooks that use this collection"
    )
    
    class Meta:
        db_table = 'ansible_collections'
        ordering = ['namespace', 'name']
    
    def __str__(self):
        return f"{self.namespace}.{self.name}:{self.version}"


# ============================================================================
# TÂCHES RÉUTILISABLES
# ============================================================================

class AnsibleTask(BaseModel):
    """Tâches Ansible réutilisables"""
    name = models.CharField('Name', max_length=200, unique=True)
    description = models.TextField('Description', blank=True)
    
    # Contenu de la tâche
    content = models.JSONField('Content', help_text="Task definition in JSON/YAML format")
    
    # ⚠️ REMPLACÉ ArrayField par JSONField
    tags = models.JSONField('Tags', default=list, blank=True)
    
    # ========================================================================
    # ASSOCIATIONS
    # ========================================================================
    playbooks = models.ManyToManyField(
        Playbook, 
        related_name='tasks', 
        blank=True,
        help_text="Playbooks that use this task"
    )
    
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_tasks'
    )
    
    class Meta:
        db_table = 'ansible_tasks'
        ordering = ['name']
    
    def __str__(self):
        return self.name


# ============================================================================
# VARIABLES ENVIRONNEMENT
# ============================================================================

class AnsibleVars(BaseModel):
    """Variables globales pour Ansible"""
    name = models.CharField('Name', max_length=200, unique=True)
    description = models.TextField('Description', blank=True)
    
    # Variables (clé-valeur)
    variables = models.JSONField('Variables', default=dict)
    
    # ========================================================================
    # ASSOCIATIONS
    # ========================================================================
    inventory = models.ForeignKey(
        AnsibleInventory, 
        on_delete=models.CASCADE, 
        related_name='extra_vars', 
        null=True, 
        blank=True
    )
    
    playbook = models.ForeignKey(
        Playbook, 
        on_delete=models.CASCADE, 
        related_name='extra_vars', 
        null=True, 
        blank=True
    )
    
    tenant = models.ForeignKey(
        Tenant, 
        on_delete=models.CASCADE, 
        related_name='ansible_vars', 
        null=True, 
        blank=True
    )
    
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_vars'
    )
    
    class Meta:
        db_table = 'ansible_vars'
        ordering = ['name']
    
    def __str__(self):
        return self.name


# ============================================================================
# CREDENTIALS ANSIBLE
# ============================================================================

class AnsibleCredential(BaseModel):
    """Credentials pour connexion aux équipements"""
    CREDENTIAL_TYPE_CHOICES = [
        ('ssh', 'SSH Key'),
        ('password', 'Password'),
        ('vault', 'Ansible Vault'),
        ('network', 'Network Device'),
        ('cloud', 'Cloud Provider'),
    ]
    
    name = models.CharField('Name', max_length=200, unique=True)
    credential_type = models.CharField('Type', max_length=20, choices=CREDENTIAL_TYPE_CHOICES)
    description = models.TextField('Description', blank=True)
    
    # Credentials (chiffrés)
    username = models.CharField('Username', max_length=100, blank=True)
    password = models.CharField('Password', max_length=500, blank=True)  # Chiffré
    ssh_key = models.TextField('SSH Key', blank=True)  # Chiffré
    ssh_key_passphrase = models.CharField('SSH Key Passphrase', max_length=500, blank=True)  # Chiffré
    
    # Vault
    vault_password = models.CharField('Vault Password', max_length=500, blank=True)  # Chiffré
    
    # Cloud
    access_key = models.CharField('Access Key', max_length=500, blank=True)  # Chiffré
    secret_key = models.CharField('Secret Key', max_length=500, blank=True)  # Chiffré
    
    # ========================================================================
    # ASSOCIATIONS
    # ========================================================================
    playbooks = models.ManyToManyField(
        Playbook, 
        related_name='credentials', 
        blank=True
    )
    
    inventories = models.ManyToManyField(
        AnsibleInventory, 
        related_name='credentials', 
        blank=True
    )
    
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_credentials'
    )
    
    class Meta:
        db_table = 'ansible_credentials'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_credential_type_display()})"