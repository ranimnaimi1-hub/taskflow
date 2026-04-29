"""
EVE-NG App Models - Professional
Gestion des laboratoires EVE-NG
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.core.models import BaseModel
from apps.users.models import User
import json


# ============================================================================
# SERVEURS EVE-NG
# ============================================================================

class EVENServer(BaseModel):
    """Configuration des serveurs EVE-NG"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Maintenance'),
    ]
    
    name = models.CharField('Name', max_length=200, unique=True, db_index=True)
    description = models.TextField('Description', blank=True)
    
    # Connexion
    url = models.URLField('EVE-NG URL', help_text="e.g., http://eveng:80")
    username = models.CharField('Username', max_length=100)
    password = models.CharField('Password', max_length=500)  # À chiffrer
    
    # Configuration
    timeout = models.IntegerField('Timeout (seconds)', default=30,
                                 validators=[MinValueValidator(5), MaxValueValidator(300)])
    
    # Statistiques
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='active')
    version = models.CharField('EVE-NG Version', max_length=50, blank=True)
    cpu_usage = models.FloatField('CPU Usage %', null=True, blank=True)
    memory_usage = models.FloatField('Memory Usage %', null=True, blank=True)
    disk_usage = models.FloatField('Disk Usage %', null=True, blank=True)
    last_sync_at = models.DateTimeField('Last Sync', null=True, blank=True)
    
    # Propriétaire
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='eveng_servers'
    )
    
    class Meta:
        db_table = 'eveng_servers'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.url})"
    
    def get_client(self):
        """Retourne un client EVE-NG configuré"""
        from .eveng_client import EVENGClient
        return EVENGClient(
            url=self.url,
            username=self.username,
            password=self.password
        )


# ============================================================================
# LABORATOIRES EVE-NG
# ============================================================================

class EVENLab(BaseModel):
    """Laboratoires EVE-NG"""
    LAB_STATUS_CHOICES = [
        ('stopped', 'Stopped'),
        ('running', 'Running'),
        ('building', 'Building'),
        ('error', 'Error'),
    ]
    
    server = models.ForeignKey(
        EVENServer, 
        on_delete=models.CASCADE, 
        related_name='labs'
    )
    
    # Informations du lab
    lab_path = models.CharField('Lab Path', max_length=500, help_text="Path in EVE-NG")
    name = models.CharField('Name', max_length=200)
    description = models.TextField('Description', blank=True)
    
    # Métadonnées
    lab_id = models.CharField('Lab ID', max_length=100, blank=True)
    filename = models.CharField('Filename', max_length=200, blank=True)
    folder = models.CharField('Folder', max_length=500, blank=True)
    
    # Statut
    status = models.CharField('Status', max_length=20, choices=LAB_STATUS_CHOICES, default='stopped')
    
    # Statistiques
    node_count = models.IntegerField('Node Count', default=0)
    link_count = models.IntegerField('Link Count', default=0)
    network_count = models.IntegerField('Network Count', default=0)
    
    # Configuration
    config = models.JSONField('Configuration', default=dict, blank=True)
    topology = models.JSONField('Topology', default=dict, blank=True)
    
    # Synchronisation
    synced_at = models.DateTimeField('Synced At', null=True, blank=True)
    is_active = models.BooleanField('Active', default=True)
    
    # Propriétaire
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='eveng_labs'
    )
    
    class Meta:
        db_table = 'eveng_labs'
        ordering = ['server', 'name']
        unique_together = ['server', 'lab_path']
        indexes = [
            models.Index(fields=['server', 'lab_path']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.server.name} - {self.name}"


# ============================================================================
# NŒUDS EVE-NG
# ============================================================================

class EVENNode(BaseModel):
    """Nœuds dans les laboratoires EVE-NG"""
    NODE_TYPE_CHOICES = [
        ('router', 'Router'),
        ('switch', 'Switch'),
        ('firewall', 'Firewall'),
        ('host', 'Host'),
        ('server', 'Server'),
        ('vm', 'Virtual Machine'),
        ('docker', 'Docker Container'),
        ('other', 'Other'),
    ]
    
    NODE_STATUS_CHOICES = [
        ('stopped', 'Stopped'),
        ('running', 'Running'),
        ('building', 'Building'),
        ('error', 'Error'),
        ('unknown', 'Unknown'),
    ]
    
    CONSOLE_TYPE_CHOICES = [
        ('telnet', 'Telnet'),
        ('vnc', 'VNC'),
        ('spice', 'SPICE'),
        ('rdp', 'RDP'),
    ]
    
    lab = models.ForeignKey(
        EVENLab, 
        on_delete=models.CASCADE, 
        related_name='nodes'
    )
    
    # Informations du nœud
    node_id = models.IntegerField('Node ID')
    name = models.CharField('Name', max_length=200)
    node_type = models.CharField('Type', max_length=50, choices=NODE_TYPE_CHOICES, default='other')
    
    # Image/Template
    image = models.CharField('Image', max_length=200, blank=True)
    template = models.CharField('Template', max_length=200, blank=True)
    
    # Statut
    status = models.CharField('Status', max_length=20, choices=NODE_STATUS_CHOICES, default='stopped')
    
    # Configuration
    cpu = models.IntegerField('CPU Cores', default=1)
    ram = models.IntegerField('RAM (MB)', default=512)
    ethernet = models.IntegerField('Ethernet Ports', default=4)
    console = models.CharField('Console', max_length=50, blank=True)
    console_type = models.CharField('Console Type', max_length=20, choices=CONSOLE_TYPE_CHOICES, default='telnet')
    console_port = models.IntegerField('Console Port', null=True, blank=True)
    
    # Position dans le lab
    position_x = models.IntegerField('Position X', default=0)
    position_y = models.IntegerField('Position Y', default=0)
    
    # Configuration
    config = models.JSONField('Configuration', default=dict, blank=True)
    interfaces = models.JSONField('Interfaces', default=list, blank=True)
    
    # Métadonnées
    url = models.URLField('Node URL', blank=True)
    
    class Meta:
        db_table = 'eveng_nodes'
        ordering = ['lab', 'node_id']
        unique_together = ['lab', 'node_id']
        indexes = [
            models.Index(fields=['lab', 'status']),
        ]
    
    def __str__(self):
        return f"{self.lab.name} - {self.name} (ID: {self.node_id})"


# ============================================================================
# RÉSEAUX EVE-NG
# ============================================================================

class EVENNetwork(BaseModel):
    """Réseaux dans les laboratoires EVE-NG"""
    NETWORK_TYPE_CHOICES = [
        ('bridge', 'Bridge'),
        ('nat', 'NAT'),
        ('host_only', 'Host Only'),
        ('cloud', 'Cloud'),
    ]
    
    lab = models.ForeignKey(
        EVENLab, 
        on_delete=models.CASCADE, 
        related_name='networks'
    )
    
    # Informations du réseau
    network_id = models.IntegerField('Network ID')
    name = models.CharField('Name', max_length=200, blank=True)
    network_type = models.CharField('Type', max_length=50, choices=NETWORK_TYPE_CHOICES, default='bridge')
    
    # Configuration
    left = models.IntegerField('Left', default=0)
    top = models.IntegerField('Top', default=0)
    
    # Métadonnées
    count = models.IntegerField('Count', default=0)
    
    class Meta:
        db_table = 'eveng_networks'
        ordering = ['lab', 'network_id']
        unique_together = ['lab', 'network_id']
    
    def __str__(self):
        return f"{self.lab.name} - {self.name or f'Network {self.network_id}'}"


# ============================================================================
# LIENS EVE-NG
# ============================================================================

class EVENLink(BaseModel):
    """Liens entre nœuds dans EVE-NG"""
    LINK_TYPE_CHOICES = [
        ('ethernet', 'Ethernet'),
        ('serial', 'Serial'),
        ('bridge', 'Bridge'),
    ]
    
    lab = models.ForeignKey(
        EVENLab, 
        on_delete=models.CASCADE, 
        related_name='links'
    )
    
    # Source
    source_node = models.ForeignKey(
        EVENNode, 
        on_delete=models.CASCADE, 
        related_name='source_links'
    )
    source_label = models.CharField('Source Label', max_length=50, blank=True)
    source_interface = models.CharField('Source Interface', max_length=50, blank=True)
    
    # Destination
    destination_node = models.ForeignKey(
        EVENNode, 
        on_delete=models.CASCADE, 
        related_name='destination_links'
    )
    destination_label = models.CharField('Destination Label', max_length=50, blank=True)
    destination_interface = models.CharField('Destination Interface', max_length=50, blank=True)
    
    # Type
    link_type = models.CharField('Type', max_length=50, choices=LINK_TYPE_CHOICES, default='ethernet')
    
    # Configuration
    color = models.CharField('Color', max_length=50, default='#000000')
    width = models.IntegerField('Width', default=2)
    
    class Meta:
        db_table = 'eveng_links'
        ordering = ['lab', 'id']
        indexes = [
            models.Index(fields=['lab', 'source_node', 'destination_node']),
        ]
    
    def __str__(self):
        return f"{self.source_node.name} → {self.destination_node.name}"


# ============================================================================
# IMAGES/TEMPLATES EVE-NG
# ============================================================================

class EVENImage(BaseModel):
    """Images/Templates disponibles dans EVE-NG"""
    IMAGE_TYPE_CHOICES = [
        ('qemu', 'QEMU'),
        ('iol', 'IOL'),
        ('dynamips', 'Dynamips'),
        ('docker', 'Docker'),
    ]
    
    server = models.ForeignKey(
        EVENServer, 
        on_delete=models.CASCADE, 
        related_name='images'
    )
    
    # Informations de l'image
    name = models.CharField('Name', max_length=200)
    image_type = models.CharField('Type', max_length=50, choices=IMAGE_TYPE_CHOICES)
    path = models.CharField('Path', max_length=500)
    
    # Métadonnées
    description = models.TextField('Description', blank=True)
    version = models.CharField('Version', max_length=50, blank=True)
    size_mb = models.IntegerField('Size (MB)', default=0)
    
    # Configuration par défaut
    default_cpu = models.IntegerField('Default CPU', default=1)
    default_ram = models.IntegerField('Default RAM (MB)', default=512)
    default_ethernet = models.IntegerField('Default Ethernet', default=4)
    
    # Synchronisation
    synced_at = models.DateTimeField('Synced At', null=True, blank=True)
    
    class Meta:
        db_table = 'eveng_images'
        ordering = ['server', 'name']
        unique_together = ['server', 'path']
    
    def __str__(self):
        return f"{self.server.name} - {self.name} ({self.get_image_type_display()})"


# ============================================================================
# SESSIONS UTILISATEURS
# ============================================================================

class EVENUserSession(BaseModel):
    """Sessions des utilisateurs sur EVE-NG"""
    server = models.ForeignKey(
        EVENServer, 
        on_delete=models.CASCADE, 
        related_name='sessions'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='eveng_sessions'
    )
    
    # Session
    session_id = models.CharField('Session ID', max_length=200, unique=True)
    cookie = models.TextField('Cookie', blank=True)
    
    # Timestamps
    logged_in_at = models.DateTimeField('Logged In At', auto_now_add=True)
    last_activity_at = models.DateTimeField('Last Activity At', auto_now=True)
    expires_at = models.DateTimeField('Expires At', null=True, blank=True)
    
    # Statut
    is_active = models.BooleanField('Active', default=True)
    
    class Meta:
        db_table = 'eveng_user_sessions'
        ordering = ['-last_activity_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.server.name}"