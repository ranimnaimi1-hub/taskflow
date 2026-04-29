"""
Users Serializers with validation
"""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Team, Role, Permission, UserActivity


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user info for listings"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'role', 'avatar']
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class TeamSerializer(serializers.ModelSerializer):
    """Team serializer"""
    team_lead_name = serializers.CharField(source='team_lead.get_full_name', read_only=True)
    members_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Team
        fields = '__all__'
    
    def get_members_count(self, obj):
        return obj.members.count()


class PermissionSerializer(serializers.ModelSerializer):
    """Permission serializer"""
    class Meta:
        model = Permission
        fields = '__all__'


class RoleSerializer(serializers.ModelSerializer):
    """Role serializer"""
    permissions_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = '__all__'
    
    def get_permissions_details(self, obj):
        perms = Permission.objects.filter(code__in=obj.permissions)
        return PermissionSerializer(perms, many=True).data


class UserActivitySerializer(serializers.ModelSerializer):
    """User activity serializer"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = UserActivity
        fields = '__all__'


class UserListSerializer(serializers.ModelSerializer):
    """User list serializer"""
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_admin = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'role_display', 'status', 'status_display',
            'department', 'is_active', 'is_admin', 'last_login',
            'created_at'
        ]


class UserDetailSerializer(serializers.ModelSerializer):
    """User detail serializer"""
    teams = TeamSerializer(many=True, read_only=True)
    recent_activities = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        exclude = ['password']
    
    def get_recent_activities(self, obj):
        activities = obj.activities.all()[:10]
        return UserActivitySerializer(activities, many=True).data


class UserCreateSerializer(serializers.ModelSerializer):
    """Create user serializer"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'role', 'department', 'job_title'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """Change password serializer"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value