# apps/terraform_app/admin.py
"""
Terraform App Admin - Interface d'administration ultra professionnelle
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from import_export.admin import ImportExportModelAdmin
import json

from .models import (
    TerraformConfig, TerraformPlan, TerraformApply, TerraformState,
    TerraformModule, TerraformProvider, TerraformVariable, TerraformCredential
)


# ============================================================================
# INLINES
# ============================================================================

class TerraformPlanInline(admin.TabularInline):
    """Inline pour les plans dans la config"""
    model = TerraformPlan
    extra = 0
    fields = ['plan_id', 'status_badge', 'has_changes_badge', 'resources_summary', 'created_at']
    readonly_fields = ['plan_id', 'status_badge', 'has_changes_badge', 'resources_summary', 'created_at']
    can_delete = False
    ordering = ['-created_at']
    
    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'running': 'info',
            'completed': 'success',
            'failed': 'danger',
            'cancelled': 'secondary',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_status_display())
    status_badge.short_description = 'Status'
    
    def has_changes_badge(self, obj):
        if obj.has_changes:
            return format_html('<span class="badge badge-warning">Has Changes</span>')
        return format_html('<span class="badge badge-secondary">No Changes</span>')
    has_changes_badge.short_description = 'Changes'
    
    def resources_summary(self, obj):
        return f"+{obj.resources_add} ~{obj.resources_change} -{obj.resources_destroy}"
    resources_summary.short_description = 'Resources'
    
    def has_add_permission(self, request, obj=None):
        return False


class TerraformApplyInline(admin.TabularInline):
    """Inline pour les apply dans la config"""
    model = TerraformApply
    extra = 0
    fields = ['apply_id', 'status_badge', 'return_code_display', 'duration_display', 'created_at']
    readonly_fields = ['apply_id', 'status_badge', 'return_code_display', 'duration_display', 'created_at']
    can_delete = False
    ordering = ['-created_at']
    
    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'running': 'info',
            'completed': 'success',
            'failed': 'danger',
            'cancelled': 'secondary',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_status_display())
    status_badge.short_description = 'Status'
    
    def return_code_display(self, obj):
        if obj.return_code == 0:
            return format_html('<span style="color: #28a745;">✓ Success</span>')
        elif obj.return_code:
            return format_html('<span style="color: #dc3545;">✗ Failed ({})</span>', obj.return_code)
        return '-'
    return_code_display.short_description = 'Return Code'
    
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
    
    def has_add_permission(self, request, obj=None):
        return False


class TerraformStateInline(admin.TabularInline):
    """Inline pour les états dans la config"""
    model = TerraformState
    extra = 0
    fields = ['version', 'resources_count', 'captured_at']
    readonly_fields = ['version', 'resources_count', 'captured_at']
    can_delete = False
    ordering = ['-version']
    
    def has_add_permission(self, request, obj=None):
        return False


# ============================================================================
# CONFIGURATIONS TERRAFORM
# ============================================================================

@admin.register(TerraformConfig)
class TerraformConfigAdmin(ImportExportModelAdmin):
    """Admin pour les configurations Terraform"""
    list_display = [
        'name_display', 'provider_badge', 'status_badge', 
        'site_link', 'cluster_link', 'tenant_link',
        'apply_count', 'last_apply_status_badge', 'created_at'
    ]
    list_filter = ['provider', 'status', 'backend_type', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'apply_count', 
        'last_apply_status', 'last_apply_at', 'config_preview'
    ]
    filter_horizontal = ['allowed_users']
    raw_id_fields = ['site', 'cluster', 'tenant', 'created_by']
    inlines = [TerraformPlanInline, TerraformApplyInline, TerraformStateInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'provider', 'provider_version', 'version', 'status')
        }),
        ('Terraform Files', {
            'fields': ('main_tf', 'variables_tf', 'outputs_tf', 'terraform_tfvars'),
            'classes': ('wide',),
            'description': 'Main Terraform configuration files'
        }),
        ('Structured Variables', {
            'fields': ('variables', 'config_files'),
            'classes': ('collapse',),
            'description': 'Structured variables and additional files'
        }),
        ('Backend Configuration', {
            'fields': ('backend_type', 'backend_config'),
            'classes': ('collapse',)
        }),
        ('📍 Inventory Associations', {
            'fields': ('site', 'cluster', 'tenant'),
            'classes': ('wide',),
            'description': 'Associate with inventory resources'
        }),
        ('👥 Access Control', {
            'fields': ('created_by', 'allowed_users'),
            'classes': ('collapse',)
        }),
        ('📊 Statistics', {
            'fields': ('apply_count', 'last_apply_status', 'last_apply_at'),
            'classes': ('collapse',)
        }),
        ('📝 Preview', {
            'fields': ('config_preview',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def name_display(self, obj):
        url = reverse('admin:terraform_app_terraformconfig_change', args=[obj.id])
        return format_html('<a href="{}"><strong>{}</strong></a>', url, obj.name)
    name_display.short_description = 'Name'
    
    def provider_badge(self, obj):
        colors = {
            'aws': '#ff9900',
            'azure': '#0078d4',
            'gcp': '#4285f4',
            'openstack': '#da1a32',
            'vmware': '#1ba0d7',
            'proxmox': '#e57000',
            'kubernetes': '#326ce5',
            'docker': '#2496ed',
            'custom': '#6c757d',
        }
        color = colors.get(obj.provider, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_provider_display()
        )
    provider_badge.short_description = 'Provider'
    
    def status_badge(self, obj):
        colors = {
            'draft': 'secondary',
            'active': 'success',
            'archived': 'warning',
            'deprecated': 'danger',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_status_display())
    status_badge.short_description = 'Status'
    
    def last_apply_status_badge(self, obj):
        if obj.last_apply_status == 'completed':
            return format_html('<span style="color: #28a745;">✓ Success</span>')
        elif obj.last_apply_status == 'failed':
            return format_html('<span style="color: #dc3545;">✗ Failed</span>')
        return '-'
    last_apply_status_badge.short_description = 'Last Apply'
    
    def site_link(self, obj):
        if obj.site:
            url = reverse('admin:inventory_site_change', args=[obj.site.id])
            return format_html('<a href="{}">{}</a>', url, obj.site.name)
        return '-'
    site_link.short_description = 'Site'
    
    def cluster_link(self, obj):
        if obj.cluster:
            url = reverse('admin:inventory_cluster_change', args=[obj.cluster.id])
            return format_html('<a href="{}">{}</a>', url, obj.cluster.name)
        return '-'
    cluster_link.short_description = 'Cluster'
    
    def tenant_link(self, obj):
        if obj.tenant:
            url = reverse('admin:inventory_tenant_change', args=[obj.tenant.id])
            return format_html('<a href="{}">{}</a>', url, obj.tenant.name)
        return '-'
    tenant_link.short_description = 'Tenant'
    
    def config_preview(self, obj):
        """Aperçu de la configuration"""
        if not obj.id:  # Si l'objet n'est pas encore sauvegardé
            return "Configuration preview will be available after saving."
        
        files = obj.get_full_config()
        html = ['<div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">']
        
        for filename, content in files.items():
            if content:
                preview = content[:500] + ('...' if len(content) > 500 else '')
                html.append(f'<h5>{filename}</h5>')
                html.append(f'<pre style="background-color: #e9ecef; padding: 10px; border-radius: 3px; overflow-x: auto;">{preview}</pre>')
        
        html.append('</div>')
        return format_html(''.join(html))
    config_preview.short_description = 'Configuration Preview'
    
    actions = ['validate_configs', 'export_as_tf']
    
    def validate_configs(self, request, queryset):
        valid_count = 0
        for config in queryset:
            result = config.validate_config()
            if result['valid']:
                valid_count += 1
        self.message_user(request, f"{valid_count}/{queryset.count()} configurations are valid")
    validate_configs.short_description = "Validate configurations"
    
    def export_as_tf(self, request, queryset):
        """Exporte les configurations en fichier zip"""
        import zipfile
        from io import BytesIO
        from django.http import HttpResponse
        
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for config in queryset:
                files = config.get_full_config()
                for filename, content in files.items():
                    if content:
                        zip_file.writestr(f"{config.name}_{filename}", content)
        
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="terraform_configs_{timezone.now().strftime("%Y%m%d")}.zip"'
        return response
    export_as_tf.short_description = "Export as .tf files (ZIP)"


# ============================================================================
# PLANS TERRAFORM
# ============================================================================

@admin.register(TerraformPlan)
class TerraformPlanAdmin(ImportExportModelAdmin):
    """Admin pour les plans Terraform"""
    list_display = [
        'id_short', 'config_link', 'status_badge', 'has_changes_badge',
        'resources_summary', 'executed_by', 'duration_display', 'created_at'
    ]
    list_filter = ['status', 'has_changes', 'created_at']
    search_fields = ['config__name', 'plan_id']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'started_at', 'completed_at',
        'duration', 'stdout', 'stderr', 'return_code', 'plan_json_preview'
    ]
    raw_id_fields = ['config', 'executed_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('config', 'plan_id', 'status', 'has_changes')
        }),
        ('Resources Summary', {
            'fields': ('resources_add', 'resources_change', 'resources_destroy')
        }),
        ('Execution', {
            'fields': ('executed_by', 'started_at', 'completed_at', 'duration')
        }),
        ('Results', {
            'fields': ('return_code', 'stdout', 'stderr', 'plan_json_preview'),
            'classes': ('wide',)
        }),
        ('Files', {
            'fields': ('plan_file',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def id_short(self, obj):
        return str(obj.id)[:8] + "..."
    id_short.short_description = 'ID'
    
    def config_link(self, obj):
        url = reverse('admin:terraform_app_terraformconfig_change', args=[obj.config.id])
        return format_html('<a href="{}">{}</a>', url, obj.config.name)
    config_link.short_description = 'Configuration'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'running': 'info',
            'completed': 'success',
            'failed': 'danger',
            'cancelled': 'secondary',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_status_display())
    status_badge.short_description = 'Status'
    
    def has_changes_badge(self, obj):
        if obj.has_changes:
            return format_html('<span class="badge badge-warning">Has Changes</span>')
        return format_html('<span class="badge badge-secondary">No Changes</span>')
    has_changes_badge.short_description = 'Changes'
    
    def resources_summary(self, obj):
        return f"+{obj.resources_add} ~{obj.resources_change} -{obj.resources_destroy}"
    resources_summary.short_description = 'Resources'
    
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
    
    def plan_json_preview(self, obj):
        if obj.plan_json:
            return format_html('<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">{}</pre>',
                             json.dumps(obj.plan_json, indent=2)[:1000])
        return '-'
    plan_json_preview.short_description = 'Plan JSON Preview'


# ============================================================================
# APPLICATIONS TERRAFORM
# ============================================================================

@admin.register(TerraformApply)
class TerraformApplyAdmin(ImportExportModelAdmin):
    """Admin pour les applications Terraform"""
    list_display = [
        'id_short', 'config_link', 'status_badge', 'return_code_display',
        'executed_by', 'duration_display', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['config__name', 'apply_id']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'started_at', 'completed_at',
        'duration', 'stdout', 'stderr', 'return_code', 'outputs_preview', 'state_json_preview'
    ]
    raw_id_fields = ['config', 'plan', 'executed_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('config', 'plan', 'apply_id', 'status')
        }),
        ('Execution', {
            'fields': ('executed_by', 'started_at', 'completed_at', 'duration')
        }),
        ('Results', {
            'fields': ('return_code', 'stdout', 'stderr'),
            'classes': ('wide',)
        }),
        ('Outputs', {
            'fields': ('outputs_preview',),
            'classes': ('collapse',)
        }),
        ('State', {
            'fields': ('state_json_preview',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def id_short(self, obj):
        return str(obj.id)[:8] + "..."
    id_short.short_description = 'ID'
    
    def config_link(self, obj):
        url = reverse('admin:terraform_app_terraformconfig_change', args=[obj.config.id])
        return format_html('<a href="{}">{}</a>', url, obj.config.name)
    config_link.short_description = 'Configuration'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'running': 'info',
            'completed': 'success',
            'failed': 'danger',
            'cancelled': 'secondary',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_status_display())
    status_badge.short_description = 'Status'
    
    def return_code_display(self, obj):
        if obj.return_code == 0:
            return format_html('<span style="color: #28a745;">✓ Success</span>')
        elif obj.return_code:
            return format_html('<span style="color: #dc3545;">✗ Failed ({})</span>', obj.return_code)
        return '-'
    return_code_display.short_description = 'Return Code'
    
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
    
    def outputs_preview(self, obj):
        if obj.outputs:
            return format_html('<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">{}</pre>',
                             json.dumps(obj.outputs, indent=2))
        return '-'
    outputs_preview.short_description = 'Outputs'
    
    def state_json_preview(self, obj):
        if obj.state_json:
            return format_html('<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">{}</pre>',
                             json.dumps(obj.state_json, indent=2)[:1000])
        return '-'
    state_json_preview.short_description = 'State Preview'


# ============================================================================
# ÉTATS TERRAFORM
# ============================================================================

@admin.register(TerraformState)
class TerraformStateAdmin(ImportExportModelAdmin):
    """Admin pour les états Terraform"""
    list_display = [
        'config_link', 'version', 'resources_count', 'resources_summary_preview', 'captured_at'
    ]
    list_filter = ['captured_at']
    search_fields = ['config__name', 'lineage']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'captured_at',
        'version', 'lineage', 'serial', 'resources_count',
        'state_json_preview', 'resources_summary_preview'
    ]
    raw_id_fields = ['config', 'apply']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('config', 'apply', 'version', 'lineage', 'serial')
        }),
        ('Resources', {
            'fields': ('resources_count', 'resources_summary_preview')
        }),
        ('State File', {
            'fields': ('state_file',),
            'classes': ('collapse',)
        }),
        ('State JSON', {
            'fields': ('state_json_preview',),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'captured_at'),
            'classes': ('collapse',)
        }),
    )
    
    def config_link(self, obj):
        url = reverse('admin:terraform_app_terraformconfig_change', args=[obj.config.id])
        return format_html('<a href="{}">{}</a>', url, obj.config.name)
    config_link.short_description = 'Configuration'
    
    def resources_summary_preview(self, obj):
        if obj.resources_summary:
            by_type = obj.resources_summary.get('by_type', {})
            by_provider = obj.resources_summary.get('by_provider', {})
            
            html = ['<div>']
            html.append('<h6>By Type:</h6><ul>')
            for rtype, count in list(by_type.items())[:5]:
                html.append(f'<li>{rtype}: {count}</li>')
            if len(by_type) > 5:
                html.append(f'<li>... and {len(by_type) - 5} more</li>')
            html.append('</ul>')
            
            html.append('<h6>By Provider:</h6><ul>')
            for provider, count in list(by_provider.items())[:3]:
                html.append(f'<li>{provider}: {count}</li>')
            if len(by_provider) > 3:
                html.append(f'<li>... and {len(by_provider) - 3} more</li>')
            html.append('</ul></div>')
            
            return format_html(''.join(html))
        return '-'
    resources_summary_preview.short_description = 'Resources Summary'
    
    def state_json_preview(self, obj):
        if obj.state_json:
            return format_html('<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">{}</pre>',
                             json.dumps(obj.state_json, indent=2)[:2000])
        return '-'
    state_json_preview.short_description = 'State JSON Preview'


# ============================================================================
# MODULES TERRAFORM
# ============================================================================

@admin.register(TerraformModule)
class TerraformModuleAdmin(ImportExportModelAdmin):
    """Admin pour les modules Terraform"""
    list_display = [
        'name', 'namespace', 'version', 'source_badge',
        'download_count', 'used_in_configs', 'created_at'
    ]
    list_filter = ['source', 'namespace']
    search_fields = ['name', 'namespace', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'download_count', 'used_in_configs']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'namespace', 'version', 'description', 'documentation')
        }),
        ('Source', {
            'fields': ('source', 'source_url', 'source_version')
        }),
        ('Variables', {
            'fields': ('input_variables', 'output_variables'),
            'classes': ('collapse',)
        }),
        ('Providers', {
            'fields': ('required_providers',),
            'classes': ('collapse',)
        }),
        ('Files', {
            'fields': ('module_path', 'readme'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('download_count', 'used_in_configs'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def source_badge(self, obj):
        colors = {
            'local': 'secondary',
            'registry': 'success',
            'git': 'warning',
            'http': 'info',
        }
        color = colors.get(obj.source, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_source_display())
    source_badge.short_description = 'Source'


# ============================================================================
# PROVIDERS TERRAFORM
# ============================================================================

@admin.register(TerraformProvider)
class TerraformProviderAdmin(ImportExportModelAdmin):
    """Admin pour les providers Terraform"""
    list_display = ['name', 'version', 'source', 'documentation_link', 'created_at']
    list_filter = ['name']
    search_fields = ['name', 'source']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'version', 'source')
        }),
        ('Configuration', {
            'fields': ('config_schema', 'default_config'),
            'classes': ('collapse',)
        }),
        ('Documentation', {
            'fields': ('documentation_url', 'documentation_link'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def documentation_link(self, obj):
        if obj.documentation_url:
            return format_html('<a href="{}" target="_blank">📚 Documentation</a>', obj.documentation_url)
        return '-'
    documentation_link.short_description = 'Documentation'


# ============================================================================
# VARIABLES TERRAFORM
# ============================================================================

@admin.register(TerraformVariable)
class TerraformVariableAdmin(ImportExportModelAdmin):
    """Admin pour les variables Terraform"""
    list_display = [
        'name', 'config_link', 'environment', 'is_sensitive_badge',
        'value_preview', 'created_by', 'created_at'
    ]
    list_filter = ['environment', 'is_sensitive']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'created_by']
    raw_id_fields = ['config', 'created_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'config', 'environment', 'description')
        }),
        ('Value', {
            'fields': ('value', 'is_sensitive', 'encrypted_value'),
            'description': 'Pour les variables sensibles, utilisez encrypted_value'
        }),
        ('Metadata', {
            'fields': ('created_by', 'id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def config_link(self, obj):
        if obj.config:
            url = reverse('admin:terraform_app_terraformconfig_change', args=[obj.config.id])
            return format_html('<a href="{}">{}</a>', url, obj.config.name)
        return '-'
    config_link.short_description = 'Configuration'
    
    def is_sensitive_badge(self, obj):
        if obj.is_sensitive:
            return format_html('<span class="badge badge-warning">🔒 Sensitive</span>')
        return format_html('<span class="badge badge-success">🔓 Public</span>')
    is_sensitive_badge.short_description = 'Sensitive'
    
    def value_preview(self, obj):
        if obj.is_sensitive:
            return '********'
        if obj.value:
            return str(obj.value)[:50]
        return '-'
    value_preview.short_description = 'Value Preview'


# ============================================================================
# CREDENTIALS TERRAFORM
# ============================================================================

@admin.register(TerraformCredential)
class TerraformCredentialAdmin(ImportExportModelAdmin):
    """Admin pour les credentials Terraform"""
    list_display = [
        'name', 'provider_badge', 'username_display', 
        'configs_count', 'created_by', 'created_at'
    ]
    list_filter = ['provider']
    search_fields = ['name', 'description', 'username']
    readonly_fields = ['id', 'created_at', 'updated_at', 'created_by']
    filter_horizontal = ['configs']
    raw_id_fields = ['created_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'provider', 'description')
        }),
        ('🔑 Credentials', {
            'fields': ('access_key', 'secret_key', 'token'),
            'classes': ('wide',)
        }),
        ('☁️ AWS', {
            'fields': ('aws_profile', 'aws_region'),
            'classes': ('collapse',)
        }),
        ('📊 Azure', {
            'fields': ('azure_subscription_id', 'azure_tenant_id', 'azure_client_id', 'azure_client_secret'),
            'classes': ('collapse',)
        }),
        ('🌐 GCP', {
            'fields': ('gcp_project', 'gcp_service_account'),
            'classes': ('collapse',)
        }),
        ('🔐 SSH', {
            'fields': ('ssh_user', 'ssh_private_key', 'ssh_key_passphrase'),
            'classes': ('collapse',)
        }),
        ('Associations', {
            'fields': ('configs',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def provider_badge(self, obj):
        colors = {
            'aws': '#ff9900',
            'azure': '#0078d4',
            'gcp': '#4285f4',
            'ssh': '#28a745',
            'token': '#6f42c1',
            'custom': '#6c757d',
        }
        color = colors.get(obj.provider, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_provider_display()
        )
    provider_badge.short_description = 'Provider'
    
    def username_display(self, obj):
        if obj.ssh_user:
            return obj.ssh_user
        if obj.aws_profile:
            return obj.aws_profile
        if obj.azure_client_id:
            return obj.azure_client_id[:10] + '...'
        return '-'
    username_display.short_description = 'Username/Profile'
    
    def configs_count(self, obj):
        count = obj.configs.count()
        return format_html('<span class="badge badge-info">{}</span>', count)
    configs_count.short_description = 'Configs'