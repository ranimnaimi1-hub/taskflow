# apps/inventory/admin.py
"""
Inventory Admin - Ultra Professional
Interface d'administration complète pour tous les modèles
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from import_export.admin import ImportExportModelAdmin
from .models import *


# ============================================================================
# HIÉRARCHIE
# ============================================================================

@admin.register(Region)
class RegionAdmin(ImportExportModelAdmin):
    list_display = ['name', 'code', 'sites_count', 'created_at']
    search_fields = ['name', 'code', 'description']
    prepopulated_fields = {'code': ('name',)}
    
    def sites_count(self, obj):
        count = obj.sites.count()
        url = reverse('admin:inventory_site_changelist') + f'?region__id__exact={obj.id}'
        return format_html('<a href="{}"><b>{}</b></a>', url, count)
    sites_count.short_description = 'Sites'


@admin.register(Site)
class SiteAdmin(ImportExportModelAdmin):
    list_display = ['name_display', 'code', 'region_info', 'site_type_badge', 
                   'city', 'country', 'status_badge', 'devices_count']
    list_filter = ['site_type', 'status', 'region', 'country']
    search_fields = ['name', 'code', 'city', 'address']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['region', 'parent']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'site_type', 'status', 'region', 'parent')
        }),
        ('Location', {
            'fields': ('address', 'city', 'state', 'postal_code', 'country', 
                      'latitude', 'longitude')
        }),
        ('Contact', {
            'fields': ('contact_name', 'contact_email', 'contact_phone')
        }),
        ('Security', {
            'fields': ('physical_security_level',)
        }),
        ('Metadata', {
            'fields': ('description',)
        }),
    )
    
    def name_display(self, obj):
        url = reverse('admin:inventory_site_change', args=[obj.id])
        return format_html('<a href="{}"><strong>{}</strong></a>', url, obj.name)
    name_display.short_description = 'Name'
    
    def region_info(self, obj):
        if obj.region:
            url = reverse('admin:inventory_region_change', args=[obj.region.id])
            return format_html('<a href="{}">{}</a>', url, obj.region.name)
        return '-'
    region_info.short_description = 'Region'
    
    def site_type_badge(self, obj):
        colors = {
            'datacenter': '#0d6efd', 'campus': '#198754', 'headquarters': '#dc3545',
            'branch': '#ffc107', 'pop': '#6f42c1', 'warehouse': '#20c997',
        }
        color = colors.get(obj.site_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_site_type_display()
        )
    site_type_badge.short_description = 'Type'
    
    def status_badge(self, obj):
        colors = {'active': '#198754', 'planned': '#ffc107', 'decommissioned': '#6c757d'}
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, 'white' if obj.status == 'active' else 'black', obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def devices_count(self, obj):
        count = obj.devices.count()
        url = reverse('admin:inventory_device_changelist') + f'?site__id__exact={obj.id}'
        return format_html('<a href="{}"><b>{}</b></a>', url, count)
    devices_count.short_description = 'Devices'


@admin.register(Location)
class LocationAdmin(ImportExportModelAdmin):
    list_display = ['name', 'site', 'location_type', 'floor_number', 'racks_count']
    list_filter = ['location_type', 'site']
    search_fields = ['name', 'site__name']
    raw_id_fields = ['site', 'parent']
    
    def racks_count(self, obj):
        return obj.racks.count()
    racks_count.short_description = 'Racks'


# ============================================================================
# MANUFACTURERS ET DEVICE TYPES
# ============================================================================

@admin.register(Manufacturer)
class ManufacturerAdmin(ImportExportModelAdmin):
    list_display = ['name', 'slug', 'website', 'device_types_count']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    
    def device_types_count(self, obj):
        return obj.device_types.count()
    device_types_count.short_description = 'Device Types'


@admin.register(DeviceType)
class DeviceTypeAdmin(ImportExportModelAdmin):
    list_display = ['name', 'manufacturer', 'model', 'device_class_badge', 
                   'rack_units', 'port_count']
    list_filter = ['device_class', 'manufacturer']
    search_fields = ['name', 'manufacturer__name', 'model']
    raw_id_fields = ['manufacturer']
    
    def device_class_badge(self, obj):
        colors = {
            'router': '#0d6efd', 'switch': '#198754', 'firewall': '#dc3545',
            'load_balancer': '#ffc107', 'server': '#6f42c1', 'storage': '#20c997',
        }
        color = colors.get(obj.device_class, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_device_class_display()
        )
    device_class_badge.short_description = 'Class'


# ============================================================================
# RACKS ET ÉQUIPEMENTS
# ============================================================================

class DeviceInline(admin.TabularInline):
    model = Device
    extra = 0
    fields = ['name', 'hostname', 'device_type', 'status', 'rack_position']
    readonly_fields = ['status']


@admin.register(Rack)
class RackAdmin(ImportExportModelAdmin):
    list_display = ['name', 'site', 'location', 'rack_type', 'height_u', 
                   'devices_count', 'status_badge']
    list_filter = ['rack_type', 'status', 'site']
    search_fields = ['name', 'site__name']
    raw_id_fields = ['site', 'location']
    inlines = [DeviceInline]
    
    def devices_count(self, obj):
        return obj.devices.count()
    devices_count.short_description = 'Devices'
    
    def status_badge(self, obj):
        colors = {'active': '#198754', 'planned': '#ffc107', 'decommissioned': '#6c757d'}
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, 'white' if obj.status == 'active' else 'black', obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    actions = ['generate_svg_elevation']
    
    def generate_svg_elevation(self, request, queryset):
        from .utils.svg_renderer import SVGRackRenderer
        for rack in queryset:
            renderer = SVGRackRenderer(rack)
            rack.svg_elevation = renderer.render()
            rack.save()
        self.message_user(request, f'SVG generated for {queryset.count()} racks')
    generate_svg_elevation.short_description = "Generate SVG elevation"


class InterfaceInline(admin.TabularInline):
    model = Interface
    extra = 0
    fields = ['name', 'interface_type', 'status', 'enabled', 'mac_address', 'speed']
    readonly_fields = ['status']


class PowerPortInline(admin.TabularInline):
    model = PowerPort
    extra = 0
    fields = ['name', 'port_type', 'allocated_power_w']


@admin.register(Device)
class DeviceAdmin(ImportExportModelAdmin):
    list_display = ['name_display', 'hostname', 'device_type_info', 'site_info', 
                   'rack_info', 'status_badge', 'management_ip', 'reachable_indicator']
    list_filter = ['status', 'site', 'device_type__device_class', 'role']
    search_fields = ['name', 'hostname', 'management_ip', 'serial_number']
    readonly_fields = ['id', 'created_at', 'updated_at', 'uptime_display', 'is_reachable']
    raw_id_fields = ['site', 'rack', 'device_type', 'tenant', 'owner']
    inlines = [InterfaceInline, PowerPortInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'hostname', 'device_type', 'role', 'status')
        }),
        ('Location', {
            'fields': ('site', 'rack', 'rack_position', 'face')
        }),
        ('Management', {
            'fields': ('management_ip', 'username', 'password', 'enable_password', 'ssh_port')
        }),
        ('Hardware', {
            'fields': ('serial_number', 'asset_tag', 'firmware_version', 'hardware_version')
        }),
        ('Monitoring', {
            'fields': ('last_seen', 'uptime_seconds', 'uptime_display', 
                      'cpu_usage', 'memory_usage', 'temperature', 'is_reachable')
        }),
        ('Tenancy & Ownership', {
            'fields': ('tenant', 'owner')
        }),
        ('Metadata', {
            'fields': ('description', 'notes', 'tags')
        }),
    )
    
    def name_display(self, obj):
        url = reverse('admin:inventory_device_change', args=[obj.id])
        return format_html('<a href="{}"><strong>{}</strong></a>', url, obj.name)
    name_display.short_description = 'Name'
    
    def device_type_info(self, obj):
        return format_html(
            '{}<br><small>{}</small>',
            obj.device_type.name,
            obj.device_type.manufacturer.name
        )
    device_type_info.short_description = 'Device Type'
    
    def site_info(self, obj):
        url = reverse('admin:inventory_site_change', args=[obj.site.id])
        return format_html('<a href="{}">{}</a>', url, obj.site.code)
    site_info.short_description = 'Site'
    
    def rack_info(self, obj):
        if obj.rack:
            url = reverse('admin:inventory_rack_change', args=[obj.rack.id])
            return format_html('<a href="{}">U{}</a>', url, obj.rack_position)
        return '-'
    rack_info.short_description = 'Rack'
    
    def status_badge(self, obj):
        colors = {
            'active': '#198754', 'inactive': '#6c757d', 'maintenance': '#ffc107',
            'failed': '#dc3545', 'planned': '#0d6efd', 'decommissioned': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, 'white' if obj.status not in ['maintenance', 'planned'] else 'black',
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def reachable_indicator(self, obj):
        if obj.is_reachable:
            return format_html('<span style="color: #198754;">● Online</span>')
        return format_html('<span style="color: #6c757d;">● Offline</span>')
    reachable_indicator.short_description = 'Reachable'


# ============================================================================
# INTERFACES ET IP
# ============================================================================

class IPAddressInline(admin.TabularInline):
    model = IPAddress
    extra = 0
    fields = ['address', 'prefix_length', 'vrf', 'status', 'dns_name']


@admin.register(Interface)
class InterfaceAdmin(ImportExportModelAdmin):
    list_display = ['name', 'device_link', 'interface_type', 'status_badge', 
                   'enabled', 'mac_address', 'ip_count', 'speed_display']
    list_filter = ['status', 'enabled', 'interface_type', 'device__site']
    search_fields = ['name', 'device__name', 'mac_address']
    raw_id_fields = ['device']
    inlines = [IPAddressInline]
    
    def device_link(self, obj):
        url = reverse('admin:inventory_device_change', args=[obj.device.id])
        return format_html('<a href="{}">{}</a>', url, obj.device.name)
    device_link.short_description = 'Device'
    
    def status_badge(self, obj):
        colors = {'up': '#198754', 'down': '#dc3545', 'admin_down': '#6c757d', 'testing': '#ffc107'}
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, 'white' if obj.status == 'up' else 'black', obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def ip_count(self, obj):
        return obj.ip_addresses.count()
    ip_count.short_description = 'IPs'
    
    def speed_display(self, obj):
        if obj.speed:
            if obj.speed >= 1_000_000_000:
                return f"{obj.speed / 1_000_000_000:.0f}G"
            elif obj.speed >= 1_000_000:
                return f"{obj.speed / 1_000_000:.0f}M"
        return '-'
    speed_display.short_description = 'Speed'


@admin.register(IPAddress)
class IPAddressAdmin(ImportExportModelAdmin):
    list_display = ['address', 'prefix_length', 'family_badge', 'interface_link', 
                   'vrf_info', 'ip_type_badge', 'status_badge', 'dns_name']
    list_filter = ['status', 'ip_type', 'family', 'vrf']
    search_fields = ['address', 'dns_name', 'description']
    raw_id_fields = ['interface', 'vrf', 'tenant']
    
    def interface_link(self, obj):
        if obj.interface:
            url = reverse('admin:inventory_interface_change', args=[obj.interface.id])
            return format_html('<a href="{}">{}</a>', url, obj.interface.name)
        return '-'
    interface_link.short_description = 'Interface'
    
    def vrf_info(self, obj):
        if obj.vrf:
            url = reverse('admin:inventory_vrf_change', args=[obj.vrf.id])
            return format_html('<a href="{}">{}</a>', url, obj.vrf.name)
        return 'Global'
    vrf_info.short_description = 'VRF'
    
    def family_badge(self, obj):
        if obj.family == 4:
            return format_html('<span style="color: #0d6efd;">IPv4</span>')
        return format_html('<span style="color: #198754;">IPv6</span>')
    family_badge.short_description = 'Family'
    
    def ip_type_badge(self, obj):
        colors = {
            'primary': '#0d6efd', 'secondary': '#6c757d', 'virtual': '#198754',
            'loopback': '#6f42c1', 'management': '#ffc107', 'vip': '#dc3545'
        }
        color = colors.get(obj.ip_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, 'white' if obj.ip_type in ['primary', 'virtual', 'vip'] else 'black',
            obj.get_ip_type_display()
        )
    ip_type_badge.short_description = 'Type'
    
    def status_badge(self, obj):
        colors = {'active': '#198754', 'reserved': '#ffc107', 'deprecated': '#6c757d', 'dhcp': '#0d6efd'}
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, 'white' if obj.status != 'reserved' else 'black', obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(Prefix)
class PrefixAdmin(ImportExportModelAdmin):
    list_display = ['prefix', 'vrf_info', 'site', 'family_badge', 'status_badge', 
                   'is_pool', 'description']
    list_filter = ['status', 'family', 'vrf', 'site']
    search_fields = ['prefix', 'description']
    raw_id_fields = ['vrf', 'site', 'tenant']
    
    def vrf_info(self, obj):
        if obj.vrf:
            url = reverse('admin:inventory_vrf_change', args=[obj.vrf.id])
            return format_html('<a href="{}">{}</a>', url, obj.vrf.name)
        return 'Global'
    vrf_info.short_description = 'VRF'
    
    def family_badge(self, obj):
        if obj.family == 4:
            return format_html('<span style="color: #0d6efd;">IPv4</span>')
        return format_html('<span style="color: #198754;">IPv6</span>')
    family_badge.short_description = 'Family'
    
    def status_badge(self, obj):
        colors = {
            'container': '#6f42c1', 'active': '#198754', 
            'reserved': '#ffc107', 'deprecated': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, 'white' if obj.status != 'reserved' else 'black', obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(VRF)
class VRFAdmin(ImportExportModelAdmin):
    list_display = ['name', 'rd', 'tenant', 'prefixes_count', 'enforce_unique']
    list_filter = ['tenant']
    search_fields = ['name', 'rd', 'description']
    filter_horizontal = ['import_targets', 'export_targets']
    raw_id_fields = ['tenant']
    
    def prefixes_count(self, obj):
        return obj.prefixes.count()
    prefixes_count.short_description = 'Prefixes'


@admin.register(RouteTarget)
class RouteTargetAdmin(ImportExportModelAdmin):
    list_display = ['name', 'tenant', 'description']
    search_fields = ['name']
    raw_id_fields = ['tenant']


# ============================================================================
# VLANS
# ============================================================================

@admin.register(VLANGroup)
class VLANGroupAdmin(ImportExportModelAdmin):
    list_display = ['name', 'site', 'vlans_count', 'min_vid', 'max_vid']
    list_filter = ['site']
    search_fields = ['name', 'site__name']
    
    def vlans_count(self, obj):
        return obj.vlans.count()
    vlans_count.short_description = 'VLANs'


@admin.register(VLAN)
class VLANAdmin(ImportExportModelAdmin):
    list_display = ['vlan_id', 'name', 'site', 'group', 'status_badge']
    list_filter = ['status', 'site', 'group']
    search_fields = ['name', 'vlan_id']
    raw_id_fields = ['site', 'group', 'tenant']
    
    def status_badge(self, obj):
        colors = {'active': '#198754', 'reserved': '#ffc107', 'deprecated': '#6c757d'}
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, 'white' if obj.status != 'reserved' else 'black', obj.get_status_display()
        )
    status_badge.short_description = 'Status'


# ============================================================================
# CÂBLAGE
# ============================================================================

@admin.register(Cable)
class CableAdmin(ImportExportModelAdmin):
    list_display = ['cable_type', 'interface_a_info', 'interface_b_info', 
                   'length', 'status_badge']
    list_filter = ['cable_type', 'status']
    search_fields = ['label', 'description']
    raw_id_fields = ['interface_a', 'interface_b']
    
    def interface_a_info(self, obj):
        return f"{obj.interface_a.device.name} - {obj.interface_a.name}"
    interface_a_info.short_description = 'Interface A'
    
    def interface_b_info(self, obj):
        return f"{obj.interface_b.device.name} - {obj.interface_b.name}"
    interface_b_info.short_description = 'Interface B'
    
    def status_badge(self, obj):
        colors = {'connected': '#198754', 'planned': '#ffc107', 'decommissioned': '#6c757d'}
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, 'white' if obj.status == 'connected' else 'black', obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(BreakoutCable)
class BreakoutCableAdmin(ImportExportModelAdmin):
    list_display = ['parent_cable', 'child_cable', 'position']
    list_filter = ['position']


# ============================================================================
# POWER
# ============================================================================

@admin.register(PowerPort)
class PowerPortAdmin(ImportExportModelAdmin):
    list_display = ['name', 'device', 'port_type', 'allocated_power_w', 'max_power_w']
    list_filter = ['port_type', 'device__site']
    search_fields = ['name', 'device__name']
    raw_id_fields = ['device']


@admin.register(PowerFeed)
class PowerFeedAdmin(ImportExportModelAdmin):
    list_display = ['power_port', 'source', 'voltage', 'amperage', 'power_w', 'is_active']
    list_filter = ['is_active', 'source']
    raw_id_fields = ['power_port']


# ============================================================================
# CIRCUITS WAN
# ============================================================================

@admin.register(Provider)
class ProviderAdmin(ImportExportModelAdmin):
    list_display = ['name', 'slug', 'account_number', 'circuits_count']
    search_fields = ['name', 'account_number']
    prepopulated_fields = {'slug': ('name',)}
    
    def circuits_count(self, obj):
        return obj.circuits.count()
    circuits_count.short_description = 'Circuits'


@admin.register(Circuit)
class CircuitAdmin(ImportExportModelAdmin):
    list_display = ['circuit_id', 'circuit_type', 'provider', 'bandwidth_mbps', 
                   'site_a', 'site_b', 'status_badge']
    list_filter = ['circuit_type', 'provider', 'status', 'site_a', 'site_b']
    search_fields = ['circuit_id', 'provider__name']
    raw_id_fields = ['provider', 'site_a', 'site_b', 'tenant']
    
    def status_badge(self, obj):
        colors = {'active': '#198754', 'planned': '#ffc107', 'decommissioned': '#6c757d'}
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, 'white' if obj.status == 'active' else 'black', obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(CircuitTermination)
class CircuitTerminationAdmin(ImportExportModelAdmin):
    list_display = ['circuit', 'role', 'device', 'interface']
    list_filter = ['role']
    raw_id_fields = ['circuit', 'device', 'interface']


# ============================================================================
# ROUTING
# ============================================================================

@admin.register(ASN)
class ASNAdmin(ImportExportModelAdmin):
    list_display = ['number', 'asdot', 'asn_type', 'organization', 'tenant']
    list_filter = ['asn_type', 'tenant']
    search_fields = ['number', 'organization']
    raw_id_fields = ['tenant']


@admin.register(FHRPGroup)
class FHRPGroupAdmin(ImportExportModelAdmin):
    list_display = ['protocol', 'group_id', 'virtual_ip', 'vlan', 'priority', 'preempt']
    list_filter = ['protocol', 'preempt']
    raw_id_fields = ['vlan']


@admin.register(BGPSession)
class BGPSessionAdmin(ImportExportModelAdmin):
    list_display = ['name', 'device_a', 'device_b', 'session_type', 'state', 'last_state_change']
    list_filter = ['session_type', 'state']
    raw_id_fields = ['device_a', 'device_b', 'asn_a', 'asn_b', 'ip_a', 'ip_b']


# ============================================================================
# VIRTUALISATION
# ============================================================================

@admin.register(Cluster)
class ClusterAdmin(ImportExportModelAdmin):
    list_display = ['name', 'cluster_type', 'total_cpu_cores', 'total_ram_gb', 
                   'total_disk_tb', 'hosts_count', 'vms_count']
    list_filter = ['cluster_type', 'tenant']
    search_fields = ['name']
    filter_horizontal = ['hosts']
    raw_id_fields = ['tenant']
    
    def hosts_count(self, obj):
        return obj.hosts.count()
    hosts_count.short_description = 'Hosts'
    
    def vms_count(self, obj):
        return obj.vms.count()
    vms_count.short_description = 'VMs'


@admin.register(VirtualMachine)
class VirtualMachineAdmin(ImportExportModelAdmin):
    list_display = ['name', 'cluster', 'host', 'vcpus', 'ram_gb', 'disk_gb', 
                   'power_state_badge']
    list_filter = ['power_state', 'cluster', 'tenant']
    search_fields = ['name', 'uuid']
    filter_horizontal = ['interfaces', 'ip_addresses']
    raw_id_fields = ['cluster', 'host', 'tenant']
    
    def power_state_badge(self, obj):
        colors = {'running': '#198754', 'stopped': '#6c757d', 'suspended': '#ffc107'}
        color = colors.get(obj.power_state, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, 'white' if obj.power_state == 'running' else 'black', obj.get_power_state_display()
        )
    power_state_badge.short_description = 'Power State'


# ============================================================================
# TENANCY
# ============================================================================

@admin.register(Tenant)
class TenantAdmin(ImportExportModelAdmin):
    list_display = ['name', 'slug', 'tenant_id', 'parent', 'contact_name', 
                   'devices_count', 'vlans_count', 'prefixes_count']
    search_fields = ['name', 'tenant_id']
    prepopulated_fields = {'slug': ('name',)}
    raw_id_fields = ['parent']
    
    def devices_count(self, obj):
        return obj.devices.count()
    devices_count.short_description = 'Devices'
    
    def vlans_count(self, obj):
        return obj.vlans.count()
    vlans_count.short_description = 'VLANs'
    
    def prefixes_count(self, obj):
        return obj.prefixes.count()
    prefixes_count.short_description = 'Prefixes'


@admin.register(Contact)
class ContactAdmin(ImportExportModelAdmin):
    list_display = ['name', 'title', 'email', 'phone']
    search_fields = ['name', 'email']
    filter_horizontal = ['tenants', 'sites']


@admin.register(TenantAssignment)
class TenantAssignmentAdmin(ImportExportModelAdmin):
    list_display = ['tenant', 'content_type', 'object_id', 'role']
    list_filter = ['content_type', 'tenant']
    raw_id_fields = ['tenant']


# ============================================================================
# L2VPN (optionnel)
# ============================================================================

@admin.register(L2VPN)
class L2VPNAdmin(ImportExportModelAdmin):
    list_display = ['name', 'vpn_type', 'vni', 'tenant']
    list_filter = ['vpn_type', 'tenant']
    search_fields = ['name']
    raw_id_fields = ['tenant']