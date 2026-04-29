"""
Monitoring App Admin - Interface d'administration professionnelle
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from import_export.admin import ImportExportModelAdmin

from .models import (
    SystemMetric, DeviceMetric, InterfaceMetric, ApplicationMetric,
    Alert, AlertThreshold, NotificationChannel, NotificationLog,
    Dashboard, MetricCollection
)


# ============================================================================
# INLINES
# ============================================================================

class NotificationLogInline(admin.TabularInline):
    model = NotificationLog
    extra = 0
    fields = ['channel', 'status_badge', 'sent_at']
    readonly_fields = ['channel', 'status_badge', 'sent_at']
    can_delete = False
    ordering = ['-sent_at']

    def status_badge(self, obj):
        if obj.status is None:
            return "N/A"

        colors = {
            'sent': 'success',
            'failed': 'danger',
            'pending': 'warning',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge badge-{}">{}</span>',
            color,
            obj.get_status_display()
        )

    status_badge.short_description = 'Status'

    def has_add_permission(self, request, obj=None):
        return False


# ============================================================================
# SYSTEM METRICS
# ============================================================================

@admin.register(SystemMetric)
class SystemMetricAdmin(ImportExportModelAdmin):
    """Admin pour les métriques système"""

    list_display = [
        'id_short', 'collected_at', 'cpu_usage_bar',
        'memory_usage_bar', 'disk_usage_bar', 'load_avg_display'
    ]

    list_filter = ['collected_at']
    readonly_fields = ['id', 'created_at', 'collected_at', 'usage_bars']
    ordering = ['-collected_at']

    fieldsets = (
        ('Timing', {
            'fields': ('collected_at', 'created_at')
        }),
        ('CPU', {
            'fields': ('cpu_usage', 'cpu_count', 'load_avg_1min', 'load_avg_5min', 'load_avg_15min')
        }),
        ('Memory', {
            'fields': ('memory_total', 'memory_available', 'memory_used', 'memory_percent')
        }),
        ('Disk', {
            'fields': ('disk_total', 'disk_used', 'disk_free', 'disk_percent')
        }),
        ('Network', {
            'fields': ('network_bytes_sent', 'network_bytes_recv',
                       'network_packets_sent', 'network_packets_recv')
        }),
        ('Visualization', {
            'fields': ('usage_bars',),
            'classes': ('wide',)
        }),
    )

    def id_short(self, obj):
        return str(obj.id)[:8] + "..."

    id_short.short_description = 'ID'

    # ---------------- CPU ----------------
    def cpu_usage_bar(self, obj):
        if obj.cpu_usage is None:
            return "N/A"

        color = 'danger' if obj.cpu_usage > 80 else 'warning' if obj.cpu_usage > 60 else 'success'

        return format_html(
            '<div class="progress" style="height: 20px; width: 100px;">'
            '<div class="progress-bar bg-{}" style="width: {}%;">{}%</div>'
            '</div>',
            color, obj.cpu_usage, obj.cpu_usage
        )

    cpu_usage_bar.short_description = 'CPU'

    # ---------------- Memory ----------------
    def memory_usage_bar(self, obj):
        if obj.memory_percent is None:
            return "N/A"

        color = 'danger' if obj.memory_percent > 80 else 'warning' if obj.memory_percent > 60 else 'success'

        return format_html(
            '<div class="progress" style="height: 20px; width: 100px;">'
            '<div class="progress-bar bg-{}" style="width: {}%;">{}%</div>'
            '</div>',
            color, obj.memory_percent, obj.memory_percent
        )

    memory_usage_bar.short_description = 'Memory'

    # ---------------- Disk ----------------
    def disk_usage_bar(self, obj):
        if obj.disk_percent is None:
            return "N/A"

        color = 'danger' if obj.disk_percent > 80 else 'warning' if obj.disk_percent > 60 else 'success'

        return format_html(
            '<div class="progress" style="height: 20px; width: 100px;">'
            '<div class="progress-bar bg-{}" style="width: {}%;">{}%</div>'
            '</div>',
            color, obj.disk_percent, obj.disk_percent
        )

    disk_usage_bar.short_description = 'Disk'

    # ---------------- Load Average ----------------
    def load_avg_display(self, obj):
        if obj.load_avg_1min is None:
            return "N/A"

        return f"{obj.load_avg_1min:.2f}, {obj.load_avg_5min:.2f}, {obj.load_avg_15min:.2f}"

    load_avg_display.short_description = 'Load Average'

    # ---------------- Combined View ----------------
    def usage_bars(self, obj):

        def render(label, value):
            if value is None:
                return f"<div><strong>{label}:</strong> N/A</div>"

            color = 'danger' if value > 80 else 'warning' if value > 60 else 'success'

            return (
                f'<div><strong>{label}:</strong> {value}%</div>'
                f'<div class="progress" style="height: 20px; margin-bottom: 10px;">'
                f'<div class="progress-bar bg-{color}" style="width: {value}%;"></div>'
                f'</div>'
            )

        html = '<div>'
        html += render("CPU", obj.cpu_usage)
        html += render("Memory", obj.memory_percent)
        html += render("Disk", obj.disk_percent)
        html += '</div>'

        return format_html(html)

    usage_bars.short_description = 'Resource Usage'