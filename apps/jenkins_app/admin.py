"""
Jenkins App Admin - Interface d'administration professionnelle
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from import_export.admin import ImportExportModelAdmin

from .models import (
    JenkinsServer, JenkinsJob, JenkinsBuild, JenkinsNode,
    JenkinsPlugin, JenkinsCredential, JenkinsView, JenkinsPipeline
)

# ============================================================================
# INLINES
# ============================================================================

class JenkinsJobInline(admin.TabularInline):
    model = JenkinsJob
    extra = 0
    fields = ['name_link', 'job_type', 'color', 'last_build_status', 'is_active']
    readonly_fields = ['name_link', 'job_type', 'color', 'last_build_status']
    can_delete = False

    def name_link(self, obj):
        url = reverse('admin:jenkins_app_jenkinsjob_change', args=[obj.id])
        return format_html('<a href="{}">{}</a>', url, obj.name)
    name_link.short_description = 'Name'

    def has_add_permission(self, request, obj=None):
        return False


class JenkinsBuildInline(admin.TabularInline):
    model = JenkinsBuild
    extra = 0
    fields = ['build_number', 'status_badge', 'result', 'started_at', 'duration_display']
    readonly_fields = ['build_number', 'status_badge', 'result', 'started_at', 'duration_display']
    can_delete = False
    ordering = ['-build_number']

    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'running': 'info',
            'completed': 'success',
            'failed': 'danger',
            'aborted': 'secondary',
            'unstable': 'warning',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_status_display())
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

    def has_add_permission(self, request, obj=None):
        return False


# ============================================================================
# SERVERS
# ============================================================================

@admin.register(JenkinsServer)
class JenkinsServerAdmin(ImportExportModelAdmin):
    list_display = [
        'name_display', 'url', 'status_badge', 'version',
        'jobs_count', 'last_sync_at', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'description', 'url']
    readonly_fields = ['id', 'created_at', 'updated_at', 'version', 'last_sync_at']
    autocomplete_fields = ['created_by']
    inlines = [JenkinsJobInline]

    def name_display(self, obj):
        url = reverse('admin:jenkins_app_jenkinsserver_change', args=[obj.id])
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

    def jobs_count(self, obj):
        return format_html('<span class="badge badge-info">{}</span>', obj.jobs.count())
    jobs_count.short_description = 'Jobs'


# ============================================================================
# JOBS
# ============================================================================

@admin.register(JenkinsJob)
class JenkinsJobAdmin(ImportExportModelAdmin):
    list_display = [
        'name_display', 'server_link', 'job_type', 'color_badge',
        'last_build_status', 'build_count', 'is_active'
    ]
    autocomplete_fields = ['server']
    inlines = [JenkinsBuildInline]

    def name_display(self, obj):
        url = reverse('admin:jenkins_app_jenkinsjob_change', args=[obj.id])
        return format_html('<a href="{}"><strong>{}</strong></a>', url, obj.name)

    def server_link(self, obj):
        url = reverse('admin:jenkins_app_jenkinsserver_change', args=[obj.server.id])
        return format_html('<a href="{}">{}</a>', url, obj.server.name)

    def color_badge(self, obj):
        colors = {
            'blue': 'success',
            'red': 'danger',
            'yellow': 'warning',
            'grey': 'secondary',
        }
        return format_html('<span class="badge badge-{}">{}</span>', colors.get(obj.color, 'info'), obj.color)


# ============================================================================
# BUILDS
# ============================================================================

@admin.register(JenkinsBuild)
class JenkinsBuildAdmin(ImportExportModelAdmin):
    list_display = [
        'id_short', 'job_link', 'build_number', 'status_badge'
    ]

    def id_short(self, obj):
        return str(obj.id)[:8] + "..."

    def job_link(self, obj):
        url = reverse('admin:jenkins_app_jenkinsjob_change', args=[obj.job.id])
        return format_html('<a href="{}">{}</a>', url, obj.job.name)

    def status_badge(self, obj):
        return format_html('<span class="badge badge-info">{}</span>', obj.status)


# ============================================================================
# NODES
# ============================================================================

@admin.register(JenkinsNode)
class JenkinsNodeAdmin(ImportExportModelAdmin):
    list_display = ['name', 'server_link', 'status_badge']
    autocomplete_fields = ['server']

    def server_link(self, obj):
        url = reverse('admin:jenkins_app_jenkinsserver_change', args=[obj.server.id])
        return format_html('<a href="{}">{}</a>', url, obj.server.name)

    def status_badge(self, obj):
        return format_html('<span class="badge badge-info">{}</span>', obj.status)


# ============================================================================
# PLUGINS
# ============================================================================

@admin.register(JenkinsPlugin)
class JenkinsPluginAdmin(ImportExportModelAdmin):
    list_display = ['name', 'version', 'server_link']
    autocomplete_fields = ['server']

    def server_link(self, obj):
        url = reverse('admin:jenkins_app_jenkinsserver_change', args=[obj.server.id])
        return format_html('<a href="{}">{}</a>', url, obj.server.name)


# ============================================================================
# CREDENTIALS (FIXED HERE)
# ============================================================================

@admin.register(JenkinsCredential)
class JenkinsCredentialAdmin(ImportExportModelAdmin):
    list_display = ['name', 'credential_type', 'server_link']
    autocomplete_fields = ['server']  # ✅ FIXED

    def server_link(self, obj):
        url = reverse('admin:jenkins_app_jenkinsserver_change', args=[obj.server.id])
        return format_html('<a href="{}">{}</a>', url, obj.server.name)


# ============================================================================
# VIEWS
# ============================================================================

@admin.register(JenkinsView)
class JenkinsViewAdmin(ImportExportModelAdmin):
    list_display = ['name', 'server_link']
    autocomplete_fields = ['server']

    def server_link(self, obj):
        url = reverse('admin:jenkins_app_jenkinsserver_change', args=[obj.server.id])
        return format_html('<a href="{}">{}</a>', url, obj.server.name)


# ============================================================================
# PIPELINES
# ============================================================================

@admin.register(JenkinsPipeline)
class JenkinsPipelineAdmin(ImportExportModelAdmin):
    list_display = ['name', 'jobs_count']
    filter_horizontal = ['jobs']

    def jobs_count(self, obj):
        return obj.jobs.count()