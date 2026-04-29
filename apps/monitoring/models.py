"""
Monitoring App Models - Professional
Gestion des métriques et alertes de la plateforme
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.core.models import BaseModel
from apps.users.models import User
from apps.inventory.models import Device, Interface
import json


# ============================================================================
# MÉTRIQUES SYSTÈME
# ============================================================================

class SystemMetric(BaseModel):
    """Métriques système de la plateforme"""
    
    # CPU
    cpu_usage = models.FloatField('CPU Usage %', validators=[MinValueValidator(0), MaxValueValidator(100)])
    cpu_count = models.IntegerField('CPU Count', default=0)
    load_avg_1min = models.FloatField('Load Average 1min', null=True, blank=True)
    load_avg_5min = models.FloatField('Load Average 5min', null=True, blank=True)
    load_avg_15min = models.FloatField('Load Average 15min', null=True, blank=True)
    
    # Memory
    memory_total = models.BigIntegerField('Memory Total (bytes)')
    memory_available = models.BigIntegerField('Memory Available (bytes)')
    memory_used = models.BigIntegerField('Memory Used (bytes)')
    memory_percent = models.FloatField('Memory Usage %', validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # Disk
    disk_total = models.BigIntegerField('Disk Total (bytes)')
    disk_used = models.BigIntegerField('Disk Used (bytes)')
    disk_free = models.BigIntegerField('Disk Free (bytes)')
    disk_percent = models.FloatField('Disk Usage %', validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # Network
    network_bytes_sent = models.BigIntegerField('Network Bytes Sent')
    network_bytes_recv = models.BigIntegerField('Network Bytes Received')
    network_packets_sent = models.BigIntegerField('Network Packets Sent')
    network_packets_recv = models.BigIntegerField('Network Packets Received')
    
    # Timestamp
    collected_at = models.DateTimeField('Collected At', db_index=True)
    
    class Meta:
        db_table = 'monitoring_system_metrics'
        ordering = ['-collected_at']
        indexes = [
            models.Index(fields=['-collected_at']),
        ]
    
    def __str__(self):
        return f"System Metric at {self.collected_at}"


# ============================================================================
# MÉTRIQUES DES ÉQUIPEMENTS
# ============================================================================

class DeviceMetric(BaseModel):
    """Métriques des équipements réseau"""
    
    device = models.ForeignKey(
        Device, 
        on_delete=models.CASCADE, 
        related_name='metrics'
    )
    
    # Métriques de santé
    cpu_usage = models.FloatField('CPU Usage %', null=True, blank=True,
                                 validators=[MinValueValidator(0), MaxValueValidator(100)])
    memory_usage = models.FloatField('Memory Usage %', null=True, blank=True,
                                    validators=[MinValueValidator(0), MaxValueValidator(100)])
    temperature = models.FloatField('Temperature °C', null=True, blank=True)
    uptime = models.BigIntegerField('Uptime (seconds)', null=True, blank=True)
    
    # Statut de connectivité
    is_reachable = models.BooleanField('Is Reachable', default=False)
    response_time = models.FloatField('Response Time (ms)', null=True, blank=True)
    
    # Métadonnées
    collected_at = models.DateTimeField('Collected At', db_index=True)
    
    class Meta:
        db_table = 'monitoring_device_metrics'
        ordering = ['-collected_at']
        indexes = [
            models.Index(fields=['device', '-collected_at']),
            models.Index(fields=['-collected_at']),
        ]
    
    def __str__(self):
        return f"Metrics for {self.device.hostname} at {self.collected_at}"


class InterfaceMetric(BaseModel):
    """Métriques des interfaces réseau"""
    
    interface = models.ForeignKey(
        Interface, 
        on_delete=models.CASCADE, 
        related_name='metrics'
    )
    
    # Statistiques d'interface
    status = models.CharField('Status', max_length=20, blank=True)
    rx_bytes = models.BigIntegerField('RX Bytes', default=0)
    tx_bytes = models.BigIntegerField('TX Bytes', default=0)
    rx_packets = models.BigIntegerField('RX Packets', default=0)
    tx_packets = models.BigIntegerField('TX Packets', default=0)
    rx_errors = models.BigIntegerField('RX Errors', default=0)
    tx_errors = models.BigIntegerField('TX Errors', default=0)
    rx_drops = models.BigIntegerField('RX Drops', default=0)
    tx_drops = models.BigIntegerField('TX Drops', default=0)
    
    # Taux
    rx_rate_bps = models.FloatField('RX Rate (bps)', null=True, blank=True)
    tx_rate_bps = models.FloatField('TX Rate (bps)', null=True, blank=True)
    
    # Métadonnées
    collected_at = models.DateTimeField('Collected At', db_index=True)
    
    class Meta:
        db_table = 'monitoring_interface_metrics'
        ordering = ['-collected_at']
        indexes = [
            models.Index(fields=['interface', '-collected_at']),
            models.Index(fields=['-collected_at']),
        ]
    
    def __str__(self):
        return f"Metrics for {self.interface.name} at {self.collected_at}"


# ============================================================================
# MÉTRIQUES APPLICATIVES
# ============================================================================

class ApplicationMetric(BaseModel):
    """Métriques des applications de la plateforme"""
    
    METRIC_TYPE_CHOICES = [
        ('ansible', 'Ansible'),
        ('terraform', 'Terraform'),
        ('jenkins', 'Jenkins'),
        ('grafana', 'Grafana'),
        ('eveng', 'EVE-NG'),
        ('users', 'Users'),
        ('system', 'System'),
    ]
    
    metric_type = models.CharField('Metric Type', max_length=50, choices=METRIC_TYPE_CHOICES, db_index=True)
    metric_name = models.CharField('Metric Name', max_length=200)
    metric_value = models.FloatField('Metric Value')
    
    # Métadonnées
    tags = models.JSONField('Tags', default=dict, blank=True)
    collected_at = models.DateTimeField('Collected At', db_index=True)
    
    class Meta:
        db_table = 'monitoring_application_metrics'
        ordering = ['-collected_at']
        indexes = [
            models.Index(fields=['metric_type', '-collected_at']),
            models.Index(fields=['-collected_at']),
        ]
    
    def __str__(self):
        return f"{self.get_metric_type_display()} - {self.metric_name}: {self.metric_value}"


# ============================================================================
# ALERTES
# ============================================================================

class Alert(BaseModel):
    """Alertes de la plateforme"""
    
    SEVERITY_CHOICES = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('info', 'Info'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
        ('expired', 'Expired'),
    ]
    
    SOURCE_CHOICES = [
        ('system', 'System'),
        ('device', 'Device'),
        ('interface', 'Interface'),
        ('application', 'Application'),
        ('custom', 'Custom'),
    ]
    
    # Informations de l'alerte
    name = models.CharField('Name', max_length=200)
    description = models.TextField('Description', blank=True)
    severity = models.CharField('Severity', max_length=20, choices=SEVERITY_CHOICES, default='medium')
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='active')
    source = models.CharField('Source', max_length=20, choices=SOURCE_CHOICES, default='system')
    
    # Source spécifique
    device = models.ForeignKey(
        Device, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='alerts'
    )
    interface = models.ForeignKey(
        Interface, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='alerts'
    )
    
    # Valeur de seuil
    metric_name = models.CharField('Metric Name', max_length=200, blank=True)
    metric_value = models.FloatField('Metric Value', null=True, blank=True)
    threshold_value = models.FloatField('Threshold Value', null=True, blank=True)
    operator = models.CharField('Operator', max_length=10, blank=True, 
                               choices=[('>', '>'), ('<', '<'), ('>=', '>='), ('<=', '<='), ('==', '==')])
    
    # Métadonnées
    first_occurrence = models.DateTimeField('First Occurrence', auto_now_add=True)
    last_occurrence = models.DateTimeField('Last Occurrence', auto_now=True)
    occurrence_count = models.IntegerField('Occurrence Count', default=1)
    
    # Actions
    acknowledged_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField('Acknowledged At', null=True, blank=True)
    resolved_at = models.DateTimeField('Resolved At', null=True, blank=True)
    
    # Notification
    notifications_sent = models.IntegerField('Notifications Sent', default=0)
    last_notification_at = models.DateTimeField('Last Notification At', null=True, blank=True)
    
    # Notes
    notes = models.TextField('Notes', blank=True)
    
    class Meta:
        db_table = 'monitoring_alerts'
        ordering = ['-last_occurrence']
        indexes = [
            models.Index(fields=['status', 'severity']),
            models.Index(fields=['source']),
            models.Index(fields=['device']),
            models.Index(fields=['-last_occurrence']),
        ]
    
    def __str__(self):
        return f"[{self.get_severity_display()}] {self.name}"
    
    def acknowledge(self, user):
        """Marque l'alerte comme acquittée"""
        self.status = 'acknowledged'
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save()
    
    def resolve(self):
        """Marque l'alerte comme résolue"""
        self.status = 'resolved'
        self.resolved_at = timezone.now()
        self.save()
    
    def increment_occurrence(self):
        """Incrémente le compteur d'occurrences"""
        self.occurrence_count += 1
        self.last_occurrence = timezone.now()
        self.save()


# ============================================================================
# SEUILS D'ALERTE
# ============================================================================

class AlertThreshold(BaseModel):
    """Seuils de déclenchement des alertes"""
    
    THRESHOLD_TYPE_CHOICES = [
        ('system_cpu', 'System CPU Usage'),
        ('system_memory', 'System Memory Usage'),
        ('system_disk', 'System Disk Usage'),
        ('device_cpu', 'Device CPU Usage'),
        ('device_memory', 'Device Memory Usage'),
        ('device_temperature', 'Device Temperature'),
        ('device_reachability', 'Device Reachability'),
        ('interface_status', 'Interface Status'),
        ('interface_errors', 'Interface Errors'),
        ('interface_bandwidth', 'Interface Bandwidth'),
        ('application', 'Application Metric'),
    ]
    
    name = models.CharField('Name', max_length=200)
    threshold_type = models.CharField('Type', max_length=50, choices=THRESHOLD_TYPE_CHOICES)
    description = models.TextField('Description', blank=True)
    
    # Seuil
    warning_threshold = models.FloatField('Warning Threshold', null=True, blank=True)
    critical_threshold = models.FloatField('Critical Threshold', null=True, blank=True)
    operator = models.CharField('Operator', max_length=10, default='>',
                               choices=[('>', '>'), ('<', '<'), ('>=', '>='), ('<=', '<=')])
    
    # Durée (en secondes)
    duration = models.IntegerField('Duration (seconds)', default=0,
                                  help_text="Duration threshold must be exceeded before alert")
    
    # Période de silence (en minutes)
    silence_period = models.IntegerField('Silence Period (minutes)', default=5,
                                        help_text="Minimum time between alerts")
    
    # Cibles
    devices = models.ManyToManyField(
        Device, 
        related_name='alert_thresholds', 
        blank=True,
        help_text="Specific devices to monitor (leave empty for all)"
    )
    
    # Statut
    is_enabled = models.BooleanField('Enabled', default=True)
    
    # Métadonnées
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_thresholds'
    )
    
    class Meta:
        db_table = 'monitoring_alert_thresholds'
        ordering = ['name']
        indexes = [
            models.Index(fields=['threshold_type', 'is_enabled']),
        ]
    
    def __str__(self):
        return self.name
    
    def check_value(self, value):
        """Vérifie si une valeur dépasse les seuils"""
        results = {
            'warning': False,
            'critical': False,
            'value': value
        }
        
        if self.operator == '>':
            if self.critical_threshold is not None and value > self.critical_threshold:
                results['critical'] = True
            elif self.warning_threshold is not None and value > self.warning_threshold:
                results['warning'] = True
        elif self.operator == '<':
            if self.critical_threshold is not None and value < self.critical_threshold:
                results['critical'] = True
            elif self.warning_threshold is not None and value < self.warning_threshold:
                results['warning'] = True
        elif self.operator == '>=':
            if self.critical_threshold is not None and value >= self.critical_threshold:
                results['critical'] = True
            elif self.warning_threshold is not None and value >= self.warning_threshold:
                results['warning'] = True
        elif self.operator == '<=':
            if self.critical_threshold is not None and value <= self.critical_threshold:
                results['critical'] = True
            elif self.warning_threshold is not None and value <= self.warning_threshold:
                results['warning'] = True
        
        return results


# ============================================================================
# NOTIFICATIONS
# ============================================================================

class NotificationChannel(BaseModel):
    """Canaux de notification"""
    
    CHANNEL_TYPE_CHOICES = [
        ('email', 'Email'),
        ('slack', 'Slack'),
        ('webhook', 'Webhook'),
        ('telegram', 'Telegram'),
    ]
    
    name = models.CharField('Name', max_length=200)
    channel_type = models.CharField('Type', max_length=50, choices=CHANNEL_TYPE_CHOICES)
    description = models.TextField('Description', blank=True)
    
    # Configuration
    config = models.JSONField('Configuration', default=dict, blank=True)
    
    # Statut
    is_enabled = models.BooleanField('Enabled', default=True)
    
    class Meta:
        db_table = 'monitoring_notification_channels'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"


class NotificationLog(BaseModel):
    """Historique des notifications envoyées"""
    
    alert = models.ForeignKey(
        Alert, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    channel = models.ForeignKey(
        NotificationChannel, 
        on_delete=models.CASCADE, 
        related_name='logs'
    )
    
    # Statut
    status = models.CharField('Status', max_length=20, default='sent',
                             choices=[('sent', 'Sent'), ('failed', 'Failed'), ('pending', 'Pending')])
    error_message = models.TextField('Error Message', blank=True)
    
    # Métadonnées
    sent_at = models.DateTimeField('Sent At', auto_now_add=True)
    
    class Meta:
        db_table = 'monitoring_notification_logs'
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"Notification for {self.alert.name} at {self.sent_at}"


# ============================================================================
# TABLEAUX DE BORD
# ============================================================================

class Dashboard(BaseModel):
    """Tableaux de bord personnalisés"""
    
    name = models.CharField('Name', max_length=200)
    description = models.TextField('Description', blank=True)
    
    # Configuration du dashboard (JSON)
    config = models.JSONField('Configuration', default=dict, blank=True)
    
    # Widgets (JSON)
    widgets = models.JSONField('Widgets', default=list, blank=True)
    
    # Propriétaire
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='dashboards',
        null=True,
        blank=True
    )
    
    # Visibilité
    is_public = models.BooleanField('Public', default=False)
    
    class Meta:
        db_table = 'monitoring_dashboards'
        ordering = ['name']
    
    def __str__(self):
        return self.name


# ============================================================================
# COLLECTIONS DE MÉTRIQUES
# ============================================================================

class MetricCollection(BaseModel):
    """Collection de métriques pour les graphiques"""
    
    name = models.CharField('Name', max_length=200)
    description = models.TextField('Description', blank=True)
    
    # Type de collection
    metric_type = models.CharField('Metric Type', max_length=50, choices=ApplicationMetric.METRIC_TYPE_CHOICES)
    metric_names = models.JSONField('Metric Names', default=list, blank=True)
    
    # Période de rétention (en jours)
    retention_days = models.IntegerField('Retention Days', default=30)
    
    # Agrégation
    aggregation = models.CharField('Aggregation', max_length=20, default='avg',
                                  choices=[('avg', 'Average'), ('min', 'Minimum'), 
                                           ('max', 'Maximum'), ('sum', 'Sum')])
    
    class Meta:
        db_table = 'monitoring_metric_collections'
        ordering = ['name']
    
    def __str__(self):
        return self.name