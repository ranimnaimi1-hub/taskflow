# apps/inventory/models.py
"""
Inventory Models - Ultra Professional
Network Inventory Management complet avec UUID et BaseModel
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import timedelta
from apps.core.models import BaseModel
from apps.users.models import User
import ipaddress


# ============================================================================
# 1. HIÉRARCHIE AVANCÉE : Régions, Sites, Locations
# ============================================================================

class Region(BaseModel):
    """Région géographique (Europe, Amérique du Nord, Asie, etc.)"""
    name = models.CharField('Name', max_length=100, unique=True)
    code = models.CharField('Code', max_length=20, unique=True)
    description = models.TextField('Description', blank=True)
    
    class Meta:
        db_table = 'inventory_regions'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Site(BaseModel):
    """Network Site/Location avec hiérarchie"""
    SITE_TYPE_CHOICES = [
        ('datacenter', 'Data Center'),
        ('campus', 'Campus'),
        ('headquarters', 'Headquarters'),
        ('branch', 'Branch Office'),
        ('remote', 'Remote Office'),
        ('pop', 'Point of Presence'),
        ('warehouse', 'Warehouse'),
        ('lab', 'Laboratory'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('planned', 'Planned'),
        ('decommissioned', 'Decommissioned'),
    ]
    
    name = models.CharField('Name', max_length=100, unique=True, db_index=True)
    code = models.CharField('Code', max_length=20, unique=True, db_index=True)
    site_type = models.CharField('Type', max_length=50, choices=SITE_TYPE_CHOICES)
    status = models.CharField('Status', max_length=50, choices=STATUS_CHOICES, default='active')
    
    # Hiérarchie
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name='sites', null=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='children')
    
    # Location
    address = models.TextField('Address')
    city = models.CharField('City', max_length=100)
    state = models.CharField('State/Province', max_length=100, blank=True)
    postal_code = models.CharField('Postal Code', max_length=20, blank=True)
    country = models.CharField('Country', max_length=100)
    latitude = models.DecimalField('Latitude', max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField('Longitude', max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Contact
    contact_name = models.CharField('Contact Name', max_length=100, blank=True)
    contact_email = models.EmailField('Contact Email', blank=True)
    contact_phone = models.CharField('Contact Phone', max_length=20, blank=True)
    
    # Métadonnées
    description = models.TextField('Description', blank=True)
    physical_security_level = models.CharField('Security Level', max_length=50, default='normal')
    
    class Meta:
        db_table = 'inventory_sites'
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['site_type']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class Location(BaseModel):
    """Location à l'intérieur d'un site (salle, étage, baie)"""
    LOCATION_TYPE_CHOICES = [
        ('room', 'Room'),
        ('floor', 'Floor'),
        ('suite', 'Suite'),
        ('cage', 'Cage'),
        ('cabinet', 'Cabinet'),
        ('aisle', 'Aisle'),
    ]
    
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='locations')
    name = models.CharField('Name', max_length=100)
    location_type = models.CharField('Type', max_length=50, choices=LOCATION_TYPE_CHOICES)
    parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='children')
    
    # Dimensions
    length = models.FloatField('Length (m)', null=True, blank=True)
    width = models.FloatField('Width (m)', null=True, blank=True)
    height = models.FloatField('Height (m)', null=True, blank=True)
    floor_number = models.IntegerField('Floor Number', null=True, blank=True)
    
    # Accès
    has_raised_floor = models.BooleanField('Raised Floor', default=False)
    has_drop_ceiling = models.BooleanField('Drop Ceiling', default=False)
    
    description = models.TextField('Description', blank=True)
    
    class Meta:
        db_table = 'inventory_locations'
        ordering = ['site', 'name']
        unique_together = ['site', 'name']
    
    def __str__(self):
        return f"{self.site.code} - {self.name}"


# ============================================================================
# 2. MANUFACTURERS, DEVICE TYPES ET RACKS
# ============================================================================

class Manufacturer(BaseModel):
    """Fabricant d'équipements"""
    name = models.CharField('Name', max_length=100, unique=True)
    slug = models.SlugField('Slug', max_length=100, unique=True)
    description = models.TextField('Description', blank=True)
    website = models.URLField('Website', blank=True)
    
    class Meta:
        db_table = 'inventory_manufacturers'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class DeviceType(BaseModel):
    """Device Type/Model amélioré"""
    DEVICE_CLASS_CHOICES = [
        ('router', 'Router'),
        ('switch', 'Switch'),
        ('firewall', 'Firewall'),
        ('load_balancer', 'Load Balancer'),
        ('wireless_controller', 'Wireless Controller'),
        ('access_point', 'Access Point'),
        ('server', 'Server'),
        ('storage', 'Storage'),
        ('patch_panel', 'Patch Panel'),
        ('pdu', 'PDU'),
        ('ups', 'UPS'),
        ('other', 'Other'),
    ]
    
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.PROTECT, related_name='device_types')
    model = models.CharField('Model', max_length=100)
    device_class = models.CharField('Class', max_length=50, choices=DEVICE_CLASS_CHOICES)
    name = models.CharField('Name', max_length=100)
    
    # Specifications
    port_count = models.IntegerField('Port Count', default=0)
    power_consumption = models.IntegerField('Power (W)', null=True, blank=True)
    rack_units = models.IntegerField('Rack Units', default=1)
    depth_mm = models.IntegerField('Depth (mm)', null=True, blank=True)
    weight_kg = models.FloatField('Weight (kg)', null=True, blank=True)
    
    class Meta:
        db_table = 'inventory_device_types'
        ordering = ['manufacturer', 'model']
        unique_together = ['manufacturer', 'model']
        indexes = [
            models.Index(fields=['manufacturer']),
            models.Index(fields=['device_class']),
        ]
    
    def __str__(self):
        return f"{self.manufacturer.name} {self.model}"


class Rack(BaseModel):
    """Rack/Baie pour équipements"""
    RACK_TYPE_CHOICES = [
        ('server', 'Server Rack'),
        ('network', 'Network Rack'),
        ('enclosure', 'Enclosure'),
        ('wall_mount', 'Wall Mount'),
    ]
    
    WIDTH_CHOICES = [
        ('19', '19 inches'),
        ('23', '23 inches'),
        ('etsi', 'ETSI'),
    ]
    
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='racks')
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='racks')
    name = models.CharField('Name', max_length=100)
    rack_type = models.CharField('Type', max_length=50, choices=RACK_TYPE_CHOICES, default='server')
    width = models.CharField('Width', max_length=10, choices=WIDTH_CHOICES, default='19')
    height_u = models.IntegerField('Height (U)', validators=[MinValueValidator(1), MaxValueValidator(60)])
    
    # Position
    row = models.CharField('Row', max_length=10, blank=True)
    position = models.IntegerField('Position', null=True, blank=True)
    
    # Puissance
    max_power_kw = models.FloatField('Max Power (kW)', null=True, blank=True)
    max_weight_kg = models.FloatField('Max Weight (kg)', null=True, blank=True)
    
    # Statut
    status = models.CharField('Status', max_length=50, choices=[
        ('active', 'Active'),
        ('planned', 'Planned'),
        ('decommissioned', 'Decommissioned'),
    ], default='active')
    
    # SVG
    svg_elevation = models.TextField('SVG Elevation', blank=True, editable=False)
    
    class Meta:
        db_table = 'inventory_racks'
        ordering = ['site', 'name']
        unique_together = ['site', 'name']
    
    def __str__(self):
        return f"{self.site.code} - {self.name}"


class Device(BaseModel):
    """Network Device amélioré avec plus de fonctionnalités"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Maintenance'),
        ('failed', 'Failed'),
        ('planned', 'Planned'),
        ('staged', 'Staged'),
        ('decommissioned', 'Decommissioned'),
    ]
    
    ROLE_CHOICES = [
        ('core_router', 'Core Router'),
        ('distribution', 'Distribution Switch'),
        ('access', 'Access Switch'),
        ('border_firewall', 'Border Firewall'),
        ('load_balancer', 'Load Balancer'),
        ('storage', 'Storage'),
        ('compute', 'Compute'),
        ('management', 'Management'),
    ]
    
    name = models.CharField('Name', max_length=100, db_index=True)
    hostname = models.CharField('Hostname', max_length=255, unique=True, db_index=True)
    device_type = models.ForeignKey(DeviceType, on_delete=models.PROTECT, related_name='devices')
    role = models.CharField('Role', max_length=50, choices=ROLE_CHOICES, blank=True)
    
    # Location
    site = models.ForeignKey(Site, on_delete=models.PROTECT, related_name='devices')
    rack = models.ForeignKey(Rack, on_delete=models.SET_NULL, null=True, blank=True, related_name='devices')
    rack_position = models.IntegerField('Rack Position', null=True, blank=True, validators=[MinValueValidator(1)])
    face = models.CharField('Face', max_length=10, choices=[
        ('front', 'Front'),
        ('rear', 'Rear'),
    ], default='front')
    
    # Management
    management_ip = models.GenericIPAddressField('Management IP', db_index=True)
    username = models.CharField('Username', max_length=100, blank=True)
    password = models.CharField('Password', max_length=255, blank=True)  # Should be encrypted
    ssh_port = models.IntegerField('SSH Port', default=22, validators=[MinValueValidator(1), MaxValueValidator(65535)])
    enable_password = models.CharField('Enable Password', max_length=255, blank=True)
    
    # Status
    status = models.CharField('Status', max_length=50, choices=STATUS_CHOICES, default='active', db_index=True)
    last_seen = models.DateTimeField('Last Seen', null=True, blank=True)
    
    # Hardware Info
    serial_number = models.CharField('Serial Number', max_length=100, blank=True, db_index=True)
    asset_tag = models.CharField('Asset Tag', max_length=100, blank=True)
    firmware_version = models.CharField('Firmware Version', max_length=100, blank=True)
    hardware_version = models.CharField('Hardware Version', max_length=100, blank=True)
    uptime_seconds = models.BigIntegerField('Uptime (seconds)', null=True, blank=True)
    
    # Monitoring
    cpu_usage = models.FloatField('CPU Usage %', null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    memory_usage = models.FloatField('Memory Usage %', null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    temperature = models.FloatField('Temperature °C', null=True, blank=True)
    
    # Tenancy & Ownership
    tenant = models.ForeignKey('inventory.Tenant', on_delete=models.SET_NULL, null=True, blank=True, related_name='devices')
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_devices')
    
    # Metadata
    description = models.TextField('Description', blank=True)
    notes = models.TextField('Notes', blank=True)
    tags = models.JSONField('Tags', default=list, blank=True)
    
    class Meta:
        db_table = 'inventory_devices'
        ordering = ['site', 'name']
        indexes = [
            models.Index(fields=['hostname']),
            models.Index(fields=['status']),
            models.Index(fields=['serial_number']),
            models.Index(fields=['site', 'status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.hostname})"
    
    @property
    def is_reachable(self):
        if self.last_seen:
            delta = timezone.now() - self.last_seen
            return delta < timedelta(minutes=5)
        return False
    
    @property
    def uptime_display(self):
        if self.uptime_seconds:
            days = self.uptime_seconds // 86400
            hours = (self.uptime_seconds % 86400) // 3600
            minutes = (self.uptime_seconds % 3600) // 60
            return f"{days}d {hours}h {minutes}m"
        return "Unknown"


# ============================================================================
# 3. IPAM COMPLET : VRFs, Route Targets, Prefixes
# ============================================================================

class RouteTarget(BaseModel):
    """BGP Route Target"""
    name = models.CharField('Name', max_length=100, unique=True, help_text="Format: ASN:NN")
    description = models.TextField('Description', blank=True)
    tenant = models.ForeignKey('inventory.Tenant', on_delete=models.PROTECT, null=True, blank=True)
    
    class Meta:
        db_table = 'inventory_route_targets'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class VRF(BaseModel):
    """Virtual Routing and Forwarding instance"""
    name = models.CharField('Name', max_length=100)
    rd = models.CharField('Route Distinguisher', max_length=100, unique=True, 
                         help_text="Format: ASN:NN or IP:NN")
    description = models.TextField('Description', blank=True)
    
    # Import/Export Route Targets
    import_targets = models.ManyToManyField(RouteTarget, related_name='importing_vrfs', blank=True)
    export_targets = models.ManyToManyField(RouteTarget, related_name='exporting_vrfs', blank=True)
    
    tenant = models.ForeignKey('inventory.Tenant', on_delete=models.PROTECT, null=True, blank=True, related_name='vrfs')
    enforce_unique = models.BooleanField('Enforce Unique Space', default=True)
    
    class Meta:
        db_table = 'inventory_vrfs'
        ordering = ['name']
        unique_together = ['name', 'rd']
    
    def __str__(self):
        return f"{self.name} ({self.rd})"


class Prefix(BaseModel):
    """IP Prefix pour IPAM"""
    FAMILY_CHOICES = [
        (4, 'IPv4'),
        (6, 'IPv6'),
    ]
    
    STATUS_CHOICES = [
        ('container', 'Container'),
        ('active', 'Active'),
        ('reserved', 'Reserved'),
        ('deprecated', 'Deprecated'),
    ]
    
    prefix = models.CharField('Prefix', max_length=100, unique=True)
    vrf = models.ForeignKey(VRF, on_delete=models.PROTECT, null=True, blank=True, related_name='prefixes')
    site = models.ForeignKey(Site, on_delete=models.PROTECT, null=True, blank=True, related_name='prefixes')
    
    family = models.IntegerField('Family', choices=FAMILY_CHOICES, editable=False)
    status = models.CharField('Status', max_length=50, choices=STATUS_CHOICES, default='active')
    
    description = models.TextField('Description', blank=True)
    is_pool = models.BooleanField('Is Pool', default=False, help_text="Allocate child prefixes from this pool")
    
    tenant = models.ForeignKey('inventory.Tenant', on_delete=models.PROTECT, null=True, blank=True, related_name='prefixes')
    
    class Meta:
        db_table = 'inventory_prefixes'
        ordering = ['vrf', 'prefix']
        indexes = [
            models.Index(fields=['prefix']),
            models.Index(fields=['vrf']),
        ]
    
    def save(self, *args, **kwargs):
        try:
            ipnet = ipaddress.ip_network(self.prefix)
            self.family = 4 if ipnet.version == 4 else 6
        except:
            pass
        super().save(*args, **kwargs)
    
    def __str__(self):
        vrf_str = f" ({self.vrf.name})" if self.vrf else ""
        return f"{self.prefix}{vrf_str}"
    
    def get_available_prefixes(self, prefix_length):
        """Retourne les sous-préfixes disponibles"""
        if not self.is_pool:
            return []
        
        used = [ipaddress.ip_network(p.prefix) for p in self.prefix_set.all()]
        network = ipaddress.ip_network(self.prefix)
        
        available = []
        for subnet in network.subnets(new_prefix=prefix_length):
            if not any(subnet.overlaps(u) for u in used):
                available.append(subnet)
        return available
    
    def get_available_ips(self):
        """Retourne les IPs disponibles dans ce préfixe"""
        used = set(ipaddress.ip_address(ip.address) for ip in self.ipaddress_set.filter(status='active'))
        network = ipaddress.ip_network(self.prefix)
        
        available = []
        for ip in network.hosts():
            if ip not in used:
                available.append(ip)
        return available


class IPAddress(BaseModel):
    """IP Address Assignment amélioré avec VRF"""
    IP_TYPE_CHOICES = [
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
        ('virtual', 'Virtual'),
        ('loopback', 'Loopback'),
        ('management', 'Management'),
        ('floating', 'Floating'),
        ('anycast', 'Anycast'),
        ('vip', 'VIP'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('reserved', 'Reserved'),
        ('deprecated', 'Deprecated'),
        ('dhcp', 'DHCP'),
    ]
    
    FAMILY_CHOICES = [
        (4, 'IPv4'),
        (6, 'IPv6'),
    ]
    
    address = models.GenericIPAddressField('IP Address', db_index=True)
    prefix_length = models.IntegerField('Prefix Length', validators=[MinValueValidator(0), MaxValueValidator(128)])
    family = models.IntegerField('Family', choices=FAMILY_CHOICES, editable=False)
    interface = models.ForeignKey('inventory.Interface', on_delete=models.CASCADE, related_name='ip_addresses', null=True, blank=True)
    
    # VRF
    vrf = models.ForeignKey(VRF, on_delete=models.PROTECT, null=True, blank=True, related_name='ip_addresses')
    
    # Type & Status
    ip_type = models.CharField('Type', max_length=50, choices=IP_TYPE_CHOICES, default='primary')
    status = models.CharField('Status', max_length=50, choices=STATUS_CHOICES, default='active')
    
    # Metadata
    description = models.CharField('Description', max_length=255, blank=True)
    dns_name = models.CharField('DNS Name', max_length=255, blank=True)
    
    # Tenancy
    tenant = models.ForeignKey('inventory.Tenant', on_delete=models.PROTECT, null=True, blank=True, related_name='ip_addresses')
    
    class Meta:
        db_table = 'inventory_ip_addresses'
        ordering = ['address']
        unique_together = ['vrf', 'address']
        indexes = [
            models.Index(fields=['address']),
            models.Index(fields=['vrf']),
            models.Index(fields=['status']),
        ]
    
    def save(self, *args, **kwargs):
        try:
            ip = ipaddress.ip_address(self.address)
            self.family = 4 if ip.version == 4 else 6
        except:
            pass
        super().save(*args, **kwargs)
    
    def __str__(self):
        vrf_str = f" ({self.vrf.name})" if self.vrf else ""
        return f"{self.address}/{self.prefix_length}{vrf_str}"


# ============================================================================
# 4. VLANs ET VLAN GROUPS
# ============================================================================

class VLANGroup(BaseModel):
    """Groupe de VLANs"""
    name = models.CharField('Name', max_length=100)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='vlan_groups', null=True, blank=True)
    description = models.TextField('Description', blank=True)
    
    # Plage de VLANs
    min_vid = models.IntegerField('Min VLAN ID', default=1, validators=[MinValueValidator(1), MaxValueValidator(4094)])
    max_vid = models.IntegerField('Max VLAN ID', default=4094, validators=[MinValueValidator(1), MaxValueValidator(4094)])
    
    class Meta:
        db_table = 'inventory_vlan_groups'
        ordering = ['site', 'name']
        unique_together = ['site', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.site.code if self.site else 'Global'})"


class VLAN(BaseModel):
    """VLAN Configuration amélioré"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('reserved', 'Reserved'),
        ('deprecated', 'Deprecated'),
    ]
    
    vlan_id = models.IntegerField('VLAN ID', validators=[MinValueValidator(1), MaxValueValidator(4094)])
    name = models.CharField('Name', max_length=100)
    group = models.ForeignKey(VLANGroup, on_delete=models.PROTECT, related_name='vlans', null=True, blank=True)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='vlans')
    
    description = models.TextField('Description', blank=True)
    status = models.CharField('Status', max_length=50, choices=STATUS_CHOICES, default='active')
    
    tenant = models.ForeignKey('inventory.Tenant', on_delete=models.PROTECT, null=True, blank=True, related_name='vlans')
    
    class Meta:
        db_table = 'inventory_vlans'
        ordering = ['site', 'vlan_id']
        unique_together = ['site', 'vlan_id']
        indexes = [
            models.Index(fields=['vlan_id']),
        ]
    
    def __str__(self):
        return f"VLAN {self.vlan_id} - {self.name}"


# ============================================================================
# 5. INTERFACES ET CABLAGE
# ============================================================================

class Interface(BaseModel):
    """Network Interface amélioré"""
    INTERFACE_TYPE_CHOICES = [
        ('ethernet', 'Ethernet'),
        ('fastethernet', 'FastEthernet'),
        ('gigabitethernet', 'GigabitEthernet'),
        ('tengigabitethernet', '10GigabitEthernet'),
        ('fortygigabitethernet', '40GigabitEthernet'),
        ('hundredgigabitethernet', '100GigabitEthernet'),
        ('loopback', 'Loopback'),
        ('vlan', 'VLAN'),
        ('tunnel', 'Tunnel'),
        ('port_channel', 'Port Channel'),
        ('management', 'Management'),
    ]
    
    STATUS_CHOICES = [
        ('up', 'Up'),
        ('down', 'Down'),
        ('admin_down', 'Admin Down'),
        ('testing', 'Testing'),
    ]
    
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='interfaces')
    name = models.CharField('Name', max_length=100)
    interface_type = models.CharField('Type', max_length=50, choices=INTERFACE_TYPE_CHOICES)
    
    # Configuration
    enabled = models.BooleanField('Enabled', default=True)
    description = models.CharField('Description', max_length=255, blank=True)
    mtu = models.IntegerField('MTU', default=1500, validators=[MinValueValidator(68), MaxValueValidator(9216)])
    speed = models.BigIntegerField('Speed (bps)', null=True, blank=True)
    duplex = models.CharField('Duplex', max_length=20, blank=True, choices=[
        ('full', 'Full'),
        ('half', 'Half'),
        ('auto', 'Auto'),
    ])
    mac_address = models.CharField('MAC Address', max_length=17, blank=True)
    
    # Status
    status = models.CharField('Status', max_length=50, choices=STATUS_CHOICES, default='down')
    last_change = models.DateTimeField('Last Change', null=True, blank=True)
    
    # Statistics
    rx_bytes = models.BigIntegerField('RX Bytes', default=0)
    tx_bytes = models.BigIntegerField('TX Bytes', default=0)
    rx_packets = models.BigIntegerField('RX Packets', default=0)
    tx_packets = models.BigIntegerField('TX Packets', default=0)
    rx_errors = models.BigIntegerField('RX Errors', default=0)
    tx_errors = models.BigIntegerField('TX Errors', default=0)
    rx_drops = models.BigIntegerField('RX Drops', default=0)
    tx_drops = models.BigIntegerField('TX Drops', default=0)
    
    class Meta:
        db_table = 'inventory_interfaces'
        ordering = ['device', 'name']
        unique_together = ['device', 'name']
        indexes = [
            models.Index(fields=['device', 'status']),
            models.Index(fields=['mac_address']),
        ]
    
    def __str__(self):
        return f"{self.device.name} - {self.name}"


class Cable(BaseModel):
    """Câble physique entre interfaces"""
    CABLE_TYPE_CHOICES = [
        ('cat5e', 'Cat5e'),
        ('cat6', 'Cat6'),
        ('cat6a', 'Cat6a'),
        ('cat7', 'Cat7'),
        ('cat8', 'Cat8'),
        ('mmf', 'Multimode Fiber'),
        ('smf', 'Singlemode Fiber'),
        ('coax', 'Coaxial'),
        ('power', 'Power'),
        ('console', 'Console'),
    ]
    
    STATUS_CHOICES = [
        ('connected', 'Connected'),
        ('planned', 'Planned'),
        ('decommissioned', 'Decommissioned'),
    ]
    
    cable_type = models.CharField('Type', max_length=50, choices=CABLE_TYPE_CHOICES)
    status = models.CharField('Status', max_length=50, choices=STATUS_CHOICES, default='connected')
    
    # Connecteurs
    interface_a = models.ForeignKey(Interface, on_delete=models.PROTECT, related_name='cables_a')
    interface_b = models.ForeignKey(Interface, on_delete=models.PROTECT, related_name='cables_b')
    
    # Métadonnées
    length = models.FloatField('Length (m)', null=True, blank=True)
    color = models.CharField('Color', max_length=50, blank=True)
    label = models.CharField('Label', max_length=100, blank=True)
    
    # SVG pour le traçage
    svg_path = models.TextField('SVG Path', blank=True, editable=False)
    
    description = models.TextField('Description', blank=True)
    
    class Meta:
        db_table = 'inventory_cables'
        unique_together = ['interface_a', 'interface_b']
        indexes = [
            models.Index(fields=['cable_type']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.interface_a} → {self.interface_b}"


class BreakoutCable(BaseModel):
    """Câble de breakout (ex: 100G -> 4x25G)"""
    parent_cable = models.ForeignKey(Cable, on_delete=models.CASCADE, related_name='breakouts')
    child_cable = models.ForeignKey(Cable, on_delete=models.CASCADE, related_name='parent')
    
    position = models.IntegerField('Position', help_text="Position dans le breakout (1-4)")
    
    class Meta:
        db_table = 'inventory_breakout_cables'
        unique_together = ['parent_cable', 'position']
    
    def __str__(self):
        return f"Breakout {self.position}: {self.parent_cable} → {self.child_cable}"


# ============================================================================
# 6. POWER : Alimentation électrique
# ============================================================================

class PowerPort(BaseModel):
    """Port d'alimentation sur un équipement"""
    PORT_TYPE_CHOICES = [
        ('iec_c13', 'IEC C13'),
        ('iec_c19', 'IEC C19'),
        ('nema_5_15', 'NEMA 5-15'),
        ('nema_5_20', 'NEMA 5-20'),
        ('dc_terminal', 'DC Terminal'),
    ]
    
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='power_ports')
    name = models.CharField('Name', max_length=100)
    port_type = models.CharField('Type', max_length=50, choices=PORT_TYPE_CHOICES)
    
    # Alimentation
    allocated_power_w = models.IntegerField('Allocated Power (W)', default=0)
    max_power_w = models.IntegerField('Max Power (W)', null=True, blank=True)
    
    description = models.TextField('Description', blank=True)
    
    class Meta:
        db_table = 'inventory_power_ports'
        ordering = ['device', 'name']
        unique_together = ['device', 'name']
    
    def __str__(self):
        return f"{self.device.name} - {self.name}"


class PowerFeed(BaseModel):
    """Alimentation électrique"""
    power_port = models.ForeignKey(PowerPort, on_delete=models.CASCADE, related_name='feeds')
    source = models.CharField('Source', max_length=100, help_text="PDU, UPS, etc.")
    
    # Mesures
    voltage = models.FloatField('Voltage (V)', null=True, blank=True)
    amperage = models.FloatField('Amperage (A)', null=True, blank=True)
    power_w = models.FloatField('Power (W)', null=True, blank=True)
    
    # Statut
    is_active = models.BooleanField('Active', default=True)
    last_measured = models.DateTimeField('Last Measured', null=True, blank=True)
    
    class Meta:
        db_table = 'inventory_power_feeds'
    
    def __str__(self):
        return f"{self.power_port} → {self.source}"


# ============================================================================
# 7. CIRCUITS WAN : Providers et circuits
# ============================================================================

class Provider(BaseModel):
    """Fournisseur de services"""
    name = models.CharField('Name', max_length=100, unique=True)
    slug = models.SlugField('Slug', max_length=100, unique=True)
    account_number = models.CharField('Account Number', max_length=100, blank=True)
    
    # Contact
    portal_url = models.URLField('Portal URL', blank=True)
    support_phone = models.CharField('Support Phone', max_length=50, blank=True)
    support_email = models.EmailField('Support Email', blank=True)
    
    description = models.TextField('Description', blank=True)
    
    class Meta:
        db_table = 'inventory_providers'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Circuit(BaseModel):
    """Circuit WAN/Métro"""
    CIRCUIT_TYPE_CHOICES = [
        ('ethernet', 'Ethernet'),
        ('mpls', 'MPLS'),
        ('dark_fiber', 'Dark Fiber'),
        ('dwdm', 'DWDM'),
        ('internet', 'Internet'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('planned', 'Planned'),
        ('decommissioned', 'Decommissioned'),
    ]
    
    circuit_id = models.CharField('Circuit ID', max_length=100, unique=True)
    circuit_type = models.CharField('Type', max_length=50, choices=CIRCUIT_TYPE_CHOICES)
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT, related_name='circuits')
    
    # Sites
    site_a = models.ForeignKey(Site, on_delete=models.PROTECT, related_name='circuits_a')
    site_b = models.ForeignKey(Site, on_delete=models.PROTECT, related_name='circuits_b')
    
    # Débits
    bandwidth_mbps = models.IntegerField('Bandwidth (Mbps)')
    mtu = models.IntegerField('MTU', default=1500)
    
    # Statut
    status = models.CharField('Status', max_length=50, choices=STATUS_CHOICES, default='active')
    
    # Métadonnées
    contract_start = models.DateField('Contract Start', null=True, blank=True)
    contract_end = models.DateField('Contract End', null=True, blank=True)
    monthly_cost = models.DecimalField('Monthly Cost', max_digits=10, decimal_places=2, null=True, blank=True)
    
    description = models.TextField('Description', blank=True)
    tenant = models.ForeignKey('inventory.Tenant', on_delete=models.PROTECT, null=True, blank=True, related_name='circuits')
    
    class Meta:
        db_table = 'inventory_circuits'
        ordering = ['provider', 'circuit_id']
    
    def __str__(self):
        return f"{self.circuit_id} ({self.get_circuit_type_display()})"


class CircuitTermination(BaseModel):
    """Terminaison de circuit sur équipement"""
    circuit = models.ForeignKey(Circuit, on_delete=models.CASCADE, related_name='terminations')
    device = models.ForeignKey(Device, on_delete=models.PROTECT, related_name='circuit_terminations')
    interface = models.ForeignKey(Interface, on_delete=models.PROTECT, related_name='circuit_terminations')
    
    # Rôle (A/Z)
    role = models.CharField('Role', max_length=10, choices=[
        ('a', 'A'),
        ('z', 'Z'),
    ])
    
    description = models.TextField('Description', blank=True)
    
    class Meta:
        db_table = 'inventory_circuit_terminations'
        unique_together = ['circuit', 'role']
    
    def __str__(self):
        return f"{self.circuit} - {self.role} on {self.device}:{self.interface}"


# ============================================================================
# 8. ROUTING : ASN, BGP, FHRP
# ============================================================================

class ASN(BaseModel):
    """Autonomous System Number"""
    ASN_TYPE_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
    ]
    
    number = models.BigIntegerField('AS Number', unique=True, 
                                   validators=[MinValueValidator(1), MaxValueValidator(4294967295)])
    asn_type = models.CharField('Type', max_length=50, choices=ASN_TYPE_CHOICES, default='public')
    description = models.TextField('Description', blank=True)
    
    # Propriétaire
    organization = models.CharField('Organization', max_length=200, blank=True)
    tenant = models.ForeignKey('inventory.Tenant', on_delete=models.PROTECT, null=True, blank=True, related_name='asns')
    
    class Meta:
        db_table = 'inventory_asns'
        ordering = ['number']
    
    def __str__(self):
        return f"AS{self.number}"
    
    @property
    def asdot(self):
        """Format ASdot pour les ASN 32-bit"""
        if self.number > 65535:
            high = self.number >> 16
            low = self.number & 65535
            return f"{high}.{low}"
        return str(self.number)


class FHRPGroup(BaseModel):
    """First Hop Redundancy Protocol Group"""
    PROTOCOL_CHOICES = [
        ('vrrp', 'VRRP'),
        ('hsrp', 'HSRP'),
        ('glbp', 'GLBP'),
        ('carp', 'CARP'),
    ]
    
    protocol = models.CharField('Protocol', max_length=50, choices=PROTOCOL_CHOICES)
    group_id = models.IntegerField('Group ID')
    
    # Adresse virtuelle
    virtual_ip = models.GenericIPAddressField('Virtual IP')
    virtual_mac = models.CharField('Virtual MAC', max_length=17, blank=True)
    
    # Priorité
    priority = models.IntegerField('Priority', default=100)
    preempt = models.BooleanField('Preempt', default=True)
    
    description = models.TextField('Description', blank=True)
    vlan = models.ForeignKey(VLAN, on_delete=models.PROTECT, null=True, blank=True)
    
    class Meta:
        db_table = 'inventory_fhrp_groups'
        unique_together = ['protocol', 'group_id', 'vlan']
    
    def __str__(self):
        return f"{self.get_protocol_display()} {self.group_id}"


class BGPSession(BaseModel):
    """BGP Session entre routeurs"""
    SESSION_TYPE_CHOICES = [
        ('ebgp', 'eBGP'),
        ('ibgp', 'iBGP'),
    ]
    
    SESSION_STATE_CHOICES = [
        ('idle', 'Idle'),
        ('connect', 'Connect'),
        ('active', 'Active'),
        ('opensent', 'OpenSent'),
        ('openconfirm', 'OpenConfirm'),
        ('established', 'Established'),
    ]
    
    name = models.CharField('Name', max_length=200, blank=True)
    session_type = models.CharField('Type', max_length=50, choices=SESSION_TYPE_CHOICES)
    
    # Routeurs
    device_a = models.ForeignKey(Device, on_delete=models.PROTECT, related_name='bgp_sessions_a')
    device_b = models.ForeignKey(Device, on_delete=models.PROTECT, related_name='bgp_sessions_b')
    
    # ASNs
    asn_a = models.ForeignKey(ASN, on_delete=models.PROTECT, related_name='bgp_sessions_a')
    asn_b = models.ForeignKey(ASN, on_delete=models.PROTECT, related_name='bgp_sessions_b')
    
    # IPs
    ip_a = models.ForeignKey(IPAddress, on_delete=models.PROTECT, related_name='bgp_sessions_a')
    ip_b = models.ForeignKey(IPAddress, on_delete=models.PROTECT, related_name='bgp_sessions_b')
    
    # Statut
    state = models.CharField('State', max_length=50, choices=SESSION_STATE_CHOICES, default='idle')
    last_state_change = models.DateTimeField('Last State Change', null=True, blank=True)
    
    description = models.TextField('Description', blank=True)
    
    class Meta:
        db_table = 'inventory_bgp_sessions'
        unique_together = ['device_a', 'device_b', 'asn_a', 'asn_b']
    
    def __str__(self):
        return f"{self.device_a.name} (AS{self.asn_a}) <-> {self.device_b.name} (AS{self.asn_b})"


# ============================================================================
# 9. VIRTUALISATION : Clusters et VMs
# ============================================================================

class Cluster(BaseModel):
    """Cluster de virtualisation"""
    CLUSTER_TYPE_CHOICES = [
        ('vmware', 'VMware vSphere'),
        ('proxmox', 'Proxmox VE'),
        ('xen', 'XenServer'),
        ('kvm', 'KVM'),
        ('hyperv', 'Hyper-V'),
        ('nutanix', 'Nutanix'),
    ]
    
    name = models.CharField('Name', max_length=100, unique=True)
    cluster_type = models.CharField('Type', max_length=50, choices=CLUSTER_TYPE_CHOICES)
    
    # Infrastructure
    hosts = models.ManyToManyField(Device, related_name='clusters')
    datastores = models.JSONField('Datastores', default=list, blank=True)
    
    # Configuration
    total_ram_gb = models.IntegerField('Total RAM (GB)', default=0)
    total_cpu_cores = models.IntegerField('Total CPU Cores', default=0)
    total_disk_tb = models.FloatField('Total Disk (TB)', default=0)
    
    description = models.TextField('Description', blank=True)
    tenant = models.ForeignKey('inventory.Tenant', on_delete=models.PROTECT, null=True, blank=True, related_name='clusters')
    
    class Meta:
        db_table = 'inventory_clusters'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class VirtualMachine(BaseModel):
    """Machine Virtuelle"""
    POWER_STATE_CHOICES = [
        ('running', 'Running'),
        ('stopped', 'Stopped'),
        ('suspended', 'Suspended'),
    ]
    
    name = models.CharField('Name', max_length=100)
    cluster = models.ForeignKey(Cluster, on_delete=models.PROTECT, related_name='vms')
    host = models.ForeignKey(Device, on_delete=models.PROTECT, related_name='vms')
    
    # Resources
    vcpus = models.IntegerField('vCPUs', default=1, validators=[MinValueValidator(1)])
    ram_gb = models.IntegerField('RAM (GB)', default=1)
    disk_gb = models.IntegerField('Disk (GB)', default=10)
    
    # Réseau
    interfaces = models.ManyToManyField(Interface, related_name='vms', blank=True)
    ip_addresses = models.ManyToManyField(IPAddress, related_name='vms', blank=True)
    
    # Statut
    power_state = models.CharField('Power State', max_length=50, choices=POWER_STATE_CHOICES, default='stopped')
    guest_os = models.CharField('Guest OS', max_length=100, blank=True)
    
    # Métadonnées
    uuid = models.CharField('UUID', max_length=36, unique=True, blank=True)
    description = models.TextField('Description', blank=True)
    tenant = models.ForeignKey('inventory.Tenant', on_delete=models.PROTECT, null=True, blank=True, related_name='vms')
    
    class Meta:
        db_table = 'inventory_virtual_machines'
        ordering = ['cluster', 'name']
        unique_together = ['cluster', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.cluster.name})"


# ============================================================================
# 10. TENANCY : Tenants et Contacts
# ============================================================================

class Tenant(BaseModel):
    """Client/propriétaire des ressources"""
    name = models.CharField('Name', max_length=100, unique=True)
    slug = models.SlugField('Slug', max_length=100, unique=True)
    
    # Informations
    tenant_id = models.CharField('Tenant ID', max_length=100, unique=True)
    description = models.TextField('Description', blank=True)
    
    # Hiérarchie
    parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='children')
    
    # Contact
    contact_name = models.CharField('Contact Name', max_length=200, blank=True)
    contact_email = models.EmailField('Contact Email', blank=True)
    contact_phone = models.CharField('Contact Phone', max_length=50, blank=True)
    
    class Meta:
        db_table = 'inventory_tenants'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Contact(BaseModel):
    """Contact individuel"""
    name = models.CharField('Name', max_length=200)
    title = models.CharField('Title', max_length=200, blank=True)
    
    # Coordonnées
    phone = models.CharField('Phone', max_length=50, blank=True)
    email = models.EmailField('Email', blank=True)
    
    # Adresse
    address = models.TextField('Address', blank=True)
    
    # Relations
    tenants = models.ManyToManyField(Tenant, related_name='contacts', blank=True)
    sites = models.ManyToManyField(Site, related_name='contacts', blank=True)
    
    class Meta:
        db_table = 'inventory_contacts'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class TenantAssignment(BaseModel):
    """Assignation de ressources à un tenant"""
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='assignments')
    
    # Resource (Generic FK)
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    object_id = models.UUIDField()
    
    role = models.CharField('Role', max_length=100, blank=True)
    
    class Meta:
        db_table = 'inventory_tenant_assignments'
        unique_together = ['tenant', 'content_type', 'object_id']


# ============================================================================
# 11. L2VPN (Optionnel - si besoin)
# ============================================================================

class L2VPN(BaseModel):
    """Layer 2 VPN Overlay"""
    TYPE_CHOICES = [
        ('vpls', 'VPLS'),
        ('vxlan', 'VXLAN'),
        ('evpn', 'EVPN'),
        ('pbb', 'PBB'),
        ('vpws', 'VPWS'),
    ]
    
    name = models.CharField('Name', max_length=100, unique=True)
    vpn_type = models.CharField('Type', max_length=50, choices=TYPE_CHOICES)
    vni = models.BigIntegerField('VNI', null=True, blank=True, help_text="VXLAN Network Identifier")
    
    description = models.TextField('Description', blank=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, null=True, blank=True, related_name='l2vpns')
    
    class Meta:
        db_table = 'inventory_l2vpns'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_vpn_type_display()})"