"""
EVE-NG App Admin - Interface d'administration professionnelle
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from import_export.admin import ImportExportModelAdmin
import json

from .models import (
    EVENServer, EVENLab, EVENNode, EVENNetwork,
    EVENLink, EVENImage, EVENUserSession
)


# ============================================================================
# INLINES
# ============================================================================

class EVENLabInline(admin.TabularInline):
    """Inline pour les labs dans le serveur"""
    model = EVENLab
    extra = 0
    fields = ['name_link', 'lab_path', 'status_badge', 'node_count', 'is_active']
    readonly_fields = ['name_link', 'lab_path', 'status_badge', 'node_count']
    can_delete = False
    
    def name_link(self, obj):
        url = reverse('admin:eveng_app_evenlab_change', args=[obj.id])
        return format_html('<a href="{}">{}</a>', url, obj.name)
    name_link.short_description = 'Name'
    
    def status_badge(self, obj):
        colors = {
            'running': 'success',
            'stopped': 'secondary',
            'building': 'warning',
            'error': 'danger',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_status_display())
    status_badge.short_description = 'Status'
    
    def has_add_permission(self, request, obj=None):
        return False


class EVENNodeInline(admin.TabularInline):
    """Inline pour les nœuds dans le lab"""
    model = EVENNode
    extra = 0
    fields = ['node_id', 'name', 'node_type', 'status_badge', 'cpu', 'ram']
    readonly_fields = ['node_id', 'name', 'node_type', 'status_badge', 'cpu', 'ram']
    can_delete = False
    ordering = ['node_id']
    
    def status_badge(self, obj):
        colors = {
            'running': 'success',
            'stopped': 'secondary',
            'building': 'warning',
            'error': 'danger',
            'unknown': 'info',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_status_display())
    status_badge.short_description = 'Status'
    
    def has_add_permission(self, request, obj=None):
        return False


class EVENNetworkInline(admin.TabularInline):
    """Inline pour les réseaux dans le lab"""
    model = EVENNetwork
    extra = 0
    fields = ['network_id', 'name', 'network_type', 'count']
    readonly_fields = ['network_id', 'name', 'network_type', 'count']
    can_delete = False
    ordering = ['network_id']
    
    def has_add_permission(self, request, obj=None):
        return False


# ============================================================================
# SERVEURS EVE-NG
# ============================================================================

@admin.register(EVENServer)
class EVENServerAdmin(ImportExportModelAdmin):
    """Admin pour les serveurs EVE-NG"""
    list_display = [
        'name_display', 'url', 'status_badge', 'version',
        'labs_count', 'images_count', 'cpu_usage_bar', 'last_sync_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'description', 'url']
    readonly_fields = ['id', 'created_at', 'updated_at', 'version', 'last_sync_at',
                      'cpu_usage', 'memory_usage', 'disk_usage', 'usage_bars']
    raw_id_fields = ['created_by']
    inlines = [EVENLabInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'url', 'status')
        }),
        ('Authentication', {
            'fields': ('username', 'password'),
            'classes': ('wide',)
        }),
        ('Configuration', {
            'fields': ('timeout',),
            'classes': ('collapse',)
        }),
        ('System Status', {
            'fields': ('version', 'usage_bars', 'last_sync_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def name_display(self, obj):
        url = reverse('admin:eveng_app_even_server_change', args=[obj.id])
        return format_html('<a href="{}"><strong>{}</strong></a>', url, obj.name)
    name_display.short_description = 'Name'
    
    def status_badge(self, obj):
        colors = {
            'active': 'success',
            'inactive': 'secondary',
            'maintenance': 'warning',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_status_display())
    status_badge.short_description = 'Status'
    
    def labs_count(self, obj):
        count = obj.labs.count()
        return format_html('<span class="badge badge-info">{}</span>', count)
    labs_count.short_description = 'Labs'
    
    def images_count(self, obj):
        count = obj.images.count()
        return format_html('<span class="badge badge-success">{}</span>', count)
    images_count.short_description = 'Images'
    
    def cpu_usage_bar(self, obj):
        if obj.cpu_usage:
            color = 'danger' if obj.cpu_usage > 80 else 'warning' if obj.cpu_usage > 60 else 'success'
            return format_html(
                '<div class="progress" style="height: 20px;">'
                '<div class="progress-bar bg-{}" role="progressbar" style="width: {}%;">{}%</div>'
                '</div>',
                color, obj.cpu_usage, obj.cpu_usage
            )
        return '-'
    cpu_usage_bar.short_description = 'CPU Usage'
    
    def usage_bars(self, obj):
        html = '<div style="margin-bottom: 10px;">'
        
        # CPU
        if obj.cpu_usage:
            cpu_color = 'danger' if obj.cpu_usage > 80 else 'warning' if obj.cpu_usage > 60 else 'success'
            html += f'<div><strong>CPU:</strong> {obj.cpu_usage}%</div>'
            html += f'<div class="progress" style="height: 20px; margin-bottom: 10px;">'
            html += f'<div class="progress-bar bg-{cpu_color}" role="progressbar" style="width: {obj.cpu_usage}%;"></div>'
            html += f'</div>'
        
        # Memory
        if obj.memory_usage:
            mem_color = 'danger' if obj.memory_usage > 80 else 'warning' if obj.memory_usage > 60 else 'success'
            html += f'<div><strong>Memory:</strong> {obj.memory_usage}%</div>'
            html += f'<div class="progress" style="height: 20px; margin-bottom: 10px;">'
            html += f'<div class="progress-bar bg-{mem_color}" role="progressbar" style="width: {obj.memory_usage}%;"></div>'
            html += f'</div>'
        
        # Disk
        if obj.disk_usage:
            disk_color = 'danger' if obj.disk_usage > 80 else 'warning' if obj.disk_usage > 60 else 'success'
            html += f'<div><strong>Disk:</strong> {obj.disk_usage}%</div>'
            html += f'<div class="progress" style="height: 20px;">'
            html += f'<div class="progress-bar bg-{disk_color}" role="progressbar" style="width: {obj.disk_usage}%;"></div>'
            html += f'</div>'
        
        html += '</div>'
        return format_html(html)
    usage_bars.short_description = 'Resource Usage'
    
    actions = ['test_connection', 'sync_all']
    
    def test_connection(self, request, queryset):
        success = 0
        for server in queryset:
            client = server.get_client()
            result = client.login()
            if result['success']:
                # Récupérer le statut système
                status_result = client.get_system_status()
                if status_result['success']:
                    status_data = status_result.get('status', {})
                    server.version = status_data.get('version', '')
                    server.cpu_usage = status_data.get('cpu', 0)
                    server.memory_usage = status_data.get('memory', 0)
                    server.disk_usage = status_data.get('disk', 0)
                server.last_sync_at = timezone.now()
                server.save()
                success += 1
        self.message_user(request, f"{success}/{queryset.count()} servers connected successfully")
    test_connection.short_description = "Test connection"
    
    def sync_all(self, request, queryset):
        for server in queryset:
            client = server.get_client()
            # Cette action serait implémentée avec des tâches Celery
        self.message_user(request, "Sync started for selected servers")
    sync_all.short_description = "Sync all data"


# ============================================================================
# LABORATOIRES EVE-NG
# ============================================================================

@admin.register(EVENLab)
class EVENLabAdmin(ImportExportModelAdmin):
    """Admin pour les laboratoires EVE-NG"""
    list_display = [
        'name_display', 'server_link', 'lab_path', 'status_badge',
        'node_count', 'link_count', 'is_active'
    ]
    list_filter = ['status', 'is_active', 'server']
    search_fields = ['name', 'description', 'lab_path']
    readonly_fields = ['id', 'created_at', 'updated_at', 'synced_at',
                      'node_count', 'link_count', 'network_count',
                      'topology_preview']
    raw_id_fields = ['server', 'created_by']
    inlines = [EVENNodeInline, EVENNetworkInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('server', 'lab_path', 'name', 'description', 'is_active')
        }),
        ('Status', {
            'fields': ('status', 'node_count', 'link_count', 'network_count')
        }),
        ('Configuration', {
            'fields': ('config',),
            'classes': ('collapse',)
        }),
        ('Topology', {
            'fields': ('topology_preview',),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('lab_id', 'filename', 'folder'),
            'classes': ('collapse',)
        }),
        ('Synchronization', {
            'fields': ('synced_at',),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_by', 'id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def name_display(self, obj):
        url = reverse('admin:eveng_app_evenlab_change', args=[obj.id])
        return format_html('<a href="{}"><strong>{}</strong></a>', url, obj.name)
    name_display.short_description = 'Name'
    
    def server_link(self, obj):
        url = reverse('admin:eveng_app_even_server_change', args=[obj.server.id])
        return format_html('<a href="{}">{}</a>', url, obj.server.name)
    server_link.short_description = 'Server'
    
    def status_badge(self, obj):
        colors = {
            'running': 'success',
            'stopped': 'secondary',
            'building': 'warning',
            'error': 'danger',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_status_display())
    status_badge.short_description = 'Status'
    
    def topology_preview(self, obj):
        if obj.topology:
            return format_html('<pre style="background-color: #f8f9fa; padding: 10px;">{}</pre>',
                             json.dumps(obj.topology, indent=2)[:2000])
        return '-'
    topology_preview.short_description = 'Topology Preview'


# ============================================================================
# NŒUDS EVE-NG
# ============================================================================

@admin.register(EVENNode)
class EVENNodeAdmin(ImportExportModelAdmin):
    """Admin pour les nœuds EVE-NG"""
    list_display = [
        'name', 'lab_link', 'node_id', 'node_type', 'status_badge',
        'cpu', 'ram', 'console_port'
    ]
    list_filter = ['node_type', 'status', 'lab__server']
    search_fields = ['name', 'image', 'template']
    readonly_fields = ['id', 'created_at', 'updated_at', 'interfaces_preview']
    raw_id_fields = ['lab']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('lab', 'node_id', 'name', 'node_type')
        }),
        ('Image & Template', {
            'fields': ('image', 'template')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Hardware', {
            'fields': ('cpu', 'ram', 'ethernet')
        }),
        ('Console', {
            'fields': ('console', 'console_type', 'console_port')
        }),
        ('Position', {
            'fields': ('position_x', 'position_y'),
            'classes': ('collapse',)
        }),
        ('Interfaces', {
            'fields': ('interfaces_preview',),
            'classes': ('collapse',)
        }),
        ('Configuration', {
            'fields': ('config',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('url', 'id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def lab_link(self, obj):
        url = reverse('admin:eveng_app_evenlab_change', args=[obj.lab.id])
        return format_html('<a href="{}">{}</a>', url, obj.lab.name)
    lab_link.short_description = 'Lab'
    
    def status_badge(self, obj):
        colors = {
            'running': 'success',
            'stopped': 'secondary',
            'building': 'warning',
            'error': 'danger',
            'unknown': 'info',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_status_display())
    status_badge.short_description = 'Status'
    
    def interfaces_preview(self, obj):
        if obj.interfaces:
            return format_html('<pre style="background-color: #f8f9fa; padding: 10px;">{}</pre>',
                             json.dumps(obj.interfaces, indent=2))
        return '-'
    interfaces_preview.short_description = 'Interfaces'


# ============================================================================
# RÉSEAUX EVE-NG
# ============================================================================

@admin.register(EVENNetwork)
class EVENNetworkAdmin(ImportExportModelAdmin):
    """Admin pour les réseaux EVE-NG"""
    list_display = ['name', 'lab_link', 'network_id', 'network_type', 'count']
    list_filter = ['network_type', 'lab__server']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['lab']
    
    def lab_link(self, obj):
        url = reverse('admin:eveng_app_evenlab_change', args=[obj.lab.id])
        return format_html('<a href="{}">{}</a>', url, obj.lab.name)
    lab_link.short_description = 'Lab'


# ============================================================================
# LIENS EVE-NG
# ============================================================================

@admin.register(EVENLink)
class EVENLinkAdmin(ImportExportModelAdmin):
    """Admin pour les liens EVE-NG"""
    list_display = [
        'id', 'lab_link', 'source_info', 'destination_info', 'link_type'
    ]
    list_filter = ['link_type', 'lab__server']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['lab', 'source_node', 'destination_node']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('lab', 'link_type')
        }),
        ('Source', {
            'fields': ('source_node', 'source_label', 'source_interface')
        }),
        ('Destination', {
            'fields': ('destination_node', 'destination_label', 'destination_interface')
        }),
        ('Style', {
            'fields': ('color', 'width'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def lab_link(self, obj):
        url = reverse('admin:eveng_app_evenlab_change', args=[obj.lab.id])
        return format_html('<a href="{}">{}</a>', url, obj.lab.name)
    lab_link.short_description = 'Lab'
    
    def source_info(self, obj):
        return f"{obj.source_node.name} {obj.source_label or ''}".strip()
    source_info.short_description = 'Source'
    
    def destination_info(self, obj):
        return f"{obj.destination_node.name} {obj.destination_label or ''}".strip()
    destination_info.short_description = 'Destination'


# ============================================================================
# IMAGES EVE-NG
# ============================================================================

@admin.register(EVENImage)
class EVENImageAdmin(ImportExportModelAdmin):
    """Admin pour les images EVE-NG"""
    list_display = [
        'name', 'server_link', 'image_type', 'version',
        'size_mb', 'default_ram', 'synced_at'
    ]
    list_filter = ['image_type', 'server']
    search_fields = ['name', 'description', 'version']
    readonly_fields = ['id', 'created_at', 'updated_at', 'synced_at', 'size_mb']
    raw_id_fields = ['server']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('server', 'name', 'image_type', 'description')
        }),
        ('File', {
            'fields': ('path', 'version', 'size_mb')
        }),
        ('Default Hardware', {
            'fields': ('default_cpu', 'default_ram', 'default_ethernet')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'synced_at'),
            'classes': ('collapse',)
        }),
    )
    
    def server_link(self, obj):
        url = reverse('admin:eveng_app_even_server_change', args=[obj.server.id])
        return format_html('<a href="{}">{}</a>', url, obj.server.name)
    server_link.short_description = 'Server'


# ============================================================================
# SESSIONS UTILISATEURS
# ============================================================================

@admin.register(EVENUserSession)
class EVENUserSessionAdmin(ImportExportModelAdmin):
    """Admin pour les sessions utilisateurs"""
    list_display = [
        'user_email', 'server_link', 'logged_in_at',
        'last_activity_at', 'expires_at', 'is_active'
    ]
    list_filter = ['is_active', 'server']
    search_fields = ['user__email', 'session_id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'logged_in_at',
                      'last_activity_at', 'session_id']
    raw_id_fields = ['server', 'user']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('server', 'user', 'session_id', 'is_active')
        }),
        ('Timing', {
            'fields': ('logged_in_at', 'last_activity_at', 'expires_at')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'
    
    def server_link(self, obj):
        url = reverse('admin:eveng_app_even_server_change', args=[obj.server.id])
        return format_html('<a href="{}">{}</a>', url, obj.server.name)
    server_link.short_description = 'Server'
