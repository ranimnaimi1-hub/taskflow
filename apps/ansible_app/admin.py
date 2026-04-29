# apps/ansible_app/admin.py
"""
Ansible App Admin - Interface d'administration ultra professionnelle
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from import_export.admin import ImportExportModelAdmin

# Better practice: import models explicitly
from .models import (
    AnsibleInventory, Playbook, PlaybookExecution, PlaybookSchedule,
    AnsibleRole, AnsibleCollection, AnsibleTask, AnsibleVars, AnsibleCredential
)


# ============================================================================
# INVENTAIRES ANSIBLE
# ============================================================================

class PlaybookInline(admin.TabularInline):
    model = Playbook
    fk_name = 'inventory'
    extra = 0
    fields = ['name', 'status', 'version', 'execution_count']
    readonly_fields = ['execution_count']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(AnsibleInventory)  # 👈 ADD THIS DECORATOR
class AnsibleInventoryAdmin(ImportExportModelAdmin):
    list_display = [
        'name_display', 'inventory_type_badge', 'format_badge', 
        'hosts_count_display', 'is_active_badge', 'created_at'
    ]
    list_filter = ['inventory_type', 'format', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'hosts_count_display']
    filter_horizontal = ['devices', 'sites', 'clusters', 'tenants']
    inlines = [PlaybookInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'inventory_type', 'format', 'is_active')
        }),
        ('Content', {
            'fields': ('content', 'variables'),
            'classes': ('wide',),
            'description': 'Pour inventaire statique, remplissez le contenu. Pour inventaire dynamique, utilisez les associations ci-dessous.'
        }),
        ('Dynamic Sources', {
            'fields': ('source_script', 'source_url'),
            'classes': ('collapse',)
        }),
        ('📡 Inventory Associations', {
            'fields': ('devices', 'sites', 'clusters', 'tenants', 'device_filters'),
            'classes': ('wide',),
            'description': 'Sélectionnez les ressources à inclure dans l\'inventaire'
        }),
        ('Files', {
            'fields': ('vars_file',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def name_display(self, obj):
        url = reverse('admin:ansible_app_ansibleinventory_change', args=[obj.id])
        return format_html('<a href="{}"><strong>{}</strong></a>', url, obj.name)
    name_display.short_description = 'Name'
    
    def inventory_type_badge(self, obj):
        colors = {
            'static': '#6c757d',
            'dynamic': '#28a745',
            'file': '#17a2b8',
            'script': '#ffc107',
        }
        color = colors.get(obj.inventory_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_inventory_type_display()
        )
    inventory_type_badge.short_description = 'Type'
    
    def format_badge(self, obj):
        colors = {
            'ini': '#6c757d',
            'yaml': '#dc3545',
            'json': '#28a745',
        }
        color = colors.get(obj.format, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_format_display().upper()
        )
    format_badge.short_description = 'Format'
    
    def hosts_count_display(self, obj):
        count = obj.get_hosts_count()
        return format_html('<span class="badge badge-info">{}</span>', count)
    hosts_count_display.short_description = 'Hosts'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: #28a745;">✓ Active</span>')
        return format_html('<span style="color: #dc3545;">✗ Inactive</span>')
    is_active_badge.short_description = 'Status'
    
    actions = ['sync_inventories', 'generate_inventory_files']
    
    def sync_inventories(self, request, queryset):
        for inventory in queryset:
            inventory.sync_from_inventory()
        self.message_user(request, f"{queryset.count()} inventories synchronized")
    sync_inventories.short_description = "Sync inventories from device associations"
    
    def generate_inventory_files(self, request, queryset):
        for inventory in queryset:
            inventory.content = inventory.generate_inventory_content()
            inventory.save()
        self.message_user(request, f"{queryset.count()} inventory files generated")
    generate_inventory_files.short_description = "Generate inventory files"


# ============================================================================
# PLAYBOOKS
# ============================================================================

class PlaybookExecutionInline(admin.TabularInline):
    model = PlaybookExecution
    extra = 0
    fields = ['status_badge', 'started_at', 'completed_at', 'duration_display']
    readonly_fields = ['status_badge', 'started_at', 'completed_at', 'duration_display']
    can_delete = False
    
    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'running': 'info',
            'completed': 'success',
            'failed': 'danger',
            'cancelled': 'secondary',
            'timeout': 'danger'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(f'<span class="badge badge-{color}">{{}}</span>', obj.get_status_display())
    status_badge.short_description = 'Status'
    
    def duration_display(self, obj):
        if obj.duration:
            if obj.duration < 60:
                return f"{obj.duration:.1f}s"
            return f"{obj.duration/60:.1f}m"
        return '-'
    duration_display.short_description = 'Duration'


class RoleInline(admin.TabularInline):
    model = Playbook.roles.through
    extra = 0
    verbose_name = "Role"
    verbose_name_plural = "Roles"


@admin.register(Playbook)  # 👈 ADD THIS DECORATOR
class PlaybookAdmin(ImportExportModelAdmin):
    list_display = [
        'name_display', 'version', 'status_badge', 'visibility_badge',
        'inventory_link', 'success_rate_display', 'execution_count', 'created_at'
    ]
    list_filter = ['status', 'visibility', 'created_at']
    search_fields = ['name', 'description', 'tags']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'execution_count', 
        'success_count', 'failure_count', 'avg_duration', 'success_rate'
    ]
    filter_horizontal = ['allowed_users']
    raw_id_fields = ['inventory', 'default_inventory', 'created_by']
    inlines = [PlaybookExecutionInline, RoleInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'version', 'status', 'visibility')
        }),
        ('📝 Playbook Content', {
            'fields': ('content', 'requirements'),
            'classes': ('wide',),
            'description': 'YAML content of the playbook'
        }),
        ('⚙️ Configuration', {
            'fields': ('inventory', 'default_inventory', 'timeout', 'forks', 'tags'),
            'classes': ('collapse',)
        }),
        ('Files', {
            'fields': ('playbook_file', 'vars_file'),
            'classes': ('collapse',)
        }),
        ('👥 Access Control', {
            'fields': ('allowed_users',),
            'classes': ('collapse',),
            'description': 'Users allowed to access this playbook (for shared visibility)'
        }),
        ('📊 Statistics', {
            'fields': ('execution_count', 'success_count', 'failure_count', 'avg_duration', 'success_rate'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def name_display(self, obj):
        url = reverse('admin:ansible_app_playbook_change', args=[obj.id])
        return format_html('<a href="{}"><strong>{}</strong></a>', url, obj.name)
    name_display.short_description = 'Name'
    
    def status_badge(self, obj):
        colors = {
            'draft': 'secondary',
            'active': 'success',
            'archived': 'warning',
            'deprecated': 'danger',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(f'<span class="badge badge-{color}">{{}}</span>', obj.get_status_display())
    status_badge.short_description = 'Status'
    
    def visibility_badge(self, obj):
        colors = {
            'private': 'danger',
            'team': 'warning',
            'shared': 'info',
            'public': 'success',
        }
        color = colors.get(obj.visibility, 'secondary')
        return format_html(f'<span class="badge badge-{color}">{{}}</span>', obj.get_visibility_display())
    visibility_badge.short_description = 'Visibility'
    
    def inventory_link(self, obj):
        if obj.inventory:
            url = reverse('admin:ansible_app_ansibleinventory_change', args=[obj.inventory.id])
            return format_html('<a href="{}">{}</a>', url, obj.inventory.name)
        return '-'
    inventory_link.short_description = 'Inventory'
    
    def success_rate_display(self, obj):
        rate = obj.success_rate
        color = '#28a745' if rate > 80 else '#ffc107' if rate > 50 else '#dc3545'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color, rate
        )
    success_rate_display.short_description = 'Success Rate'
    
    actions = ['validate_playbooks', 'export_as_yaml']
    
    def validate_playbooks(self, request, queryset):
        valid_count = 0
        for playbook in queryset:
            is_valid, msg = playbook.validate_yaml()
            if is_valid:
                valid_count += 1
        self.message_user(request, f"{valid_count}/{queryset.count()} playbooks have valid YAML syntax")
    validate_playbooks.short_description = "Validate YAML syntax"
    
    def export_as_yaml(self, request, queryset):
        import yaml
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/yaml')
        response['Content-Disposition'] = 'attachment; filename="playbooks.yaml"'
        
        data = []
        for playbook in queryset:
            try:
                data.append(yaml.safe_load(playbook.content))
            except:
                data.append({"name": playbook.name, "error": "Invalid YAML"})
        
        response.write(yaml.dump(data, default_flow_style=False))
        return response
    export_as_yaml.short_description = "Export as YAML"


# ============================================================================
# PLAYBOOK EXECUTIONS
# ============================================================================

@admin.register(PlaybookExecution)  # 👈 ADD THIS DECORATOR
class PlaybookExecutionAdmin(ImportExportModelAdmin):
    list_display = [
        'id_short', 'playbook_link', 'status_badge', 'executed_by', 
        'duration_display', 'started_at', 'return_code_display'
    ]
    list_filter = ['status', 'check_mode', 'created_at']
    search_fields = ['playbook__name', 'executed_by__email']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'started_at', 'completed_at',
        'duration', 'output', 'error_output', 'summary', 'facts',
        'return_code', 'command', 'inventory_snapshot', 'host_results'
    ]
    raw_id_fields = ['playbook', 'inventory', 'executed_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('playbook', 'inventory', 'status', 'executed_by')
        }),
        ('📋 Inventory Snapshot', {
            'fields': ('inventory_snapshot',),
            'classes': ('collapse',)
        }),
        ('⚙️ Execution Configuration', {
            'fields': ('extra_vars', 'limit', 'tags', 'skip_tags', 'check_mode', 'diff_mode'),
            'classes': ('collapse',)
        }),
        ('⏱️ Timing', {
            'fields': ('started_at', 'completed_at', 'duration'),
            'classes': ('collapse',)
        }),
        ('📊 Results', {
            'fields': ('return_code', 'summary', 'facts', 'host_results'),
            'classes': ('collapse',)
        }),
        ('📝 Output', {
            'fields': ('output', 'error_output'),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('command', 'execution_host', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def id_short(self, obj):
        return str(obj.id)[:8] + "..."
    id_short.short_description = 'ID'
    
    def playbook_link(self, obj):
        url = reverse('admin:ansible_app_playbook_change', args=[obj.playbook.id])
        return format_html('<a href="{}">{}</a>', url, obj.playbook.name)
    playbook_link.short_description = 'Playbook'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'running': 'info',
            'completed': 'success',
            'failed': 'danger',
            'cancelled': 'secondary',
            'timeout': 'danger'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(f'<span class="badge badge-{color}">{{}}</span>', obj.get_status_display())
    status_badge.short_description = 'Status'
    
    def duration_display(self, obj):
        if obj.duration:
            if obj.duration < 60:
                return f"{obj.duration:.1f}s"
            elif obj.duration < 3600:
                return f"{obj.duration/60:.1f}m"
            else:
                return f"{obj.duration/3600:.1f}h"
        return '-'
    duration_display.short_description = 'Duration'
    
    def return_code_display(self, obj):
        if obj.return_code == 0:
            return format_html('<span style="color: #28a745;">✓ Success</span>')
        elif obj.return_code:
            return format_html('<span style="color: #dc3545;">✗ Failed ({})</span>', obj.return_code)
        return '-'
    return_code_display.short_description = 'Return Code'


# ============================================================================
# PLAYBOOK SCHEDULES
# ============================================================================

@admin.register(PlaybookSchedule)  # 👈 ADD THIS DECORATOR
class PlaybookScheduleAdmin(ImportExportModelAdmin):
    list_display = [
        'name', 'playbook_link', 'schedule_type_badge', 'status_badge',
        'next_run', 'execution_count', 'created_by'
    ]
    list_filter = ['status', 'schedule_type']
    search_fields = ['name', 'playbook__name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_run', 'next_run', 'execution_count']
    raw_id_fields = ['playbook', 'inventory', 'created_by', 'last_execution']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'playbook', 'inventory', 'status')
        }),
        ('⏰ Schedule Configuration', {
            'fields': ('schedule_type', 'cron_expression', 'start_date', 'end_date'),
            'description': 'Configure when the playbook should run'
        }),
        ('⚙️ Execution Configuration', {
            'fields': ('extra_vars', 'limit', 'tags', 'check_mode'),
            'classes': ('collapse',)
        }),
        ('📧 Notifications', {
            'fields': ('notify_on_success', 'notify_on_failure', 'notification_emails'),
            'classes': ('collapse',)
        }),
        ('📊 Execution History', {
            'fields': ('last_run', 'next_run', 'execution_count', 'last_execution'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def playbook_link(self, obj):
        url = reverse('admin:ansible_app_playbook_change', args=[obj.playbook.id])
        return format_html('<a href="{}">{}</a>', url, obj.playbook.name)
    playbook_link.short_description = 'Playbook'
    
    def schedule_type_badge(self, obj):
        colors = {
            'once': 'secondary',
            'hourly': 'info',
            'daily': 'success',
            'weekly': 'warning',
            'monthly': 'primary',
            'cron': 'danger',
        }
        color = colors.get(obj.schedule_type, 'secondary')
        return format_html(f'<span class="badge badge-{color}">{{}}</span>', obj.get_schedule_type_display())
    schedule_type_badge.short_description = 'Type'
    
    def status_badge(self, obj):
        colors = {
            'active': 'success',
            'paused': 'warning',
            'completed': 'info',
            'failed': 'danger',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(f'<span class="badge badge-{color}">{{}}</span>', obj.get_status_display())
    status_badge.short_description = 'Status'


# ============================================================================
# RÔLES ANSIBLE
# ============================================================================

@admin.register(AnsibleRole)  # 👈 ADD THIS DECORATOR
class AnsibleRoleAdmin(ImportExportModelAdmin):
    list_display = ['name', 'namespace', 'version', 'source_badge', 'download_count', 'used_in_playbooks']
    list_filter = ['source', 'namespace']
    search_fields = ['name', 'namespace', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'download_count', 'used_in_playbooks']
    filter_horizontal = ['playbooks']
    
    def source_badge(self, obj):
        colors = {
            'local': 'secondary',
            'galaxy': 'success',
            'git': 'warning',
        }
        color = colors.get(obj.source, 'secondary')
        return format_html(f'<span class="badge badge-{color}">{{}}</span>', obj.get_source_display())
    source_badge.short_description = 'Source'


# ============================================================================
# COLLECTIONS ANSIBLE
# ============================================================================

@admin.register(AnsibleCollection)  # 👈 ADD THIS DECORATOR
class AnsibleCollectionAdmin(ImportExportModelAdmin):
    list_display = ['name', 'namespace', 'version', 'installed_at']
    list_filter = ['namespace']
    search_fields = ['name', 'namespace', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'installed_at']
    filter_horizontal = ['playbooks']


# ============================================================================
# TÂCHES ANSIBLE
# ============================================================================

@admin.register(AnsibleTask)  # 👈 ADD THIS DECORATOR
class AnsibleTaskAdmin(ImportExportModelAdmin):
    list_display = ['name', 'playbooks_count', 'created_by', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    filter_horizontal = ['playbooks']
    raw_id_fields = ['created_by']
    
    def playbooks_count(self, obj):
        return obj.playbooks.count()
    playbooks_count.short_description = 'Playbooks'


# ============================================================================
# VARIABLES ANSIBLE
# ============================================================================

@admin.register(AnsibleVars)  # 👈 ADD THIS DECORATOR
class AnsibleVarsAdmin(ImportExportModelAdmin):
    list_display = ['name', 'tenant_link', 'inventory_link', 'playbook_link', 'created_by']
    list_filter = ['tenant']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['inventory', 'playbook', 'tenant', 'created_by']
    
    def tenant_link(self, obj):
        if obj.tenant:
            url = reverse('admin:inventory_tenant_change', args=[obj.tenant.id])
            return format_html('<a href="{}">{}</a>', url, obj.tenant.name)
        return '-'
    tenant_link.short_description = 'Tenant'
    
    def inventory_link(self, obj):
        if obj.inventory:
            url = reverse('admin:ansible_app_ansibleinventory_change', args=[obj.inventory.id])
            return format_html('<a href="{}">{}</a>', url, obj.inventory.name)
        return '-'
    inventory_link.short_description = 'Inventory'
    
    def playbook_link(self, obj):
        if obj.playbook:
            url = reverse('admin:ansible_app_playbook_change', args=[obj.playbook.id])
            return format_html('<a href="{}">{}</a>', url, obj.playbook.name)
        return '-'
    playbook_link.short_description = 'Playbook'


# ============================================================================
# CREDENTIALS ANSIBLE
# ============================================================================

@admin.register(AnsibleCredential)  # 👈 ADD THIS DECORATOR
class AnsibleCredentialAdmin(ImportExportModelAdmin):
    list_display = ['name', 'credential_type_badge', 'username', 'playbooks_count', 'inventories_count']
    list_filter = ['credential_type']
    search_fields = ['name', 'username', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    filter_horizontal = ['playbooks', 'inventories']
    raw_id_fields = ['created_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'credential_type', 'description')
        }),
        ('🔐 Credentials', {
            'fields': ('username', 'password', 'ssh_key', 'ssh_key_passphrase'),
            'classes': ('wide',)
        }),
        ('🔑 Vault & Cloud', {
            'fields': ('vault_password', 'access_key', 'secret_key'),
            'classes': ('collapse',)
        }),
        ('Associations', {
            'fields': ('playbooks', 'inventories'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def credential_type_badge(self, obj):
        colors = {
            'ssh': 'success',
            'password': 'warning',
            'vault': 'danger',
            'network': 'info',
            'cloud': 'primary',
        }
        color = colors.get(obj.credential_type, 'secondary')
        return format_html(f'<span class="badge badge-{color}">{{}}</span>', obj.get_credential_type_display())
    credential_type_badge.short_description = 'Type'
    
    def playbooks_count(self, obj):
        return obj.playbooks.count()
    playbooks_count.short_description = 'Playbooks'
    
    def inventories_count(self, obj):
        return obj.inventories.count()
    inventories_count.short_description = 'Inventories'