"""
Grafana App Admin - Interface d'administration professionnelle
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from import_export.admin import ImportExportModelAdmin
import json

from .models import (
    GrafanaServer, GrafanaDashboard, GrafanaDatasource, GrafanaAlert,
    GrafanaOrganization, GrafanaUser, GrafanaFolder, GrafanaPanel,
    GrafanaSnapshot, GrafanaTeam
)


# ============================================================================
# INLINES
# ============================================================================

class GrafanaDashboardInline(admin.TabularInline):
    """Inline pour les dashboards dans le serveur"""
    model = GrafanaDashboard
    extra = 0
    fields = ['title_link', 'dashboard_uid', 'version', 'is_active']
    readonly_fields = ['title_link', 'dashboard_uid', 'version']
    can_delete = False
    
    def title_link(self, obj):
        url = reverse('admin:grafana_app_grafanadashboard_change', args=[obj.id])
        return format_html('<a href="{}">{}</a>', url, obj.title)
    title_link.short_description = 'Title'
    
    def has_add_permission(self, request, obj=None):
        return False


class GrafanaDatasourceInline(admin.TabularInline):
    """Inline pour les datasources dans le serveur"""
    model = GrafanaDatasource
    extra = 0
    fields = ['name_link', 'type', 'is_default', 'is_active']
    readonly_fields = ['name_link', 'type', 'is_default']
    can_delete = False
    
    def name_link(self, obj):
        url = reverse('admin:grafana_app_grafanadatasource_change', args=[obj.id])
        return format_html('<a href="{}">{}</a>', url, obj.name)
    name_link.short_description = 'Name'
    
    def has_add_permission(self, request, obj=None):
        return False


class GrafanaAlertInline(admin.TabularInline):
    """Inline pour les alertes dans le serveur"""
    model = GrafanaAlert
    extra = 0
    fields = ['name', 'state_badge', 'severity_badge', 'new_state_date']
    readonly_fields = ['name', 'state_badge', 'severity_badge', 'new_state_date']
    can_delete = False
    
    def state_badge(self, obj):
        colors = {
            'pending': 'warning',
            'firing': 'danger',
            'resolved': 'success',
            'paused': 'secondary',
            'unknown': 'info',
        }
        color = colors.get(obj.state, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_state_display())
    state_badge.short_description = 'State'
    
    def severity_badge(self, obj):
        colors = {
            'critical': 'danger',
            'high': 'warning',
            'medium': 'info',
            'low': 'success',
            'info': 'primary',
        }
        color = colors.get(obj.severity, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_severity_display())
    severity_badge.short_description = 'Severity'
    
    def has_add_permission(self, request, obj=None):
        return False


class GrafanaPanelInline(admin.TabularInline):
    """Inline pour les panels dans le dashboard"""
    model = GrafanaPanel
    extra = 0
    fields = ['panel_id', 'title', 'type', 'preview']
    readonly_fields = ['panel_id', 'title', 'type', 'preview']
    can_delete = False
    
    def preview(self, obj):
        if obj.type:
            icons = {
                'graph': '📈',
                'stat': '📊',
                'table': '📋',
                'singlestat': '🔢',
                'text': '📝',
                'heatmap': '🔥',
                'gauge': '🌡️',
            }
            icon = icons.get(obj.type, '📊')
            return f"{icon} {obj.type}"
        return '-'
    preview.short_description = 'Preview'
    
    def has_add_permission(self, request, obj=None):
        return False


# ============================================================================
# SERVEURS GRAFANA
# ============================================================================

@admin.register(GrafanaServer)
class GrafanaServerAdmin(ImportExportModelAdmin):
    """Admin pour les serveurs Grafana"""
    list_display = [
        'name_display', 'url', 'status_badge', 'version',
        'dashboards_count', 'datasources_count', 'alerts_count', 'last_sync_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'description', 'url']
    readonly_fields = ['id', 'created_at', 'updated_at', 'version', 'last_sync_at']
    autocomplete_fields = ['created_by']
    inlines = [GrafanaDashboardInline, GrafanaDatasourceInline, GrafanaAlertInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'url', 'status')
        }),
        ('Authentication', {
            'fields': ('api_key', 'username', 'password'),
            'classes': ('wide',)
        }),
        ('Configuration', {
            'fields': ('timeout',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('version', 'last_sync_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def name_display(self, obj):
        url = reverse('admin:grafana_app_grafanaserver_change', args=[obj.id])
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
    
    def dashboards_count(self, obj):
        count = obj.dashboards.count()
        return format_html('<span class="badge badge-info">{}</span>', count)
    dashboards_count.short_description = 'Dashboards'
    
    def datasources_count(self, obj):
        count = obj.datasources.count()
        return format_html('<span class="badge badge-success">{}</span>', count)
    datasources_count.short_description = 'Datasources'
    
    def alerts_count(self, obj):
        count = obj.alerts.filter(state='firing').count()
        if count > 0:
            return format_html('<span class="badge badge-danger">{}</span>', count)
        return format_html('<span class="badge badge-secondary">0</span>', count)
    alerts_count.short_description = 'Alerts'
    
    actions = ['test_connection', 'sync_all']
    
    def test_connection(self, request, queryset):
        success = 0
        for server in queryset:
            client = server.get_client()
            result = client.get_health()
            if result['success']:
                server.version = result.get('data', {}).get('version', '')
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
# DASHBOARDS GRAFANA
# ============================================================================

@admin.register(GrafanaDashboard)
class GrafanaDashboardAdmin(ImportExportModelAdmin):
    """Admin pour les dashboards Grafana"""
    list_display = [
        'title_display', 'server_link', 'version', 'panels_count',
        'is_active_badge', 'updated_at'
    ]
    list_filter = ['is_active', 'server']
    search_fields = ['title', 'description', 'dashboard_uid']
    readonly_fields = ['id', 'created_at', 'updated_at', 'synced_at', 'version', 'dashboard_preview']
    autocomplete_fields = ['server', 'created_by']
    inlines = [GrafanaPanelInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('server', 'dashboard_uid', 'title', 'description', 'is_active')
        }),
        ('Metadata', {
            'fields': ('version', 'url', 'slug', 'tags'),
            'classes': ('collapse',)
        }),
        ('JSON Preview', {
            'fields': ('dashboard_preview',),
            'classes': ('wide',)
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
    
    def title_display(self, obj):
        url = reverse('admin:grafana_app_grafanadashboard_change', args=[obj.id])
        return format_html('<a href="{}"><strong>{}</strong></a>', url, obj.title)
    title_display.short_description = 'Title'
    
    def server_link(self, obj):
        url = reverse('admin:grafana_app_grafanaserver_change', args=[obj.server.id])
        return format_html('<a href="{}">{}</a>', url, obj.server.name)
    server_link.short_description = 'Server'
    
    def panels_count(self, obj):
        count = obj.panels.count()
        return format_html('<span class="badge badge-info">{}</span>', count)
    panels_count.short_description = 'Panels'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="badge badge-success">Active</span>')
        return format_html('<span class="badge badge-secondary">Inactive</span>')
    is_active_badge.short_description = 'Status'
    
    def dashboard_preview(self, obj):
        if obj.dashboard_json:
            preview = json.dumps(obj.dashboard_json, indent=2)[:2000]
            return format_html('<pre style="background-color: #f8f9fa; padding: 10px;">{}</pre>', preview)
        return '-'
    dashboard_preview.short_description = 'Dashboard JSON'


# ============================================================================
# DATASOURCES GRAFANA
# ============================================================================

@admin.register(GrafanaDatasource)
class GrafanaDatasourceAdmin(ImportExportModelAdmin):
    """Admin pour les sources de données Grafana"""
    list_display = [
        'name_display', 'server_link', 'type_badge', 'url',
        'is_default_badge', 'is_active_badge'
    ]
    list_filter = ['type', 'is_default', 'is_active', 'server']
    search_fields = ['name', 'url']
    readonly_fields = ['id', 'created_at', 'updated_at', 'synced_at', 'version']
    autocomplete_fields = ['server']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('server', 'datasource_uid', 'name', 'type', 'url', 'access')
        }),
        ('Options', {
            'fields': ('is_default', 'read_only', 'is_active')
        }),
        ('Authentication', {
            'fields': ('basic_auth', 'basic_auth_user', 'basic_auth_password', 'with_credentials'),
            'classes': ('collapse',)
        }),
        ('JSON Configuration', {
            'fields': ('json_data', 'secure_json_data'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('version', 'synced_at', 'id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def name_display(self, obj):
        url = reverse('admin:grafana_app_grafanadatasource_change', args=[obj.id])
        return format_html('<a href="{}"><strong>{}</strong></a>', url, obj.name)
    name_display.short_description = 'Name'
    
    def server_link(self, obj):
        url = reverse('admin:grafana_app_grafanaserver_change', args=[obj.server.id])
        return format_html('<a href="{}">{}</a>', url, obj.server.name)
    server_link.short_description = 'Server'
    
    def type_badge(self, obj):
        colors = {
            'prometheus': 'warning',
            'graphite': 'info',
            'influxdb': 'primary',
            'elasticsearch': 'danger',
            'mysql': 'info',
            'postgresql': 'info',
            'cloudwatch': 'success',
            'loki': 'purple',
            'tempo': 'purple',
        }
        color = colors.get(obj.type, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_type_display())
    type_badge.short_description = 'Type'
    
    def is_default_badge(self, obj):
        if obj.is_default:
            return format_html('<span class="badge badge-success">Default</span>')
        return '-'
    is_default_badge.short_description = 'Default'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="badge badge-success">Active</span>')
        return format_html('<span class="badge badge-secondary">Inactive</span>')
    is_active_badge.short_description = 'Status'


# ============================================================================
# ALERTES GRAFANA
# ============================================================================

@admin.register(GrafanaAlert)
class GrafanaAlertAdmin(ImportExportModelAdmin):
    """Admin pour les alertes Grafana"""
    list_display = [
        'name', 'server_link', 'dashboard_link', 'state_badge',
        'severity_badge', 'new_state_date'
    ]
    list_filter = ['state', 'severity', 'server']
    search_fields = ['name', 'message']
    readonly_fields = ['id', 'created_at', 'updated_at', 'synced_at', 'eval_data', 'execution_error']
    autocomplete_fields = ['server', 'dashboard', 'datasource']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('server', 'dashboard', 'datasource', 'alert_id', 'name', 'message')
        }),
        ('State', {
            'fields': ('state', 'severity', 'new_state_date', 'url')
        }),
        ('Timing', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
        ('Evaluation', {
            'fields': ('eval_data', 'execution_error'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'synced_at'),
            'classes': ('collapse',)
        }),
    )
    
    def server_link(self, obj):
        url = reverse('admin:grafana_app_grafanaserver_change', args=[obj.server.id])
        return format_html('<a href="{}">{}</a>', url, obj.server.name)
    server_link.short_description = 'Server'
    
    def dashboard_link(self, obj):
        if obj.dashboard:
            url = reverse('admin:grafana_app_grafanadashboard_change', args=[obj.dashboard.id])
            return format_html('<a href="{}">{}</a>', url, obj.dashboard.title)
        return '-'
    dashboard_link.short_description = 'Dashboard'
    
    def state_badge(self, obj):
        colors = {
            'pending': 'warning',
            'firing': 'danger',
            'resolved': 'success',
            'paused': 'secondary',
            'unknown': 'info',
        }
        color = colors.get(obj.state, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_state_display())
    state_badge.short_description = 'State'
    
    def severity_badge(self, obj):
        colors = {
            'critical': 'danger',
            'high': 'warning',
            'medium': 'info',
            'low': 'success',
            'info': 'primary',
        }
        color = colors.get(obj.severity, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_severity_display())
    severity_badge.short_description = 'Severity'


# ============================================================================
# ORGANISATIONS GRAFANA
# ============================================================================

@admin.register(GrafanaOrganization)
class GrafanaOrganizationAdmin(ImportExportModelAdmin):
    """Admin pour les organisations Grafana"""
    list_display = ['name', 'server_link', 'org_id', 'users_count', 'teams_count']
    list_filter = ['server']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'synced_at']
    autocomplete_fields = ['server']
    
    def server_link(self, obj):
        url = reverse('admin:grafana_app_grafanaserver_change', args=[obj.server.id])
        return format_html('<a href="{}">{}</a>', url, obj.server.name)
    server_link.short_description = 'Server'
    
    def users_count(self, obj):
        return obj.users.count()
    users_count.short_description = 'Users'
    
    def teams_count(self, obj):
        return obj.teams.count()
    teams_count.short_description = 'Teams'


# ============================================================================
# UTILISATEURS GRAFANA
# ============================================================================

@admin.register(GrafanaUser)
class GrafanaUserAdmin(ImportExportModelAdmin):
    """Admin pour les utilisateurs Grafana"""
    list_display = ['email', 'name', 'server_link', 'organization_link', 'role_badge', 'is_active']
    list_filter = ['role', 'is_active', 'is_disabled', 'server']
    search_fields = ['email', 'name', 'login']
    readonly_fields = ['id', 'created_at', 'updated_at', 'synced_at', 'last_seen_at']
    autocomplete_fields = ['server', 'organization']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('server', 'organization', 'user_id', 'email', 'name', 'login')
        }),
        ('Role & Status', {
            'fields': ('role', 'is_disabled', 'is_active')
        }),
        ('Profile', {
            'fields': ('avatar_url', 'last_seen_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'synced_at'),
            'classes': ('collapse',)
        }),
    )
    
    def server_link(self, obj):
        url = reverse('admin:grafana_app_grafanaserver_change', args=[obj.server.id])
        return format_html('<a href="{}">{}</a>', url, obj.server.name)
    server_link.short_description = 'Server'
    
    def organization_link(self, obj):
        if obj.organization:
            url = reverse('admin:grafana_app_grafanaorganization_change', args=[obj.organization.id])
            return format_html('<a href="{}">{}</a>', url, obj.organization.name)
        return '-'
    organization_link.short_description = 'Organization'
    
    def role_badge(self, obj):
        colors = {
            'Admin': 'danger',
            'Editor': 'warning',
            'Viewer': 'success',
        }
        color = colors.get(obj.role, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.role)
    role_badge.short_description = 'Role'


# ============================================================================
# FOLDERS GRAFANA
# ============================================================================

@admin.register(GrafanaFolder)
class GrafanaFolderAdmin(ImportExportModelAdmin):
    """Admin pour les dossiers Grafana"""
    list_display = ['title', 'server_link', 'folder_uid', 'version']
    list_filter = ['server']
    search_fields = ['title']
    readonly_fields = ['id', 'created_at', 'updated_at', 'synced_at']
    autocomplete_fields = ['server']
    
    def server_link(self, obj):
        url = reverse('admin:grafana_app_grafanaserver_change', args=[obj.server.id])
        return format_html('<a href="{}">{}</a>', url, obj.server.name)
    server_link.short_description = 'Server'


# ============================================================================
# PANELS GRAFANA
# ============================================================================

@admin.register(GrafanaPanel)
class GrafanaPanelAdmin(ImportExportModelAdmin):
    """Admin pour les panels Grafana"""
    list_display = ['panel_id', 'title', 'dashboard_link', 'type', 'preview']
    list_filter = ['type', 'dashboard__server']
    search_fields = ['title', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'panel_preview']
    autocomplete_fields = ['dashboard']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('dashboard', 'panel_id', 'title', 'type', 'description')
        }),
        ('Configuration', {
            'fields': ('grid_pos', 'targets', 'panel_preview'),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def dashboard_link(self, obj):
        url = reverse('admin:grafana_app_grafanadashboard_change', args=[obj.dashboard.id])
        return format_html('<a href="{}">{}</a>', url, obj.dashboard.title)
    dashboard_link.short_description = 'Dashboard'
    
    def preview(self, obj):
        icons = {
            'graph': '📈',
            'stat': '📊',
            'table': '📋',
            'singlestat': '🔢',
            'text': '📝',
            'heatmap': '🔥',
            'gauge': '🌡️',
        }
        icon = icons.get(obj.type, '📊')
        return f"{icon} {obj.type}"
    preview.short_description = 'Type'
    
    def panel_preview(self, obj):
        if obj.panel_json:
            return format_html('<pre style="background-color: #f8f9fa; padding: 10px;">{}</pre>',
                             json.dumps(obj.panel_json, indent=2)[:1000])
        return '-'
    panel_preview.short_description = 'Panel JSON'


# ============================================================================
# SNAPSHOTS GRAFANA
# ============================================================================

@admin.register(GrafanaSnapshot)
class GrafanaSnapshotAdmin(ImportExportModelAdmin):
    """Admin pour les snapshots Grafana"""
    list_display = ['name', 'server_link', 'dashboard_link', 'snapshot_key', 'expires_at']
    list_filter = ['server']
    search_fields = ['name', 'snapshot_key']
    readonly_fields = ['id', 'created_at', 'updated_at', 'snapshot_preview']
    autocomplete_fields = ['server', 'dashboard']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('server', 'dashboard', 'name', 'snapshot_key', 'snapshot_url')
        }),
        ('Details', {
            'fields': ('created_by', 'expires_at', 'snapshot_preview'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def server_link(self, obj):
        url = reverse('admin:grafana_app_grafanaserver_change', args=[obj.server.id])
        return format_html('<a href="{}">{}</a>', url, obj.server.name)
    server_link.short_description = 'Server'
    
    def dashboard_link(self, obj):
        if obj.dashboard:
            url = reverse('admin:grafana_app_grafanadashboard_change', args=[obj.dashboard.id])
            return format_html('<a href="{}">{}</a>', url, obj.dashboard.title)
        return '-'
    dashboard_link.short_description = 'Dashboard'
    
    def snapshot_preview(self, obj):
        if obj.snapshot_json:
            return format_html('<pre style="background-color: #f8f9fa; padding: 10px;">{}</pre>',
                             json.dumps(obj.snapshot_json, indent=2)[:1000])
        return '-'
    snapshot_preview.short_description = 'Snapshot JSON'


# ============================================================================
# TEAMS GRAFANA
# ============================================================================

@admin.register(GrafanaTeam)
class GrafanaTeamAdmin(ImportExportModelAdmin):
    """Admin pour les teams Grafana"""
    list_display = ['name', 'server_link', 'organization_link', 'email', 'member_count']
    list_filter = ['server']
    search_fields = ['name', 'email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'synced_at']
    autocomplete_fields = ['server', 'organization']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('server', 'organization', 'team_id', 'name', 'email')
        }),
        ('Stats', {
            'fields': ('member_count', 'permission')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'synced_at'),
            'classes': ('collapse',)
        }),
    )
    
    def server_link(self, obj):
        url = reverse('admin:grafana_app_grafanaserver_change', args=[obj.server.id])
        return format_html('<a href="{}">{}</a>', url, obj.server.name)
    server_link.short_description = 'Server'
    
    def organization_link(self, obj):
        if obj.organization:
            url = reverse('admin:grafana_app_grafanaorganization_change', args=[obj.organization.id])
            return format_html('<a href="{}">{}</a>', url, obj.organization.name)
        return '-'
    organization_link.short_description = 'Organization'