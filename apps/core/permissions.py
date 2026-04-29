"""
Custom Permission Classes for NetDevOps
"""
from rest_framework import permissions


class IsSuperAdmin(permissions.BasePermission):
    """Only superadmins can access"""
    message = "Only superadmins can perform this action."
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'superadmin'


class IsAdmin(permissions.BasePermission):
    """Superadmins and admins can access"""
    message = "Only administrators can perform this action."
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin


class IsAdminOrReadOnly(permissions.BasePermission):
    """Admins can edit, others can only read"""
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and request.user.is_admin


class CanManageInventory(permissions.BasePermission):
    """Permission to manage network inventory"""
    message = "You don't have permission to manage inventory."
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.can_manage_inventory


class CanExecuteAnsible(permissions.BasePermission):
    """Permission to execute Ansible playbooks"""
    message = "You don't have permission to execute Ansible playbooks."
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.can_execute_ansible


class CanManageTerraform(permissions.BasePermission):
    """Permission to manage Terraform"""
    message = "You don't have permission to manage Terraform."
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.can_manage_terraform


class IsOwnerOrAdmin(permissions.BasePermission):
    """User is owner of object or admin"""
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_admin:
            return True
        
        # Check if object has 'user' or 'owner' or 'created_by' field
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        return False


class IsActiveUser(permissions.BasePermission):
    """User account must be active"""
    message = "Your account is not active."
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.status == 'active'


class HasAPIAccess(permissions.BasePermission):
    """User has API access enabled"""
    message = "Your API access is disabled."
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.api_access_enabled


class IsVerified(permissions.BasePermission):
    """User account must be verified"""
    message = "Your account must be verified first."
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_verified


# Combined permissions
class IsAdminAndActive(permissions.BasePermission):
    """Must be admin and have active account"""
    
    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and 
                request.user.is_admin and request.user.status == 'active')


class HasPermissionCode(permissions.BasePermission):
    """Check if user has specific permission code"""
    required_permission = None
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superadmins have all permissions
        if request.user.role == 'superadmin':
            return True
        
        # Check user's role permissions
        from apps.users.models import Role
        try:
            user_role = Role.objects.get(name=request.user.role)
            permission_code = self.required_permission or getattr(view, 'required_permission', None)
            return user_role.has_permission(permission_code) if permission_code else False
        except Role.DoesNotExist:
            return False
