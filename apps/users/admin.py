"""
Users Admin - Ultra Professional
"""
from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from .models import User, Team, Role, Permission, UserActivity
import json


@admin.register(User)
class UserAdmin(ImportExportModelAdmin):
    list_display = ['username_display', 'email', 'role_badge', 'status_badge', 
                   'department', 'is_active', 'created_at']
    list_filter = ['role', 'status', 'is_active', 'department', 'created_at']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'employee_id']
    readonly_fields = ['created_at', 'updated_at', 'last_login', 'last_activity_at']
    
    fieldsets = (
        ('Authentication', {'fields': ('username', 'password', 'email')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone', 'avatar', 
                                      'department', 'job_title', 'employee_id')}),
        ('Permissions', {'fields': ('role', 'status', 'is_active', 'is_staff', 'is_superuser',
                                    'groups', 'user_permissions')}),
        ('Security', {'fields': ('is_verified', 'two_factor_enabled', 'failed_login_attempts', 
                                'account_locked_until', 'last_login_ip')}),
        ('API Access', {'fields': ('api_access_enabled', 'api_rate_limit')}),
        ('Preferences', {'fields': ('timezone', 'language', 'theme')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at', 'last_login', 'last_activity_at')}),
    )
    
    def username_display(self, obj):
        icons = {
            'superadmin': '👑',
            'admin': '⭐',
            'network_engineer': '🔧',
            'devops_engineer': '⚙️',
            'security_analyst': '🛡️',
            'analyst': '📊',
            'viewer': '👤',
        }
        icon = icons.get(obj.role, '👤')
        display_name = obj.username
        return format_html('<strong>{} {}</strong>', icon, display_name)
    username_display.short_description = 'Username'
    
    def role_badge(self, obj):
        colors = {
            'superadmin': '#dc3545',
            'admin': '#fd7e14',
            'network_engineer': '#0d6efd',
            'devops_engineer': '#198754',
            'security_analyst': '#6f42c1',
            'analyst': '#6c757d',
            'viewer': '#6c757d',
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_role_display()
        )
    role_badge.short_description = 'Role'
    
    def status_badge(self, obj):
        colors = {
            'active': '#198754',
            'inactive': '#6c757d',
            'suspended': '#dc3545',
            'locked': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    actions = ['activate_users', 'deactivate_users', 'suspend_users']
    
    def activate_users(self, request, queryset):
        updated = queryset.update(status='active', is_active=True)
        self.message_user(request, f'{updated} users activated successfully.')
    activate_users.short_description = "Activate selected users"
    
    def deactivate_users(self, request, queryset):
        updated = queryset.update(status='inactive', is_active=False)
        self.message_user(request, f'{updated} users deactivated successfully.')
    deactivate_users.short_description = "Deactivate selected users"
    
    def suspend_users(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        updated = queryset.update(
            status='suspended', 
            is_active=False,
            account_locked_until=timezone.now() + timedelta(days=7)
        )
        self.message_user(request, f'{updated} users suspended for 7 days.')
    suspend_users.short_description = "Suspend selected users"


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'team_lead', 'members_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    filter_horizontal = ['members']
    raw_id_fields = ['team_lead']
    
    def members_count(self, obj):
        count = obj.members.count()
        return format_html('<b>{}</b>', count)
    members_count.short_description = 'Members'


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'permissions_count', 'permissions_preview', 'created_at']
    search_fields = ['name', 'description']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('Permissions', {
            'fields': ('permissions',),
            'description': 'Enter permissions as a JSON list. Example: ["view_dashboard", "manage_inventory"]'
        }),
    )
    
    def permissions_count(self, obj):
        count = len(obj.permissions) if obj.permissions else 0
        if count == 0:
            return format_html('<span style="color: #6c757d;">0</span>')
        return format_html(
            '<span style="background-color: #0d6efd; color: white; padding: 2px 8px; '
            'border-radius: 10px;">{}</span>',
            count
        )
    permissions_count.short_description = 'Count'
    
    def permissions_preview(self, obj):
        if not obj.permissions:
            return format_html('<span style="color: #6c757d;">No permissions</span>')
        
        perms = obj.permissions
        if len(perms) > 3:
            preview = ', '.join(perms[:3])
            remaining = len(perms) - 3
            return format_html(
                '{} <span style="color: #6c757d;">and {} more</span>',
                preview,
                remaining
            )
        return ', '.join(perms)
    permissions_preview.short_description = 'Permissions'
    
    def save_model(self, request, obj, form, change):
        """S'assure que permissions est bien une liste"""
        if isinstance(obj.permissions, str):
            try:
                obj.permissions = json.loads(obj.permissions)
            except:
                obj.permissions = [p.strip() for p in obj.permissions.split(',') if p.strip()]
        super().save_model(request, obj, form, change)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category_badge', 'created_at']
    list_filter = ['category']
    search_fields = ['code', 'name', 'description']
    
    def category_badge(self, obj):
        colors = {
            'inventory': '#0d6efd',
            'ansible': '#dc3545',
            'terraform': '#198754',
            'jenkins': '#fd7e14',
            'monitoring': '#6f42c1',
            'users': '#6c757d',
            'system': '#343a40',
        }
        color = colors.get(obj.category, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px;">{}</span>',
            color, obj.get_category_display()
        )
    category_badge.short_description = 'Category'


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'action_badge', 'severity_badge', 'resource_type', 
                   'success_icon', 'ip_address', 'created_at']
    list_filter = ['action', 'severity', 'success', 'created_at']
    search_fields = ['user__username', 'user__email', 'description', 'resource_type', 'ip_address']
    readonly_fields = ['user', 'action', 'severity', 'description', 'resource_type', 
                      'resource_id', 'ip_address', 'user_agent', 'metadata', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def user_link(self, obj):
        url = f"/admin/users/user/{obj.user.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = 'User'
    
    def action_badge(self, obj):
        colors = {
            'login': '#0d6efd',
            'logout': '#6c757d',
            'create': '#198754',
            'update': '#ffc107',
            'delete': '#dc3545',
            'view': '#17a2b8',
            'execute': '#fd7e14',
            'download': '#20c997',
            'upload': '#0dcaf0',
            'export': '#6610f2',
        }
        color = colors.get(obj.action, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; '
            'border-radius: 3px;">{}</span>',
            color, 'white' if obj.action in ['delete'] else 'black',
            obj.get_action_display()
        )
    action_badge.short_description = 'Action'
    
    def severity_badge(self, obj):
        colors = {
            'low': '#198754',
            'medium': '#ffc107',
            'high': '#fd7e14',
            'critical': '#dc3545',
        }
        color = colors.get(obj.severity, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color, 'white' if obj.severity in ['high', 'critical'] else 'black',
            obj.get_severity_display()
        )
    severity_badge.short_description = 'Severity'
    
    def success_icon(self, obj):
        if obj.success:
            return format_html('<span style="color: #198754;">✓ Success</span>')
        return format_html('<span style="color: #dc3545;">✗ Failed</span>')
    success_icon.short_description = 'Status'