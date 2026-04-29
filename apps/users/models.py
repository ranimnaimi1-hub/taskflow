"""
Users Models with Roles and Permissions
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from apps.core.models import BaseModel, UUIDModel
import uuid


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'superadmin')
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser, BaseModel):
    """Enhanced User model with roles and permissions"""
    
    ROLE_CHOICES = [
        ('superadmin', 'Super Administrator'),
        ('admin', 'Administrator'),
        ('network_engineer', 'Network Engineer'),
        ('devops_engineer', 'DevOps Engineer'),
        ('security_analyst', 'Security Analyst'),
        ('analyst', 'Analyst'),
        ('viewer', 'Viewer'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('locked', 'Locked'),
    ]
    
    # Override username to make it non-unique (use email as unique)
    username = models.CharField(max_length=150)
    email = models.EmailField(unique=True, db_index=True)
    
    # Role and Status
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='viewer', db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Profile
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    department = models.CharField(max_length=100, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    employee_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    
    # Security
    is_verified = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    
    # API Access
    api_access_enabled = models.BooleanField(default=True)
    api_rate_limit = models.IntegerField(default=1000, help_text="Requests per hour")
    
    # Preferences
    timezone = models.CharField(max_length=50, default='UTC')
    language = models.CharField(max_length=10, default='en')
    theme = models.CharField(max_length=20, default='light', choices=[('light', 'Light'), ('dark', 'Dark')])
    
    # Activity tracking
    last_activity_at = models.DateTimeField(null=True, blank=True)

    # 👇 AJOUTEZ CETTE LIGNE
    date_joined = models.DateTimeField(auto_now_add=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.email} ({self.get_full_name()})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    @property
    def is_admin(self):
        return self.role in ['superadmin', 'admin']
    
    @property
    def can_manage_inventory(self):
        return self.role in ['superadmin', 'admin', 'network_engineer']
    
    @property
    def can_execute_ansible(self):
        return self.role in ['superadmin', 'admin', 'devops_engineer']
    
    @property
    def can_manage_terraform(self):
        return self.role in ['superadmin', 'admin', 'devops_engineer']
    
    @property
    def is_account_locked(self):
        if self.account_locked_until:
            from django.utils import timezone
            return timezone.now() < self.account_locked_until
        return False


class Team(BaseModel):
    """Teams for organizing users"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    team_lead = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='led_teams')
    members = models.ManyToManyField(User, related_name='teams', blank=True)
    
    class Meta:
        db_table = 'teams'
    
    def __str__(self):
        return self.name


class Permission(BaseModel):
    """Custom permissions system"""
    CATEGORY_CHOICES = [
        ('inventory', 'Inventory Management'),
        ('ansible', 'Ansible Automation'),
        ('terraform', 'Terraform IaC'),
        ('jenkins', 'Jenkins CI/CD'),
        ('monitoring', 'Monitoring'),
        ('users', 'User Management'),
        ('system', 'System Administration'),
    ]
    
    code = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    
    class Meta:
        db_table = 'permissions'
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.category}.{self.code}"


class Role(BaseModel):
    """Roles with associated permissions"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    permissions = models.JSONField(default=list, help_text="List of permission codes")
    
    class Meta:
        db_table = 'roles'
    
    def __str__(self):
        return self.name
    
    def has_permission(self, permission_code):
        return permission_code in self.permissions


class UserActivity(BaseModel):
    """User activity log"""
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('execute', 'Execute'),
        ('download', 'Download'),
        ('upload', 'Upload'),
        ('export', 'Export'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='low')
    
    description = models.TextField()
    resource_type = models.CharField(max_length=100, blank=True)
    resource_id = models.CharField(max_length=100, blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict)
    
    success = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'user_activities'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action']),
            models.Index(fields=['severity']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.action} - {self.created_at}"
